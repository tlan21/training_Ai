# AI-18 evidence — Fusion vòng 7: learning rate / weight decay / lịch ngắn (2026-10-29)

Quy tắc đăng ký trước: `.claude/evaluation_plan.md` §2.1 "Vòng 7". Kernel `traininghighlight/ai-core-fusion-r7` v1 (nền = vòng 6: chuẩn hóa theo video + augment).

| biến thể (seed 1337) | val F1 thô @step (lr) | val loss đáy @step | val loss cuối | train loss nửa đầu → sau |
|---|---|---|---|---|
| mốc vòng 6 (lr 3e-4, wd 0.1, 4000) | 0.2300 @1800 (2.0e-4) | 0.971 @600 | +57% | 0.922 → 0.665 |
| lr 1e-4, wd 0.1, 4000 | 0.2104 @2800 (3.0e-5) | 0.973 @900 | **+6%** | 0.983 → 0.857 |
| **lr 3e-4, wd 0.3, 4000 (thắng)** | **0.2303** @1800 (2.0e-4) | 0.971 @600 | +51% | 0.925 → 0.679 |
| lr 1e-4, wd 0.3, 4000 | 0.2089 @2800 (3.0e-5) | 0.968 @900 | **+4%** | 0.988 → 0.864 |
| lr 3e-4, wd 0.1, 1500 | 0.2150 @1300 (4.3e-5) | 0.964 @900 | **+2%** | 1.014 → 0.896 |
Seed 1338 / 1339 của biến thể thắng: 0.2197 / 0.2222 (val loss +57% / +64%).

- LR thấp hoặc lịch ngắn **gần như hết overfit theo val loss** (+2–6%) nhưng F1 thấp hơn → train ít hơn = học thiếu phần xếp hạng.
- Weight decay 0.3 thắng mốc chỉ +0.0003 F1 thô (trong nhiễu) và vẫn overfit theo loss như vòng 6.

## Chấm theo quy trình DoD (stride 30, gộp 3 seed, k+τ trên val) — `round7_result.json`
| | k | τ | val F1 | train60 | gap | val loss TB tại ckpt chọn | test F1 |
|---|---|---|---|---|---|---|---|
| vòng 6 (active) | 9 | 0.50 | 0.3053 | 0.4744 | 0.1692 | 1.2136 | 0.3280 |
| vòng 7 | 9 | 0.51 | **0.3151** | 0.4756 | **0.1606** | **1.1477** | 0.3298 |
- Quyết định (val + gap + val loss): 0.3151 ≥ 0.3053 ✓ · 0.1606 < 0.1692 ✓ · 1.1477 < 1.2136 ✓ → **ĐẠT quy tắc**. Test mở sau quyết định.
- Mức cải thiện thực tế **rất nhỏ**: test +0.0018 (trong nhiễu của 27 hiệp); val +0.010, gap −0.009, val loss −0.066.
- Tập test này đã xem nhiều lần (DoD vòng 5, 3 lần đo AI-16, vòng 6, lần này) — chỉ để báo cáo, không dùng chọn.
