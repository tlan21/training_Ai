# SESSION — làn Claude (điểm resume)

Cập nhật + commit sau mỗi bước (`chore(claude-progress): ...`). Phiên mới đọc file này trước TASKS.md.

## Phiên đang chạy
- Task: — (không có task IN_PROGRESS)
- Bước đã xong: —
- Bước kế: —
- File đang sửa: —
- Lệnh verify dở: —

## Task kế an toàn
AI-06 (sửa nguồn checkpoint local) → AI-01 (phát hành AI API Contract v1).
AI-02/AI-03 chờ user; AI-04 chờ GPU.

## Phiên trước
- 2026-10-26 — AI-00 tách làn + kiểm kê.
  ```
  Lane: claude
  Changed: coordination/**, AGENTS.md, .claude/CLAUDE.md, .claude/plan/00_master_plan.md §0/§3/§5.4, my-agent/agent/instructions.md §4.0
  Verified: ai-core pytest 285 passed; inference pytest 37 passed/1 skipped; 6 ckpt nạp thật stub_mode=false; Go vet/test/build, CMS tsc/build, Client tsc/lint/build PASS
  Contract touched: no (AI API Contract v0 DRAFT mới tạo, chưa đổi code)
  Next safe task: AI-06
  ```
