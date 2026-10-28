# INT-06 — approved Client production QA, 2026-10-28

Owner: CODEX. User explicitly approved running Client QA on3100. Branch codex/integration;
HEAD..master empty, clean initial worktree, Release#1/#2/#3 already received. No new API/release/live-deployment approval inferred.
Start/progress commit: b82a75c. Client source unchanged at a4bbb01; no implementation or assertion changes in this QA run.

## Result

**65 PASS in1.6m** against the existing Next16.4.3 production build, buildID `CAT_3TF7GI5-2Dm5o3Y8f`.
The previously failing dev tracking test passed with its original assertions: one watch_time on session end,
12–13watched seconds, seek/hidden time excluded, no duplicate exit record, no heartbeat. No tracking source was changed.
This demonstrates the failure was not reproduced on this production run; it does not certify every possible dev lifecycle.

Commands:

```powershell
# client directory
node node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3100
# repository root
$env:E2E_CLIENT_UI_URL='http://127.0.0.1:3100'
node node_modules/@playwright/test/cli.js test e2e/client_design.spec.ts e2e/client_player.spec.ts e2e/client_onboarding_layout.spec.ts --output=backend/.tmp/int06-production-20261028 --reporter=list
```

Evidence: [complete test output](INT-06-production-20261028.log), [paired screenshot index](INT-06-comparison/index.json).
Preserved16production layout PNGs +16geometry JSONs +2original-source player PNGs, both390x844/1440x900.
The index retains older before/dev/reference captures with separate stage labels.

Passed scope: auth refresh concurrency/logout/identity isolation, no persisted access JWT, onboarding IDs/DOM/keyboard order
and511packing combinations, mobile/desktop auth and navigation geometry, original-source player layout, seek/transcript/download,
similarity upload/threshold and unavailable/error/empty/loading states, feed interactions/swipe, product-role-only tracking,
highlight range/offset logic. Existing forgot/reset regression cases ran unchanged; this does not reactivate deferred INT-10.

## Runtime checks and cleanup

- QA `/login`: HTTP200 with production Next static assets; ready in3.9s, bound only to127.0.0.1.
- QA `/api/feed` without credentials: HTTP401 `UNAUTHORIZED`, confirming the existing gateway rewrite.
- Gateway `/healthz`: ok. Existing Client3000 `/login`: HTTP200. No service/container was replaced.
- Owned Next PID19872 and its exact command/listener ownership were checked before stopping. Port3100 then had no listener.
  QA process session exit1 is the intentional stop; Playwright exit0/65PASS is recorded separately.
- Next emitted the existing multiple-lockfile/workspace-root warning; no config/dependency change was made for this QA task.

These are deterministic fixture UI tests plus player/helper checks. API data/AI responses in them are intercepted;
they are **not new real AI integration acceptance**. The unauthenticated proxy check is read-only, not a full authenticated business flow.
Client build/tsc/lint were already verified2026-10-27; no source changed and those gates were not redundantly rerun.

## Acceptance boundary

The approved QA3100 action is complete. INT-06 remains PARTIAL: pending library API/forgot-link decisions and full per-screen
design differences in INT-06.md are not accepted or implemented by this approval. No full design-parity/DONE claim.
No liveClient deployment, master/shared-status update, push, model/checkpoint/AI code or product-data change.

Lane: codex
Changed: owned QA evidence, comparison index/captures, SESSION/TASKS; no app source change
Verified: Next production start/HTTP200;65browser/helper checks PASS1.6m;proxy401;owned stop/closed3100
Contract touched: no (public0.3.2/AI-APIv1.3 unchanged)
Next safe task: INT-05 existing-API visual corrections; INT-06 unresolved scope remains pending
