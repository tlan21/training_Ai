# INT-26 — explicitly authorized production Client QA3100 (2026-10-29)

Owner CODEX. DONE for requested QA; HC-12 source verification moves INT-24 to REVIEW pending release/deployment authorization.
User explicitly renewed exact startup permission; previous automatic approval blocker resolved. No alternate launcher/port/container used.

- Existing buildGDlD_B05A4hk6gQkPj679 is newer than all current Client source. No source/config/dependency change, no rebuild needed.
- Exact command from client directory:
  `node node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3100`
  QA PID27160 verified by full command line +creation time. Login200; same-origin API/categories401 (actual gateway proxy).
- E2E_CLIENT_UI_URL=http://127.0.0.1:3100:
  `node node_modules/@playwright/test/cli.js test e2e/client_design.spec.ts e2e/client_player.spec.ts e2e/client_onboarding_layout.spec.ts --output=backend/.tmp/int26-qa --reporter=list`
  **71PASS /1.3m /no retries**. Current suite is a superset of the older63 count, no tests removed/skipped/weakened.
  Includes both390x844/1440x900 transcript draft notice, subtitle overlay draft label, filtered search +full TXT draft header/content/filename;
  pending summary hidden, auth/refresh/logout, role/tracking, media seek/playback, onboarding/keyboard/layout, truthful popularity/fallback modes.
- Inspected INT-26-transcript-390.png / -1440.png. HC-12 notices wrap inside panel/sheet; text+semantic contrast, no viewport overflow.
  User-approved D23 copy override documented in owned plans. Existing full-page visual parity gaps remain INT-05/06;
  no new UI change or FULL Stitch acceptance inferred from this test run.
- Stopped exact QA PID27160 after command/time identity recheck;3100 closed. First stop guard safely rejected its own date-string formatting comparison
  (PS JSON auto-parses ISO datetime); fixed guard comparison to UTC ticks, not a PID change. No other process stopped.
- Product Client3000 containerID/StartedAt/image unchanged and HTTP200 after QA; INT-26-runtime-before.json / -after.json.
- Client source3a2adf3 labels remain SOURCE/QA only; product image int23-fa8a382 not replaced, as user required. No master/push/AI/DB change.
- Existing real CMS edit/summary-approval evidence INT-24-real-edit-approval.log remains valid. Newly stronger original-summary test INT-25 failed
  on synthetic tone and is not counted PASS or hidden by this UI fixture suite. AI APIv1.3 unchanged.

Changed: owned evidence/session/tracker/HANDOFF only for this work; corrected INT-25 secondary snapshot to actual pre-cleanup HTTP trace.
Next: INT-27 actual cold Compose startup, preserving images/containers/volumes/AI PID; INT-25 natural-speech media input pending.
