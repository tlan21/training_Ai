# SESSION — authoritative resume state (2026-10-27)

## Branch / coordination
- Worktree E:/traning_ai-codex, branch codex/integration. Release#1/#2/#3 received; HEAD..master empty at resume.
- No Codex release/push/master/shared-file edits. Claude source read only via git show; no model/checkpoint/inference changes.
- Skill: backend_endpoint for image/integration verification; Ponytail full. Current public contract0.3.1/AI-APIv1.3 unchanged.
- No task IN_PROGRESS. INT-17 BLOCKED on scoped major-framework decision; INT-13 PARTIAL on deployed runtime gate.

## Verified this session
- INT-13 d6388dd: full own Python3.11-slim/CPU worker image build PASS, context14.31kB.
  Image4caf38a8cfdc2651bdcb76195aae61ed7410d24edfe41f711a2002834fd0681b (inspect362651913bytes).
  Four packaged tests PASS13.836s/networknone/memory1GiB/no product volumes; pipcheckPASS.
  CPU/no model/checkpoint/inference-service audit PASS. Existing worker not replaced; actual Kafka/MinIO pipeline NOT_RUN.
  Evidence verification/INT-13-runtime-* +INT-13.md. INT-13 PARTIAL.
- INT-16 fresh Docker build PASS, context4.37MB/client-only Dockerfile ignore; npmci/Next14.2.35 types/lint/build14routes PASS.
  Image83d175168674232e4ce43a38bdc519a478d6001735d210b723c5f027d1f15e67 (inspect208700149bytes).
  e2e/client_container_smoke.cjs PASS: production login200, baked gatewayDNS rewrite, cookie/HttpOnly/Bearer/JSON/query/503 envelope forwarding.
  Ephemeral networknone container with internal fixture, no product service/port/volume, removed after test. INT-16 REVIEW functional acceptance.
- INT-15 REVIEW: Claude2026-10-27 handoff+report accepted final bundle schema/provenance/rows/SHA. Data gate NO_DATA, not training readiness.
  Only accepted bundle E:/traning_ai-codex/backend/.tmp/ttv2/20261026T113856Z, exporter33495fba40f2a3ffd79c1dbb50471585180ae3d7.
  users/videos/clips/interactions0, categories10; no promotion of test/unknown data. Quarantined20261026T113611Z never consume.
  Cleanup correction33495fb verified0fixtures; final manifest committed. Claude owns labels/loader/training.

## New concrete blocker INT-17
- Fresh image npmci reports6 vulnerable packages overall; readonly runtime-only audit: Nextcritical +PostCSShigh.
- Primary Next advisories confirm Windows-hosted RCE (GHSA-p293-qw3h-jr36) and external-rewrite request smuggling (GHSA-ggv3-7p47-pfv8).
  No exploit or current public exposure claimed. Current Windows server stopped; Linux smoke functionality is not a security pass.
- Registry latest14=14.2.35; audit fix proposes Next16.4.3/isSemVerMajor=true (Node22 supports its>=20.9engine).
- Concrete scope/acceptance in verification/INT-17.md; ask user approval for major migration under significant-architecture-change rule.
  No package/lock upgrade, auditfix or forced install applied. Keep public deployment gated.

## Runtime / resources
- Docker restarted externally before resume; only faktory_server running. Project video-ai containers are stopped, no app/API listeners.
  Gateway exited2 from prior session; other project containers exited255 around Docker restart. Claude real8001 currently not listening.
- Prior automatic approval review rejected targeted gateway start with reason "blocked by policy". Do not retry through another route;
  user manual recovery/intervention remains needed. No Docker/WSL global restart or existing-container start by Codex this session.
- Direct daemon CLI works with current dockerd pid193:
  wsl -d docker-desktop -- /mnt/host/wsl/docker-desktop/cli-tools/usr/bin/docker -H unix:///proc/193/root/run/docker.raw.sock ps -a
  Recheck PID after external restart. Compose/buildx binaries: same cli-tools/usr/local/lib/docker/cli-plugins/.
- Existing binary bind override backend/.tmp/docker-direct.yml retained; gateway binary is latest18d1a3b interaction/provenance source.
  Own ingest image now built but stopped old worker still references cached legacy image; replace only after runtime recovery.
- C:13.26GiB/E:1.48GiB at final image checks. No prune/delete/project data loss, no new npm dependencies on host.
  Test containers autoremove; images remain for verified deployment. Never start legacy inference-service container/attach checkpoints.

## Historical valid evidence / outstanding scope
- INT-00/02 REVIEW; INT-12 CMS auth REVIEW d607226/41E2E(2live), INT-16 host c30c664/52E2E then55Client E2E with INT-15.
- INT-15 source18d1a3b, contract987d647; Go vet/test/build, CMS/Client checks,8intendedPGtests/no skips and55browser PASS2026-10-26.
  Latest business restart attempt NOT_PASS/Desktop stalled; exact fixture rollback restored threshold75 and softdeleted owned testvideo.
- INT-14 primary popularity02001e0 verified PG/metadata/modes/Client; full parity+feed pagination unfinished. Personalized gated AI-12 production readiness.
- INT-11/01 realAI E2E still HO-03 transport; host health was real6models previously, container→host8001 timed out. No new INTEGRATED_REAL.
- INT-05/06 full Stitch parity +extra API scope decision pending CONTRACT_DECISIONS.md; no unapproved routes. INT-10 DEFERRED unchanged.
- INT-07/08 GPU/load/48hsoak gates; INT-09 docs depends on them. No task DONE repeated.

## Next safe actions
1. User major-migration decision -> INT-17 IN_PROGRESS/commit; scoped compatibility update then audit/types/lint/build/Docker/proxy/UI/live checks.
2. User runtime recovery -> inspect intended containers/health first. Deploy verified own ingest image without pull/build, run pipeline with explicit mock.
   Do not bypass the earlier gateway-start rejection or start Claude's legacy Docker inference container.
3. Claude8001/API health ready +container transport recovered -> INT-11 real pipeline/search E2E; only then update real integration matrix.
4. Continue full UI parity only within approved contract; collect real product interactions without fabricating data to satisfy AI-12.

Lane: codex
Changed: ingest package audit/test/docs; Client build allowlist/container proxy smoke; Codex evidence/audit/task checkpoints
Verified: full ingest image+4tests/pip; full Client npmci/build+production proxy smoke; Compose configs/syntax/diff; Claude bundle ACCEPTED/NO_DATA
Contract touched: no; existing public0.3.1 and AI-APIv1.3 unchanged
Next safe task: INT-17 after major decision; INT-13 deployed pipeline after user runtime recovery

## INT-17 approval / migration started2026-10-27
- User explicitly approved the proposed major upgrade: "hãy nâng lên". INT-17 IN_PROGRESS, only active task.
- Branch correct/clean, no new master release. Read coordination/Claude handoff; no new AI contract/schema.
- Project skill client_screen for Client behavior/route compatibility regression; Ponytail full. Preserve Stitch markup/styles/API/auth behavior.
- Scope: Next16.4.3 +compatible ESLint tooling, lockfile/config/compatibility only; retain React18 where supported and verified.
- C:13.27GiB/E:1.48GiB. Prefer lockfile-only resolution then clean Docker install/build on C:; no host dependency trees/download duplication on E:.
- Need runtime audit, type/lint/build, Docker proxy smoke,55Client E2E with live2 cases separately gated by stopped gateway.
