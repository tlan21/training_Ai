# INT-59 — CMS Settings (3 new tabs) + Users admin password reset · 2026-11-12 (Claude, app lane)

Scope approved by user 2026-11-12 (AskUserQuestion): Users = no roles, no create/lock/delete, **admin resets passwords**; deletion not allowed;
Users **admin-only**; Settings opens **Cài đặt chung, Thông báo (in-app), Bảo mật: đổi mật khẩu, Bảo mật: phiên đăng nhập**.
Task + acceptance: `coordination/claude/OPEN_TASKS.md` (INT-59). Stitch only designs the AI tab → new tabs reuse its tokens/components.

## Commits
- `7612400` scope/task · `24307ab` API 0.11.0 contract + regenerated types (oapi-codegen 2.8.0, openapi-typescript 7.13.0; CMS = Client)
- `bd6c294` backend · `b0959f5` CMS + e2e · (this commit) live spec, compose pin, evidence, tracker

## Contract (`infra/openapi.yaml` 0.10.0 → 0.11.0, additive)
- `POST /api/cms/users/{id}/password` (admin; self 409, unknown 404, 8–72 bytes) — bcrypt cost 12, revokes all target sessions.
- `POST /api/cms/me/password` (any CMS account) — wrong current = **422 `INVALID_CURRENT_PASSWORD`** (not 401: no refresh/logout loop);
  keeps the current refresh session, revokes the others.
- `POST /api/cms/me/sessions/revoke-others` → `{revoked}`.
- Settings: `system_name`, `display_timezone` (5 zones), `notify_failed_jobs`, `notify_uncategorized_videos`, `session_ttl_days` (1–30) —
  **admin-only writes** (editor → 403, nothing saved); AI flags unchanged. Defaults via `coalesce` → **no migration**.
- `CmsMetrics.uncategorized_videos` (processed, no category, deleted excluded). `GET /api/cms/users` now admin-only.
- Refresh TTL + cookie `Max-Age` follow `session_ttl_days` for **new** sessions (auth is shared → applies to Client users too; stated on UI).

## Verified (VERIFIED-NOW)
- Go `vet` + `go test ./...` PASS (new: `TestAccountSecurity_ChangeResetRevoke`, `TestRefreshTTLFollowsSettings`,
  `TestAccountRoutes_RolesAndErrors`, `TestSettings_AdminOnlyFields`, `TestAccountSecurityContract`).
- **Real PostgreSQL** (stack DB, TEMP tables on one connection, test binary run in a throwaway container on `video-ai_default`;
  host :5432 is a different native Postgres): 12/12 PASS incl. new `TestAccountSecurity_RealPostgres` and `uncategorized_videos` in
  `TestCMSOperationsRealPersistence` → `pg_real_tests.txt`.
- CMS `tsc --noEmit` + `vite build` PASS.
- Fixture e2e (API mocked) `e2e/cms_int59_settings_users.spec.ts` 6/6 ×2 runs, 390×844 + 1440×900, states loading/empty/error/disabled
  (editor) → `fixture/*.png` (24). Regression: `cms_design` + `cms_settings_faults` + `cms_operational_search` + `cms_account_scope`
  76 passed / 4 skipped (opt-in), `cms_auth` 9/9 (needs `localhost`, the 127.0.0.1 cookie host fails also on the old build).
  Updated old specs that asserted the superseded scope (editor on /users, disabled tabs, bell as link).
- **Live** `e2e/cms_int59_live.spec.ts` (opt-in) 3/3 PASS on gateway/CMS `int59-b0959f5` → `live/steps.json`, `live/*.png`:
  bell = real metrics (0 failed + 5 uncategorized); general saved + reload (sidebar/title/UTC); notifications off → bell follows;
  TTL 2 → new login cookie `Max-Age=172800`; admin reset QA viewer → 204, old refresh 401, old pw 401, new pw 200; editor:
  users/reset/ttl/system_name 403, wrong current shown, change 204, other device 401, current kept, revoke-others 2 devices 401;
  390 read-only pass: 4 tabs/users/bell no horizontal overflow.

## Deploy
- C: had ~2.9 GB free and ~1.5 GB RAM → **overlay images**, no golang/node base pull: `Dockerfile.gateway-overlay`
  (`FROM video-ai-gateway:int11-843a56e` + gateway binary cross-compiled on host, go1.26.10, CGO_ENABLED=0, label revision b0959f5;
  orchestrator/cutter binaries unchanged and not redeployed) and `Dockerfile.cms-overlay` (`FROM video-ai-cms:int11-6288d60` + dist).
- `docker compose -p video-ai --env-file <empty> … up -d --no-deps --no-build gateway cms` with `AI_SERVICE_KEY` from the inference
  container (not printed). Gateway env hash before = after `56e23179db570721`. Both healthy. Pin in `docker-compose.cms-completion.yml`.

## Data
- `live/manifest_before.txt` = `live/manifest_after.txt` (**identical**): settings, users 51 / admins 1 / editors 0 / sessions 376,
  password fingerprint of all pre-existing accounts unchanged (admin@local password never changed).
- Own data only (`live/qa_manifest.json`): 2 QA accounts `int59-*@int59-qa.invalid` (editor role set by SQL), deleted with cascade;
  the 5 new setting keys (absent before) deleted after the API put defaults back; 1 orphan admin@local session from the first live run
  (see below) deleted → `live/cleanup.txt`.

## Follow-up 0.11.1 — "Kết nối & Lưu trữ" removed (user 2026-11-12: "bỏ hẳn và cập nhật tài liệu cho khớp")
- Why: the block was display-only — AI key shown as a fixed mask (gateway reads env `AI_SERVICE_KEY`; DB row `ai_service_api_key`
  unused), Storage Provider a locked one-option select, bucket names hard-coded (`raw-videos`/`clips`/`thumbnails`).
- `e9323d2` contract 0.11.1: `ai_service_api_key` `deprecated` in `Settings`/`SettingsUpdate`; `3c3b33b` gateway ignores writes, CMS AI tab
  without the block (Settings no longer polls `/system/health`); old specs assert absence. Docs: `.claude/cms_ui_spec.md`, `features.md`,
  `database_schema.md`, `plan/00_master_plan.md`, `plan/03_cms_ui_plan.md` (incl. CẮT-list), `infra/README.md`. `.opencode/**` was an old
  mirror (last change 20e9b9f): its 19 tracked doc copies were removed on user request (OpenCode CLI install files there are untracked, kept).
- Dead-code review: staticcheck U1000 + `tsc --noUnusedLocals` clean; removed the now-unread `SystemSettings.AIServiceAPIKey` (+ its column in
  `SettingsRepo.Get`) and the unused CMS `cloud` icon (`226e7e6`, real-PG 12/12 → `pg_real_tests_deadcode.txt`). Pre-existing dead code left
  as is (user picked none): `backend/internal/handlers/stubs.go` (no callers since a75ea5c), `.threshold-card input` slider CSS, role steps in
  `e2e/cms_audit_edges_live.spec.ts`, seed row `ai_service_api_key` in `002_seed.sql`.
- Verified: go vet + handler/contract tests PASS (key sent → not saved), CMS tsc/build, fixture 74 passed / 4 skipped (`fixture/settings-ai-admin-*.png`),
  deployed `int59-3c3b33b` (env hash unchanged `56e23179db570721`), live: PUT key → 200 with `md5(value)`+`updated_at` unchanged, GET masked,
  live parity 390 PASS (AI tab without the block). `live/manifest_after_0.11.1.txt` = before except sessions 376→377: one admin@local
  session created 09:53:46 UTC while no command of mine ran (assumed the user's own login) — left untouched.
- Superseded own images `int59-b0959f5` removed; seed row kept (no data deletion).

## Notes / limits
- Access JWT (15 min) stays valid until expiry after a reset/revoke; refresh is revoked immediately.
- Observed (pre-existing, not changed): two back-to-back page loads race refresh-token rotation and can log the user out; the first live
  run hit it (spec fixed to one navigation).
- "Số dòng mỗi trang" dropped (every list API has a fixed page size); add when requested. Login page keeps the default name (pre-auth).
