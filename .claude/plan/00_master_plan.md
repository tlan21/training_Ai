# 00 — MASTER PLAN TRIỂN KHAI (BINDING CONTRACT)
*Nguồn sự thật cho 4 plan con: @01_ai_core_plan.md, @02_backend_plan.md, @03_cms_ui_plan.md, @04_client_ui_plan.md. Mọi plan con và mọi dòng code PHẢI khớp file này. Nền tảng: 14 tài liệu thiết kế trong `.claude\` (đã review hết conflict 2026-07).*

---

## 0. HAI LÀN SONG SONG + AI-GATE (quyết định 2026-10-26, thay luật AI-FIRST 2026-07-17)

**Luật:** dự án chạy 2 làn song song — **Claude = làn AI** (ai-core, training, checkpoint, inference-service :8001, AI API Contract), **Codex = làn Tích hợp** (backend, ingest-worker, CMS, Client, OpenAPI public, compose, E2E, load/soak). Phân quyền path, Git workflow, handoff, release: `coordination/README.md`; luật riêng `.claude/CLAUDE.md` (Claude) và `AGENTS.md` (Codex). Task độc lập được làm song song; **không** còn cấm Phase 2/3 khi AI-GATE chưa mở.

**Giữ nguyên (không nới):**
- Thứ tự dependency trong làn AI (dòng "Thứ tự trong phase AI" bên dưới).
- AI-GATE (4 điều kiện bên dưới) là **cổng nghiệm thu AI**: làn Claude chỉ được báo AI hoàn chỉnh khi đủ cả 4; không hạ ngưỡng âm thầm.
- DoD tổng mục 4.

**Dependency chéo bắt buộc:**
- Codex được phát triển trên mock (Go `AIClientMem`, inference `FORCE_STUB=1`) khi endpoint còn DRAFT/đang train, nhưng tích hợp model X chỉ DONE khi endpoint X `API_READY` (`coordination/claude/api/AI_API_CONTRACT.md`) **và** integration test gọi :8001 thật (`stub_mode=false`) PASS.
- T5.1/T5.2 (load/soak GPU) ⇐ đo VRAM ≤4 GB (AI-04). Chất lượng summary/phụ đề video thật ⇐ AI-03/AI-02 (không chặn tích hợp kỹ thuật).

**AI-GATE — "AI hoàn chỉnh" (đủ CẢ 4; trạng thái hiện tại: `coordination/PROJECT_STATUS.md` mục 1):**
1. T1.1–T1.7 xong: 6 model train xong, unit test toán học pass (gradient check, AdamW parity, BPE roundtrip, SDPA parity).
2. Metric đạt ngưỡng bảng §1 @evaluation_plan.md — hoặc không đạt thì ghi số thật + limitation, được duyệt bởi chủ dự án (không âm thầm hạ ngưỡng).
3. Checkpoint 6 model + config + seed nằm trong `data/manifests/`, load lại được.
4. **T1.8 (chuyển từ T2.6 lên):** inference-service FastAPI :8001 nạp 6 checkpoint THẬT, đủ 6 endpoint + `/health` + GPU queue + Bearer key, trả đúng schema bảng 2.4 — đo VRAM ≤ 4GB. Đây là sản phẩm bàn giao của phase AI: các phần sau chỉ việc gọi.

*(Đã bỏ 2026-10-26: luật cũ "chỉ Phase 0 được chen lúc GPU bận train; CẤM Phase 2/3 trước AI-GATE" — thay bằng 2 làn song song ở trên.)*

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

> **Từ 2026-10-26:** mỗi task gắn `[LÀN·STATUS]` (CLAUDE | CODEX; DONE | IN_PROGRESS | PARTIAL | BLOCKED | TODO). Trạng thái **sống** ở `coordination/claude/TASKS.md` và `coordination/codex/TASKS.md`; mục này chỉ cập nhật trong release commit (`coordination/README.md` mục 6), mỗi làn chỉ sửa dòng có tag làn mình. Tick `[x]` chỉ khi có bằng chứng kiểm thử (kiểm kê: `coordination/INVENTORY_2026-10-26.md`).

### Phase 0 — Contract & Hạ tầng (W1, song song R&D)
- [x] **[CODEX·DONE]** T0.1 docker-compose: postgres, mongo, milvus, kafka, minio, redis
- [x] **[CODEX·DONE]** T0.2 Migration SQL đầy đủ (@database_schema.md sau bổ sung) + seed categories + admin user + seed `system_settings` (threshold 75/65, AI_SERVICE_KEY)
- [x] **[CODEX·DONE]** T0.3 Skeleton gateway + inference-service với endpoint stub trả mock đúng schema → FE code được ngay từ W1 (OpenAPI `infra/openapi.yaml` + gateway Go stub `backend/` 39 path build+run OK + inference-service stub)
- [x] **[CODEX·DONE]** T0.4 Sinh TypeScript types từ OpenAPI → `cms/src/api-types.ts`, `client/src/api-types.ts`

### Phase 1 — AI Core (W1–W6 GPU tuần tự, chi tiết @01_ai_core_plan.md)
- [x] **[CLAUDE·DONE]** T1.1 (W1) primitives + optim + tokenizer + unit tests toán học (gradient check, AdamW parity, BPE roundtrip, SDPA parity)
- [x] **[CLAUDE·DONE]** T1.2 (W1–2) data pipeline: thu thập video, tool gán nhãn, weak-label highlight bằng audio cross-correlation — **T1.2a–d XONG** (80 trận/160 hiệp, 442.998 keyframe, 155 WAV, nhãn/giây {0,1,-1}); **T1.2e XONG**: `ai_core/scripts/label_tool.py` stdlib `http.server :8010`, `GET /api/videos` + `POST /api/labels` ghi `categories.json` + `highlight/{id}.json`, smoke `category+highlight` roundtrip ✓
- [x] **[CLAUDE·DONE]** T1.3 (W2) train ViT + Siamese → checkpoint + báo cáo metric (@evaluation_plan.md) — **phạm vi ViT MVP đã chốt:** `bong_da`, `the_thao`, `ca_nhac`, `tin_tuc`; Siamese Recall@10 0.804 (≥0.80) vs 0.095/0.226; ViT 3 seed Top-1 mean 74.30%±4.96% (best s1338 79.81%) vs LogReg 61.70%/KNN 58.14%; ckpt `vit/best.pt` (s1338, 5.07M) + `siamese/best.pt` đã nạp inference-service ✓
- [x] **[CLAUDE·DONE · AI-02]** T1.4 (W3–4) train ASR CTC (chạy đêm) — test VIVOS chính thức (760 câu, 19 người nói khác hẳn): **CER 0.1347** (≤0.20), **WER 0.3581** (≤0.45); 20.000 step ở 1.91 step/s, loss 8.185→0.274, val WER còn đang giảm khi hết step (kernel v30)
  Follow-up T1.4/T1.6 sau 2026-10-15 (ASR robust/domain, MiniGPT aligned/replay/real-domain, Whisper review, label contract) → đã chuyển nguyên văn sang `coordination/claude/TASKS.md` mục Lịch sử (2026-10-26); trạng thái sống: AI-02, AI-03.
- [x] **[CLAUDE·DONE]** T1.5 (W4) train Highlight Fusion + ablation visual/audio/fusion — **DoD ĐẠT ở vòng 5** (140 trận/273 hiệp, tập test mới): gộp 3 seed F1 test 0.2632, vượt RMS +0.119 (bootstrap theo trận CI95 [+0.070, +0.166], P(≥0.10)=0.79) và frame-diff +0.158 (CI95 [+0.122, +0.200]) (@docs/T1.5_bao_cao.md §6g). Lịch sử: vòng 3 F1 test 0.1528±0.0116, vượt baseline +0.0491 (cần +0.10); kèm sweep 6 thiết kế nhãn cho thấy ngưỡng +0.10 phụ thuộc mạnh vào thiết kế nhãn (@docs/T1.5_bao_cao.md); **T1.5e ablation ĐẠT**: fusion vượt cả hai đơn phương thức — visual +0.0510 (p 0.0002), audio +0.0254 (p 0.0058), fusion 7 seed; 2 đối chứng khớp dung lượng cho thấy 3× tham số cho nhánh đơn chỉ được −0.0006/−0.0028 nên đóng góp đến từ modality chứ không từ dung lượng
- [ ] **[CLAUDE·PARTIAL · AI-03]** T1.6 (W5–6) Mini-GPT — **T1.6a/b DONE, NEWS TRAIN/EVAL ROUGE-L PASS, T1.6e DONE LOCAL TECHNICAL (2026-10-15)**. News76k/4k/1k; T4 clean16000+ASR4000/3.038h, bestASR3000 theo val. Frozen test1000 RL0.202308 vsLead-1 0.187109, delta+0.015199/CI95[+0.003965,+0.026687]. News active local Docker (old weights backed up), trained EOS512/96/noBOS +CTC case normalization, recursive map-reduce1120tokens API/direct3format PASS. Python37+1skip, Go/CMS/Client FULL, Playwright3 PASS(37.2s),6real/no stub healthy. **Full DoD NOT MET — SHARED HUMAN MEAN1.6/5<3 (2026-10-15)**: đã tải10 CC YouTube video/6kênh/133.36phút, giữ original+provenance trên `D:/data_training_ai/minigpt_real_video_20261015`;30 frozen60s clips→actual ASR→MiniGPT; user báo3người điểm giống nhau, nộp30scores ở notes file1:25×1/1×3/4×5,mean1.6/5,5of30≥3; giữ raw+normalized riêng, không nhân bản3phiếu/không kiểm chứng độc lập90records. Shared report @docs/T1.6_real_video_shared_human_results.json;0of30reference người chép, chưa CER/WER video; diagnostic VIVOS30 macroWER35.3647%/CER13.9602%,3utterance audio/mel/direct/API parity PASS,MiniGPT nhận3reference đúng vẫn bịa/lặp: không chỉ lỗi ASR; @docs/T1.4_asr_diagnostic.md. User cho phép riêng pretrained draft3mẫu: Whisper small CPU INT8 62.062s, TXT/SRT/JSON/CSV/review trênD:,0human-verified, không train/thaymodel; @docs/T1.4_pretrained_drafts.md. Không suy điểm từ ROUGE; raw/derived SHA+ZIP/browser playback+8scorer tests+Go/CMS/Client FULL PASS; ASR nhiễu/summary lặp trên video thật, xem `docs/T1.6_real_video_evaluation.md`; model còn bịa/lặp, CUDA VRAM chưa đo. WikiFAIL history @docs/T1.6_bao_cao.md; News eval @docs/T1.6c_news_evaluation.md; local integration @docs/T1.6e_bao_cao.md.
- [x] **[CLAUDE·DONE]** T1.7 (W6) train Two-Tower (MovieLens + onboarding) — NDCG@10 0.0990±0.0026 vs pop 0.0760 (3 seed; kernel v27 tái lập đúng số v14), 2.624 vector 128-d → Milvus IP, endpoint recommendation 10 ms (@docs/T1.7_bao_cao.md §10)
- [ ] **[CLAUDE·PARTIAL · VRAM chưa đo → AI-04]** T1.8 (W6) inference-service :8001 nạp 6 checkpoint thật + GPU queue + Bearer key + /health — **release #2 (2026-10-26):** runtime :8001 UP (AI-07), AI-API v1.2: 6 endpoint API_READY, recommendation DRAFT (D14); smoke :8001 6/6, inference 51 PASS, ai-core 285 PASS; `/health.dependencies`, degraded đúng ngữ nghĩa (AI-10); vision `video_id` (AI-11). Chưa tick: VRAM ≤4 GB chưa đo (CPU-only) → AI-04 / RTX 3060. Chi tiết `coordination/claude/TASKS.md`.

### Phase 2 — Backend (W3–5, chi tiết @02_backend_plan.md)
- [x] **[CODEX·DONE]** T2.1 Hexagonal shared: entities, ports, adapters + mock adapters cho unit test
- [x] **[CODEX·DONE]** T2.2 Auth service (JWT + refresh rotation + user_sessions)
- [x] **[CODEX·DONE]** T2.3 Ingest worker (Decord 1fps + wav) + orchestrator (Kafka chain gọi 6 AI endpoint)
- [x] **[CODEX·DONE]** T2.4 FFmpeg cutter worker (`-ss -to -c copy`)
- [ ] **[CODEX·PARTIAL · memory adapter → INT-02/INT-03]** T2.5 Toàn bộ endpoint 2.1–2.3 thay stub bằng thật + Redis cache (feed, search)
- [x] **[—]** ~~T2.6~~ → đã chuyển thành T1.8 (AI-FIRST, mục 0). Phase 2 chỉ còn tiêu thụ :8001 có sẵn.

### Phase 3 — Frontend (W5–7, chi tiết @03_cms_ui_plan.md, @04_client_ui_plan.md)
- [ ] **[CODEX·PARTIAL · INT-05]** T3.1 CMS: 10 màn (login, dashboard, upload/queue, video list, highlight review, **subtitle+summary gộp 1 màn 3 cột theo Stitch**, clips/thư viện xuất bản, categories, users, **settings — tab Cấu hình AI**). **UI IMPLEMENTED / VERIFIED — 2026-10-14; Design Parity FULL còn PARTIAL**: đã sửa toàn CMS, SVG/fonts local, responsive, form/toast/heatmap; 30 case Playwright PASS (28 UI + 2 AI thật/MinIO), Go vet/test/build + CMS build + Client tsc/Next --no-lint PASS; CMS đã rebuild. Chưa tick DONE vì thiếu contract/backend nguồn phát video gốc/metadata/analytics/rules/editor fields và Settings chưa persist. Báo cáo + screenshot: `docs/T3.1_cms_design_parity.md`; theo dõi `.claude/TodoWrite.md`. Design reference: `stitch_ai_video_cms/` + CẮT-list @03_cms_ui_plan.md mục 7
- [ ] **[CODEX·PARTIAL · INT-06]** T3.2 **UI IMPLEMENTED / VERIFIED (2026-10-14); DESIGN PARITY FULL = PARTIAL**. Client: 8 màn (auth, onboarding, feed, video detail, visual search, text search, profile, **discovery**). Design reference: `stitch_ai_video_platform_vietnamese/` + CẮT-list @04_client_ui_plan.md mục 8. Client Docker :3000, **42 Playwright PASS** gồm flow AI thật + video playback/seek; Go/CMS/Client full lint/build PASS. Thiếu URL video gốc/saved-list/analytics API; chưa tick DONE 100%. Báo cáo `docs/T3.2_client_design_parity.md`.

### Phase 4 — Tích hợp & Tối ưu (W7–8)
- [x] **[CODEX·DONE]** T4.1 E2E: upload → processed → duyệt → publish → hiện feed (test tự động Playwright) — **DONE — REAL UPLOAD/AI FLOW**: Nginx/gateway 2 GiB file; PostgreSQL/Mongo/MinIO/Kafka/Redis thật; PyAV ingest; Vision/ASR/Fusion/Mini-GPT checkpoint thật **CPU**, không silent fallback. Playwright **2 passed (21.7s)** với file >16 MiB, clip MinIO 206; persistence sau gateway restart PASS (sample `vid_dm3nf6fi23us`). Go vet/test/build + PG/Mongo integration + Python 19 tests + CMS tsc/Vite + Client tsc/Next --no-lint PASS. **Limitation:** chưa test toàn file 2 GiB/VRAM/leak; Mini-GPT T1.6c quality FAIL giữ nguyên; Siamese/Milvus/vector recommendation, một số memory adapter/player UX chưa hoàn thiện. Chi tiết `docs/T4.1_bao_cao.md`; todo `.claude/TodoWrite.md`. T4.2/T4.3 chưa bắt đầu.
- [x] **[CODEX·DONE]** T4.2 **DONE — REAL VISUAL SEARCH / LOCAL VALIDATED (2026-10-14)**. Siamese 128d checkpoint thật → Milvus COSINE/HNSW (M=16, efConstruction=200, ef100), auto index + backfill; thumbnail MinIO thật; Redis TTL120s/revision và processed+published filter kể cả cache hit. HTTP 20 misses p95 86,30ms/max97,54ms; 20 hits p95 51,51ms/max51,59ms. HNSW exact-cosine ANN Recall@10=1,0/p95 4,89ms, index Finished; 18 live vectors còn sau repeat backfill/recreate. Go/CMS/Client FULL checks PASS; Python 23+1 PASS; Playwright 3 PASS (40,6s) trên bản cuối. **Limitation:** CPU/corpus local nhỏ, chưa load/GPU; top100 rồi lọc có thể thiếu hit khi private frames lấn át; Two-Tower và T3 API gaps chưa đóng. `docs/T4.2_bao_cao.md` / `.claude/TodoWrite.md`. T4.3 chưa bắt đầu.
- [ ] **[CLAUDE·PARTIAL · GPU → AI-04]** T4.3 **PARTIAL — CPU MEMORY VERIFIED / GPU VRAM NOT MEASURED (2026-10-14)**. Fix GPUQueue giữ last fn/fut/result (weakref FAIL trước/PASS sau). CPU 2 warmup +20/20 video8–10s thật tuần tự PASS (3,0m), không GC/empty_cache/restart: inference median RSS569,26→569,87MiB (+0,61), peak589,51MiB; gateway +0,11MiB/ingest −15,25MiB. Python27 PASS +1 opt-in skip; Go/CMS/Client FULL checks PASS; 3 real E2E regression PASS (46,7s). **GPU còn thiếu:** máy chỉ nhận Intel UHD630, Docker CUDA probeexit125/no adapters; VRAM0 CPU không PASS4GiB. CUDA override/config đã chuẩn bị/validate, chưa build/execution GPU. Báo cáo `docs/T4.3_bao_cao.md`, hardware/metrics JSON và `.claude/TodoWrite.md`. Không tick DONE; hoàn tất GPU T4.3 trước T5.1.

### Phase 5 — Kiểm thử & Bàn giao (W9–12)
- [ ] **[CODEX·BLOCKED ⇐ AI-04 · INT-07]** T5.1 Load test 50 video dồn hàng đợi (tiêu chí @roadmap.md đã sửa)
- [ ] **[CODEX·BLOCKED ⇐ INT-07 · INT-08]** T5.2 Soak test 48h + fix bug
- [ ] **[CLAUDE+CODEX·TODO · AI-05 / INT-09]** T5.3 Docs bàn giao + số liệu evaluation cho luận án

**Thứ tự (sửa 2026-10-26 theo mục 0 — 2 làn):** làn Claude đi theo dependency T1.x và AI-GATE; làn Codex làm song song T2–T5 trên mock hoặc :8001 thật, chỉ DONE tích hợp khi endpoint `API_READY` + integration test thật PASS; T5.1/T5.2 chờ AI-04 (VRAM GPU).

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
Mỗi task xong phải báo 5 dòng (dòng `Lane` thêm 2026-10-26):

```text
Lane: claude|codex
Changed: <files>
Verified: <commands>
Contract touched: yes/no
Next safe task: <task id>
```

Nếu build/test chưa chạy được, task chưa xong.
