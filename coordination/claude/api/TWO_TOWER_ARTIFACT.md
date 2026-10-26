# Two-Tower artifact contract — AI-09 (2026-10-26)

Trả lời yêu cầu Codex (RE:HC-04, `TWO_TOWER_PRODUCT_MAPPING.md`): input encoder, vocabulary, unknown-input policy, chuẩn hóa, version/checksum.
Manifest máy đọc: `two_tower_artifact_manifest.json` (sinh bởi `python -m ai_core.scripts.export_two_tower_milvus --manifest`).

## 1. Artifact active
| Trường | Giá trị |
|---|---|
| `artifact_version` | `two_tower-ml100k-v1` |
| checkpoint | `ai-core/checkpoints/two_tower/best.pt`, SHA256 `f28c37943ec499d168f43b5281879273af326a97ee47e571100c93dee0c91695` |
| dữ liệu train | MovieLens-100k `u.data` SHA256 `06416e59…`, `u.item` SHA256 `553841eb…` (rating ≥ 4, leave-last-10 hai lần) |
| metric offline | NDCG@10 = 0.1225 (step 2000, seed 1337) |
| vector | 128-d, L2-norm, metric IP (= cosine); service trả score = (IP+1)/2 ∈ [0,1] |

## 2. Encoder input (transductive)
- **User tower** (942-d): one-hot chỉ số user MovieLens trong fit split. Không có feature nào khác.
- **Video tower** (1702-d): 19 genre MovieLens + log1p(popularity)/max + one-hot chỉ số item MovieLens (1682).
- Vocabulary không lưu trong checkpoint; dựng lại tất định từ `u.data`/`u.item` + split (`build_features`).

## 3. Unknown-input policy
ID ngoài vocabulary huấn luyện **không encode được** → không sinh vector (không vector 0, không hash/modulo, không tái dùng ID train).
Hệ quả: **artifact v1 không hỗ trợ user/video sản phẩm** (`usr_*`, `vid_*`, 10 danh mục tiếng Việt ≠ 19 genre MovieLens).
`product_ids_supported = false`. Collection sản phẩm `user_recommendation_embeddings` **không được nạp** từ artifact này (D14; script chặn cứng).

## 4. Sandbox (D14) — đã nạp, đã kiểm
- `sandbox_two_tower_ai09_20261026` (Codex tạo): 2 624 row = 942 `ml100k_u_<id>` + 1 682 `ml100k_i_<id>`; không `usr_`/`vid_`.
- Re-export idempotent (chỉ xóa namespace `ml100k_*`): 2 624 row sống, 0 row ngoài namespace.
- ANN IVF_FLAT nprobe 128 vs brute-force IP: recall@10 = 1.0000 (53 user).
- Service thật (instance tạm :8011, `MILVUS_RECO_COLLECTION`=sandbox): `ml100k_u_1` → 200, 5 gợi ý score 0–1; user lạ → 503 cold-start;
  `/health.dependencies.recommendation_index=ok`. Runtime :8001 sản phẩm không đổi (vẫn `missing_collection` → 503 → popularity fallback).
- Lưu ý: `title`/`thumbnail_url` trong response recommendation là **placeholder** do service dựng (`Video <id>`, `https://storage.local/...`);
  gateway phải lấy metadata thật từ Postgres theo `video_id`.

## 5. Personalized cho sản phẩm — cần quyết định user (chưa làm)
Artifact v1 không thể phục vụ product. Phương án:
- **A (đề xuất cho MVP):** giữ popularity fallback; personalized product = DEFERRED; Two-Tower báo cáo luận án trên MovieLens (offline + sandbox).
- **B:** Two-Tower v2 inductive: user = sở thích danh mục (10) + tổng hợp video đã tương tác; video = danh mục (10) + embedding ViT 256-d + popularity.
  Cần dữ liệu tương tác thật (`user_interactions`) đủ lớn để train/eval — hiện gần như chưa có.
- **C:** gợi ý theo nội dung không cần train (vector user = trung bình embedding video đã thích) — không phải Two-Tower, đổi phạm vi "6 model".
