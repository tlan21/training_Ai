# Two-Tower v2 — Data contract (AI-12a/12c ↔ Codex INT-13)

**Version: `ttv2-data-v1` (2026-10-26), DRAFT.** Owner: Claude (định nghĩa dữ liệu + nhãn). Codex: ghi tương tác + xuất bundle.
Bộ đọc/kiểm tra: `ai-core/ai_core/training/datasets/product_interactions.py` (test: `ai_core/tests/test_product_interactions.py`).
Quyết định liên quan: D14, D18, D19 (gate 3 giai đoạn), D21 (phân việc). Không pseudo-label từ model ngoài.

## 1. Ghi tương tác (Codex, bảng `user_interactions` hiện có — không đổi schema)

| `interaction_type` | Ghi khi | `duration_watched` | `clip_id` |
|---|---|---|---|
| `click` | user mở video/clip từ feed, search hoặc gợi ý | 0 | clip được mở, NULL nếu video gốc |
| `watch_time` | **1 dòng / 1 phiên xem**, khi kết thúc phiên (rời màn, chuyển clip, đóng tab) — không ghi heartbeat | tổng giây thực xem trong phiên (≥ 0, không tính tua) | như trên |
| `like` / `share` / `save` | hành động tường minh (`save` = yêu thích/lưu) | 0 | như trên |
| `skip` | user lướt qua clip trong feed khi đã hiện ≥ 1 s nhưng xem < 3 s | 0 | clip bị lướt |

- `user_id`, `video_id`, `clip_id`: đúng ID Postgres (`usr_*`, `vid_*`, `clp_*`); `clip_id` phải thuộc `video_id`.
- `created_at`: thời điểm sự kiện, UTC, do server đặt.
- Chỉ ghi cho user role `client` (không ghi admin/editor thử nghiệm). Không ghi khi chưa đăng nhập.
- Không sinh tương tác giả/seed vào bảng sản phẩm. Dữ liệu demo nếu cần → đánh dấu riêng và **không** xuất vào bundle.

## 2. Bundle xuất (Codex → Claude), read-only cho Claude

Thư mục mỗi lần xuất: `D:/video-ai-exports/ttv2/<YYYYMMDDTHHMMSSZ>/` (Codex sở hữu path, Claude chỉ đọc; đổi path → ghi handoff).
UTF-8, JSON Lines, thời gian ISO8601 UTC có hậu tố `Z`. **Không PII**: không email/username/mật khẩu/avatar/IP.

| File | Mỗi dòng |
|---|---|
| `manifest.json` | `{"export_version":"ttv2-data-v1","generated_at","snapshot_at","files":{"<name>":{"rows":int,"sha256":hex}}}` |
| `users.jsonl` | `{"user_id","created_at","preferred_category_ids":[cat_*]}` — chỉ role `client` |
| `categories.jsonl` | `{"category_id","name"}` — toàn bộ bảng `categories` |
| `videos.jsonl` | `{"video_id","category_id"\|null,"duration_seconds","visible_to_client":bool,"created_at"}` |
| `clips.jsonl` | `{"clip_id","video_id","start_time","end_time","status"}` |
| `interactions.jsonl` | `{"interaction_id","user_id","video_id","clip_id"\|null,"interaction_type","duration_watched","created_at"}` |

- `visible_to_client` = đúng quy tắc hiển thị của Client (processed/published, chưa xóa) tại `snapshot_at`.
- Snapshot nhất quán: mọi file cùng một thời điểm; `interactions` chỉ gồm dòng `created_at ≤ snapshot_at`.
- Xuất toàn bộ lịch sử (không incremental) ở `ttv2-data-v1`; idempotent: cùng snapshot → cùng sha256.
- Tùy chọn giai đoạn 2 (không bắt buộc): `impressions.jsonl` `{"user_id","video_id","clip_id","shown_at","position","source":"feed|search|recommendation"}`
  để làm negative theo exposure — cần Codex thêm cơ chế ghi; báo trước khi làm.

## 3. Claude kiểm tra + gán nhãn (không yêu cầu Codex làm)

- Loại (đếm theo lý do): sai định dạng ID (vd ID số MovieLens), user/video không tồn tại, type ngoài enum, timestamp lỗi/sau snapshot/trước khi user tạo,
  video không `visible_to_client`, `clip_id` không thuộc `video_id`, `duration_watched` âm hoặc > 1.5× độ dài + 5 s; trùng (cùng user/video/clip/type trong 30 s, `watch_time` giữ max).
- Độ dài mục: clip (end − start) nếu có `clip_id`, ngược lại `videos.duration_seconds`.
- **Positive:** `like`/`share`/`save`; `watch_time` ≥ 50% độ dài **hoặc** ≥ 30 s. **Negative tường minh:** `skip`; `watch_time` < 10% (và < 30 s).
  `click` một mình: không phải nhãn (chỉ dùng cho popularity/exposure). Mỗi cặp (user, video) một nhãn; positive thắng, mốc = positive đầu tiên.
- Split theo **mốc thời gian toàn cục** (mặc định 20% cuối là eval) → không sự kiện eval nào trước sự kiện train; popularity/feature chỉ tính từ phần train.
  User chỉ có positive sau mốc = **cold-start**, báo cáo riêng.
- Vocabulary danh mục: `category_id` sắp xếp, version = sha256(12 ký tự đầu) ghi vào manifest model. Danh mục mới → version mới, train lại.
- Gate dữ liệu D19: `EVAL_READY` khi ≥ 200 user, ≥ 5 000 tương tác hợp lệ sau lọc, và có user eval với ≥ 5 positive; chưa đạt → `TRAIN_EXPERIMENTAL`
  (chỉ sandbox, không tuyên bố kết quả tin cậy).

## 4. Không làm
- Không ghép/hash ID MovieLens với ID sản phẩm. Không vector 0/giả cho user/video thiếu dữ liệu (giữ popularity/fallback).
- Claude không đọc trực tiếp Postgres sản phẩm, không ghi vào bundle/Postgres/collection sản phẩm.
