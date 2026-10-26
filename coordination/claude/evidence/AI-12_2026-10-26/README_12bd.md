# AI-12b/12d evidence — 2026-10-26 (VERIFIED-NOW, SYNTHETIC LOGIC CHECK ONLY)

Không phải kết quả chất lượng (D19): dữ liệu synthetic trong bộ nhớ, provenance=`synthetic` → `production_ready` luôn False.

- Nhãn `ttv2-labels-v2`: test RED (35 s/600 s bị gán positive) → GREEN; quét lưới 7 980 (giây xem × độ dài) → 0 xung đột; không cặp (user, video) nào ở cả train và eval.
- `ai_core/training/two_tower_v2.py` (feature `ttv2-features-v1`): user = danh mục yêu thích K + trung bình vector video positive TRAIN + log #positive;
  video = danh mục one-hot K + has_content + slot ViT 256 (0 khi chưa có nguồn) + log-popularity TRAIN. Kiến trúc `TwoTower` cũ, loss in-batch softmax + logQ.
- Harness: Recall/NDCG@10 model vs Popularity cùng user + cùng candidate (video visible tại snapshot, loại positive train của user), bootstrap cặp B=1000
  percentile, coverage@10, p95 latency CPU (score 1 user + top-k, ghi CPU/threads), cold-start riêng, data stage D19.
- Test `test_two_tower_v2.py` 8/8 (RED: module thiếu → GREEN): feature chỉ từ train (xóa toàn bộ eval → feature y hệt), danh mục lạ/cold-start,
  oracle = 1.0 và item đã xem bị loại, popularity chỉ đếm train, bootstrap tất định, gate kiểm từng điều kiện + synthetic không bao giờ qua.
- Kiểm tra test không rỗng: synthetic 60 user/40 video — chưa train R@10 0.258, đã train (150 step) 0.731, Popularity 0.211, CI95 chênh [0.42, 0.61];
  model chưa train đã hơn Popularity → test so cả với model chưa train (+0.2) và CI cận dưới > 0.
- ai-core suite: 306 passed.
