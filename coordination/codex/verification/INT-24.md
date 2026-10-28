# INT-24 — HC-12/D23 subtitle drafts (2026-10-28)

Owner CODEX. Status BLOCKED on Client QA3100 startup approval review; source and CMS/real-backend gates verified.
User approved HC-12 first, then INT-05. Release#4 received; public0.4.0/AI-APIv1.3 unchanged.

Implemented explicit machine-draft notice in CMS transcript and shared Client transcript (desktop/mobile sheet),
plus draft label on Client subtitle overlay. Text download carries draft header and filename; CMS SRT uses draft filename
without modifying cue format. Existing subtitle API has no approval state, so edited text never claims official approval.
No new endpoint/type/schema/dependency, AI model/checkpoint or inference changes. Owned plans record user-approved copy override.

VERIFIED-NOW:
- CMS tsc +Vite build PASS (INT-24-cms-build.log).
- Client eslint +Next production webpack build +tsc PASS (INT-24-client-build.log), host QA rewrite127.0.0.1:8000.
- E2E types/diffcheck PASS.
- CMS QA5174: HC-12 tests390x844/1440x900 plus existing warning/seek/save/approval:3PASS17.3s, no retries (INT-24-cms.log).
  Explicit draft remains after edit/save/reload; SRT filename/content/cue syntax preserved, no horizontal overflow. Two screenshots saved.
- Real backend +realAI +CMSQA5174 +existing ClientDocker3000: video_flow upload test1PASS38.0s (INT-24-real-edit-approval.log).
  Summary publicnull before approval; admin-edited summary public after approval; manual editorial test caption saved via actual CMS,
  survives reload and public cache readback. Test deliberately seeds one editorial test segment to exercise UI, not a fabricated ASR-quality claim.
  Existing real worker/inference/publish/media checks also passed. Test video softdeleted/clip rejected/category removed by finally.

NOT VERIFIED / BLOCKER:
- New Client transcript/overlay labels and downloaded text browser checks: pending. Exact already-authorized Node Next start
  --hostname127.0.0.1 --port3100 was rejected by automatic approval review: 'blocked by policy'. No bypass/retry/start or Client test PASS claimed.
  User asked asynchronously to start that command externally; continue independent CMS INT-05 while waiting.
- Current product CMS5173/Client3000 images still INT-23; new labels are SOURCE/QA ONLY. No Docker recreation in this checkpoint.
- Existing full-page design gaps remain INT-05/06. Ten-item scoped check: layout/spacing adds only approved notice; colors/token text contrast,
  copy/AI disclosure/user-approved override, no new icons; CMS save/loading/empty/error and mobile wrapping use existing states/tests.
  Client responsive/visual items OPEN until browser available. Full Stitch PASS not claimed.

Changed: CMS subtitles/styles; Client Transcript/detail overlay/styles; three E2E files; two owned UI plans; task/session/handoff/evidence.
Next: finish Client QA when external3100 is running; then RE:HC-12 with final evidence. INT-05 independent CMS work can proceed now.
