# INT-05 — CMS player parity checkpoint, 2026-10-27

Owner: CODEX. Overall task remains IN_PROGRESS; this checkpoint does not certify full CMS parity.
Dependencies: INT-02/INT-04 functional source playback available. Full parity still needs the scope decisions in
`../CONTRACT_DECISIONS.md` and remaining per-screen corrections. No new endpoint, response field or AI behavior was added.

## Implemented

- Highlight proposals enable **Xem trước** when the existing `VideoDetail.playback_url` is available.
  Preview seeks to the proposal start, plays and pauses at the end without changing the editable clip range.
  Manual timeline seeking cancels the preview boundary. Invalid/nonfinite preview bounds are ignored.
- Shared original-video player exposes the existing review controls through real media events: play/pause,
  keyboard Enter/Space, load/play error messages. Highlight and subtitle buttons use measured Stitch dimensions:
  64/48px, 12px radius, white20%/primary90%, filled Material play icon, source hover/active scale.
  Although the source class says rounded-full, its rendered theme resolves to **12px**, which is the value used here.
- Published clip modal keeps native browser controls. Original-source absence retains its explicit empty state.
- All source/contract changes are confined to Codex-owned CMS/E2E files; no model, inference or shared document edits.

Changed files: `cms/src/components/player/VideoPlayer.tsx`, `cms/src/components/common/Icon.tsx`,
`cms/src/pages/HighlightPage.tsx`, `cms/src/pages/SubtitlesPage.tsx`, `cms/src/lib/time.ts`, `cms/src/styles/global.css`,
`e2e/cms_design.spec.ts`, `e2e/cms_stitch_reference.spec.ts`, owned verification/tracker/session files.
Commit: `f601958` original preview; follow-up `int(cms): align review timeline and proposal spacing` in git history.

Follow-up: highlight player/proposal times now use HH:MM:SS, including durations over1h; existing minute-only callers
keep their format. Player timeline uses12px/16px text,16px padding,4px track and white30% background. Subtitle player
has its4px progress track/12px thumb bound to actual media time and4px outer radius. Proposal header57px, compact
actions/32px remove icon, pill badges and selected-time styling now follow the source. No additional API dependency.

## Verification

| Command (direct Node CLIs; npx wrapper is broken locally) | Result |
|---|---|
| CMS `node node_modules/typescript/bin/tsc --noEmit` and `node node_modules/vite/bin/vite.js build` | PASS, final bundle index-DOmBeB3S.js / index-CCft9cBB.css |
| Root `node node_modules/typescript/bin/tsc -p e2e/tsconfig.json --noEmit` | PASS |
| Baseline `cms_design.spec.ts --grep 'T3.1 (390\|1440) .* layout'` on existing CMS5173 | 18 PASS, 24.5s |
| `E2E_CMS_URL=http://127.0.0.1:5174` Playwright `cms_design.spec.ts cms_stitch_reference.spec.ts --output=backend/.tmp/int05-final --reporter=list` | 37 PASS, 38.7s (before final radius correction) |
| Same QA URL, `cms_design.spec.ts --grep INT-05 --output=backend/.tmp/int05-controls-final --reporter=list` | 3 PASS, 10.3s after final radius correction; also verifies manual seek cancels preview and published modal retains native controls |
| Same QA URL, `cms_design.spec.ts --grep 'INT-05\|highlight layout' --output=backend/.tmp/int05-spacing-final --reporter=list` | 5 PASS, 11.7s after time/progress/proposal follow-up; asserts90min format,57px header, media progress at50%, native modal and error state |
| Existing CMS5173, `cms_stitch_reference.spec.ts --output=backend/.tmp/int05-all-references --reporter=list` | 16 reference captures PASS57.0s for all8Stitch screens, both viewports; original image requests succeeded |
| `git diff --check` | PASS |
| Read-only gateway `/healthz` and Claude `/health` | gateway ok; stub_mode=false, 6 models, degraded=[], CPU |

Initial combined run had 33 application cases PASS and 4 reference captures FAIL: original Stitch HTML redirected to
its login page because the capture omitted its `currentUser` localStorage state. Only the reference harness was fixed;
the subsequent four captures and full37 run passed. Test fixture response types were corrected to generated `VideoDetail`;
no handwritten API types. Fixture tests are **UI evidence**, not real AI/E2E acceptance or AI quality evidence.

QA used the production Vite bundle at127.0.0.1:5174. Owned PID22248, then follow-up PID1636, were checked and stopped afterwards.
CMS5173 and real gateway/AI runtime were not replaced. Client production QA3100 remains pending its separate startup approval.

## Design Parity Check — scoped player checkpoint

References are original, unchanged HTML in `stitch_ai_video_cms/ph_duy_t_c_t_highlight_ai` and `ph_t_m_t_t_ai`.
Paired screenshots: [comparison directory](INT-05-comparison/README.md), both390x844 and1440x900.

| # | Item | Stitch / current / result |
|---|---|---|
| 1 | Layout | Highlight two columns / subtitle three columns retained on desktop. Center controls now exist over real video. Full CMS review still open. |
| 2 | Colors | Scoped button backgrounds white20% and #46159990%, white glyph match rendered reference. Dynamic video frames excluded. |
| 3 | Typography | Inherited local Inter/mono preserved; scoped player time12px/16px and HH:MM:SS restored. Other per-screen typography is not certified. |
| 4 | Spacing/radius | Center buttons64/48px and12px radius; subtitle4px track/12px thumb; proposal header57px/32px remove action restored and asserted. Full-page spacing review still open. |
| 5 | Icons | play_arrow filled / pause Material SVG through existing icon system; no new icon library. |
| 6 | Vietnamese copy | Existing Xem trước and missing-source message retained; actual playback errors exposed. Full copy review still open. |
| 7 | AI UI | Preview uses returned proposal times, no fabricated score/model results. Heatmap/store and editable range remain independent of preview. |
| 8 | States | Play/pause, keyboard, bounded stop, manual seek, unavailable-source error, missing-source baseline and native modal tested. |
| 9 | Responsive | Buttons and interactions tested at390x844/1440x900; baseline18 and regression18 shell layouts retain no horizontal body overflow. CMS has no separate mobile source exports; raw reference is fixed desktop geometry at390. |
| 10 | Cut elements | Object detection/tracking/character recognition/H100/Vision-X remain absent in app. Raw reference screenshots retain the original cut content solely for comparison. |

Remaining: actual width/height/fps; analytics/editor/category rule definitions; full-page ten-item comparisons beyond
these scoped player/proposal fixes. These are not marked DONE or silently accepted.
No CMS deployment/master release/push performed. Next safe task: continue INT-05 existing-API visual corrections;
INT-06 production regression requires the pending startup decision; new fields/routes require separate contract approval/task.

Lane: codex
Changed: CMS player/callers/styles/icons, E2E, owned verification/session/tracker
Verified: CMS tsc/build; E2E tsc; 37 browser cases +3 player checks +5 follow-up checks; gateway/AI health
Contract touched: no (OpenAPI0.3.2 and AI-APIv1.3 consumed unchanged)
Next safe task: INT-05 existing-API visual corrections

## Remaining screen comparison audit

All eight original HTML exports were captured at both required sizes. Desktop images were compared block by block;
reference and baseline screenshots for all screens are preserved in the comparison directory. A successful capture
does not mean the app matches it. The six unchanged screens use baseline images, not a fictitious new deployment.

| Screen | Concrete remaining differences using existing fields | Contract-dependent differences |
|---|---|---|
| Dashboard | Stat/card and chart heights; heading/action/table font weights; avatar/toolbar and sidebar spacing | Accuracy, online users, storage usage and historical model-update/log data have no defined source. Current job-derived chart is labelled; it is not a complete analytics API. |
| Upload/queue | Upload copy size/wrapping, table/header density, stage legend appearance, toolbar spacing | CPU metric, uploader and elapsed stage timings unavailable. GPU/VRAM/queue use existing health values; H100/80GB remains cut. |
| Videos | Filter/date row heights, table/action density, sidebar divider and header button sizing | Filename/MIME/size/uploader fields missing; filters currently operate partly on the loaded page. Do not claim whole-dataset filtering. |
| Highlight | Scoped player/proposal fixes above verified; other header/heatmap typography and selection geometry still open | Logo proposal/insertion lacks an AI behavior contract; do not invent it. |
| Subtitles/summary | Scoped controls/progress verified; remaining transcript/header/editor spacing and typography still open | Width/height/fps and title/description/priority/hashtag persistence need contract decisions. Low-confidence warnings use real schema fields. |
| Categories | Table column wrapping, panel heading/row fonts and sidebar spacing | Description/status/custom rules absent. No fabricated system category, rule result or character-recognition control. |
| Published library | Tab font/spacing, table/status/action sizing and toolbar proportions | Views/editor/render/storage metrics undefined; distinct hide/delete semantics require scope. Existing soft-hide and native preview remain functional. |
| Settings | Tabs and secondary field spacing, sidebar divider, a few text/button dimensions | AI key remains masked/read-only; runtime rotation is a separate AI coordination operation. MinIO/vi-only/copy substitutions are approved cuts. |

Ten-item status across these screens: layout/colors/typography/spacing/icons/copy remain **OPEN** beyond the scoped
player fixes; AI content is **BLOCKED** where no field/behavior exists; states/responsive have passing fixture coverage
but are not exhaustive visual/state certification; cut-list checks pass the exercised layouts. Login/Users use plan
wireframes rather than one of these eight exports. No unreviewed category is represented as a full PASS.

Next safe work remains scoped existing-API visual fixes; full acceptance additionally requires the pending contract
scope decision. No new endpoint, model edit or release is inferred from this audit.
