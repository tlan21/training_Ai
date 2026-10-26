# SESSION — Codex integration (resume here)

## Current gate
- Branch codex/integration; Release #1 96ebc24 received. No merge/push/release by Codex.
- BLOCKED_RESOURCE: C: ~0 GB, E: ~1.50 GiB. No cleanup/prune/delete performed; user capacity/cleanup decision pending.
- Docker stop/disk-scan CLI stalled; canceled only task-owned CLI requests. Reinspect daemon/container state after disk recovery.
  Last readonly HTTP gateway/CMS/Client all 200; do not assume latest binary deployed.
- User scope question INT-05/06 pending: CONTRACT_DECISIONS.md. No additional library endpoint added.

## Evidence / state
- INT-00 REVIEW: a96b883 / 122ee33 / b952675. npm ci CMS/Client; Go/CMS/Client checks; cached stack healthy,
  authenticated mock HTTP + real PG/Mongo tests PASS. Fresh Docker image rebuild not run.
- INT-02 REVIEW: 7efe2c9. PG interactions/history/likes/settings; real PG tests, restart persistence, MinIO206/privacy PASS.
- INT-04 PARTIAL: 8733f97 OpenAPI v0.2.0; 39e7af6 mapping/E2E. CMS/Client original playback + mobile click fix;
  Go/FE checks, 2 original browser cases + 2 player logic PASS. 10-item parity has gaps, no full parity claim.
- INT-11 PARTIAL: 7af1b1d portable Vision data URI/WAV HTTP + 503 fallback, unit/mock pipeline PASS;
  fae980c v1.2 video_id metadata (3 package unit PASS), not yet rebuilt/deployed to Linux runtime.
- INT-03 BLOCKED: 5615055 empty sandbox/identity policy; 9eded76 preference persistence source.
  Sandbox 2x idempotent PASS/entities0; 5 real PG tests PASS; Go tests/vet/build PASS with Go temp redirected to E:.
  New preference restart/login script checks NOT RUN; runtime update blocked.
- INT-12/13 BLOCKED_RESOURCE: CMS JWT currently persisted in browser storage; clean ingest build currently relies on cached legacy image.
  No implementation/test evidence for these fixes yet. INT-10 DEFERRED untouched.

## Runtime / local artifacts
- Existing project video-ai and volumes preserved. Milvus :19530; mock :18001, gateway :8000, CMS :5173.
- Claude owns real :8001; last health observation: stub_mode=false, 6 models; no real business integration claimed.
- CMS serves current dist bind :ro. Old Client container stopped; current production build on host :3000:
  npm run start -- --hostname 127.0.0.1 --port 3000. Reference capture server :8765 stopped.
- Ignored backend/bin/: Linux gateway/ai-mock/pg.test/mongo.test. Gateway binary prepared for preference commit 9eded76,
  older than fae980c metadata. Ignored docker-compose.local.yml mounts binary, ingest source and CMS dist.
- Temp workaround: GOTMPDIR/TMP/TEMP=E:/traning_ai-codex/backend/.tmp; GOMAXPROCS=1. Do not fill C: with linker/test temp.

## Next steps when unblocked
1. Check C:/E:, Docker and actual process/container states; no cache/data deletion without explicit user decision.
2. Read AGENTS/README, branch + git log HEAD..master. If approved Release #2 reached master, follow lane sync; never force/reset.
3. Rebuild latest Linux gateway with temp on E:, restart only owned runtime; ./e2e/verify_business_persistence.ps1 on mock.
   Must prove preferences after restart and at login, plus existing history/likes/settings/fallback checks.
4. Read latest Claude contract/handoff. v1.2 adds optional video_id + whole-video data URI indexing, consumed in source already.
   Release #2 was not on master at last check. Only switch real after master/API_READY and capacity, match key without logging it.
5. Real T4.1/T4.2 + index/search then matrix INTEGRATED_REAL where valid. Recommendation remains fallback until AI-09 encoder/schema/version/mapping verified.
6. INT-12 token/RAM and INT-13 own ingest image; continue parity after user scope decision. Do not mark unrun gates DONE.

## Handoffs
- HC-02/03 ACK; HC-04 READY_SANDBOX: sandbox_two_tower_ai09_20261026, 128/IP/IVF_FLAT/nlist1024, 0 rows at verification.
- HC-05 chose HTTP media option b; HO-01 addressed by Claude v1.2, source/unit consumed fae980c, runtime gate pending.
- HO-02 shared C:/Docker resource gate, user capacity/cleanup approval pending. No checkpoint copy/mount or Claude file writes.

## Evidence
verification/INT-00.md + smoke JSON; INT-02.md + persistence JSON (last run predates preference extension);
INT-03.md + sandbox JSON; INT-04.md + INT-04-design/; INT-11.md; TWO_TOWER_PRODUCT_MAPPING.md.
