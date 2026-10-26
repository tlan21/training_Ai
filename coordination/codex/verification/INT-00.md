# INT-00 — verification 2026-10-26 (runtime mock verified)

Owner: CODEX. Baseline Release #1 `96ebc24`; HC-02/HC-03 đọc từ Claude `91b0242`.
Skill dự án: `my-agent/agent/skills/backend_endpoint.md`.

## Contract và phạm vi

- AI-API v0.1 DRAFT: 6 POST `/v1/*` và GET `/health`, Bearer, error envelope; không đổi contract.
- Public `GET /api/cms/system/health` → `{gpu_vram_used,gpu_util,models_loaded,queue_depth}`; schema không đổi.
- Callers kiểm: gateway startup + CMS health, aihttp client, config, mock fixtures/tests, Dockerfile,
  compose mặc định/mock/GPU cũ, `.env.example`, hướng dẫn E2E. Pipeline Go thực chạy trong gateway;
  standalone orchestrator/cutter cũ ngoài runtime hiện tại.
- Không copy/mount checkpoint, không sửa Claude/AI/Milvus collection hoặc dữ liệu người dùng.
- Mock không đọc media/model/vector; chỉ kiểm schema cơ bản và trả fixture rõ MOCK_ONLY.
  Search/recommendation trả mảng rỗng, không tạo ID video ảo. Health `stub_mode=true`, `models_loaded=[]`.
- `AI_ALLOW_STUB=1` chỉ bật qua mock override; mặc định gateway tiếp tục yêu cầu 6 model thật.

## VERIFIED-NOW

| Command | Result |
|---|---|
| `git branch --show-current`; `git log HEAD..master --oneline` (đầu phiên) | `codex/integration`; không thiếu commit master |
| `docker info`; `docker compose version` | engine 28.4.0; Compose v2.39.4 |
| `npm ci --no-audit --no-fund` (cms) | PASS, 100 packages |
| `npm ci --no-audit --no-fund` (client) | PASS, 395 packages; npm báo deprecated dependencies hiện có |
| `Get-PSDrive E` sau npm ci | 1.79 GiB trống, đạt ≥1.5 GiB |
| `cd backend; $env:GOMAXPROCS='2'; go test -p 1 ./...` | PASS; DB integration chưa bật env trong lượt này |
| `cd backend; go vet ./...; go build ./...` | PASS (exit 0) |
| `cd cms; npx tsc --noEmit; npm run build` (lượt tuần tự) | PASS; Vite 181 modules, JS 431.85 kB |
| `docker compose -f docker-compose.yml -f docker-compose.mock.yml config --quiet` | PASS |
| `docker compose -f docker-compose.yml -f docker-compose.gpu.yml config --quiet` | PASS; GPU override đã nghỉ, không còn inference local |

Lượt test/build đầu chạy khi hạ tầng vừa bật bị thiếu RAM: Go vet không fork được, CMS không hoàn tất;
PowerShell có OutOfMemoryException. Đã dừng đúng 6 container vừa bật (không xóa volume), chạy lại Go/CMS đạt PASS.
Không dùng lượt lỗi làm bằng chứng nghiệm thu. C: từ 3.48 xuống ~1.92 GiB khi hệ thống tăng dùng bộ nhớ;
chưa build/pull image mới. Image và volume cũ thuộc project `video-ai` (xác minh qua Docker labels/mounts).

## Cách chạy dùng image đã cache, tránh build image mới

Cross-compile Go với cache đã có trên D:; binary ở `backend/bin/` (ignored):

```powershell
cd backend
$env:GOMAXPROCS='2'
$env:CGO_ENABLED='0'
$env:GOOS='linux'
$env:GOARCH='amd64'
go build -p 1 -o bin/gateway ./cmd/gateway
go build -p 1 -o bin/ai-mock ./cmd/ai-mock
cd ..
```

File local ignored `docker-compose.local.yml` trong phiên:

```yaml
services:
  gateway:
    volumes:
      - ./backend/bin/gateway:/usr/local/bin/gateway:ro
  ai-mock:
    volumes:
      - ./backend/bin/ai-mock:/usr/local/bin/ai-mock:ro
  ingest-worker:
    volumes:
      - ./backend/ingest-worker:/srv/ingest-worker:ro
```

Khi còn đủ RAM/disk, dùng 3 file compose trên cùng project `video-ai`, `--no-build --pull never`.
Không dùng `--remove-orphans`, không start inference container cũ. Bản build chuẩn Dockerfile đã thêm binary ai-mock,
nhưng chưa build image mới trong phiên thiếu dung lượng này.

## VERIFIED-NOW bổ sung

- Client `npx tsc --noEmit; npm run lint; npm run build`: PASS, ESLint 0 warnings/errors, 14 routes generated.
- Linux gateway/ai-mock + pg.test/mongo.test cross-compile: PASS; không Docker build/pull.
- `go test -p 1 ./internal/mocks ./internal/config ./internal/adapters/aihttp`; `go vet -p 1 ./...`: PASS sau test opt-in bổ sung.
- `docker compose ... ps`: Postgres/Mongo/Redis/MinIO/etcd/Kafka/Milvus/gateway/ai-mock healthy; ingest/CMS/Client Up.
- Authenticated admin HTTP smoke: `/healthz` OK, `/api/cms/system/health` 200, fields khớp mock, CMS/Client HTTP 200.
  Payload không token: `INT-00-smoke.json`. Mock port host 18001, không chiếm :8001 của Claude.
- Trước bật consumers: jobs completed=40/failed=17, không pending/running; 3 nhóm Kafka gateway lag=0.
- DB tests: cả `TestJobRepository_RealTransitions` và `TestStores_RealVietnameseRoundTrip` PASS trong network `video-ai_default`.
  Lệnh: cross-compile test binaries rồi `docker run --rm --network video-ai_default --mount type=bind,source=E:/traning_ai-codex/backend/bin/pg.test,target=/tmp/pg.test,readonly -e TEST_POSTGRES_DSN=postgres://app:123456@postgres:5432/video_ai?sslmode=disable video-ai-gateway /tmp/pg.test '-test.v=true'`;
  tương tự mongo.test với `TEST_MONGO_URI=mongodb://app:123456@mongo:27017`.
- Test Windows qua localhost/127.0.0.1 có auth FAIL: `Get-NetTCPConnection` xác nhận **Postgres native PID 5932 chiếm :5432**,
  Mongo native PID 4760 chiếm 127.0.0.1:27017. Không đổi/xóa/dừng các DB native; dùng network Docker để đúng DB của stack.
- E: sau binaries/build 1.61 GiB, C: 2.14 GiB. Cần chạy build/test tuần tự; không pull/build image lớn.

## Pending

Docker image build mới chưa chạy (dùng cached image + binary mới :ro).
E2E AI thật không thuộc nghiệm thu mock, còn chờ AI-01/AI-07 và không được ghi INTEGRATED_REAL.


## Checkpoint

Lane: codex
Changed: backend mock/config/HTTP client + Dockerfile, compose/env, docs/tracker
Verified: Go tests/vet/build, CMS/Client checks, compose config, stack healthy, gateway→mock HTTP, PG/Mongo integration PASS
Contract touched: no (public OpenAPI unchanged; AI-API v0.1 DRAFT consumed)
Next safe task: INT-02 (Postgres); INT-01 real E2E waits AI-01/AI-07
