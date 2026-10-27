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
`cms/src/pages/HighlightPage.tsx`, `cms/src/pages/SubtitlesPage.tsx`, `cms/src/styles/global.css`,
`e2e/cms_design.spec.ts`, `e2e/cms_stitch_reference.spec.ts`, owned verification/tracker/session files.
Commit: see INT-05 task checkpoint entry / git history `int(cms): enable bounded original-video preview`.

## Verification

| Command (direct Node CLIs; npx wrapper is broken locally) | Result |
|---|---|
| CMS `node node_modules/typescript/bin/tsc --noEmit` and `node node_modules/vite/bin/vite.js build` | PASS, final bundle index-0zIpT5Ez.js / index-CoE8D0fz.css |
| Root `node node_modules/typescript/bin/tsc -p e2e/tsconfig.json --noEmit` | PASS |
| Baseline `cms_design.spec.ts --grep 'T3.1 (390\|1440) .* layout'` on existing CMS5173 | 18 PASS, 24.5s |
| `E2E_CMS_URL=http://127.0.0.1:5174` Playwright `cms_design.spec.ts cms_stitch_reference.spec.ts --output=backend/.tmp/int05-final --reporter=list` | 37 PASS, 38.7s (before final radius correction) |
| Same QA URL, `cms_design.spec.ts --grep INT-05 --output=backend/.tmp/int05-controls-final --reporter=list` | 3 PASS, 10.3s after final radius correction; also verifies manual seek cancels preview and published modal retains native controls |
| `git diff --check` | PASS |
| Read-only gateway `/healthz` and Claude `/health` | gateway ok; stub_mode=false, 6 models, degraded=[], CPU |

Initial combined run had 33 application cases PASS and 4 reference captures FAIL: original Stitch HTML redirected to
its login page because the capture omitted its `currentUser` localStorage state. Only the reference harness was fixed;
the subsequent four captures and full37 run passed. Test fixture response types were corrected to generated `VideoDetail`;
no handwritten API types. Fixture tests are **UI evidence**, not real AI/E2E acceptance or AI quality evidence.

QA used the production Vite bundle at127.0.0.1:5174. Owned PID22248 was checked and stopped afterwards.
CMS5173 and real gateway/AI runtime were not replaced. Client production QA3100 remains pending its separate startup approval.

## Design Parity Check — scoped player checkpoint

References are original, unchanged HTML in `stitch_ai_video_cms/ph_duy_t_c_t_highlight_ai` and `ph_t_m_t_t_ai`.
Paired screenshots: [comparison directory](INT-05-comparison/README.md), both390x844 and1440x900.

| # | Item | Stitch / current / result |
|---|---|---|
| 1 | Layout | Highlight two columns / subtitle three columns retained on desktop. Center controls now exist over real video. Full CMS review still open. |
| 2 | Colors | Scoped button backgrounds white20% and #46159990%, white glyph match rendered reference. Dynamic video frames excluded. |
| 3 | Typography | Inherited local Inter/mono preserved. Remaining player time format/font and other per-screen differences are not certified. |
| 4 | Spacing/radius | Center buttons64/48px and12px radius asserted at both viewports. Proposal/header spacing and subtitle scrubber still need correction. |
| 5 | Icons | play_arrow filled / pause Material SVG through existing icon system; no new icon library. |
| 6 | Vietnamese copy | Existing Xem trước and missing-source message retained; actual playback errors exposed. Full copy review still open. |
| 7 | AI UI | Preview uses returned proposal times, no fabricated score/model results. Heatmap/store and editable range remain independent of preview. |
| 8 | States | Play/pause, keyboard, bounded stop, manual seek, unavailable-source error, missing-source baseline and native modal tested. |
| 9 | Responsive | Buttons and interactions tested at390x844/1440x900; baseline18 and regression18 shell layouts retain no horizontal body overflow. CMS has no separate mobile source exports; raw reference is fixed desktop geometry at390. |
| 10 | Cut elements | Object detection/tracking/character recognition/H100/Vision-X remain absent in app. Raw reference screenshots retain the original cut content solely for comparison. |

Remaining: actual width/height/fps; analytics/editor/category rule definitions; source time formatting and subtitle progress
scrubber; proposal/header spacing and full-page ten-item comparisons. These are not marked DONE or silently accepted.
No CMS deployment/master release/push performed. Next safe task: continue INT-05 existing-API visual corrections;
INT-06 production regression requires the pending startup decision; new fields/routes require separate contract approval/task.

Lane: codex
Changed: CMS player/callers/styles/icons, E2E, owned verification/session/tracker
Verified: CMS tsc/build; E2E tsc; 37 browser cases +3 final player checks; gateway/AI health
Contract touched: no (OpenAPI0.3.2 and AI-APIv1.3 consumed unchanged)
Next safe task: INT-05 existing-API visual corrections
