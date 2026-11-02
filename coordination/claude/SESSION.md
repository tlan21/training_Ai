# SESSION — làn Claude (điểm resume)

Cập nhật + commit sau mỗi bước (`chore(claude-progress): ...`). Phiên mới đọc file này trước TASKS.md.

## Phiên đang chạy
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
