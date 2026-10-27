# SESSION — authoritative resume state (2026-10-27, real AI verified)

## Current outcome / branch
- Worktree E:/traning_ai-codex, branch codex/integration. Release#1/#2/#3 received; HEAD..master empty at session check.
- User explicitly approved: "cho phép chuyển sang AI thật" (eaca064). Approved gateway-only transition is complete; no further apply confirmation pending.
- INT-01 +INT-11 REVIEW: real upload/search integration **3PASS54.3s**. Six API_READY AIv1.3 matrix rows now INTEGRATED_REAL.
- INT-19 REVIEW: public0.3.2 pagination/error contract clarified, 3types regenerated, bothTS/Go/embeddedSpec checks PASS. No application logic changed yet.
- INT-14 IN_PROGRESS: implement primary/fallback feed and newest/trending catalog cursor pages under contract213aaa9. Only one active task.
  Acceptance/callers/tests listed in TASKS. Current gateway remains real; no runtime change until checks pass.
- INT-14 current verification checkpoint: final Go vet/test/build +Linux artifacts PASS; real PG joined-query tests PASS/no skips using TEMP tables.
  New gateway-int14 (SHA c5284c5c2fe00f5f2c20fe9faab0dfecb3fec1bfb62bc085ff5a1f0ab45c8d81) now deployed gateway-only, all env including realAI/stub0 unchanged.
  Running guarded live4E2E session23040: content_pagination_live +video_flow +visual_search. Do not start another task/recreate gateway during this run.
  Script backend/.tmp/apply-pagination.ps1 rolls back to verified real gateway-int18 on failure, never mock. Evidence INT-14-pagination.md/logs.
  INT-13/17/18 REVIEW, own worker/Next16/startup binary deployed locally. No master release/push authorized/performed.
- Project skill backend_endpoint.md +Ponytail full. Claude code/checkpoints/models untouched; committed handoff communication only.

## Live runtime — keep real
- Gateway healthy, AI_BASE_URL=http://host.docker.internal:8001, AI_ALLOW_STUB=0. Shared Claude HTTP key is container env only,
  read from the previously authorized local env into process memory for apply; never print/commit it or full container env/Compose config.
- Gateway-only recreation used existing image/no-build/no-deps/pullnever. Readonly binary mount backend/bin/gateway-int18 →/usr/local/bin/gateway;
  SHA256 da8d646b8a8bdfc48775ae9b15fd2ed313e50cedbedb548e307e4a8194cda280. INT-18 startup code now deployed.
- Local ignored backend/.tmp/docker-real-direct.yml describes AI URL/stub0/required process key +binary mount. Root Compose defaults already real.
  Preserve key processenv/WSLENV discipline if future recreation is needed; do not run mock override over current gateway accidentally.
- Claude host8001 real/stubfalse/6models/degradedempty/visual_indexok; devicecpu, recommendation_indexmissing_collection expected.
  Gateway authenticated CMS systemhealth6; missingBearer search401. Primary feed recommendation_mode=popularity, personalized remains disabled.
- Existing CMS5173/Client3000/own ingest/PG/Mongo/Redis/MinIO/Kafka/Milvus running. Mock remains available but gateway no longer calls it.
  Legacy Docker inference stays stopped; faktory untouched. No other service recreation/global restart/checkpoint mount.
- Ingest image ed21674b559e233f4b6f4bd3600496ebf2c4da7d974db0f104822c6debebba0c; only ingest_work volume, no AI source bind.
- Client image4fcf241026fb926cfd8d56bf5d31dade374df42dcded6c1037f2d2792d376cc3, Next16.4.3/React18.3.1.
- Direct daemon pid193 last verified. Recheck after external restart. CLI:
  wsl -d docker-desktop -- /mnt/host/wsl/docker-desktop/cli-tools/usr/bin/docker -H unix:///proc/193/root/run/docker.raw.sock ps
  Compose/buildx under same cli-tools/usr/local/lib/docker/cli-plugins/; Windows named pipes previously hung.
- C:5.93GiB/E:1.24GiB last disk check before real transition; no large install/build/pull without fresh resource check.
  Go GOMAXPROCS1/TMP/TEMP/GOTMPDIR backend/.tmp. No source build repeated for this config/evidence-only step.

## Real E2E evidence — VERIFIED-NOW
- Command (environment E2E_GATEWAY_URL=http://127.0.0.1:8000, E2E_AI_URL=http://127.0.0.1:8001):
  node node_modules/@playwright/test/cli.js test e2e/video_flow.spec.ts e2e/visual_search.spec.ts --reporter=list
- 3PASS54.3s/no retries: upload/vision/ASR/highlight/summary draft/approval/cut/publish/CMS+mobileClient playback38.4s;
  invalid media failed/private1.6s; actual Siamese/Milvus newvideo search/JPEG200/publish privacy/cache/desktop+mobile UI12.5s.
- 20cold gateway-cache samples p50/p95/max48.53/150.87/178.14ms;20warm8.92/11.74/13.97ms, all below2s.
  This sequential CPU sample is not load/soak/GPU/model-quality acceptance. Full Stitch parity not certified by flow screenshots.
- Final independent readback gatewayhealthy/real, strict6model/stubfalse andBearer401, primarypopularity;3exact fixtures softdeleted:
  vid_dmfcfh717m5b,vid_dmfcftrr3gtp,vid_dmfcfukqtor5. Test accounts/media retained/no existing data deletion/product export promotion.
- First invocation failed before tests because machine npx wrapper invoked npm exec px; rollback restored mock. Then installed Node CLI succeeded,
  final real config retained. Do not count first attempt PASS; preserved runner-attempt1.log. No test process left running.
- Evidence verification/INT-11.md, INT-11-real-e2e.log, INT-11-live-health.json, INT-11-final-runtime.json,
  INT-11-visual-latency.json, INT-11-real-screenshots/. Matrix/INT-01/11/handoff updated. Public0.3.1/AIv1.3 unchanged.
- Summary regeneration route not separately retested; real completions endpoint exercised via upload stage. No fresh full gateway image build/release gates.

## Completed checkpoints — do not repeat
- INT-18 91e7ef8 +6e25029: bounded90s dependency startup Go wait, strictAI health retained; Go vet/test/build +3unit PASS.
  Isolated delayed realPG29.35s PASS/no skips/networknone/tmpfs removed. Worker Kafka3 uses KafkaConnectionError/bootstrap_timeout_ms5000,
  partialcleanup/deadline/permanent-config tests;8packagedtestsPASS0.185s. Gateway artifact now deployed as above.
- INT-13 6e25029: own CPU/PyAV/DSP worker image built/deployed, no models/checkpoints. Actual Kafka/MinIO/mockAI/cutter/publish/playback206/privacy
  pipeline PASS INT-13-pipeline.json/log; restart_verified=false. First bad SDK-key attempt failed/cleaned before finalpass, never countedPASS.
- INT-17 691ede2/fbfa730: Next16.4.3/React18.3.1/ESLint9/Webpack; host+Docker cleaninstall/lint/build/tsc PASS, full/runtime audits0,
  53fixtureE2E PASS1.4m, isolated proxy smokePASS; deployed Next16twoactual live auth sessions PASS10.8s. No UI/style/API change for real transition.
- INT-02/12/15/16 REVIEW with committed historical evidence. INT-15 verifier accepted final bundle20261026T113856Z but **NO_DATA**,
  0productrows/10categories. Never consume quarantined113611 bundle, never fabricate product vectors or training readiness.

## Next safe work / open gates
- INT-14 PARTIAL: primary PGpopularity/metadata/mode/liveUI verified; existing feed/catalog cursor pagination gap remains. Continue this independent
  assigned scope after reading its contract/callers/tests; mark exactly1task IN_PROGRESS and commit first. No new endpoints unilaterally.
- INT-03 personalized blocked AI-12 productionquality/productvectors/API_READY gate, not required for primary popularity.
- INT-05/06 full Stitch parity and extra routes require existing CONTRACT_DECISIONS scope decisions; INT-10 forgot/resetDEFERRED unchanged.
- INT-07 GPU/load requires RTX3060 or user-approved equivalent; INT-08 48hsoak and INT-09 docs dependent. CPU/T4prelim not finalacceptance.
- Release only when user requests: run full Go/CMS/Client +relevant real matrix gates, shared status/masterplan updates only in that release flow.
  Current technical API integration success does not certify model quality/fullappcompletion/productiondeployment.

Lane: codex
Changed: approved real gateway config/startup artifact deployment; owned evidence/matrix/tracker/handoff
Verified:3real E2E PASS54.3s;health6/stubfalse/Bearer401;finalreadback/popularity/3fixturecleanup
Contract touched: no (public0.3.1/AI-APIv1.3 consumed)
Next safe task: INT-14 pagination; release gates only upon explicit user release instruction

Final real acceptance commit: ff0494f (runtime/evidence/matrix/INT-01+11 REVIEW/handoff). All verification commands completed; no running E2E session.
