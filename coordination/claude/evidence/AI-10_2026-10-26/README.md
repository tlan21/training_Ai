# AI-10 evidence — 2026-10-26 (VERIFIED-NOW)

D15: degraded chỉ khi inference lỗi thật; input sai không tính; dependency có trạng thái riêng; tự phục hồi; tương thích contract.

- RED trước khi sửa: `tests/test_health_status.py` 9/9 ERROR (chưa có `registry.dependencies`, `_dep_checked`, `refresh_dependencies`).
- GREEN `test_health_status.txt`: 9/9 PASS — validation error (highlight lệch số giây / rỗng / vision 255-d / audio 63-d; ảnh hỏng; WAV không tồn tại)
  → 503 nhưng `degraded` rỗng; model failure → degraded rồi tự gỡ khi chạy lại được; Milvus search lỗi → `dependencies.visual_index=unavailable`,
  siamese không degraded, tự về `ok`; recommendation `missing_collection` → giữ trong cửa sổ 30 s → `ok` khi collection có → `unavailable` khi Milvus sập;
  `/health` trả `dependencies`.
- `suite_default.txt`: `pytest tests/` 46 passed, 7 skipped.
- Live (uvicorn startup production :8011, Milvus thật, media thật): `live_smoke_run1.txt`, `live_smoke_run2.txt` — 2 lượt liên tiếp 6/6 PASS
  (trước AI-10 lượt 2 FAIL vì degraded dính). `/health` sau 2 lượt: `degraded=[]`,
  `dependencies={"recommendation_index":"missing_collection","visual_index":"ok"}`.
- OpenAPI export lại: diff duy nhất là field `HealthResponse.dependencies` (object<string,string>, default `{}`).
