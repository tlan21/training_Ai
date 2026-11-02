# AI-16 B — checkpoint highlight active thuộc vòng nào (2026-10-29, chỉ đọc)

| | active `ai-core/checkpoints/highlight_fusion/best.pt` | vòng 5 (DoD ĐẠT, `docs/T1.5_ket_qua_v5_273hiep.json`) |
|---|---|---|
| SHA256 | `becbd378ca23…` (contract §1) | s1337 `34199b6890da…` · s1338 `9678110e0cc8…` · s1339 `3e837fd1f149…` |
| config | d_model 256, dropout 0.3, window 120 | d_model 128, dropout 0.3, window 120 |
| metrics trong ckpt | seed 1337, step 1300, val F1 0.1993 | seed 1337/1338/1339, step 2800/2300/3500 (khớp file kết quả) |
| ngày | 2026-08-15 | 2026-09-25 (kernel `traininghighlight/ai-core-fusion-140`) |
| khớp file kết quả | **vòng 3** (`T1.5_ket_qua_vong3.json`: seed 1337 step 1300, d256/p0.3, 80 trận) — DoD **không đạt** | vòng 5 — DoD **đạt** (gộp 3 seed test F1 0.2632) |
| hậu xử lý khi chấm | — | cửa sổ 120 stride 30 (trung bình cửa sổ chồng), gộp 3 seed (mean), làm mượt k=9, τ=0.51 |
| service hiện tại | 1 ckpt, cửa sổ 120 không chồng, không làm mượt, ngưỡng cứng 0.75 | — |

- 3 checkpoint vòng 5 **không còn trên D:** (`D:/data_training_ai/kfusion140` đã mất); tải lại từ output kernel Kaggle (version mới nhất, COMPLETE)
  về `D:/tmp/ai16_20261029/kout/ckpt_fusion_best_s13{37,38,39}/` (3 × 5.2 MB) — lệnh `kaggle kernels output traininghighlight/ai-core-fusion-140 --file-pattern ckpt_fusion_best_s13`.
- Feature tái hiện: `D:/data_training_ai/kaggle_fusion_140_ds/highlight_features_140.pt` (train/val/test = 218/28/27 hiệp; tên test trùng file kết quả v5).
- Kết luận: số DoD T1.5 chưa bao giờ phản ánh model đang phục vụ. Đổi active sang vòng 5 = đổi checkpoint → bump contract + release, **user duyệt**.
