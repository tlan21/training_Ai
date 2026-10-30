# INT-47 — CMS accounts simplified (implementation checkpoint)

User override2026-10-30; public contract0.7.0/f3d6080. Source implemented, pending real deployed gateway/UI acceptance with remaining CMS batch.

- Removed CMS recovery page/link and quick-login/default credentials; old recovery bookmark redirects to login. Removed unused quick-login CSS and corresponding active recovery UI test. Client still consumes shared recovery; service now denies recovery for CMS accounts without revealing existence. Public Client behavior preserved while clarification pending.
- Removed role-write gateway route/handler, UserRepository method and PG/memory implementation, frontend role hook/editor/adminOnly branch. All provisioned CMS accounts share the same management capability; authentication still excludes public Client accounts. No account data/role value/schema deleted; no CMS account-delete implementation existed.
- Users is read-only, server-side username/email search with literal ILIKE escaping, deterministic pagination and created_at; no role or password-hash response. Header search stays on users. Fixed ignored DB errors.
- Backend `go vet ./...`, `go test ./...`, `go build ./...` PASS. New tests cover read-only search/no secret or role disclosure and CMS recovery denial. CMS typecheck/build PASS; Client typecheck passed contract gate, unchanged source. E2E types PASS.
- Browser new scope4PASS8.5s; regression63PASS/2FAIL due old Users heading expected. Kept original Stitch heading and reran affected layout/scope checks **6PASS10.6s**; original regression log retained, not called65PASS. Existing61remaining fixture tests are valid for unchanged paths.
- QA uses only own Vite preview PID3392 :5174; service5173/Client3000 untouched. QA still needed for subsequent batch, stop exact recorded PID at final checkpoint. No deployment/model/DB mutation yet.
- Design10: existing layout/colors/type/spacing/icons preserved; user-authorized removals of recovery/quick roles/role-edit controls. Created-date table/search replaces role widgets.390/1440 screenshots in ignored test-results/int47-final; full pixel parity remains INT-05, no fabricated counters. Guard/loading/error/auth states checked. Source reference unchanged/read-only.

Next: operational contract INT-48, existing41..44 and8screen implementation; deploy only owned app services at final acceptance and verify real APIs/data preservation before promoting this task DONE.
