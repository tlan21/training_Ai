# INT-14 — primary feed/catalog cursor pagination (2026-10-27)

Owner CODEX; project skill backend_endpoint.md +Ponytail full. Contract first: INT-19/213aaa9, public OpenAPI0.3.2.
GET /api/feed?cursor&limit → {items,next_cursor,recommendation_mode}; GET /api/videos?category_id&sort&cursor&limit → {items,next_cursor}.
No endpoint/field/library/schema/AI change. Existing Client infinite-query hooks already send cursor/read next_cursor; no UI source change planned.

## Implementation scope
- Primary/fallback feed uses bounded Postgres page queries, including zero-interaction cold clips after ranked clips. Multiple clips of one video
  continue across pages; no first-page video/clip truncation. Current published clips/processed nondeleted videos only.
- Newest catalog applies category before paging; trending keeps published-video eligibility and seven-day product counts, includes zero-score cold tail.
  No fixed100/1000 candidate scan limit or app-side full catalog load. Popularity aggregated once and joined in the SQL query.
- Keyset order: countDESC/created_atDESC/idDESC (newest count0). Cursor carries immutable first-page time/window +last tuple;
  new interactions/created rows do not shift an existing traversal; current visibility/title remain live. Deleting the seen anchor does not shift offsets.
- Cursor base64url JSON is a position, never an authorization token; every page still enforces DB visibility. Route/sort/category binding,
  size/ID/time/count validation and strict limit1..50; invalid query422 existing envelope. No public response fields changed.
- Optional personalized path remains production-disabled/single-page under INT-03/AI-12; not enabled by this task. Fallback pages use the same primary cursor.
  Full Stitch parity remains INT-06, separate from pagination behavior.

## Verification checkpoints
- New domain cursor validation/tuple ordering and handler feed/newest/trending traversal/error tests PASS with mocks.
- Final Go vet/test/build and Linux artifacts PASS, including the joined ranking query and missing-cursor-field rejection guard.
- Real PG initial query tests PASS without skips: feed24original clips, hidden/deleted3 excluded; fixed snapshot/new interactions/new clip/current title,
  seen-row deletion/cold tail; newest+trending6category rows/filter mismatch/exhaustion. Final joined-source rerun PASS0.12s feed/0.11s catalog, no skips.
  Tests use session-local TEMP shadow tables copied from live schema, no product rows/sequences touched; pool close drops them.
- First invocation mistakenly skipped because nested shell expansion lost DSN; preserved skipped-attempt.log, not counted PASS.
  First real fixture failed required duration_seconds; corrected fixture to real schema, preserved fixture-failure.log. No query PASS inferred from failures.
- E2E typecheck PASS. Actual live gate: content_pagination_live +existing video_flow/visual_search, **4PASS1.6m**, no retries/mockAI.
- Runtime: gateway-int14 deployed for live verification, SHA256 c5284c5c2fe00f5f2c20fe9faab0dfecb3fec1bfb62bc085ff5a1f0ab45c8d81.
  Local guarded script changes only gateway binary mount, compares all gateway env,
  preserves real URL/stub0/key; failure rolls back to previous verified real binary. No build/pull/other service/AI/checkpoint change.

## VERIFIED-NOW final live acceptance
```powershell
$env:E2E_GATEWAY_URL='http://127.0.0.1:8000'
$env:E2E_AI_URL='http://127.0.0.1:8001'
node node_modules/@playwright/test/cli.js test e2e/content_pagination_live.spec.ts e2e/video_flow.spec.ts e2e/visual_search.spec.ts --reporter=list
```
- 4PASS1.6m: pagination1.0m; video approve/publish/playback20.6s; invalid/private1.6s; real visual search/privacy/cache/Client12.9s.
- Three real8s uploads→AI processed→category→12FFmpeg clips/published; feed3pages(limit5), newest/trending2pages each(limit2), no duplicate IDs/exhaustionnull.
  Live Next16 same-origin proxy used for API checks; route/filter-mismatched cursor, malformedcursor/limit/sort422.
- Existing Client desktop infinite query fetched10→12unique clips by scroll using returned cursor; no Tải thêm after exhaustion.
  Screenshot INT-14-pagination-client.png inspected; no UI code/style/layout change and no full Stitch parity claim.
- Final gateway healthy/realAI6/stubfalse/popularity verified independently. All3 exact pagination videos softdeleted and12clips public404,
  test accounts/media retained; no existing media/volumes deleted. Original3regression fixtures cleaned by their guarded tests.
  Evidence INT-14-pagination-{live,runtime,cleanup}.json +real-e2e.log. No shared/Claude/model/checkpoint modification or image pull/build.
- Visual search regression20cold p95/max49.72/105.27ms,20warm11.16/11.32ms; not load/soak acceptance.
- `go vet -p 1 ./...`, `go test -p 1 ./...`, `go build -p 1 ./...` PASS; finalLinux PG test +gateway artifacts PASS.
  Actual PG fixture tests executed inside gateway with its existing DSN passed only in process env (never logged): feed0.12s/catalog0.11s, no skips.
  Compiler/unit runs without TEST_POSTGRES_DSN skipped integration as expected; only the explicit real run counts toward realPG acceptance.
  Schema/version/422 verification and generated FE checks are recorded in INT-19.md; no runtime FE source changed, no repeated full FE builds needed here.
- Known scope: fixed ranking/creation snapshot, live publication/deletion filtering. Publication/category changes to old rows remain live;
  no historical transaction snapshot guarantee. Personalized pagination remains disabled/pending INT-03/AI-12.

Pagination acceptance complete on source e476005 and local runtime. INT-14 overall remains PARTIAL because its full Client parity dependency INT-06 remains open;
do not interpret this as full app/release/AI quality readiness. No master/push performed.

Lane: codex
Changed: domain cursor/ports/PG/mocks/handlers/tests/liveE2E; public0.3.2 contract already accepted213aaa9; owned evidence/tracking
Verified: Go vet/test/build;3real PG scenarios/no skips;4real Playwright PASS1.6m;FE/E2Etypes/schema;finalrealhealth/cleanup
Contract touched: yes public0.3.2 (INT-19); AI-APIv1.3 unchanged
Next safe task: INT-06 existing API/Stitch parity scope
