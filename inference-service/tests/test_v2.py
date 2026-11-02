"""AI-15 (D24): AI-API v2.0 compute-only endpoints — never MinIO/Milvus, stable errors, ASR splits = one-shot."""
import base64
import io
import sys
import wave

import pytest
import torch
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image

from app import main, schemas, services, v2, visual_index
from app.config import settings
from app.registry import registry


def png_b64():
    data = io.BytesIO()
    Image.new("RGB", (16, 16), "red").save(data, format="PNG")
    return base64.b64encode(data.getvalue()).decode()


def wav_bytes(seconds, sr=16000):
    data = io.BytesIO()
    with wave.open(data, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(b"\x10\x00" * int(seconds * sr))
    return data.getvalue()


AUTH = {"Authorization": f"Bearer {settings.ai_service_key}"}


@pytest.fixture
def stub_client(monkeypatch):
    monkeypatch.setattr(settings, "force_stub", True)
    with TestClient(main.app) as c:
        yield c


def test_v2_requires_bearer(stub_client):
    for path in ("/v2/vision/completions", "/v2/search/embeddings", "/v2/recommendation/embeddings", "/v2/asr/completions"):
        r = stub_client.post(path, json={})
        assert r.status_code == 401 and r.json()["error"]["code"] == "UNAUTHORIZED", path


def test_v2_stub_shapes_for_mock_development(stub_client):
    r = stub_client.post("/v2/vision/completions", headers=AUTH, json={"keyframes": [png_b64(), "data:image/png;base64," + png_b64()]})
    body = r.json()
    assert r.status_code == 200 and len(body["siamese_vectors"]) == 2 and len(body["siamese_vectors"][0]) == 128
    assert len(body["embeddings_256"]) == 2 and max(body["category_logit_sums"], key=body["category_logit_sums"].get) == body["category_suggestion"]
    r = stub_client.post("/v2/search/embeddings", headers=AUTH, json={"image": png_b64()})
    assert r.status_code == 200 and r.json()["dim"] == 128 and sum(x * x for x in r.json()["vector"]) == pytest.approx(1, abs=1e-4)
    r = stub_client.post("/v2/asr/completions", headers=AUTH, files={"file": ("a.wav", wav_bytes(1), "audio/wav")}, data={"offset_seconds": "40"})
    assert r.status_code == 200 and r.json()["segments"][0]["start_time"] == 40.0
    r = stub_client.post("/v2/recommendation/embeddings", headers=AUTH, json={
        "videos": [{"video_id": "vid_a", "category_id": "cat_x"}], "users": [{"user_id": "usr_a", "positive_video_ids": ["vid_a"]}]})
    assert r.status_code == 200 and [u["user_id"] for u in r.json()["users"]] == ["usr_a"]


def test_v2_validation_errors(stub_client, monkeypatch):
    r = stub_client.post("/v2/vision/completions", headers=AUTH, json={"keyframes": ["E:/srv/work/vid_x/00000001.jpg"]})
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"      # no server paths in v2
    r = stub_client.post("/v2/recommendation/embeddings", headers=AUTH, json={"users": [{"user_id": "usr_a", "positive_video_ids": ["vid_missing"]}]})
    assert r.status_code == 422
    r = stub_client.post("/v2/asr/completions", headers=AUTH, files={"file": ("a.wav", wav_bytes(1))}, data={"language": "en"})
    assert r.status_code == 422
    monkeypatch.setattr(v2, "MAX_AUDIO_BYTES", 10)
    r = stub_client.post("/v2/asr/completions", headers=AUTH, files={"file": ("a.wav", wav_bytes(1))})
    assert r.status_code == 413 and r.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


# ---- real mode (fake models): no data store is ever touched ----

class ViT:
    def __call__(self, imgs, return_embedding):
        return torch.ones(len(imgs), 4), torch.zeros(len(imgs), 256)


class Siamese:
    def backbone(self, imgs, return_embedding):
        return None, torch.zeros(len(imgs), 256)

    def encode(self, batch):
        return torch.ones(len(batch), 128) / 128**.5


@pytest.fixture
def real_no_storage(monkeypatch):
    monkeypatch.setattr(settings, "force_stub", False)
    monkeypatch.setattr(registry, "models", {"vit": ViT(), "siamese": Siamese(), "asr_ctc": object()})
    monkeypatch.setattr(registry, "vit_classes", ["bong_da", "the_thao", "ca_nhac", "tin_tuc"])
    monkeypatch.setattr(registry, "degraded", set())
    monkeypatch.setattr(registry, "dependencies", {})

    def forbidden(*args, **kwargs):
        raise AssertionError("v2 must not touch MinIO/Milvus")
    for name in ("collection", "index_frames", "search"):
        monkeypatch.setattr(visual_index, name, forbidden)
    monkeypatch.setattr(services, "_milvus_collection", forbidden)
    monkeypatch.setitem(sys.modules, "minio", None)
    monkeypatch.setitem(sys.modules, "pymilvus", None)


def test_real_vision_and_search_return_vectors_only(real_no_storage):
    out = v2.run_vision(schemas.VisionV2Request(keyframes=[png_b64()] * 17))       # crosses the 16-frame Siamese batch
    assert len(out.siamese_vectors) == 17 and out.category_logit_sums["bong_da"] == 17.0
    vec = v2.run_search_embedding(schemas.SearchEmbeddingRequest(image=png_b64())).vector
    assert len(vec) == 128 and registry.degraded == set()
    with pytest.raises(HTTPException) as bad:
        v2.run_search_embedding(schemas.SearchEmbeddingRequest(image=base64.b64encode(b"not an image").decode()))
    assert bad.value.status_code == 422                                                  # unreadable image is input, not model


def test_real_asr_split_at_20s_matches_one_shot(real_no_storage, monkeypatch):
    def decode(signal):
        n = round(signal.numel() / 16000)
        return f"w{n}", [schemas.ASRSegment(id=0, start_time=1.0, end_time=2.0, text=f"w{n}", confidence=0.5)]
    monkeypatch.setattr(services, "_decode_asr", decode)
    whole = v2.run_asr(wav_bytes(50), 0.0, "m")
    parts = [v2.run_asr(wav_bytes(40), 0.0, "m"), v2.run_asr(wav_bytes(10), 40.0, "m")]
    assert [(s.start_time, s.text) for s in whole.segments] == [(s.start_time, s.text) for p in parts for s in p.segments]
    assert [s.start_time for s in whole.segments] == [1.0, 21.0, 41.0]
    with pytest.raises(HTTPException) as bad:
        v2.run_asr(b"not audio", 0.0, "m")
    assert bad.value.status_code == 422 and registry.degraded == set()


def test_real_recommendation_encode_is_not_ready_until_ai12(real_no_storage):
    with pytest.raises(HTTPException) as err:
        v2.run_reco_embeddings(schemas.RecoEmbeddingRequest(users=[schemas.RecoUserFeatures(user_id="usr_a")]))
    assert err.value.status_code == 503 and err.value.detail["code"] == "MODEL_NOT_READY"
