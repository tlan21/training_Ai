# INT-31 — real inference-service in Docker (2026-10-29)

Explicit user request: start inference-service on Docker and test real processing. Deployment-only scope;
Claude AI source/contract/model remains unchanged. Reuse the exact existing read-onlycheckpointbind, never copy/edit weights.
No host process stop or port conflict: Claude hostPID15852/:8001 remains untouched;
new inference internal8001 on existing video-ai network, gateway ->http://inference-service:8001 /AI_ALLOW_STUB0.

Startup found old inferencecontainer(created2026-10-15) exited3 withMilvusconnectionerror; it predated/v2.
Docker memoryavailable~4.8GiB, C1.65GiB/E1.31GiB. Rebuilding dependencies/pulling largeimages unnecessary.
Pinned source Claude **478052e6afea1139cb85ecb84100a0727a4535ad**, deployment/testsource commit **f1ad77c**.

Build/source integrity:
- Export `git archive 478052e ai-core/ai_core inference-service/app` into ignoredbackend/.tmp/int31-image/source.
 139files/699867bytes; assert no symlinks/pathescape/checkpoints/.env. No AI-owned file edited. Sourcemanifest INT-31-source.json.
- Retag exact cachedlegacyimage sha256ddd6ebd334333940024b1cc42197872b02b989a52b16495f667747d2dc6b241f to video-ai-inference:base-int31.
 `infra/inference/Dockerfile.runtime` COPY unmodifiedAI package/app only, no pip/model download.
- `docker-buildx build --network=none --pull=false --load --progress=plain -t video-ai-inference:ai-v2-478052e -f .../.tmp/int31-image/Dockerfile .../.tmp/int31-image`:PASS.
 Image manifest616c63aec37d5e7bb8447a26b34562bbf9eca94b99e88892c46a5b0c9578cddd; smallsource layers overexisting454MBbase.
 SourcefilehashesinsideDocker all139matchpinnedGit, sixmountedbest.ptSHAs/sizes match activehost before+after. No checkpoint copy/bake/change.

Runtime commands (WSL DockerDesktop, existing singleproject):
Docker=/mnt/host/wsl/docker-desktop/cli-tools/usr/bin/docker;
Compose=/mnt/host/wsl/docker-desktop/cli-tools/usr/local/lib/docker/cli-plugins/docker-compose;
DOCKER_HOST=unix:///proc/193/root/run/docker.raw.sock.
Compose arguments `-p video-ai --project-directory /mnt/host/e/traning_ai-codex
 -f /mnt/host/e/traning_ai-codex/docker-compose.yml -f /mnt/host/e/traning_ai-codex/docker-compose.inference.yml`.
AI_SERVICE_KEY read-only from Claude.env into memory, neverlogged/committed;
AI_CHECKPOINT_BIND set to the oldcontainer's exact /run/desktop/mnt/host/e/traning_ai/ai-core/checkpoints source;
APP_IMAGE_TAG=latest verified currentgatewayimage; processenv restored after eachcommand.
WindowsCompose defaultcheckpointpath E:/traning_ai/ai-core/checkpoints; create_host_path=false/read_only=true.

1. Validate explicitAIoverride: nohostports, FORCE_STUB0/INFER_DEVICEcpu, readonlyexistingmount, currentmodelkey,
 Milvushealthydependency for currentv1 compatibilitystartupwarmup (Claude removal afterrelease still pending).
 Initial preflight guard falsely countednullports asone in PowerShell; corrected to actualnonemptyports and passed, no mutation before correction.
2. `compose ... up -d --no-deps --no-build --pull never inference-service`: PASS, replaces only oldexitedAIcontainer.
 Dockerhealthtrue onlyifstubfalse/sixmodels/no degraded. Actual /health sixrealCPU/load_errornull.
3. Verified all139sourcefilehashes and6checkpointSHAs insidecontainer vsGit/activehost; then checkedactivejobs0.
 `compose ... up -d --no-deps --no-build --pull never --force-recreate gateway`: PASS, samegatewayimage/credentials/allenv exceptAI_BASE_URL.
 PrimarytargetnowDockerDNS, startupAIprobePASS, gatewayhealth200 minio/milvusok.
4. `E2E_AI_DOCKER_CONTAINER=video-ai-inference-service-1 E2E_DOCKER_HOST=unix:///proc/193/root/run/docker.raw.sock
 E2E_AI_V2_VIDEO=.../int28-natural.mp4 E2E_AI_V2_FRAME=.../int28-query.jpg
 node node_modules/@playwright/test/cli.js test e2e/ai_v2_live.spec.ts e2e/video_flow.spec.ts e2e/visual_search.spec.ts --output=backend/.tmp/int31-e2e --reporter=list`:
 **4PASS1.2m** (20.2/28.8/1.6/17.4s). Strictcontenttest readsDockerhealth viaexec/publichealth, not hostprocess.
 Realuploadprocessed/backend10vectors+thumbnails/categoryca_nhac/ASR3segments/summarydraft240chars,
 ownvideoTOP1score **0.99206525**, feedpopularity. Repeateddelete204/ownvectors0/rawclipthumb404/Mongoanalysisempty.
 CMSedit/review/publish/Clientplayback +invalidvideo privacy +ANNcache/latency/publishprivacy/Client regressions PASS.
5. DockerAI log actual200POST/v2vision,/v2asr,/v2search,/v1highlight,/v1completions;
 gatewaylogbannerAI http://inference-service:8001 and no4retired/v1primarypaths. Endpointauth401 withoutBearer PASS;
 real/v2recommendation503MODEL_NOT_READY (expectedAI-12), nofake personalized vectors.
6. FinalhealthDockerstubfalse/6/no degraded,14othercontainers IDs/images/start/mounts unchanged;
 hostAI PID15852 remainsreal/unchanged. Only gateway+previousexitedinference replaced; no mock reintroduced/hostports published.
 Original100PGrows hash42a7d5f45e2b974b7b724b1a3d8bd91c and10categories hash2279cd784f346ec1e52ce40605752c91 unchanged;
 fournewowntestuploads softdeleted, activejobs0. Milvus original411live/49videos allIDs/values/payload identical;
 MinIO95raw/47clips/460thumbs alloriginalkeys/size/ETags unchanged. Sixcheckpointfiles unchanged.
 Gateway/CMS5173/Client3000 healthy/HTTP200. Data/volume removal none.
7. E2ETypeScriptnoEmit, PowerShellASTsyntax, diffcheckPASS. Coldstartuputility detects currentDockerAI mode,
 includesexplicitoverride/13services, preserveshostPID andexcludesownedAIfromoutsiders; read-onlypreflightPASS13services/1outsider.
 No fullcoldstackstop/reboot repeated. Go/FE sourceunchanged, no redundantbuild/dependency install.

Scope/limits:
- Source/model/checkpoint files remainClaude-owned; this deployment consumes the user's Docker request without editing them.
 CurrentAIcode retainsv1 startupMilvus compatibility; /v2 compute endpoints own no persistence. Claude's removal/release work not performed here.
- CPU realinference verified, no GPU/load/soak/modelquality claim. DraftASR/summary adminreview remainsrequired (D23).
 Docker runtime uses cached dependencybase to avoid large downloads; freshdependencyimagebuild not performed.
 /v2 remainsDRAFT untilClaude release, so no INTEGRATED_REAL/DONE endpoint promotion; INT-31 deployment acceptance is complete.
- To manage this DockerAI mode, include docker-compose.inference.yml. Root-onlyCompose intentionally remains the hostAI mode.
 Do not change/stop Claudehostruntime or checkpointfiles when managing this stack.

Lane: codex
Changed: ownedinferenceDockerrecipe/explicitComposeoverride/coldstartup/E2Ehealthsource/docs/coordination
Verified: 139source+6checkpoint hashes,6realDockerhealth,4realE2E,auth/recommendation errors,persistentdata+host/14containers preservation PASS
Contract touched: no (public0.4.1 unchanged, consumeClaudev2DRAFT read-only)
Next safe task: Claudev2API_READY release; Docker deployment running/verified, no extra imagebuild required
