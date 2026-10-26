# SESSION — làn Claude (điểm resume)

Cập nhật + commit sau mỗi bước (`chore(claude-progress): ...`). Phiên mới đọc file này trước TASKS.md.

## Phiên đang chạy
- Task: AI-08 đợt #1 (dọn D:, user uỷ quyền tự quyết 2026-10-26) — IN_PROGRESS
- Bước đã xong: 1 điều kiện trước · 2 khảo sát · 3 manifest `coordination/claude/cleanup/CLEANUP_2026-10-26.md`
- Bước kế: 5 xóa đúng 6 path trong manifest mục 1 → 6 kiểm sau dọn → 7 ghi kết quả
- File đang sửa: manifest trên
- Lệnh verify dở: —

## Task kế an toàn
AI-06 (ưu tiên 1: xác minh vit/minigpt thiếu ở D:, thang sẵn sàng 6 model) → AI-01 → AI-07 (runtime :8001 cho Codex).
Khi chờ (Kaggle/người duyệt): AI-03a (soạn 40 summary), AI-02a (đề xuất 53 clip ASR), AI-04 (VRAM sơ bộ T4).
AI-02b/AI-03b chờ user duyệt. Runtime :8001: DOWN (chưa chạy).

## Phiên trước
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
