# INT-16 — Client same-origin API (2026-10-26)

Owner CODEX. Acceptance met on host; REVIEW pending lane release. No API schema change.

Browser defaults to relative `/api`; built-in Next rewrites forward to IPv4 gateway on host and `gateway:8000` in Docker.
Compose passes the destination at build time. Requests retain HttpOnly cookies, JSON bodies and Bearer headers; HTTP timeout10s.
Explicit external browser API remains optional. Docker uses npm ci without an unlocked fallback.

Live tests exposed a refresh/logout navigation race. Shared auth handling now serializes refresh/logout, shares concurrent401 refresh,
checks renewed user identity before retry, clears cached user data on session changes, and guards protected routes through Next navigation.
A nonsecret signed-out marker prevents cookie bootstrap after a failed logout. JWT remains in RAM; no token in browser storage.
Login/register validate user IDs. Existing screen markup/styles and deferred forgot/reset behavior were preserved.

## Verified now
- Client `npx tsc --noEmit`, `npm run lint`, `npm run build`: PASS,14 routes; single build CPU/1024MiB heap.
- Root `npm run test:e2e:types`: PASS.
- Assert-based config check: host IPv4, Docker DNS/trailing slash and built route manifest: PASS.
- `npx playwright test e2e/client_design.spec.ts e2e/client_auth_live.spec.ts --reporter=list`: **52 PASS (1.0m)**.
  Output: INT-16-playwright.log. Two cases use actual gateway/Postgres through Client on localhost and127.0.0.1, without route mocks:
  register/login,401 envelope, cookie domain/HttpOnly, feed200/modepopularity, PUT profile, reload/rotated refresh, logout204/cookie removal/reload.
  Test accounts carry e2e-int16 prefix; retained, not training data.
  Four targeted fixtures cover parallel401/singleflight, logout during held refresh, logout503/reload, different refresh-cookie user.
  Other46 cases exercise390×844 and1440×900 layouts, playback/actions/error/empty states and truthful recommendation labels.
- `git diff --check`: PASS.

No layout redesign; existing INT-14 Design Parity Check and INT-06 full-screen gaps remain applicable.
Fresh Docker image and containerized Client smoke were NOT_RUN because shared disk capacity remains limited.
Backend pipeline still uses explicit AI mock; this check makes no new INTEGRATED_REAL claim.

## 2026-10-27 — Docker build/proxy gate
- Added client/Dockerfile.dockerignore allowlist: only Client sources, excluding node_modules/.next/env/tsbuildinfo; context4.37MB.
- Full `docker-buildx build --load --progress plain -t video-ai-client -f client/Dockerfile .`: PASS/exit0.
  npm ci from existing lockfile, Next14.2.35 production compile/lint/types/14routes PASS. Node22-alpine base digest
  fe4f6d74e20370acb04ad889077d14d0f64a9c8ea6a42bc60cddf1e844699914. INT-16-container-build.log.
- Image83d175168674232e4ce43a38bdc519a478d6001735d210b723c5f027d1f15e67, inspect size208700149bytes;
  npm start command. INT-16-container-image.json.
- e2e/client_container_smoke.cjs in an ephemeral networknone container, gatewayalias127.0.0.1, readonly test mount,
  no product port/volume: production login200 +compiled Docker rewrite +POST body/Bearer/cookie/HttpOnly Set-Cookie +GET query +503 error envelope PASS/exit0.
  Fixture gateway and Next process terminate, container autoremove. No DB/AI use; no deployed-stack browser claim for this run.
- Node syntax check and git diff --check PASS. No UI markup/style/business API change; prior55browser evidence remains historical.
- **Security gate is separate:** npm ci reports6 vulnerable packages overall; runtime-only audit identifies Nextcritical and PostCSShigh.
  Existing Next14.2.35 stays pinned; no auditfix/major upgrade. INT-17 records primary advisories and requested migration decision.
  Functional build/smoke PASS does not imply public-deployment readiness. Existing stack remains stopped, no gateway-start bypass.

Lane: codex
Changed: Client HTTP/auth/config/callers, Compose/env/docs, browser tests, Codex trackers
Verified: tsc/lint/build/config/types;52 E2E including2 live gateway sessions
Contract touched: no; existing public0.3 endpoints only
Next safe task: INT-15 interactions and readonly export
