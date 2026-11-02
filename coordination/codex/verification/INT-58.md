# INT-58 — Publish HC-19 and current open-task checklist (2026-11-02)

Owner CODEX. Status DONE. User first requested push/merge, then asked for the open-task checklist; the latter steers rather than cancels publication. Initial clean codex/integrationHEAD8a37ab6/master8e6fd39; gitmerge master alreadyuptodate. Received source11584c5/actualHC19evidence8a37ab6, source unchanged. Start727a8b2; release **053b143406ab905a3131b5ffb2400ece13acf078**.

## Publication scope / preflight

- Initial difference versus master22files/19014insertions/24deletions, primarily sanitized baseline/after hashes and parity reports. Operational difference: existing inference image/env/dependency change; tests/verifier updates. No manual AI-lane source/checkpoint/API-contract edits.
- gitfetch origin PASS: remote master/integration36b8a1f46392aa70f5afd33c90ca75d124e0202b both ancestors of HEAD. Remote Claude26c2346d61b8585c6c2627ef232fa0eb6209002a and phase115976b3761a3c29f04fc83f9a522541fe0b015f3 retained. No master worktree checked out; normal fast-forward possible.
- Shared release status/tagged CODEX masterplan/sync14 updated only under this authorization. HC-19deployment/E2E complete, current imagev3.0/101source/deps{}, recommendationDRAFT and model-quality/GPU/fullCMS gates unchanged. New Claude ACK read via gitshow, no manual Claude-file write or merge of unpublished lane work.

## Verified checklist

OPEN_TASKS.md contains **exactly32existing non-DONE IDs**, matched against all detailed TASKS sections by assertion (publicationINT-58 excluded). Counts:10PARTIAL/4BLOCKED/16REVIEW/1TODO/1DEFERRED. No status automatically promoted merely because code was previously released.

Checklist distinguishes actual CMS/fourpolicy/UI acceptance, recommendation/GPU/soak/docs dependencies, deferred Client recovery and16REVIEW rows needing evidence reconciliation. Existing contract/persistence/runtime fixes are not blindly repeated. Relevant stale nextactions reconciled: product006alreadyappliedtwice, cancellation74344bbalreadydeployed, latestCMStitlefixnotdeployed, oldPID3392mustnotbeassumedvalid. The initial text-extraction command hit Windows cp1252 on Vietnamese; corrected to JSONensure_ascii before the full32ID audit, no status falsely inferred from truncated output.

## Release gates — VERIFIED-NOW

| Gate | Command | Result |
|---|---|---|
| Backend | cd backend; GOPROXY=off/GOMAXPROCS=1; go vet ./...; go test ./...; go build ./... (stop on nonzero) | PASS/exit0; INT-58-go.log, cached package results retained |
| CMS | cd cms; node node_modules/typescript/bin/tsc --noEmit; npm run build | PASS/exit0; Vite4.04s/index-DciNKmBZ.js; INT-58-cms.log |
| Client | cd client; node node_modules/typescript/bin/tsc --noEmit --incremental false; npm run lint; npm run build | PASS/exit0; Next compiled3.7s/generated13pages; INT-58-client.log |
| Current actual runtime | existing-container health +readonlycheckpoint hashes +gatewayhealth | PASS6real/stubfalse/deps{}, correctv3imageSHAf626..., no MINIO/MILVUSenv, checkpointRO;10filesmatch sameimage4videoparity0.0; gateway200; INT-58-live.json |
| Real pipeline acceptance | retained actualINT-57Playwright results from testedsource11584c5, unchanged afterrun | 1PASS16.8s, newprocessed/10vectors/3ASRsegments/threshold51/TOP1.99206525, owncleanup/alloriginaldata+15othercontainersPASS; not replayed solely for Git publication |
| Checklist/whitespace | exact32IDset assertion; git diff --check/stagedcheck | PASS |

No repeated model/raw-upload/fullCMS workload, runtime recreation, schema/data/model/checkpoint write, imagebuild/download or new dependency. Current model-file hashes match the full parity proof; existing Client multiple-lockfile and React18 warnings nonfatal. Default Go suite is not opt-in live DB testing. Existing original-data/rawE2E proof remains clearly separate from build/fixture tests. No new INTEGRATED_REAL promotion from health alone.

## Publication

Actual publication PASS: release053b143406ab905a3131b5ffb2400ece13acf078, git push . HEAD:master fast-forward8e6fd39→053b143; git push --atomic origin master:master codex/integration:codex/integration advanced both36b8a1f→053b143. git ls-remote --heads origin asserted both targetSHAs=HEAD; Claude26c2346d61b8585c6c2627ef232fa0eb6209002a/phase115976b3761a3c29f04fc83f9a522541fe0b015f3 unchanged; gitstatusshort empty. No force/history/defaultbranch change. This docs-only completioncheckpoint follows to localmaster/bothoriginrefs, final equality/cleanstate/source/checklist assertions in tool output; no functionalgates repeated for docs-only completion.

Lane: codex
Changed: release-authorized sharedstatus/taggedplan/sync14 +owned checklist/tracker/session/handoff/logs
Verified: mandatoryGo/CMS/Clientgates, currentv3health/parity-provenance, retainedactualHC19E2E, complete32taskchecklist PASS
Contract touched: no (public0.8/AIv3 consumed unchanged)
Next safe task: scopedCMSQA/evidence reconciliation per OPEN_TASKS.md; no outstanding merge/push work
