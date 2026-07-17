# SKILL: Thêm/sửa bảng, cột, collection (task T0.2 hoặc phát sinh)

**Trigger:** task đụng schema Postgres / MongoDB / Milvus.

## READ ONLY THESE FILES
1. `.claude/database_schema.md` — nguồn sự thật schema (DDL + JSON mẫu + index)
2. `.claude/plan/00_master_plan.md` mục 2 — endpoint nào tiêu thụ field này

## STEPS
1. **Schema đổi = sửa `database_schema.md` TRƯỚC**, migration code SAU — doc là nguồn sự thật, không để trôi.
2. Postgres: viết migration SQL thuận + nghịch (up/down), giữ convention: id prefix VARCHAR(50), `created_at/updated_at TIMESTAMPTZ`, CHECK cho enum, FK có ON DELETE rõ ràng.
3. Mongo: cập nhật JSON mẫu trong doc + index cần tạo. Milvus: dimension/metric/index là bất biến (128d COSINE HNSW · 128d IP IVF_FLAT) — đổi = vi phạm, DỪNG.
4. Field mới phải có ≥1 endpoint tiêu thụ trong contract — không có → hỏi lại, không thêm "để dành".
5. Seed đi kèm nếu bảng cấu hình (như `system_settings` — 6 key mặc định ghi trong doc).

## DONE WHEN
- `database_schema.md` và migration khớp 100% (diff từng cột).
- Migration chạy lên/xuống sạch trên docker-compose Postgres.
- Index trong doc mục 2.2 được tạo đủ.

## DO NOT
- Thêm bảng/cột không có endpoint tiêu thụ. Đổi ID prefix/enum đã có. Đổi schema Milvus.
- Xóa cột dữ liệu thật mà không có bước backup trong migration.
