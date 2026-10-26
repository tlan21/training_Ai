# HANDOFF_OUT — Claude → Codex (append-only)

Chỉ Claude ghi. Mỗi mục: `## <ngày> <ID> — <tiêu đề>` + nội dung + trạng thái. Không sửa mục cũ; đính chính bằng mục mới.
Loại mục: `REL` (phát hành AI API version), `RE:HO-xx` (phản hồi yêu cầu Codex), `HC-xx` (Claude yêu cầu Codex).

---

## 2026-10-26 REL AI-API v0 — DRAFT (chưa API_READY)
- Contract: `coordination/claude/api/AI_API_CONTRACT.md` v0.
- Trạng thái mọi endpoint: `DRAFT`. Codex dùng mock (`mocks.AIClientMem`, `FORCE_STUB=1`) hoặc :8001 thật hiện có,
  nhưng chưa được đánh `INTEGRATED_REAL` mới cho tới khi AI-01 phát hành v1 `API_READY`.
- Các tích hợp đã chạy thật trước tách làn (T4.1/T4.2, 2026-10-14) vẫn là bằng chứng lịch sử hợp lệ;
  ghi `INTEGRATED_REAL (HIST)` trong matrix.
- Lưu ý kỹ thuật đã xác minh 2026-10-26: `/v1/highlight` yêu cầu `vision_embeddings` 256-d (đầu ra ViT) +
  `audio_spectrogram_features` 64-d, gửi sai chiều → 503 `AI_UNAVAILABLE`. Search/recommendation trả 503 khi Milvus tắt.

## 2026-10-26 HC-01 — Mount checkpoint cho worktree Codex
- Worktree `E:\traning_ai-codex` không có `ai-core/checkpoints/` (gitignored). Compose `inference` đang mount
  `./ai-core/checkpoints` → sẽ rỗng → service fail khởi động.
- Yêu cầu: biến `AI_CHECKPOINT_DIR` (mặc định `./ai-core/checkpoints`), Codex đặt trong `.env` của worktree
  `AI_CHECKPOINT_DIR=E:/traning_ai/ai-core/checkpoints`, mount `:ro`. Claude chỉ thay `best.pt` active khi release AI API mới.
- Gắn với task Codex `INT-00`.

## 2026-10-26 HC-01 — RÚT LẠI (theo quyết định user 2026-10-26, mục 6)
- Bỏ yêu cầu mount `AI_CHECKPOINT_DIR` vào compose của Codex. Codex **không** sao chép, mount hay quản lý checkpoint của Claude.
- Thay bằng HC-02.

## 2026-10-26 REL AI-API v0.1 — DRAFT (chỉ tài liệu, schema không đổi)
- Thêm contract mục 1b (thang sẵn sàng `DECLARED → CKPT_PRESENT → LOADED → ENDPOINT_OK → API_READY`) và 1c (runtime :8001 thuộc Claude).
- Chưa endpoint nào `API_READY`. Codex dùng mock đúng contract cho tới khi AI-01 phát hành v1.

## 2026-10-26 HC-02 — Quyết định user 2026-10-26 ảnh hưởng làn Codex (Codex tự cập nhật file của mình)
Claude không sửa `AGENTS.md` / `coordination/codex/**` (giữ ranh giới, quyết định 7). Codex áp dụng ở phiên đầu:
1. **INT-00 sửa lại:** không mount/copy checkpoint, bỏ `AI_CHECKPOINT_DIR`. Phạm vi mới: `npm ci` cms+client; chạy stack hạ tầng
   (Postgres, Mongo, Redis, MinIO, Kafka, Milvus — Milvus mở `localhost:19530` để runtime :8001 của Claude dùng);
   gateway/orchestrator gọi AI qua `AI_BASE_URL` có thể trỏ (a) mock HTTP đúng contract, hoặc (b) :8001 thật trên host do Claude chạy
   (AI-07; trong Docker thường là `http://host.docker.internal:8001`). Service `inference` trong compose không được dựng từ
   checkpoint của Claude; cách tắt/thay (profile, mock) do Codex chọn.
   Acceptance gợi ý: stack chạy với mock, `/api/cms/system/health` trả health mock đúng schema; khi Claude báo :8001 UP thì đổi
   `AI_BASE_URL` không cần sửa code.
2. Sửa `AGENTS.md` mục 2 (dòng mount `AI_CHECKPOINT_DIR`) cho khớp mục 1.
3. **INT-10:** forgot-password → `DEFERRED / OUT_OF_SCOPE`. Giữ nguyên code, không xóa, không revert commit `6528c62`.
   Không tính vào phạm vi release hiện tại khi chưa được user duyệt; không phát triển thêm.
4. **Dependency đề xuất** để 2 làn không chặn nhau: INT-02 (memory → Postgres) và INT-04 (OpenAPI video gốc) không phụ thuộc AI → làm
   ngay sau INT-00. INT-01 tách: phần backend/integration DB làm được với mock; phần E2E AI thật ⇐ AI-07 (:8001 UP).
   INT-03 ⇐ AI-01 + AI-07.
5. Ghi `RE:HC-02` vào `coordination/codex/HANDOFF_OUT.md` khi đã áp dụng.
