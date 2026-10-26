"""Smoke test 6 endpoint + /health + auth ở STUB mode (không cần checkpoint/GPU)."""

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


def test_search_threshold_filter():
    with _client() as c:
        r = c.post("/v1/search/completions",
                   json={"image": "data:image/jpeg;base64,AAAA", "top_k": 5, "threshold": 0.8},
                   headers=AUTH)
        assert r.status_code == 200
        for res in r.json()["results"]:
            assert res["similarity_score"] >= 0.8
            assert 0 <= res["similarity_score"] <= 1


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


def test_asr():
    with _client() as c:
        r = c.post("/v1/asr/completions",
                   json={"audio_url": "https://storage.local/a.wav"}, headers=AUTH)
        assert r.status_code == 200
        body = r.json()
        assert body["full_transcript"]
        assert all(0 <= s["confidence"] <= 1 for s in body["segments"])


def test_recommendation():
    with _client() as c:
        r = c.post("/v1/recommendation/completions",
                   json={"user_id": "usr_888", "limit": 5}, headers=AUTH)
        assert r.status_code == 200
        recs = r.json()["recommendations"]
        assert len(recs) == 5
        assert all(0 <= x["score"] <= 1 for x in recs)


def test_vision_internal():
    with _client() as c:
        r = c.post("/v1/vision/completions",
                   json={"keyframes": ["f1.png", "f2.png"]}, headers=AUTH)
        assert r.status_code == 200
        body = r.json()
        assert body["category_suggestion"]
        assert len(body["embeddings_256"]) == 2
        assert len(body["embeddings_256"][0]) == 256


def test_validation_error_envelope():
    with _client() as c:
        r = c.post("/v1/completions", json={"max_tokens": 5}, headers=AUTH)  # thiếu prompt
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "VALIDATION_ERROR"


# ---------------- T1.7d: recommendation qua Milvus (collection giả, không cần Milvus thật) -------

class _FakeHit:
    def __init__(self, vid, score):
        self._e, self.score = {"id": vid}, score

    @property
    def entity(self):
        return self._e


class _FakeCollection:
    """Giả Milvus: query trả vector user, search trả danh sách hit định sẵn."""

    def __init__(self, hits, has_user=True):
        self._hits, self._has_user = hits, has_user
        self.nprobe = None

    def query(self, expr, output_fields, limit):
        return [{"vector": [0.0] * 128}] if self._has_user else []

    def search(self, data, anns_field, param, limit, expr, output_fields):
        self.nprobe = param["params"]["nprobe"]
        return [self._hits[:limit]]


def _patch(monkeypatch, col):
    from app import services
    monkeypatch.setattr(services, "_milvus_collection", lambda: col)
    return services


def test_reco_maps_inner_product_to_unit_range(monkeypatch):
    """IP trên vector L2-norm ∈ [-1,1]; schema quy ước score 0–1 nên phải ánh xạ, không truyền thô."""
    services = _patch(monkeypatch, _FakeCollection([_FakeHit("vid_56", 0.2354),
                                                    _FakeHit("vid_9", -1.0)]))
    recs = services._reco_from_milvus("usr_1", 2)
    assert [r.video_id for r in recs] == ["vid_56", "vid_9"]
    assert recs[0].score == round((0.2354 + 1) / 2, 4)
    assert all(0 <= r.score <= 1 for r in recs)


def test_reco_empty_search_falls_back_instead_of_returning_empty(monkeypatch):
    """Đã cắn thật: IVF_FLAT nlist=1024 trên 2.624 vector + filter type=="video" với nprobe=16 trả
    0 hit. Trả list rỗng thì client nhận HTTP 200 kèm danh sách trống, không lỗi nào để lần ra.
    Phải trả None để caller rơi về stub và log."""
    services = _patch(monkeypatch, _FakeCollection([]))
    assert services._reco_from_milvus("usr_1", 5) is None


def test_reco_unknown_user_is_cold_start_not_error(monkeypatch):
    services = _patch(monkeypatch, _FakeCollection([_FakeHit("vid_1", 0.5)], has_user=False))
    assert services._reco_from_milvus("usr_moi", 5) is None


def test_reco_uses_nprobe_large_enough_for_nlist_1024(monkeypatch):
    """nprobe=16 đo được là ra 0 kết quả trên dữ liệu thật; khoá mức tối thiểu để không tụt lại."""
    col = _FakeCollection([_FakeHit("vid_1", 0.5)])
    services = _patch(monkeypatch, col)
    services._reco_from_milvus("usr_1", 1)
    assert col.nprobe >= 64


def test_reco_never_invents_metadata_and_reports_mode(monkeypatch):
    """D18: title/thumbnail come from the product backend by video_id; inference only knows id + score."""
    from app import schemas
    services = _patch(monkeypatch, _FakeCollection([_FakeHit("vid_56", 0.2)]))
    monkeypatch.setattr(services.settings, "force_stub", False)
    out = services.run_recommendation(schemas.RecommendationRequest(user_id="usr_1", limit=1))
    assert out.recommendation_mode == "personalized"
    assert out.recommendations[0].video_id == "vid_56"
    assert out.recommendations[0].title is None and out.recommendations[0].thumbnail_url is None


def test_stub_recommendation_is_labelled_and_has_no_fake_metadata():
    with _client() as c:
        body = c.post("/v1/recommendation/completions", json={"user_id": "usr_888", "limit": 2}, headers=AUTH).json()
    assert body["recommendation_mode"] == "stub"
    assert all(x["title"] is None and x["thumbnail_url"] is None for x in body["recommendations"])
