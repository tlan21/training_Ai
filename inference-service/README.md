# inference-service

1 process FastAPI (port **8001**, nội bộ) nạp cả 6 model AI tự train, phục vụ 6 endpoint + `/health`. Sản phẩm bàn giao của Phase AI (T1.8, master plan §0 AI-GATE). Backend gọi qua REST; hệ thống **không gọi AI ngoài**.

## Chế độ chạy

- **STUB** (mặc định khi chưa có checkpoint hoặc `FORCE_STUB=1`): mọi endpoint trả đúng schema với dữ liệu mock → backend/UI code song song. `/health.load_error` giải thích vì sao chưa load đủ model.
- **THẬT**: đặt `CHECKPOINT_DIR` trỏ `ai-core/checkpoints/`; `/health` báo `models_loaded` và `stub_mode`. `stub_mode` vẫn là `true` nếu thiếu bất kỳ checkpoint nào, nên AI-GATE không thể mở với model thiếu.

## Env

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `AI_SERVICE_KEY` | `sk-local-dev-key` | Bearer key (format `sk-local-...`), khớp gateway |
| `CHECKPOINT_DIR` | `../ai-core/checkpoints` | thư mục best.pt 6 model |
| `INFER_DEVICE` | `auto` | `auto\|cpu\|cuda` |
| `FORCE_STUB` | `0` | `1` ép stub kể cả có checkpoint |

## Cấu hình .env

Copy `.env.example` → `.env` (không commit, đã gitignore). `app/config.py` tự nạp `.env`
(biến env thật ưu tiên hơn `.env`). Không có `.env` → dùng default trong `config.py`.

```bash
cp .env.example .env
python -m app.gen_key          # sinh AI_SERVICE_KEY mới (sk-local-...), dán vào .env
```

| Biến | Default | Ý nghĩa |
|---|---|---|
| `AI_SERVICE_KEY` | `sk-local-dev-key` | Bearer key nội bộ, phải trùng ở gateway |
| `CHECKPOINT_DIR` | `../ai-core/checkpoints` | thư mục best.pt 6 model; thiếu → STUB |
| `INFER_DEVICE` | `auto` | `auto\|cpu\|cuda` |
| `FORCE_STUB` | `0` | `1` ép stub kể cả có checkpoint |

## Chạy

```bash
# dev (stub, không cần GPU/checkpoint)
FORCE_STUB=1 ../.venv/Scripts/python.exe -m uvicorn app.main:app --port 8001
# thật: đặt CHECKPOINT_DIR trỏ checkpoints, INFER_DEVICE=cuda, FORCE_STUB=0
# test
../.venv/Scripts/python.exe -m pytest tests/ -q
```

Validate all six reloadable checkpoints before starting the service:

```bash
cd ../ai-core
../.venv/Scripts/python.exe -m ai_core.scripts.validate_artifacts --checkpoints checkpoints
```

## Auth token

`AI_SERVICE_KEY` là **shared secret** (format `sk-local-...`), KHÔNG phải JWT, không hết hạn.
Sinh bằng `python -m app.gen_key`. Đặt CÙNG giá trị ở env của inference-service và gateway.
Gateway (và mọi caller nội bộ) gửi header `Authorization: Bearer ${AI_SERVICE_KEY}` mỗi request.
Đổi key = revoke tức thì: request với key cũ trả 401. (JWT của người dùng cuối là lớp riêng ở
gateway Go — Phase 2, không liên quan key này.)

```bash
# gọi thử (stub)
curl -s http://127.0.0.1:8001/health
curl -s -X POST http://127.0.0.1:8001/v1/completions \
  -H "Authorization: Bearer sk-local-dev-key" -H "Content-Type: application/json" \
  -d '{"prompt":"Tóm tắt trận đấu...","max_tokens":20}'
```

## Endpoint (master plan §2.4, schema architecture §2)

| Path | Model | Ghi chú |
|---|---|---|
| `POST /v1/completions` | Mini-GPT | OpenAI-style; map-reduce transcript >1024 token |
| `POST /v1/search/completions` | Siamese | ảnh → top-k (0–1) |
| `POST /v1/highlight/completions` | Fusion | timeline_scores **0–100** |
| `POST /v1/asr/completions` | ASR CTC | transcript + segments + confidence |
| `POST /v1/recommendation/completions` | Two-Tower | user → ranked (0–1) |
| `POST /v1/vision/completions` | ViT | **nội bộ** ingest, không expose qua gateway |
| `GET /health` | — | gpu_vram_used, gpu_util, models_loaded, queue_depth |

Mọi POST cần `Authorization: Bearer ${AI_SERVICE_KEY}`. Job GPU (vision/asr/highlight/completions) qua **hàng đợi asyncio tuần tự 1 worker** (không tranh VRAM). Error envelope `{"error":{"code","message"}}`.
