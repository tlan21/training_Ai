# INT-36 — Discovery frames bounded to layout

Owner CODEX. **DONE (scoped discovery sizing bug)**. Startup **22dcc32**; source **c4de07e**. User screenshot of Client /discover shows giant real thumbnail frames overlapping subsequent content. Skill client_screen + UI/UX Pro Max + Ponytail. Read original desktop/mobile discovery HTML, plan04 §8 and CẮT-list, coordination/owned trackers/Claude handoff. No master delta; no AI or API changes. Targeted UI/UX search returned verified Responsive/Image Scaling guidance; existing Stitch geometry remains the design authority.

Root cause: desktop grid height was520px, but implicit auto minimum track sizing used loaded image intrinsic dimensions. Square images pushed child frames to **914.6875px**, portrait to **2696.0625px** while the grid remained520px. Following sections therefore overlapped. Placeholder/landscape fixtures had hidden the failure.

Small fix in client/src/app/globals.css, only desktop discovery selectors: bounded minmax(0,...) columns/rows, min-width/min-height0 for main/side/side links and two bounded side rows. Existing520px/gap24px, typography, colors, images, overlays, responsive mobile ratios and all API mappings retained. No global thumbnail/component change.

Verification before deployment:
- New e2e/client_design.spec.ts loaded square224×224/portrait300×900/landscape1600×400 image cases at390×844,1440×900,1903×900. Initial production3000: **4FAIL/5PASS14.7s**, reproducing square/portrait desktop overflow. Before log/metrics retained, not counted as success.
- Fixed productionQA3100: **9layoutPASS +2originalStitch reference captures PASS**, total11PASS14.1s. Actual desktop main520px and side248px for every image shape; mobile main201.375px(16:9)/side173px(square), body no overflow, following section below all cards. Screenshots inspected.
- `node node_modules/next/dist/bin/next build --webpack` (GATEWAY_INTERNAL_URL=http://gateway:8000), Client tsc noEmit, eslint src, E2E tsc PASS, no new dependencies/downloads.
- `node node_modules/@playwright/test/cli.js test e2e/client_design.spec.ts e2e/client_player.spec.ts e2e/compilation_timeline.spec.ts --grep-invert 'INT-36' --reporter=list`: **72PASS1.2m** on QA3100. Existing links/filter/loading/empty/error/player/compilation behavior retained.
- Exact approved QA command: `node node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3100`, ownPID8704. Stop after verification, never touch Client3000 host listener/AI.

## Deployment and actual UI acceptance

- Offline overlay on cached `video-ai-client:int35-8918060`; `docker-buildx build --network=none --pull=false --load ...` produced **video-ai-client:int36-c4de07e**, manifest **sha256:fa34fd3c8168e2e9788254aaefff2556c037a194dd45f8905c430acefa21f8f6**. No downloads. First attempt aborted on unexpected WSL metadata before image/deployment; validated daemon PID/image identity and retried same CLI successfully. No alternative port/launcher/service or AI runtime change.
- Existing WSL Docker Desktop compose command: `docker-compose -p video-ai --project-directory /mnt/host/e/traning_ai-codex -f /mnt/host/e/traning_ai-codex/docker-compose.yml -f /mnt/host/e/traning_ai-codex/docker-compose.inference.yml up -d --no-deps --no-build --pull never --force-recreate client`.
- Only Client recreated, latest alias updated and rollback-int36 retained. BUILD_ID **a9opFtacvy3Uyx55aFH6d** matches host artifact. Existing Dockerfiles/Compose topology/configuration reused. Required interpolation values stayed in memory; no secrets logged/committed or model mounts changed.
- `node node_modules/@playwright/test/cli.js test e2e/discovery_live.spec.ts --output=backend/.tmp/int36-live --reporter=list`: **3 PASS15.0s** on actual Client3000/API/MinIO at390×844/1440×900/1903×900, no route mocks. Existing admin login only, no account/media/clip creation or publish.
- Natural JPEGs decoded, desktop main520px/side248px fit grid, next section below frame bounds, body no horizontal overflow. Video link still targets original video detail. Actual screenshots inspected in INT-36-screens, including user's wide desktop case. Mobile real history/feed state preserved.

## Scoped Design Parity Check

Original discovery mobile/desktop HTML rendered fresh with cached Tailwind/reference assets (2PASS), screenshots inspected side-by-side with fixed layouts at390×844/1440×900. Full-page global INT-06 parity is not promoted; this verifies the sizing correction and retained UI.

|#|Item|Reference / fixed result|
|---|---|---|
|1|Layout|Desktop main +2 stacked side cards inside520px grid; following sections no longer overlap. Mobile existing section order retained.|
|2|Color|No color/token changes; background/gradient/badges unchanged.|
|3|Typography|No font, size, weight or line-height changes.|
|4|Spacing/radius|24px gap and existing card radii/padding unchanged; explicit bounded tracks restore intended geometry.|
|5|Icons|No icon changes/additions.|
|6|Vietnamese copy|Unchanged. Existing recommendation-mode wording follows approved D18 behavior, no fake personalization.|
|7|AI components|Existing real-score heatmap/badges preserved, no new AI claim/score.|
|8|States|Loaded square/portrait/landscape9cases; existing loading/empty/error/filter regression suite passed. No JS/conditional rendering change.|
|9|Responsive|390 main201.375px16:9/side173pxsquare unchanged;1440/1903 main520px/side248px. Body fits viewport, image never expands frame.|
|10|CẮT-list|No translation/social/follow/comment/creator features added; original mappings retained.|

## Preservation

- Other **15** containers retain IDs/images/start times/status/sorted mounts. Gateway/CMS unchanged, all apps healthy. Host Claude AI **PID27064** unchanged for this task; Docker real6/stubfalse/degradedempty, no AI code/model/checkpoint/runtime edits.
- Original **106 videos** hash **41e538d83f6b7f6d73faa03ae214c62e**, **58 clips** hash **9186844a706846cea3a6c3b8a17a6a67** unchanged; active pending/running jobs0. No source-media writes.
- Exact ownQA **PID8704** verified against approved command, stopped;3100closed. Client3000 remains running. No master/shared-status edits or push.
- No backend/AI E2E rerun because only scoped Client CSS changed; actual API/MinIO read/browser checks passed. No image-resolution/model-quality/GPU/load/soak claims. Global INT-06 remains PARTIAL.

Lane: codex
Changed: scoped discovery grid CSS, loaded-image regression and real browser test, owned coordination/evidence
Verified: build/types/lint/E2Etypes;11fixed/reference +72regression +3real browser PASS; build artifact identity/runtime/data/QA-stop checks
Contract touched: no (public0.5.0 / AI contract unchanged)
Next safe task: remaining assigned INT-05/06 scope; screenshot sizing bug complete.
