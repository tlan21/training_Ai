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
- E2E typecheck PASS. Planned live gate: content_pagination_live +existing video_flow/visual_search,4tests total, no mockAI.
- Runtime: gateway-int14 deployed for live verification, SHA256 c5284c5c2fe00f5f2c20fe9faab0dfecb3fec1bfb62bc085ff5a1f0ab45c8d81.
  Local guarded script changes only gateway binary mount, compares all gateway env,
  preserves real URL/stub0/key; failure rolls back to previous verified real binary. No build/pull/other service/AI/checkpoint change.

Status: IN_PROGRESS; no live pagination PASS yet.
