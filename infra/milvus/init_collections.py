"""init_collections.py — tạo collection frame Milvus (D24; recommendation chờ AI-12) (database_schema §4). T0.1b.

Chạy sau khi milvus healthy:
    pip install pymilvus
    python infra/milvus/init_collections.py            # host mặc định localhost:19530
    MILVUS_HOST=milvus python infra/milvus/init_collections.py   # trong mạng docker

Idempotent: collection đã tồn tại thì bỏ qua.
"""

import os

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

HOST = os.environ.get("MILVUS_HOST", "localhost")
PORT = os.environ.get("MILVUS_PORT", "19530")
DIM = 128


def _video_frame_embeddings() -> None:
    """Visual Search — Siamese ViT 128d, COSINE, HNSW (M=16, efConstruction=200)."""
    name = "video_frame_embeddings"
    if utility.has_collection(name):
        print(f"[skip] {name} đã tồn tại")
        return
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=DIM),
        FieldSchema(name="payload", dtype=DataType.JSON),
    ]
    col = Collection(name, CollectionSchema(fields, description="Visual Search frame embeddings"))
    col.create_index("vector", {
        "index_type": "HNSW",
        "metric_type": "COSINE",
        "params": {"M": 16, "efConstruction": 200},
    })
    col.load()
    print(f"[ok] tạo + load {name} (JSON payload, HNSW/COSINE)")


def _user_recommendation_embeddings() -> None:
    """Two-Tower — user/video 128d, IP, IVF_FLAT. PK = user_id/video_id (VARCHAR)."""
    name = "user_recommendation_embeddings"
    if utility.has_collection(name):
        print(f"[skip] {name} đã tồn tại")
        return
    fields = [
        FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=50, is_primary=True),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=DIM),
        FieldSchema(name="type", dtype=DataType.VARCHAR, max_length=10),   # 'user' | 'video'
    ]
    col = Collection(name, CollectionSchema(fields, description="Two-Tower recommendation vectors"))
    col.create_index("vector", {
        "index_type": "IVF_FLAT",
        "metric_type": "IP",
        "params": {"nlist": 1024},
    })
    print(f"[ok] tạo {name} (IVF_FLAT/IP)")


def main() -> None:
    connections.connect(alias="default", host=HOST, port=PORT)
    print(f"[milvus] kết nối {HOST}:{PORT}")
    _video_frame_embeddings()
    # D24/AI-12: do not create a recommendation collection before the real v2 checkpoint.
    print("[milvus] init xong:", utility.list_collections())


if __name__ == "__main__":
    main()
