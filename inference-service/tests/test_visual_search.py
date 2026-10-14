import base64
import io

from fastapi import HTTPException
from PIL import Image
import pytest
import torch

from app import schemas, services, visual_index


def query_image():
    data = io.BytesIO()
    Image.new("RGB", (16, 16), "red").save(data, format="PNG")
    return base64.b64encode(data.getvalue()).decode()


def test_siamese_search_has_real_metadata_and_no_stub(monkeypatch):
    monkeypatch.setattr(services.settings, "force_stub", False)
    monkeypatch.setattr(visual_index, "encode", lambda images: [[0.1]*128])
    def search(vector, top_k, threshold):
        assert len(vector) == 128 and top_k == 5 and threshold == .75
        return [{"video_id": "vid_real", "timestamp": 3, "similarity_score": .91,
                 "thumbnail_url": "thumbnails/vid_real/00000003.jpg"}]
    monkeypatch.setattr(visual_index, "search", search)
    result = services.run_search(schemas.SearchRequest(image=query_image()))
    assert result.results[0].video_id == "vid_real"
    assert "total_candidates_searched" not in result.query_metadata
    def fail(*args):
        raise RuntimeError("Milvus unavailable")
    monkeypatch.setattr(visual_index, "search", fail)
    with pytest.raises(HTTPException) as exc:
        services.run_search(schemas.SearchRequest(image=query_image()))
    assert exc.value.status_code == 503


def test_bad_image_is_validation_error(monkeypatch):
    monkeypatch.setattr(services.settings, "force_stub", False)
    with pytest.raises(HTTPException) as exc:
        services.run_search(schemas.SearchRequest(image="bm90IGFuIGltYWdl"))
    assert exc.value.status_code == 422


def test_encode_is_batched_finite_128d_and_inference_only(monkeypatch):
    class Siamese:
        def encode(self, batch):
            assert not torch.is_grad_enabled()
            assert batch.shape == (2, 3, 224, 224)
            return torch.ones(2, 128) / 128**.5
    monkeypatch.setattr(visual_index.registry, "models", {"siamese": Siamese()})
    rows = visual_index.encode([torch.zeros(3,224,224)]*2)
    assert len(rows) == 2 and len(rows[0]) == 128
    assert sum(x*x for x in rows[0]) == pytest.approx(1)


def test_milvus_uses_cosine_hnsw_ef_and_threshold(monkeypatch):
    class Entity:
        def get(self, name):
            assert name == "payload"
            return {"video_id":"vid_real","timestamp":2,"thumbnail_url":"thumbnails/v/2.jpg"}
    class Hit:
        entity = Entity()
        def __init__(self, distance):
            self.distance = distance
    class Collection:
        def search(self, data, field, param, **kwargs):
            assert field == "vector" and len(data[0]) == 128
            assert param == {"metric_type":"COSINE","params":{"ef":100}}
            assert kwargs["consistency_level"] == "Session" and kwargs["timeout"] == 1
            return [[Hit(1.0000001),Hit(.7),Hit(-.2)]]
    monkeypatch.setattr(visual_index,"collection",lambda:Collection())
    result = visual_index.search([.1]*128,100,.75)
    assert len(result) == 1 and result[0]["similarity_score"] == 1
    assert visual_index.INDEX["params"] == {"M":16,"efConstruction":200}
