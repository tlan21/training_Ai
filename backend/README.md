# backend (Go)

Go module `traning_ai/backend`. Phase 0 giao: **gateway stub** trả mock đúng `infra/openapi.yaml`
để FE code ngay. Phase 2 thêm DB/Kafka/AI thật (orchestrator, ffmpeg-cutter, adapters).

## Trạng thái

| Thành phần | Trạng thái |
|---|---|
| `cmd/gateway` — Gin :8000, 39 path stub, JWT-presence auth, error envelope, CORS | ✅ build+run |
| `internal/gen/api.gen.go` — types + embedded spec (oapi-codegen từ openapi.yaml) | ✅ sinh tự động |
| `internal/handlers` — stub trả mock schema-shaped | ✅ |
| orchestrator · ffmpeg-cutter · adapters (pg/mongo/milvus/kafka/minio/redis) · JWT thật | ⏳ Phase 2 |

## Chạy

```bash
cd backend
go run ./cmd/gateway            # :8000  (GATEWAY_PORT đổi cổng)
# smoke
curl -s localhost:8000/api/auth/login -X POST -H "Content-Type: application/json" -d '{"email":"a@b.c","password":"x"}'
curl -s localhost:8000/api/feed                              # 401 (thiếu token)
curl -s localhost:8000/api/feed -H "Authorization: Bearer x" # 200 mock
curl -s localhost:8000/openapi.json                          # embedded spec (39 path)
```

## Sinh lại types khi đổi contract

```bash
# cài 1 lần: go install github.com/oapi-codegen/oapi-codegen/v2/cmd/oapi-codegen@latest
oapi-codegen -config oapi-codegen.yaml ../infra/openapi.yaml   # → internal/gen/api.gen.go
```

## Env

| Biến | Default |
|---|---|
| `GATEWAY_PORT` | `8000` |
| `AI_BASE_URL` | `http://localhost:8001` |
| `AI_SERVICE_KEY` | `sk-local-dev-key` |
