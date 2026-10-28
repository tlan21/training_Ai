# INT-21 — CMS planA implementation, 2026-10-28

Runtime update: [INT-22](INT-22.md) subsequently applied004 to the live product DB with backup/data/schema/repeat checks.
Application services remain the prior deployment. The no-live-migration statements below describe the earlier source checkpoint.

Owner CODEX. Status: REVIEW on codex/integration; scoped planA implementation verified, not deployed/released.
User explicitly approved CMS metadata/editorial/category-description scope after API clarification.
Contract checkpoint af0e989 (OpenAPI0.4.0) preceded implementation; final generated types also document category409/422 responses.
Implementation/evidence commit: aad0c75.
Release#4 received by normal master merge; AI-APIv1.3 and active checkpoints unchanged.

## Delivered behavior

- Additive migration004 adds nullable videos.width/height/fps/hashtags and categories.description; fresh init schema matches.
  No historical backfill, product-row deletion, provenance change or replacement of media. Unknown source values remain null.
- CPU ingest reads encoded source width/height and average fps before224px resize, publishes them on video.preprocessed.
  Orchestrator validates/persists optional fields; old payloads remain valid and cannot clear known metadata.
- Admin/editor PUT /api/cms/videos/{id} stores required title/description/editorial hashtags atomically in Postgres.
  Rejects missing/null/unknown fields, blank/oversized title, oversized description, duplicate/invalid/oversized tags;
  limits255/10000/30x64 characters, bounded JSON body. Missing/deleted videos404; file/status/provenance remain unchanged.
- Editorial tags stay separate from Mongo AI proposals. NULL means no override; [] is an explicit empty override.
  CMS can adopt existing AI tags, edit/save/reload them and regenerate AI proposals without losing saved tags.
  Client detail prioritizes editorial tags; explicit[] hides them, NULL falls back to AI tags. No new AI request/endpoint.
- Existing category create/update/list APIs persist descriptions, invalidate category cache, retain name-only compatibility;
  omitted/null description preserves it and empty string clears. Name conflicts map409 and invalid values422.
- CMS maps real resolution/fps and editable title/description/tags; draft errors retain fields and stop later mutations.
  Metadata can save when analysis is unavailable. Metadata-only saves do not rewrite an unchanged AI summary/approval.
  Save/regenerate controls lock affected inputs while requests run. Existing subtitle/summary approval flow remains tested.
- Approved deferrals remain disabled/unknown: priority scheduling, custom AI rules/category approval workflow, logo proposals,
  undefined metrics and AI key rotation. Removed fabricated category approval/automatic-rule claims. Existing soft-hide retained.

## Verification (VERIFIED-NOW)

| Gate | Result |
|---|---|
| Backend `go vet ./...`, `go test ./...`, `go build ./...` | PASS; final output INT-21-go.log. Default unit run skips opt-in external-integration fixtures; real PG cases below ran explicitly. |
| Protected handler + validation tests | PASS: real signed JWT401/403/editor/admin paths, invalid JSON/fields/tags/limits, clear values, deleted404; category compatibility/cache/conflicts. |
| Real PostgreSQL | PASS: migration twice, nullable legacy values, source/editorial persistence, protected HTTP PUT→GET via Gin+real repositories, explicit clearing, sticky provenance, deleted guard, category description. Final extended HTTP case0.05s. |
| Existing real PG feed/catalog pages | PASS: feed snapshot/privacy/cold-tail and newest/trending category pages, no skips. |
| CPU ingest `python -m unittest -v test_preprocess` | 8PASS1.016s in existing own CPU image with read-only updated sources +real fixture;64x64/10fps silent fractional file and original file metadata verified, no checkpoint/model load. |
| CMS tsc +Vite production build | PASS; final index-B8Z5jrXZ.js / index-CCft9cBB.css. |
| CMS browser regression | 39PASS45.9s before final input-lock/copy/summary-write refinement. |
| CMS final targeted +existing transcript approval | 7PASS9.7s on final bundle; tests also cover adopt AI tags, reload, explicit clearing, unavailable analysis, failed writes and pending-regeneration input lock. |
| Client tsc +ESLint +Next build --webpack | PASS; buildID0jpAiC3YO74qVW4EcxQDJ. |
| Client production browser/helper suite | 71PASS1.2m, including6editorial-tag precedence/clear/fallback cases at390/1440 plus previous65auth/tracking/player/onboarding regressions. |
| Final CMS/Client/E2E tsc after response-type regeneration | PASS; request/runtime shapes unchanged by added error responses. |
| git diff --check | PASS |

Commands use direct Node CLIs because the local npx wrapper is broken. Go uses GOMAXPROCS1 and owned backend/.tmp.
Client/CMS browser suites intercept API responses with isolated typed UI fixtures: not new real-AI or whole-stack E2E acceptance.
The PG HTTP test uses real Postgres with temporary shadow tables and signed test JWT; no inference/storage request is needed for metadata.
Worker tests use the installed CPU image with networking disabled; no new dependency/image/checkpoint download.

The first host5432 attempt failed authentication; no credentials were printed and no DB mutation occurred.
An initial WSL launch also failed shell argument parsing before tests; both failed attempts are preserved separately.
Final PG tests ran inside the correct container over its Unix socket. Both ALTER targets were shadowed, so migration never touched public product tables.

## Design check — scoped approved additions

Screenshots: INT-21-screenshots/editorial-{390,1440}.png and category-description-{390,1440}.png.
Reference: existing INT-05-comparison/reference-subtitles-* and reference-categories-*; original Stitch files unchanged.
Images use UI fixtures and include honest missing-source/toast states. Scroll reset before full-page capture avoids displaced fixed-header artifacts.

| # | Check | Scope/result |
|---|---|---|
|1|Layout|Existing desktop3-column editor/category table+aside preserved. Editable hashtag field/category-description modal are user-approved functional additions.|
|2|Colors|Existing input/card/badge/button semantic CSS reused; no new palette.|
|3|Typography|Existing input/label/micro tokens reused. Global prior typography differences remain INT-05, not silently accepted.|
|4|Spacing/radius|Existing form controls used; narrow deferred-priority label shortened to Đã hoãn to fit mobile. Global spacing audit remains INT-05.|
|5|Icons|Existing Material SVG system unchanged; no new library.|
|6|Copy|Existing field labels retained; explicit adopt-AI-tags/action guidance and approved deferred labels added.|
|7|AI UI|Canonical edits separated from AI candidates; confidence/summary/subtitles/heatmap unaffected. No fake model/accuracy values.|
|8|States|Save/reload/clear/error/analysis-unavailable/pending-regeneration verified; errors preserve unsaved fields.|
|9|Responsive|390x844 and1440x900 tested, no horizontal body overflow in new cases; final images inspected.|
|10|Cuts|Priority/rules/undefined status/metrics/key rotation remain deferred; no logo/tracking/object/face features reintroduced.|

This completes scoped planA acceptance, not full INT-05/06 design parity. Older visual differences and Client library/forgot-link decisions remain separate.

## Changed files

- Contract/generated: infra/openapi.yaml; backend/internal/gen/api.gen.go/spec_test.go; CMS/Client src/api-types.ts.
- Storage/domain: infra/postgres/init/001_schema.sql +migrations/004_cms_metadata.sql; backend/internal/domain/entities.go;
  ports/repositories.go; adapters/pg/repositories.go/content_pages.go/metadata_test.go/content_pages_test.go; mocks/mem.go.
- API/worker: backend/cmd/gateway/main.go; internal/handlers/cms/metadata.go/metadata_test.go/categories.go/videos.go;
  internal/handlers/content.go; internal/orchestrator/runner.go/runner_test.go; ingest-worker/main.py/test_preprocess.py.
- UI/tests: cms/src/hooks/useCms.ts; pages/SubtitlesPage.tsx/CategoriesPage.tsx; client/src/app/videos/[id]/page.tsx;
  e2e/cms_design.spec.ts/client_design.spec.ts; owned plan02/03/database spec and coordination evidence/tracker/session.

## Runtime boundary / next action

QA servers3100/5174 were stopped after exact PID/command checks. Owned PG test artifacts removed from container /tmp;
temporary DB tables disappear with test connections. Existing gateway/CMS5173/Client3000/worker/AI services were not replaced.
No application migration applied to the live product DB, no model/checkpoint edit, no master/shared-status publication or push.

For a later approved deployment: apply migration004 **before** binaries that select the new columns, then deploy gateway/orchestrator/CPUworker,
CMS and Client builds. Existing videos stay unknown until source metadata is obtained; no automatic reprocessing/backfill is authorized here.
Next safe task: INT-05 remaining visual corrections. Release/deployment is a separate action; AI contract remains unchanged.

Lane: codex
Changed: approved CMS metadata/editorial/category stack +Client hashtag mapping +tests/docs
Verified: Go gates; realPG protected HTTP/migration/pages;8worker tests;CMS39+final7;Client71;FE/E2Etypes/build/lint
Contract touched: public0.4.0; AI-APIv1.3 consumed unchanged
Next safe task: INT-05 remaining visual corrections
