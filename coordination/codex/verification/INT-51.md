# INT-51 — Authorized integration publication (2026-11-02)

Owner: CODEX. User requested `hãy push code lên và merge vào master`, then `tiếp tục task`. This task publishes committed source and accurate progress; it does not certify INT-50 complete or deploy containers.

## Scope and startup

- Branch: `codex/integration`; working tree initially clean; application source `7c7dd74`.
- Local master: `62b7e0501cba80edcebaf3d7aad0a764d6494a9f` (Claude release #5), already merged without conflicts as `ab9e4d9`. `git log HEAD..master --oneline` empty; `git merge-base --is-ancestor master HEAD` exit0.
- Read AGENTS.md, coordination/README.md, Codex SESSION/TASKS, Claude HANDOFF_OUT, AI_API_CONTRACT and TASKS via `git show`. AI-API v1.4 published; v2 still DRAFT. Project backend_endpoint skill consumed for existing backend validation; Ponytail full keeps this publication free of additional feature work.
- `git fetch origin` PASS. Remote `origin` is `https://github.com/tlan21/training_Ai.git`. Before publication: integration `6a6a982a58d6e5ead736d8dbcdf49494f8059d86`; Claude `26c2346d61b8585c6c2627ef232fa0eb6209002a`; phase1 `15976b3761a3c29f04fc83f9a522541fe0b015f3`; no remote master. Integration is an ancestor of HEAD (exit0); no force or history rewrite needed. Remote default branch remains unchanged.
- Application/evidence diff at initial HEAD versus master: 1209 files, 117064 insertions, 2512 deletions. `git diff --name-only master HEAD -- ai-core inference-service coordination/claude` empty. No manual AI-lane edits in this publication.
- Outgoing objects inspection: 1312 blobs, 36.20 MiB uncompressed at initial publication inspection; no outgoing blob above100MiB. Tracked filename scan found no .env/nonexample .env.*, private-key file or model checkpoint extensions. Existing historical training artefacts already reachable from origin are left untouched.

## Verification

Prior process handles no longer existed when resuming, so their unknown results were not counted. The following gates were rerun with output retained:

| Gate | Command | Result |
|---|---|---|
| Backend | `cd backend; $env:GOPROXY='off'; $env:GOMAXPROCS='1'; go vet ./...; go test ./...; go build ./...` (stop on any nonzero exit) | PASS, exit0; INT-51-go.log; AI HTTP4.008s, cutter6.717s; cached package results retained |
| CMS | `cd cms; node node_modules/typescript/bin/tsc --noEmit; npm run build` (stop on nonzero exit) | PASS; INT-51-cms.log; Vite11.00s, index-DciNKmBZ.js / index-Y6W6UZTl.css |
| Client | `cd client; node node_modules/typescript/bin/tsc --noEmit --incremental false; npm run lint; npm run build` (stop on nonzero exit) | PASS; INT-51-client.log; Next compiled22.1s, TypeScript7.7s, generated13/13pages |
| Whitespace | `git diff --check` | PASS; repeated before publication commit |

Fresh live E2E: **NOT RUN**. Docker Engine is unavailable; the prior real-QA file-creation/run action remains policy-rejected and awaits explicit approval as recorded in INT-50-resume-2026-11-02.md. No alternative launcher/port/container, new QA data mutation, runtime repair or deployment was attempted by INT-51.

Default Go tests include cached results and do not replace the opt-in real database/inference integration suites. No current live database or inference result is inferred from this local gate.

Client build emitted existing multiple-lockfile/workspace-root and React18-deprecation warnings; both lint and build exited0. No dependency/config change was added for this Git publication.

Existing integration evidence remains **VERIFIED-HIST**, allowed by coordination/README.md §4; none is relabeled as a current runtime result:

- INT-11-real-e2e.log / INT-14-pagination-real-e2e.log: actual upload/analysis/review/publish/search/privacy/popularity; retained API_READY v1 highlight/text/health INTEGRATED_REAL rows.
- INT-28.md: actual v2 compute-only/backend storage/search/delete flow, preserved411old vectors/49videos, natural speech segments; status remains REVIEW/REAL_PENDING because Claude v2 API_READY release is still pending.
- INT-31.md: real Docker inference six models/stubfalse, four actual E2E tests, data/runtime preservation; no new model-quality or v2-readiness promotion.
- INT-35.md / INT-36.md / INT-39.md: real compilation, frame sizing and FFmpeg precision scoped acceptance.
- INT-50.md: source/fixture/adapter and historical rollout proof; final eight-screen real acceptance remains BLOCKED. The title correction7c7dd74 is not deployed.

No matrix row is promoted by this publication. Current-source/current-runtime AI feature parity remains HO-04. Personalized recommendation, GPU/load/48h-soak and full Stitch parity retain their existing gates.

## Publication

All local release gates passed. Shared Codex status/tagged master-plan lines and sync log synchronized without promoting unfinished functional work. Next: commit exact owned/shared-release paths, then `git push . HEAD:master` (fast-forward only), followed by normal pushes of integration/master to origin. Verify both remote SHAs and preserve other remote branches. Explicit user Git authorization is already present; no additional confirmation is required for these normal pushes. Actual publication results will be appended after success.

Lane: codex
Changed: release-authorized Codex status/master-plan metadata, owned tracker/session/handoff/evidence only
Verified: Go vet/test/build and CMS/Client release gates PASS; existing real evidence HIST; fresh real E2E not run
Contract touched: no (public0.8.0 consumed, AI v1.4 published/v2DRAFT unchanged)
Next safe task: finish INT-51 publication; INT-50 after Docker Engine recovery and explicit approval of the previously rejected real-QA action
