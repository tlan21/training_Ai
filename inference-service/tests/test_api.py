"""Smoke test /v1/completions, /v1/highlight, /health + auth ở STUB mode (không cần checkpoint/GPU); /v2 stub: test_v2.py."""

import os

os.environ["FORCE_STUB"] = "1"
os.environ["AI_SERVICE_KEY"] = "sk-local-test"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

AUTH = {"Authorization": "Bearer sk-local-test"}


def _client():
    return TestClient(app)


def test_health_stub():
    with _client() as c:
        r = c.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["stub_mode"] is True
        assert body["models_loaded"] == []
        assert body["degraded"] == []
        assert body["queue_depth"] == 0


def test_auth_required():
    with _client() as c:
        r = c.post("/v1/completions", json={"prompt": "xin chào"})
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "UNAUTHORIZED"


def test_auth_wrong_key():
    with _client() as c:
        r = c.post("/v1/completions", json={"prompt": "x"}, headers={"Authorization": "Bearer wrong"})
        assert r.status_code == 401


def test_completions():
    with _client() as c:
        r = c.post("/v1/completions", json={"prompt": "Tóm tắt trận đấu hôm nay rất kịch tính",
                                            "max_tokens": 20}, headers=AUTH)
        assert r.status_code == 200
        body = r.json()
        assert body["object"] == "text_completion"
        assert body["choices"][0]["text"]
        assert body["usage"]["total_tokens"] > 0


def test_highlight_scale_0_100():
    with _client() as c:
        feats = {"vision_embeddings": [[0.1, 0.2]] * 10, "audio_spectrogram_features": [[1.0, 2.0]] * 10}
        r = c.post("/v1/highlight/completions",
                   json={"video_id": "vid_001", "features": feats}, headers=AUTH)
        assert r.status_code == 200
        body = r.json()
        assert len(body["timeline_scores"]) == 10
        for ts in body["timeline_scores"]:
            assert 0 <= ts["score"] <= 100


def test_validation_error_envelope():
    with _client() as c:
        r = c.post("/v1/completions", json={"max_tokens": 5}, headers=AUTH)  # thiếu prompt
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "VALIDATION_ERROR"
