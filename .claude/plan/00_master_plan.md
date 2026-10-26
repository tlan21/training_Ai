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
- [x] T0.1 docker-compose: postgres, mongo, milvus, kafka, minio, redis
- [x] T0.2 Migration SQL đầy đủ (@database_schema.md sau bổ sung) + seed categories + admin user + seed `system_settings` (threshold 75/65, AI_SERVICE_KEY)
- [x] T0.3 Skeleton gateway + inference-service với endpoint stub trả mock đúng schema → FE code được ngay từ W1 (OpenAPI `infra/openapi.yaml` + gateway Go stub `backend/` 39 path build+run OK + inference-service stub)
- [x] T0.4 Sinh TypeScript types từ OpenAPI → `cms/src/api-types.ts`, `client/src/api-types.ts`

### Phase 1 — AI Core (W1–W6 GPU tuần tự, chi tiết @01_ai_core_plan.md)
- [x] T1.1 (W1) primitives + optim + tokenizer + unit tests toán học (gradient check, AdamW parity, BPE roundtrip, SDPA parity)
- [x] T1.2 (W1–2) data pipeline: thu thập video, tool gán nhãn, weak-label highlight bằng audio cross-correlation — **T1.2a–d XONG** (80 trận/160 hiệp, 442.998 keyframe, 155 WAV, nhãn/giây {0,1,-1}); **T1.2e XONG**: `ai_core/scripts/label_tool.py` stdlib `http.server :8010`, `GET /api/videos` + `POST /api/labels` ghi `categories.json` + `highlight/{id}.json`, smoke `category+highlight` roundtrip ✓
- [x] T1.3 (W2) train ViT + Siamese → checkpoint + báo cáo metric (@evaluation_plan.md) — **phạm vi ViT MVP đã chốt:** `bong_da`, `the_thao`, `ca_nhac`, `tin_tuc`; Siamese Recall@10 0.804 (≥0.80) vs 0.095/0.226; ViT 3 seed Top-1 mean 74.30%±4.96% (best s1338 79.81%) vs LogReg 61.70%/KNN 58.14%; ckpt `vit/best.pt` (s1338, 5.07M) + `siamese/best.pt` đã nạp inference-service ✓
- [x] T1.4 (W3–4) train ASR CTC (chạy đêm) — test VIVOS chính thức (760 câu, 19 người nói khác hẳn): **CER 0.1347** (≤0.20), **WER 0.3581** (≤0.45); 20.000 step ở 1.91 step/s, loss 8.185→0.274, val WER còn đang giảm khi hết step (kernel v30)
  ASR robustness follow-up **TRAIN/EVAL DONE — VIDEO VALIDATION PENDING (xác nhận2026-10-19)**: Kaggle ai-core-asr-robust v2 COMPLETE, TeslaT4/FP16/seed1337/4000steps, best3500 theo validation; output đã tải trênD:/data_training_ai/asr_robust/outputs-v2. Paired test VIVOS760: WER36.0519→32.9727%/CER13.5446→12.4467% (PASS20/45); FLEURS857: WER76.7465→53.6727%/CER50.5133→23.9063%, vẫn lỗi cao. VIVOS+human FLEURS train≈22.0073h/13557mẫu sau4CTC exclusions, không dùngYouTube30/Whisper drafts; head93→133 giữ prefix, encoder/loss không đổi. Full logs4sanity+step1→4000, checkpoint/config/metric arithmetic/hashes verified; trainVRAM allocated1.203/reserved3.039GiB≤8, chưa chứng nhận inference4GiB. Candidate SHA d03ef0a962220618e90e5ff478a2fbab5ff35dd68deb539a4933eb7c15a4f3de, chưa deploy; activeASR/MiniGPT giữ nguyên. Chỉ1seed, human video refs0/30; fullT1.6 human quality chưa đánh giá lại. @docs/T1.4_asr_robust_training.md; @data/manifests/asr_robust_training.json.
  Real-video paired pilot **DONE TECHNICAL / HUMAN REFERENCES PENDING (2026-10-19)**: sample_01/10/28×ASR cũ/candidate→cùngMiniGPT,6ASR+6summary nonempty, oldASR text3/3 khớp frozen; production helpers/20s/CPUFP32/Torch2.13/temp0/max96, không deploy. Packet D:/data_training_ai/minigpt_real_video_20261015/asr_candidate_comparison_3_20261019/review.html có video/side-by-side/form lời chuẩn+exportCSV riêng; model/media/ref/ratings SHA giữ nguyên. 3tests+browser playback/exportCSV Unicode/desktop+mobile/QC+Go/CMS/Client FULL PASS. Candidate còn transcript nhiễu; MiniGPT vẫn lặp/thêm chi tiết ngoài transcript. Humanrefs0/3 và0/30, CER/WER/điểm human mới null; sharedmean1.6/5/fullT1.6 chưa đổi. @docs/T1.4_asr_candidate_video_pilot.md.
  User feedback + direct-draft control (2026-10-19): user xác nhận đúng nội dung3draft; candidate-ASR MiniGPT card1/3sai,card2đúng. Chạy trực tiếp chính3draft→cùngMiniGPT/temp0/max96 vẫn lỗi: sample10lặp an ninh, sample28lệch tiểu sửNewton;3outputs tái lập cached summaries. Giữ rawfeedback+scopedjudgments, không suy thành điểm1–5/rawASRaccuracy/CER-WERđộc lập; không train/deploy hoặc sửa original refs/weights. @docs/T1.6_confirmed_draft_diagnostic.md.
  MiniGPT pipeline diagnostic **DONE (2026-10-19)**:3draft222/250/271BPEtokens<411, lỗi xảy ra single-pass. Real BPE prefix253train+8val/mask-EOS8val/cachefullforward8steps PASS; audit256train/253sum:144source và11target bị cắt. Train75581sum/303581instances nhưng checkpoint selection chỉ titleROUGE; fixedval129–136sumRL0.174967 vsLead0.209702 (8mẫu chẩn đoán, không globalmetric),3longinputs rawtoken coverage PASS nhưng1reduce lặp94.68%trigram; short inputs vẫn sai ngày/số/entity. No test tuning/weight/production/contract change;16Python tests+4subtests, Go/CMS/Client PASS; Docker engine off. Next: grounded human target dataset/complete labels +sum-based selection +separate long-input quality, chưa tự train/deploy; fullT1.6 vẫn FAIL. @docs/T1.6_pipeline_diagnostic.md; @data/manifests/minigpt_pipeline_diagnostic.json.
  Summary data/recipe **PREPARATION DONE — LABEL AUDIT PENDING (2026-10-19)**: strictscreen76k/4k→391/24; pinnedrawprefix197135rows adds593/40, final984train/64val, preserve originalsplits/reservehash95/5/exclude1000frozenIDs fromIDindex only. Editorialbody/sapo +syntheticASR, no generated/video-test labels/source-target truncation. New opt-in sum-aligned-v1 chooses pairedclean/noisy sumRL, title/cap regression;4clean+1noisypasses=248/62steps/eval62, legacyprofile unchanged. Existingcheckpoint baseline64cases cleanRL0.290132 vsLead0.407114, noisy0.175906 vs0.115482, mean0.233019 (developmentonly/noimprovementclaim). 8384itemchecks/4productionparity/31tests+4subtests/Go/CMS/Client PASS. 48blankauditrows gate training; privatebundle/codezip/owninitcopy verified, noKagglejob/deploy/model/APIchange. Next: human label audit +resolve/reversion/provenance, then smallcandidate train; realtranscriptdomaintransfer unproven/fullT1.6 stillFAIL. @docs/T1.6_aligned_summary_preparation.md; @data/manifests/minigpt_aligned_summary.json.
  Label preflight follow-up **V2 DATA DONE / HUMAN AUDIT PENDING (2026-10-19)**: previous ending check admitted terminal ../.../Unicode ellipsis; corrected shared filter/trainer gate rejects50train+3val. V2=956train/64val, all53 excluded, retained IDs keep split/61val retained+3new, original files/hashes preserved. 4CPU sanity items+41tests/4subtests+8160encodedchecks/4productionparity+Go/CMS/Client PASS. Unchanged checkpoint baseline cleanSumRL0.294504 vsLead0.415168/noisy0.173516 vs0.114252; no trained improvement claim. Budget240/60/eval60. Mechanical evidence48 stored separately, no human verdicts filled;48blankannotations still gate candidate training. No job/deploy/model/API/frozen-eval change; fullT1.6 stillFAIL. @docs/T1.6_label_preflight.md; @data/manifests/minigpt_label_preflight.json.
- [x] T1.5 (W4) train Highlight Fusion + ablation visual/audio/fusion — **DoD ĐẠT ở vòng 5** (140 trận/273 hiệp, tập test mới): gộp 3 seed F1 test 0.2632, vượt RMS +0.119 (bootstrap theo trận CI95 [+0.070, +0.166], P(≥0.10)=0.79) và frame-diff +0.158 (CI95 [+0.122, +0.200]) (@docs/T1.5_bao_cao.md §6g). Lịch sử: vòng 3 F1 test 0.1528±0.0116, vượt baseline +0.0491 (cần +0.10); kèm sweep 6 thiết kế nhãn cho thấy ngưỡng +0.10 phụ thuộc mạnh vào thiết kế nhãn (@docs/T1.5_bao_cao.md); **T1.5e ablation ĐẠT**: fusion vượt cả hai đơn phương thức — visual +0.0510 (p 0.0002), audio +0.0254 (p 0.0058), fusion 7 seed; 2 đối chứng khớp dung lượng cho thấy 3× tham số cho nhánh đơn chỉ được −0.0006/−0.0028 nên đóng góp đến từ modality chứ không từ dung lượng
- [ ] T1.6 (W5–6) Mini-GPT — **T1.6a/b DONE, NEWS TRAIN/EVAL ROUGE-L PASS, T1.6e DONE LOCAL TECHNICAL (2026-10-15)**. News76k/4k/1k; T4 clean16000+ASR4000/3.038h, bestASR3000 theo val. Frozen test1000 RL0.202308 vsLead-1 0.187109, delta+0.015199/CI95[+0.003965,+0.026687]. News active local Docker (old weights backed up), trained EOS512/96/noBOS +CTC case normalization, recursive map-reduce1120tokens API/direct3format PASS. Python37+1skip, Go/CMS/Client FULL, Playwright3 PASS(37.2s),6real/no stub healthy. **Full DoD NOT MET — SHARED HUMAN MEAN1.6/5<3 (2026-10-15)**: đã tải10 CC YouTube video/6kênh/133.36phút, giữ original+provenance trên `D:/data_training_ai/minigpt_real_video_20261015`;30 frozen60s clips→actual ASR→MiniGPT; user báo3người điểm giống nhau, nộp30scores ở notes file1:25×1/1×3/4×5,mean1.6/5,5of30≥3; giữ raw+normalized riêng, không nhân bản3phiếu/không kiểm chứng độc lập90records. Shared report @docs/T1.6_real_video_shared_human_results.json;0of30reference người chép, chưa CER/WER video; diagnostic VIVOS30 macroWER35.3647%/CER13.9602%,3utterance audio/mel/direct/API parity PASS,MiniGPT nhận3reference đúng vẫn bịa/lặp: không chỉ lỗi ASR; @docs/T1.4_asr_diagnostic.md. User cho phép riêng pretrained draft3mẫu: Whisper small CPU INT8 62.062s, TXT/SRT/JSON/CSV/review trênD:,0human-verified, không train/thaymodel; @docs/T1.4_pretrained_drafts.md. Không suy điểm từ ROUGE; raw/derived SHA+ZIP/browser playback+8scorer tests+Go/CMS/Client FULL PASS; ASR nhiễu/summary lặp trên video thật, xem `docs/T1.6_real_video_evaluation.md`; model còn bịa/lặp, CUDA VRAM chưa đo. WikiFAIL history @docs/T1.6_bao_cao.md; News eval @docs/T1.6c_news_evaluation.md; local integration @docs/T1.6e_bao_cao.md.
- [x] T1.7 (W6) train Two-Tower (MovieLens + onboarding) — NDCG@10 0.0990±0.0026 vs pop 0.0760 (3 seed; kernel v27 tái lập đúng số v14), 2.624 vector 128-d → Milvus IP, endpoint recommendation 10 ms (@docs/T1.7_bao_cao.md §10)
- [x] T1.8 (W6) inference-service :8001 nạp 6 checkpoint thật + GPU queue + Bearer key + /health — 6 ckpt `ai-core/checkpoints/{vit,siamese,asr_ctc,highlight_fusion,minigpt,two_tower}/best.pt` smoke `TestClient health→stub_mode False`, `/v1/vision`+`/v1/completions` 200, thiếu Bearer→401; `pytest 14 passed`; local CPU (không đo VRAM ≤4GB) ✓

### Phase 2 — Backend (W3–5, chi tiết @02_backend_plan.md)
- [ ] T2.1 Hexagonal shared: entities, ports, adapters + mock adapters cho unit test
- [ ] T2.2 Auth service (JWT + refresh rotation + user_sessions)
- [ ] T2.3 Ingest worker (Decord 1fps + wav) + orchestrator (Kafka chain gọi 6 AI endpoint)
- [ ] T2.4 FFmpeg cutter worker (`-ss -to -c copy`)
- [ ] T2.5 Toàn bộ endpoint 2.1–2.3 thay stub bằng thật + Redis cache (feed, search)
- [ ] ~~T2.6~~ → đã chuyển thành T1.8 (AI-FIRST, mục 0). Phase 2 chỉ còn tiêu thụ :8001 có sẵn.

### Phase 3 — Frontend (W5–7, chi tiết @03_cms_ui_plan.md, @04_client_ui_plan.md)
- [ ] T3.1 CMS: 10 màn (login, dashboard, upload/queue, video list, highlight review, **subtitle+summary gộp 1 màn 3 cột theo Stitch**, clips/thư viện xuất bản, categories, users, **settings — tab Cấu hình AI**). **UI IMPLEMENTED / VERIFIED — 2026-10-14; Design Parity FULL còn PARTIAL**: đã sửa toàn CMS, SVG/fonts local, responsive, form/toast/heatmap; 30 case Playwright PASS (28 UI + 2 AI thật/MinIO), Go vet/test/build + CMS build + Client tsc/Next --no-lint PASS; CMS đã rebuild. Chưa tick DONE vì thiếu contract/backend nguồn phát video gốc/metadata/analytics/rules/editor fields và Settings chưa persist. Báo cáo + screenshot: `docs/T3.1_cms_design_parity.md`; theo dõi `.claude/TodoWrite.md`. Design reference: `stitch_ai_video_cms/` + CẮT-list @03_cms_ui_plan.md mục 7
- [ ] T3.2 **UI IMPLEMENTED / VERIFIED (2026-10-14); DESIGN PARITY FULL = PARTIAL**. Client: 8 màn (auth, onboarding, feed, video detail, visual search, text search, profile, **discovery**). Design reference: `stitch_ai_video_platform_vietnamese/` + CẮT-list @04_client_ui_plan.md mục 8. Client Docker :3000, **42 Playwright PASS** gồm flow AI thật + video playback/seek; Go/CMS/Client full lint/build PASS. Thiếu URL video gốc/saved-list/analytics API; chưa tick DONE 100%. Báo cáo `docs/T3.2_client_design_parity.md`.

### Phase 4 — Tích hợp & Tối ưu (W7–8)
- [x] T4.1 E2E: upload → processed → duyệt → publish → hiện feed (test tự động Playwright) — **DONE — REAL UPLOAD/AI FLOW**: Nginx/gateway 2 GiB file; PostgreSQL/Mongo/MinIO/Kafka/Redis thật; PyAV ingest; Vision/ASR/Fusion/Mini-GPT checkpoint thật **CPU**, không silent fallback. Playwright **2 passed (21.7s)** với file >16 MiB, clip MinIO 206; persistence sau gateway restart PASS (sample `vid_dm3nf6fi23us`). Go vet/test/build + PG/Mongo integration + Python 19 tests + CMS tsc/Vite + Client tsc/Next --no-lint PASS. **Limitation:** chưa test toàn file 2 GiB/VRAM/leak; Mini-GPT T1.6c quality FAIL giữ nguyên; Siamese/Milvus/vector recommendation, một số memory adapter/player UX chưa hoàn thiện. Chi tiết `docs/T4.1_bao_cao.md`; todo `.claude/TodoWrite.md`. T4.2/T4.3 chưa bắt đầu.
- [x] T4.2 **DONE — REAL VISUAL SEARCH / LOCAL VALIDATED (2026-10-14)**. Siamese 128d checkpoint thật → Milvus COSINE/HNSW (M=16, efConstruction=200, ef100), auto index + backfill; thumbnail MinIO thật; Redis TTL120s/revision và processed+published filter kể cả cache hit. HTTP 20 misses p95 86,30ms/max97,54ms; 20 hits p95 51,51ms/max51,59ms. HNSW exact-cosine ANN Recall@10=1,0/p95 4,89ms, index Finished; 18 live vectors còn sau repeat backfill/recreate. Go/CMS/Client FULL checks PASS; Python 23+1 PASS; Playwright 3 PASS (40,6s) trên bản cuối. **Limitation:** CPU/corpus local nhỏ, chưa load/GPU; top100 rồi lọc có thể thiếu hit khi private frames lấn át; Two-Tower và T3 API gaps chưa đóng. `docs/T4.2_bao_cao.md` / `.claude/TodoWrite.md`. T4.3 chưa bắt đầu.
- [ ] T4.3 **PARTIAL — CPU MEMORY VERIFIED / GPU VRAM NOT MEASURED (2026-10-14)**. Fix GPUQueue giữ last fn/fut/result (weakref FAIL trước/PASS sau). CPU 2 warmup +20/20 video8–10s thật tuần tự PASS (3,0m), không GC/empty_cache/restart: inference median RSS569,26→569,87MiB (+0,61), peak589,51MiB; gateway +0,11MiB/ingest −15,25MiB. Python27 PASS +1 opt-in skip; Go/CMS/Client FULL checks PASS; 3 real E2E regression PASS (46,7s). **GPU còn thiếu:** máy chỉ nhận Intel UHD630, Docker CUDA probeexit125/no adapters; VRAM0 CPU không PASS4GiB. CUDA override/config đã chuẩn bị/validate, chưa build/execution GPU. Báo cáo `docs/T4.3_bao_cao.md`, hardware/metrics JSON và `.claude/TodoWrite.md`. Không tick DONE; hoàn tất GPU T4.3 trước T5.1.

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

Follow-up 2026-10-19 — **ALIGNED CANDIDATE TRAIN/EVAL DONE; ASR REGRESSION / NOT DEPLOYED**. User confirmed48v2 pairs via chat with exact ID/hash provenance;956train/64val, seed1337,240clean+60ASR,5validation rounds; private Kaggle ai-core-minigpt-aligned-v2 version1 COMPLETE, output downloaded/verified. Predeclared paired-mean selection chose clean180: clean ROUGE-L0.292511→0.517913, synthetic-ASR0.172177→0.114637; noisy repetition/cap hits increased. No quality PASS from mean improvement; fullT1.6 human gate unmet, shared1.6/5 unchanged. T4 allocated1.055/reserved2.520GiB,507.8s baseline+train/validation,4remote sanity+50local tests/4subtests+Go/CMS/Client PASS. Six post-selection video-control outputs still show ASR failure; no new human score. Candidate5cc63c... retained separately, activecf9cfa... unchanged. Report @docs/T1.6_aligned_training.md, curves/metrics/manifests updated. Next: mixed clean+ASR replay and per-condition non-regression guard; reuse unchanged48pair confirmation, no repeated audit. No new experiment launched; Docker engine unavailable/no liveE2E/six-model4GiB proof.

Follow-up 2026-10-19 — **MIXED REPLAY TRAIN/EVAL DONE; SUMMARY GUARD PASS / NOT DEPLOYED**. Same confirmed956/64 and48pair hashes; seed1337, microbatch4clean+4noisy/effective64,300updates/eval60. Private ai-core-minigpt-replay-v1 version1 COMPLETE;4remote sanity+62local Python tests+Go/CMS/Client PASS. Output/rawprediction means/IDs/checkpoint/config/guard/hashes verified. Only mixed300 eligible: clean ROUGE-L0.292511→0.475816, synthetic-ASR0.172177→0.186158, ASR repetition0.174653→0.162928, cap/EOS equal init. Higher-mean240 rejected for ASR repetition. Auxiliary titleRL0.356232→0.343602 regresses, outside summary guard. T4 runtime446.03s, peak allocated1.056/reserved1.805GiB≤8; not inference4GiB proof. Candidate70ec4790... retained separately, activecf9cfa... unchanged; fullT1.6 human gate unmet/shared1.6/5 unchanged. Report @docs/T1.6_mixed_replay.md, metrics/curves/manifest updated. Next: isolated real-ASR paired evaluation then fresh human ratings before promotion; no frozen-test tuning/repeated48pair audit. Docker engine off/no liveHTTP/E2E; no new real-video generation this task.

Follow-up 2026-10-19 — **MIXED CANDIDATE REAL-VIDEO PILOT DONE / ERRORS OBSERVED / NOT DEPLOYED**. User authorized continuation after training. Mixed300 SHA70ec4790... vs activecf9cfa...,3previously inspected clips×3exact inputs (confirmed draft/activeASR/candidateASR)×2models =18fresh nonempty summaries via production helper, CPUFP32/temp0/max96/18.734s. Active cache parity9/9, prior source/service/weights/frozen media/refs/ratings hashes unchanged; no newASR/train/tuning/human score. Still off-topic/repetitive on actualASR; confirmed Newton draft also fails. Summary proxy guard PASS does not establish real-video quality; do not promote, fullT1.6 human gate/shared1.6/5 unchanged. Reviewpacket onD:/data_training_ai/minigpt_news/mixed_replay_video_pilot_3_v1, escaping test+Playwright desktop/mobile3video playback/9pairs/no overflow+visualQC+Go/CMS/Client PASS. @docs/T1.6_mixed_video_pilot.md; @data/manifests/minigpt_mixed_video_pilot.json. Next: separate real-domain human-authored train/validation on new videos outside frozen30/3diagnostics; keep current48News confirmation, no pseudo-labeling of test clips or relaxed guard.

Follow-up 2026-10-19 — **REAL-DOMAIN DATA PREPARATION DONE / HUMAN LABELS0/40 / TRAIN GATE CLOSED**. User requested proposed new data. Downloaded20newCC videos/4new channels outside all10frozen source videos/6test channels, originals499544485bytes retained onD:/data_training_ai/minigpt_domain_v1_20261019. SeededID/channel grouping:15train videos/3channels→30clips;5val videos/1channel→10clips;40×30s=20min.40WAV/MP4 +80own-ASR inputs(active/candidate),0empty/0overbudget/max229prompt tokens, no human/generated-summary targets. Blank authoring page at localhost8890 withJSONexport/autosave, strictID/mediaSHA/attestation/complete-label/budget/disjoint gate; actualblank import rejected/noacceptedexport.20unit tests+Playwright desktop/mobile40cards/4representative playback/UTF8export/autosave/nooverflow+visualQC+Go/CMS/Client PASS. Frozen source/ref/ratings/production weight hashes unchanged; no train/deploy/externalmodel/Kaggleupload; prior48News confirmation retained. Next: humans write these new transcript-summary labels, import/review before bounded training; source-channel split is not verified speaker identity, smallmostly-news domain/near-dups not certified. @docs/T1.6_real_domain_preparation.md; @data/manifests/minigpt_real_domain.json. FullT1.6 human gate/shared1.6/5 unchanged.


- [x] Follow-up 2026-10-19 — **WHISPERWEB CONVERSION DONE, 40/40 DRAFTS; TRAINING NOT STARTED**. User replaced Clideo with WhisperWeb. Public free local browser workflow, whisper-base multilingual/Vietnamese, fixed configuration: 120 TXT/JSON/SRT exports for 40 new 30s clips (30train/10val), kept separately onD:/data_training_ai/minigpt_domain_v1_20261019/whisperweb_drafts_v1. All IDs/output hashes/TXT-JSON agreement,80clip hashes,7prep packet hashes and8frozen/active-weight hashes PASS; collector self-check +Go/CMS/Client checks PASS. 22clips have mechanical review flags (6unknown end,5repeated8word,14outside clip; overlap). External automatic drafts remain unverified, not human labels or summary targets; no gate bypass, train, deploy or weight/test changes. FullT1.6 quality gate/shared1.6/5 unchanged. Next: listen/correct with machine-assisted provenance and author summaries before separate label intake. Report @docs/T1.6_whisperweb_drafts.md; manifests @data/manifests/minigpt_whisperweb_drafts.json and minigpt_whisperweb_verification.json.

- [x] Follow-up 2026-10-20 — WHISPER REVIEW PREPROCESSING DONE. Prepared40editable Whisper transcripts/40blank summaries,22flagged-first, separate browser drafts and assisted-origin export at localhost8890/whisper_review_v1/index.html.21timing proposals across20clips/40derived SRTs; text/raw120exports/original packet/frozen data/weights unchanged.27unit tests, desktop/mobile browser and Go/CMS/Client builds PASS. No API change. Report @docs/T1.6_whisper_review.md; manifest @data/manifests/minigpt_whisper_review.json.
- [ ] Actual listening/corrections and human summaries remain pending: no direct audio-listening tool in this agent session, no invented semantic verification. Await reviewed_whisper_domain_v1.json, then separate intake preserving external-ASR provenance. No training/deploy or T1.6 quality-gate change.


- [x] Follow-up 2026-10-20 — REVIEW JSON RECEIVED AND ERROR AUDIT DONE. Exact73967-byte export SHA860f8068d0bd... saved in whisper_review_v1/received_860f8068d0bd;40IDs/source/media/copy/protected hashes PASS.40transcripts/39edits/37summaries/33feedback/0exported confirmations;31summary copies/25over95BPE/3blank. User error-review pass is received; no invented approval or WER/CER. Separate vocabulary audit: active93 lacksF/J/W/Z,9digits and punctuation; CharVocab silently drops unknown symbols. Candidate133 covers example identifiers but is not promoted. Reviewed page is Whisper-base Transcribe, not a paired project-ASR score or translation test. No code/API/weights/test/train change. Report @docs/T1.6_whisper_review_intake.md; manifest @data/manifests/minigpt_whisper_review_intake.json.
- [ ] Next: fix ASR label unknown-character handling and define English/number/identifier conventions before targeted supervised data and paired ASR evaluation; concise approved summaries are still required for MiniGPT domain training.


- [x] Follow-up 2026-10-20 — T1.4 STRICT LABEL ENCODING/PREFLIGHT DONE. SharedCharVocab rejects unsupported symbols instead of deleting them; alltrain labels validated before audio/model training. SharedReferenceASRDataset/raw-text metrics cover general/robust evaluation without dropping held-out symbols or growing vocabulary. Actual133symbol train13561/13561roundtrip;13557CTCfeasible/4existing exclusions retained;10567legacyVIVOS labels valid.3val/7testOOVlabels preserved; active93mixed training rejected before audio.80Python tests+Go/CMS/Client builds PASS; checkpoints/IDs/head/datasets/frozen tests/review hashes unchanged. Lossless label convention documented in dataset_spec3.3 and @docs/T1.4_asr_label_contract.md; proof @data/manifests/asr_label_preflight.json. No training, promotion, API change or acoustic quality claim.
- [ ] Next safe task: audio-backed supervised domain examples for English/code switching, numeric/legal identifiers, proper names and compounds; approved references and coverage/head checks before a new bounded ASR experiment. Previous40Whisper reviews remain diagnostic/unapproved, not autoaccepted targets.
