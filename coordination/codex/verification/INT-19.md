# INT-19 — public pagination contract clarification (2026-10-27)

Owner CODEX; project skill backend_endpoint.md. Existing routes:
- GET /api/feed?cursor&limit → FeedPage {items,next_cursor,recommendation_mode}.
- GET /api/videos?category_id&sort=trending|newest&cursor&limit → {items,next_cursor}.

OpenAPI0.3.2 adds documentation and existing ValidationError422 responses only; no new endpoint/request/response field or AI contract change.
Primary popularity/catalog cursors are opaque and route/filter-bound. A first-page creation cutoff and seven-day ranking window stay fixed across pages;
current visibility is still checked, exhaustion returns null. Invalid cursor/sort/limit returns the existing error envelope422.
Internal ranking cursor implementation follows in INT-14; this contract checkpoint does not claim live pagination yet.

Verification:
- Cached openapi-typescript7.13.0 parses schema and regenerates CMS/Client types: PASS.
- node cms/node_modules/typescript/bin/tsc --noEmit -p cms/tsconfig.json: PASS.
- node client/node_modules/typescript/bin/tsc --noEmit -p client/tsconfig.json: PASS.
- Cached oapi-codegenv2.8.0 regeneration PASS; Go gen package compiles, embedded GetSpec validates OpenAPI0.3.2 and both422 responses PASS. First versioned go-run with GOPROXYoff could not resolve deprecation metadata;
  running the exact cached v2.8.0 module directly avoids dependency/version changes and network lookup.

No runtime recreation/restart or AI request in this task; current gateway remains on real AI. Full UI parity belongs INT-05/06.

Generator config output is relative by default; temporary config used an absolute owned output. An initial generated cache artifact was removed after correcting the output path; final repo embedded spec explicitly validated.
Lane: codex
Changed: OpenAPI0.3.2 +3generated types +owned tracking
Verified: bothTS typechecks, generated Go package, embedded schema/version/422 assertions PASS; diffcheck PASS
Contract touched: yes (public0.3.2; AIv1.3 unchanged)
Next safe task: INT-14 pagination implementation
