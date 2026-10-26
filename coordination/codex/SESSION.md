# SESSION — làn Codex (điểm resume)

Cập nhật + commit sau mỗi bước (`chore(codex-progress): ...`). Phiên mới đọc file này trước TASKS.md.

## Phiên đang chạy
- Task: INT-00 (IN_PROGRESS 2026-10-26)
- Bước đã xong: branch codex/integration đúng; tree sạch; HEAD/master = 96ebc24 (Release #1).
  Đọc README/PROJECT_STATUS/master plan/inventory, HC-02/HC-03 và AI-API v0.1 DRAFT từ Claude 91b0242.
  Áp dụng ownership runtime/checkpoint, INT-10 deferred và dependency không chặn AI.
  Docker 28.4.0 đang chạy; stack video-ai cũ dừng, image/volume video-ai_* còn đủ; không tạo project mới.
  E: 2.19 GiB, C: 3.48 GiB, D: 6.08 GiB; RAM free ~446 MiB lúc đo. Chưa build/pull.
- Bước kế: hoàn tất cross-compile Linux đang chạy; bật stack hiện hữu tuần tự với image cũ + binary mới bind :ro;
  kiểm health gateway/mock, DB integration. Client tsc/lint/build đã PASS; CMS tsc/build PASS; Go vet/build/test -p1 PASS.
- File đang sửa: backend mock/config/client HTTP + Dockerfile; compose default/mock/GPU; .env.example/.gitignore;
  e2e/README.md; coordination/codex/{TASKS,SESSION,INTEGRATION_MATRIX,verification/INT-00}.md
- Lệnh verify dở: Linux `CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -p 1 ...` (gateway + ai-mock).
- Dependency đã cài: npm ci CMS 100 packages, Client 395 packages, E: sau cài 1.79 GiB.
- Giới hạn thực tế: lượt Go/CMS đầu thiếu RAM khi bật infra; đã stop 6 container vừa bật, chạy lại PASS.
  C: sau tăng bộ nhớ hệ thống ~1.92 GiB; không build/pull image mới. Dữ liệu/volume giữ nguyên.
- Evidence: coordination/codex/verification/INT-00.md (đang bổ sung), matrix MOCK_ONLY hiện tại; HIST giữ nguyên.

## Task kế an toàn
INT-00 (dependency + stack hiện hữu + mock HTTP, không checkpoint) → INT-01 DB/mock → INT-02.
Việc không cần Docker có thể làm trước: INT-04 bước sửa OpenAPI + regen types (vẫn phải test lại khi stack chạy).

## Phiên trước
- 2026-10-26 — Claude khởi tạo file này trong AI-00 (tách làn). Codex chưa chạy phiên nào.
