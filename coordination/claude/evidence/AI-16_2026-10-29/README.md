# AI-16 evidence — highlight: checkpoint + hậu xử lý như lúc chấm + luật clip (2026-10-29)

VERIFIED-NOW 2026-10-29, CPU local.

| Kiểm | Kết quả | File |
|---|---|---|
| B: checkpoint active thuộc vòng nào | vòng 3 (DoD không đạt); vòng 5 (đạt) tải lại từ Kaggle output | `B_checkpoint_provenance.md` |
| A: recipe = pipeline chấm DoD | `test_highlight_recipe.py`: worker.highlight == `smooth(mean(model_scores_overlap))` từng giá trị (n = 50/120/301) | suite |
| A: tái hiện số DoD qua code service | test F1 **0.2628** (DoD 0.2632, lệch do làm tròn 0.1); val 0.2748 (0.2750) | `service_recipe_round5.json`, `eval_service_recipe.py` |
| ngưỡng cứng 75 trên cùng model | test F1 0.168 | như trên |
| C: luật clip chọn trên val | lưới gap {0,1,2,3,5,8} × min {1,2,3,5,8}; chọn gap 5 / min 3 (val 0.2765 vs 0.2748, lân cận 0.2756–0.2760) | như trên |
| C: trên test (chấm 1 lần) | F1 0.2624 (vs 0.2628); clip 616 → 483, dài TB 9.3 → 12.1 s, clip < 3 s: 97 → 0 | như trên |
| C: luật mặc định = clip cũ | 50 chuỗi ngẫu nhiên trùng thuật toán cũ | suite |
| không đổi hành vi active | inference 77 passed / 10 skipped; :8001 restart (PID 23292) smoke 9/9; `highlight.*` example SAME | `smoke_8001_legacy_active.log` |
| ứng viên (chưa kích hoạt) | `D:/tmp/ai16_20261029/candidate/highlight_fusion/`: best.pt `34199b68…`, seed1338.pt `9678110e…`, seed1339.pt `3e837fd1…`, postproc.json `8b327e2e…`; registry nạp 3 member | — |

Chưa làm (cần user duyệt): kích hoạt ứng viên (đổi checkpoint active, contract §1 SHA, release); build lại dataset Kaggle worker
(giao thức `highlight` đổi: trả `{scores, clip_rules}`).
Giới hạn: chọn/đo trên SoccerNet (bóng đá) — chưa có nhãn highlight cho thể loại khác; snap theo câu không đo được bằng nhãn SoccerNet (không có transcript).

## Overfitting check (2026-10-29, user hỏi) — Fusion vòng 5 ensemble, recipe service
| tập | hiệp | F1/giây | điểm TB giây dương | điểm TB giây âm |
|---|---|---|---|---|
| train (60 hiệp đầu) | 60 | **0.480** | 0.667 | 0.211 |
| val | 28 | 0.275 | 0.401 | 0.169 |
| test | 27 | 0.263 | 0.426 | 0.190 |
- Khoảng cách train − val ≈ 0.21 → model **có học thuộc** trận train. Val ≈ test (0.275 vs 0.263; split theo TRẬN) → mức tổng quát hóa sang trận bóng đá mới ổn định.
- Val F1 theo step (log kernel `ai-core-fusion-140`): tăng tới ~900–2100 rồi đi ngang/dao động 0.17–0.20, không sụp → early stopping theo val giữ được; overfit không làm val tụt mạnh.
- Video ngoài bóng đá: lệch chủ yếu do **lệch miền** (không có thể loại đó trong train), overfit làm nặng thêm vì model bám tín hiệu hẹp của trận train.
- Script `overfit_check.py` (cùng code service; feature `highlight_features_140.pt`).
