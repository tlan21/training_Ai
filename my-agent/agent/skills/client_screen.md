# SKILL: Dựng 1 màn hình Client (task T3.2.x)

**Trigger:** task dựng/sửa 1 màn Client Next.js.

## READ ONLY THESE FILES
1. `stitch_ai_video_platform_vietnamese/<màn>_mobile/code.html` (chuẩn) + `_desktop` (layout ≥1024px) — **nguồn sự thật layout/màu/copy**
2. `.claude/plan/04_client_ui_plan.md` — mục 3 (đặc tả màn) **+ mục 8 (override Stitch + CẮT-list — đọc TRƯỚC)** + mục 4 (playerStore) nếu là màn phát video + mục 5 (tracking) nếu có interaction
3. `client/src/api-types.ts` — type đã sinh

Map màn → folder: feed=`short_video_feed` · video detail=`video_detail_ai_player(_animated)` · search=`multimodal_search` · onboarding=`interest_onboarding` · discovery=`discovery` · login/register=`login`/`ng_k` · profile=`personal_library`.

## STEPS (data flow)
1. Đọc mục 8 plan 04 → gạch phần tử CẮT (dịch AI, comment, follow, tab Đang theo dõi, quên mật khẩu).
2. Đối chiếu bảng UI→API→field của màn: mỗi phần tử map đúng endpoint bảng 2.1/2.2 master plan. Không map được → mục 8.1; vẫn không → DỪNG, báo cáo.
3. Dựng theo Stitch mobile trước (dvh, safe-area, scroll-snap nếu feed), desktop 2 cột theo bản desktop.
4. Màn phát video: player ghi `currentTime` 1 chiều vào `playerStore`; heatmap/subtitle read-only, chỉ gọi `seekTo`. Ngưỡng highlight đọc 75 (hằng `HIGHLIGHT_THRESHOLD`).
5. Interaction tracking theo bảng mục 5 plan 04 (click/like/share/save bắn ngay; watch_time gom 10s + sendBeacon; skip <2s). Fire-and-forget.
6. Đủ states: loading skeleton / empty / error; khối analysis lỗi không chặn phát video.

## DONE WHEN
- Render stub giống Stitch (mobile + desktop), không cuộn ngang body.
- `playerStore` self-check pass (buildHighlightRanges / nextHighlightStart) nếu đụng player.
- Interaction bắn đúng loại + thời điểm (kiểm network tab).
- **Design Parity Check pass:** chạy checklist 10 mục trong `skills/ui_design_review.md` đối chiếu với `stitch_ai_video_platform_vietnamese/<màn>_mobile|_desktop/code.html`, đính bảng kết quả vào báo cáo. Chưa pass = task chưa xong.

## DO NOT
- Đổi design khỏi Stitch. Dựng phần tử CẮT-list. Lưu access token vào localStorage. Thêm endpoint.
