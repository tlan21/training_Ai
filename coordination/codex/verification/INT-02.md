# INT-02 — storage verification 2026-10-26

Owner CODEX; project skill `backend_endpoint.md`. Public OpenAPI unchanged, AI-API v0.1 consumed as MOCK_ONLY.

## Scope

- Existing tables/seed `user_interactions` and `system_settings` verified in schema and running Postgres; no DDL/migration needed.
- `POST /api/interactions` persists events and validates processed video + matching published clip; duration fits INT and is nonnegative.
- History groups click/watch_time by clip, sums duration, orders most recent event; likes deduplicate by clip. Both isolate user,
  validate cursor, page by latest interaction ID, and hide content no longer processed/published. Video-only events remain stored
  for popularity/recommendation, but do not invent a clip for the history API's Clip schema.
- Popularity uses stored interactions from the last seven days.
- History/likes reuse existing public Clip serializer and MinIO presigned playback helper.
- Settings PATCH writes in one atomic SQL statement, retains untouched keys; false/zero supported, API masks key, failures do not report success.
  Saving an API key persists configuration only; runtime auth keys continue to come from env on both services (no inference key rotation here).
- No user/Claude data deleted or overwritten. Repo tests create only uniquely named fixtures; settings test uses TEMP table on one connection.

## VERIFIED-NOW

| Command | Result |
|---|---|
| `cd backend; GOMAXPROCS=2 go test -p 1 ./...` | PASS, including settings masking/validation/failure and history playback serialization tests; real DB tests opt-in |
| `cd backend; GOMAXPROCS=2 go vet -p 1 ./...` | PASS |
| `CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go test -p 1 -c -o bin/pg.test ./internal/adapters/pg` | PASS |
| `docker run --rm --network video-ai_default --mount type=bind,source=E:/traning_ai-codex/backend/bin/pg.test,target=/tmp/pg.test,readonly -e TEST_POSTGRES_DSN=postgres://app:123456@postgres:5432/video_ai?sslmode=disable video-ai-gateway /tmp/pg.test '-test.v=true'` | 4 tests PASS: events/history/likes privacy+cursor+dedup+seven-day popularity; invalid input; job transitions; atomic settings patch |
| `CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -p 1 -o bin/gateway ./cmd/gateway` | PASS; freshly built gateway started on cached runtime image |
| `./e2e/verify_business_persistence.ps1` | PASS; fixture upload→real ingest→mock AI HTTP→real Mongo/PG→real FFmpeg/MinIO→publish; interactions/settings survive gateway restart |

First real PG test caught `42P08 inconsistent types deduced for parameter $2` in INSERT SELECT; fixed typed parameters at the shared adapter.
Reran the same four real tests: all PASS. No failing attempt counted as acceptance.

Persistence output: `INT-02-persistence.json` (no tokens/keys). History count=1, watched duration=2, likes count=1 after restart;
settings retained and key masked; both playback URLs returned HTTP 206; unpublished interaction rejected 404;
soft-deleting this test's video removed it from history/likes. Script restores only its own threshold change,
and leaves concurrent caller changes intact. Test viewer/MinIO objects retained per existing E2E policy.

No UI code changed, so no design parity change. No new dependency, AI code or Milvus interface change.
Real AI E2E and Docker image rebuild remain pending separately; these results establish business persistence with MOCK_ONLY AI.

## Checkpoint

Lane: codex
Changed: PG interaction/settings adapters + tests, settings port/domain, gateway/CMS/auth handlers + tests, persistence script
Verified: Go tests/vet/Linux build, 4 real Postgres tests, restart persistence HTTP smoke PASS
Contract touched: no (public OpenAPI unchanged; AI-API v0.1 DRAFT consumed)
Next safe task: INT-04 (OpenAPI original video playback)
