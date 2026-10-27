# INT-17 — Client framework security decision (2026-10-27)

Owner CODEX. Status REVIEW: approved migration/security/browser checks and two live gateway sessions PASS2026-10-27.
Initial audit/proposal below is historical evidence. No public deployment, force install, AI/API/DB change performed.

## Evidence
- Fresh Client image builds with pinned Next14.2.35; npm ci reports6 vulnerable packages overall.
- Readonly `cd client; npm audit --omit=dev --json`: Nextcritical +PostCSShigh (2runtime packages), raw INT-16-runtime-audit.json.
  npm proposes next16.4.3 with isSemVerMajor=true. Registry `npm view next@14 version --json` ends at14.2.35;
  latest15=15.5.28. Node22 image satisfies the reported Node>=20.9 requirement for16.4.3.
- Primary maintainer advisories checked2026-10-27:
  - [GHSA-p293-qw3h-jr36](https://github.com/vercel/next.js/security/advisories/GHSA-p293-qw3h-jr36): unauthenticated RCE
    on Windows filesystems, affected13.4..<15.5.24 and16..<16.3.3; no known Windows workaround; fixes15.5.24/16.3.3.
    Previous host Client ran on Windows; currently stopped. Linux image does not establish exposure to this Windows-specific path.
  - [GHSA-ggv3-7p47-pfv8](https://github.com/vercel/next.js/security/advisories/GHSA-ggv3-7p47-pfv8): request smuggling
    via chunked DELETE/OPTIONS in self-hosted external rewrites; fixes15.5.13/16.1.7. This Client uses external gateway rewrites;
    gateway still enforces JWT/roles. Passing ordinary proxy requests is not an adversarial security verification.
  - [GHSA-2xp9-vwfh-vxw4](https://github.com/vercel/next.js/security/advisories/GHSA-2xp9-vwfh-vxw4): Image Optimization AVIF RCE,
    fixes15.5.24/16.3.3. Client uses existing img thumbnails; no exploit or optimizer-route exposure is asserted here.
  The raw audit includes additional advisories; resolving these examples alone is not a clean audit.

## Concrete proposed scope for approval
- Upgrade Client Next to16.4.3 (registry audit proposal) and compatible eslint-config-next; update the lockfile through npm.
  Keep React18 if supported/verified; request further scope only if framework compatibility makes a React major necessary.
- Adjust existing build/lint/config and route parameter handling only where required by migration. Preserve public OpenAPI0.3.1,
  same-origin gateway proxy/cookie/JWT semantics, existing Stitch screens and deferred forgot-password behavior.
- Verify clean npm ci, tsc/lint/build, Docker build, production proxy smoke, full55Client E2E +live gateway sessions after runtime recovery.
  Rerun runtime audit; document any remaining finding rather than suppressing it. No production release without its normal approval gates.
- Expected files: client/package*.json, config/type definitions and existing route callers if compatibility requires;
  existing E2E fixtures/config only as needed, Codex evidence/tracker. No API/DB/Claude edits or new business capability.

Acceptance: approved scoped migration, required checks PASS, critical/high runtime findings resolved or explicitly reviewed,
UI/API behavior preserved. Current build is functionally verified for isolated development; public deployment remains gated.

## Implemented / verified2026-10-27
- Pinned Next16.4.3, eslint-config-next16.4.3, ESLint9.39.5; React/ReactDOM18.3.1 and their type major retained.
  Lockfile resolved normally, no --force/auditfix. Transitive postcss-selector-parser6.1.4→6.1.5 fixes the remaining moderate development advisory.
- Replaced legacy .eslintrc with flat eslint.config.mjs and nextlint CLI with eslintsrc. Webpack remains explicit in build script.
  Next16 new set-state-in-effect/preserve-manual-memoization diagnostics flagged existing React18 patterns; disabled only these2new diagnostics,
  documented shortcut until adopting React Compiler. rules-of-hooks/exhaustive-deps and other Next/TS rules remain enabled.
  Removed2unused inline lint directives only; rendered JSX/labels/styles/behavior unchanged. Initial lint failure recorded in INT-17-initial-lint.log,
  final lint passes. This is a compatibility policy, not a claim that compiler optimization has been validated.
- Next generated TypeScript configuration: jsxreact-jsx, targetES2017, .next/dev/types include and generated-route imports in next-env.
  Standalone tsc on fresh checkout needs `npx next typegen` first; build also generates them. No route parameter rewrite needed because callers use navigation hooks.
  Official [Next16 upgrade guide](https://nextjs.org/docs/app/guides/upgrading/version-16) documents CLI/bundler/typing migration.
- Host clean `npm ci --no-audit --no-fund`: PASS403packages (INT-17-host-install.log). `npm run lint`, `npm run build`, `npx tsc --noEmit`: PASS,
  all12existing route entries including dynamic video detail listed; Next reports13static generation jobs, a framework count change from14.
- Docker clean npmci408packages/lint/productionbuild/tsc PASS, output INT-17-container-build.log; no host node_modules copied.
  Image4fcf241026fb926cfd8d56bf5d31dade374df42dcded6c1037f2d2792d376cc3; inspect237333048bytes (INT-17-checks.json).
  Next18compatibility deprecation warning and host monorepo tracing-root warning remain informational; React18 was deliberately retained, root lockfile not removed.
- Docker production proxy smoke PASS/exit0, networknone/gatewayaliasloopback/no product volumes. Updated test to Next16 rewrites.afterFiles manifest format;
  actual POST/Bearer/cookie/HttpOnly/JSON/query/503 envelope forwarding assertions retained. INT-17-container-smoke.log.
- Full npm audit and runtime-only audit **0findings**, raw INT-17-full-audit.json/INT-17-runtime-audit.json. This verifies resolved dependencies at audit time,
  not a general application-security guarantee.
- `npm run test:e2e:types` PASS. **53Client fixture browser tests PASS (1.4m)** on host Next16 production (INT-17-playwright.log):
  auth singleflight/logout race/cookieidentity/cache behavior, media seek/transcript/download, visual/text search, interactions and390×844/1440×900 layouts.
- Two actual gateway session cases **NOT_RUN**, preflight127.0.0.1:8000 unavailable (INT-17-live-preflight.json). Earlier55tests belong to the pre-upgrade source,
  not claimed as55new passes. Gateway remains stopped after prior automatic start rejection; no alternate start path used.
  Keepalive fixture events during browser teardown can reach the unavailable proxy after route disposal; no product DB/service was running or modified.
- Owned host testserver was stopped after verification; smoke container autoremove. Existing project/Claude/faktory containers unchanged.

## Design compatibility check —390×844 /1440×900
Migration changes no layout, tokens, copy or event logic. Inspected new screenshots against pre-upgrade Client baseline;
original discovery_mobile/discovery_desktop HTML and INT-14 Stitch references remain read-only.

| # | Item | Migration result / inherited scope |
|---|---|---|
|1|Layout|Same sections/nav/cards as prior build; whole-page Stitch gaps stillINT-06|
|2|Colors|Existing CSS/Tailwind unchanged; preserved|
|3|Typography|Existing font/size/weight unchanged; preserved|
|4|Spacing/radius|Same geometry as baseline; inherited Stitch differences not repaired here|
|5|Icons|Same SVG renderer/icons; browser assertions PASS|
|6|Vietnamese copy|Unchanged; snapshot recommendation modes differ only by fixture data|
|7|AI elements|Badges/player/mode labels unchanged; personalized never inferred from upgrade|
|8|States|Loading/empty/error/disabled/auth/session/media tests PASS|
|9|Responsive|390×844/1440×900 browser checks PASS/no body overflow|
|10|Cut scope|No translation/social/new feature added; deferred forgot/reset behavior retained underD1|

Screenshots: INT-17-design/client-discover-390.png and client-discover-1440.png; baseline/stitch refs in INT-14-design.
Full-screen Stitch parity remains PARTIAL/INT-06; this check records migration compatibility, not full UI acceptance.

Lane: codex
Changed: Client package/lock/lint/TypeScript/Docker gate; unused comments; proxy-smoke manifest reader; owned evidence/tracker
Verified: host+Docker clean install/lint/build/tsc;full+runtime audits0;53E2E/types;proxy smoke;design compatibility
Contract touched: no (public0.3.1/AI-APIv1.3 unchanged)
Next safe task: run2live Client cases after user gateway recovery, then INT-17 REVIEW; no release/push without user

## Live runtime gate closed2026-10-27
- Gateway/infra/mock recovered externally. Existing Client container referenced old cached image, so Codex recreated only Client via
  Compose up -d --no-deps --no-build --pull never client, using already-verified Next16 image4fcf2410.
  No existing gateway/Claude/faktory start/restart by Codex; no dependency container recreation or orphan removal.
- `npx playwright test e2e/client_auth_live.spec.ts --reporter=list`: **2PASS10.8s**, raw INT-17-live-auth.log.
  Actual Client Docker→gateway→Postgres, both localhost/127.0.0.1: register/login, cookie origin/HttpOnly/rotation,
  profilePUT, feed/modepopularity, logout/cookie removal/reload. No route mocks; test accounts retain test provenance.
- This closes the2NOT_RUN cases in the earlier preflight. The53fixture cases were not needlessly repeated; same Client source/image already verified.
  Readonly unauthenticated /api/categories requests return401 on both origins. Local deployment snapshot RUNTIME-20261027.json.
- INT-17 acceptance met on lane, REVIEW pending normal release. No public API/schema/AI behavior change, no master push/release.
