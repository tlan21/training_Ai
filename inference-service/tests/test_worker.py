"""D24 (AI-14): pure model worker + facade→worker transport. No Milvus/MinIO anywhere in these tests."""
import io
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
import torch
import uvicorn
from PIL import Image

from app import schemas, services, worker, worker_app, worker_client
from app.registry import registry

KEY = "wk-test-" + "x" * 24


def png():
    data = io.BytesIO()
    Image.new("RGB", (16, 16), "red").save(data, format="PNG")
    return data.getvalue()


class ViT:
    def __call__(self, imgs, return_embedding):
        logits = torch.zeros(len(imgs), 4)
        logits[:, 2] = 1
        return logits, torch.full((len(imgs), 256), 0.25)


class Siamese:
    def backbone(self, imgs, return_embedding):
        return None, torch.full((len(imgs), 256), 0.75)

    def encode(self, batch):
        return torch.ones(len(batch), 128) / 128**.5


class Fusion:
    def __call__(self, vision, audio):
        if vision.shape[1] == 3:
            raise RuntimeError("CUDA error: device-side assert")
        return torch.full((1, vision.shape[1]), 0.5)


@pytest.fixture
def fake_models(monkeypatch):
    monkeypatch.setattr(registry, "models", {"vit": ViT(), "siamese": Siamese(), "highlight_fusion": Fusion()})
    monkeypatch.setattr(registry, "loaded", ["vit", "siamese", "highlight_fusion"])
    monkeypatch.setattr(registry, "vit_classes", ["bong_da", "the_thao", "ca_nhac", "tin_tuc"])
    monkeypatch.setattr(registry, "device", "cpu")
    monkeypatch.setattr(registry, "degraded", set())
    monkeypatch.setattr(registry, "dependencies", {})


def test_worker_never_imports_data_clients():
    code = ("import sys; import app.worker, app.worker_app, app.worker_client; "
            "bad = [m for m in ('minio', 'pymilvus') if m in sys.modules]; assert not bad, bad")
    subprocess.run([sys.executable, "-c", code], check=True, cwd=Path(__file__).resolve().parents[1])


def test_worker_ops_take_bytes_and_vectors(fake_models):
    category, emb, logit_sums = worker.vision([png(), png()])
    assert category == "ca_nhac" and len(emb) == 2 and len(emb[0]) == 256
    assert emb[0][0] == 0.75                                   # Fusion input = Siamese backbone, not the ViT classifier
    assert logit_sums == {"bong_da": 0.0, "the_thao": 0.0, "ca_nhac": 2.0, "tin_tuc": 0.0}
    vectors = worker.siamese([png()])
    assert len(vectors[0]) == 128 and sum(x * x for x in vectors[0]) == pytest.approx(1)
    assert worker.highlight([[0.0] * 256] * 2, [[0.0] * 64] * 2)["scores"] == [50.0, 50.0]
    with pytest.raises(worker.InvalidInput):
        worker.siamese([b"not an image"])
    with pytest.raises(worker.InvalidInput):
        worker.asr(b"\x00" * 5)


@pytest.fixture
def remote_worker(fake_models, monkeypatch):
    """Real HTTP worker (uvicorn thread, lifespan off so the fake models stay) + facade in remote mode."""
    monkeypatch.setenv("MODEL_WORKER_KEY", KEY)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(worker_app.app, host="127.0.0.1", port=port, lifespan="off", log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)
    monkeypatch.setattr(worker_client.settings, "model_worker_url", f"http://127.0.0.1:{port}")
    monkeypatch.setattr(worker_client.settings, "model_worker_key", KEY)
    yield port
    server.should_exit = True
    thread.join(5)


def test_remote_worker_returns_same_results_as_in_process(remote_worker):
    assert worker_client.remote()
    assert worker_client.call("siamese", images=[png()]) == worker.siamese([png()])
    assert worker_client.call("vision", images=[png()]) == worker.vision([png()])
    req = schemas.HighlightRequest(video_id="vid_t", features=schemas.HighlightFeatures(
        vision_embeddings=[[0.0] * 256] * 2, audio_spectrogram_features=[[0.0] * 64] * 2))
    remote_out = services.run_highlight(req)
    assert [t.score for t in remote_out.timeline_scores] == [50.0, 50.0]
    assert registry.dependencies["model_worker"] == "ok"


def test_remote_errors_keep_facade_semantics(remote_worker, monkeypatch):
    with pytest.raises(worker.InvalidInput):                       # 422 → validation, model not degraded
        worker_client.call("highlight", vision=[[0.0] * 255], audio=[[0.0] * 64])
    with pytest.raises(RuntimeError) as model_failure:            # 500 MODEL_ERROR → model failure
        worker_client.call("highlight", vision=[[0.0] * 256] * 3, audio=[[0.0] * 64] * 3)
    assert not isinstance(model_failure.value, worker_client.DependencyError)
    monkeypatch.setattr(worker_client.settings, "model_worker_key", "wrong-key-" + "y" * 24)
    with pytest.raises(worker_client.DependencyError) as unauthorized:
        worker_client.call("siamese", images=[png()])
    assert unauthorized.value.dependency == "model_worker" and "401" in str(unauthorized.value)


def test_unreachable_worker_is_dependency_not_model_failure(fake_models, monkeypatch):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]                                   # closed again: nothing listens
    monkeypatch.setattr(worker_client.settings, "model_worker_url", f"http://127.0.0.1:{port}")
    monkeypatch.setattr(worker_client.settings, "model_worker_key", KEY)
    monkeypatch.setattr(services.settings, "force_stub", False)
    req = schemas.HighlightRequest(video_id="vid_t", features=schemas.HighlightFeatures(
        vision_embeddings=[[0.0] * 256], audio_spectrogram_features=[[0.0] * 64]))
    with pytest.raises(Exception) as err:
        services.run_highlight(req)
    assert err.value.status_code == 503
    assert registry.degraded == set() and registry.dependencies["model_worker"] == "unavailable"
    assert worker_client.gpu_stats() == (0.0, 0.0)


@pytest.mark.parametrize("key", ["", "short", worker_client.DEV_KEY])
def test_attach_refuses_weak_or_shared_keys(monkeypatch, key):
    monkeypatch.setattr(worker_client.settings, "model_worker_url", "http://127.0.0.1:9")
    monkeypatch.setattr(worker_client.settings, "model_worker_key", key)
    with pytest.raises(RuntimeError, match="MODEL_WORKER_KEY"):
        worker_client.attach()
    monkeypatch.setattr(worker_client.settings, "model_worker_key", worker_client.settings.ai_service_key)
    with pytest.raises(RuntimeError, match="MODEL_WORKER_KEY"):
        worker_client.attach()
