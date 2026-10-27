# INT-06 — Client Stitch parity checkpoint (2026-10-27)

Owner CODEX. User approved Client→CMS parity work within current API, followed by release preparation tests; no master/push authorization.
Project skill client_screen.md, required ui_design_review10items; UI/UX Pro Max targeted overflow/accessibility guidance +Ponytail full.
Public0.3.2/AIv1.3 unchanged; real gateway/AI/Client3000 unchanged in this checkpoint.

## References and deterministic capture
- Eight groups: login, register/ng_k, onboarding, short feed, discovery, multimodal search, personal library, animated video detail.
  Each mobile390x844/desktop1440x900: original HTML read only, original Tailwind CDN runtime cached418973bytes;82/83 public reference images fetched,
  ng_k desktop's unavailable background uses the previously exported studio.png. No reference file was edited.
- e2e/stitch_reference.spec.ts captures exact HTML/styles/geometry and asserts images load. Final16captures PASS36.8s; initial3font assertions
  failed because some original exports omit body font/config; corrected harness tests generated CSS instead. Failed attempt preserved, not countedPASS.
- Baseline existing Client16layouts PASS17.5s. Paired images/metrics in INT-06-comparison/index.json; labels distinguish before/dev iteration.
  Reference personal_library_mobile omits its Tailwind token configuration; raw rendered black/default-font header is an export gap, not a justified
  instruction to replace the app's semantic brand tokens. Full parity for that reference needs resolution, not an invented acceptance.
- Dynamic videos/categories/times differ legitimately under checklist§4; source images are references, not product media/AI results.

## Implemented, existing API only
- Mobile login input boxes now exactly reference x16/y288,380/w358/h56 (paragraph line20); existing reference glow retained exactly.
- Mobile register fields exactly x16/y324,426,528,630/w358/h58, submit60px, spacing/type tracking; desktop fields remain50px.
- Onboarding packs API categories before wide cards so there are no internal holes. DOM/visual/keyboard order remain together; original query data
  and category IDs are unchanged. Exhaustive511small/wide permutations verified. Card backgrounds/states map exact mobile#fff8f5/#ede0ff,
  desktop#fff/#f5f3ff and original active/hover effects.
- Shared desktop header now groups brand/nav as reference; per-screen search widths512/480/512px, heights44/44/40px, font16/24, exact placeholders;
  detail uses32px/14px text, no active navigation underline/image action. Feed add_a_photo SVG is Google's original Apache-licensed Material icon,
  same existing icon system; no icon library/dependency added.
- Text-search desktop similarity slider can be prepared before image upload; no AI call until file+visual tab. Upload synchronizes selected threshold
  immediately, then existing debounced slider behavior continues. No API/schema change.
- Removed the extra auto-highlight row outside the mobile player because animated mobile Stitch has no such row. Existing desktop toggle, playerStore,
  range/seek logic and feed controls retained. Happy-path original-source fixture verifies no fallback notice and metadata16px after player;
  unavailable-source notice remains an honest error state.
- Next16 dev auto-generated client/AGENTS.md; verified generate-agent-files.js and read bundled CSS/Tailwind3 docs. No framework/dependency migration.

## Verification / current gate
- Targeted first5checks PASS13.4s; extended run7PASS/1harness failure (incorrect button locator for role=tab, task-owned waiting worker stopped,
  locator corrected). Current source full dev regression62PASS/1FAIL3.3m: tracking emitted watch_time0 at effect cleanup before expected session end.
  Tracking source unchanged; dev/StrictMode/HMR behavior must be distinguished on production without weakening assertions.
- E2Etypes and Client tsc PASS. ESLint from root exited0 with a root-dir warning; proper client-directory lint PASS before production build.
- Final source production next build/tsc PASS,13prerendered pages,1dynamic route. No full63production PASS yet.
- Automatic approval review rejected the combined production QA startup step at127.0.0.1:3100, reason "blocked by policy".
  Build-only command then PASS. Did not retry startup through another route/port or replace the live Client to bypass that rejection.
  Exact start command and stop-after-test plan submitted to user through async question; approval pending.
- Owned Next dev server3100 stopped; current gateway realAI/Client3000 untouched. No inference/AI/checkpoint, DB or other service change.

## Ten-item review — NOT full parity approval

Each row covers both required viewports. M=measured match for listed scope, G=remaining gap, P=production verification pending.
Paired evidence and per-element values are in INT-06-comparison/*.json; no blanket PASS inferred from screenshot test success.

| # | Block | Stitch → current implementation | Result / remaining work |
|---|---|---|---|
|1|Layout|All8groups have corresponding sections; register mobile input positions match, onboarding holes removed, header group corrected|M scoped; desktop register vertical offsets still differ; library API/old-row states remain|
|2|Colors|Canonical surface#fff8f5/primary#630ed4; onboarding explicit mobile/desktop selected backgrounds corrected|Source match; final card-color runtime P; mobile library export tokens missing|
|3|Typography|Inter; mobile login14/20, register inputs16/24/58px; desktop header16/24 vs previous14/21|M scoped; exact remaining per-screen metrics P|
|4|Spacing/radius|Register y324/426/528/630; nav widths512/480/512; original player metadata16px; existing radii preserved|M scoped; desktop register first input still10px lower in prior capture|
|5|Icons|Existing Google Material SVG system; feed add_a_photo now same source name; no fallback icon in layout checks|M scoped; all8full icon inventories P|
|6|Vietnamese copy|Per-screen nav placeholders corrected; dynamic titles/categories honest; D18 popularity overrides reference personalized copy|M scoped; forgot link user decision pending|
|7|AI components|Existing heatmap0–100, real API mapping, draft privacy preserved; desktop auto toggle exercised; no extra mobile auto row|Targeted happy-path checks PASS; production regression P|
|8|States|Auth/refresh/loading/error/empty/player/visual/tracking cases included; reference hover/selected cards preserved|Dev62PASS/1trackingFAIL; full production63 P, never markedPASS|
|9|Responsive|390/1440 baseline and fixture layout checks, explicit card bounds+keyboard order tests|Targeted PASS; current production screenshots P|
|10|CẮT/scope|No translation/comment/follow added; library/count actions unavailable without contract; forgot/reset code deferred unchanged|G: library decision, metrics/playlist/notifications, forgot link and malformed library export unresolved|

Screen-specific remaining items:
- Login: desktop fields prior y321/423 vs reference322.5/424.5; checkbox18 vs20; forgot link under INT-10 decision. Mobile fields measured exact.
- Register: mobile measured exact. Desktop first field prior274 vs264, row cadence98 vs102; fix/verify before full parity claim.
- Onboarding: current source grid/order/colors corrected; final production selected/hover captures pending.
- Feed: new header dimensions/copy/icon corrected; last dev x586.94 vs reference577.98 needs final font/group spacing verification.
  View/like/save counts have no source; no fabricated figures. Following/comment/translation intentionally cut.
- Discovery: mobile search controls still differ (reference inner input vs current whole input); compare wrapper geometry before correction.
  Desktop hero/cards are dynamic data, not fake static counts; D18 popularity override applies.
- Search: active similarity control now matches reference and remains request-gated. Final per-screen header/grid typography pending production.
- Library: raw mobile export token/config missing; saved/unlike/delete/history/playlist/metrics scope remains undecided. No new endpoints added.
- Detail: original-source happy path checked separately from old clip-fallback fixture; extra mobile auto row removed; desktop functionality intact.
  User/view counts unavailable; fallback notice is an allowed error state, not reference happy-path geometry.

## Pending decisions (async questions already sent)
1. Approve concrete4library routes in CONTRACT_DECISIONS.md or accept current MVP-disabled actions. AGENTS§8 prohibits unapproved endpoints.
2. Change only login forgot link to "Liên hệ quản trị viên" while retaining deferred routes, or preserve link as explicit parity exception.
3. Approve exact production QA3100 startup rejected by automatic review. No elapsed time interpreted as approval.

Status remains IN_PROGRESS/PARTIAL; no full Design Parity/production/deployment/release PASS claimed.

Lane: codex
Changed: Client forms/header/onboarding/search/detail scoped fixes; generated scoped Next guide; reference/fixture tests and comparison evidence
Verified:16reference captures/images,16baseline layouts,5targeted,dev62/63 (one failure),types/lint/final production build
Contract touched: no (public0.3.2/AIv1.3 unchanged)
Next safe task: production QA after explicit approval; continue independent remaining UI/CMS work meanwhile
