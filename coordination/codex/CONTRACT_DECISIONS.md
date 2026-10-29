# Public contract decisions needed for complete Stitch parity

2026-10-26, CODEX. Original proposal below; latest scoped decision2026-10-28 takes precedence.
AGENTS §8 prohibits endpoints outside master §2 without a scope decision. Existing code, Stitch and historical parity reports confirm these gaps.

## Approved2026-10-28 — CMS planA (INT-20 contract, INT-21 implementation)

User approved planA after clarification that this is the CMS/business API, not model APIs.
Authorized: source width/height/fps from CPU ingest; persist video title/description/editorial hashtags;
category description; preserve soft-hide. Add PUT /api/cms/videos/{id} for admin/editor metadata and extend existing category routes.
No AI request/schema/checkpoint changes. Original filename/uploader/statistics are not implicitly added.

Definitions: width/height are encoded source pixels before224px preprocessing; fps is average source frame rate;
unknown/unavailable values remain null. Editorial hashtags live in Postgres separately from Mongo AI proposals,
so later inference cannot overwrite saved edits. Explicit empty tags clear editorial tags; null response means no editorial override yet.
Video metadata save replaces title/description/hashtags together with validated required fields; it never rewrites file/status/AI outputs.
Category description is optional for old name-only callers; omitted/null preserves on update, empty string clears.

Defer this release: scheduling priority, custom category AI rules/status workflow, logo insertion/proposals,
undefined accuracy/online/render/storage/view metrics and AI key rotation. Hide/disable with clear copy; no fabricated values.
The four Client library routes below, playlists and forgot-link/INT-10 decisions remain UNAPPROVED: the latest planA was CMS-only.
Contract/types must be committed before implementation. Full historical Stitch acceptance is limited by these approved deferrals.

Implementation checkpoint: INT-20 contract af0e989, INT-21 source/tests REVIEW (verification/INT-21.md).
CMS metadata/category fields are no longer waiting for a scope decision; migration/live deployment remains separate.

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

## 2026-10-29 — User-authorized AI highlight compilation (INT-34/35)

User requested one combined video containing the notable situations from a source video, and explicitly instructed implementation.
OpenAPI 0.5.0 extends existing POST /api/cms/clips with optional auto_highlights=true; backend uses stored AI proposals, merges overlaps, orders chronologically and creates one draft MP4. Empty proposals return 422. Legacy explicit start/end requests are unchanged. Clip.source_segments preserves source intervals; compilation start/end describe output 0..total duration, allowing correct playback/subtitle mapping. Existing review/publish endpoints are reused, no automatic publishing or AI contract change. A CMS action/preview using existing components is authorized by this feature request; broader Stitch parity remains separate.
