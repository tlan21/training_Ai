# INT-23 — Approved Docker application update

Owner: CODEX · Status: DONE (2026-10-28) · No master release/push.

User approved deployment after planA implementation INT-21 and live DB004 INT-22.
Updated gateway (with embedded orchestrator/cutter), CPU ingest worker, CMS :5173 and Client :3000.
No AI source, checkpoint, host inference process, database migration/backfill or datastore container was changed.

## Docker changes and deployed identity

- `.dockerignore`: exclude private backups, temporary binaries, environments, datasets/checkpoints and coordination from root build context.
- `backend/Dockerfile`: constrain Go build concurrency. `cms/Dockerfile`: require locked `npm ci`.
- `client/Dockerfile`: use direct TypeScript CLI. `docker-compose.yml`: application image tag parameter,
  restart unless-stopped and CMS/Client health checks.
- Removed gateway binary and CMS dist development binds through root-Compose recreation; only the existing ingest_work named volume remains on gateway/worker.
- All four live containers use `int23-fa8a382`. Local latest tags now reference these verified images; rollback-int23 tags retain old images.
  Exact image IDs, mounts, policies and start times: INT-23-before.json / INT-23-after-final.json.
- Gateway artifact SHA256: `15d87d90aee7a94360dede79b7eb2e73b4d4ad2395425fdbf60bcc4d68e48b1a`.
  CMS bundle `index-B8Z5jrXZ.js`; Client build `GDlD_B05A4hk6gQkPj679`, rewrite `http://gateway:8000/api/:path*`.
- Guarded Compose config compared every configured gateway/worker environment value against existing containers in memory;
  existing Bearer key was inherited through process environment, never logged or committed. Both recreations used
  `up -d --no-deps --no-build --pull never gateway ingest-worker cms client`, without dev overrides/full profile/down/remove-orphans.
  Nine unrelated running containers retained their IDs; databases, volumes, mock and Faktory were untouched.

## Build method and limits

C: ~3.1 GiB / E: ~0.9 GiB free at preflight. Initial standard gateway build with network disabled failed at uncached APK packages;
its log is retained as INT-23-build-gateway.log, not counted PASS. The frontend/Go clean dependency rebuild was not completed in Docker.
To avoid large dependency downloads, produced small offline artifact-overlay images on the captured existing runtimes:

- Four Linux Go binaries compiled from current source (actual artifact toolchain go1.26.0, amd64, CGO disabled, stripped).
- CPU worker main copied; requirements and reused DSP SHA256 exactly match the prior container. No Torch/model reinstall or AI code copy.
- CMS production bundle from verified INT-21 build packaged with current nginx config.
- Client lint, webpack production build and TypeScript checked again with the Docker gateway rewrite, packaged without build cache.
  Existing Linux runtime node_modules were retained; Client package/lock dependency source remains INT-17, unchanged by INT-21/23.

Recipes, source/lock/artifact hashes and build IDs: INT-23-builds.json. Each offline `buildx build --load --pull=false --network=none` succeeded;
logs: INT-23-image-{gateway,worker,cms,client}.log and INT-23-image-gateway-final.log. No image/cache/volume prune or data deletion.
Current standard Dockerfiles remain the clean rebuild path when resources/network permit; offline runtime inheritance is explicitly recorded.

## Real regression found and fixed

First deployed image passed health but real E2E found source width/height/fps null. Gateway audio relay decoded/re-encoded
an older event struct, dropping worker metadata before the orchestrator. `fa8a382` adds the three optional fields in
`backend/cmd/gateway/pipeline.go`; no AI API request/schema changed. Newly uploaded fixture now persists original 160x90, 10 FPS,
not resized 224x224. Legacy payloads remain accepted; old videos stay null without approved reprocessing.

Failed runs retained: initial missing metadata (INT-23-real-e2e.log); category label-selector timeout (INT-23-real-e2e-final.log);
duplicate detail/related heading selector (INT-23-metadata-e2e.log). Corrected test selectors use accessible textbox role and level-1 heading.
Timeout interrupted finally; identified exactly that run's one video/category and cleaned via protected API (204 each),
recorded INT-23-timeout-cleanup.json. No test skip, forced response, mock AI or weakened metadata assertion.

## VERIFIED-NOW 2026-10-28

- Backend: `go vet ./...`, `go test ./...`, `go build ./...` PASS. Test output INT-23-go.log;
  default external opt-in test skips are not new DB evidence (explicit live PG checks below/INT-21 provide that evidence).
- Client: direct eslint, `next build --webpack`, `tsc --noEmit` PASS; INT-23-build-client.log.
- E2E TypeScript and `git diff --check` PASS.
- Final actual stack command, E2E_GATEWAY_URL=http://127.0.0.1:8000 and E2E_AI_URL=http://127.0.0.1:8001:
  `node node_modules/@playwright/test/cli.js test e2e/video_flow.spec.ts e2e/visual_search.spec.ts --reporter=list`
  **3 PASS / 40.0s, no retries** (INT-23-e2e-pass.log):
  1. Upload via CMS proxy (16MiB padding) -> real CPU/Kafka/MinIO/AI -> encoded metadata160x90/10fps ->
     metadata PUT401/403/422 -> edit title/description/hashtags via CMS, reload and persisted readback ->
     approve summary -> create/edit category description/reload -> cut/publish -> real byte-range media -> CMS/Client playback ->
     Client original-video title and editorial hashtags. File URL object path and processed status unchanged by edit.
  2. Invalid upload reaches failed preprocessing and remains private.
  3. Real Siamese search, publish/privacy, Redis cache/latency and Client mapping.
- Final gateway healthy; CMS/Client HTTP200 and Docker health healthy; worker running and exercised by actual pipeline.
  AI health stub_mode=false, 6 loaded, degraded=[]; unchanged real host URL/key/stub0.
- All 79 predeployment video rows fingerprint `caaadd6588f7f8f4a2da381f51577b9a` and original 10 category rows
  fingerprint `2279cd784f346ec1e52ce40605752c91` match INT-22 exactly after tests. Active jobs0.
  Every new test upload soft-deleted, test clips rejected and test categories removed; test accounts/media retained with test provenance.
  INT-23-data-preserved.log / INT-23-final-health.json. Nine infrastructure container IDs rechecked unchanged after final tests.
- Scoped screenshots inspected: INT-23-client-detail.png (mobile title/summary/editorial tags/player), INT-23-cms-player.png.
  No full Stitch parity, model-quality, GPU/load or 48-hour soak claim.

## Rollback / next work

Old images remain locally tagged rollback-int23; exact identities and old bind paths in INT-23-before.json.
To restore the actual prior runtime, preserve current environment/key and datastore volumes, select rollback images and restore
readonly gateway-int14 binary and cms/dist binds from that snapshot. Do not restore/down the database or change host AI.
Rollback was not needed; no secret-bearing full inspect/config is retained. Guarded local runner is ignored backend/.tmp/apply-int23.ps1;
refresh daemon PID/socket after Docker Desktop restart. Existing compose/buildx plugin path workaround remains necessary on this host.

Next safe task: INT-05 remaining scoped Stitch parity; INT-06 library/forgot-link decisions still pending. No new API routes inferred.
INT-03 recommendation remains DRAFT/NO_DATA, GPU/load/soak gates remain open. No master/shared status edit or push authorized.

Lane: codex
Changed: Docker context/files/compose; gateway metadata relay; real E2E; owned task/session/evidence
Verified: offline images4; Go gates; Client gates; real E2E3PASS40s; 79/10 fingerprints; final health/infra9 unchanged
Contract touched: no (public0.4.0 consumed; AI-APIv1.3 unchanged)
Next safe task: INT-05 visual parity
