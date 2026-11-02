"""Opt-in smoke against a RUNNING inference-service with real checkpoints (release gate, AI-01).

    INFERENCE_LIVE_URL=http://127.0.0.1:8001 INFERENCE_LIVE_KEY=<AI_SERVICE_KEY> pytest tests/test_live_smoke.py
Optional: INFERENCE_LIVE_MEDIA=<dir with *.jpg + clip.wav> (real media, else synthetic);
          INFERENCE_EXAMPLES_DIR=<dir> writes <endpoint>.{request,response,error}.json from these exact calls.
AI-API v3.0 (AI-23): every input travels in the request (data URI / multipart bytes) — no shared filesystem needed.
"""
import base64
import io
import json
import math
import os
import struct
import urllib.error
import urllib.request
import wave
from pathlib import Path

import pytest

from app import schemas

URL = os.environ.get("INFERENCE_LIVE_URL")
KEY = os.environ.get("INFERENCE_LIVE_KEY", "")
MEDIA = os.environ.get("INFERENCE_LIVE_MEDIA")
EXAMPLES = os.environ.get("INFERENCE_EXAMPLES_DIR")
MODELS = {"vit", "siamese", "asr_ctc", "highlight_fusion", "minigpt", "two_tower"}

pytestmark = pytest.mark.skipif(not URL, reason="set INFERENCE_LIVE_URL to smoke a running real service")


def _call(method, path, body=None, auth=True):
    headers = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = f"Bearer {KEY}"
    req = urllib.request.Request(URL + path, method=method, headers=headers,
                                 data=None if body is None else json.dumps(body).encode())
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _save(name, kind, data):
    if EXAMPLES:
        Path(EXAMPLES).mkdir(parents=True, exist_ok=True)
        Path(EXAMPLES, f"{name}.{kind}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _example(name, method, path, body=None, auth=True, kind="response"):
    """Call once; with INFERENCE_EXAMPLES_DIR save the exact request and {http_status, body}."""
    if body is not None:
        _save(name, "request" if kind == "response" else "error_request", body)
    status, data = _call(method, path, body, auth)
    _save(name, kind, {"http_status": status, "body": data})
    return status, data


@pytest.fixture(scope="module")
def media(tmp_path_factory):
    if MEDIA:
        frames = sorted(Path(MEDIA).glob("*.jpg"))[:3]
        return [f.read_bytes() for f in frames], str(Path(MEDIA, "clip.wav").resolve())
    from PIL import Image
    frames = []
    for i in range(3):
        buf = io.BytesIO()
        Image.new("RGB", (224, 224), (40 * i, 120, 200 - 40 * i)).save(buf, "JPEG")
        frames.append(buf.getvalue())
    wav = tmp_path_factory.mktemp("live") / "clip.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 220 * t / 16000))) for t in range(3 * 16000)))
    return frames, str(wav)


def _data_uri(jpg):
    return "data:image/jpeg;base64," + base64.b64encode(jpg).decode()


def test_health_real_and_auth():
    status, body = _example("health", "GET", "/health", auth=False)
    health = schemas.HealthResponse.model_validate(body)
    assert status == 200 and not health.stub_mode and set(health.models_loaded) == MODELS
    assert not {"visual_index", "recommendation_index"} & set(health.dependencies)    # v3.0: no MinIO/Milvus left
    status, body = _example("completions", "POST", "/v1/completions", {"prompt": "x", "max_tokens": 1}, auth=False, kind="error")
    assert status == 401 and body["error"]["code"] == "UNAUTHORIZED"


def test_vision_then_highlight(media):
    frames, wav = media
    status, body = _example("v2_vision", "POST", "/v2/vision/completions", {"keyframes": [_data_uri(f) for f in frames]})
    vision = schemas.VisionV2Response.model_validate(body)
    assert status == 200 and vision.category_suggestion in {"bong_da", "the_thao", "ca_nhac", "tin_tuc"}
    assert len(vision.embeddings_256) == len(frames) and all(len(e) == 256 for e in vision.embeddings_256)
    assert len(vision.siamese_vectors) == len(frames) and all(len(v) == 128 for v in vision.siamese_vectors)
    status, body = _example("v2_vision", "POST", "/v2/vision/completions", {}, kind="error")
    assert status == 422 and body["error"]["code"] == "VALIDATION_ERROR"

    import soundfile as sf
    import torch
    from ai_core.audio.features import audio_features_per_second
    signal, sr = sf.read(wav, dtype="float32")
    audio = audio_features_per_second(torch.from_numpy(signal), sr).tolist()
    n = min(len(audio), len(frames))
    req = {"video_id": "vid_ai01example", "features": {"vision_embeddings": vision.embeddings_256[:n], "audio_spectrogram_features": audio[:n]}}
    status, body = _example("highlight", "POST", "/v1/highlight/completions", req)
    hl = schemas.HighlightResponse.model_validate(body)
    assert status == 200 and [s.second for s in hl.timeline_scores] == list(range(n))
    assert all(0 <= s.score <= 100 for s in hl.timeline_scores)
    bad = {"video_id": "vid_ai01example", "features": {"vision_embeddings": vision.embeddings_256[:n], "audio_spectrogram_features": audio[: n - 1]}}
    status, body = _example("highlight", "POST", "/v1/highlight/completions", bad, kind="error")
    assert status == 503 and body["error"]["code"] == "AI_UNAVAILABLE"
    assert "highlight_fusion" not in _call("GET", "/health", auth=False)[1]["degraded"]   # bad input ≠ model failure


def test_completions():
    prompt = ("Tóm tắt: Chiều nay tại Hà Nội, đội tuyển bóng đá quốc gia đã có buổi tập đầu tiên chuẩn bị cho vòng loại. "
              "Huấn luyện viên cho biết toàn đội đang trong trạng thái tốt và quyết tâm giành chiến thắng.")
    status, body = _example("completions", "POST", "/v1/completions", {"prompt": prompt, "max_tokens": 48, "temperature": 0})
    out = schemas.CompletionResponse.model_validate(body)
    assert status == 200 and out.choices[0].text.strip() and out.usage.completion_tokens <= 48


# ---- /v2 endpoints (AI-15; API_READY since release #6): compute-only ----

def _multipart(path, fields, audio, auth=True):
    boundary = "ai15boundary"
    parts = [f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in fields.items()]
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="clip.wav"\r\nContent-Type: audio/wav\r\n\r\n'.encode()
                 + audio + f"\r\n--{boundary}--\r\n".encode())
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    if auth:
        headers["Authorization"] = f"Bearer {KEY}"
    req = urllib.request.Request(URL + path, method="POST", headers=headers, data=b"".join(parts))
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_v2_search_embedding_matches_vision_vector(media):
    frames, _ = media
    _, out = _call("POST", "/v2/vision/completions", {"keyframes": [_data_uri(f) for f in frames]})
    vis = schemas.VisionV2Response.model_validate(out)
    status, out = _example("v2_search", "POST", "/v2/search/embeddings", {"image": _data_uri(frames[0])})
    emb = schemas.SearchEmbeddingResponse.model_validate(out)
    assert status == 200 and max(abs(a - b) for a, b in zip(emb.vector, vis.siamese_vectors[0])) < 1e-5
    status, out = _example("v2_search", "POST", "/v2/search/embeddings", {"image": "not base64!"}, kind="error")
    assert status == 422 and out["error"]["code"] == "VALIDATION_ERROR"


def test_v2_asr_bytes(media):
    _, wav = media
    fields = {"language": "vi", "offset_seconds": "0"}
    status, out = _multipart("/v2/asr/completions", fields, Path(wav).read_bytes())
    _save("v2_asr", "request", {"multipart": {**fields, "file": f"<{Path(wav).name}, {Path(wav).stat().st_size} bytes>"}})
    _save("v2_asr", "response", {"http_status": status, "body": out})
    asr = schemas.ASRResponse.model_validate(out)
    assert status == 200 and all(0 <= s.start_time <= s.end_time for s in asr.segments)
    status, out = _multipart("/v2/asr/completions", fields, b"not audio")
    _save("v2_asr", "error_request", {"multipart": {**fields, "file": "<9 bytes: 'not audio'>"}})
    _save("v2_asr", "error", {"http_status": status, "body": out})
    assert status == 422 and "asr_ctc" not in _call("GET", "/health", auth=False)[1]["degraded"]


def test_v2_recommendation_encode_not_ready():
    body = {"videos": [{"video_id": "vid_ai15example", "category_id": "cat_bong_da", "positive_count": 3}],
            "users": [{"user_id": "usr_ai15example", "preferred_category_ids": ["cat_bong_da"], "positive_video_ids": ["vid_ai15example"]}]}
    status, out = _example("v2_recommendation", "POST", "/v2/recommendation/embeddings", body, kind="error")
    assert status == 503 and out["error"]["code"] == "MODEL_NOT_READY"      # until AI-12 promotes Two-Tower v2
