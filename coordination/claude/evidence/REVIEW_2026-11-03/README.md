# REVIEW reconciliation — 15 inherited INT tasks · 2026-11-03 (Claude)

Method: each task's acceptance block in `coordination/codex/TASKS.md` (snapshot a317c3c) mapped bullet → evidence by three read-only
review passes, then spot-checked. `V/` = `coordination/codex/verification/`, `CE/` = `coordination/claude/evidence/`.
VERIFIED-NOW = re-run/inspected 2026-11-03 on the running stack (gateway `int06-d41fe71`, CMS `int05-fd0b418`, client `int06-e33e956`,
ingest `int23-fa8a382`, inference `ai-v3.0-48735ff`). No new test data was created for this pass.

Re-run today: Go `./internal/mocks ./internal/adapters/aihttp ./internal/handlers/... ./internal/gen ./internal/domain` PASS; real-PG
`TestSettingsRepository_RealAtomicPatch` (TEMP table, in gateway container) PASS; embedded spec in `backend/internal/gen` = `infra/openapi.yaml`
0.8.0 and CMS/Client generated types identical; container inspections listed per task. Not run: `TestInteractionRepository_*` (writes real
tables), `client_auth_live` / `video_flow` (create users/uploads).

| Task | Verdict | Evidence (main) | Note |
|---|---|---|---|
| INT-00 | CLOSE-WITH-NOTE | `V/INT-00.md`, `V/INT-00-smoke.json`; NOW: datastores healthy, Milvus `127.0.0.1:19530`, gateway mounts only `ingest_work`, mock tests PASS | Mock-switch item superseded by real AI runtime (AI-22, `AI_BASE_URL=http://inference-service:8001`, `AI_ALLOW_STUB=0`). |
| INT-01 | CLOSE | `V/INT-11-real-e2e.log`, `V/INT-28-regression.log`, `V/INT-31-real-e2e.log`, `V/INT-57.md` | Latest full real E2E on the previous gateway image (INT-57). |
| INT-02 | CLOSE-WITH-NOTE | `V/INT-02.md`, `V/INT-02-persistence.json`; NOW: settings real-PG PASS, wiring uses `pg.InteractionRepo`/`pg.SettingsRepo`, interactions survive gateway recreate (70 rows older than current start) | — |
| INT-11 | CLOSE-WITH-NOTE | `V/INT-11.md`, `V/INT-11-real-e2e.log`, INT-31/INT-57 | "host :8001" wording is history; transport proven on the inference container. |
| INT-12 | CLOSE-WITH-NOTE | `V/INT-12.md`, `V/INT-50-ui-regression.log` (cms_auth 2026-10-30); NOW: `cms/src/stores/authStore.ts` never persists the JWT; live login in `CE/INT-50_2026-11-02/` | Forgot/reset test obsolete (INT-47). |
| INT-13 | CLOSE | `V/INT-13*.{md,log,json}`, `V/INT-18-worker-tests.log`; NOW: worker torch CPU-only, only DSP files, real uploads processed 2026-11-02 | Event gained 3 optional metadata fields in INT-23 (intended). |
| INT-15 | CLOSE-WITH-NOTE | `V/INT-15*.{md,log,json}`, `CE/AI-12_2026-10-26/verify_INT-15_*.json` (RE:INT-15 ACCEPTED) | Format accepted; export still NO_DATA (`PRODUCT_DATA_ORIGIN=unknown`, 41 unknown-origin + 29 test interactions). Data readiness = AI-12/D19, not INT-15. |
| INT-16 | CLOSE | `V/INT-16*.{md,log}`, `V/INT-17-live-auth.log`; NOW: compiled rewrite → `gateway:8000/api/:path*`, `:3000/api/*` returns gateway envelope | Transport files unchanged since 3f3f7e4. |
| INT-17 | CLOSE-WITH-NOTE | `V/INT-17*.{md,log,json}`; NOW: next 16.4.3 / react 18.3.1 in container | New runtime high (follow-redirects 1.16.1 via axios, GHSA-mrwp-f3q8-3g9p) fixed: e33e956 → 1.16.2, `npm audit --omit=dev` 0, client `int06-e33e956` built (lint+tsc+build) and regression 96/96 PASS. 16 moderate = dev-only eslint chain. |
| INT-18 | CLOSE | `backend/internal/startup/wait.go` + tests, `V/INT-18*.{md,log}`, `V/INT-27.md` cold start; NOW: worker retried Kafka at start and connected, consumer lag 0 | "Alternate route" clause obsolete (HO-05). |
| INT-19 | CLOSE-WITH-NOTE | `V/INT-19.md`; NOW: openapi feed/catalog 422 + cursor text, `handlers/content_pages_test.go` PASS | Pagination behaviour tracked under INT-14. |
| INT-20 | CLOSE-WITH-NOTE | `V/INT-20.md`; NOW: `TestCMSPlanAContract` PASS on 0.8.0 | Contract 0.4.0 superseded by 0.8.0, rules still asserted. |
| INT-21 | CLOSE-WITH-NOTE | `V/INT-21.md`, `V/INT-23.md`, `CE/INT-50_2026-11-02/` live metadata/categories | "Custom rules deferred" partly superseded by approved keyword rules (INT-44/48); old videos keep NULL width (no backfill, by design). |
| INT-24 | CLOSE | `V/INT-24-real-edit-approval.log`, INT-26 run; code `backend/internal/handlers/content.go` exposes summary only when `summary_status=approved`; draft labels in deployed bundles | — |
| INT-29 | CLOSE | `infra/openapi.yaml` DELETE contract, `TestVideoDeletionStorageContract` + `handlers/cms/videos_test.go` PASS now; live repeat delete `V/INT-28.md`, INT-50 cleanup files | 409 active-writer covered by unit tests (acceptance is the contract). |

INT-38 (16th REVIEW) was closed earlier (`CE/INT-50_2026-11-02/README.md`).
