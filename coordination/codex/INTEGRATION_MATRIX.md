# INTEGRATION_MATRIX — AI endpoint × nơi tích hợp (owner: Codex)

Trạng thái: `MOCK_ONLY` (chỉ chạy với mock/stub) · `REAL_PENDING` (code gọi thật nhưng chưa có integration test thật PASS) ·
`INTEGRATED_REAL` (integration test gọi :8001 thật, `stub_mode=false`, PASS — ghi lệnh + ngày) · `(HIST)` = bằng chứng trước tách làn.
Chỉ `INTEGRATED_REAL` với endpoint `API_READY` trên `master` mới được tính DONE (README mục 5).

Bản đầu do Claude khởi tạo 2026-10-26 từ INVENTORY; từ đây Codex tự cập nhật.

| AI endpoint | Contract | Nơi gọi (Go) | Màn/flow | Trạng thái | Bằng chứng |
|---|---|---|---|---|---|
| `POST /v1/vision/completions` | v0 DRAFT | `backend/internal/orchestrator/runner.go` (stage vision) qua `adapters/aihttp/ai_client.go` | Upload → category suggestion (CMS Highlight/Video) | INTEGRATED_REAL (HIST) | `docs/T4.1_bao_cao.md` Playwright 2 PASS 2026-10-14 |
| `POST /v1/asr/completions` | v0 DRAFT | orchestrator stage asr | Subtitles CMS + Client video detail | INTEGRATED_REAL (HIST) | T4.1 |
| `POST /v1/highlight/completions` | v0 DRAFT | orchestrator stage highlight (`runner.go` clamp clip ≤ duration) | Heatmap CMS/Client, AI clips | INTEGRATED_REAL (HIST) | T4.1 |
| `POST /v1/completions` | v0 DRAFT | orchestrator stage summary; `handlers/cms/videos.go` regenerate | Summary review CMS, Client (chỉ approved) | INTEGRATED_REAL (HIST) — chất lượng AI-03 | T4.1 |
| `POST /v1/search/completions` | v0 DRAFT | `handlers/search.go` (visual) + Milvus frame index | Client visual search | INTEGRATED_REAL (HIST) | `docs/T4.2_bao_cao.md` Playwright 3 PASS |
| `POST /v1/recommendation/completions` | v0 DRAFT | `handlers/content.go:68` feed | Client feed | REAL_PENDING — user vector còn `mocks.NewVectorStoreMem()`; fallback popularity | INT-03 |
| `GET /health` | v0 DRAFT | `handlers/cms/system.go` (`/api/cms/system/health`); gateway startup check | CMS Dashboard/Settings | INTEGRATED_REAL (HIST) | T4.1 |

Việc phải làm lại sau khi AI-01 phát hành v1 `API_READY`: chạy lại integration thật cho mọi dòng, đổi `(HIST)` → ngày mới, ghi `ACK AI-API v1.0` vào `coordination/codex/HANDOFF_OUT.md`.
