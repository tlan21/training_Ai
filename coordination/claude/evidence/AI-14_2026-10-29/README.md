# AI-14 evidence — D24 bước 1: facade/worker trong inference-service (2026-10-29)

VERIFIED-NOW 2026-10-29, máy local Windows, CPU, 6 checkpoint active (SHA contract §1). Không file nào chứa key.

| Kiểm | Kết quả | File |
|---|---|---|
| inference suite (`pytest inference-service/tests`, gồm `test_contract_compat.py`) | 63 passed / 7 skipped (baseline trước sửa 55/7; +8 test worker; skip = live smoke + Milvus integration như cũ) | `inference_suite.log` |
| ai-core suite (`pytest ai-core/ai_core/tests`) | 314 passed (không đổi code ai-core) | — (output phiên) |
| unit worker không Milvus/MinIO | `tests/test_worker.py`: import worker/worker_app/worker_client không kéo `minio`/`pymilvus`; ops nhận bytes/vector; worker HTTP thật (uvicorn) trả trùng in-process; 422/500/401/unreachable giữ ngữ nghĩa | `inference_suite.log` |
| OpenAPI | `app.openapi()` == `coordination/claude/api/inference_openapi.json` (v1.3) → True | — |
| smoke :8001 worker in-process (PID 16512) | 6/6 PASS (gồm 401 thiếu Bearer); thêm curl search không Bearer → 401 | `smoke_inprocess_8001.log` |
| so với examples đã công bố (cùng media AI-01) | mọi file SAME trừ `search.response` — chỉ khác vì Milvus có thêm `vid_ai11probe` (index AI-11 sau khi ghi example); điểm các hit cũ trùng từng bit | `compare_published_vs_inprocess.txt` |
| smoke worker từ xa: worker `app.worker_app` :8002 (PID 24304, 6 ckpt thật) + facade :8001 `MODEL_WORKER_URL` (PID 632), key ngẫu nhiên chỉ qua env | 6/6 PASS; facade không Bearer 401; worker không key / key `sk-local-dev-key` → 401 | `smoke_remote_worker.log` |
| in-process vs remote | mọi response SAME; `health` chỉ thêm `dependencies.model_worker: "ok"` | `compare_inprocess_vs_remote.txt` |
| worker chết | highlight → 503 `AI_UNAVAILABLE` (DependencyError), `/health` `model_worker: unavailable`, `degraded: []` | `worker_down.log` |
| :8001 khôi phục in-process (PID 16292) | 6/6 PASS | `smoke_8001_restored_inprocess.log` |
| kernel Kaggle dry-run local (CPU, `--no-tunnel`) | dataset build kiểm SHA từ contract §1; kernel kiểm manifest, nạp đủ 6 ckpt, `/info` qua key; `session.json` không key | `kernel_dryrun.log` |

Chưa làm: push dataset/kernel lên Kaggle + smoke qua tunnel (push = bắt đầu phiên GPU tốn quota; chờ user quyết).
