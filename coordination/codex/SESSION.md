# SESSION — resume here (2026-10-26)

## Current state
- INT-14 contract checkpoint: public OpenAPI0.3.0 FeedPage with required recommendation_mode enum, existing ClipPage reused.
  Go types/spec generated with oapi-codegen2.8.0; CMS+Client types generated openapi-typescript7.13.0.
  gen Go compile +CMS/Client tsc PASS. Runtime behavior now implemented and verified; see verification/INT-14.md. Historical contract-only checkpoint retained.
- Active INT-16 IN_PROGRESS: Client same-origin API proxy (live browser localhost8000 auth abort8s, IPv4/CMS proxy healthy).
- INT-14 PARTIAL: primary PG popularity +honest3modes/realmetadata implemented; Go+5PG+46UI+8modes+live primary persistence PASS.
  Full-screen design gaps remainINT-06; liveClient transport needsINT-16. INT-15 TODO (HC-07 interactions/export). Historical INT-12/13 IDs kept; mapping committed to handoff.
- Release#3 masterfee83b2 received; read v1.3 +ttv2-data-v1/D18–D21. Next contract-first FeedPage0.3 then backend/Client; HO-03 still open.
- Branch codex/integration; Release#1 received, Release#2 master70bf011 merged5691526 without conflict.
  No Codex push/release/master update. Shared/Claude files only received via merge; no manual edits.
- INT-12 REVIEW d607226: CMS JWT/user RAM only, HttpOnly refresh bootstrap, single-flight401, role guard, logout race/cache clear,
  signed-out marker prevents restore after failed logout. CMS build/E2E types +41 browser tests PASS (50s), including2 live gateway auth cases.
  Login parity at390×844/1440×900 checked/fixed; verification/INT-12.md +screenshots/log. Full CMS parity remains INT-05.
- INT-03 personalized BLOCKED AI-09; sandbox+ID spec ready5615055, preference source9eded76 and runtime restart6d860ee verified.
  verify_business_persistence.ps1 PASS: preferences+login preferences/history/likes/settings/playback206/privacy/recommendation503 fallback.
- INT-11 BLOCKED HO-03 (fc5a3c7): real API transport. AI-API v1.2 six API_READY on master; recommendation DRAFT.
  Latest Linux gateway built (Go vet/test/build PASS), deployedmock and persistence PASS. Actual real deploy startup health timed out;
  independent container→host.docker.internal:8001 TCP timeout3s. Host127001:8001 health200/stubfalse/6models/401missingBearer PASS.
  Real video_flow/visual_search E2E NOT_RUN because preflight blocked; added real-health assertions and E2E types PASS.
  Gateway rolled back explicitmock health200. No new INTEGRATED_REAL claim.
- INT-13 BLOCKED capacity/full runtime build (048fb6a). Own image Dockerfile/allowlist/locked deps +compose now prepared; source target build14.31kB PASS.
  3 preprocess tests using extracted2unchangedDSP helpers +cachedCPU dependencies PASS0.147s; valid/silent2.5s/invalidmedia, no model import/load.
  Full new image NOT_BUILT, current ingest container remains cached video-ai-inference preprocessing-only. See verification/INT-13.md.
- INT-00/02 REVIEW; INT-04/05/06 PARTIAL. INT-10 DEFERRED untouched. INT-07/08 need AI/GPU gates, INT-09 depends on them.
- User scope question INT-05/06 remains pending (CONTRACT_DECISIONS.md); no extra public endpoint added.

## Runtime / resource
- Existing project video-ai preserved; gateway/mock/PG/Mongo/Redis/MinIO/Kafka/Milvus healthy, CMS5173/Client host127001:3000.
  Claude owns real :8001. Unrelated faktory_server still running. No Docker/WSL global restart, no volume/data deletion or prune.
- Windows Docker named-pipe _ping both time out. Existing Linux CLI works:
  wsl -d docker-desktop -- /mnt/host/wsl/docker-desktop/cli-tools/usr/bin/docker -H unix:///proc/195/root/run/docker.raw.sock ps
  PID195 is current dockerd; recheck after daemon restart. Compose/buildx binaries under same cli-tools/usr/local/lib/docker/cli-plugins/.
- Ignored backend/.tmp/docker-direct.yml maps gateway binary to daemon path /run/desktop/mnt/host/e/traning_ai-codex/backend/bin/gateway.
  Linux Compose root+mock+direct --no-deps --no-build --pull never gateway deployed latest mock binary.
  Dockerfile/compose new ingest image is not built: don't accidentally run up --build while restoring runtime.
- Shared AI key read from Claude-local .env per HC-05; passed only through process env/WSLENV, not persisted/logged.
- Last free C:1.98GiB E:1.53GiB. No large CPU Torch/base image download. Go TMP/TEMP/GOTMPDIR on E:/traning_ai-codex/backend/.tmp; GOMAXPROCS1.
- Current open user decision: Desktop restart affects unrelated faktory_server. Async question offered user restart / authorize Codex restart+restore / staymock.
  No answer/approval received; do not infer approval from elapsed time. Handoff HO-03 committed.

## Next safe actions
1. After user reports recovery or authorizes restart: recheck desktop transport, host AI health and container→host health; preserve/recover prior containers,
   not a new stack. Do not touch Claude runtime/checkpoints or other service configuration.
2. Set INT-11 IN_PROGRESS, commit. Use real AI key env, root+direct gateway host.docker.internal:8001/stub0, verify gateway6models, then
   npx playwright test e2e/video_flow.spec.ts e2e/visual_search.spec.ts --reporter=list. Only mark matrix real when all relevant tests PASS.
3. After sufficient disk: full ingest image build, tests inside new image (README command), deploy worker and pipeline regression. Until then INT-13 BLOCKED.
4. AI-09 handshake remains required for product vector collection/sync; no dataset IDs or fabricated zero vectors in product index.

Lane: codex
Changed: CMS auth+login parity; real gates/progress; own ingest package+compose/tests; preference runtime evidence
Verified:41CMS E2E+2live auth; Go vet/test/build; mock pipeline/restart persistence; source image14.31kB+3DSP tests; compose/type/diff checks
Contract touched: no public or AI schema change; AI-API v1.2 consumed from Release#2
Next safe task: INT-11 after HO-03; INT-13 after capacity recovery
