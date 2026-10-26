# AI-11 evidence — 2026-10-26 (VERIFIED-NOW)

HO-01 (Codex RE:HC-05 chọn phương án b): Vision nhận `video_id` optional, index frame từ data URI theo 1 fps.

- RED: `tests/test_visual_search.py` 2 failed (index data URI; vision không truyền video_id) → GREEN sau sửa `app/visual_index.py`, `app/schemas.py`,
  `app/services.py`. Suite `pytest tests/` 51 passed, 7 skipped.
- Unit: data URI + video_id → giây 0/1/2, key `thumbnails/vid_abc/0000000N.jpg`, bytes thumbnail = ảnh gốc, delete theo video_id trước insert;
  không video_id → 0, không ghi; video_id `../etc` → ValueError trước mọi ghi; vision truyền video_id, id sai → 503 không degraded.
- Live :8001 (restart với code mới + `MINIO_*` default compose trong `.env` local) — `probe_result.json`:
  vision 200 `tin_tuc`, 3 row Milvus giây [0,1,2], 3 thumbnail; search frame 2 → `vid_ai11probe` giây 1 similarity 1.0;
  ASR presigned `localhost:9000` → 200, 5 segment; sau dọn: 0 row Milvus, 0 thumbnail, WAV probe đã xóa.
- Regression smoke :8001: 6 passed. OpenAPI diff: chỉ thêm `VisionRequest.video_id` (string|null).
