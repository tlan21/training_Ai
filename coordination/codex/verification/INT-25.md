# INT-25 — HO-03 real AI acceptance, 2026-10-29

Owner CODEX · DONE. User explicitly authorized real integration; master26c2346 / AI-APIv1.3 read, Release#4 already received.

## Runtime / key

Gateway was ALREADY using http://host.docker.internal:8001, AI_ALLOW_STUB=0, int23-fa8a382 image and healthy.
Compared Bearer byte-for-byte in memory with read-only E:/traning_ai/inference-service/.env: matches. Never printed/persisted key.
Startup log explicitly names real URL; /healthz200; real /health stubfalse,6models/degraded[]. Existing real switch INT-11/23 was not repeated.
No gateway recreation necessary. Mock retained unchanged for CI; no inference process/checkpoint/model/internal source changes.
INT-25-runtime.json +INT-25-final-health.json record safe selected configuration/banner/health (not full inspect/env/config).

## Actual original AI content — PASS with documented real user media

Existing T4.3 report (read through claude/ai-core) documented an existing user video10.08s/2,504,101bytes;
old filesystem staging copy is absent, original processed video vid_dm46jsx30bah remains in owned MinIO.
Read-only admin detail ->presigned GET ->own ignored backend/.tmp/int25-user-source.mp4. Original row/media not changed.
Source bytes/hash/provenance: INT-25-source-provenance.json. A presigned GET URL rejected a preliminary HEAD403;
GET succeeded and actual downloaded size independently asserted2,504,101bytes. Signed URL/token not logged/committed.
No source media/transcript or test vectors promoted into training data; all new uploads have test provenance.

Strict gate (no UI edits/seeded outputs/mocks):
```powershell
$env:E2E_AI_CONTENT_VIDEO='E:/traning_ai-codex/backend/.tmp/int25-user-source.mp4'
$env:E2E_GATEWAY_URL='http://127.0.0.1:8000'
$env:E2E_AI_URL='http://127.0.0.1:8001'
node node_modules/@playwright/test/cli.js test e2e/ai_content_live.spec.ts --output=backend/.tmp/int25-user-final --reporter=list
```
**1PASS24.6s** final source (first real-media run1PASS10.3s before adding persisted JSON output).
Original AI response counts are captured BEFORE any editorial write and before cleanup:
- processed; category ca_nhac;10timeline seconds
- summary123characters, statusdraft
-3ASRsegments, all3nonempty
- realAI6models/stubfalse/degraded[], source SHA256 matches downloaded original
Full count-only proof: INT-25-user-content-counts.json; raw user transcript/summary not committed.
Fresh test upload softdeleted by finally; original source staysprocessed. This certifies integration/content presence, NOT model accuracy.
D23 still requires human review; recommendation remains DRAFT/NO_DATA.

## Protocol / recommendation / preserved failures

Existing upload->processed->editorial subtitle+summary approval->cut/publish->Client playback flow after cold reboot:
**1PASS42.9s**, INT-25-protocol.log. Explicit feed mode assertionpopularity; original outputs attached before editorial overrides.

Real recommendation POST /v1/recommendation/completions with current Bearer returns503/AI_UNAVAILABLE (missing collection),
INT-25-runtime.json. Actual gateway GET /api/feed?limit=1 returns200/modepopularity (INT-25-feed-mode.json).
MVP deliberately passes no recommendation client to feed: primary Postgres popularity; do not claim the current gateway makes an upstream
recommendation request then catches503. Optional fallback modes/metadata/privacy/cache regression5subcases PASS:
`go test ./internal/handlers -run '^TestFeedModeMetadataLimitAndCachedVisibility$' -count=1 -v`, INT-25-feed-regression.log.
That unit test is mock-adapter evidence, distinct from the real503 probe/live primary feed. No personalization readiness claim.

Initial strict run on8s synthetic colorbars/tone FAIL summaryempty; dedicated gate also FAIL summary0 /ASRnonempty0
(categorytin_tuc/timeline8/processed). Retained INT-25-real-flow.log / -ai-content.json / -content-gate.log / -original-content-counts.json.
Not counted PASS or hidden. First secondary snapshot was taken after cleanup; corrected to actual precleanup HTTP response in trace.
Known nonspeech fixture is valid for protocol/state checks, not a content-presence gate. Dedicated e2e/ai_content_live.spec.ts takes explicit
short natural-speech input <=20MiB; absentinput SKIP is never counted as contentPASS. Existing protocol assertions preserved separately.
No AI implementation was changed to manufacture text; valid existing input completed this previously partial requirement.

## Final protection / scope

Original79video fingerprints caaadd6588f7f8f4a2da381f51577b9a and10categories2279cd784f346ec1e52ce40605752c91 unchanged.
Strict-test uploads verifieddeleted/training_origintest, activejobs0: INT-25-data-cleanup.log. Original user source included in preserved79.
Final AI PID26848,6real/degradedempty; gatewayhealthy/CMS5173+Client3000HTTP200; QA3100closed.
Cold startup/volume proof INT-27; production QA71PASS INT-26. No app-image replacement, master/shared status update or remote push.
E2Etypes/diffcheck PASS. No app source or API schema change in this acceptance work, no need to repeat unrelated full builds.

Lane: codex
Changed: live protocol evidence/assertion, dedicated explicit-input content gate, owned tracker/session/matrix/handoff/evidence
Verified: real content1PASS24.6s; real protocol1PASS42.9s; recommendation503/feedpopularity;5mode regressions; data/runtime checks
Contract touched: no (public0.4.0 and AI-APIv1.3 unchanged)
Next safe task: remaining INT-05/06 scoped UI parity; HC-12 product rollout only with authorization to replace existing UI images
