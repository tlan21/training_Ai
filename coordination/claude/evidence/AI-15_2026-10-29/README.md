# AI-15 evidence — D24 bước 2 phía AI: AI-API v2.0 DRAFT (2026-10-29)

VERIFIED-NOW 2026-10-29, local Windows CPU, 6 checkpoint active (SHA contract §1). Không file nào chứa key.

| Kiểm | Kết quả | File |
|---|---|---|
| inference suite | 71 passed / 10 skipped (AI-14 63/7; +6 `test_v2.py`; compat giờ 4 = v1.2 + v1.3; skip = 9 live smoke + 1 Milvus integration) | `inference_suite.log` |
| v2 không chạm dữ liệu | `test_v2.py::real_no_storage`: `visual_index.collection/index_frames/search`, `_milvus_collection` ném lỗi, `minio`/`pymilvus` bị chặn import — vision/search/asr/reco v2 vẫn chạy | — |
| ASR chia đoạn | 50 s một lần == 40 s + 10 s (`offset_seconds=40`) | `test_v2.py` |
| OpenAPI | `inference_openapi.json` chỉ thêm (596+, 0−); `/v1` trùng snapshot `inference_openapi_v1.3.json` | git diff |
| smoke live :8001 (PID 15852, code AI-15) | 9/9 PASS: v1 6/6 (+401) và v2 3/3 — v2 vision trùng v1 (category + embeddings_256), vector search = siamese frame 0 (<1e-5), transcript v2 bytes = v1 path, reco v2 503 `MODEL_NOT_READY` | `smoke_v1_v2_8001.log` |
| examples v1 sau khi thêm v2 | SAME trừ `search.response` (Milvus có thêm vid_ai11probe, như AI-14) | `compare_v1_examples_after_v2.txt` |
| Milvus đo cho HC-13 | `video_frame_embeddings`: 411 vector sống / 49 video, `num_entities` 447; schema `id` auto + `vector` 128 + `payload` JSON; HNSW M16/efC200 COSINE | contract v2 §6.1 |
| ai-core | 314 passed (AI-14, cùng phiên; AI-15 không sửa ai-core) | — |
