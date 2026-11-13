# INT-63 — BUG: Client and CMS logged each other in/out · 2026-11-13 (Claude)

User: "tại sao khi login hay đăng xuất ở client thì ở cms cũng login hoặc logout và ngược lại hãy rà bug này".

## Root cause
The gateway set ONE host-only HttpOnly cookie named `refresh` (Path=/) for every app. Browsers scope cookies by host, **not by port**,
so the Client (`localhost:3000`) and the CMS (`localhost:5173`) shared it:
- login in app B overwrote app A's refresh cookie → app A's next refresh used B's session (A silently became B, or failed);
- logout in app B revoked that session and cleared the cookie → app A's next refresh got 401 → A logged out.
The same would happen in any deployment that serves both apps on one host name.

## Fix (API 0.14.1, additive)
- Optional request header `X-App` (`components.parameters.AppHeader`) on register/login/refresh/logout and the CMS
  own-password / revoke-other-sessions endpoints. `X-App: cms` → cookie **`cms_refresh`**; no header → **`refresh`** (Client unchanged).
- Gateway `handlers.RefreshCookie(c)` used at all 8 former `"refresh"` sites (auth.go, cms/account.go); CORS allows `X-App`.
- CMS `apiClient` sends `X-App: cms` on every request, including the separate refresh call. Client code unchanged.
- One-time effect: CMS sessions created before the deploy (in the old `refresh` cookie) had to log in again.

## Commits
`bfe9b4d` scope · `2a58769` contract 0.14.1 + regenerated types · `193bcfe` gateway + CMS fix + tests/specs · `21e8ba4` live spec, pins, tracker.

## Verified (VERIFIED-NOW)
- Go: vet clean; `TestRefreshCookieIsScopedPerApp` (both cookies sent to both apps: each refresh/logout uses and clears only its own;
  CMS logout revokes only the CMS session); existing handler/cms/auth tests ok.
- CMS: tsc + build; fixture `cms_auth.spec.ts` 9/9 (now also asserts `X-App: cms` on refresh/logout and that a Client `refresh` cookie
  survives a CMS logout).
- Live: new `e2e/cross_app_session_live.spec.ts` **1/1** — one browser context, admin in the CMS + QA viewer in the Client: both cookies
  present, both refresh 200; CMS logout → `cms_refresh` gone, Client reload refresh 200 and still signed in; CMS login again, Client logout →
  `refresh` gone, CMS reload refresh 200 and still on the dashboard. Existing `cms_auth_live` + `client_auth_live` 4/4.
- QA data: 1 `int63-*@int63-qa.invalid` + 2 `e2e-int16-*@example.test` (created by client_auth_live) deleted → users client 50 / admin 1.

## Deploy
`video-ai-gateway:int63-193bcfe` (overlay of int62-e8a2498), `video-ai-cms:int63-193bcfe` (overlay of api012-f6bc07f, host-built dist);
env hashes unchanged (gateway 56e23179db570721, cms b3f8fe29fb2cde11); pins in `docker-compose.cms-completion.yml`; rollback = previous tags.
