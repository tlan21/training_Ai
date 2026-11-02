# AI-17 evidence — Fusion vòng 6: chuẩn hóa theo từng video + augment (2026-10-29)

Quy tắc đăng ký trước: `.claude/evaluation_plan.md` §2.1 "Vòng 6". Kernel `traininghighlight/ai-core-fusion-r6` v2 (Trainer ghi val loss, train loss trung bình, lr).

## Sweep trên val (seed 1337, F1 thô ở ngưỡng 0.5 do Trainer chọn best.pt)
| biến thể | chuẩn hóa | augment | val F1 | step |
|---|---|---|---|---|
| n0_a0 (= cấu hình vòng 5) | không | không | 0.2008 | 900 |
| n0_a1 | không | có | 0.1924 | 2200 |
| n1_a0 | có | không | 0.2216 | 1200 |
| **n1_a1 (thắng)** | có | có | **0.2300** | 1800 |
Seed 1338 / 1339: 0.2209 / 0.2196.

## Đường cong (history.json) — overfit theo val loss ở MỌI lần train
| run | F1 đỉnh @step (lr) | val loss tại F1 đỉnh | val loss thấp nhất @step | val loss cuối | train loss nửa đầu → nửa sau |
|---|---|---|---|---|---|
| n0_a0 | 0.2008 @900 (2.8e-4) | 1.172 | 1.042 @1100 | 1.497 (+44%) | 0.946 → 0.690 |
| n0_a1 | 0.1924 @2200 (1.5e-4) | 1.194 | 1.046 @1100 | 1.279 (+22%) | 0.996 → 0.805 |
| n1_a0 | 0.2216 @1200 (2.6e-4) | 1.082 | 0.983 @600 | 2.319 (+136%) | 0.841 → 0.449 |
| n1_a1 | 0.2300 @1800 (2.0e-4) | 1.065 | 0.971 @600 | 1.529 (+57%) | 0.922 → 0.665 |
| best_s1338 | 0.2209 @2200 (1.5e-4) | 1.267 | 0.974 @500 | 1.570 (+61%) | 0.927 → 0.670 |
| best_s1339 | 0.2196 @2400 (1.3e-4) | 1.310 | 0.967 @1000 | 1.635 (+69%) | 0.919 → 0.663 |
- Val loss chạm đáy ở step 500–1100 rồi tăng trong khi train loss vẫn giảm → model bắt đầu tự tin quá mức / học thuộc sau khoảng 1/4 lịch train.
- F1 (xếp hạng giây) vẫn tốt lên sau đáy val loss → best.pt theo F1 nằm sau đáy loss; xác suất kém hiệu chỉnh, τ chọn trên val bù lại.
- Augment giảm mức tăng val loss rõ khi có chuẩn hóa (+136% → +57%). Train loss có augment bị nâng nhân tạo → khoảng cách overfit đo bằng F1 trên dữ liệu SẠCH bên dưới.

## Chấm theo quy trình DoD (stride 30, gộp 3 seed, k+τ chọn trên val) — `round6_result.json`
| | k | τ | val F1 | train60 F1 | gap train−val | test F1 |
|---|---|---|---|---|---|---|
| vòng 5 (chấm lại cùng code) | 9 | 0.51 | 0.2750 | 0.4796 | 0.2046 | 0.2632 |
| **vòng 6** | 9 | 0.50 | **0.3053** | 0.4744 | **0.1692** | **0.3280** |
- Quyết định (chỉ val + gap): val 0.3053 ≥ 0.2750 ✓, gap 0.1692 < 0.205 ✓ → **ĐẠT, thay vòng 5**. Test mở sau khi quyết.
- Train60 F1 gần như không đổi (0.480 → 0.474) mà val/test tăng → cải thiện là ở **tổng quát hóa**, không phải học thuộc thêm.
- Baseline trên cùng tập test (`docs/T1.5_ket_qua_v5_273hiep.json`): RMS 0.1440, frame-diff 0.1052 → vòng 6 hơn RMS +0.184, frame-diff +0.223.
- Tập test này đã được xem: 1 lần chấm DoD vòng 5 + 3 lần đo lại (AI-16) không dùng để chọn + lần này (sau khi quyết).

## Qua code service + luật clip chọn trên val — `clip_rules_round6.json`
- Service path, không luật clip: test 0.3281 (khớp 0.3280). Luật chọn trên val: nối khe 0 s, bỏ clip < 5 s → test 0.3334; clip 542 → 385, dài TB 9.2 → 12.0 s, clip < 3 s: 86 → 0.
- Ứng viên (chưa kích hoạt): `D:/tmp/ai17_20261029/candidate/highlight_fusion/` (best.pt = seed 1337, seed1338.pt, seed1339.pt, postproc.json).

## Giới hạn
- Vẫn còn overfit (gap 0.17, val loss tăng sau ~step 600). Vòng sau: chọn checkpoint có xét val loss / dừng sớm hơn, giảm lr hoặc tăng weight decay.
- Chỉ bóng đá (SoccerNet); chuẩn hóa theo video là bước cần cho thể loại khác nhưng chưa có nhãn để đo.
9b59a7b06d592ea8bf74b33a286cc15fe2722ea65bc030c556d1f9a5edb0be23 *best.pt
cdb501d94395a193efcfe607cf0f3643bd9b6c182e555e3a908fabcc2ff4a9b7 *postproc.json
970cc06819009d1f97e6e784d24cb163d7ed85634bed4ce1d11f46f82d445411 *seed1338.pt
931d26c616a76b8c3e584eb0710ab4df7fd69b4764ee2b043c62ddf7b0119ab3 *seed1339.pt
