# SKILL: Implement 1 endpoint backend Go (task T2.x)

**Trigger:** task thêm/hoàn thiện 1 endpoint gateway hoặc 1 handler worker.

## READ ONLY THESE FILES
1. `infra/openapi.yaml` (nếu đã có; chưa có → bảng mục 2 `.claude/plan/00_master_plan.md` là contract)
2. `.claude/plan/02_backend_plan.md` — vị trí file, port/adapter liên quan
3. `.claude/database_schema.md` — CHỈ khi endpoint đọc/ghi DB

## STEPS (data flow — điền cụ thể cho endpoint của bạn)
1. Chép nguyên dòng contract của endpoint (method, path, body → response) vào đầu PR/ghi chú. Mọi field code ra phải có mặt trong dòng này.
2. Request vào gateway (Gin) → middleware auth (JWT Bearer; role admin/editor nếu prefix `/api/cms`) → handler → port (interface) → adapter (pgx/mongo/milvus/kafka/minio/redis) → response envelope.
3. Viết handler với **mock adapter trước** — unit test pass trên mock.
4. Nối adapter thật. Lỗi trả đúng envelope `{"error":{"code","message"}}` + HTTP status.
5. Endpoint gọi AI: base URL `http://inference:8001`, header `Authorization: Bearer ${AI_SERVICE_KEY}` — key đọc từ env, KHÔNG hardcode.
6. Endpoint ghi event: produce đúng topic + payload bảng 2.5 master plan.

## DONE WHEN
- `go build ./...` + `go test ./...` pass.
- curl endpoint trên docker-compose trả đúng schema contract (dán output vào báo cáo).
- Pagination/error/time format đúng conventions 2.6 master plan.

## DO NOT
- Thêm endpoint/field ngoài contract (thiếu → DỪNG, báo cáo).
- Gọi thẳng DB từ handler (phải qua port/adapter). Import lib mới ngoài danh sách adapter master plan.
- Trả dữ liệu chưa duyệt cho route public (`processed`/`published` only).
