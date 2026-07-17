# 00 — MASTER PLAN TRIỂN KHAI (BINDING CONTRACT)
*Nguồn sự thật cho 4 plan con: @01_ai_core_plan.md, @02_backend_plan.md, @03_cms_ui_plan.md, @04_client_ui_plan.md. Mọi plan con và mọi dòng code PHẢI khớp file này. Nền tảng: 14 tài liệu thiết kế trong `.claude\` (đã review hết conflict 2026-07).*

---

## 0. ƯU TIÊN THI CÔNG BẮT BUỘC — AI-FIRST (quyết định 2026-07-17, override mọi thứ tự khác)

**Luật:** Phase 1 (AI Core) phải HOÀN CHỈNH trước khi bắt đầu bất kỳ task Phase 2/3/4 nào. AI là tiền đề — mọi tính năng khác chỉ tiêu thụ output AI.

**"AI hoàn chỉnh" định nghĩa bằng cổng (AI-GATE), đủ CẢ 4 mới mở Phase 2/3:**
1. T1.1–T1.7 xong: 6 model train xong, unit test toán học pass (gradient check, AdamW parity, BPE roundtrip, SDPA parity).
2. Metric đạt ngưỡng bảng §1 @evaluation_plan.md — hoặc không đạt thì ghi số thật + limitation, được duyệt bởi chủ dự án (không âm thầm hạ ngưỡng).
3. Checkpoint 6 model + config + seed nằm trong `data/manifests/`, load lại được.
4. **T1.8 (chuyển từ T2.6 lên):** inference-service FastAPI :8001 nạp 6 checkpoint THẬT, đủ 6 endpoint + `/health` + GPU queue + Bearer key, trả đúng schema bảng 2.4 — đo VRAM ≤ 4GB. Đây là sản phẩm bàn giao của phase AI: các phần sau chỉ việc gọi.

**Ngoại lệ duy nhất (tận dụng giờ GPU train qua đêm):** được làm task Phase 0 (T0.1–T0.4 contract/stub/docker-compose — CPU-bound, không phụ thuộc AI) trong lúc GPU bận train. CẤM đụng Phase 2/3 trước khi AI-GATE mở, kể cả "làm sẵn cho nhanh".

**Thứ tự trong phase AI (dependency cứng, không đảo):** T1.1 primitives → T1.2 data pipeline → T1.3 ViT + Siamese → T1.4 ASR → T1.5 Fusion (cần Siamese embedding + nhãn weak) → T1.6 Mini-GPT (cần BPE; fine-tune ASR-noise cần CER thật từ T1.4) → T1.7 Two-Tower → T1.8 inference-service.

---

## 1. Cấu trúc Monorepo

```
traning_ai/
├── ai-core/                # Python package thuật toán nguyên thủy (KHÔNG dính web/DB)
│   └── ai_core/
│       ├── primitives/     # attention.py, rmsnorm.py, swiglu.py, rope.py, block.py
│       ├── optim/          # adamw.py (tự viết)
│       ├── tokenizer/      # bpe.py (tự viết)
│       ├── audio/          # mel.py (FFT + Mel filterbank tự cài), features.py
│       ├── vision/         # patchify.py, augment.py
│       ├── models/         # vit.py, siamese.py, asr_ctc.py, highlight_fusion.py, minigpt.py, two_tower.py
│       ├── training/       # trainer.py, schedule.py, configs/*.yaml, datasets/*.py
│       └── tests/          # gradient_check, adamw_parity, overfit_one_batch, bpe_roundtrip, sdpa_parity
├── inference-service/      # 1 FastAPI process, nạp 6 model, port 8001 (nội bộ)
├── backend/                # Go — mọi service KHÔNG dính AI (trừ ingest-worker Python vì Decord)
│   ├── gateway/            # Go (Gin) public API, port 8000, prefix /api
│   ├── workers/
│   │   ├── orchestrator/   # Go — consume Kafka, gọi AI qua REST :8001, update DB/stage
│   │   ├── ffmpeg-cutter/  # Go — os/exec gọi FFmpeg -ss -to -c copy
│   │   └── ingest-worker/  # Python — Decord/PyAV (binding chỉ có Python, tiền xử lý AI)
│   └── internal/           # Go: domain entities, ports (interfaces), adapters (pgx, mongo-go-driver, milvus-sdk-go, kafka-go, minio-go, go-redis)
├── cms/                    # React + Vite + Zustand + TanStack Query, port 5173
├── client/                 # Next.js + Zustand, port 3000
├── data/                   # raw/ processed/ labels/ manifests (theo @dataset_spec.md)
└── infra/                  # docker-compose.yml (postgres, mongo, milvus, kafka, minio, redis, services)
```

---

## 2. BẢNG API CONTRACT (bất biến — UI và backend code theo đây, không tự bịa thêm)

### 2.1. Auth & User (public, prefix `/api`)
| Method | Path | Auth | Body → Response |
|---|---|---|---|
| POST | `/api/auth/register` | — | `{username,email,password}` → `{user, access_token}` + Set-Cookie refresh (HttpOnly) |
| POST | `/api/auth/login` | — | `{email,password}` → `{user, access_token}` + cookie |
| POST | `/api/auth/refresh` | cookie | → `{access_token}` |
| POST | `/api/auth/logout` | JWT | → 204, xóa cookie + row `user_sessions` |
| GET | `/api/users/me` | JWT | → `{id,username,email,role,preferences:[category_id]}` |
| PUT | `/api/users/me` | JWT | `{username?}` → user |
| PUT | `/api/users/me/preferences` | JWT | `{category_ids:[...]}` (≥3) → 200; backend khởi tạo lại user vector Milvus |
| GET | `/api/users/me/history` | JWT | → `{items:[{clip,watched_at,duration_watched}],next_cursor}` |
| GET | `/api/users/me/likes` | JWT | → `{items:[clip],next_cursor}` |

### 2.2. Client content (public, JWT)
| Method | Path | Ghi chú |
|---|---|---|
| GET | `/api/feed?cursor&limit=10` | Clips `status='published'`. Gọi nội bộ `/v1/recommendation/completions`; fallback popularity khi user mới/AI lỗi |
| GET | `/api/videos?category_id&sort=trending\|newest&cursor&limit` | Duyệt video `processed` công khai (màn Discovery). `trending` = popularity từ `user_interactions` 7 ngày gần nhất |
| GET | `/api/videos/{id}` | Chỉ `status='processed'`. → meta + category + danh sách clips published |
| GET | `/api/videos/{id}/analysis` | → `{timeline_scores:[{second,score}], summary, key_moments:[{timestamp,text}], hashtags:[]}` (score 0–100; chỉ khi processed, summary/key_moments chỉ khi approved) |
| GET | `/api/videos/{id}/subtitles` | → `{segments:[{segment_index,start_time,end_time,text,confidence,warning?}]}` (confidence 0–1; warning ∈ `low_confidence\|blacklist`) |
| GET | `/api/clips/{id}` | Clip published + video gốc ref |
| POST | `/api/search/visual` | multipart `image` + form `min_similarity?` (0–1, mặc định 0.5 — slider "Mức độ tương đồng" UI) → gọi `/v1/search/completions`, gateway lọc theo min_similarity → `{results:[{video_id,timestamp,similarity_score,thumbnail_url}]}` (similarity 0–1) |
| GET | `/api/search?q=` | Text: Mongo text-index `subtitles.segments.text` + Postgres `videos.title` → kết quả kèm timestamp câu khớp |
| POST | `/api/interactions` | `{video_id, clip_id?, interaction_type: click\|watch_time\|like\|share\|skip\|save, duration_watched?}` → 201 (`save` = bookmark, tín hiệu dương cho Two-Tower) |
| GET | `/api/categories` | Danh mục public |

### 2.3. CMS (prefix `/api/cms`, role `admin|editor`, JWT)
| Method | Path | Ghi chú |
|---|---|---|
| POST | `/api/cms/videos` | multipart ≤2GB → MinIO, row `videos(uploaded)`, row `video_processing_jobs(pending)`, Kafka `video.uploaded` |
| GET | `/api/cms/videos?status&page` | Mọi trạng thái |
| GET | `/api/cms/videos/{id}` | Meta + job + analysis refs |
| DELETE | `/api/cms/videos/{id}` | Xóa mềm + xóa vectors Milvus + ẩn clips |
| GET | `/api/cms/videos/{id}/analysis` | → `{timeline_scores, ai_generated_clips, category_suggestion, summary, summary_status, suggested_title, key_moments, hashtags}` |
| POST | `/api/cms/videos/{id}/summary/regenerate` | Gọi lại `/v1/completions` với temperature/top-k khác (nút "Thử tiêu đề khác") → draft mới `{summary, suggested_title}` |
| PUT | `/api/cms/videos/{id}/category` | `{category_id}` — Admin duyệt suggestion → ghi Postgres (nguyên tắc 6.3.3) |
| PUT | `/api/cms/videos/{id}/summary` | `{summary}` (sửa draft) |
| POST | `/api/cms/videos/{id}/summary/approve` | Đánh dấu approved → Client mới thấy |
| PUT | `/api/cms/videos/{id}/subtitles` | `{segments:[...]}` bulk update Mongo |
| GET | `/api/cms/jobs?status` | Job queue + `current_stage` + `progress` (0–100 thô theo stage) |
| GET | `/api/cms/jobs/{id}` | Chi tiết + `error_log` |
| POST | `/api/cms/jobs/{id}/retry` | Chỉ khi `failed` → reset `pending`, re-produce Kafka từ stage lỗi |
| POST | `/api/cms/jobs/{id}/cancel` | Chỉ khi `pending\|running` → `failed`, `error_log='canceled_by_user'` |
| GET | `/api/cms/settings` | → `system_settings` (key AI trả masked `sk-local-••••`) |
| PUT | `/api/cms/settings` | `{highlight_threshold?, asr_warning_threshold?, auto_highlight_enabled?, auto_subtitle_enabled?, ai_service_api_key?}` — **admin only** |
| GET | `/api/cms/system/health` | Proxy `GET :8001/health` → `{gpu_vram_used,gpu_util,models_loaded,queue_depth}` (số thật RTX 3060 12GB — không hard-code H100 như mock Stitch) |
| POST | `/api/cms/clips` | `{video_id,title,start_time,end_time}` → row `clips(draft→processing)`, Kafka `clip.cut.requested` |
| POST | `/api/cms/clips/{id}/publish` | Chỉ khi cut xong → `status='published'` |
| PUT/DELETE | `/api/cms/clips/{id}` | Sửa meta / reject |
| GET | `/api/cms/clips?video_id&status` | |
| CRUD | `/api/cms/categories` | GET/POST/PUT/DELETE |
| GET | `/api/cms/users` · PUT `/api/cms/users/{id}/role` | admin only |

### 2.4. AI Inference Service (nội bộ `:8001`, 1 FastAPI process nạp cả 6 model — @features.md quy ước triển khai)
| Path | Model | Vào → Ra (schema chi tiết @architecture.md mục 2) |
|---|---|---|
| `POST /v1/vision/completions` | ViT | keyframe paths/base64 → `{category_suggestion, embeddings_256[]}` — CHỈ nội bộ |
| `POST /v1/asr/completions` | ASR CTC | audio_url wav → `{full_transcript, segments[]}` |
| `POST /v1/highlight/completions` | Fusion | vision_embeddings + audio_features → `{timeline_scores(0–100), recommended_clips}` |
| `POST /v1/search/completions` | Siamese | image → top-k `{video_id,timestamp,similarity_score}` (đọc Milvus) |
| `POST /v1/recommendation/completions` | Two-Tower | user_id → ranked videos (đọc Milvus) |
| `POST /v1/completions` | Mini-GPT | prompt (transcript; service tự map-reduce >1024 token) → OpenAI-style choices |
| `GET /health` | — | GPU stats + queue depth |
Quy tắc: GPU jobs qua 1 hàng đợi tuần tự nội bộ (asyncio queue + 1 GPU worker). Search/recommendation chỉ encode nhẹ + query Milvus.
**Auth :8001:** mọi request kèm `Authorization: Bearer ${AI_SERVICE_KEY}` (format `sk-local-...`, đặt qua env của inference-service + gateway; hiển thị masked tại màn Cài đặt CMS). Đây là "API key của AI nguyên thủy tự dựng" — hệ thống KHÔNG gọi OpenAI hay bất kỳ AI ngoài nào.

### 2.5. Kafka Topics (event contract)
| Topic | Payload | Producer → Consumer |
|---|---|---|
| `video.uploaded` | `{video_id, raw_file_path}` | gateway → ingest-worker |
| `video.preprocessed` | `{video_id, keyframes_path, audio_path, duration}` | ingest-worker → orchestrator |
| `ai.stage.completed` | `{video_id, stage: vision\|asr\|highlight\|embedding\|summary, ok, error?}` | orchestrator (tự produce/consume để chain) |
| `clip.cut.requested` | `{clip_id, video_id, start_time, end_time}` | gateway → ffmpeg-cutter |
| `clip.cut.completed` | `{clip_id, clip_file_path, ok}` | ffmpeg-cutter → gateway handler (update Postgres) |
Orchestrator cập nhật `video_processing_jobs.current_stage` theo từng stage; đủ 4 stage GĐ2 + summary → `videos.status='processed'`, job `completed`.

### 2.6. Conventions (mọi service/UI tuân thủ)
- Auth: access JWT 15 phút để RAM (Zustand); refresh 7 ngày HttpOnly cookie; header `Authorization: Bearer`.
- Error envelope: `{"error":{"code":"VIDEO_NOT_FOUND","message":"..."}}` + HTTP status chuẩn.
- Pagination: cursor-based `?cursor=&limit=` → `{items,next_cursor}` (client); page-based cho CMS bảng.
- Thời gian: ISO8601 UTC. Điểm highlight 0–100; similarity 0–1 (@architecture.md quy ước thang điểm).
- OpenAPI **contract-first**: file `infra/openapi.yaml` viết tay là nguồn sự thật (đúng bảng mục 2) → `oapi-codegen` sinh Go server stubs + types cho gateway; `openapi-typescript` sinh TS types cho CMS/Client — **cả BE lẫn UI đều không viết type tay** → ghép là chạy, không sửa nhiều. Riêng inference-service (Python FastAPI) tự sinh `/openapi.json` nội bộ.
- Ngôn ngữ: **Go** cho gateway/orchestrator/ffmpeg-cutter (không dính AI); **Python** cho inference-service + ingest-worker (PyTorch/Decord).
- ID prefix theo @database_schema.md (`usr_`,`vid_`,`clp_`,`job_`,`cat_`,`ses_`).
- **UI design reference:** HTML Stitch export (`stitch_ai_video_cms/`, `stitch_ai_video_platform_vietnamese/`) là nguồn sự thật về layout/copy/màu — dựng chính xác theo đó SAU KHI áp CẮT-list (mục 7 @03 / mục 8 @04: bỏ dịch AI, object detection, face recognition, phụ đề Nhật/Hàn, comment/follow, quên mật khẩu). Copy sai trong Stitch phải sửa: "thuật toán NLP"→"đa phương thức vision+audio", "Vision-X v2.4"→tên checkpoint thật, "H100 80GB"→số thật từ `/health`.

---

## 3. PHASES & TASK BREAKDOWN (khớp @roadmap.md đã hiệu chỉnh)

### Phase 0 — Contract & Hạ tầng (W1, song song R&D)
- [ ] T0.1 docker-compose: postgres, mongo, milvus, kafka, minio, redis
- [ ] T0.2 Migration SQL đầy đủ (@database_schema.md sau bổ sung) + seed categories + admin user + seed `system_settings` (threshold 75/65, AI_SERVICE_KEY)
- [ ] T0.3 Skeleton gateway + inference-service với endpoint stub trả mock đúng schema → FE code được ngay từ W1
- [ ] T0.4 Sinh TypeScript types từ OpenAPI → `cms/src/api-types.ts`, `client/src/api-types.ts`

### Phase 1 — AI Core (W1–W6 GPU tuần tự, chi tiết @01_ai_core_plan.md)
- [x] T1.1 (W1) primitives + optim + tokenizer + unit tests toán học (gradient check, AdamW parity, BPE roundtrip, SDPA parity)
- [ ] T1.2 (W1–2) data pipeline: thu thập video, tool gán nhãn, weak-label highlight bằng audio cross-correlation (@dataset_spec.md)
- [ ] T1.3 (W2) train ViT + Siamese → checkpoint + báo cáo metric (@evaluation_plan.md)
- [ ] T1.4 (W3–4) train ASR CTC (chạy đêm)
- [ ] T1.5 (W4) train Highlight Fusion + ablation visual/audio/fusion
- [ ] T1.6 (W5–6) pretrain Mini-GPT + fine-tune tóm tắt (chạy đêm)
- [ ] T1.7 (W6) train Two-Tower (MovieLens + onboarding)
- [ ] T1.8 (W6) inference-service :8001 nạp 6 checkpoint thật + GPU queue + Bearer key + /health (chuyển từ T2.6 lên — điều kiện AI-GATE mục 0)

### Phase 2 — Backend (W3–5, chi tiết @02_backend_plan.md)
- [ ] T2.1 Hexagonal shared: entities, ports, adapters + mock adapters cho unit test
- [ ] T2.2 Auth service (JWT + refresh rotation + user_sessions)
- [ ] T2.3 Ingest worker (Decord 1fps + wav) + orchestrator (Kafka chain gọi 6 AI endpoint)
- [ ] T2.4 FFmpeg cutter worker (`-ss -to -c copy`)
- [ ] T2.5 Toàn bộ endpoint 2.1–2.3 thay stub bằng thật + Redis cache (feed, search)
- [ ] ~~T2.6~~ → đã chuyển thành T1.8 (AI-FIRST, mục 0). Phase 2 chỉ còn tiêu thụ :8001 có sẵn.

### Phase 3 — Frontend (W5–7, chi tiết @03_cms_ui_plan.md, @04_client_ui_plan.md)
- [ ] T3.1 CMS: 10 màn (login, dashboard, upload/queue, video list, highlight review, **subtitle+summary gộp 1 màn 3 cột theo Stitch**, clips/thư viện xuất bản, categories, users, **settings — tab Cấu hình AI**). Design reference: `stitch_ai_video_cms/` + CẮT-list @03_cms_ui_plan.md mục 7
- [ ] T3.2 Client: 8 màn (auth, onboarding, feed, video detail, visual search, text search, profile, **discovery**). Design reference: `stitch_ai_video_platform_vietnamese/` + CẮT-list @04_client_ui_plan.md mục 8

### Phase 4 — Tích hợp & Tối ưu (W7–8)
- [ ] T4.1 E2E: upload → processed → duyệt → publish → hiện feed (test tự động Playwright)
- [ ] T4.2 Visual search < 2s; Redis cache; HNSW tuning (M=16, efConstruction=200)
- [ ] T4.3 Đo VRAM inference ≤ 4GB, kiểm memory leak 20 video liên tiếp

### Phase 5 — Kiểm thử & Bàn giao (W9–12)
- [ ] T5.1 Load test 50 video dồn hàng đợi (tiêu chí @roadmap.md đã sửa)
- [ ] T5.2 Soak test 48h + fix bug
- [ ] T5.3 Docs bàn giao + số liệu evaluation cho luận án

**Thứ tự vàng (đã sửa theo mục 0 — AI-FIRST):** Phase 1 AI hoàn chỉnh trước tiên (AI-GATE mục 0); Phase 0 contract/stub chỉ chen vào lúc GPU bận train; Phase 2/3 chỉ bắt đầu sau khi AI-GATE mở — khi đó backend/UI ghép vào inference-service THẬT ngay từ đầu, không cần mock AI.

---

## 4. Định nghĩa Hoàn thành (DoD) tổng
- Mọi metric đạt ngưỡng @evaluation_plan.md mục 1; mọi unit test toán học pass.
- E2E flow chạy demo được trên docker-compose 1 máy, 1× RTX 3060.
- FE không có type viết tay lệch OpenAPI; không endpoint nào ngoài bảng mục 2.

---

## 5. Protocol cho model yếu / agent nhỏ (bắt buộc khi giao việc)

Mục tiêu: một model yếu vẫn hoàn thành được nếu task đủ hẹp và không phải tự suy luận qua 14 file.

### 5.1. Thứ tự nguồn sự thật
Khi có mâu thuẫn, dùng thứ tự này và không tranh luận:

1. `infra/openapi.yaml` — shape API, request/response, enum, path.
2. `.claude/plan/00_master_plan.md` — kiến trúc, topic, conventions, thứ tự phase.
3. Plan con đúng khu vực: `01_ai_core_plan.md`, `02_backend_plan.md`, `03_cms_ui_plan.md`, `04_client_ui_plan.md`.
4. Spec nền: `database_schema.md`, `model_spec.md`, `dataset_spec.md`, `evaluation_plan.md`.
5. Các file cũ như `features.md`, `roadmap.md`, `architecture*.md` chỉ để đọc bối cảnh, không dùng để override contract.

### 5.2. Quy tắc giao task
Mỗi task giao cho model yếu phải có đúng format sau:

```text
TASK: <mã task từ plan, ví dụ T2.2.3>
READ ONLY THESE FILES:
- infra/openapi.yaml
- .claude/plan/00_master_plan.md
- .claude/plan/02_backend_plan.md
CHANGE ONLY:
- <danh sách file/dir được phép sửa>
DONE WHEN:
- <lệnh build/test cụ thể pass>
- <endpoint/component/logic cụ thể chạy theo contract>
DO NOT:
- thêm endpoint mới
- đổi schema OpenAPI nếu không được yêu cầu
- refactor ngoài phạm vi
```

Không giao kiểu “làm backend auth” hoặc “làm CMS”. Giao task nhỏ như “T2.2.3 refresh rotation” hoặc “T3.1.5 HeatmapTimeline + test”.

### 5.3. Cách làm từng task
- Đọc `infra/openapi.yaml` trước. Nếu thiếu field thật sự cần, dừng và sửa OpenAPI trong task riêng trước khi code.
- Sinh types/stubs trước, không viết tay response type.
- Làm stub/mock pass trước khi nối DB/GPU thật.
- Viết test nhỏ nhất cho logic dễ sai: auth rotation, heatmap mapping, player highlight ranges, orchestrator retry.
- Không tối ưu Redis/GPU/cache khi chưa có flow đúng. Stub trước, thật sau.

### 5.4. Checkpoint bắt buộc sau mỗi task
Mỗi task xong phải báo 4 dòng:

```text
Changed: <files>
Verified: <commands>
Contract touched: yes/no
Next safe task: <task id>
```

Nếu build/test chưa chạy được, task chưa xong.
