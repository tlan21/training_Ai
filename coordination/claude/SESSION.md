# SESSION — làn Claude (điểm resume)

Cập nhật + commit sau mỗi bước (`chore(claude-progress): ...`). Phiên mới đọc file này trước TASKS.md.

## Phiên đang chạy
- Task: — (không có task IN_PROGRESS; chờ user trước khi sang AI-01)
- Bước đã xong: —
- Bước kế: —
- File đang sửa: —
- Lệnh verify dở: —

## Task kế an toàn
AI-01 (phát hành contract v1; AI-06 DONE) → AI-07 (runtime :8001, cần Milvus của Codex — startup thật fail khi Milvus tắt).
Khi chờ (Kaggle/người duyệt): AI-03a (soạn 40 summary), AI-02a (đề xuất 53 clip ASR), AI-04 (VRAM sơ bộ T4).
AI-02b/AI-03b chờ user duyệt. Runtime :8001: DOWN (chưa chạy).

## Phiên trước
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
