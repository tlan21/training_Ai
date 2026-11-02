# INT-56 — Publish HC-17/HC-18 to master and origin (2026-11-02)

Owner CODEX. Status DONE. User explicitly requested push and merge master after the prior push request was interrupted. Startup audit found no partial uncommitted operation: clean codex/integration HEADA9f1bd9, master479f5d5, five owned commits pending local release. `git merge master` already up to date. Task start **121e59e**, release **f60d7a2e92e9e227a87b2f1ec84f87f0377ed919**.

## Scope and remote preflight

- Initial diff versus master20files/2273insertions/18deletions, primarily sanitized verification artifacts. Operational change is only the existing inference compose image/comment; no application/AI source or public/AI contract change by Codex.
- Includes HC-18 image/full parity3e63056 and RE:HC-183807519; HC-17 provenance/tests/readinesscb86e0d and RE:HC-17 closurea9f1bd9. Published Claude release#6/master479f5d5 already received.
- `git fetch origin` PASS. Before push: origin/master479f5d5a07b6caeef44d0d7013b4c1646f9b6b2b, origin/integrationf1a8a29de720584eba07e62f06ab48a810abc996, origin/Claude26c2346d61b8585c6c2627ef232fa0eb6209002a, phase115976b3761a3c29f04fc83f9a522541fe0b015f3. Both target remote refs are ancestors of HEAD (exit0), no force required. Master is not checked out in either worktree.
- Shared status/tagged Codex master-plan entries/sync12 updated under explicit release authorization: INT-54/55 DONE and INT-28 formal readiness gate resolved using publishedv2+existing real VERIFIED-HIST E2E. No false current raw-upload result, model-quality or fullCMS acceptance. Existing AI status/metrics retained; runtime deployment facts updated from Codex evidence.

## Release gates — VERIFIED-NOW

| Gate | Command | Result |
|---|---|---|
| Backend | `cd backend; GOPROXY=off GOMAXPROCS=1; go vet ./...; go test ./...; go build ./...` (PowerShell env, stop on nonzero) | PASS/exit0; INT-56-go.log, cached package results retained |
| CMS | `cd cms; node node_modules/typescript/bin/tsc --noEmit; npm run build` | PASS/exit0; Vite3.84s, index-DciNKmBZ.js/index-Y6W6UZTl.css; INT-56-cms.log |
| Client | `cd client; node node_modules/typescript/bin/tsc --noEmit --incremental false; npm run lint; npm run build` | PASS/exit0; Next compiled3.9s, generated13pages; INT-56-client.log |
| Current real service | existing-container GET /health + /openapi.json, readonly mounted-file hashes, gateway /healthz | PASS: healthy6real/stubfalse/degraded[], exactHC18imageSHA271bb4bab6f4,4deprecatedflags,10currentfiles match retainedparity, gateway200; INT-56-live.json |
| Full parity proof | validate both INT-54 official news/soccer outputs, same current image and ten current checkpoint/recipe hashes | 4realfeaturevideo PASS, maxdiff0.0/clipsidentical/threshold51; not rerun unchanged full verifier merely for publication |
| Whitespace | git diff --check +staged check before commits | PASS |

Existing nonfatal Client multiple-lockfile/root and React18 deprecation warnings retained. Go default suite is not opt-in live DB testing. No dependency/image build/download, new container/port/runtime recreation, source/model/checkpoint write or product-data operation during this publication.

Changed matrix readiness rows use **valid VERIFIED-HIST actual E2E INT-28/31 (2026-10-29)** plus API_READY onmaster479f5d5, with current source/runtime/official parity confirmation INT-54/55. This follows coordination README§4 evidence levels. No fresh raw-upload/search/deletion/fullCMS workload is claimed. Recommendation remainsDRAFT/popularity, INT-50 blocked on explicit approval for its previously rejected real-QA action; model-quality/GPU/load/soak/fullStitch gates unchanged.

## Publication

Executed after gated release commit f60d7a2e92e9e227a87b2f1ec84f87f0377ed919:

```text
git push . HEAD:master
  479f5d5..f60d7a2 HEAD -> master
git push --atomic origin master:master codex/integration:codex/integration
  f1a8a29..f60d7a2 codex/integration -> codex/integration
  479f5d5..f60d7a2 master -> master
git ls-remote --heads origin
  f60d7a2e92e9e227a87b2f1ec84f87f0377ed919 refs/heads/master
  f60d7a2e92e9e227a87b2f1ec84f87f0377ed919 refs/heads/codex/integration
  26c2346d61b8585c6c2627ef232fa0eb6209002a refs/heads/claude/ai-core
  15976b3761a3c29f04fc83f9a522541fe0b015f3 refs/heads/phase1-ai-core
HC17_HC18_PUBLICATION_VERIFIED
git status --short  # empty
```

Both target remote refs asserted equalHEAD, unrelated branch SHAs unchanged; no force/history rewrite/default-branch change. This documentation-only completion commit records actual success, is forwarded normally to local master and both origin targets, followed by final equality/clean-state/unchanged-source assertions in tool output. Functional gates are not repeated for the documentation-only completion.

Lane: codex
Changed: release shared Codex metadata/tagged plan/sync log +owned tracker/session/handoff/logs
Verified: all mandatory release gates, current real health/exact image+checkpoint parity provenance, localfastforward/atomicpush/remoteassertions PASS
Contract touched: no (publishedv1.5/v2API_READY consumed, recommendationDRAFT retained)
Next safe task: separate approvedCMSQA or Claude D24step3; no outstanding master/origin publication work
