# AI-20 evidence — Fusion vòng 8: bóng đá + tin tức có nhãn người (2026-10-30)

Quy tắc đăng ký trước: `.claude/evaluation_plan.md` §2.1 "Vòng 8". Kernel `traininghighlight/ai-core-fusion-r8` v1, 9 run (×1/×10/×30 × 3 seed).
Nhãn tin tức: khoatm 2026-10-30, 10/10 video HUMAN_VERIFIED, gộp đoạn chồng (`news_intake_report.json`); train 7 / val 3 video.

## Chấm (gộp 3 seed, stride 30, k+τ chọn trên val bóng đá; tin tức ở cùng k/τ) — `round8_result.json`
| | k | τ | val bóng đá | gap train−val (bóng đá) | val tin tức | val tin tức τ riêng (chỉ tham khảo) | test bóng đá |
|---|---|---|---|---|---|---|---|
| vòng 7 (active) | 9 | 0.51 | 0.3151 | 0.1606 | 0.1852 | 0.2946 @0.26 | 0.3298 |
| vòng 8 ×1 | 9 | 0.53 | 0.3126 | **0.2240** | **0.5111** | 0.5503 @0.65 | 0.3267 |
| vòng 8 ×10 | 9 | 0.51 | **0.3228** | **0.1326** | 0.3756 | 0.5076 @0.24 | (chưa mở) |
| vòng 8 ×30 | 5 | 0.56 | 0.3060 | 0.1600 | 0.1922 | 0.4891 @0.22 | (chưa mở) |
- Quy tắc: biến thể đủ điều kiện (val bóng đá ≥ 0.3051) = cả 3; thắng = val tin tức cao nhất = ×1; ×1 có gap 0.224 > 0.1706 → **KHÔNG thay vòng 7**.
- ×10 riêng lẻ thỏa mọi ngưỡng (bóng đá 0.3228, tin tức 0.3756 ≥ 0.2352, gap 0.133) nhưng quy tắc đăng ký chọn ×1 trước rồi mới kiểm gap
  → chọn ×10 bây giờ là đổi quy tắc SAU khi xem kết quả. Không làm. Bài học: lần sau đưa gap vào điều kiện đủ (eligibility).
- Mốc đoán-bừa tin tức (mọi giây = highlight): F1 ≈ 0.22 (val 12.4% giây dương). Vòng 7 (0.185) dưới mốc; mọi biến thể vòng 8 khi dùng τ riêng ≥ 0.49.
- τ dùng chung bóng đá không hợp tin tức (×30: 0.192 ở τ chung vs 0.489 ở τ riêng) → điểm hai thể loại hiệu chỉnh khác nhau; một ngưỡng chung là giới hạn.
- Val tin tức chỉ 3 video; 1/3 (`y9_TESYEbmA`) cùng kênh "Báo điện tử ĐCSVN" với 2 video train → val tin tức có phần lạc quan. Không có test tin tức.

## Đường cong (history.json): learning rate / overfit / val loss
| run | F1 đỉnh @step (lr) | val loss đáy @step | val loss tại best | val loss cuối |
|---|---|---|---|---|
| ×1 s1337/s1338/s1339 | @3000 (7.4e-5) / @2600 (1.1e-4) / @2400 (1.3e-4) | 0.948@1500 / 0.938@900 / 0.952@1500 | 1.380 / 1.192 / 1.161 | +53% / +48% / +52% |
| ×10 s1337/s1338/s1339 | @2000 (1.8e-4) / @1500 (2.3e-4) / @2300 (1.4e-4) | 0.972@400 / 0.964@400 / 0.979@1000 | 1.188 / 1.064 / 1.147 | +58% / +55% / +65% |
| ×30 s1337/s1338/s1339 | @1700 (2.1e-4) / @1000 (2.7e-4) / @2700 (1.0e-4) | 0.989@500 / 0.993@700 / 1.000@300 | 1.164 / 1.093 / 1.464 | +64% / +53% / +58% |
- Mọi run: val loss chạm đáy sớm (step 300–1500) rồi tăng ~50–65% → overfit theo loss vẫn như vòng 6–7. Lặp tin tức nhiều (×30) đẩy đáy sớm hơn (300–700).
- ×1: gap bóng đá tăng (0.161 → 0.224) — F1 train bóng đá tăng mạnh hơn val → học thuộc bóng đá nhiều hơn; ×10 gap thấp nhất các vòng (0.133).
