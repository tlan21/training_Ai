# AI API Contract — inference-service :8001

**Version: AI-API v1.2-rc1 — DRAFT (2026-10-26).** Owner: Claude. Codex chỉ đọc
(`git show claude/ai-core:coordination/claude/api/AI_API_CONTRACT.md`, hoặc bản trên `master` sau release).
Nguồn code: `inference-service/app/schemas.py`, `app/main.py`, `app/services.py`, `app/visual_index.py` trên `claude/ai-core` (AI-01).
Đi kèm: `inference_openapi.json` (export `app.main:app.openapi()`, không sửa tay) và `examples/` (request/response/error sinh từ chạy thật, mục 4).

**D16 (user 2026-10-26):** `API_READY` chỉ công bố khi code cần thiết đã trên `master`, runtime :8001 hoạt động và smoke đạt (AI-07 + release).
Tới lúc đó mọi endpoint là `DRAFT`; cột "Ứng viên" = đã có ví dụ thật + smoke PASS trên server tạm :8011. Codex tiếp tục bằng mock.

Trạng thái endpoint: `API_READY` = schema ổn định + ví dụ thật đóng gói + smoke live PASS. `DRAFT` = schema theo code nhưng chưa có ví dụ
thành công thật; Codex được dùng mock, chưa được đánh `INTEGRATED_REAL`. `API_READY` nói về **API**, không phải chất lượng model (ghi riêng từng endpoint).

| Endpoint | Trạng thái v1.0-rc1 | Ứng viên API_READY |
|---|---|---|
| `GET /health` | `DRAFT` | ✓ (v1.1: thêm `dependencies`, chỉ thêm field) |
| `POST /v1/vision/completions` | `DRAFT` | ✓ |
| `POST /v1/asr/completions` | `DRAFT` | ✓ |
| `POST /v1/highlight/completions` | `DRAFT` | ✓ |
| `POST /v1/completions` | `DRAFT` | ✓ |
| `POST /v1/search/completions` | `DRAFT` | ✓ |
| `POST /v1/recommendation/completions` | `DRAFT` | ✗ — Milvus chưa có collection `user_recommendation_embeddings`, luôn 503; personalized chờ D14 (AI-09 + HC-04) |

## 0. Quy ước chung

- Base URL nội bộ: `http://127.0.0.1:8001` trên host (runtime do Claude chạy, AI-07); từ container Docker thường là `http://host.docker.internal:8001`.
  Không public ra internet.
- Auth: mọi `/v1/*` cần header `Authorization: Bearer ${AI_SERVICE_KEY}` (format `sk-local-...`, cùng giá trị ở inference và gateway).
  `/health` không cần key.
- Error envelope (mọi lỗi): `{"error": {"code": "<CODE>", "message": "<text>"}}`. `message` chỉ để log, không parse.

| HTTP | code | Khi nào |
|---|---|---|
| 401 | `UNAUTHORIZED` | thiếu/sai Bearer key |
| 422 | `VALIDATION_ERROR` | body sai schema (thiếu field, `top_k` ngoài 1–100, …); search: ảnh không phải JPEG/PNG/WebP hoặc >20 MP |
| 503 | `AI_UNAVAILABLE` | real path lỗi: vision ảnh hỏng/>20 MP, file audio không đọc được, sai số giây/chiều highlight (input sai — **không** làm model degraded); Milvus lỗi/thiếu collection (dependency); inference lỗi thật (model degraded). Không bao giờ trả stub lặng lẽ khi `FORCE_STUB=0` |
| 4xx/5xx khác | `HTTP_ERROR` | lỗi HTTP chung |

- Khởi động (`FORCE_STUB=0`): lifespan bắt buộc đủ 6 checkpoint, kết nối Milvus `video_frame_embeddings` và chạy 1 search warmup; thiếu bất kỳ → process thoát
  (`Application startup failed`), không chạy nửa vời.
- GPU queue: vision, asr, highlight, completions chạy tuần tự qua 1 hàng đợi; search, recommendation chạy trực tiếp (encode nhẹ + Milvus).
- Thang điểm: highlight 0–100; similarity/score/confidence 0–1.
- Mock cho Codex: `FORCE_STUB=1` → mọi endpoint trả dữ liệu giả đúng schema, `/health.stub_mode=true`. Mock không bao giờ tính là tích hợp thật.

## 1. Model & checkpoint (active tại v1.0)

| Model key (`/health.models_loaded`) | Endpoint | `model` mặc định | SHA256 `best.pt` |
|---|---|---|---|
| `vit` | `/v1/vision/completions` | `primitive-vit-classifier` | `192d90e4fad893cec1542c5630715cc3bc22197e8cd8ba22a6fb84a64a88ad7f` |
| `siamese` | `/v1/search/completions` (+ index frame) | `primitive-siamese-vit` | `b4ded465b8eea134a01652811008656b9e0c59716431136bb161216310bbcebb` |
| `asr_ctc` | `/v1/asr/completions` | `primitive-asr-transformer` | `8f87986781cfb3d4716691f2051e5798187693e2452f9f41b28ca4a753ea5531` |
| `highlight_fusion` | `/v1/highlight/completions` | `primitive-seq2seq-highlighter` | `becbd378ca237c6992867ca5309663d3c1c142a99b40da57f9a0fb652489b49c` |
| `minigpt` | `/v1/completions` | `primitive-gpt-summarizer` | `cf9cfa7141d40f9d40b0065ae68855ff39ffe750260ee7b42c7c0eac719330ac` |
| `two_tower` | `/v1/recommendation/completions` | `primitive-two-tower-recommender` | `f28c37943ec499d168f43b5281879273af326a97ee47e571100c93dee0c91695` |

Nguồn canonical: `E:/traning_ai/ai-core/checkpoints` (AI-06). Claude chỉ thay `best.pt` active khi phát hành AI API version mới.

## 1b. Thang sẵn sàng từng model

Mức: `DECLARED` → `CKPT_PRESENT` → `LOADED` → `ENDPOINT_OK` (HTTP thật) → `API_READY`. Chỉ ghi mức có bằng chứng.

- `DECLARED`: key có trong `inference-service/app/registry.py` `_MODEL_FILES`.
- `CKPT_PRESENT`: `sha256sum` file ở nguồn canonical = SHA mục 1 (AI-06).
- `LOADED`: uvicorn startup complete + `GET /health` → `stub_mode=false`, `models_loaded` đủ 6, `degraded=[]` ngay sau startup.
- `ENDPOINT_OK`: HTTP thật qua uvicorn, Bearer, response validate bằng `app.schemas`; thiếu Bearer → 401.
- `API_READY`: ví dụ thật trong `examples/` + `tests/test_live_smoke.py` PASS.

**AI-07, VERIFIED-NOW 2026-10-26**: runtime thật **:8001** (startup production, `FORCE_STUB=0`, Milvus thật của stack Codex `127.0.0.1:19530`,
không `PYTHONUTF8`), CPU (`device=cpu`, máy không có GPU chạy torch → VRAM ≤4 GB **chưa** kiểm được, AI-04/RTX 3060). `tests/test_live_smoke.py`
media thật 6/6 + synthetic 6/6; `/health` → `stub_mode=false`, 6 model, `degraded=[]`. Bằng chứng: `coordination/claude/evidence/AI-07_2026-10-26/`
(trước đó: AI-01 :8011 `evidence/AI-01_2026-10-26/`, AI-06 launcher không Milvus `evidence/AI-06_2026-10-26/`).

| Model | DECLARED | CKPT_PRESENT | LOADED | ENDPOINT_OK | API_READY | Ghi chú |
|---|---|---|---|---|---|---|
| vit | ✓ | ✓ `192d90e4…` | ✓ | ✓ | ứng viên | |
| asr_ctc | ✓ | ✓ `8f879867…` | ✓ | ✓ | ứng viên | chất lượng video thật kém (transcript nhiễu, AI-02) |
| highlight_fusion | ✓ | ✓ `becbd378…` | ✓ | ✓ | ứng viên | |
| minigpt | ✓ | ✓ `cf9cfa71…` | ✓ | ✓ | ứng viên | chất lượng human 1.6/5 (AI-03), chỉ dùng làm draft cho admin |
| siamese | ✓ | ✓ `b4ded465…` | ✓ | ✓ | ứng viên | Milvus `video_frame_embeddings` 280 vector, HNSW/COSINE/M16/efC200; index qua `video_id` + data URI (AI-11) |
| two_tower | ✓ | ✓ `f28c3794…` | ✓ | ✗ | ✗ | collection `user_recommendation_embeddings` chưa có → 503 |

## 1c. Runtime :8001 (quyết định user 2026-10-26)

- Claude sở hữu tiến trình inference-service chạy checkpoint thật (task AI-07). Codex **không** sao chép, mount hay quản lý checkpoint;
  chỉ gọi HTTP `:8001` với Bearer key.
- Khi :8001 chưa sẵn sàng (DOWN hoặc endpoint chưa `API_READY`), Codex phát triển bằng mock đúng contract này. Mock không bao giờ được tính là tích hợp thật.
- Lệnh chạy chuẩn (Windows host, worktree Claude, tiến trình độc lập): `inference-service/run_local_8001.cmd`
  (`powershell Start-Process cmd.exe -ArgumentList '/c','E:\traning_ai\inference-service\run_local_8001.cmd' -WindowStyle Hidden`),
  tương đương `cd inference-service && PYTHONPATH=../ai-core ../.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8001`.
  Log: `D:/tmp/ai07_runtime/inference_8001.log`. Checkpoint canonical, `AI_SERVICE_KEY` trong `inference-service/.env` (không commit; gateway phải dùng cùng giá trị).
  UTF-8 Windows đã sửa trong code (`app/__init__.py`), không cần `PYTHONUTF8`.
- Từ container Docker: `http://host.docker.internal:8001` — đã kiểm `docker exec video-ai-gateway-1 wget host.docker.internal:8001/health` → 200.
- **Trạng thái: UP từ 2026-10-26 14:47 (PID 26396)**. Máy khởi động lại / tiến trình chết → DOWN; Claude ghi UP/DOWN mới trong `coordination/claude/SESSION.md`.
- HC-05 đã chốt phương án (b) (RE:HC-05): gateway gửi data URI + `video_id` cho vision, URL MinIO presigned `localhost:9000` cho asr; không dùng `/srv/work`.
  Runtime cần `MINIO_ENDPOINT/ACCESS_KEY/SECRET_KEY` trong `inference-service/.env` (local) để index frame — đã đặt theo default compose.

## 2. Endpoints

Ví dụ thật cho mỗi endpoint: `examples/<name>.request.json`, `<name>.response.json`, `<name>.error_request.json`, `<name>.error.json`
(file response/error có dạng `{"http_status": int, "body": <JSON trả về>}`).

### 2.1 `POST /v1/vision/completions` — ViT (chỉ nội bộ pipeline) — DRAFT (ứng viên)
Req: `{"model"?: str, "keyframes": [str], "video_id"?: str}` — mỗi keyframe là data URI base64, base64 trần, hoặc path file mà process inference đọc được.
- `video_id` (v1.2, tùy chọn, HO-01): `vid_*`. Có field này → frame được index cho visual search (Milvus `video_frame_embeddings` + thumbnail MinIO
  `thumbnails/<video_id>/<8 số>.jpg`), keyframe thứ i = giây i (1 fps theo thứ tự request). **Gửi toàn bộ frame của video trong 1 request**: index ghi đè
  frame đã index trước đó của cùng `video_id`. Không có `video_id` + data URI → chỉ phân loại, không index. `video_id` sai định dạng → 503, không làm model degraded.
  Topology host/Docker (RE:HC-05 phương án b): gateway gửi data URI + `video_id`; không dùng path `/srv/work`.
Resp: `{"id","object":"vision_completion","created","model","category_suggestion": str,"embeddings_256": [[float×256]]}`
- `category_suggestion` ∈ `bong_da | the_thao | ca_nhac | tin_tuc` (ViT MVP 4 lớp). 6 danh mục còn lại của Postgres không có gợi ý.
- `embeddings_256`: 1 vector/keyframe, cùng thứ tự; dùng làm `vision_embeddings` cho highlight.
- Lỗi: thiếu `keyframes` → 422; ảnh hỏng/>20 MP → 503. Ví dụ: `examples/vision.*` (3 frame thật → `tin_tuc`, 3×256).

### 2.2 `POST /v1/asr/completions` — ASR CTC — DRAFT (ứng viên)
Req: `{"model"?: str, "audio_url": str, "language": "vi"}` — `audio_url` = path WAV **trên máy chạy inference** hoặc `http(s)://` (MinIO nội bộ). 16 kHz mono.
- Topology host/Docker: dùng URL MinIO presigned với host `localhost:9000` (đã kiểm AI-11: 200, 5 segment).
Resp: `{"id","object":"asr_completion","created","model","full_transcript": str,"segments":[{"id":int,"start_time":float,"end_time":float,"text":str,"confidence":0–1,"warning": null|"low_confidence"|"blacklist"}]}`
- Audio xử lý theo cửa sổ 20 s, timestamp tuyệt đối; đoạn im lặng bị bỏ (có thể trả `segments: []`).
- Lỗi: file không đọc được → 503. Ví dụ: `examples/asr.*` (path trong request là path cục bộ máy test, chỉ minh họa).
- Chất lượng: VIVOS CER 0.1347; video thật còn nhiều lỗi (AI-02).

### 2.3 `POST /v1/highlight/completions` — Fusion — DRAFT (ứng viên)
Req: `{"model"?: str, "video_id": str, "features": {"vision_embeddings": [[float×256]], "audio_spectrogram_features": [[float×64]]}}`
- **Ràng buộc:** 2 mảng **cùng số phần tử** (1 phần tử = 1 giây); vision 256-d (đầu ra 2.1), audio 64-d (`ai_core.audio.features.audio_features_per_second`).
  Sai → 503 `AI_UNAVAILABLE` (không phải 422).
Resp: `{"id","object":"highlight_completion","created","model","video_id","timeline_scores":[{"second":int,"score":0–100}],"recommended_clips":[{"clip_id","start_time","end_time","average_score":0–100}]}`
- `second` bắt đầu từ 0, liên tục; clip đề xuất = đoạn liên tiếp có score > 75 (có thể rỗng).

### 2.4 `POST /v1/search/completions` — Siamese + Milvus — DRAFT (ứng viên)
Req: `{"model"?: str, "image": str (data URI/base64/path), "top_k": 1–100 (mặc định 5), "threshold": 0–1 (mặc định 0.75)}`
Resp: `{"id","object":"search_completion","created","model","results":[{"video_id","timestamp":float,"similarity_score":0–1,"thumbnail_url"}],"query_metadata":{"execution_time_ms": float}}`
- Collection Milvus `video_frame_embeddings` (128-d, HNSW, COSINE, M=16, efConstruction=200). Kết quả lọc `similarity_score >= threshold` phía inference.
- `thumbnail_url` = object key MinIO dạng `thumbnails/<video_id>/<8 chữ số>.jpg` (tương đối, gateway tự dựng URL).
- Gateway tự lọc processed/published + `min_similarity`. Ảnh hỏng/`top_k` ngoài 1–100 → 422; Milvus lỗi → 503.

### 2.5 `POST /v1/recommendation/completions` — Two-Tower + Milvus — DRAFT
Req: `{"model"?: str, "user_id": str, "limit": int (mặc định 10), "context": {}}`
Resp: `{"id","object":"recommendation_completion","created","model","recommendations":[{"video_id","score":0–1,"title","thumbnail_url"}]}`
- Hành vi thật (sửa so với v0.x): trả **503 `AI_UNAVAILABLE`** khi Milvus không kết nối, khi chưa có collection `user_recommendation_embeddings`,
  **và khi user chưa có vector (cold-start)** hoặc ANN trả 0 video. Gateway dùng popularity fallback cho mọi 503.
- Hiện tại collection chưa tồn tại trong Milvus của stack → luôn 503 (`examples/recommendation.*`). Chưa có ví dụ 200 thật → giữ `DRAFT`.
- Nối Milvus thất bại / thiếu collection: thử lại tối đa mỗi 30 s (request hoặc `/health`), không cần restart. Trạng thái ở `/health.dependencies.recommendation_index`.

### 2.6 `POST /v1/completions` — Mini-GPT (OpenAI-style) — DRAFT (ứng viên)
Req: `{"model"?: str, "prompt": str, "max_tokens": ≥1 (mặc định 150), "temperature": 0–2 (mặc định 0.7), "top_p": 0.9, "frequency_penalty": 0, "presence_penalty": 0}`
Resp: `{"id","object":"text_completion","created","model","choices":[{"text","index":0,"logprobs":null,"finish_reason":"stop"}],"usage":{"prompt_tokens","completion_tokens","total_tokens"}}`
- Prompt dài: service tự map-reduce theo chunk BPE (không giới hạn phía gateway). `temperature: 0` cho kết quả lặp lại được.
- Chất lượng: tóm tắt video thật còn bịa/lặp (human 1.6/5, AI-03). Chỉ dùng làm **draft** để admin duyệt.

### 2.7 `GET /health` — DRAFT (ứng viên)
Resp: `{"status":"ok","gpu_vram_used": MB,"gpu_util": %,"models_loaded":[...],"degraded":[...],"dependencies":{str: str},"queue_depth":int,"device":"cpu|cuda","stub_mode":bool,"load_error": str|null}`
- Integration test thật phải assert `stub_mode == false` và `models_loaded` đủ 6 key ở mục 1.
- `degraded` (D15, v1.1): model có **inference lỗi thật** ở lần gọi gần nhất. Input không hợp lệ (422, ảnh/audio không đọc được, sai số giây/chiều highlight)
  và lỗi dependency **không** tính. Tự gỡ khi model chạy thành công lần sau.
- `dependencies` (mới ở v1.1, mặc định `{}` → client cũ bỏ qua được): trạng thái hạ tầng sau từng capability, không phải lỗi model.
  Key: `visual_index` (Milvus `video_frame_embeddings` + MinIO thumbnail; dùng cho search và index frame của vision),
  `recommendation_index` (Milvus `user_recommendation_embeddings`). Giá trị: `ok` | `unavailable` | `missing_collection`.
  `/health` tự thử lại dependency chưa `ok` tối đa mỗi 30 s → trạng thái tự phục hồi khi Milvus/collection được sửa. `FORCE_STUB=1` → `{}`.

## 3. Changelog
- **v0 (2026-10-26)** — DRAFT, ghi lại API hiện có tại baseline `15976b3`. Không đổi code.
- **v0.1 (2026-10-26)** — DRAFT, chỉ tài liệu: thêm thang sẵn sàng (1b) và quyền runtime :8001 thuộc Claude, Codex chỉ HTTP/mock (1c). Schema không đổi.
- **v0.2 (2026-10-26)** — DRAFT, chỉ tài liệu (AI-06): nguồn checkpoint canonical, thang sẵn sàng có bằng chứng HTTP thật (1b); ghi rõ startup thật cần Milvus và `PYTHONUTF8=1` trên Windows. Schema không đổi.
- **v1.2-rc1 (2026-10-26)** — AI-11 (HO-01). Tương thích ngược: chỉ thêm `VisionRequest.video_id` (optional). Index frame từ data URI theo 1 fps;
  ASR qua MinIO presigned `localhost:9000` xác nhận. Nhánh ingest path cũ giữ nguyên.
- **v1.1-rc1 (2026-10-26)** — AI-10 (D15). Tương thích ngược: chỉ thêm `/health.dependencies` (default `{}`); status code không đổi.
  Đổi ngữ nghĩa `degraded` (chỉ lỗi inference thật, tự phục hồi); recommendation thử lại Milvus mỗi 30 s thay vì cache thất bại tới restart.
  AI-07 (cùng rc): sửa UTF-8 stdout trên Windows trong code; runtime :8001 UP; examples sinh lại từ :8001.
- **v1.0-rc1 (2026-10-26)** — AI-01 (ban đầu ghi "v1.0, 6 endpoint API_READY"; đính chính theo D16 → mọi endpoint DRAFT, 6 ứng viên). Schema request/response **không đổi** so với v0.x.
  Thêm `inference_openapi.json`, `examples/`, `tests/test_live_smoke.py`. Sửa hành vi: startup chạy 1 search warmup Milvus (trước đây search đầu tiên
  sau startup có thể 503 `DEADLINE_EXCEEDED` vì vượt timeout 1 s). Sửa tài liệu cho khớp code: cold-start recommendation trả 503 (không phải 200),
  lệch số giây highlight trả 503, vision ảnh hỏng trả 503 (search 422), `thumbnail_url` search là key tương đối, ngữ nghĩa `degraded`.

## 4. Tái lập ví dụ + smoke (release gate)

```bash
# service thật đang chạy (mục 1c), Milvus UP
cd E:/traning_ai/inference-service
INFERENCE_LIVE_URL=http://127.0.0.1:8001 INFERENCE_LIVE_KEY=<AI_SERVICE_KEY> \
  [INFERENCE_LIVE_MEDIA=<dir *.jpg + clip.wav>] [INFERENCE_EXAMPLES_DIR=../coordination/claude/api/examples] \
  PYTHONUTF8=1 PYTHONPATH=../ai-core ../.venv/Scripts/python -m pytest tests/test_live_smoke.py -v
# OpenAPI
PYTHONPATH=../ai-core ../.venv/Scripts/python -c "import json; from app.main import app; print(json.dumps(app.openapi(), ensure_ascii=False, indent=2))"
```
Không set `INFERENCE_LIVE_URL` → test skip (suite mặc định không cần server). `examples/` v1.0 sinh với media thật: 3 frame + 10 s audio
cắt từ `D:/data_training_ai/minigpt_domain_v1_20261019/raw/youtube/-1Is0o2ZWk0.mp4` (60–70 s).
