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

## Follow-up AI-API v1.2

Claude published optional video_id + data URI indexing (HO-01 addressed). fae980c consumes identity from canonical ingest directory;
all frames remain in one request. Tests assert metadata + bytes; 3 packages aihttp/mocks/gateway PASS with TMP/GOTMPDIR on E:.
No fresh Linux binary/runtime deploy for this final metadata change: C: full/Docker control stalled. Rebuild before real tests.
Release #2 not yet present in master at last check; no real integration claim. Missing identity above describes the earlier checkpoint.

## Current checkpoint after Release #2
- Master70bf011 received via merge5691526; AI-API v1.2 sixAPI_READY, recommendationDRAFT. Earlier master-pending notes above are historical.
- Go vet/test/build all PASS; latest Linux gateway rebuilt/deployed into existing stack via bundled Linux Docker CLI/direct Unix socket.
- verify_business_persistence.ps1 MOCK_ONLY PASS again (6d860ee), including stored preferences returned after restart and subsequent login.
- Actual real gateway deployment with shared Bearer key env and AI_ALLOW_STUB=0 failed startup /health deadline (host.docker.internal:8001).
  Independent urllib probe from ingest-worker: sameTCP timeout3s. Host127001:8001 realhealth200/6models/stubfalse and missing-Bearer401 PASS.
  Both Desktop named pipes timeout; direct Docker daemon responds. Gateway restored mock health200. HO-03/user Desktop restart decision pending.
- Real video_flow/visual_search E2E NOT_RUN: preflight stopped before Playwright. No new INTEGRATED_REAL claim.
  Evidence: INT-11-real-health.json, INT-11-real-blocker.json. Auth-only live gateway tests belong to INT-12 and do not prove AI integration.

## Current acceptance — VERIFIED-NOW 2026-10-27 (supersedes prior blockers)

- Release#3 AI-APIv1.3/masterfee83b2 received; six API_READY endpoints unchanged, recommendationDRAFT. Public OpenAPI0.3.1 unchanged.
- User explicitly approved real transition (eaca064). Recreated gateway only using existing image, no build/pull/dependency recreation.
  Canonical `AI_BASE_URL=http://host.docker.internal:8001`, `AI_ALLOW_STUB=0`; shared HTTP key read into process env only, never printed/committed.
  No AI source/checkpoint/model mount or legacy inference container started. Faktory/other services untouched.
- Tested INT-18 startup binary mounted readonly from backend/bin/gateway-int18, SHA256
  da8d646b8a8bdfc48775ae9b15fd2ed313e50cedbedb548e307e4a8194cda280 (source91e7ef8; Go vet/test/build and delayed real PG tests already PASS).
- Gateway readiness200 +authenticated CMS system health6 PASS. Host AI stubfalse/6models/degradedempty; visual_index ok.
  Missing Bearer POSTsearch401 PASS. Evidence INT-11-live-health.json +INT-11-final-runtime.json.

Actual PowerShell command (no AI key needed in browser test environment):
```powershell
$env:E2E_GATEWAY_URL='http://127.0.0.1:8000'
$env:E2E_AI_URL='http://127.0.0.1:8001'
node node_modules/@playwright/test/cli.js test e2e/video_flow.spec.ts e2e/visual_search.spec.ts --reporter=list
```
**3 PASS, 0 failures, no retry, 54.3s**; INT-11-real-e2e.log:
1. Real upload→processed→ASR/vision/highlight/summary draft→editor approval→clip cut/publish→CMS and mobile Client playback/seek:38.4s.
   Real Kafka, own CPU/PyAV worker, MinIO, HTTP AI, DB, FFmpeg and UI; draft summary hidden until approval, media range206.
2. Invalid MP4→failed preprocessing/private public404:1.6s.
3. Real Siamese/Milvus index→search exact fixture score>0.95/timestamp<8s/JPEG thumbnail200, publication/cache privacy,
   desktop/mobile Client visual search and deletion404:12.5s.

Sequential visual search latency, local CPU runtime (INT-11-visual-latency.json):

| Sample | n | p50 ms | p95 ms | max ms |
|---|---:|---:|---:|---:|
| Cold gateway cache (distinct thresholds) |20|48.53|150.87|178.14|
| Warm gateway cache |20|8.92|11.74|13.97|

All below2s assertion. This sample is not GPU/load/48hsoak or model quality acceptance. Screenshots retained in INT-11-real-screenshots/;
they prove exercised flow rendering, not full Stitch Design Parity acceptance.

- First attempt: npx wrapper generated `npm exec px`, failed before any Playwright test. Script restored original mock configuration.
  Preserved INT-11-runner-attempt1.log; retried through installed Node CLI, with no dependency download needed for the fix.
- Final independent runtime readback: gateway healthy, canonicalreal/stub0, original non-AI env comparison passed before apply.
  Exactly three own fixtures vid_dmfcfh717m5b/vid_dmfcftrr3gtp/vid_dmfcfukqtor5 verified softdeleted, no existing data deleted.
  Test accounts/media retained as before; no test data promoted to product exports. Primary feed mode remains `popularity`.
- Six matrix rows now INTEGRATED_REAL; recommendationDRAFT stillREAL_PENDING/disabled, missing product recommendation collection expected.
  Regenerate-summary route was not separately retested; endpoint completions exercised through real upload stage.
- No application source change needed in this step, so prior source/build checks retained; no full release gate rerun or master/push performed.
  Runtime still uses a local verified binary bind; clean production gateway image deployment is a separate release step.

Lane: codex
Changed: gateway real configuration/startup binary deployment; owned evidence/matrix/tracker/handoff
Verified:3real Playwright PASS54.3s; strict6model/stubfalse/systemhealth;401;finalrealreadback/3fixturecleanup/popularity
Contract touched: no (public0.3.1; AI-APIv1.3 consumed)
Next safe task: INT-14 existing pagination gap; release gates only when user requests release
