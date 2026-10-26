# Public contract decisions needed for complete Stitch parity

2026-10-26, CODEX. Proposal only: no new endpoint below has been added to OpenAPI/master/source.
AGENTS §8 prohibits endpoints outside master §2 without a scope decision. Existing code, Stitch and historical parity reports confirm these gaps.

## Smallest useful extension (recommended)

| Proposed route | Behavior | Existing UI |
|---|---|---|
| GET /api/users/me/saved?cursor&limit | ClipPage from this user's save events; published/processed only, deduplicate like likes | Watch-later tab |
| DELETE /api/users/me/saved/{clip_id} | Remove own saves for clip; idempotent 204 | Remove from watch-later |
| DELETE /api/users/me/likes/{clip_id} | Remove own likes for clip; idempotent 204 | Unlike/remove liked item |
| DELETE /api/users/me/history?clip_id | Remove own click/watch_time records; optional clip_id selects one, absent clears own history, 204 | History item menu + Clear all |

These delete only the acting user's interaction records, never media or another user's data. Existing database tables suffice.
This changes recommendation history for the user; confirm delete intent in UI before clearing all history.
Contract and generated types must be committed in a separate task before implementation.

CMS field additions can use existing routes, but require concrete definitions: video width/height/fps from preprocessing;
title/description/priority/hashtags edit fields, category description/status/rules. Metrics such as accuracy/online users/render rate
must have a defined source and meaning; no invented values.

## Items to defer explicitly for the minimal release

- Personal playlists/folders (new schema + CRUD + permissions), notifications, advanced analytics without defined sources.
- Logo insertion/proposals and custom category AI rules without an inference contract/model behavior; do not pretend these are AI outputs.
- Runtime AI key rotation remains coordinated env configuration; persisting masked CMS settings is not rotating an AI process key.

Decision options:
1. Approve the four library routes + defined CMS metadata/edit fields; defer advanced items above. Proposed minimal extension.
2. Keep current MVP contract and explicitly cut/disable missing Stitch sections for this release.
3. Request full remaining Stitch scope; schedule a separate contract/metric/playlist design before implementation.

Until decision: INT-05/06 stay PARTIAL, missing API actions disabled; no new endpoint or arbitrary data.
