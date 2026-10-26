# INT-12 — CMS JWT in memory (2026-10-26)

Owner: CODEX. Project skill: `cms_screen.md`; required Design Parity Check: `ui_design_review.md`.

## Change
- Removed Zustand persist and discarded legacy `cms-auth` from both browser stores. JWT and user remain in RAM.
- Bootstrap rotates the HttpOnly refresh cookie, loads generated `UserMe`, then permits admin/editor routes.
  Refresh is single-flight, requests retry once, a rejected refreshed bearer signs out, and stale failures do not clear a newer token.
- Login validates generated response types/role; logout waits for pending refresh before revoking its cookie and clears query cache/RAM.
  A nonsecret signed-out flag prevents reload from restoring a session after a failed logout request.
- Storage contains only remember preference, signed-out flag and a session marker. Unchecked remember survives reload in the current
  browser session, but does not silently restore in a new browser session. No contract/schema/dependency changes.
- Login parity corrections scoped to `.cms-login`: line heights, spacing, input padding, checkbox, button states, missing/extra icons.
  Forgot/reset behavior unchanged (INT-10 remains deferred).

## Verification
- `cd cms; npm run build`: PASS (tsc + Vite, 180 modules). `npx tsc --noEmit`: PASS earlier independently.
- `npm run test:e2e:types`: PASS.
- `npx playwright test e2e/cms_auth.spec.ts e2e/cms_auth_live.spec.ts e2e/cms_design.spec.ts --reporter=list --output=test-results/int12-checkpoint`:
  see `INT-12-playwright.log` for the completed run. 2 live gateway cases, 9 adversarial auth cases, 30 UI/regression cases.
- Live cases use the running gateway/Postgres with no intercepted API: login 200, HttpOnly cookie, refresh 200 and cookie rotation,
  dashboard restored for both remember choices, logout 204, cookie removed, reload stays signed out. No AI call required.
- Adversarial fixtures cover legacy stored bearer rejection, concurrent 401s, refresh failure, rejected retry bearer, failed logout/reload,
  logout/refresh race, new session without remember and denial/revocation for client role.
- `git diff --check`: PASS. Screenshots inspected at both required viewports; `INT-12-design/measurements.json` contains computed geometry.

## Design Parity Check — login only

Reference: read-only `stitch_ai_video_cms/index.html`; CẮT-list plan 03 §7.2 (none removed from login).
Screenshots: `INT-12-design/stitch-login-{390,1440}.png`, `INT-12-design/cms-login-{390,1440}.png`.

| # | Block | Stitch | CMS | Result |
|---|---|---|---|---|
| 1 | Layout | centered card + footer, same order | 390: x16/y104/w358/h588; 1440: x490/y140/w460/h572 | Match, identical card geometry |
| 2 | Colors | #461599 accent; #FAF9F6 background; white .7 card | same hex/alpha, editor button transparent/black as exported HTML | Match |
| 3 | Typography | Inter, h1 24/32 700, subtitle 12/16, inputs 14/20, submit16/24 | same family/size/weight/line-height | Match specified styles; local TTF versus remote font has ~1.3px text-width difference |
| 4 | Spacing/radius | card32/r16; input40 padding; footer32; input/r8 | same; password/submit/footer y391/493/724 mobile, y427/529/744 desktop | Match |
| 5 | Icons | movie_filter filled, person, lock, visibility, shield_person, edit_document | same names, existing local Material SVG; removed submit arrow | Match |
| 6 | Vietnamese copy | all login labels, title, footer, quick buttons | same; development default credentials are dynamic data | Match |
| 7 | AI elements | none | none | Match |
| 8 | States | focus glow, hover, pressed, disabled/loading/error | implemented, keyboard focus retained; house skeleton during session restore | Match + plan loading/error |
| 9 | Responsive | centered at390/1440, divider wraps on mobile | same, no body overflow; login geometry assertions at both widths | Match |
| 10 | CẮT | none on login | no removed original element; forgot link kept per D1 | Match |

This verifies login scope, not the full CMS parity task INT-05. No pixel-identical raster claim across font assets.
Refresh cookie revocation requires an available backend; if logout fails the local flag prevents automatic restore, but cannot revoke the server session offline.

Lane: codex
Changed: cms auth store/client/bootstrap/router/hooks/Sidebar/LoginPage/global.css; e2e auth/live/design fixtures; Codex evidence/trackers
Verified: CMS build, E2E types, browser auth/live/UI suite; see log
Contract touched: no (existing public auth contract consumed; AI untouched)
Next safe task: INT-11 — receive master Release #2, verify real integration gates
