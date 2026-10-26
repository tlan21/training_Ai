# AI-01 evidence — 2026-10-26 (VERIFIED-NOW)

Máy: Windows 11, CPU (torch 2.13.0+cpu), `.venv` Python 3.11.14. Milvus của stack Codex `127.0.0.1:19530` UP (RE:HC-03).
Server: startup **production** `PYTHONUTF8=1 PYTHONPATH=../ai-core python -m uvicorn app.main:app --port 8011` (`FORCE_STUB=0`, checkpoint canonical).

1. `inference_openapi.json` export từ `app.main:app.openapi()`; export lại sau sửa code → `cmp` giống hệt (schema không đổi).
2. Lần smoke đầu (code cũ, server vừa khởi động): 5 PASS / 1 FAIL — `test_search_needs_milvus`: 503 `AI_UNAVAILABLE`
   `search/siamese/milvus: _InactiveRpcError ... DEADLINE_EXCEEDED`. 3 lần gọi lại ngay sau đó → 200 (121–457 ms).
   Đo ở process mới: `collection()+load` 1884 ms, search #1 474 ms, #2 7 ms, #3 5 ms → query đầu sau load chậm, `visual_index.search` timeout 1 s.
   Sửa: `visual_index.search(..., timeout=1)` nhận tham số; lifespan chạy 1 search warmup `timeout=60` (`app/main.py`).
3. Sau sửa, server khởi động lại (`uvicorn_prod_startup.log`):
   - `live_smoke_real_media.txt`: 6/6 PASS, `INFERENCE_LIVE_MEDIA` = 3 frame + 10 s audio từ `minigpt_domain_v1_20261019/raw/youtube/-1Is0o2ZWk0.mp4` (60–70 s),
     `INFERENCE_EXAMPLES_DIR=coordination/claude/api/examples` → 23 file ví dụ (không chứa key).
   - `live_smoke_synthetic.txt`: 6/6 PASS (ảnh/tone tự sinh, đường mặc định cho release gate).
   - Lần synthetic đầu FAIL vì `/health.degraded=['asr_ctc','highlight_fusion']` — do các request lỗi có chủ đích của lượt trước (file thiếu, lệch chiều).
     `degraded` dính tới khi restart → bỏ điều kiện `degraded` khỏi smoke, ghi ngữ nghĩa vào contract §2.7.
   - `suite_default.txt`: `pytest tests/` không server → 37 passed, 7 skipped (6 live smoke skip + 1 T42).
4. Milvus (chỉ đọc): `video_frame_embeddings` 280 entity, 128-d, HNSW/COSINE/M16/efC200 khớp contract; `user_recommendation_embeddings` **không tồn tại**
   → recommendation luôn 503 → giữ `DRAFT`.
