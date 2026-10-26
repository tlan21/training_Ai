# AI API Contract — inference-service :8001

**Version: AI-API v0.1 — DRAFT (2026-10-26).** Owner: Claude. Codex chỉ đọc
(`git show claude/ai-core:coordination/claude/api/AI_API_CONTRACT.md`, hoặc bản trên `master` sau release).
Nguồn code: `inference-service/app/schemas.py`, `app/main.py`, `app/services.py` tại baseline `15976b3`.
v1.0 (`API_READY`) phát hành ở task AI-01 kèm `inference_openapi.json` + `examples/` sinh từ chạy thật.

## 0. Quy ước chung

- Base URL nội bộ: `http://inference:8001` (compose) / `http://127.0.0.1:8001` (local). Không public ra internet.
- Auth: mọi `/v1/*` cần header `Authorization: Bearer ${AI_SERVICE_KEY}` (format `sk-local-...`, env cả inference lẫn gateway).
  `/health` không cần key.
- Error envelope (mọi lỗi): `{"error": {"code": "<CODE>", "message": "<text>"}}`

| HTTP | code | Khi nào |
|---|---|---|
| 401 | `UNAUTHORIZED` | thiếu/sai Bearer key |
| 422 | `VALIDATION_ERROR` | body sai schema; ảnh không phải JPEG/PNG/WebP hoặc >20 MP |
| 503 | `AI_UNAVAILABLE` | model/real path lỗi (không bao giờ trả stub lặng lẽ khi `FORCE_STUB=0`); Milvus không kết nối |
| 4xx/5xx khác | `HTTP_ERROR` | lỗi HTTP chung |

- Khởi động: lifespan bắt buộc đủ 6 checkpoint (nếu `FORCE_STUB=0`) và kết nối Milvus visual index, nếu không → process fail (không chạy nửa vời).
- GPU queue: vision, asr, highlight, completions chạy tuần tự qua 1 hàng đợi; search, recommendation chạy trực tiếp (encode nhẹ + Milvus).
- Thang điểm: highlight 0–100; similarity/score/confidence 0–1.
- Mock cho Codex: `FORCE_STUB=1` → mọi endpoint trả dữ liệu giả đúng schema, `/health.stub_mode=true`. Go: `mocks.AIClientMem`.

## 1. Model & checkpoint (active tại v0)

| Model key (`/health.models_loaded`) | Endpoint | `model` mặc định | SHA256 `best.pt` |
|---|---|---|---|
| `vit` | `/v1/vision/completions` | `primitive-vit-classifier` | `192d90e4fad893cec1542c5630715cc3bc22197e8cd8ba22a6fb84a64a88ad7f` |
| `siamese` | `/v1/search/completions` (+ index frame) | `primitive-siamese-vit` | `b4ded465b8eea134a01652811008656b9e0c59716431136bb161216310bbcebb` |
| `asr_ctc` | `/v1/asr/completions` | `primitive-asr-transformer` | `8f87986781cfb3d4716691f2051e5798187693e2452f9f41b28ca4a753ea5531` |
| `highlight_fusion` | `/v1/highlight/completions` | `primitive-seq2seq-highlighter` | `becbd378ca237c6992867ca5309663d3c1c142a99b40da57f9a0fb652489b49c` |
| `minigpt` | `/v1/completions` | `primitive-gpt-summarizer` | `cf9cfa7141d40f9d40b0065ae68855ff39ffe750260ee7b42c7c0eac719330ac` |
| `two_tower` | `/v1/recommendation/completions` | `primitive-two-tower-recommender` | `f28c37943ec499d168f43b5281879273af326a97ee47e571100c93dee0c91695` |

## 1b. Thang sẵn sàng từng model (cập nhật trong AI-06/AI-01)

Mức: `DECLARED` → `CKPT_PRESENT` → `LOADED` → `ENDPOINT_OK` (HTTP thật) → `API_READY`. Chỉ ghi mức có bằng chứng.
Bằng chứng hiện có: AI-00, 2026-10-26, nguồn `E:/traning_ai/ai-core/checkpoints`, gọi `app.services` trực tiếp (**chưa qua HTTP**).

| Model | DECLARED | CKPT_PRESENT | LOADED | ENDPOINT_OK | API_READY | Ghi chú |
|---|---|---|---|---|---|---|
| vit | ✓ | ✓ (E:) · ✗ (D:) | ✓ | — (service call OK) | ✗ | thiếu ở `D:/data_training_ai/checkpoints` → AI-06 |
| minigpt | ✓ | ✓ (E:) · ✗ (D:) | ✓ | — (service call OK) | ✗ | thiếu ở D: → AI-06 |
| siamese | ✓ | ✓ (E:, D: chưa so SHA) | ✓ | — (503 khi Milvus tắt) | ✗ | cần Milvus |
| asr_ctc | ✓ | ✓ (E:, D: chưa so SHA) | ✓ | — (service call OK) | ✗ | |
| highlight_fusion | ✓ | ✓ (E:, D: chưa so SHA) | ✓ | — (service call OK, 256-d) | ✗ | |
| two_tower | ✓ | ✓ (E:, D: chưa so SHA) | ✓ | — (503 khi Milvus tắt) | ✗ | cần Milvus |

## 1c. Runtime :8001 (quyết định user 2026-10-26)

- Claude sở hữu tiến trình inference-service chạy checkpoint thật (task AI-07). Codex **không** sao chép, mount hay quản lý checkpoint;
  chỉ gọi HTTP `:8001` với Bearer key.
- Khi :8001 chưa sẵn sàng (DOWN hoặc endpoint chưa `API_READY`), Codex phát triển bằng mock đúng contract này
  (`mocks.AIClientMem` hoặc stub HTTP trả đúng schema mục 2). Mock không bao giờ được tính là tích hợp thật.
- Lệnh chạy, địa chỉ host cho gateway trong Docker, và trạng thái UP/DOWN sẽ ghi tại đây trong AI-07.

## 2. Endpoints

Trạng thái: `DRAFT` = schema ổn định theo code hiện tại nhưng chưa có ví dụ thật đóng gói; Codex được dùng, chưa được đánh `INTEGRATED_REAL` mới.

### 2.1 `POST /v1/vision/completions` — ViT (chỉ nội bộ pipeline) — DRAFT
Req: `{"model"?: str, "keyframes": [str]}` — mỗi phần tử là path file mà inference đọc được, data URI base64, hoặc base64 trần.
Resp: `{"id","object":"vision_completion","created","model","category_suggestion": str,"embeddings_256": [[float×256]]}`
- `category_suggestion` ∈ `bong_da | the_thao | ca_nhac | tin_tuc` (ViT MVP 4 lớp). 6 danh mục còn lại của Postgres không có gợi ý.
- `embeddings_256`: 1 vector/keyframe, dùng làm `vision_embeddings` cho highlight.
- Xác minh 2026-10-26 (CPU, service call): 3 frame → 524 ms, 256-d.

### 2.2 `POST /v1/asr/completions` — ASR CTC — DRAFT
Req: `{"model"?: str, "audio_url": str, "language": "vi"}` — `audio_url` = path WAV cục bộ hoặc `http(s)://` (MinIO nội bộ). Audio 16 kHz mono.
Resp: `{"id","object":"asr_completion","created","model","full_transcript": str,"segments":[{"id":int,"start_time":float,"end_time":float,"text":str,"confidence":0–1,"warning": null|"low_confidence"|"blacklist"}]}`
- Audio xử lý theo cửa sổ 20 s, timestamp tuyệt đối; đoạn im lặng bị bỏ.
- Chất lượng: VIVOS CER 0.1347; video thật còn nhiều lỗi (AI-02).

### 2.3 `POST /v1/highlight/completions` — Fusion — DRAFT
Req: `{"model"?: str, "video_id": str, "features": {"vision_embeddings": [[float×256]], "audio_spectrogram_features": [[float×64]]}}`
- **Ràng buộc:** 2 mảng **cùng số phần tử** (1 phần tử = 1 giây); vision 256-d (đầu ra 2.1), audio 64-d (ingest-worker). Sai → 503 `AI_UNAVAILABLE`.
Resp: `{"id","object":"highlight_completion","created","model","video_id","timeline_scores":[{"second":int,"score":0–100}],"recommended_clips":[{"clip_id","start_time","end_time","average_score":0–100}]}`
- `second` bắt đầu từ 0; clip đề xuất = đoạn liên tiếp có score > 75.

### 2.4 `POST /v1/search/completions` — Siamese + Milvus — DRAFT
Req: `{"model"?: str, "image": str (data URI/base64/path), "top_k": 1–100 (mặc định 5), "threshold": 0–1 (mặc định 0.75)}`
Resp: `{"id","object":"search_completion","created","model","results":[{"video_id","timestamp":float,"similarity_score":0–1,"thumbnail_url"}],"query_metadata":{}}`
- Cần Milvus collection frame (COSINE/HNSW). Milvus tắt → 503. Gateway tự lọc processed/published + `min_similarity`.

### 2.5 `POST /v1/recommendation/completions` — Two-Tower + Milvus — DRAFT
Req: `{"model"?: str, "user_id": str, "limit": int (mặc định 10), "context": {}}`
Resp: `{"id","object":"recommendation_completion","created","model","recommendations":[{"video_id","score":0–1,"title","thumbnail_url"}]}`
- Milvus không sẵn sàng → 503, gateway dùng popularity fallback. User chưa có vector → cold-start (không lỗi).

### 2.6 `POST /v1/completions` — Mini-GPT (OpenAI-style) — DRAFT
Req: `{"model"?: str, "prompt": str, "max_tokens": ≥1 (mặc định 150), "temperature": 0–2 (mặc định 0.7), "top_p": 0.9, "frequency_penalty": 0, "presence_penalty": 0}`
Resp: `{"id","object":"text_completion","created","model","choices":[{"text","index":0,"logprobs":null,"finish_reason":"stop"}],"usage":{"prompt_tokens","completion_tokens","total_tokens"}}`
- Prompt dài: service tự map-reduce theo chunk BPE (không giới hạn phía gateway).
- Chất lượng: tóm tắt video thật còn bịa/lặp (human 1.6/5, AI-03). Chỉ dùng làm **draft** để admin duyệt.

### 2.7 `GET /health`
Resp: `{"status":"ok","gpu_vram_used": MB,"gpu_util": %,"models_loaded":[...],"degraded":[...],"queue_depth":int,"device":"cpu|cuda","stub_mode":bool,"load_error": str|null}`
- Integration test thật phải assert `stub_mode == false` và `models_loaded` đủ 6 key ở mục 1.

## 3. Changelog
- **v0 (2026-10-26)** — DRAFT, ghi lại API hiện có tại baseline `15976b3`. Không đổi code.
- **v0.1 (2026-10-26)** — DRAFT, chỉ tài liệu: thêm thang sẵn sàng (1b) và quyền runtime :8001 thuộc Claude, Codex chỉ HTTP/mock (1c). Schema không đổi.
