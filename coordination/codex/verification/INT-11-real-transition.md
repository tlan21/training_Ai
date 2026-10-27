# INT-11 — reviewed real-API transition (2026-10-27)

Preflight complete; applying this plan awaits explicit user confirmation because an earlier targeted gateway-start action was rejected
by automatic review with reason “blocked by policy”. No alternate start/reconfiguration was used to bypass that rejection.

## Verified readiness
- AI-APIv1.3 release#3 present on master; six endpoints API_READY, recommendation stillDRAFT.
- Host /health200, stub_mode=false and6models (AI-HEALTH-20261027.json).
- From deployed ingest container: host.docker.internal:8001/health200, stub_mode=false and6models
  (INT-11-transport-recheck.log); missing Bearer POSTsearch401. Old HO-03 TCP timeout no longer reproduces.
- New Go startup artifact backend/bin/gateway-int18 built/tested underINT-18; SHA256
  da8d646b8a8bdfc48775ae9b15fd2ed313e50cedbedb548e307e4a8194cda280.
- Existing stack healthy with gateway on explicit mock; own ingest and Next16Client already deployed/tested. No AI checkpoint/source change needed.

## Exact change prepared, not applied
Local override backend/.tmp/docker-real-direct.yml merges with root Compose for gateway only:
- AI_BASE_URL=http://host.docker.internal:8001, AI_ALLOW_STUB=0;
- AI_SERVICE_KEY required from secure process environment, never persisted or printed;
- readonly /usr/local/bin/gateway mount points at the tested gateway-int18 artifact.

Compose config --quiet PASS using a preflight placeholder (never sent to AI). No production secret in this artifact/report.
After confirmation, read the shared HTTP key from the previously authorized Claude-local env location, pass through process env/WSLENV only,
and apply root+real-direct with `up -d --no-deps --no-build --pull never gateway`. Do not start/recreate any other service or remove orphans/volumes.

## Verify / rollback
- Save previous gateway AI env/binary mapping in process memory for rollback; do not log the secret. Existing rollback config:
  root+docker-compose.mock.yml+backend/.tmp/docker-direct.yml, original mock key from existing gateway configuration.
- Check gateway health +authenticated CMS system health real6models; run e2e/video_flow.spec.ts and visual_search.spec.ts with explicit IPv4 gateway/AI URL.
  Same-origin CMS/Client endpoints remain unchanged. Test fixtures carry E2E provenance and clean up only their own video/index records.
- On failure, restore original mock mapping/env; report failure rather than marking matrixreal. Do not edit Claude code/checkpoints or loosen readiness assertions.
- Only after relevant real tests PASS mark the affected matrix rows INTEGRATED_REAL; recommendation remains primary popularity/DRAFTpersonalized.

Current state: **not applied**, gateway stillmock, real E2E NOT_RUN. No master release/push authorized.
