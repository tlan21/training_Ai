"""D15 (AI-10): degraded = real model failure only; dependencies have their own status; both recover."""
import asyncio

import pytest
import torch
from fastapi import HTTPException

from app import main, schemas, services
from app.registry import registry


@pytest.fixture(autouse=True)
def real_mode(monkeypatch):
    monkeypatch.setattr(services.settings, "force_stub", False)
    monkeypatch.setattr(registry, "degraded", set())
    monkeypatch.setattr(registry, "dependencies", {})


class Fusion:
    def __init__(self, fail=False):
        self.fail = fail

    def __call__(self, vision, audio):
        if self.fail:
            raise RuntimeError("CUDA error: device-side assert")
        return torch.full((1, vision.shape[1]), 0.5)


def _highlight(n_vision=2, n_audio=2, vdim=256, adim=64):
    return schemas.HighlightRequest(video_id="vid_t", features=schemas.HighlightFeatures(
        vision_embeddings=[[0.0] * vdim] * n_vision, audio_spectrogram_features=[[0.0] * adim] * n_audio))


def _expect_503(fn, *args):
    with pytest.raises(HTTPException) as err:
        fn(*args)
    assert err.value.status_code == 503 and err.value.detail["code"] == "AI_UNAVAILABLE"


# ---- validation error: still 503 (contract unchanged) but never marks the model ----

@pytest.mark.parametrize("req", [_highlight(n_audio=1), _highlight(n_vision=0, n_audio=0), _highlight(vdim=255), _highlight(adim=63)])
def test_invalid_highlight_input_is_not_model_failure(monkeypatch, req):
    monkeypatch.setattr(registry, "models", {"highlight_fusion": Fusion()})
    _expect_503(services.run_highlight, req)
    assert registry.degraded == set()


# ---- model failure: marks degraded, success clears it ----

def test_model_failure_degrades_then_recovers(monkeypatch):
    model = Fusion(fail=True)
    monkeypatch.setattr(registry, "models", {"highlight_fusion": model})
    _expect_503(services.run_highlight, _highlight())
    assert registry.degraded == {"highlight_fusion"}
    model.fail = False
    assert len(services.run_highlight(_highlight()).timeline_scores) == 2
    assert registry.degraded == set()


def test_health_reports_dependencies(monkeypatch):
    # AI-API v3.0: no MinIO/Milvus left; the only dependency is the remote model worker (D24), reported as-is.
    monkeypatch.setattr(registry, "dependencies", {"model_worker": "unavailable"})
    body = asyncio.run(main.health())
    assert body.dependencies == {"model_worker": "unavailable"}
    assert body.degraded == []
