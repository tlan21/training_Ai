# INT-03 — independent preparation, 2026-10-26

Owner CODEX; skill db_migration.md. Product personalization is not complete.

## Sandbox and mapping

- `5615055`: schema spec §4.3 written before initializer; isolated collection `sandbox_two_tower_ai09_20261026`.
- Two real initializer runs PASS, second idempotent: schema verified, 128-d, IP/IVF_FLAT/nlist1024, entities=0.
  Command: `docker run --rm --pull never --network video-ai_default -e MILVUS_HOST=milvus --mount type=bind,source=E:/traning_ai-codex/infra/milvus/init_recommendation_sandbox.py,target=/tmp/init_sandbox.py,readonly video-ai-inference python /tmp/init_sandbox.py`.
- No training/model/export imported, no product collection/vector write, frame collection unchanged. RE:HC-04 READY_SANDBOX committed.
- Product identity/missing-input rules: TWO_TOWER_PRODUCT_MAPPING.md. Exact usr_*/vid_*; no arbitrary MovieLens mapping; AI-09 encoder/version still required.

## Preference persistence bug found during mapping

Before: PUT preferences wrote 128 zero values into memory; GET me always returned []; login also returned empty preferences.
After in source: existing user_preferences table is source of truth; atomic replacement locks the user row to serialize concurrent writes;
FK/unique errors roll back the old preferences. Handler accepts distinct category IDs, rejects names/unknown/duplicate IDs;
GET/profile/login return stored preferences. No fake recommendation vector is written.

VERIFIED-NOW:

- `GOMAXPROCS=2 go test -p 1 ./...`: PASS, including handler validation/write-failure/readback tests.
- `go vet -p 1 ./...`: PASS. Initial `go build -p 1 ./...` then failed in Windows linker because C: ran out of space.
- Retried build with `GOMAXPROCS=1 GOTMPDIR=E:/traning_ai-codex/backend/.tmp go build -p 1 ./...`: PASS.
- Cross-compiled real PG tests: all **5 PASS** in video-ai_default: interactions/privacy/cursor; invalid input;
  preferences replacement/rollback/isolation; jobs; settings atomic patch.
- Linux gateway cross-build with GOTMPDIR on E: PASS. Binary prepared, runtime restart **not confirmed**: Docker control commands stalled at full C:.
- `verify_business_persistence.ps1` now also checks preferences after restart and at login, but **this new preference extension has not run yet**.
  Prior INT-02/11 pipeline/persistence/fallback evidence remains valid for its original checks; do not infer preference runtime PASS from that JSON.

## Current blockers

- **BLOCKED_RESOURCE**: C: reached ~0 GB, Docker control commands stall. E: ~1.50 GiB. No cleanup/prune/delete authorized or performed.
  Read-only Docker disk scan was canceled after hanging. User capacity/cleanup choice requested; do not run image build/pull.
- Before concluding this checkpoint, read-only HTTP checks still returned 200 for gateway/CMS/Client; gateway may still be the preceding binary.
  A pending `docker stop video-ai-gateway-1` request may complete when Docker recovers. Reinspect container state before restart/testing.
- Product vectors require AI-09 encoder/schema/version and both-lane ID mapping validation; recommendation remains DRAFT/503/fallback.
- Real AI integration requires release/master + API_READY + tests. Latest v1.2 release candidate supports HO-01 video_id; master had no new commits when last checked.

Checkpoint:

Lane: codex
Changed: sandbox/spec/identity policy; preferences PG port/repo/handler/wiring/tests; persistence-script extension
Verified: sandbox 2× PASS; Go unit/vet/build and 5 real PG tests PASS; runtime preference restart NOT RUN
Contract touched: no public/AI schema change (existing preference API/table)
Next safe task: restore disk/Docker capacity, restart prepared gateway, run preference persistence; consume AI-API v1.2 then real gate
