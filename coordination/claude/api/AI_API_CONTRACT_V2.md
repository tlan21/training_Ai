# AI API Contract v2.0 — inference-service chỉ tính toán (D24)

**Version: AI-API v2.0 — `DRAFT` (2026-10-29, AI-15).** Chạy **song song** với v1.3 (`AI_API_CONTRACT.md`, `API_READY`) trên cùng :8001.
v1.3 giữ nguyên tới khi Codex chuyển xong + E2E PASS (mục 5); khi đó v1.3 → `DEPRECATED`, rồi gỡ.
Owner: Claude. Codex chỉ đọc (`git show claude/ai-core:coordination/claude/api/AI_API_CONTRACT_V2.md`).
Nguồn code: `inference-service/app/v2.py`, `app/schemas.py` (mục "AI-API v2.0"), `app/worker.py`. OpenAPI: `inference_openapi.json` (có cả `/v1` và `/v2`).
Ví dụ thật (media AI-01, :8001 CPU, 6 checkpoint active): `examples/v2_*.json`.

## 0. Kiến trúc đích (D24, user 2026-10-29)

```
Client/CMS ──HTTP──▶ Backend Go Gateway (+ ingest worker, job queue) ──HTTP (Bearer AI_SERVICE_KEY)──▶ AI Inference Service :8001
                      │  sở hữu TOÀN BỘ dữ liệu                                                     │  chỉ checkpoint + tiền xử lý + suy luận
                      ├─ MinIO     media, thumbnail                                                  │  vào: ảnh, bytes audio, đặc trưng, text
                      ├─ Milvus    vector (video_frame_embeddings, user_recommendation_embeddings)   │  ra:  nhãn, vector, text
                      ├─ Postgres  metadata, jobs                                                    │  KHÔNG kết nối MinIO/Milvus/DB
                      └─ MongoDB   phụ đề, summary                                                   └─ (tùy chọn) model worker GPU từ xa, AI-14
```

- Mọi endpoint `/v2` **không** đọc/ghi MinIO, Milvus, filesystem server (test `inference-service/tests/test_v2.py` khóa).
- Auth, error envelope `{"error":{"code","message"}}`, Bearer `AI_SERVICE_KEY`: như v1.3.
- Checkpoint: 6 SHA y như `AI_API_CONTRACT.md` §1 (không đổi). Two-Tower v2 chưa có (AI-12) → mục 2.4.

| Endpoint | Trạng thái | Thay cho (v1.3) |
|---|---|---|
| `POST /v2/vision/completions` | `DRAFT` (chạy thật, ví dụ thật) | `/v1/vision/completions` + index frame vào MinIO/Milvus |
| `POST /v2/search/embeddings` | `DRAFT` (chạy thật, ví dụ thật) | `/v1/search/completions` (tìm Milvus phía AI) |
| `POST /v2/asr/completions` | `DRAFT` (chạy thật, ví dụ thật) | `/v1/asr/completions` (`audio_url` MinIO presigned) |
| `POST /v2/recommendation/embeddings` | `DRAFT` — thật trả `503 MODEL_NOT_READY` tới AI-12 | `/v1/recommendation/completions` (tìm Milvus phía AI) |
| `POST /v1/highlight/completions` | `API_READY` — **giữ nguyên** | — |
| `POST /v1/completions` | `API_READY` — **giữ nguyên** | — |
| `GET /health` | `API_READY` — giữ nguyên schema | `dependencies` rỗng sau khi gỡ MinIO/Milvus (mục 5) |

`DRAFT` ở đây: schema + hành vi đã chạy thật trên :8001 và có ví dụ thật, nhưng chưa qua release/E2E Codex. Codex được dùng ngay (mock `FORCE_STUB=1` trả đúng schema).

## 1. Chung

- Ảnh: chuỗi `data:image/...;base64,<...>` hoặc base64 trần, JPEG/PNG/WebP ≤20 MP. **Không** nhận path (v1 nhận path `/srv/work`).
- Lỗi input (ảnh/audio không đọc được, sai chiều, vượt giới hạn) = **422 `VALIDATION_ERROR`** — khác v1.3 (v1 trả 503 cho media hỏng).
- Lỗi model/worker = 503 `AI_UNAVAILABLE` (model vào `/health.degraded`; worker từ xa mất → `dependencies.model_worker`).
- Vector: float32 → JSON number, đã L2-normalize. Siamese = 128-d COSINE. Two-Tower = 128-d IP (IP = cosine vì đã normalize).

## 2. Endpoints

### 2.1 `POST /v2/vision/completions` — ViT + Siamese, không index
Req: `{"model"?: "primitive-vit-classifier", "keyframes": [ảnh, 1..600]}` — keyframe thứ i = giây i (ingest 1 fps).
Resp 200:
```json
{"id":"vis-primitive-…","object":"vision_completion","created":1793243164,"model":"primitive-vit-classifier",
 "category_suggestion":"tin_tuc",
 "category_logit_sums":{"bong_da":-4.13,"ca_nhac":-4.63,"the_thao":-0.51,"tin_tuc":3.19},
 "embeddings_256":[[...256], ...],   // backbone Siamese (đặc trưng Fusion đã train, AI-19), 1/keyframe → input /v1/highlight
 "siamese_vectors":[[...128], ...]}  // Siamese 1/keyframe → backend ghi Milvus video_frame_embeddings
```
- Video > 600 frame: chia lô theo thứ tự, **cộng `category_logit_sums` của các lô**, lấy argmax = đúng nhãn của v1 khi gửi cả video một lần.
  Nhãn chỉ 4 lớp ViT MVP (`bong_da`,`the_thao`,`ca_nhac`,`tin_tuc`).
- Lỗi: 422 (thiếu/ >600 keyframe, không phải base64, ảnh hỏng); 503 model. Ví dụ: `examples/v2_vision.{request,response}.json`.
- Smoke thật: `category_suggestion` + `embeddings_256` trùng `/v1/vision` trên cùng frame.

### 2.2 `POST /v2/search/embeddings` — vector truy vấn Siamese
Req: `{"model"?: "primitive-siamese-vit", "image": ảnh}`
Resp 200: `{"id","object":"search_embedding","created","model","vector":[...128],"dim":128,"metric":"COSINE","normalized":true}`
- Backend tự tìm Milvus (mục 6.1): cùng tham số v1 → cùng kết quả v1. `top_k`/`threshold` giờ là việc của backend.
- Lỗi: 422 ảnh không đọc được; 503 model. Ví dụ: `examples/v2_search.*`. Smoke thật: vector = `siamese_vectors[0]` của 2.1 (sai số < 1e-5).

### 2.3 `POST /v2/asr/completions` — bytes audio (multipart)
Req `multipart/form-data`: `file` (WAV/FLAC/OGG, khuyến nghị 16 kHz mono PCM16; ≤ 64 MiB), `language`=`vi` (khác → 422),
`model`? , `offset_seconds` (float ≥ 0, mặc định 0 — cộng vào mọi timestamp).
Resp 200: y hệt `ASRResponse` v1.3 (`full_transcript`, `segments[{id,start_time,end_time,text,confidence,warning}]`).
- **File dài:** backend cắt thành phần ≤ 64 MiB **tại bội số 20 s** (vd mỗi phần 600 s = 19.2 MB PCM16 mono 16 kHz), gửi tuần tự với
  `offset_seconds` = điểm bắt đầu phần; nối `segments` (đánh lại `id`), nối `full_transcript` bằng dấu cách.
  Cắt đúng bội số 20 s → kết quả **trùng** gửi một lần (model giải mã cửa sổ 20 s cố định; test `test_real_asr_split_at_20s_matches_one_shot`).
- Lỗi: 413 `PAYLOAD_TOO_LARGE`; 422 audio không đọc được / language; 503 model. Ví dụ: `examples/v2_asr.*` (request ghi tóm tắt multipart).
- Smoke thật: transcript trùng `/v1/asr` (audio_url path) trên cùng `clip.wav`.
- Chất lượng (D23): phụ đề là **bản nháp máy**, admin duyệt — không đổi.

### 2.4 `POST /v2/recommendation/embeddings` — Two-Tower encode (khớp AI-12, `ttv2-features-v1`)
Req:
```json
{"model"?: "primitive-two-tower-recommender",
 "videos":[{"video_id":"vid_…","category_id":"cat_…"|null,"content_embedding_256":[...256]|null,"positive_count":3}],
 "users":[{"user_id":"usr_…","preferred_category_ids":["cat_…"],"positive_video_ids":["vid_…"]}]}
```
≤1000 video + ≤1000 user/request; mỗi `positive_video_ids` phải có trong `videos` của cùng request (feature user = trung bình vector video dương, AI-12).
Resp 200: `{"id","object":"recommendation_embeddings","created","model","feature_version":"ttv2-features-v1","dim":128,"metric":"IP","normalized":true,
"videos":[{"video_id","vector":[...128]}],"users":[{"user_id","vector":[...128]}]}` → backend ghi Milvus `user_recommendation_embeddings`, tự ANN (mục 6.2).
- **Hiện tại chạy thật luôn `503 MODEL_NOT_READY`**: checkpoint active là MovieLens v1 (không encode được `usr_*`/`vid_*`); Two-Tower v2 chờ dữ liệu thật (AI-12 ⇐ INT-15).
  Gateway giữ popularity. `FORCE_STUB=1` trả vector tất định để dựng luồng. Feature cụ thể có thể chỉnh khi AI-12 train — đổi = bump minor + REL.
- Lỗi: 422 (id dương không có trong `videos`, `content_embedding_256` sai chiều); 503 `MODEL_NOT_READY`. Ví dụ: `examples/v2_recommendation.error*.json`.

### 2.5 Giữ nguyên
`/v1/highlight/completions`, `/v1/completions`, `/health` — như `AI_API_CONTRACT.md` §2.3/§2.6/§2.7.

## 3. Error codes (v2)

| HTTP | `code` | Khi nào |
|---|---|---|
| 401 | `UNAUTHORIZED` | thiếu/sai Bearer |
| 413 | `PAYLOAD_TOO_LARGE` | audio > 64 MiB → chia nhỏ (2.3) |
| 422 | `VALIDATION_ERROR` | schema sai, ảnh/audio không đọc được, path thay vì base64, >600 keyframe, language ≠ vi, id dương thiếu |
| 503 | `AI_UNAVAILABLE` | model lỗi thật (vào `degraded`) hoặc worker từ xa mất (`dependencies.model_worker`) |
| 503 | `MODEL_NOT_READY` | recommendation encode khi chưa có Two-Tower v2 |

## 4. Bảng di chuyển v1.3 → v2.0

| Việc | v1.3 (hiện tại) | v2.0 (đích) — ai làm |
|---|---|---|
| Phân loại + embedding video | `/v1/vision` (+`video_id`) | `/v2/vision` — gateway/ingest gọi (Codex) |
| Ghi vector frame Milvus | AI ghi (`visual_index.index_frames`) | Backend ghi `siamese_vectors` (Codex, mục 6.1) |
| Upload thumbnail MinIO | AI ghi `thumbnails/{vid}/{sec:08d}.jpg` | Backend ghi (cùng key), Codex |
| Tìm bằng ảnh | `/v1/search` (AI tìm Milvus, trả video_id/timestamp/thumbnail) | `/v2/search/embeddings` → backend tìm Milvus + lọc publish/privacy (Codex) |
| Phụ đề | `/v1/asr` `audio_url` (AI tải MinIO presigned) | `/v2/asr` multipart bytes + `offset_seconds` (Codex) |
| Highlight / tóm tắt | `/v1/highlight`, `/v1/completions` | không đổi |
| Gợi ý | `/v1/recommendation` (AI tra Milvus, luôn 503) | `/v2/recommendation/embeddings` → backend ghi/tra Milvus; MVP vẫn popularity (Codex + AI-12) |
| Xóa video | AI xóa vector khi re-index; backend xóa Postgres | Backend xóa đồng bộ MinIO + Milvus + Postgres/Mongo một chỗ (Codex) |
| `/health.dependencies` | `visual_index`, `recommendation_index` | rỗng (`model_worker` chỉ khi worker từ xa) — sau cutover |

## 5. Giai đoạn song song + cutover

1. Hiện tại: `/v1` (API_READY) + `/v2` (DRAFT) cùng chạy trên :8001. Codex chuyển từng luồng theo HC-13; mỗi luồng chuyển xong có thể tắt gọi `/v1` tương ứng.
2. Codex báo E2E PASS trên `/v2` (RE:HC-13) → release (README mục 6): `/v2` → `API_READY`, `/v1/vision|search|asr|recommendation` → `DEPRECATED`.
3. Release kế: gỡ `minio`/`pymilvus` khỏi inference-service, lifespan không cần Milvus, xóa `/v1` deprecated (bump v3.0 nếu xóa path; chỉ khi Codex xác nhận không còn gọi).

## 6. Đặc tả dữ liệu backend tiếp quản (đo trên Milvus stack Codex, 2026-10-29)

### 6.1 `video_frame_embeddings` (Siamese)
- Schema hiện có: `id` INT64 primary **auto_id**, `vector` FLOAT_VECTOR dim 128, `payload` JSON `{"video_id","timestamp","thumbnail_url"}`
  (vd `{"video_id":"vid_dm3nf6fi23us","timestamp":0.0,"thumbnail_url":"thumbnails/vid_dm3nf6fi23us/00000000.jpg"}`).
- Index: HNSW `M=16, efConstruction=200`, metric COSINE. Search: `ef=max(64, top_k)`, consistency Session, trả hit `distance ≥ threshold`,
  `similarity_score = clamp(distance, 0, 1)`; v1 mặc định `top_k=5`, `threshold=0.75`.
- Ghi một video: **xóa trước** `payload["video_id"] == "<vid>"` rồi insert (không nhân bản khi retry); timestamp = giây của frame.
- Thumbnail: bucket `thumbnails`, key `{video_id}/{second:08d}.jpg`, `image/jpeg`; `thumbnail_url` lưu key tương đối `thumbnails/...`.
- Hiện có: **411 vector sống / 49 video** (`num_entities` 447 gồm bản đã xóa chưa compact). Schema giữ nguyên → backend dùng tiếp collection, **không cần copy**;
  chỉ cần đo lại trước/sau cutover (count + mẫu payload) và backfill video thiếu vector bằng `/v2/vision`.

### 6.2 `user_recommendation_embeddings` (Two-Tower) — chưa tồn tại trên stack
- database_schema §4: dim 128, IVF_FLAT `nlist=1024`, metric IP; search `nprobe=128` (đo AI-13: nprobe 16 → 0 hit với filter `type=="video"`).
- Score hiển thị 0–1 = `(IP + 1) / 2`. Chỉ tạo khi AI-12 có checkpoint v2.

## 7. Changelog
- **v2.0 DRAFT (2026-10-29)** — AI-15 (D24 bước 2). Thêm `/v2/vision/completions`, `/v2/search/embeddings`, `/v2/asr/completions`,
  `/v2/recommendation/embeddings`. Không đổi gì ở `/v1` (compat test khóa với snapshot v1.2 và v1.3).

## 8. Tái lập smoke + ví dụ
```bash
cd E:/traning_ai/inference-service
INFERENCE_LIVE_URL=http://127.0.0.1:8001 INFERENCE_LIVE_KEY=<AI_SERVICE_KEY> INFERENCE_LIVE_MEDIA=D:/tmp/ai01_20261026/media \
  [INFERENCE_EXAMPLES_DIR=<dir>] PYTHONUTF8=1 PYTHONPATH=../ai-core ../.venv/Scripts/python -m pytest tests/test_live_smoke.py -v   # 9 test: v1 6 + v2 3
```
