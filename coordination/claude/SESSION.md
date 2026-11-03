# SESSION — làn Claude (điểm resume)

Cập nhật + commit sau mỗi bước (`chore(claude-progress): ...`). Phiên mới đọc file này trước TASKS.md.

## Phiên đang chạy
- **2026-11-03 (D29, user "xóa tóm tắt và làm bước tiếp theo training tóm tắt… bóng đá"):** xóa 5 tóm tắt bịa (c0c4261, `evidence/SUMMARY-CLEANUP_2026-11-03/`).
  AI-24 IN_PROGRESS: Kaggle `traininghighlight/ai-core-minigpt-football-v1` v1 RUNNING (dataset `minigpt-football-v1`, code 807079d/8ef8e07).
  Xong → TẢI OUTPUT NGAY (Kaggle chỉ giữ bản mới nhất) vào `D:/data_training_ai/minigpt_football_v1/output_v1/`, đọc `football_run/gate/football_gate.json`.
  Gate PASS → đề xuất user thay checkpoint (image inference mới + parity); FAIL → báo số liệu, không promote. AI-25: tìm nguồn CC (chỉ metadata) chờ user duyệt.
- **2026-11-03 (API 0.10.0 transcript_quality, "tiếp tục task"):** C: đầy → Docker treo, 7 container infra exit 255 → `docker start` lại, healthy. Commit 6601bd0:
  tỉ lệ âm tiết tiếng Việt (VIVOS 4.859) trong phụ đề; <0.7 không tóm tắt AI, CMS/Client nhãn "CHẤT LƯỢNG THẤP". Go vet/test/build, CMS tsc, Client tsc PASS (lint host lệch ESLint 8.57 → chạy trong Docker build).
  User duyệt prune build cache (20,26 GB trong ổ Docker). Gateway/CMS/Client `int10-6601bd0` deployed healthy; CMS fixture 64 PASS; live regenerate 422 (a51464d,
  `evidence/API-0.10.0_2026-11-03/`). Còn: kế hoạch train domain bóng đá; summary AI cũ của video chất lượng thấp vẫn giữ (chờ user).
- **2026-11-03 (user test 2 video bóng đá CC BY-SA):** 6 model nạp đúng (stub=false). Không có đề xuất highlight = đúng recipe (min_video 120 s, τ 51; video 123 s max 40.5). Phụ đề rỗng = âm thanh Pháp/khán giả, ASR chỉ tiếng Việt (ngoài miền CER 50–58%, D23). Lỗi thật: MiniGPT bịa tóm tắt từ transcript gần rỗng → sửa 26bd596 (≥20 từ mới tóm tắt, bỏ đoạn ASR rỗng, CMS giải thích); gateway/CMS `int09-26bd596`, CMS fixture 78 PASS. 2 video cũ vẫn giữ dữ liệu cũ (chờ user: xóa+tải lại hay để Claude dọn).
- **2026-11-03 (API 0.9.0, user "làm mục A"):** feed category_id + view_count, CMS sort/category_assigned_at (migration 007 áp live, dữ liệu không đổi), header search inline. Gateway `int09-85436a3`, CMS/Client `int09-32083e5`, 175 PASS. INT-05/06/14/50 DONE. Còn mở: INT-03 (AI-12/D19), INT-07/08 (GPU), INT-09 docs, AI-05 §7, AI-12, AI-04.
- **2026-11-03 (L items UI):** INT-04 DONE (client `int06-387ec2a`); INT-05 L xong (CMS `int05-0316dc6`, fixture 77 PASS), còn Danh mục 'N phút trước' cần field API. Còn mở chỉ là mục cần đổi API/owner: view_count feed, search inline, lọc clip theo danh mục, mốc gán danh mục.
- **2026-11-03 ("tiếp tục theo bạn đề xuất"):** INT-06 quyết định owner áp dụng (client `int06-73b13e3`); REVIEW 15 task INT đóng
  (`evidence/REVIEW_2026-11-03/README.md`), INT-17 vá follow-redirects (client `int06-e33e956`, 96/96 PASS). Gate: INT-03 chặn (NO_DATA, AI-12/D19),
  INT-07/08 chặn (máy này không có GPU; cần RTX 3060/GPU user chấp nhận), INT-09 chỉ chuẩn bị được phần ổn định. Chờ user chọn hướng.
- **2026-11-03 ("tiếp tục task"):** INT-05 owner decisions áp dụng (CMS `int05-fd0b418`). INT-06/04/14 batch Stitch Client xong một lượt: client `int06-a52a911`,
  gateway `int06-d41fe71` (sửa `/api/videos` 500), regression 96/96 PASS, QA viewer đã xóa, preservation OK (`evidence/INT-06_2026-11-02/README.md`).
  INT-04/06/14 vẫn PARTIAL: 7 quyết định owner + L items. Kế tiếp: đối chiếu REVIEW (16 task) → gate INT-03/07/08/09 → AI-05 §7, AI-12, AI-04.
- **2026-11-02 (user "kéo lại 2 cho phép xóa…"):** `D:/data_training_ai/highlight_news_v1/` khôi phục từ Kaggle `traininghighlight/highlight-news-v1`
  (highlight_news_labeled.pt sha256 49dca3e1…, intake_report.json; xem PROVENANCE.md tại đó — export JSON gốc/features_news/proposals không khôi phục được).
  Xóa danh mục chỉ còn video đã xóa: DONE (gateway int50-83bacd4). INT-43 DONE. Đang: INT-05 đối chiếu Stitch (4 agent soát 8 màn).
- **INT-50 batch (2026-11-02):** real QA 10/10 PASS (`coordination/claude/evidence/INT-50_2026-11-02/README.md`); INT-41/42/44/47/49/38 DONE; INT-50 PARTIAL (Stitch ⇒ INT-05); INT-43 PARTIAL (phân trang, bulk request). CMS chạy `int50-045988a`.
  ⚠ Phát hiện: `D:/data_training_ai/highlight_news_v1/` (nhãn người tin tức vòng 8 + features train, KEEP theo AI-08 đợt #2) KHÔNG còn trên D:/E: — chưa rõ ai xóa; đã báo user; bản sao có thể ở Kaggle `traininghighlight/highlight-news-v1`.
  Câu hỏi sản phẩm chờ user: danh mục chỉ còn video đã xóa mềm vẫn 409 (giữ theo thiết kế Codex).
- **HO-05 nhận (2026-11-02):** Claude làm toàn bộ dự án; backlog `coordination/claude/OPEN_TASKS.md`. INT-50 chờ user duyệt QA thật + kiểm dung lượng ổ (E: 332 MB). Song song: đối chiếu REVIEW.
- **HC-19 đóng (2026-11-02):** inference v3.0 chạy trong compose (Codex INT-57), Claude đã kiểm. D24 xong phía AI. Còn: AI-05 REVIEW (§7), AI-12 ⇐ INT-15, AI-04 ⇐ RTX 3060.
- **Release #7 (2026-11-02):** AI-23 DONE (AI-API v3.0) lên master. Chờ RE:HC-19; AI-05 REVIEW chờ user chọn §7.
- **AI-23 REVIEW (2026-11-02):** AI-API v3.0 (gỡ /v1 lưu trữ + MinIO/Milvus), image `ai-v3.0-48735ff` parity PASS; chờ user duyệt release; HC-19.
- **Release #6 (2026-11-02):** master ← claude/ai-core (AI-15 DONE, AI-22 DONE, AI-05 REVIEW, D27). Mở: HC-17, HC-18; AI-05 chờ user chọn §7.
- **AI-15 REVIEW (2026-11-02):** cutover bước 2 xong trên branch (v2.0 API_READY, v1.5); chờ user duyệt release; bước 3 ⇐ RE:HC-17.
- **AI-05 REVIEW (2026-11-02):** `evidence/AI-05_2026-11-02/SO_LIEU_LUAN_AN.md`; chờ user chọn bổ sung §7.
- **AI-22 DONE phần Claude (2026-11-02):** runtime AI = container Docker. Image `video-ai-inference:ai-v1.4-62b7e05` parity PASS; HC-16 chờ Codex đổi tag compose. Host :8001 không chạy (dự phòng dev).
- Task: **AI-16 REVIEW (2026-10-29)** — highlight vòng 5 ACTIVE trên :8001 (PID 14896); chờ release. Rollback: `_archive/highlight_fusion_round3_becbd378/`.
- **AI-17 REVIEW:** vòng 6 ACTIVE trên :8001 (PID 27064). Rollback `_archive/highlight_fusion_round5_34199b68/`.
- **AI-18 REVIEW:** vòng 7 ACTIVE trên :8001 (rollback `_archive/highlight_fusion_round6_9b59a7b0/`).
- **AI-19 DONE / AI-20 DONE (giữ vòng 7).** :8001 PID 19884 (vòng 7 active).
- **Release #5 (2026-10-30):** làn AI lên master (AI-API v1.4 + v2.0 DRAFT, D24–D26). :8001 PID 19220 = vòng 8 ×10. Còn mở: AI-15 ⇐ RE:HC-13; AI-12 ⇐ INT-15; AI-04 ⇐ RTX 3060; AI-05.
  mở `D:/data_training_ai/highlight_news_v1/label_news.html` → xuất `highlight_news_labels.json` → Claude chạy
  `dist/kaggle/kernel-fusion-r8/intake_news_labels.py` → đăng ký + train vòng 8 (bóng đá + tin tức).
  **Runtime :8001 UP PID 15852** (code AI-15: /v1 + /v2, worker cùng tiến trình); gateway Codex trỏ :8001 thật. Dataset Kaggle `ai-model-worker-v1` uploaded, kernel chưa push.
- Bước kế: đọc RE:HC-13 → release (user duyệt) → /v2 API_READY, /v1 DEPRECATED → gỡ minio/pymilvus. Release cũng là lúc ghi D24 + sơ đồ đích vào
  PROJECT_STATUS / master plan / kien_truc_va_thuat_toan_ai.md (file chung, theo yêu cầu user 2026-10-29).
- File đang sửa: —
- Lệnh verify dở: —
- Trước đó (2026-10-28): D23 ASR/MiniGPT dừng cải thiện cho MVP; HC-12. AI-12 ⇐ INT-15; AI-04 nghiệm thu ⇐ RTX 3060.

## Task kế an toàn
AI-10 (health/degraded, D15) → AI-07 (:8001 thật + UTF-8, D16) → chuẩn bị release, user duyệt push → công bố API_READY. Chờ: AI-09 (⇐ HC-04).
Giữ `D:/tmp/ai06_20261026/`, `D:/tmp/ai01_20261026/` (D17, không dọn).
Khi chờ (Kaggle/người duyệt): AI-03a (soạn 40 summary), AI-02a (đề xuất 53 clip ASR), AI-04 (VRAM sơ bộ T4).
AI-02b/AI-03b chờ user duyệt. Runtime :8001: DOWN (chưa chạy).

## Phiên trước
- 2026-10-26 — AI-01 DONE: AI-API v1.0, 6 endpoint API_READY, recommendation DRAFT (Milvus thiếu collection reco); openapi + 23 examples thật;
  live smoke 6/6 (real + synthetic); sửa warmup search Milvus. Commits 3fd0259, 2d34c24. Runtime :8001 DOWN. File tạm `D:/tmp/ai01_20261026/`.
- 2026-10-26 — AI-06 DONE: canonical `E:/traning_ai/ai-core/checkpoints` (vit chỉ ở E:, gốc Kaggle vit_s1338; minigpt gốc D: news_run);
  thang §1b: 4 model ENDPOINT_OK* (launcher bỏ Milvus preflight), siamese/two_tower LOADED (Milvus tắt); HTTP 9/9 PASS; inference 37 PASS/1 skip;
  contract v0.2 DRAFT. Phát hiện: Windows cần `PYTHONUTF8=1`; startup thật cần Milvus. Commits 91b0242, 8d1f053. File tạm `D:/tmp/ai06_20261026/`.
- 2026-10-26 — AI-08 đợt #1 DONE: xóa 6 mục REGENERABLE trên D: (manifest `coordination/claude/cleanup/CLEANUP_2026-10-26.md`),
  D: 1.22 → 6.75 GB; ai-core 285 PASS, inference 37 PASS/1 skip, SHA checkpoint không đổi. Task kế: AI-06.
- 2026-10-26 — Release #1: master ff 39ff344 → 96ebc24 (user duyệt), Codex worktree ff sạch; ghi D9–D12, HC-03 (Milvus, dung lượng C:/E:).
  Task kế: AI-06 (chưa bắt đầu).
- 2026-10-26 — Ghi quyết định user D1–D8 (PROJECT_STATUS mục 5): tách AI-02a/b/c, AI-03a/b/c; thêm AI-07; AI-04 TODO (sơ bộ T4);
  contract v0.1 (thang sẵn sàng, runtime :8001 thuộc Claude); rút HC-01, mở HC-02 cho Codex. Chỉ tài liệu.
- 2026-10-26 — AI-00 tách làn + kiểm kê.
  ```
  Lane: claude
  Changed: coordination/**, AGENTS.md, .claude/CLAUDE.md, .claude/plan/00_master_plan.md §0/§3/§5.4, my-agent/agent/instructions.md §4.0
  Verified: ai-core pytest 285 passed; inference pytest 37 passed/1 skipped; 6 ckpt nạp thật stub_mode=false; Go vet/test/build, CMS tsc/build, Client tsc/lint/build PASS
  Contract touched: no (AI API Contract v0 DRAFT mới tạo, chưa đổi code)
  Next safe task: AI-06
  ```
