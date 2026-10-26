"""Siamese frame index, database_schema §4.1; ViT/Fusion features stay 256d."""
import base64
import io
import json
import os
from pathlib import Path
import re
from threading import Lock

from .config import settings
from .registry import registry

COLLECTION = "video_frame_embeddings"
INDEX = {"index_type": "HNSW", "metric_type": "COSINE",
         "params": {"M": 16, "efConstruction": 200}}
_collection = None
_lock = Lock()


def collection():
    global _collection
    from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility
    with _lock:
        if _collection is not None:
            return _collection
        connections.connect(alias="visual", host=settings.milvus_host,
                            port=settings.milvus_port, timeout=5)
        if not utility.has_collection(COLLECTION, using="visual", timeout=5):
            schema = CollectionSchema([
                FieldSchema("id", DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema("vector", DataType.FLOAT_VECTOR, dim=128),
                FieldSchema("payload", DataType.JSON),
            ])
            col = Collection(COLLECTION, schema, using="visual", consistency_level="Strong")
        else:
            col = Collection(COLLECTION, using="visual")
        fields = {field.name: field for field in col.schema.fields}
        if int(fields["vector"].params.get("dim", 0)) != 128:
            raise RuntimeError("video_frame_embeddings must contain Siamese 128d vectors")
        if not col.indexes:
            col.create_index("vector", INDEX, timeout=60)
        else:
            params = col.indexes[0].params
            if params.get("index_type") != "HNSW" or params.get("metric_type") != "COSINE" or any(
                    int(params.get("params", {}).get(key, 0)) != value for key, value in INDEX["params"].items()):
                raise RuntimeError(f"Unexpected visual index: {params}; expected {INDEX}")
        col.load(timeout=60)
        _collection = col
        return col


def encode(images):
    import torch
    if not registry.is_real("siamese"):
        raise RuntimeError("Siamese checkpoint is not loaded")
    with torch.inference_mode():
        batch = torch.stack(images).to(device=registry.device, dtype=registry.model_dtype)
        vectors = registry.models["siamese"].encode(batch).float().cpu()
    if vectors.shape[1] != 128 or not torch.isfinite(vectors).all():
        raise ValueError("Invalid Siamese embeddings")
    return vectors.tolist()


def _image_bytes(ref):
    if ref.startswith("data:"):
        return base64.b64decode(ref.split(",", 1)[1])
    if os.path.exists(ref):
        return Path(ref).read_bytes()
    return base64.b64decode(ref)


def index_frames(paths, video_id=None):
    """Index one video's Siamese frames. Ingest/backfill files: seconds from `NNNNNNNN.jpg` names.
    HO-01: data URI/base64 keyframes + explicit video_id → request order is second 0, 1, 2… (1 fps)."""
    from minio import Minio
    from .services import _load_keyframe
    if not paths:
        raise ValueError("No keyframes to index")
    if all(os.path.exists(ref) for ref in paths):
        frames = [Path(ref) for ref in paths]
        if video_id is None and not all(p.parent.parent == Path("/srv/work") for p in frames):
            return 0  # Files outside ingest scratch have no video identity.
        video_id = video_id or frames[0].parent.name
        if not all(p.parent == frames[0].parent and re.fullmatch(r"\d{8}\.jpg", p.name) for p in frames):
            raise ValueError("Invalid ingest keyframe paths")
        seconds = [int(p.stem) for p in frames]
    elif video_id is None:
        return 0  # Direct base64 Vision calls without video_id have no video identity.
    else:
        seconds = list(range(len(paths)))
    if not re.fullmatch(r"vid_[A-Za-z0-9_]{1,46}", video_id):
        raise ValueError("Invalid video_id")
    storage = Minio(os.environ["MINIO_ENDPOINT"], access_key=os.environ["MINIO_ACCESS_KEY"],
                    secret_key=os.environ["MINIO_SECRET_KEY"], secure=False)
    if not storage.bucket_exists("thumbnails"):
        storage.make_bucket("thumbnails")
    col = collection()
    # Auto-ID schema: replace one video's frames before retry/backfill, never duplicate them.
    col.delete(f'payload["video_id"] == {json.dumps(video_id)}', timeout=5)
    for start in range(0, len(paths), 16):
        batch = list(zip(paths[start:start+16], seconds[start:start+16]))
        vectors = encode([_load_keyframe(str(ref)) for ref, _ in batch])
        payloads = []
        for ref, second in batch:
            data = _image_bytes(str(ref))
            key = f"{video_id}/{second:08d}.jpg"
            storage.put_object("thumbnails", key, io.BytesIO(data), len(data), content_type="image/jpeg")
            payloads.append({"video_id": video_id, "timestamp": float(second),
                             "thumbnail_url": f"thumbnails/{key}"})
        col.insert([vectors, payloads], timeout=10)
    return len(paths)


def search(vector, top_k, threshold, ef=64, timeout=1):
    # Same client indexes new uploads; Session reads its writes without the Strong time-tick wait.
    # Gateway rechecks publication/deletion in PostgreSQL even when a remote delete is not visible yet.
    hits = collection().search([vector], "vector",
        {"metric_type": "COSINE", "params": {"ef": max(ef, top_k)}},
        limit=top_k, output_fields=["payload"], consistency_level="Session", timeout=timeout)[0]
    return [{**hit.entity.get("payload"), "similarity_score": min(1.0, max(0.0, float(hit.distance)))}
            for hit in hits if hit.distance >= threshold]
