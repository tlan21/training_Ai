# INTEGRATION_MATRIX — AI endpoint × nơi tích hợp (owner: Codex)

Trạng thái: `MOCK_ONLY` (chỉ chạy với mock/stub) · `REAL_PENDING` (code gọi thật nhưng chưa có integration test thật PASS) ·
`INTEGRATED_REAL` (integration test gọi :8001 thật, `stub_mode=false`, PASS — ghi lệnh + ngày) · `(HIST)` = bằng chứng trước tách làn.
Chỉ `INTEGRATED_REAL` với endpoint `API_READY` trên `master` mới được tính DONE (README mục 5).

Bản đầu do Claude khởi tạo 2026-10-26 từ INVENTORY; từ đây Codex tự cập nhật.

| AI endpoint | Contract | Nơi gọi (Go) | Màn/flow | Trạng thái | Bằng chứng |
|---|---|---|---|---|---|
| `POST /v1/vision/completions` | v1.2 candidate (master pending) | `backend/internal/orchestrator/runner.go` (stage vision) qua `adapters/aihttp/ai_client.go` | Upload → category suggestion (CMS Highlight/Video) | MOCK_ONLY (NOW); INTEGRATED_REAL (HIST) | `docs/T4.1_bao_cao.md` Playwright 2 PASS 2026-10-14 |
| `POST /v1/asr/completions` | v1.2 candidate (master pending) | orchestrator stage asr | Subtitles CMS + Client video detail | MOCK_ONLY (NOW); INTEGRATED_REAL (HIST) | T4.1 |
| `POST /v1/highlight/completions` | v1.2 candidate (master pending) | orchestrator stage highlight (`runner.go` clamp clip ≤ duration) | Heatmap CMS/Client, AI clips | MOCK_ONLY (NOW); INTEGRATED_REAL (HIST) | T4.1 |
| `POST /v1/completions` | v1.2 candidate (master pending) | orchestrator stage summary; `handlers/cms/videos.go` regenerate | Summary review CMS, Client (chỉ approved) | MOCK_ONLY (NOW); INTEGRATED_REAL (HIST) — chất lượng AI-03 | T4.1 |
| `POST /v1/search/completions` | v1.2 candidate (master pending) | `handlers/search.go` (visual) + Milvus frame index | Client visual search | MOCK_ONLY (NOW); INTEGRATED_REAL (HIST) | `docs/T4.2_bao_cao.md` Playwright 3 PASS |
| `POST /v1/recommendation/completions` | v1.2 candidate (master pending) | `handlers/content.go:68` feed | Client feed | MOCK_ONLY (NOW); REAL_PENDING — user vector còn `mocks.NewVectorStoreMem()`; fallback popularity | INT-03 |
| `GET /health` | v1.2 candidate (master pending) | `handlers/cms/system.go` (`/api/cms/system/health`); gateway startup check | CMS Dashboard/Settings | MOCK_ONLY (NOW); INTEGRATED_REAL (HIST) | T4.1 |

Việc phải làm lại sau khi AI-01 phát hành v1 `API_READY`: chạy lại integration thật cho mọi dòng, đổi `(HIST)` → ngày mới, ghi `ACK AI-API v1.0` vào `coordination/codex/HANDOFF_OUT.md`.

## INT-00 hiện tại (2026-10-26)
- Unit HTTP round-trip đủ 6 endpoint + health với mock: `cd backend; $env:GOMAXPROCS='2'; go test -p 1 ./...` PASS.
- Health mock: `stub_mode=true`, `models_loaded=[]`; chỉ client opt-in `AI_ALLOW_STUB=1` chấp nhận.
- Bằng chứng HIST giữ nguyên; không có tích hợp thật mới. Stack/gateway smoke đang chuẩn bị; xem `verification/INT-00.md`.

## Latest gate checkpoint
- v1.2 optional video_id do Claude công bố, Codex consume tại fae980c; 3 unit packages PASS. No unilateral AI schema/code edit.
- Media transport + recommendation 503 fallback đã test MOCK_ONLY. Final v1.2 metadata runtime chưa rebuild/deploy do C: full.
- Read-only :8001 health: stub_mode=false, 6 models, visual_index=ok, recommendation_index=missing_collection. Không coi health riêng là pipeline integration.
- git log HEAD..master chưa có release #2 tại checkpoint; verify lại khi resume. Không có INTEGRATED_REAL mới.
