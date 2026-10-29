# INT-36 — Discovery frames bounded to layout

Owner CODEX. IN_PROGRESS. Startup **22dcc32**; source checkpoint follows. User screenshot of Client /discover shows giant real thumbnail frames overlapping subsequent content. Skill client_screen + UI/UX Pro Max + Ponytail. Read original desktop/mobile discovery HTML, plan04 §8 and CẮT-list, coordination/owned trackers/Claude handoff. No master delta; no AI or API changes.

Root cause: desktop grid height was520px, but implicit auto minimum track sizing used loaded image intrinsic dimensions. Square images pushed child frames to **914.6875px**, portrait to **2696.0625px** while the grid remained520px. Following sections therefore overlapped. Placeholder/landscape fixtures had hidden the failure.

Small fix in client/src/app/globals.css, only desktop discovery selectors: bounded minmax(0,...) columns/rows, min-width/min-height0 for main/side/side links and two bounded side rows. Existing520px/gap24px, typography, colors, images, overlays, responsive mobile ratios and all API mappings retained. No global thumbnail/component change.

Verification before deployment:
- New e2e/client_design.spec.ts loaded square224×224/portrait300×900/landscape1600×400 image cases at390×844,1440×900,1903×900. Initial production3000: **4FAIL/5PASS14.7s**, reproducing square/portrait desktop overflow. Before log/metrics retained, not counted as success.
- Fixed productionQA3100: **9layoutPASS +2originalStitch reference captures PASS**, total11PASS14.1s. Actual desktop main520px and side248px for every image shape; mobile main201.375px(16:9)/side173px(square), body no overflow, following section below all cards. Screenshots inspected.
- `node node_modules/next/dist/bin/next build --webpack` (GATEWAY_INTERNAL_URL=http://gateway:8000), Client tsc noEmit, eslint src, E2E tsc PASS, no new dependencies/downloads.
- `node node_modules/@playwright/test/cli.js test e2e/client_design.spec.ts e2e/client_player.spec.ts e2e/compilation_timeline.spec.ts --grep-invert 'INT-36' --reporter=list`: **72PASS1.2m** on QA3100. Existing links/filter/loading/empty/error/player/compilation behavior retained.
- Exact approved QA command: `node node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3100`, ownPID8704. Stop after verification, never touch Client3000 host listener/AI.

Pending: offline Client image/deployment, actual real-API loaded-image browser acceptance3sizes, final runtime/data preservation and QA stop audit. Global INT-06 remains PARTIAL; this task covers the discovery sizing regression only.
