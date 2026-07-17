# SKILL: Design Parity Check — đối chiếu màn đã dựng với Stitch (bắt buộc cuối MỌI task UI)

**Trigger:** (1) bước cuối mọi task T3.1.x / T3.2.x trước khi báo xong; (2) task review riêng "đối chiếu màn X với thiết kế".

**Luật gốc:** Stitch HTML là thiết kế CHÍNH XÁC phải đạt. Sai lệch = bug. "Làm đẹp thêm" (thêm shadow/gradient/animation/đổi màu không có trong Stitch) CŨNG là sai lệch — cấm.

## READ ONLY THESE FILES
1. `stitch_ai_video_cms/<màn>/code.html` HOẶC `stitch_ai_video_platform_vietnamese/<màn>_mobile|_desktop/code.html` — bản gốc
2. Màn đã dựng (component/page tương ứng trong `cms/src/` hoặc `client/src/`)
3. CẮT-list: `.claude/plan/03_cms_ui_plan.md` mục 7.2 hoặc `.claude/plan/04_client_ui_plan.md` mục 8.2 — danh sách sai lệch DUY NHẤT được phép

## STEPS
1. Mở song song 2 bên cùng viewport: mobile **390×844**, desktop **1440×900**. Có Playwright → screenshot cả 2, so từng khối; không có → đối chiếu thủ công theo checklist, đi từ trên xuống.
2. Chấm từng mục checklist, ghi bảng `[Khối] [Stitch] [Bản dựng] [Khớp?/Lý do]`:

| # | Mục | Chuẩn so |
|---|---|---|
| 1 | Cấu trúc layout | Đúng số cột/section/thứ tự khối như Stitch (grid, sidebar, bento, bottom-sheet) |
| 2 | Màu | Đúng hex nền/chữ/accent/badge — lấy từ class Tailwind hoặc style trong `code.html`, không "gần giống" |
| 3 | Typography | Đúng font, size, weight, line-height từng cấp (heading/body/caption/micro) |
| 4 | Spacing & radius | Padding/gap/border-radius từng khối khớp giá trị Stitch |
| 5 | Icon | Đúng tên icon (Material Symbols: `auto_awesome`, `bolt`, `insights`, `schedule`...) — không thay icon tương đương |
| 6 | Copy tiếng Việt | Nguyên văn label/placeholder/tooltip từ Stitch (trừ copy-sửa quy định: NLP→đa phương thức, Vision-X→checkpoint thật, H100→số thật, OpenAI Key→AI Service Key) |
| 7 | Thành phần AI | Heatmap gradient màu đúng, badge "AI Highlight"/"BẢN NHÁP AI"/% khớp, confidence đỏ dưới ngưỡng — đúng vị trí + màu |
| 8 | States | Hover/active/disabled/empty có trong Stitch phải có; thêm loading/error theo plan (Stitch không vẽ → dùng token cùng hệ) |
| 9 | Responsive | Mobile theo bản `_mobile`, desktop theo `_desktop`; không cuộn ngang body; safe-area |
| 10 | Phần tử CẮT | Phần tử trong CẮT-list phải VẮNG MẶT; phần tử ngoài CẮT-list không được tự ý bỏ |

3. Mỗi mục KHÔNG khớp: sửa ngay nếu ≤ 15 phút; lớn hơn → ghi vào báo cáo, task tính CHƯA XONG.
4. Data tĩnh trong Stitch (256K views, 98%...) → thay bằng data thật/stub — không tính sai lệch.

## DONE WHEN
- Bảng 10 mục toàn "Khớp" (hoặc chênh lệch nằm đúng CẮT-list/copy-sửa/data động).
- Screenshot 2 bên đính kèm báo cáo (nếu có Playwright).
- Không phần tử "sáng tạo thêm" ngoài Stitch.

## DO NOT
- Duyệt màn "nhìn chung giống" mà không đi hết 10 mục.
- Tự quyết sai lệch "chấp nhận được" — ngoài CẮT-list thì chỉ chủ dự án quyết.
- Sửa file trong `stitch_ai_video_*` để "khớp với code" — chiều sai, thiết kế là chuẩn.
