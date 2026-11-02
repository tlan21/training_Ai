# INT-50 — user approval (2026-11-02, AskUserQuestion in Claude session)

Q: "INT-50 cần QA thật trên stack đang chạy (trước đây bị chặn vì thiếu duyệt). Bạn duyệt phạm vi nào?"
A: **"Duyệt đủ phạm vi"** = triển khai riêng CMS 7c7dd74; browser QA 8 màn hình + Settings ở 390/1440; upload video test ngắn của riêng
Claude rồi xóa; bật/tắt 4 tổ hợp cờ AI toàn cục và khôi phục giá trị cũ; thử lỗi/retry/cancel chỉ trên dữ liệu test. Manifest trước/sau,
không đụng 120 video gốc.

Q: "Giải phóng dung lượng Docker trước khi build image CMS?"
A: **"Xóa build cache"** = `docker builder prune` (~21,5 GB cache build; không đụng image/container/volume đang dùng).
