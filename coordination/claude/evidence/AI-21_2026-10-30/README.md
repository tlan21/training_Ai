# AI-21 evidence — xác nhận vòng 8 ×10 trên test tin tức độc lập (2026-10-30)

Quy tắc đăng ký trước (`.claude/evaluation_plan.md` §2.1 "Xác nhận vòng 8 ×10" + sửa đổi 2026-10-30, trước khi tải video/chạy model).
Test: 8 video CC BY (`selection_final.json`): 2 kênh mới (SGGP, THVL 24News) + 6 video chưa dùng của kênh đã thấy (HYTV×3, ĐCSVN×2, LSTV×1).
Feature đường production, chế độ MÙ (không chạy model trước khi có nhãn); nhãn khoatm 2026-10-30, gán mù, 8/8 HUMAN_VERIFIED, gộp đoạn chồng.
Chấm đúng 1 lần (`confirm_result.json`, `confirm.log`).

| | k / τ (chọn trên val bóng đá) | F1 test tin tức | kênh mới (2 video) | kênh đã thấy (6) | τ riêng tin tức (tham khảo) | test bóng đá |
|---|---|---|---|---|---|---|
| vòng 7 (active) | 9 / 0.51 | 0.0238 | 0.0771 | 0.0000 | 0.287 @ τ 0.03 | 0.3298 |
| vòng 8 ×10 | 9 / 0.51 | **0.1205** | **0.0000** | 0.1667 | 0.321 @ τ 0.05 | 0.3222 |
| mốc đoán-bừa (mọi giây = highlight) | — | 0.2807 | 0.3257 | 0.2646 | — | — |

- Quy tắc: tin tức +0.0967 ≥ +0.05 ✓ và bóng đá −0.0076 ≥ −0.01 ✓ → **quy tắc cho phép CHUYỂN sang ×10**.
- Bootstrap theo video (10.000): Δ tin tức +0.097, CI95 **[−0.053, +0.238]**, P(Δ ≤ 0) = 0.15, P(Δ ≥ 0.05) = 0.71 → **không có ý nghĩa thống kê** với 8 video.
- Cả hai model ở τ production đều **dưới mốc đoán-bừa** (0.28); kể cả với τ riêng chỉ ngang mốc (0.29–0.32) → highlight tin tức **chưa được giải** trên dữ liệu độc lập.
- Cải thiện của ×10 đến hoàn toàn từ kênh đã thấy (0 → 0.167); trên 2 kênh mới ×10 = 0.0 (vòng 7 0.077) → chưa có bằng chứng tổng quát sang kênh mới.
- Điểm tin tức rất thấp so với τ (τ riêng tối ưu ≈ 0.03–0.05): mô hình gần như không bao giờ vượt ngưỡng cắt trên tin tức → thực tế ít/không ra clip tin tức ở cả hai.
