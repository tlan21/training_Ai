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


def _fake_index(monkeypatch):
    """Fake MinIO + Milvus collection; returns the recorded writes."""
    import sys
    import types
    writes = {"objects": {}, "rows": [], "deleted": []}

    class Minio:
        def __init__(self, *args, **kwargs):
            pass

        def bucket_exists(self, name):
            return True

        def put_object(self, bucket, key, data, length, content_type):
            writes["objects"][f"{bucket}/{key}"] = data.read()

    class Collection:
        def delete(self, expr, timeout):
            writes["deleted"].append(expr)

        def insert(self, rows, timeout):
            writes["rows"].extend(rows[1])

    monkeypatch.setitem(sys.modules, "minio", types.SimpleNamespace(Minio=Minio))
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "k")
    monkeypatch.setenv("MINIO_SECRET_KEY", "s")
    monkeypatch.setattr(visual_index, "collection", lambda: Collection())
    monkeypatch.setattr(visual_index, "encode", lambda images: [[0.1] * 128 for _ in images])
    return writes


def test_data_uri_frames_with_video_id_index_one_per_second(monkeypatch):
    """HO-01: Docker gateway sends data URIs + video_id; request order = second 0, 1, 2…"""
    writes = _fake_index(monkeypatch)
    frames = ["data:image/png;base64," + query_image(), query_image(), "data:image/png;base64," + query_image()]
    assert visual_index.index_frames(frames, video_id="vid_abc") == 3
    assert [r["timestamp"] for r in writes["rows"]] == [0.0, 1.0, 2.0]
    assert [r["thumbnail_url"] for r in writes["rows"]] == [f"thumbnails/vid_abc/{i:08d}.jpg" for i in range(3)]
    assert set(writes["objects"]) == {f"thumbnails/vid_abc/{i:08d}.jpg" for i in range(3)}
    assert writes["objects"]["thumbnails/vid_abc/00000001.jpg"] == base64.b64decode(query_image())
    assert writes["deleted"] == ['payload["video_id"] == "vid_abc"']


def test_data_uri_without_video_id_is_not_indexed(monkeypatch):
    writes = _fake_index(monkeypatch)
    assert visual_index.index_frames(["data:image/png;base64," + query_image()]) == 0
    assert writes["rows"] == [] and writes["objects"] == {}


def test_invalid_video_id_is_rejected_before_writes(monkeypatch):
    writes = _fake_index(monkeypatch)
    with pytest.raises(ValueError):
        visual_index.index_frames([query_image()], video_id="../etc")
    assert writes["rows"] == [] and writes["deleted"] == []


def test_vision_passes_video_id_and_bad_id_is_not_model_failure(monkeypatch):
    monkeypatch.setattr(services.settings, "force_stub", False)
    monkeypatch.setattr(services.registry, "degraded", set())
    seen = {}

    class ViT:
        def __call__(self, imgs, return_embedding):
            return torch.zeros(len(imgs), 4), torch.zeros(len(imgs), 256)
    monkeypatch.setattr(services.registry, "models", {"vit": ViT()})
    monkeypatch.setattr(services.registry, "vit_classes", ["bong_da", "the_thao", "ca_nhac", "tin_tuc"])

    def index(refs, video_id=None):
        seen["video_id"] = video_id
        if video_id != "vid_ok":
            raise ValueError("Invalid video_id")
        return len(refs)
    monkeypatch.setattr(visual_index, "index_frames", index)
    out = services.run_vision(schemas.VisionRequest(keyframes=[query_image()], video_id="vid_ok"))
    assert seen["video_id"] == "vid_ok" and len(out.embeddings_256) == 1
    with pytest.raises(HTTPException) as exc:
        services.run_vision(schemas.VisionRequest(keyframes=[query_image()], video_id="bad id"))
    assert exc.value.status_code == 503 and services.registry.degraded == set()
