# SKILL: Dựng 1 màn hình CMS (task T3.1.x)

**Trigger:** task dựng/sửa 1 màn CMS React.

## READ ONLY THESE FILES
1. `stitch_ai_video_cms/<màn tương ứng>/code.html` — **nguồn sự thật layout/màu/copy, dựng CHÍNH XÁC theo đây**
2. `.claude/plan/03_cms_ui_plan.md` — mục 3 (đặc tả màn: components, bảng UI→API→field, states) **+ mục 7 (override theo Stitch + CẮT-list — đọc TRƯỚC)**
3. `cms/src/api-types.ts` — type đã sinh, KHÔNG viết type tay

Map màn → folder Stitch: dashboard=`t_ng_quan_h_th_ng` · upload/queue=`t_i_l_n_h_ng_i_x_l` · video list=`danh_s_ch_video` · highlight review=`ph_duy_t_c_t_highlight_ai` · phụ đề+tóm tắt (GỘP)=`ph_t_m_t_t_ai` · categories=`qu_n_l_danh_m_c_ph_n_lo_i_video` · clips/thư viện=`th_vi_n_n_i_dung_xu_t_b_n` · settings=`c_i_t_h_th_ng`. (Login + Users: không có Stitch — dùng wireframe plan 03.)

## STEPS (data flow)
1. Đọc mục 7 plan 03 → gạch phần tử CẮT khỏi màn (object detection, ngôn ngữ ≠ vi, H100, Vision-X, OpenAI label...).
2. Đối chiếu bảng UI→API→field của màn trong plan 03: mỗi phần tử UI phải map về đúng 1 endpoint + field. Phần tử Stitch không map được → kiểm tra mục 7.1; vẫn không có → DỪNG, báo cáo.
3. Dựng markup theo `code.html` Stitch (giữ class/màu/spacing), thay data tĩnh bằng hook TanStack (`hooks/` — 1 endpoint 1 hook, đặt tên theo plan 03 §2c).
4. Đủ 4 states: loading (skeleton) / empty / error (envelope message) / success. Polling đúng quy định màn (5s health/jobs, 3s clip processing).
5. Luồng: user action → hook mutation → invalidateQueries → UI cập nhật. Player/heatmap đồng bộ qua `reviewStore` (1 chiều).

## DONE WHEN
- Màn render trên stub Phase 0 giống layout Stitch, đủ 4 states.
- Không type tay; không endpoint ngoài bảng 2.1/2.3; `npm run build` + test heatmap/logic thuần pass.
- **Design Parity Check pass:** chạy checklist 10 mục trong `skills/ui_design_review.md` đối chiếu với `stitch_ai_video_cms/<màn>/code.html`, đính bảng kết quả vào báo cáo. Chưa pass = task chưa xong.

## DO NOT
- "Cải thiện" design khác Stitch. Dựng lại phần tử trong CẮT-list. Thêm màn/route mới.
