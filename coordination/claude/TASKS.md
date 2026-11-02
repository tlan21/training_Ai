# TASKS — làn Claude (AI) · branch `claude/ai-core`

Owner duy nhất: Claude. Codex chỉ đọc (`git show claude/ai-core:coordination/claude/TASKS.md`).
Định dạng + trạng thái: `coordination/README.md` mục 4. Kiểm kê gốc: `coordination/INVENTORY_2026-10-26.md`.

## Tổng quan

| ID | T gốc | Tên | Status | Depends on |
|---|---|---|---|---|
| AI-00 | — | Thiết lập tách làn + kiểm kê | DONE | — |
| AI-06 | T1.8 | **Ưu tiên 1** — Xác minh nguồn checkpoint + thang sẵn sàng 6 model | DONE (2026-10-26) | — |
| AI-01 | T1.8 | Phát hành AI API Contract v1 (API_READY) | DONE (2026-10-26, release #2 — hiệu lực khi lên master; recommendation DRAFT) | AI-06 |
| AI-10 | T1.8 | Health/degraded đúng ngữ nghĩa + dependency status + tự phục hồi (D15) | DONE (2026-10-26) | — |
| AI-07 | T1.8 | Vận hành runtime :8001 thật cho Codex gọi HTTP (+ sửa UTF-8 Windows) | DONE (2026-10-26; :8001 UP; ingest path ⇐ HC-05) | AI-10; Milvus stack Codex (UP) |
| AI-11 | T1.8 / T4.2 | HO-01: `video_id` tùy chọn cho Vision + index frame từ data URI 1 fps (contract minor) | DONE (2026-10-26) | HO-01 (Codex chọn HTTP media) |
| AI-13 | T1.7 / T1.8 | D18: recommendation inference không trả metadata giả + `recommendation_mode` | DONE (2026-10-26; release #3) | D18 |
| AI-14 | T1.8 | D24 bước 1: tách facade/worker trong inference-service (contract v1.3 không đổi) + worker từ xa (MODEL_WORKER_URL) + kernel Kaggle worker GPU | DONE (2026-10-30, release #5) | D24 (user 2026-10-29) |
| AI-15 | T1.8 | D24 bước 2: AI-API v2.0 (DRAFT) — AI trả vector/kết quả, Backend sở hữu MinIO/Milvus; v1.3 chạy song song; HC cho Codex | BLOCKED ⇐ RE:HC-13 E2E (phần AI xong 2026-10-29: v2.0 DRAFT, :8001 phục vụ /v1 + /v2) | AI-14; Codex (HC) cho phần backend |
| AI-16 | T1.5 / T1.8 | Highlight: (B) đối chiếu checkpoint active với vòng đạt DoD; (A) hậu xử lý đúng như lúc chấm (làm mượt k, τ); (C) luật clip (độ dài, nối, biên câu) | DONE (2026-10-30, release #5) | user 2026-10-29 |
| AI-17 | T1.5 | Fusion vòng 6: chuẩn hóa theo từng video + augment chống overfit; thay vòng 5 chỉ khi val ≥ 0.2750 và gap train−val < 0.205 | DONE (release #5; thay bởi vòng 7/8) | AI-16; user 2026-10-29 |
| AI-18 | T1.5 | Fusion vòng 7: giảm overfit bằng lr/weight decay/lịch ngắn; thay vòng 6 chỉ khi val ≥ 0.3053, gap < 0.1692, val loss < 1.2136 | DONE (release #5; thay bởi vòng 8 ×10) | AI-17 |
| AI-19 | T1.5 | (a) SỬA lỗi đặc trưng vision cho highlight (serve ViT ≠ train Siamese backbone); (b) dữ liệu tin tức 10 video gốc: feature + đề xuất + trang gán nhãn người → vòng 8 | DONE (2026-10-30; fix vision + nhãn tin tức đã intake) | user 2026-10-29 |
| AI-20 | T1.5 | Fusion vòng 8: bóng đá + tin tức (nhãn người), lặp tin tức ×1/×10/×30; thay vòng 7 chỉ khi val tin tức +0.05 và giữ bóng đá | DONE (2026-10-30; quy tắc → GIỮ vòng 7; ×10 hứa hẹn, cần dữ liệu tin tức độc lập) | AI-19 |
| AI-21 | T1.5 | Xác nhận vòng 8 ×10 trên test tin tức độc lập (kênh mới, nhãn mù); đổi khi test tin tức +0.05 và bóng đá ≥ −0.01 | DONE (2026-10-30, release #5; ×10 ACTIVE) | AI-20; user 2026-10-30 (hướng 1) |
| AI-22 | T1.8 | HO-04: runtime AI chính thức = container Docker (user 2026-11-02) — image bất biến từ source hiện hành (v1.4 + AI-19 + recipe) + bằng chứng readiness/parity checkpoint–source; Codex đổi tag compose (HC-16) | IN_PROGRESS (2026-11-02) | HO-04; Docker engine UP |
| AI-12 | T1.7 | D18-B: Two-Tower v2 cho sản phẩm (dữ liệu thật → train → quality gate → API) | BLOCKED ⇐ bundle INT-13 (phần độc lập xong 2026-10-26) | dữ liệu tương tác thật từ Codex (đề xuất INT-13) |
| AI-09 | T1.7 | Two-Tower phía AI: embedding, schema, export, version, kiểm thử dữ liệu; chỉ sandbox (D14) | DONE (2026-10-26; sandbox + artifact; product → AI-12 theo D18) | HC-04 (sandbox READY) |
| AI-02 | T1.4 | ASR domain: 02a đề xuất 53 clip · 02b người duyệt · 02c intake/train | 02a DONE (2026-10-27) · 02b BLOCKED · 02c BLOCKED | 02b ⇐ user; 02c ⇐ 02b |
| AI-03 | T1.6 | Mini-GPT: 03a Claude soạn summary 40 clip · 03b người duyệt · 03c train/eval | 03a DONE (2026-10-26) · 03b BLOCKED ⇐ user · 03c BLOCKED | 03b ⇐ user; 03c ⇐ 03b |
| AI-04 | T1.8 / T4.3 | Đo VRAM sơ bộ Kaggle T4 (PRELIMINARY) | DONE — PRELIMINARY_T4 (2026-10-26; nghiệm thu 3060 vẫn mở) | AI-06 (DONE) |
| AI-05 | T5.3 | Số liệu evaluation cho luận án | TODO | AI-02, AI-03, AI-04 |
| AI-08 | — | Dọn dẹp dữ liệu/artefact làn AI an toàn (lặp lại sau mỗi đợt train) | TODO (đợt #1 DONE 2026-10-26) | không job/server nào đang dùng; user duyệt danh sách |

Thứ tự đề xuất (tối đa 1 IN_PROGRESS, cập nhật D14–D17): AI-10 → AI-07 → release (user duyệt) → AI-01 công bố API_READY; song song khi chờ: AI-09 (phần không cần mapping: schema/version/test), AI-03a, AI-02a, AI-04.
AI-08 (dọn dẹp) chạy sau mỗi đợt train xong hoặc khi một ổ chạm `BLOCKED_RESOURCE`; luôn qua manifest + user duyệt.

Hoàn thành trước tách làn (bằng chứng ở INVENTORY mục 3, 5): T1.1, T1.2, T1.3, T1.4 (DoD metric), T1.5, T1.7 = DONE;
T1.6, T1.8, T4.3 = PARTIAL. Không tạo lại các task này.

Quyết định user 2026-10-26 áp dụng cho làn này: AI-02 (Claude chỉ chuẩn bị/đề xuất, không tự HUMAN_VERIFIED), AI-03 (Claude soạn 40 summary, lưu nguồn/bằng chứng/trạng thái duyệt, không dùng dữ liệu giả để DONE), AI-04 (Kaggle T4 chỉ là sơ bộ, không thay nghiệm thu RTX 3060), AI-06 (ưu tiên; phân biệt 4 mức sẵn sàng, không API_READY khi chưa kiểm chứng). Xem `coordination/PROJECT_STATUS.md` mục 5.

Nhãn kiểm duyệt dữ liệu (AI-02/AI-03): `MACHINE_DRAFT` (máy sinh: Whisper/ASR) · `CLAUDE_PROPOSED` (Claude đề xuất/soạn) · `HUMAN_VERIFIED` (chỉ user/người duyệt gán, có file export làm bằng chứng) · `REJECTED`.

---

### AI-00 — Thiết lập tách làn + kiểm kê
- T gốc: — | Owner: claude | Status: DONE
- Depends on: — | Blocks: mọi task AI-xx, INT-xx
- Acceptance: `coordination/**`, `AGENTS.md`, `.claude/CLAUDE.md`, master plan §0/§3 đồng bộ; 2 worktree/branch; kiểm kê có bằng chứng.
- Evidence: VERIFIED-NOW 2026-10-26 — ai-core 285 passed, inference 37 passed/1 skipped, 6 ckpt nạp thật, Go/CMS/Client build PASS (INVENTORY §1).
- Commits: commit baseline tách làn (`git log --grep "split lanes"`)
- Checkpoint: xem SESSION.md

### AI-01 — Phát hành AI API Contract v1
- T gốc: T1.8 | Owner: claude | Status: DONE (2026-10-26, release #2) — contract v1.2: 6 endpoint `API_READY` hiệu lực khi release #2 lên `master`
  (D16: code trên master + :8001 UP + smoke PASS); recommendation `DRAFT` (D14). Nếu user không duyệt push → quay lại REVIEW.
- Depends on: AI-06 | Blocks: INT-03 (DONE), mọi dòng `INTEGRATED_REAL` mới trong matrix Codex
- Acceptance:
  1. `coordination/claude/api/inference_openapi.json` export từ `app.main:app.openapi()` (không sửa tay).
  2. `coordination/claude/api/examples/<endpoint>.{request,response,error}.json` sinh từ chạy thật checkpoint thật cho 6 endpoint + `/health` (search/recommendation cần Milvus — chạy khi Codex bật stack, hoặc ghi rõ chưa có).
  3. `AI_API_CONTRACT.md` → v1.0: mọi endpoint có schema, ràng buộc chiều (vision 256-d, audio 64-d…), error codes, model + SHA256, `API_READY` cho endpoint đã có ví dụ thật.
  4. Smoke checkpoint thật đưa vào `inference-service/tests` (opt-in theo env) để release gate chạy lại được.
  5. Append bàn giao vào `coordination/claude/HANDOFF_OUT.md`.
- Evidence (VERIFIED-NOW 2026-10-26, chi tiết `coordination/claude/evidence/AI-01_2026-10-26/README.md`):
  1. `inference_openapi.json` export `app.main:app.openapi()`; export lại sau sửa code → `cmp` giống hệt.
  2. `examples/` 23 file sinh bởi `tests/test_live_smoke.py` (`INFERENCE_EXAMPLES_DIR`) trên uvicorn startup production, Milvus thật, media thật → 6/6 PASS.
     Recommendation: ví dụ 503 thật (collection `user_recommendation_embeddings` không tồn tại) → `DRAFT`.
  3. Contract v1.0: `API_READY` health/vision/asr/highlight/completions/search; recommendation `DRAFT`; sửa tài liệu cho khớp code
     (reco cold-start 503, vision ảnh hỏng 503 vs search 422, `thumbnail_url` tương đối, `degraded` dính).
  4. `tests/test_live_smoke.py` opt-in `INFERENCE_LIVE_URL`: real media 6/6 PASS, synthetic 6/6 PASS; suite mặc định 37 passed / 7 skipped.
  5. REL v1.0 trong HANDOFF_OUT.
  - Bug sửa: search đầu tiên sau startup 503 `DEADLINE_EXCEEDED` (timeout 1 s, query đầu sau load 474 ms → >1 s khi Milvus lạnh) → warmup trong lifespan.
- Follow-up (chưa làm, cần user): tạo/nạp `user_recommendation_embeddings` (`ai_core/scripts/export_two_tower_milvus.py` ghi vào Milvus stack Codex, ID từ dataset train);
  ngữ nghĩa `degraded` dính; cache `_milvus_collection` giữ cả None tới restart.
- Commits: 3fd0259 (nhận task), 2d34c24 (code + contract v1.0 + examples + REL) | Checkpoint:
  ```
  Lane: claude
  Changed: inference-service/app/{main.py,visual_index.py}, inference-service/tests/test_live_smoke.py, coordination/claude/api/{AI_API_CONTRACT.md,inference_openapi.json,examples/**}, coordination/claude/{HANDOFF_OUT.md,TASKS.md,SESSION.md,evidence/AI-01_2026-10-26/**}
  Verified: live smoke real media 6/6 + synthetic 6/6 PASS (startup production, Milvus thật); pytest tests/ 37 passed 7 skipped; openapi cmp unchanged
  Contract touched: yes (AI-API v1.0; schema không đổi)
  Next safe task: AI-07
  ```

### AI-02 — ASR domain adaptation (T1.4 follow-up)
- T gốc: T1.4 | Owner: claude | Status: 02a DONE · 02b DONE (user duyệt 51/60, 2026-10-28) · 02c DONE — guard loại, KHÔNG promote · **D23: dừng cải thiện cho MVP** (sau MVP: thu thêm audio domain có người duyệt)
- Tiến độ duyệt (ghi 2026-10-26): **7/60 đã duyệt, 53/60 còn phải kiểm tra** — số 7/60 là tiến độ trang review hiển thị
  (lưu localStorage Chrome, `http://127.0.0.1:8891/asr_review_v2/index.html`); **chưa có file JSON export** nào
  (Downloads không có `asr_expansion_review_v2*.json`) → bằng chứng file hiện là 0/60. Gói dữ liệu:
  `D:/data_training_ai/asr_domain_expansion_v2_20261022/` (60 WAV/MP4 20 s, 180 bản nháp Whisper = `MACHINE_DRAFT`).
- **AI-02a — Claude chuẩn bị + đề xuất (TODO):** cho 53 clip chưa duyệt, ưu tiên 9 clip trùng lời máy + 25 clip bị cờ:
  đề xuất sửa chữ/chuẩn hóa theo `docs/T1.4_asr_label_contract.md`, ghi lý do, nhãn `CLAUDE_PROPOSED` trong file riêng
  (không ghi đè nháp gốc, không ghi vào kết quả duyệt của user). Claude không nghe được audio → đề xuất chỉ dựa trên văn bản,
  phải ghi rõ giới hạn này. Acceptance: file đề xuất + hash nguồn + test strict-intake vẫn từ chối mục chưa `HUMAN_VERIFIED`.
  Evidence 02a (VERIFIED-NOW 2026-10-27, `docs/T1.4_asr_claude_proposals.md`, `data/manifests/asr_claude_proposals_v1.json`): 60/60 clip
  (13 EXCLUDE_CANDIDATE gồm 9 nháp ảo giác Whisper, 30 CORRECTION, 17 LISTEN_ONLY), hash audio/video/nháp + hash packet; chữ số trùng nháp 100%;
  0 verified; file D: SHA `9ade1bb4…` không ghi đè; intake `test_claude_proposed_transcript_is_never_approved` (2 case) → 40 passed.
- **AI-02b lần 1 (export v2, 2026-10-27, `received_87a7eb6fd111`, SHA `87a7eb6f…`): KHÔNG intake** — 60/60 xác nhận nhưng 57 giống hệt nháp Whisper
  (gồm 10 câu ảo giác 'Để không bỏ lỡ…'/'Đi nào?', chuỗi lặp, lỗi chính tả rõ) → nhãn = Whisper, vi phạm §0. User chọn duyệt lại bản gọn.
  Trang v3 `asr_review_v3` (`prepare_expansion_review_v3.py`, test 10 passed + kiểm trình duyệt): 57 clip xếp ưu tiên 11/26/20, điền sẵn gợi ý Claude,
  **chỉ cho xác nhận sau khi audio phát hết** (`audio_played_full` trong export). 3 clip user đã sửa giữ từ v2. Intake 02c sẽ yêu cầu `audio_played_full=true`.
- **AI-02b/02c (VERIFIED-NOW 2026-10-28, `docs/T1.4_asr_domain_replay_v2.md`):** export `86f0ce11…` 51 xác nhận / 9 loại (không lời); intake chặt 13 test;
  domain replay v2 (81 clip) trên Kaggle T4: domain WER 91.26→83.71, VIVOS hết hồi quy (28.75→28.55) nhưng FLEURS kém ~2 điểm → guard loại mọi bước,
  parent133 giữ nguyên, ASR active không đổi. Evidence `evidence/AI-02_2026-10-28/`. Commits 72405c9, 2bc1785, (commit kết quả).
- **AI-02b — người duyệt (gốc):** user nghe/sửa/xác nhận hoặc loại từng clip, xuất JSON thật. Chỉ mục user xác nhận
  mới là `HUMAN_VERIFIED`. Claude **không** tự gán.
- **AI-02c — intake + train (BLOCKED ⇐ 02b):** strict intake giữ machine-assisted provenance/coverage/train-only vocab/CTC/split guard;
  1 thí nghiệm bounded; chỉ promote khi guard VIVOS/FLEURS/domain không hồi quy; không chọn theo test.
- Blocks: AI-05; chất lượng phụ đề video thật phía Codex (không chặn tích hợp kỹ thuật).
- Evidence: lịch sử bên dưới + `docs/T1.4_*.md`. Checkpoint active `8f87986781cf…` giữ nguyên (HOLD PROMOTION).
- Commits: `15976b3` (trước tách làn)
- Checkpoint: Next safe task = AI-02a (không phụ thuộc user); 02b chờ user.

### AI-03 — Mini-GPT human quality gate (T1.6)
- T gốc: T1.6 | Owner: claude | Status: 03a DONE · 03b DONE theo D22 (Claude duyệt, 2026-10-27) · 03c DONE — KHÔNG promote; cổng người ≥3/5 chưa đạt · **D23: dừng cho MVP, tóm tắt = bản nháp admin duyệt**
- Nguồn 40 clip real-domain (30 train / 10 val, ngoài frozen30): `data/manifests/minigpt_real_domain.json`; transcript user đã rà
  (export SHA `860f8068d0bd…`, 40 transcript/39 sửa) — `docs/T1.6_whisper_review_intake.md`.
- **AI-03a — Claude soạn summary 40 clip (TODO, theo quyết định user 2026-10-26):** soạn từ transcript user đã rà; mỗi mục lưu
  clip ID, hash media + hash transcript nguồn, văn bản summary, số BPE token (≤95), người/công cụ tạo = Claude + ngày,
  nhãn `CLAUDE_PROPOSED`. Lưu file riêng trên D: + manifest `data/manifests/` + báo cáo `docs/T1.6_*`; không ghi đè dữ liệu cũ.
  Acceptance: đủ 40 mục, hash khớp nguồn, strict intake từ chối dùng làm target khi chưa `HUMAN_VERIFIED`.
  Evidence 03a (VERIFIED-NOW 2026-10-26, `docs/T1.6_claude_summaries.md`, `data/manifests/minigpt_claude_summaries_v1.json`): 40/40 mục, hash audio/video
  từ export `860f8068…` + hash transcript nguồn, BPE mean 46.2 / max 58 (tokenizer active), 40/40 câu kết thúc, `verified=false`, `CLAUDE_PROPOSED`;
  file D: SHA `978a32e0…` (không ghi đè); intake `test_gate_refuses_claude_proposed_summaries` (2 case, kể cả verified=true giả) → 22 passed.
  Lưu ý cho người duyệt: 2 mục trùng lời chào kênh, 2 mục transcript rất nhiễu (doc). Script: `dist/kaggle/kernel-minigpt-domain/build_claude_summaries.py`.
- **AI-03b — DONE theo D22 (2026-10-27):** Claude duyệt (không phải người): 38 đạt, 1 sửa (`dom_sTeS-7km_NM_1` bỏ suy diễn), 1 loại
  (`dom_p7FlzMrLDSo_1` trùng transcript). File `D:/.../claude_review_d22_v1/claude_reviewed_summaries_v1.json` SHA `bf1ee8ec…`, provenance `claude_drafted_claude_reviewed`.
  Baseline CLAUDE_JUDGE (`evidence/AI-03_2026-10-27/judge_baseline.json`): MiniGPT active với transcript sạch 1.44/5 (val 1.50), với ASR active 1.0/5 (40/40 bịa);
  ASR active CER 0.584 / candidate 0.481 trên 40 clip. Hiệu chuẩn 30 clip người chấm: judge 1.0 vs người 1.6 — 5 bất đồng đều là câu bịa trôi chảy.
- **AI-03c (VERIFIED-NOW 2026-10-27, `docs/T1.6_d22_domain_finetune.md`):** Kaggle T4 mixed replay + 29 cặp D22 ×8, guard News PASS (0.232→0.322, step 120,
  2.19 GiB). Candidate `62974ef8…` (D:, không thay active). CLAUDE_JUDGE domain val: sạch 1.5→1.8, ASR 1.0→1.0; ROUGE sạch 0.126→0.125; train học thuộc.
  KHÔNG promote. Nút thắt = ASR (CER 0.584 video thật) → cần AI-02b (người nghe). Commits 054e2af, 77e3af8, (commit kết quả).
- *(Gốc)* **AI-03b — người duyệt:** user duyệt/sửa/loại từng summary → `HUMAN_VERIFIED`.
  ⚠ Ràng buộc dự án (`my-agent/agent/instructions.md` §1: "không pseudo-label từ model ngoài"): summary do Claude soạn là
  output của model ngoài → chỉ được làm target train/eval sau khi người duyệt từng mục **và** provenance ghi rõ
  `claude_drafted_human_verified`. Mục chưa duyệt không bao giờ được dùng.
- **AI-03c — train/eval bounded (BLOCKED ⇐ 03b):** guard clean+ASR không hồi quy; cổng cuối vẫn là human mean ≥3/5 trên video thật
  mới, điểm do người chấm (summary Claude soạn **không** thay điểm chấm của người). Không tune trên frozen test, không hạ ngưỡng.
- Blocks: AI-05; chất lượng summary phía Codex (không chặn tích hợp kỹ thuật).
- Evidence: ROUGE-L News PASS (0.2023 vs 0.1871), shared human 1.6/5 FAIL. Candidate mixed300 `70ec4790…` giữ riêng; active `cf9cfa71…`.
- Commits: `15976b3`
- Checkpoint: Next safe task = AI-03a.

### AI-04 — Đo VRAM sơ bộ trên Kaggle T4 (AI-GATE điều kiện 4, T4.3 phần GPU)
- T gốc: T1.8, T4.3 | Owner: claude | Status: DONE — mức PRELIMINARY_T4 (2026-10-26). AI-GATE đk 4 / T4.3 GPU vẫn PARTIAL (cần RTX 3060).
- Depends on: AI-06 (đúng 6 checkpoint active + SHA). Máy local chỉ Intel UHD 630.
- Cách đo: notebook Kaggle private, GPU T4; nạp đúng 6 checkpoint active (SHA khớp contract) + 20 request tuần tự đủ 6 loại,
  đo `torch.cuda.max_memory_allocated/reserved` sau nạp và sau mỗi request; tải output về trước khi push version kế
  (memory: Kaggle chỉ giữ output bản mới nhất).
- Acceptance (PRELIMINARY): báo cáo `docs/T4.3_bao_cao.md` ghi rõ GPU (T4 16 GB), driver/CUDA, torch, dtype (fp16/fp32), batch,
  danh sách request, số đo peak/tail; kết luận ghi nhãn `PRELIMINARY_T4`.
- **Không thay nghiệm thu:** AI-GATE điều kiện 4 và T4.3 vẫn `PARTIAL` cho tới khi đo trên RTX 3060 (hoặc user duyệt riêng kết quả T4
  thay thế). T4 không chứng minh hành vi trên 3060 12 GB.
- Blocks: INT-07 (T5.1 GPU) chỉ ở mức nghiệm thu cuối; Codex có thể chạy bản CPU trước.
- Evidence (VERIFIED-NOW 2026-10-26, `docs/T4.3_bao_cao.md` mục AI-04, `coordination/claude/evidence/AI-04_2026-10-26/`):
  Kaggle private kernel `traininghighlight/ai-vram-t4-run-v1` v3, 2×T4 (đo GPU 0), driver 580.178.04, CUDA 12.8, torch 2.11.0+cu128, fp16; 6 ckpt SHA khớp contract;
  20 request tuần tự (vision 32 frame, ASR 25 s, highlight 120 s, completions map-reduce, Siamese 32) 20/20 OK. Sau nạp: nvidia-smi 305 MiB; peak 347 MiB
  (PyTorch reserved 210, allocated 133); tail allocated 82 MiB ổn định. Dry-run CPU cục bộ trước khi push. v1 (input nhỏ) → v2 (input xấu nhất) → v3 (+nvidia-smi).
- Commits: 06dcb0e (nhận task), 3a380dc (kernel+builder), 4b47b5a (v2), c5d0e60 (v3), 9918151 (báo cáo) | Checkpoint:
  ```
  Lane: claude
  Changed: dist/kaggle/kernel-vram-t4/{build_dataset.py,run_vram_t4.py,kernel-metadata.json}, docs/T4.3_bao_cao.md, coordination/claude/{TASKS,SESSION,HANDOFF_OUT}.md, evidence/AI-04_2026-10-26/**
  Verified: Kaggle T4 v3 20/20 OK, peak nvidia-smi 347 MiB ≤ 4096; SHA 6 ckpt khớp; CPU dry-run 5/5
  Contract touched: no
  Next safe task: AI-03a (Claude soạn 40 summary, CLAUDE_PROPOSED) / AI-02a
  ```

### AI-10 — Health/degraded đúng ngữ nghĩa (D15)
- T gốc: T1.8 | Owner: claude | Status: DONE (2026-10-26)
- Depends on: — | Blocks: AI-07 (kiểm health/readiness)
- Việc: input không hợp lệ (400/422, ảnh/audio không đọc được, lệch chiều highlight) không đánh dấu model degraded; chỉ lỗi inference thật/timeout mới đánh dấu;
  dependency (Milvus visual/recommendation: unavailable/missing_collection) có trạng thái riêng; degraded + dependency tự phục hồi khi gọi thành công / Milvus
  sửa xong (không cache thất bại vĩnh viễn). Giữ tương thích: status code hiện có giữ nguyên; field mới trong `/health` chỉ thêm (minor version) + REL cho Codex.
- Acceptance: test cho validation error, model failure, dependency unavailable, recovery; suite inference PASS; live smoke PASS; contract + openapi cập nhật.
- Evidence (VERIFIED-NOW 2026-10-26, `coordination/claude/evidence/AI-10_2026-10-26/README.md`): `tests/test_health_status.py` RED 9 ERROR → GREEN 9/9;
  `pytest tests/` 46 passed / 7 skipped; live smoke startup production :8011 + Milvus thật 2 lượt liên tiếp 6/6 PASS, `/health` sau đó
  `degraded=[]`, `dependencies={recommendation_index: missing_collection, visual_index: ok}`; OpenAPI diff chỉ thêm `HealthResponse.dependencies` (default `{}`).
  Contract v1.1-rc1 DRAFT + REL trong HANDOFF_OUT.
- Commits: 379c2f0 (nhận task), 0e5a3da (code + test + contract) | Checkpoint:
  ```
  Lane: claude
  Changed: inference-service/app/{main,registry,schemas,services}.py, tests/{test_health_status,test_live_smoke}.py, coordination/claude/{api/**,evidence/AI-10_2026-10-26/**,HANDOFF_OUT.md,TASKS.md,SESSION.md}
  Verified: health tests 9/9; suite 46 passed 7 skipped; live smoke 2×6/6 PASS
  Contract touched: yes (AI-API v1.1-rc1 DRAFT, chỉ thêm field /health.dependencies)
  Next safe task: AI-07
  ```

### AI-11 — HO-01: Vision `video_id` + index frame từ data URI (Codex RE:HC-05 chọn phương án b)
- T gốc: T1.8 / T4.2 | Owner: claude | Status: DONE (2026-10-26)
- Depends on: HO-01 | Blocks: INT-11 (real upload → vision/index/search trên topology host/Docker), release #2
- Việc: field optional `video_id` trên VisionRequest; có `video_id` + data URI/base64 → index Siamese frame theo thứ tự request = giây 0,1,2…,
  thumbnail MinIO `thumbnails/<video_id>/<8 số>.jpg`, payload/collection/metric/index giữ nguyên; nhánh ingest path cũ giữ nguyên. Xác nhận ASR đọc WAV
  qua MinIO presigned `http://localhost:9000/...`. Contract minor (chỉ thêm field) + RE:HO-01.
- Acceptance: unit test index data URI (thứ tự/timestamp/key/payload, thiếu video_id → không index, video_id sai → 422/503 không degraded);
  live :8001: vision có video_id → frame vào Milvus, search thấy video đó; ASR presigned URL 200.
- Evidence (VERIFIED-NOW 2026-10-26, `coordination/claude/evidence/AI-11_2026-10-26/README.md`): test_visual_search RED 2 → GREEN; suite 51 passed / 7 skipped;
  live :8001 vision video_id → 3 row Milvus giây 0/1/2 + 3 thumbnail, search → `vid_ai11probe` giây 1 sim 1.0, ASR presigned localhost:9000 → 200;
  dữ liệu probe đã dọn (0 row/0 thumbnail); smoke :8001 6/6; OpenAPI chỉ thêm `VisionRequest.video_id`. RE:HO-01 trong HANDOFF_OUT.
- Commits: bc3ec2f (nhận task), 3b44592 (code + test + contract v1.2-rc1) | Checkpoint:
  ```
  Lane: claude
  Changed: inference-service/app/{visual_index,schemas,services}.py, tests/test_visual_search.py, coordination/claude/{api/**,evidence/AI-11_2026-10-26/**,HANDOFF_OUT.md}; .env local (MINIO_*)
  Verified: unit 4 mới PASS; suite 51/7; live probe :8001 index+search+ASR presigned PASS, đã dọn
  Contract touched: yes (v1.2-rc1, chỉ thêm VisionRequest.video_id)
  Next safe task: release #2 (user duyệt push)
  ```

### AI-22 — HO-04: image AI hiện hành chạy trong Docker + bằng chứng parity
- T gốc: T1.8 | Owner: claude | Status: IN_PROGRESS (2026-11-02)
- Depends on: HO-04 (Codex 2026-10-30) | user 2026-11-02 chọn runtime chính thức = container Docker (thay tiến trình host :8001)
- Hiện trạng: container `video-ai-inference-service-1` chạy image cũ `ai-v2-478052e` (trước AI-19/recipe) nhưng mount checkpoint
  `E:/traning_ai/ai-core/checkpoints` (vòng 8 ×10) → checkpoint mới + code cũ.
- Việc: build `video-ai-inference:ai-v1.4-<commit>` từ HEAD (label revision) → container thử cổng 18001 (checkpoint `:ro`) →
  /health 6 model + smoke + SHA checkpoint = contract §1 + đầu ra highlight trùng tiến trình host → HC-16 (Codex đổi tag compose; Claude không sửa compose, không `compose up`).

### AI-21 — Xác nhận vòng 8 ×10 trên test tin tức độc lập
- T gốc: T1.5 | Owner: claude | Status: REVIEW (2026-10-30) — quy tắc đạt (tin tức +0.097, bóng đá −0.008) nhưng CI [−0.05, +0.24], dưới mốc đoán-bừa; chờ user
- Depends on: AI-20 (×10 thỏa mọi ngưỡng riêng lẻ nhưng không được chọn theo quy tắc cũ) | user chọn hướng 1 (2026-10-30)
- Quy tắc đăng ký trước: `.claude/evaluation_plan.md` §2.1 "Xác nhận vòng 8 ×10". Ứng viên cố định; nhãn test mù; test tin tức chấm 1 lần.
- Việc: tìm + tải 6–10 video CC BY kênh mới (yt-dlp, giữ provenance/SHA) → feature đường production → trang gán nhãn MÙ → user gán → intake → chấm.
- Evidence (VERIFIED-NOW 2026-10-30, `coordination/claude/evidence/AI-21_2026-10-30/`): test tin tức vòng 7 0.024 / ×10 0.121 (mốc đoán-bừa 0.281);
  kênh mới ×10 0.0; bóng đá 0.3298 → 0.3222; bootstrap CI95 Δ [−0.053, +0.238]. Quy tắc → chuyển; hiệu quả chưa vững.
- Kích hoạt (VERIFIED-NOW 2026-10-30, user chọn "kích hoạt theo quy tắc"): vòng 7 sao lưu `_archive/highlight_fusion_round7_550909de/`; luật clip chọn trên val
  (nối ≤1 s, bỏ <3 s; test 0.3246); validate 6/6; :8001 PID 19220 smoke 9/9; contract §1 SHA `5aecd5c4…`; dataset Kaggle worker version mới ready.
- Commits: ad79d0d, 10a38d3, f95da24, b56a824, c27e21f, (kích hoạt: commit này)

### AI-20 — Fusion vòng 8: bóng đá + tin tức có nhãn người
- T gốc: T1.5 | Owner: claude | Status: DONE (2026-10-30) — theo quy tắc đăng ký: GIỮ vòng 7 (thắng ×1 trượt gap 0.224 > 0.1706)
- Depends on: AI-19 (nhãn tin tức) | Blocks: —
- Quy tắc: đăng ký trước `.claude/evaluation_plan.md` §2.1 "Vòng 8". Kernel mới `traininghighlight/ai-core-fusion-r8`; dataset private `traininghighlight/highlight-news-v1`
  (chỉ đặc trưng + nhãn, không có video).
- Acceptance: 3 biến thể × 3 seed; chấm local; quyết bằng val; test bóng đá sau quyết; đạt → đề xuất kích hoạt.
- Evidence (VERIFIED-NOW 2026-10-30, `coordination/claude/evidence/AI-20_2026-10-30/`): vòng 7 tin tức val 0.185 (dưới đoán-bừa 0.22);
  ×1 bóng đá 0.3126 / tin tức 0.511 / gap 0.224 (trượt) / test 0.3267; ×10 bóng đá 0.3228 / tin tức 0.376 / gap 0.133 (thỏa riêng, nhưng không được chọn theo quy tắc);
  ×30 0.306 / 0.192. Val loss đáy step 300–1500 rồi +48–65% mọi run. τ chung không hợp tin tức. Val tin tức 3 video, 1 cùng kênh với train.
- Commits: da5a55e, 8984b7b, b2f05a2, (kết quả: commit này) | Checkpoint: giữ vòng 7; đề xuất thu thêm tin tức làm val/test độc lập rồi xác nhận ×10

### AI-19 — Highlight: sửa đặc trưng vision + dữ liệu tin tức có nhãn người
- T gốc: T1.5 | Owner: claude | Status: DONE (2026-10-30) — (a) fix vision; (b) nhãn tin tức khoatm 10/10 video HUMAN_VERIFIED, intake với gộp đoạn chồng (`coordination/claude/evidence/AI-20_2026-10-30/news_intake_report.json`)
- Depends on: AI-18 (vòng 7 active); quyết định user 2026-10-29 | Blocks: vòng 8 (cần file nhãn HUMAN_VERIFIED)
- (a) DONE 2026-10-29 (1b5e211): `embeddings_256` = backbone Siamese (đặc trưng Fusion đã train; trước là ViT phân loại, cosine 0.03–0.13);
  `tests/test_feature_parity.py` khóa với checkpoint thật; :8001 PID 30580 smoke 9/9; REL cho Codex (video cũ cần chạy lại highlight).
- (b) Quyết định user (2026-10-29): dùng 10 video tin tức GỐC `D:/data_training_ai/minigpt_real_video_20261015/raw/youtube` cho train highlight;
  30 đoạn `evaluation/` (tập chấm MiniGPT) giữ nguyên, không dùng. Sau khi dùng, 10 nguồn này KHÔNG được làm test highlight.
  Nhãn: AI đề xuất (CLAUDE_PROPOSED) → user sửa/duyệt trên `label_news.html` → export HUMAN_VERIFIED → intake → vòng 8.
- Evidence: — | Commits: — | Checkpoint: —

### AI-18 — Fusion vòng 7: giảm overfit (learning rate / weight decay / lịch ngắn)
- T gốc: T1.5 | Owner: claude | Status: REVIEW (2026-10-29) — đạt cả 3 điều kiện; **ACTIVE** trên :8001 (user ra lệnh); recipe τ 0.51, bỏ clip < 3 s, video < 120 s không clip; vòng 6 lưu `_archive/highlight_fusion_round6_9b59a7b0/`
- Depends on: AI-17 (vòng 6 active; val loss đáy step 500–1100 rồi tăng) | Blocks: —
- Quy tắc: đăng ký trước `.claude/evaluation_plan.md` §2.1 "Vòng 7". Kernel mới `traininghighlight/ai-core-fusion-r7` (giữ output vòng 6).
- Acceptance: sweep 4 biến thể + (nếu thắng mốc) 3 seed; chấm local; quyết bằng val + gap + val loss; test 1 lần sau quyết; đạt → đề xuất kích hoạt.
- Evidence (VERIFIED-NOW 2026-10-29, `coordination/claude/evidence/AI-18_2026-10-29/`): thắng wd 0.3; ensemble val 0.3151 / gap 0.1606 / val loss 1.1477 → ĐẠT;
  test 0.3298 (vòng 6 0.3280). LR 1e-4 hoặc 1500 step: hết overfit theo val loss (+2–6%) nhưng F1 thấp hơn.
- Commits: 265bc16, f971166, 8e6b014, (kết quả: commit này) | Checkpoint: chờ quyết kích hoạt

### AI-17 — Fusion vòng 6: giảm overfit (chuẩn hóa theo video + augment)
- T gốc: T1.5 | Owner: claude | Status: REVIEW (2026-10-29) — vòng 6 đạt quy tắc; **ACTIVE** trên :8001 (user ra lệnh), chờ release
- Kích hoạt (VERIFIED-NOW 2026-10-29): vòng 5 sao lưu `ai-core/checkpoints/_archive/highlight_fusion_round5_34199b68/`; validate 6/6; :8001 PID 27064 smoke 9/9;
  contract §1 SHA `9b59a7b0…`; dataset Kaggle worker version mới ready (dry-run nạp đủ 6, feature_norm). Giới hạn: video < ~2 phút ngoài phân bố train.
- Depends on: AI-16 (đo overfit: train 0.480 / val 0.275 / test 0.263) | Blocks: —
- Quy tắc chọn: đăng ký trước trong `.claude/evaluation_plan.md` §2.1 (vòng 6). Kernel Kaggle MỚI (không ghi đè output vòng 5).
- Acceptance: 4 biến thể sweep + 3 seed trên Kaggle; chấm local quy trình DoD; quyết bằng val + gap; test báo cáo 1 lần; nếu đạt → đề xuất kích hoạt (user duyệt).
- Evidence (VERIFIED-NOW 2026-10-29, `coordination/claude/evidence/AI-17_2026-10-29/`): thắng n1_a1 (chuẩn hóa + augment); ensemble val 0.3053 (≥0.2750),
  gap train−val 0.1692 (<0.205) → ĐẠT; test 0.3280 (vòng 5: 0.2632). Service path 0.3281; luật clip chọn trên val (bỏ < 5 s) → test 0.3334.
  Đường cong: val loss đáy ở step 500–1100 rồi tăng 22–136% mọi run (overfit sau ~1/4 lịch) — ghi cho vòng sau. ai-core 319 passed; inference 78/10.
- Commits: 8ca8336 (đăng ký), 8f028d2 (code+kernel), 10a2417 (val-loss monitor), f08e842 (zip), d8a8bac (kết quả), 45d9320 (ứng viên) | Checkpoint:
  ```
  Lane: claude
  Changed: ai-core/ai_core/{config.py,training/trainer.py,training/datasets/highlight_dataset.py}, tests (norm/aug, trainer val loss), inference-service/app/worker.py (feature_norm), dist/kaggle/kernel-fusion-r6, evaluation_plan §2.1, evidence AI-17
  Verified: ai-core 319; inference 78/10; round 6 val 0.3053 / gap 0.169 / test 0.3280; service path 0.3281
  Contract touched: no (chưa kích hoạt; kích hoạt = đổi SHA highlight + release)
  Next safe task: user duyệt kích hoạt vòng 6
  ```

### AI-16 — Highlight: checkpoint đúng vòng DoD + hậu xử lý như lúc chấm + luật clip
- T gốc: T1.5 / T1.8 | Owner: claude | Status: REVIEW (2026-10-29) — B/A/C xong; **vòng 5 ACTIVE** trên :8001 (user: "hãy kích hoạt models training mới nhất"); chờ release
- Kích hoạt (VERIFIED-NOW 2026-10-29): sao lưu vòng 3 → `ai-core/checkpoints/_archive/highlight_fusion_round3_becbd378/`; 4 file vòng 5 vào `highlight_fusion/`
  (SHA khớp ứng viên); validate_artifacts 6/6; :8001 restart PID 14896, smoke 9/9 (`smoke_8001_round5_active.log`); contract §1 SHA `34199b68…`;
  dataset Kaggle worker version mới (ensemble + code) ready, kernel dry-run nạp đủ 6. ASR 02c / MiniGPT 03c KHÔNG kích hoạt (trượt guard/cổng).
- Depends on: user 2026-10-29 (B trước, rồi A + C) | Blocks: HC cho Codex (ngưỡng CMS, FFmpeg cắt chính xác)
- Bối cảnh: DoD T1.5 đạt với gộp 3 seed + làm mượt k=9 + τ=0.51 (`docs/T1.5_bao_cao.md` §6g), nhưng service chạy 1 checkpoint, không làm mượt, ngưỡng cứng 75;
  `best.pt` active = d256/p0.3 seed 1337 (val F1 0.199 step 1300) trong khi vòng 5 chốt d128/p0.3.
- Việc: (B) chỉ đọc — xác định checkpoint active thuộc vòng nào, checkpoint vòng 5 còn không, SHA; (A) hậu xử lý đúng cấu hình đã chấm;
  (C) độ dài clip tối thiểu/tối đa, nối khe ngắn, biên theo câu ASR. Đổi checkpoint active = bump contract + release (user duyệt).
- Acceptance: báo cáo B có bằng chứng; A/C có test + đo trên tập test đã khóa (không chọn tham số bằng test); contract cập nhật; suite + smoke PASS.
- Evidence (VERIFIED-NOW 2026-10-29, `coordination/claude/evidence/AI-16_2026-10-29/`): active = vòng 3 (DoD không đạt); service path tái hiện vòng 5
  test F1 0.2628 (DoD 0.2632); ngưỡng 75 cùng model 0.168; luật clip chọn trên val (gap 5/min 3) test F1 0.2624, clip < 3 s 97 → 0;
  inference 77/10; :8001 restart PID 23292 smoke 9/9, highlight example SAME (active chưa đổi). Ứng viên `D:/tmp/ai16_20261029/candidate/highlight_fusion/`.
- Commits: b26110b (task), 449bfd4 (B), b7ca117 (A+C code/test/evidence), (contract/HC-14: commit này) | Checkpoint:
  ```
  Lane: claude
  Changed: inference-service/app/{registry,worker,services,schemas}.py, tests/{test_highlight_recipe (mới),test_worker}.py; api/{AI_API_CONTRACT.md,inference_openapi.json}; HANDOFF_OUT (HC-14); evidence AI-16
  Verified: inference 77/10; recipe == eval pipeline; service F1 0.2628 on locked test; smoke :8001 9/9, active highlight unchanged
  Contract touched: yes (v1.4-rc1 DRAFT: asr_segments tùy chọn; đổi checkpoint chờ duyệt)
  Next safe task: user duyệt kích hoạt vòng 5 → contract §1 + release; Kaggle dataset rebuild
  ```

### AI-15 — D24 bước 2: AI-API v2.0 — inference-service chỉ tính toán, Backend sở hữu dữ liệu
- T gốc: T1.8 | Owner: claude | Status: BLOCKED ⇐ Codex RE:HC-13 (E2E backend dùng /v2) — phần AI xong 2026-10-29 (contract v2.0 DRAFT, endpoint thật, HC-13)
- Depends on: AI-14 (worker thuần) | Blocks: gỡ minio/pymilvus khỏi inference-service (sau khi Codex E2E PASS); INT-xx phía Codex
- Việc (phía AI): contract v2.0 DRAFT (vision trả thêm `siamese_vectors`, không ghi MinIO/Milvus; search nhận ảnh → vector 128; ASR nhận bytes audio multipart,
  chia đoạn; recommendation encode → vector 128 khớp Two-Tower; highlight/completions giữ nguyên) + `inference_openapi.json` + examples thật + error codes
  + bảng di chuyển v1.3→v2.0; hiện thực endpoint v2 thuần (qua worker AI-14), v1.3 không vỡ; HC cho Codex (Milvus Go, MinIO thumbnail, audio bytes,
  ingest gọi API mới, recommendation tra Milvus, migrate 280 vector, xóa video đồng bộ, E2E). Sau Codex E2E PASS: release → gỡ minio/pymilvus, v1.3 DEPRECATED.
- Acceptance (phần AI): endpoint v2 không import/gọi MinIO/Milvus (test khóa); suite inference + compat v1.2 PASS; smoke v1.3 6/6 + v2 thật trên :8001; contract v2.0 DRAFT + REL + HC.
- Evidence (VERIFIED-NOW 2026-10-29, `coordination/claude/evidence/AI-15_2026-10-29/`): inference 71 passed / 10 skipped (compat v1.2 + v1.3);
  smoke :8001 9/9 (v1 6/6 + 401, v2 3/3 trùng v1 trên media thật; reco v2 503 MODEL_NOT_READY); OpenAPI chỉ thêm; Milvus đo 411 vector / 49 video.
  Còn lại (sau RE:HC-13): release → /v2 API_READY, /v1 media/search/reco DEPRECATED → gỡ minio/pymilvus + Milvus khỏi lifespan.
- Commits: bfa4a40 (task), e307bf2 (code), deecc45 (smoke/examples/openapi), (contract/HC-13: commit này) | Checkpoint:
  ```
  Lane: claude
  Changed: inference-service/app/{v2 (mới),schemas,main,services,worker}.py, tests/{test_v2 (mới),test_live_smoke,test_contract_compat,test_worker}.py, README;
           coordination/claude/api/{AI_API_CONTRACT_V2.md (mới),AI_API_CONTRACT.md,inference_openapi.json,inference_openapi_v1.3.json,examples/v2_*}; HANDOFF_OUT (REL + HC-13); plan 01 (1 dòng D24)
  Verified: inference 71/10; smoke :8001 9/9 (v1 + v2 thật); openapi additive
  Contract touched: yes (AI-API v2.0 DRAFT thêm /v2; v1.3 không đổi)
  Next safe task: chờ RE:HC-13; song song AI-12 khi có dữ liệu INT-15
  ```

### AI-14 — D24 bước 1: tách facade/worker trong inference-service
- T gốc: T1.8 | Owner: claude | Status: REVIEW (2026-10-29) — đạt Acceptance trên `claude/ai-core`, chờ release; kernel Kaggle dựng + dry-run local, chưa push (chờ user)
- Depends on: D24 (user 2026-10-29: AI service chỉ tính toán, backend sở hữu dữ liệu; làm tuần tự bước 1 → bước 2) | Blocks: AI-15 (bước 2, contract v2.0)
- Việc: `app/worker.py` = lớp worker thuần (6 model; nhận ảnh bytes / PCM bytes / vector / text → nhãn / vector / text; không import minio/pymilvus);
  facade (`main.py`, `services.py`, `visual_index.py`) giữ nguyên 7 endpoint, Bearer, validation, error code và toàn bộ I/O MinIO/Milvus.
  `MODEL_WORKER_URL` trống = worker cùng tiến trình (mặc định, y hệt hiện nay); có URL = facade gọi worker HTTP nội bộ, Bearer riêng `MODEL_WORKER_KEY`
  (không commit; cấm `sk-local-dev-key`). Kernel Kaggle `dist/kaggle/kernel-model-worker/` (worker GPU + cloudflared quick tunnel, không dữ liệu người dùng).
- Acceptance: ai-core suite + inference suite (gồm `test_contract_compat.py`) PASS; unit test worker không cần Milvus/MinIO; smoke :8001 6/6 + 401 (worker in-process);
  1 smoke worker từ xa (process local khác cổng hoặc Kaggle) cùng schema; contract giữ v1.3 (chỉ thêm ghi chú kiến trúc).
- Evidence (VERIFIED-NOW 2026-10-29, `coordination/claude/evidence/AI-14_2026-10-29/`): inference 63 passed / 7 skipped (baseline 55/7, +8 test worker);
  ai-core 314 passed; OpenAPI == `inference_openapi.json` v1.3; smoke :8001 in-process 6/6 + 401, response trùng examples công bố (trừ search do Milvus có thêm vid_ai11probe);
  smoke worker từ xa (worker :8002 + facade :8001 `MODEL_WORKER_URL`) 6/6 + 401, response trùng in-process, health chỉ thêm `model_worker`;
  worker chết → 503 + `model_worker: unavailable`, không degraded; :8001 khôi phục in-process (PID 16292) 6/6; kernel Kaggle dry-run local OK.
- Kaggle (user 2026-10-29: chỉ upload dataset): `traininghighlight/ai-model-worker-v1` private, status ready (manifest SHA = contract §1; Kaggle tự giải nén zip).
  Version 2 (2026-10-29, sau AI-15): code worker mới (`inference_service.zip` 8b098b0d…), checkpoint không đổi. Kernel thêm kiểm GPU fail-fast + log nvidia-smi 10 phút (tham khảo video user gửi, 8d1e0e8).
  Kernel `traininghighlight/ai-model-worker` **chưa push** — push = mở phiên GPU; user tự Run khi cần.
- Commits: 7465f2b (task), 8086067 (code + test), 178d9fe (docs/evidence) | Checkpoint:
  ```
  Lane: claude
  Changed: inference-service/app/{worker,worker_client,worker_app}.py (mới), {services,visual_index,main,config}.py, tests/{test_worker (mới),test_health_status,test_visual_search}.py, README, .env.example; dist/kaggle/kernel-model-worker/**; contract §1d/§2.7/changelog (v1.3 không đổi)
  Verified: inference 63/7; ai-core 314; openapi identical; smoke in-process 6/6+401; smoke remote worker 6/6+401 (same responses)
  Contract touched: no (AI-API v1.3; chỉ ghi chú kiến trúc + key dependencies.model_worker ở chế độ remote)
  Next safe task: AI-15 (D24 bước 2, contract v2.0 DRAFT)
  ```

### AI-13 — Recommendation inference: không metadata giả + recommendation_mode (D18 mục 6–7)
- T gốc: T1.7 / T1.8 | Owner: claude | Status: DONE (2026-10-26)
- Depends on: D18 | Blocks: Codex hydrate metadata thật (đề xuất INT-12)
- Việc: `/v1/recommendation/completions` chỉ trả `video_id` + `score` thật; `title`/`thumbnail_url` → `null` (không dựng `Video <id>` / `https://storage.local/...`),
  kể cả stub; thêm `recommendation_mode` ("personalized" khi vector thật, "stub" khi FORCE_STUB) để gateway không nhầm. Tương thích ngược: field cũ còn, nullable.
- Acceptance: unit test không còn metadata giả + mode đúng; suite inference PASS; smoke :8001 PASS; contract minor + openapi + REL/HC-06.
- Evidence (VERIFIED-NOW 2026-10-26, `coordination/claude/evidence/AI-13_2026-10-26/`): test_api RED 2 → GREEN; suite 53 passed / 7 skipped;
  sandbox :8011 200 personalized + metadata null; :8001 restart (PID 16808) 503 product + smoke 6/6; OpenAPI title/thumbnail nullable + recommendation_mode.
  Contract v1.3-rc1 DRAFT + REL trong HANDOFF_OUT.
- Commits: cafd788 (task), 26d1e48 (code + docs) | Checkpoint:
  ```
  Lane: claude
  Changed: inference-service/app/{schemas,services}.py, tests/test_api.py, coordination/claude/api/{AI_API_CONTRACT.md,inference_openapi.json,TWO_TOWER_ARTIFACT.md,examples/recommendation.sandbox_response.json}, HANDOFF_OUT, evidence
  Verified: unit 2 mới PASS; suite 53/7; live sandbox 200 + product 503; smoke :8001 6/6
  Contract touched: yes (v1.3-rc1 DRAFT, recommendation only)
  Next safe task: AI-12a/12c (spec dữ liệu v2) hoặc AI-04 / AI-03a / AI-02a
  ```

### AI-12 — Two-Tower v2 cho sản phẩm (D18 phương án B, roadmap)
- T gốc: T1.7 | Owner: claude | Status: BLOCKED ⇐ bundle thật INT-13 (2026-10-26) — phần độc lập dữ liệu thật xong: 12a/12c (contract `ttv2-data-v1.1` + nhãn `ttv2-labels-v2`),
  12b/12d (feature inductive, train loop, harness, gate D19, verify bundle). Còn: chạy trên bundle thật INT-13 (12d thật, 12e, 12f) — chưa đạt acceptance, không DONE
- Depends on: dữ liệu tương tác hợp lệ của sản phẩm (Codex ghi `user_interactions`, đề xuất INT-13) | Blocks: recommendation `personalized` trên sản phẩm
- Giữ nguyên: Two-Tower v1 (`two_tower-ml100k-v1`, SHA `f28c3794…`) làm baseline nghiên cứu trong sandbox; không xóa model/checkpoint/dữ liệu.
- Bước (mỗi bước có test/bằng chứng riêng; chỉ AI-12f mới chạm sản phẩm):
  - **12a Chuẩn hóa dữ liệu:** spec đầu vào từ Postgres (users, user_preferences→10 danh mục, videos+category, user_interactions) qua export read-only của Codex;
    ID sản phẩm (`usr_*`/`vid_*`) giữ nguyên làm khóa, không hash/modulo; loại video chưa `published`.
  - **12b Mapping/vocabulary:** encoder **inductive**: user = sở thích danh mục (10) + tổng hợp embedding video đã tương tác; video = danh mục (10) + ViT 256-d
    + popularity; vocabulary danh mục versioned; user/video mới có vector từ feature (hết cold-start do one-hot).
  - **12c Tương tác hợp lệ:** positive = favorite/like/share, watch_time ≥ ngưỡng (vd ≥ 50% hoặc ≥ 30 s), click có xem; skip = negative tường minh; lọc bot/trùng;
    spec ngưỡng ghi trong `dataset_spec.md` trước khi thu dữ liệu.
  - **12d Dataset + negative sampling + offline eval:** split theo thời gian (leave-last-k/user), negatives = in-batch + sampled theo popularity (logQ đúng),
    baseline bắt buộc: popularity (chính là mode MVP); metric Recall@10, NDCG@10, coverage, CI95 bootstrap.
  - **12e Train/test/export:** train T4/RTX 3060 (VRAM ≤ 8 GB), unit test toán học, export vector vào **sandbox trước**, manifest version + SHA.
  - **12f Phát hành:** contract minor (personalized cho product), smoke :8001, handoff Codex; nạp collection sản phẩm chỉ khi quality gate đạt + user duyệt.
- **Quality gate (user duyệt D19, 3 giai đoạn):**
  - `TRAIN_EXPERIMENTAL`: train thử với dữ liệu hợp lệ hiện có; artifact chỉ sandbox.
  - `EVAL_READY`: ≥ 200 user, ≥ 5 000 tương tác hợp lệ, ≥ 5 positive/user trong tập eval. Chưa đạt → vẫn thử nghiệm, không tuyên bố kết quả đủ tin cậy.
  - `PRODUCTION_READY`: Recall@10 và NDCG@10 > Popularity trên cùng tập; CI95 (bootstrap) của chênh lệch có cận dưới > 0; coverage ≥ 20%;
    p95 CPU inference ≤ 50 ms/user trên cấu hình benchmark ghi rõ. Lên production chỉ khi user duyệt.
  - Bắt buộc: split theo thời gian, chống leakage/trùng/tương tác không hợp lệ; báo cáo kích thước mẫu, tập candidate, phương pháp CI, benchmark, cold-start.
    Không pseudo-label từ model ngoài. Ngưỡng xem lại nếu quy mô/phân phối thực tế không phù hợp (ghi lý do, user duyệt).
- Evidence 12a/12c (VERIFIED-NOW 2026-10-26, `coordination/claude/evidence/AI-12_2026-10-26/`): data contract `coordination/claude/api/TWO_TOWER_V2_DATA_CONTRACT.md`
  (`ttv2-data-v1`); `ai_core/training/datasets/product_interactions.py` — test RED (module thiếu) → 8/8 PASS (checksum, lý do loại [đính chính: 10 lý do + duplicate, không phải 9], dedup 30 s, nhãn,
  split thời gian không leakage + cold-start, vocabulary versioned, gate D19); ai-core 297 passed; `dataset_spec.md` §3.6 cập nhật; HC-07 cho Codex.
- Evidence 12b/12d + labels v2 + verify (VERIFIED-NOW 2026-10-26, `evidence/AI-12_2026-10-26/README_12bd.md`, SYNTHETIC = chỉ kiểm logic):
  nhãn v2 RED→GREEN, lưới 7 980 cặp 0 xung đột; `two_tower_v2.py` 8 test (feature chỉ từ train, oracle, loại item đã xem, popularity train-only, bootstrap,
  gate từng điều kiện, synthetic không qua production, train > untrained +0.2); `verify_ttv2_bundle.py` + schema/provenance 5 test; ai-core 311 passed.
- Verify bundle thật đầu tiên (VERIFIED-NOW 2026-10-27): Codex INT-15 `20261026T113856Z` — schema/provenance/SHA ACCEPTED, 0 tương tác → gate `NO_DATA`
  (thêm giai đoạn NO_DATA, test RED→GREEN, ai-core 311 passed). Evidence `verify_INT-15_20261026T113856Z.json`. AI-12 vẫn BLOCKED ⇐ dữ liệu tương tác thật.
- Commits: 7dc80ac (D19–D21, task), b261600 (12a/12c), e65bb74 (labels v2, HC-08), 920bf9d (12b/12d), 5a8d837 (v1.1 verify) | Kế: 12b (encoder inductive) + 12d (eval harness, baseline Popularity) trên bundle thật khi INT-13 có dữ liệu;
  có thể chuẩn bị harness với dữ liệu tổng hợp (không dùng làm kết quả).

### AI-09 — Two-Tower recommendation phía AI (D14)
- T gốc: T1.7 | Owner: claude | Status: DONE (2026-10-26) — phạm vi sandbox/artifact/interface; personalized product chuyển AI-12 (D18)
- Depends on: HC-04 (Codex: mapping ID sản phẩm user_id/video_id, collection Milvus, pipeline đồng bộ, nối backend) | Blocks: INT-03 phần personalized thật
- Việc (Claude): đặc tả embedding (dim, chuẩn hóa, metric), schema export + version model, script export có kiểm thử dữ liệu AI; chỉ thử với dataset train
  trong collection/môi trường **sandbox** tách biệt (Codex cấp theo HC-04). KHÔNG chạy `export_two_tower_milvus.py` vào collection sản phẩm khi mapping ID chưa xác minh.
- Acceptance: schema/dim/metric/ID mapping/tiêu chí nghiệm thu được hai làn xác minh trong handoff; test export; nạp thật chỉ sau đó. Tới lúc đó giữ popularity
  fallback, personalized recommendation không DONE.
- Evidence (VERIFIED-NOW 2026-10-26, `coordination/claude/evidence/AI-09_2026-10-26/`; đặc tả `coordination/claude/api/TWO_TOWER_ARTIFACT.md`):
  - Checkpoint `f28c3794…`: user_dim 942 (one-hot user MovieLens), video_dim 1702 (19 genre + pop + one-hot 1682 item), không lưu vocabulary → transductive,
    **không encode được product** (`product_ids_supported=false`).
  - `tests/test_export_two_tower.py` RED 4 → GREEN 4; ai-core suite 289 passed.
  - Export sandbox: 2624 row `ml100k_*`, re-export idempotent (2624 sống, 0 ngoài namespace), ANN recall@10 = 1.0 vs brute-force (53 user);
    service :8011 tạm trỏ sandbox: `ml100k_u_1` 200 (5 gợi ý), user lạ 503, dependency ok. :8001 product không đổi.
  - Export chặn cứng collection sản phẩm; chỉ xóa namespace `ml100k_*`. RE:HC-04 trong HANDOFF_OUT.
- User chọn (D18): A cho MVP + roadmap B → AI-12 (v2), AI-13 (bỏ metadata giả). AI-09 đóng phần sandbox/artifact; v1 giữ làm baseline sandbox.
- Commits: 54fed30 (nhận task), 34ef443 (code + docs) | Checkpoint:
  ```
  Lane: claude
  Changed: ai-core/ai_core/scripts/export_two_tower_milvus.py, ai-core/ai_core/tests/test_export_two_tower.py, coordination/claude/api/{TWO_TOWER_ARTIFACT.md,two_tower_artifact_manifest.json,AI_API_CONTRACT.md}, coordination/claude/{HANDOFF_OUT.md,evidence/AI-09_2026-10-26/**}
  Verified: export tests 4/4; ai-core 289 passed; sandbox 2624 row idempotent, ANN recall 1.0; service sandbox 200/503
  Contract touched: yes (chỉ ghi chú §2.5, schema không đổi)
  Next safe task: chờ user quyết A/B/C; song song AI-04 / AI-03a / AI-02a
  ```

### AI-07 — Vận hành runtime :8001 thật cho Codex
- T gốc: T1.8 | Owner: claude | Status: DONE (2026-10-26)
- Lý do: quyết định user 2026-10-26 — Codex không sao chép/quản lý checkpoint; tích hợp AI chỉ qua HTTP :8001.
  → Claude sở hữu tiến trình inference-service chạy checkpoint thật.
- Depends on: AI-06 (DONE), AI-10; Milvus từ stack Codex lắng nghe `localhost:19530` (UP theo RE:HC-03). | Blocks: INT-01 (phần E2E thật), INT-03, công bố API_READY (D16).
- Acceptance: lệnh chạy chuẩn (uvicorn từ worktree Claude, `CHECKPOINT_DIR` canonical, `MILVUS_HOST` của stack Codex, port 8001,
  `AI_SERVICE_KEY` dùng chung với gateway) ghi trong contract mục Runtime; `GET :8001/health` → `stub_mode=false`, 6 model;
  trạng thái runtime (UP/DOWN + thời điểm) ghi `SESSION.md`. Khi :8001 DOWN, Codex dùng mock — không chặn nhau.
- D16: kiểm model loading, endpoint, health, readiness, request/response, error handling; ghi kết quả từng model, không READY model chưa chạy.
- Thêm phạm vi (user duyệt 2026-10-26 sau AI-06): sửa trong code lỗi Windows stdout cp1252 (`services._warn` print tiếng Việt →
  `UnicodeEncodeError` → 500 plain-text thay vì 503 envelope); có test tái hiện. Tới lúc đó chạy service với `PYTHONUTF8=1`.
- Evidence (VERIFIED-NOW 2026-10-26, `coordination/claude/evidence/AI-07_2026-10-26/README.md`):
  - UTF-8: `tests/test_stdout_encoding.py` RED (`UnicodeEncodeError … 'ỗ'`) → `app/__init__.py` → GREEN; suite 47 passed / 7 skipped không có PYTHONUTF8.
  - Runtime :8001 qua `run_local_8001.cmd` + Start-Process (PID 26396), startup production, Milvus thật; contract §1c ghi lệnh/log/trạng thái.
  - Smoke :8001 media thật 6/6 (examples sinh lại từ :8001) + synthetic 6/6; `/health` stub_mode=false, 6 model, degraded=[],
    dependencies {recommendation_index: missing_collection, visual_index: ok}; log 0 UnicodeEncodeError.
  - Docker → `host.docker.internal:8001/health` 200 (từ `video-ai-gateway-1`, chỉ đọc).
  - Từng model: vit/asr_ctc/highlight_fusion/minigpt/siamese chạy; two_tower nạp nhưng recommendation 503 (collection chưa có, D14) → không READY.
  - Giới hạn: VRAM ≤4 GB chưa đo (CPU-only, AI-04); ingest `/srv/work` path ⇐ HC-05 (Codex chọn phương án).
- Commits: cdb022f (nhận task), a970368 (UTF-8 fix + runtime + evidence + HC-05) | Checkpoint:
  ```
  Lane: claude
  Changed: inference-service/app/__init__.py, inference-service/run_local_8001.cmd, inference-service/tests/test_stdout_encoding.py, coordination/claude/{api/**,evidence/AI-07_2026-10-26/**,HANDOFF_OUT.md,TASKS.md,SESSION.md}
  Verified: encoding test RED→GREEN; suite 47 passed 7 skipped; :8001 smoke real 6/6 + synthetic 6/6; Docker→:8001 health 200
  Contract touched: yes (v1.1-rc1 DRAFT §1b/§1c runtime; schema không đổi)
  Next safe task: release (user duyệt) → công bố API_READY; song song AI-09 phần đặc tả
  ```

### AI-05 — Số liệu evaluation luận án (T5.3 phần AI)
- T gốc: T5.3 | Owner: claude | Status: TODO
- Depends on: AI-02, AI-03, AI-04 (hoặc dùng số thật hiện có nếu user chốt dừng thí nghiệm)
- Acceptance: bảng metric 6 model vs baseline, CI, limitation thật, khớp `.claude/evaluation_plan.md`.
- Evidence: — | Commits: — | Checkpoint: —

### AI-08 — Dọn dẹp dữ liệu/artefact làn AI an toàn (yêu cầu user 2026-10-26)
- T gốc: — | Owner: claude | Status: TODO (task lặp lại: chạy sau mỗi đợt train xong, hoặc khi một ổ chạm `BLOCKED_RESOURCE`)
- Bối cảnh 2026-10-26: C: còn 3.5 GB, D: 1.2 GB, E: 2.2 GB. Ứng viên đã thấy (nhỏ): `ai-core/_probe_ckpt/` 3.2 MB, `ai-core/_tmp_tt/` 0.7 MB
  (untracked), pytest tmp ~0.7 MB. Khảo sát `D:/data_training_ai` chưa xong (du timeout) → bước 1.
- Mục tiêu: giải phóng dung lượng **mà không mất dữ liệu cần cho phát triển tiếp, tái lập kết quả hoặc luận án**.
  Dọn dẹp không được làm dự án lùi lại: sau dọn, mọi test/smoke/manifest phải còn PASS như trước.
- Phạm vi: chỉ path làn Claude — `ai-core/**` (file không track), `inference-service/**` cache, `data/**`, `dist/kaggle/**`,
  `D:/data_training_ai/**`, file tạm do Claude tạo (pytest tmp, `__pycache__`, `/tmp/split`). **Cấm** đụng path Codex
  (`backend`, `cms`, `client`, `node_modules`, Docker image/volume/vhdx), lịch sử git, `.git`.

**Phân loại bắt buộc (mỗi mục 1 lớp, có lý do):**
| Lớp | Ví dụ | Xử lý |
|---|---|---|
| `KEEP` — không bao giờ xóa | checkpoint active 6 model (`ai-core/checkpoints/*/best.pt`, SHA trong contract); nhãn/review/rating của người (export JSON, ASR review 7/60, transcript user đã sửa, human ratings T1.6); frozen test/val (frozen30, fixed10, VIVOS/FLEURS test refs); `data/manifests/**`; file được docs/report trích làm bằng chứng metric; nguồn không tải lại được (SoccerNet đã xóa video gốc, NDA) | giữ nguyên |
| `ARCHIVE` — cần giữ nhưng không cần trên ổ làm việc | checkpoint ứng viên bị loại nhưng có số liệu trong report (vd ASR last134, MiniGPT candidate `70ec4790…`), output Kaggle các version cũ, gói dữ liệu đã dùng xong | chỉ xóa khỏi ổ làm việc **sau khi** đã có bản sao ở nơi lưu trữ user chỉ định và đã kiểm SHA bản sao |
| `REGENERABLE` — tạo lại được bằng lệnh đã ghi | `__pycache__`, pytest tmp, `_probe_*`/`_tmp_*` scratch, feature/keyframe trung gian còn nguồn gốc + lệnh trích lại, zip packet Kaggle còn source | xóa sau khi ghi lệnh tái tạo + user duyệt |
| `UNKNOWN` | không rõ nguồn gốc/không biết ai dùng | **không xóa**, hỏi user |

**Quy trình (không bỏ bước):**
1. **Điều kiện trước:** không có job train/Kaggle/eval đang chạy; không server nào phục vụ thư mục ứng viên (vd ASR review :8891 dùng
   `D:/data_training_ai/asr_domain_expansion_v2_20261022` → KEEP khi AI-02b chưa xong); output Kaggle mới nhất đã tải về
   (Kaggle chỉ giữ version mới nhất).
2. **Khảo sát chỉ đọc:** kích thước, ngày sửa, số file, SHA256 (file ≤ vài GB; thư mục lớn: danh sách file + size), và **ai tham chiếu**
   (grep path trong `docs/`, `data/manifests/`, `ai-core/`, `inference-service/`, `coordination/`, `.claude/`). Có tham chiếu → không
   được `REGENERABLE` trừ khi tham chiếu chỉ là lịch sử và user đồng ý.
3. **Manifest dọn dẹp:** `coordination/claude/cleanup/CLEANUP_<YYYY-MM-DD>.md` + `.json` (path, size, sha256/file-list, lớp, lý do,
   tham chiếu, lệnh tái tạo nếu có, dung lượng dự kiến giải phóng). Commit trước khi xóa bất cứ gì.
4. **User duyệt từng nhóm** trong manifest. Không duyệt = không xóa.
5. **Thực hiện theo lớp:** `ARCHIVE` → sao chép sang nơi lưu trữ user chỉ định (ổ ngoài/cloud) → kiểm SHA bản sao → mới xóa bản gốc.
   `REGENERABLE` → xóa từng path đã duyệt (không wildcard rộng, không `rm -rf` ở thư mục gốc dự án/ổ, không `git clean`).
   Lưu ý: chuyển vào Recycle Bin hay thư mục `_trash` **cùng ổ không giải phóng dung lượng** — chỉ dùng làm bước đệm khi user muốn
   có thời gian kiểm tra trước khi xóa hẳn.
6. **Kiểm sau dọn:** ai-core pytest + inference pytest PASS; 6 checkpoint nạp `stub_mode=false`, SHA khớp contract; script kiểm mọi path
   trong `data/manifests/*.json` còn tồn tại (hoặc có trong danh sách `ARCHIVE` kèm nơi lưu); ASR review/label tool còn mở được nếu đang dùng.
   Có FAIL → dừng, khôi phục từ bản lưu trữ/trash, báo user.
7. **Ghi kết quả:** dung lượng trước/sau từng ổ, danh sách đã xóa/đã lưu trữ, bằng chứng bước 6 → manifest + Evidence task này.
   Ảnh hưởng tới Codex (vd đổi đường dẫn checkpoint) → append handoff trước khi đổi.

- Acceptance mỗi đợt: manifest đã duyệt, dung lượng giải phóng đo được, bước 6 PASS, 0 mục `KEEP`/`UNKNOWN` bị đụng.
- Không bao giờ: xóa để "cho chắc"; xóa thứ duy nhất chứng minh một con số trong báo cáo/luận án; xóa nhãn người; xóa mà không có
  manifest + duyệt; rewrite lịch sử git để giảm `.git`.
- Đợt #1 (2026-10-26, user uỷ quyền tự quyết): **DONE** — xóa 6 mục REGENERABLE trên D:, giải phóng 5,530,226,688 byte
  (D: 1.22 → 6.75 GB); ai-core 285 PASS, inference 37 PASS/1 skip, SHA 6 checkpoint không đổi, server :8891 HTTP 200.
  Manifest + kết quả: `coordination/claude/cleanup/CLEANUP_2026-10-26.md`. Task vẫn TODO cho các đợt sau.
- Đợt #2 (2026-10-30, user duyệt 4 nhóm): **DONE** — xóa 4 parquet gốc công khai có checksum (tin tức + FLEURS train/val) + 4 thư mục scratch
  `D:/tmp`; D: 0.84 → 7.1 GB; ai-core 319, inference 81/10, 6 checkpoint SHA khớp, manifest path 0 thiếu. `coordination/claude/cleanup/CLEANUP_2026-10-30.md`.
- Evidence: VERIFIED-NOW 2026-10-26 (đợt #1, xem manifest) | Commits: `a5f340f` (manifest trước khi xóa) + commit kết quả | Checkpoint: SESSION.md

### AI-06 — Xác minh nguồn checkpoint + thang sẵn sàng 6 model (ƯU TIÊN 1)
- T gốc: T1.8 | Owner: claude | Status: DONE (2026-10-26)
- Depends on: — | Blocks: AI-01, AI-04, AI-07
- Vấn đề: `inference-service/.env` (local, không commit) trỏ `CHECKPOINT_DIR=D:/data_training_ai/checkpoints` — thư mục đó chỉ có
  4/6 (`asr_ctc`, `highlight_fusion`, `siamese`, `two_tower`), **thiếu `vit`, `minigpt`** → uvicorn local fail khởi động.
  `E:/traning_ai/ai-core/checkpoints` có đủ 6 (SHA ở INVENTORY §3).
- Việc: (1) xác minh 2 checkpoint thiếu: tìm mọi bản `vit`/`minigpt` trên D:/E: (+ output Kaggle đã tải), so SHA với bản active
  `192d90e4…` / `cf9cfa71…`, ghi bản nào là gốc; (2) so SHA 4 model trùng tên giữa D: và E:; (3) chốt 1 nguồn canonical cho
  local + runtime :8001, sửa `.env` local, ghi `inference-service/README.md`; (4) lập bảng thang sẵn sàng cho từng model.
- Thang sẵn sàng (ghi riêng từng mức, có bằng chứng; mức sau chỉ khi mức trước đạt):
  `DECLARED` (có trong registry) → `CKPT_PRESENT` (file + SHA ở nguồn canonical) → `LOADED` (`registry.load_all`, không degraded) →
  `ENDPOINT_OK` (HTTP thật qua uvicorn, Bearer, response đúng schema) → `API_READY` (chỉ trong AI-01 khi có ví dụ thật đóng gói).
  "AI_READY" trong quyết định user = `API_READY` này. Model chưa kiểm chứng đủ mức → không `API_READY`.
- Acceptance: bảng 6 model × 4 mức đầu với lệnh + output + SHA trong `coordination/claude/api/AI_API_CONTRACT.md` mục 1b;
  không xóa/ghi đè dữ liệu trên D:; search/recommendation ghi rõ mức đạt được nếu Milvus chưa có.
- Evidence (đã có từ AI-00, VERIFIED-NOW 2026-10-26, gọi `app.services` trực tiếp — chưa qua HTTP): 6/6 CKPT_PRESENT + LOADED từ
  `E:/traning_ai/ai-core/checkpoints`; vision/asr/highlight/completions chạy; search/recommendation 503 (Milvus tắt).
- Evidence (AI-06, VERIFIED-NOW 2026-10-26, chi tiết `coordination/claude/evidence/AI-06_2026-10-26/README.md`):
  - `find D:/ E:/ … *.pt` (142 file) + `sha256sum`: vit active `192d90e4…` chỉ ở E: (`ai-core/checkpoints` ≡ `dist/kaggle/output/vit/vit_s1338`, gốc Kaggle seed 1338);
    minigpt active `cf9cfa71…` ở E: ≡ D: `minigpt_news/output-v2/news_run/minigpt/best.pt` (gốc) + 4 `pretrain.pt` upload; vocab `649ffc66…` khớp.
    4 model trùng tên D: ≡ E: (best + last). `sha256sum -c` 8 file D: sau task → 8/8 OK, không ghi/xóa gì trên D:.
  - Canonical = `E:/traning_ai/ai-core/checkpoints`; `.env` local `CHECKPOINT_DIR` đổi từ D: sang đây (không commit); `inference-service/README.md` ghi lại.
  - Startup production `uvicorn app.main:app` khi Milvus tắt → `Application startup failed` (MilvusException localhost:19530), exit 3.
  - Launcher bỏ Milvus preflight + `http_ladder.py` trên :8011 → 9/9 PASS: health `stub_mode=False`/6 model/`degraded=[]`; 401 thiếu+sai Bearer;
    vision/asr/highlight/completions 200 + schema hợp lệ; search/recommendation 503 `AI_UNAVAILABLE`.
  - `pytest inference-service/tests` → 37 passed, 1 skipped.
  - Lỗi vận hành phát hiện: không `PYTHONUTF8=1` trên Windows → `services._warn` UnicodeEncodeError → search 500 plain-text thay vì 503. Ghi README/contract; chưa sửa code.
  - Kết quả thang (contract §1b): vit/asr_ctc/highlight_fusion/minigpt = `ENDPOINT_OK*` (* launcher bỏ Milvus preflight); siamese/two_tower = `LOADED` (cần Milvus).
    Không model nào `API_READY`. Startup production đầy đủ ⇐ Milvus của Codex (AI-07).
- Commits: 91b0242 (nhận task), 8d1f053 (evidence + README + contract v0.2 + REL) | Checkpoint:
  ```
  Lane: claude
  Changed: inference-service/README.md, coordination/claude/{api/AI_API_CONTRACT.md,HANDOFF_OUT.md,TASKS.md,SESSION.md,evidence/AI-06_2026-10-26/**}; .env local (không commit)
  Verified: SHA 6 model + D: 8/8 unchanged; uvicorn HTTP ladder 9/9 PASS; prod startup fail khi Milvus tắt (đúng thiết kế); inference pytest 37 passed/1 skipped
  Contract touched: yes (AI-API v0.2 DRAFT, chỉ tài liệu §1b, schema không đổi)
  Next safe task: AI-01
  ```

---

## Lịch sử (chuyển nguyên văn từ `.claude/plan/00_master_plan.md` ngày 2026-10-26)

Follow-up T1.4/T1.6 trước tách làn. Log chi tiết hơn: `.claude/TodoWrite.md` (đóng băng).

### Từ master §3, các dòng thụt lề dưới T1.4

  ASR robustness follow-up **TRAIN/EVAL DONE — VIDEO VALIDATION PENDING (xác nhận2026-10-19)**: Kaggle ai-core-asr-robust v2 COMPLETE, TeslaT4/FP16/seed1337/4000steps, best3500 theo validation; output đã tải trênD:/data_training_ai/asr_robust/outputs-v2. Paired test VIVOS760: WER36.0519→32.9727%/CER13.5446→12.4467% (PASS20/45); FLEURS857: WER76.7465→53.6727%/CER50.5133→23.9063%, vẫn lỗi cao. VIVOS+human FLEURS train≈22.0073h/13557mẫu sau4CTC exclusions, không dùngYouTube30/Whisper drafts; head93→133 giữ prefix, encoder/loss không đổi. Full logs4sanity+step1→4000, checkpoint/config/metric arithmetic/hashes verified; trainVRAM allocated1.203/reserved3.039GiB≤8, chưa chứng nhận inference4GiB. Candidate SHA d03ef0a962220618e90e5ff478a2fbab5ff35dd68deb539a4933eb7c15a4f3de, chưa deploy; activeASR/MiniGPT giữ nguyên. Chỉ1seed, human video refs0/30; fullT1.6 human quality chưa đánh giá lại. @docs/T1.4_asr_robust_training.md; @data/manifests/asr_robust_training.json.
  Real-video paired pilot **DONE TECHNICAL / HUMAN REFERENCES PENDING (2026-10-19)**: sample_01/10/28×ASR cũ/candidate→cùngMiniGPT,6ASR+6summary nonempty, oldASR text3/3 khớp frozen; production helpers/20s/CPUFP32/Torch2.13/temp0/max96, không deploy. Packet D:/data_training_ai/minigpt_real_video_20261015/asr_candidate_comparison_3_20261019/review.html có video/side-by-side/form lời chuẩn+exportCSV riêng; model/media/ref/ratings SHA giữ nguyên. 3tests+browser playback/exportCSV Unicode/desktop+mobile/QC+Go/CMS/Client FULL PASS. Candidate còn transcript nhiễu; MiniGPT vẫn lặp/thêm chi tiết ngoài transcript. Humanrefs0/3 và0/30, CER/WER/điểm human mới null; sharedmean1.6/5/fullT1.6 chưa đổi. @docs/T1.4_asr_candidate_video_pilot.md.
  User feedback + direct-draft control (2026-10-19): user xác nhận đúng nội dung3draft; candidate-ASR MiniGPT card1/3sai,card2đúng. Chạy trực tiếp chính3draft→cùngMiniGPT/temp0/max96 vẫn lỗi: sample10lặp an ninh, sample28lệch tiểu sửNewton;3outputs tái lập cached summaries. Giữ rawfeedback+scopedjudgments, không suy thành điểm1–5/rawASRaccuracy/CER-WERđộc lập; không train/deploy hoặc sửa original refs/weights. @docs/T1.6_confirmed_draft_diagnostic.md.
  MiniGPT pipeline diagnostic **DONE (2026-10-19)**:3draft222/250/271BPEtokens<411, lỗi xảy ra single-pass. Real BPE prefix253train+8val/mask-EOS8val/cachefullforward8steps PASS; audit256train/253sum:144source và11target bị cắt. Train75581sum/303581instances nhưng checkpoint selection chỉ titleROUGE; fixedval129–136sumRL0.174967 vsLead0.209702 (8mẫu chẩn đoán, không globalmetric),3longinputs rawtoken coverage PASS nhưng1reduce lặp94.68%trigram; short inputs vẫn sai ngày/số/entity. No test tuning/weight/production/contract change;16Python tests+4subtests, Go/CMS/Client PASS; Docker engine off. Next: grounded human target dataset/complete labels +sum-based selection +separate long-input quality, chưa tự train/deploy; fullT1.6 vẫn FAIL. @docs/T1.6_pipeline_diagnostic.md; @data/manifests/minigpt_pipeline_diagnostic.json.
  Summary data/recipe **PREPARATION DONE — LABEL AUDIT PENDING (2026-10-19)**: strictscreen76k/4k→391/24; pinnedrawprefix197135rows adds593/40, final984train/64val, preserve originalsplits/reservehash95/5/exclude1000frozenIDs fromIDindex only. Editorialbody/sapo +syntheticASR, no generated/video-test labels/source-target truncation. New opt-in sum-aligned-v1 chooses pairedclean/noisy sumRL, title/cap regression;4clean+1noisypasses=248/62steps/eval62, legacyprofile unchanged. Existingcheckpoint baseline64cases cleanRL0.290132 vsLead0.407114, noisy0.175906 vs0.115482, mean0.233019 (developmentonly/noimprovementclaim). 8384itemchecks/4productionparity/31tests+4subtests/Go/CMS/Client PASS. 48blankauditrows gate training; privatebundle/codezip/owninitcopy verified, noKagglejob/deploy/model/APIchange. Next: human label audit +resolve/reversion/provenance, then smallcandidate train; realtranscriptdomaintransfer unproven/fullT1.6 stillFAIL. @docs/T1.6_aligned_summary_preparation.md; @data/manifests/minigpt_aligned_summary.json.
  Label preflight follow-up **V2 DATA DONE / HUMAN AUDIT PENDING (2026-10-19)**: previous ending check admitted terminal ../.../Unicode ellipsis; corrected shared filter/trainer gate rejects50train+3val. V2=956train/64val, all53 excluded, retained IDs keep split/61val retained+3new, original files/hashes preserved. 4CPU sanity items+41tests/4subtests+8160encodedchecks/4productionparity+Go/CMS/Client PASS. Unchanged checkpoint baseline cleanSumRL0.294504 vsLead0.415168/noisy0.173516 vs0.114252; no trained improvement claim. Budget240/60/eval60. Mechanical evidence48 stored separately, no human verdicts filled;48blankannotations still gate candidate training. No job/deploy/model/API/frozen-eval change; fullT1.6 stillFAIL. @docs/T1.6_label_preflight.md; @data/manifests/minigpt_label_preflight.json.

### Từ master cuối file (sau §5.4)

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
