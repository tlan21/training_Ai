# INTEGRATION_MATRIX — AI endpoint × nơi tích hợp (owner: Codex)

Trạng thái: `MOCK_ONLY` (chỉ chạy với mock/stub) · `REAL_PENDING` (code gọi thật nhưng chưa có integration test thật PASS) ·
`INTEGRATED_REAL` (integration test gọi :8001 thật, `stub_mode=false`, PASS — ghi lệnh + ngày) · `(HIST)` = bằng chứng trước tách làn.
Chỉ `INTEGRATED_REAL` với endpoint `API_READY` trên `master` mới được tính DONE (README mục 5).

Bản đầu do Claude khởi tạo 2026-10-26 từ INVENTORY; từ đây Codex tự cập nhật.

| AI endpoint | Contract | Nơi gọi (Go) | Màn/flow | Trạng thái | Bằng chứng |
|---|---|---|---|---|---|
| `POST /v1/vision/completions` | v1.3 API_READY | `backend/internal/orchestrator/runner.go` (stage vision) qua `adapters/aihttp/ai_client.go` | Upload → category suggestion (CMS Highlight/Video) | INTEGRATED_REAL | 2026-10-27 T4.1 real upload/category PASS; `verification/INT-11-real-e2e.log` |
| `POST /v1/asr/completions` | v1.3 API_READY | orchestrator stage asr | Subtitles CMS + Client video detail | INTEGRATED_REAL | 2026-10-27 T4.1 real pipeline/subtitles PASS; same log |
| `POST /v1/highlight/completions` | v1.3 API_READY | orchestrator stage highlight (`runner.go` clamp clip ≤ duration) | Heatmap CMS/Client, AI clips | INTEGRATED_REAL | 2026-10-27 T4.1 real timeline/publish/playback PASS; same log |
| `POST /v1/completions` | v1.3 API_READY | orchestrator stage summary; `handlers/cms/videos.go` regenerate | Summary review CMS, Client (chỉ approved) | INTEGRATED_REAL — model quality remains AI-03 | 2026-10-27 T4.1 real draft/editor approval/privacy PASS; regenerate route not separately exercised |
| `POST /v1/search/completions` | v1.3 API_READY | `handlers/search.go` (visual) + Milvus frame index | Client visual search | INTEGRATED_REAL | 2026-10-27 T4.2 real index/search/privacy/cache/Client PASS; same log + `INT-11-visual-latency.json` |
| `POST /v1/recommendation/completions` | v1.3 DRAFT | optional AI feed path; primary PG popularity enabled | Client feed | REAL_PENDING — personalized disabled under D18/D19 | INT-03/AI-12 product vectors and production gate pending; live `recommendation_mode=popularity` verified |
| `GET /health` | v1.3 API_READY | `handlers/cms/system.go` (`/api/cms/system/health`); gateway startup check | CMS Dashboard/Settings | INTEGRATED_REAL | 2026-10-27 startup/authenticated system health6 + host stubfalse PASS; `INT-11-live-health.json`, `INT-11-final-runtime.json` |

Release#3 AI-API v1.3 đã nhận từ masterfee83b2 qua merge35cd1a9. Six API_READY endpoints now have real HTTP integration evidence; recommendation remains DRAFT. Public OpenAPI0.3.1 unchanged.

## Current real gate — 2026-10-27
- User explicitly approved switching to real AI. Gateway only recreated, canonical `http://host.docker.internal:8001`, `AI_ALLOW_STUB=0`, shared Bearer key passed in process environment only; no Claude code/checkpoint/mount changes.
- `E2E_GATEWAY_URL=http://127.0.0.1:8000 E2E_AI_URL=http://127.0.0.1:8001 node node_modules/@playwright/test/cli.js test e2e/video_flow.spec.ts e2e/visual_search.spec.ts --reporter=list`: **3 PASS / 54.3s**, no retry/mock.
- Host health stubfalse/6models/degradedempty, authenticated gateway health6, missing Bearer401. Real Kafka/own CPU worker/MinIO/AI/Milvus/cutter/CMS/Client used.
- Cold visual20: p95 150.87ms/max178.14ms; warm20: p95 11.74ms/max13.97ms. All below2s; this small sequential sample is not load/soak acceptance.
- Final gateway healthy/real; all3 exact fixture videos softdeleted, publication/cache privacy tests PASS. Real model quality/GPU/personalized readiness not claimed.
- Sections below retain historical mock/transport checkpoints and are superseded by this current gate.

## INT-00 hiện tại (2026-10-26)
- Unit HTTP round-trip đủ 6 endpoint + health với mock: `cd backend; $env:GOMAXPROCS='2'; go test -p 1 ./...` PASS.
- Health mock: `stub_mode=true`, `models_loaded=[]`; chỉ client opt-in `AI_ALLOW_STUB=1` chấp nhận.
- Bằng chứng HIST giữ nguyên; không có tích hợp thật mới. Stack/gateway smoke đang chuẩn bị; xem `verification/INT-00.md`.

## Latest gate checkpoint —2026-10-26
- v1.2 optional video_id consumed atfae980c; latest gateway binary rebuilt/deployed. Media transport + recommendation503 fallback,
  runtime preferences/history/likes/settings persistence + restart/playback206/privacy PASS with MOCK_ONLY.
- Host :8001 health200/stub_mode=false/6models; missing-Bearer401 PASS. Release#2 on master and consumed, so contract gate is satisfied.
- Actual real gateway deployment failed startup health: host.docker.internal:8001 timeout. Independent ingest-worker TCP request likewise times out.
  Both Windows Desktop named pipes also hang; direct daemon Linux CLI works. HO-03/user Desktop restart decision pending.
- Gateway restored explicit mock health200. Real upload/search E2E NOT_RUN (preflight blocked), no new INTEGRATED_REAL entry.
  Evidence verification/INT-11-real-health.json + INT-11-real-blocker.json.
