# SESSION — authoritative resume state (2026-10-27)

## Branch / active task
- E:/traning_ai-codex, codex/integration. Clean at latest checkpoint; Release#1/#2/#3 received, HEAD..master empty.
- Only INT-11 IN_PROGRESS: real HTTP transition prepared, awaiting explicit gateway-apply confirmation requested via async question.
- INT-13 REVIEW own image/deployed pipeline; INT-17 REVIEW Next16/deployed live sessions; INT-18 REVIEW startup source tests.
- No master/shared-file release edits, push, reset/clean/stash. Claude code/checkpoints/models untouched; communicate through committed handoff.
- Project skill backend_endpoint for current runtime/integration work. Ponytail full.

## INT-11 ready transition — NOT applied
- Current AI-APIv1.3 release#3 on master:6API_READY, recommendationDRAFT. Primary product popularity remains enabled underD18.
- Latest host127001:8001health200/stubfalse/6models; deployed worker→host.docker.internal:8001health200/stubfalse/6models.
  Missing Bearer search401. OldHO-03 transport timeout no longer reproduces. Evidence AI-HEALTH-20261027.json +INT-11-transport-recheck.log.
- Local backend/.tmp/docker-real-direct.yml configquietPASS: gateway-only canonicalhost8001/stub0/securekey processenv;
  readonly mount backend/bin/gateway-int18 →/usr/local/bin/gateway. Artifact SHAda8d646b8a8bdfc48775ae9b15fd2ed313e50cedbedb548e307e4a8194cda280.
- Current gateway is STILLMOCK; real upload/search E2E NOT_RUN, integration matrix unchanged. No new INTEGRATED_REAL.
- Earlier automatic review rejected targeted gateway start with reason "blocked by policy". User confirmation now requested for the exact
  prepared gateway recreation/realtests step; no response received yet. Do not infer consent or bypass via another route.
- Concrete plan +verify/rollback: verification/INT-11-real-transition.md. After explicit approval, refresh daemon/health, capture existing mock env in memory,
  read previously authorized shared Claude HTTP key into processenv only, apply root+real-direct --no-deps --no-build --pull never gateway.
  No other service/legacy inference/checkpoint start. Failure restores original root+mock+docker-direct config/key; never log credentials.
- Real gate commands after success: E2E_GATEWAY_URL=http://127.0.0.1:8000, E2E_AI_URL=http://127.0.0.1:8001;
  npx playwright test e2e/video_flow.spec.ts e2e/visual_search.spec.ts --reporter=list. Only then mark relevant matrix rows real.

## Runtime now
- Stack was started externally during this turn. Gateway firstfailed PG57P03 then becamehealthy after another external restart;
  Codex never started/restarted/reconfigured the existing gateway. Its mounted binary remains preINT-18 source.
- Codex replaced only stopped ingest with own verified imageed21674b559e233f4b6f4bd3600496ebf2c4da7d974db0f104822c6debebba0c.
  Worker running, only ingest_work volume attached; no old inference image/source bind/checkpoint. Two SDK3 issues corrected before final validation.
- Codex replaced only old Client with verified Next16 image4fcf241026fb926cfd8d56bf5d31dade374df42dcded6c1037f2d2792d376cc3.
  Client3000/CMS5173/gateway8000/infra/mock healthy/running. Real8001 now UP, owned by Claude. Legacy Docker inference remains stopped.
- Faktory untouched. Isolated PG/test containers removed; no product volume deletion/prune. Own fixtures softdeleted, settings restored under guard;
  even the first timed-out fixture vid_dmfbq4y4z7kn remainsdeleted after late worker delivery. Test users/media retained aspolicy/origin=test.
- Direct daemon currentlypid193; recheck after external restart:
  wsl -d docker-desktop -- /mnt/host/wsl/docker-desktop/cli-tools/usr/bin/docker -H unix:///proc/193/root/run/docker.raw.sock ps
  Compose/buildx under same cli-tools/usr/local/lib/docker/cli-plugins/. Existing mock override backend/.tmp/docker-direct.yml retains old binary path.
- C:5.93GiB/E:1.24GiB at finalcheck; no large new build/install without space check. Go GOMAXPROCS1/TMP/TEMP/GOTMPDIR backend/.tmp.

## Verified checkpoints
- INT-18 91e7ef8 +Kafka correction6e25029: shared bounded90s/perdependency Go PG/Mongo/Redis/MinIO/AI-health startupwait;
  strict6model/stub opt-in unchanged. Go vet/test/build +3startup unitPASS, isolated delayed realPG29.35s PASS/exit0/no skips.
  Linux gateway-int18 artifact built separately, not deployed. Kafka3 startup retry/partialcleanup/permanent-config handling;
  KafkaConnectionError and bootstrap_timeout_ms match actual SDK; config-key assertions +8packaged tests PASS0.185s/networknone.
- INT-13 6e25029: own worker deployed with no deps/build/pull; real Kafka/MinIO/ingest/cutter/clip publish/range206/privacy/business persistence PASS,
  HTTP AI explicitMOCK_ONLY. Evidence INT-13-pipeline.json/log. Script SkipGatewayRestart/EvidencePath preserved old INT-02 evidence;
  restart_verified=false, no new restart claim. First failed SDK-key attempt timedout/cleaned, never markedPASS.
- INT-17 691ede2 +fbfa730: Next16.4.3/React18.3.1/ESLint9 flat config/Webpack; host+Docker cleaninstall/lint/build/tsc PASS;
  full/runtime audits0,53fixtureE2E PASS, proxyproduction smokePASS. Two actual live auth sessions NOWPASS10.8s on deployed Next16Docker,
  localhost/127001 through real gateway/Postgres. No need to rerun unchanged53fixture cases; complete source/localruntime acceptance REVIEW.
- Runtime snapshot verification/RUNTIME-20261027.json. Detailed reports INT-13.md/INT-17.md/INT-18.md and raw logs committed.

## Other tasks / scope
- INT-00/02/12/15/16 REVIEW with historical evidence; do not redo DONE work. INT-15 Claude verifier accepted final clean bundle
  backend/.tmp/ttv2/20261026T113856Z; NO_DATA (0product rows,10categories), not training readiness. Never consume quarantined20261026T113611Z.
- INT-14 PARTIAL: primary popularity/metadata/modes verified; feed/catalog pagination gap stillopen (deferred when runtime recovery became available).
  Personalized production depends AI-12 quality gate; no MovieLens/zero/fake product vectors.
- INT-05/06 full Stitch parity/extra API scope pending CONTRACT_DECISIONS.md; no new routes. INT-10 DEFERRED untouched.
- INT-07/08 GPU/load/48hsoak gates and INT-09docs dependents remain. Full app/AI completion not claimed.

Lane: codex
Changed: startup resiliency; worker SDK3 fixes/deployment; business-script no-restart evidence mode; owned runtime/live/real-preflight evidence
Verified: Go+3unit;delayedPG29.35s;8worker tests;deployed mock pipeline;2live Next16;host/container realhealth6+401;real config preflight
Contract touched: no (public0.3.1/AI-APIv1.3 unchanged)
Next safe task: INT-11 apply+realE2E after explicit confirmation; otherwise existing approved pagination/UI scope work

## INT-11 explicit approval received2026-10-27
- User: "cho phép chuyển sang AI thật". Gateway-only recreation/real API verification is authorized; no further confirmation needed for that step.
- Refresh preflight/contract/artifact before apply, compare unrelated gateway env to current, retain original mock key only in process memory for rollback.
- Apply tested gateway-int18 mount +canonicalHTTP/stub0/sharedkey processenv. Verify systemhealth6real, run2real E2E files; failure restores mock.
- No checkpoint/AI source change, no other service recreation, no master release/push.
