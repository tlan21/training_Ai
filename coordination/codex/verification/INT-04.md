# INT-04 — original video playback (2026-10-26)

Owner CODEX. Contract commit `8733f97`: OpenAPI v0.2.0, optional nullable `VideoDetail.playback_url`, TTL 1 hour;
existing public/CMS detail routes only. Go/CMS/Client types regenerated with oapi-codegen v2.8.0 / openapi-typescript 7.13.0.
Project implementation skill: backend_endpoint.md; required UI review checklist: ui_design_review.md.

## Scope and verification

- Public detail signs original media only after processed gate; CMS admin/editor detail signs non-deleted media. No raw_file_path exposed.
- CMS Highlight and Subtitle players use the signed original URL. Client defaults to original, supports full-timeline `?t=`/heatmap;
  explicit clip link continues using published clip offset/player logic. Existing fallback remains for absent original URL.
- A real mobile interaction found the player-bottom padding intercepting central Play clicks. Scoped pointer-events fix lets padding
  pass clicks while preserving buttons/inputs/details. No test force-click or event bypass.
- VERIFIED-NOW: full `GOMAXPROCS=2 go test -p 1 ./...` PASS; public status privacy and CMS deleted-source unit tests PASS.
- VERIFIED-NOW: CMS `npx tsc --noEmit; npm run build` PASS; Client `npx tsc --noEmit; npm run lint; npm run build` PASS,
  then Client build after pointer-event fix PASS. Build env CIRCLE_NODE_TOTAL=2/RAYON_NUM_THREADS=2 controls memory use, no repo config change.
- VERIFIED-NOW: `npm ci --no-audit --no-fund` root, 6 packages; `npm run test:e2e:types` PASS.
- VERIFIED-NOW: Linux gateway build PASS and current binary mounted :ro into cached runtime; CMS serves current dist :ro,
  Client current production build runs `npm run start -- --hostname 127.0.0.1 --port 3000` on host. Old Client container stopped.
- VERIFIED-NOW: `npx playwright test e2e/original_playback.spec.ts --reporter=list` **2 PASS (29.1 s)** at 390×844/1440×900:
  real MP4 upload/ingest/storage/HTTP mock pipeline, no published clips; detail presigned TTL=3600 and Range206/1024 bytes;
  viewer cannot use CMS detail (403); Client opens at 5 s, Play advances, heatmap seeks to 2 s; CMS Highlight/Subtitles play and seek to 3 s;
  no pageerror or horizontal overflow. Fixtures soft-deleted after each test; viewer/MinIO objects retained per E2E policy.
- Existing player logic tests: **2 PASS**, highlight threshold/gaps and clip offset/clamp.

Failed attempts retained as diagnostics, not PASS: first run overlapped gateway replacement (ECONNREFUSED);
second run desktop PASS/mobile timed out because real overlay intercepted Play. Fixed CSS; final both-viewports run PASS.
The timed-out test's uniquely named video was explicitly soft-deleted after identifying exact title, no unrelated data touched.

AI mode: **MOCK_ONLY**. This verifies playback/business plumbing, not AI model integration or quality.

## Design Parity Check (10 items)

Captured unmodified Stitch HTML through local static server, currentUser fixture only to bypass design demo redirect.
Actual screenshots come from real UI + mock-AI pipeline, both viewports. Images: `INT-04-design/` (stitch-* = reference).
Media, title, duration, empty clips/draft summary differ as dynamic data. Full-page parity remains PARTIAL; do not call UI 100% DONE.

| # | Item | Result |
|---|---|---|
| 1 | Layout | Original player occupies existing region; full-page gaps inherited. CMS native video controls differ from custom Stitch controls: PARTIAL, follow INT-05. |
| 2 | Colors | No token/color changes in this task; reference CMS primary #461599, Client #630ed4. Full-page/heatmap exact-color audit remains INT-05/06. |
| 3 | Typography | Existing local fonts/typographic CSS unchanged; data fixture title is deliberately labelled MOCK_ONLY. Full-page audit remains pending. |
| 4 | Spacing/radius | No spacing/radius changes; removed unavailable-source notice only when original URL exists. CMS control geometry remains PARTIAL. |
| 5 | Icons | Existing SVG system retained; native CMS controls are a known difference, not silently accepted. Client central Play click works after transparent padding fix. |
| 6 | Vietnamese copy | Player labels retained. Source-unavailable message appears only without source. View/like counts, metadata fields still need contract/scope decision. |
| 7 | AI components | Scores/timeline from explicit mock, approved summaries only; no detection/tracking overlay. Dynamic content does not certify AI quality. |
| 8 | States | Original source with no clips works; absent original keeps existing clip fallback; real Play/seek verified. Existing fixture suite covers other loading/error states. |
| 9 | Responsive | Real playback, click and seek PASS at both viewports, no body overflow. Full reference mapping remains INT-05/06. |
| 10 | Cut list | No AI translation/detection/face/social added; forgot-password deferred D1 unchanged. Unsupported library/analytics controls remain a scope gap. |

Functional acceptance PASS; overall task **PARTIAL** until required parity gaps close. No blanket parity approval.

## Checkpoint

Lane: codex
Changed: OpenAPI/generated types; public/CMS detail handlers/tests; CMS/Client source mapping; mobile pointer fix; E2E/screenshots
Verified: Go/CMS/Client build/checks, E2E types, original playback 2 PASS + player logic 2 PASS; parity reviewed with gaps
Contract touched: yes (public OpenAPI v0.2.0); AI contract unchanged
Next safe task: INT-11 host/Docker AI media boundary; INT-05/06 need parity + contract scope decision
