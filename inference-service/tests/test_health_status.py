"""D15 (AI-10): degraded = real model failure only; dependencies have their own status; both recover."""
import asyncio
import sys
import types

import pytest
import torch
from fastapi import HTTPException

from app import main, schemas, services, visual_index
from app.registry import registry


@pytest.fixture(autouse=True)
def real_mode(monkeypatch):
    monkeypatch.setattr(services.settings, "force_stub", False)
    monkeypatch.setattr(registry, "degraded", set())
    monkeypatch.setattr(registry, "dependencies", {})
    monkeypatch.setattr(services, "_dep_checked", {})
    monkeypatch.setattr(services, "_milvus_cache", {})


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


def test_unreadable_image_and_audio_are_not_model_failures(monkeypatch, tmp_path):
    monkeypatch.setattr(registry, "models", {"vit": object(), "asr_ctc": object()})
    _expect_503(services.run_vision, schemas.VisionRequest(keyframes=["not-a-real-image"]))
    _expect_503(services.run_asr, schemas.ASRRequest(audio_url=str(tmp_path / "missing.wav")))
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


# ---- dependency unavailable: own status, model stays healthy, recovers ----

def test_milvus_search_failure_is_dependency_not_siamese(monkeypatch):
    monkeypatch.setattr(registry, "models", {"siamese": object()})
    monkeypatch.setattr(services, "_load_keyframe", lambda ref: torch.zeros(3, 224, 224))
    monkeypatch.setattr(visual_index, "encode", lambda images: [[0.1] * 128])
    calls = {"n": 0}

    def search(vector, top_k, threshold):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("DEADLINE_EXCEEDED")
        return []
    monkeypatch.setattr(visual_index, "search", search)
    req = schemas.SearchRequest(image="x", top_k=1, threshold=0.5)
    _expect_503(services.run_search, req)
    assert registry.degraded == set() and registry.dependencies["visual_index"] == "unavailable"
    services.run_search(req)
    assert registry.dependencies["visual_index"] == "ok"


def _fake_pymilvus(monkeypatch, state):
    class Collection:
        def __init__(self, name):
            self.name = name

        def load(self):
            pass

    def connect(**kwargs):
        if state.get("down"):
            raise ConnectionError("Milvus down")
    fake = types.SimpleNamespace(Collection=Collection, connections=types.SimpleNamespace(connect=connect),
                                 utility=types.SimpleNamespace(has_collection=lambda name: state["has"]))
    monkeypatch.setitem(sys.modules, "pymilvus", fake)


def test_recommendation_index_status_and_recovery(monkeypatch):
    state = {"has": False}
    _fake_pymilvus(monkeypatch, state)
    monkeypatch.setattr(registry, "models", {"two_tower": object()})
    req = schemas.RecommendationRequest(user_id="usr_1", limit=1)
    _expect_503(services.run_recommendation, req)
    assert registry.dependencies["recommendation_index"] == "missing_collection"
    assert registry.degraded == set()
    state["has"] = True
    services.refresh_dependencies()            # inside retry window: no new probe
    assert registry.dependencies["recommendation_index"] == "missing_collection"
    monkeypatch.setattr(services, "_DEP_RETRY_S", 0)
    services.refresh_dependencies()
    assert registry.dependencies["recommendation_index"] == "ok"
    state["down"] = True
    services._milvus_cache.clear()
    services.refresh_dependencies()            # ok deps are not re-probed
    assert registry.dependencies["recommendation_index"] == "ok"
    _expect_503(services.run_recommendation, req)
    assert registry.dependencies["recommendation_index"] == "unavailable"


def test_health_reports_dependencies(monkeypatch):
    monkeypatch.setattr(registry, "dependencies", {"visual_index": "ok", "recommendation_index": "missing_collection"})
    monkeypatch.setattr(services, "refresh_dependencies", lambda: None)
    body = asyncio.run(main.health())
    assert body.dependencies == {"visual_index": "ok", "recommendation_index": "missing_collection"}
    assert body.degraded == []
