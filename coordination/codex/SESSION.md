# SESSION — làn Codex (điểm resume)

Cập nhật + commit sau mỗi bước (`chore(codex-progress): ...`). Phiên mới đọc file này trước TASKS.md.

## Phiên đang chạy
- Task: INT-00 (IN_PROGRESS 2026-10-26)
- Bước đã xong: branch codex/integration đúng; tree sạch; HEAD/master = 96ebc24 (Release #1).
  Đọc README/PROJECT_STATUS/master plan/inventory, HC-02/HC-03 và AI-API v0.1 DRAFT từ Claude 91b0242.
  Áp dụng ownership runtime/checkpoint, INT-10 deferred và dependency không chặn AI.
  Docker 28.4.0 đang chạy; stack video-ai cũ dừng, image/volume video-ai_* còn đủ; không tạo project mới.
  E: 2.19 GiB, C: 3.48 GiB, D: 6.08 GiB; RAM free ~446 MiB lúc đo. Chưa build/pull.
- Bước kế: dependency theo HC-03 (E sau npm ci ≥1.5 GiB); mock HTTP + gateway health + compose không checkpoint;
  chỉ chạy stack khi tài nguyên đủ, không xóa dữ liệu/cache.
- File đang sửa: AGENTS.md, coordination/codex/{TASKS,SESSION,HANDOFF_OUT}.md
- Lệnh verify dở: —

## Task kế an toàn
INT-00 (dependency + stack hiện hữu + mock HTTP, không checkpoint) → INT-01 DB/mock → INT-02.
Việc không cần Docker có thể làm trước: INT-04 bước sửa OpenAPI + regen types (vẫn phải test lại khi stack chạy).

## Phiên trước
- 2026-10-26 — Claude khởi tạo file này trong AI-00 (tách làn). Codex chưa chạy phiên nào.
