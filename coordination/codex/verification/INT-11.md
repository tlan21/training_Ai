# INT-11 — Docker gateway → host AI media (2026-10-26)

Owner CODEX; project skill backend_endpoint.md. Public OpenAPI unchanged; uses existing Vision data URI and ASR URL contract.

- Vision resolves ingest JPEGs and sends data URI bytes; no Docker filesystem paths in the request. Read failures stop before HTTP.
- Gateway streams its owned scratch WAV to `raw-videos/audio/<video_id>.wav`; ASR gets a MinIO URL signed for the 2-hour job lifetime.
  Uses canonical validated ingest directory, not an arbitrary event-provided audio path. No checkpoint/mount/AI model change.
- Temporary audio object cleanup runs on success or failure with separate timeout; failure is logged. Existing job failure/cancel handling retained.
- Mock recommendation returns 503 AI_UNAVAILABLE for cold-start, matching v1.x; gateway must use popularity fallback.
  Search query_metadata includes execution_time_ms. Health keeps stub_mode=true and no loaded models.

VERIFIED-NOW:

- `GOMAXPROCS=2 go test -p 1 ./...`, `go vet -p 1 ./...`, `go build -p 1 ./...`: PASS.
- After final data URI change: `go test -p 1 ./cmd/gateway ./internal/adapters/aihttp ./internal/mocks`: PASS.
  Tests assert encoded bytes/auth, missing-file stop, WAV unchanged + correct TTL, 503/error mapping, explicit stub opt-in.
- Linux gateway + ai-mock cross-build PASS; cached runtime containers restarted with new binaries, no image pull/build.
- `./e2e/verify_business_persistence.ps1`: PASS after transport change: real ingest → new media transport → HTTP mock → real storage/cut;
  restart persistence, playback HTTP206, privacy and **feed popularity fallback under recommendation 503** PASS.
  Latest sanitized evidence: `INT-02-persistence.json` (recommendation_fallback=true).

Gate still open: Vision base64 requests have no video identity and inference skips visual frame indexing. HO-01/HC-05 requires
Claude's optional video_id contract addition before end-to-end real search can pass. No field was added to AI request unilaterally.
Claude reports :8001 UP in HC-05; endpoint contract remains DRAFT/not on master, gateway remains MOCK_ONLY.

Checkpoint:

Lane: codex
Changed: aihttp + tests, gateway audio staging/pipeline + tests, mock fidelity, persistence/fallback regression
Verified: Go checks/Linux builds + mock pipeline/persistence/fallback PASS
Contract touched: no (AI schema unchanged; v1.x-compatible existing media formats)
Next safe task: INT-03 sandbox/ID mapping per HC-04; real index gate waits Claude HO-01
