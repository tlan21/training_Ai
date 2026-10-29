# INT-30 — Docker real-AI runtime / remove running mock (2026-10-29)

User explicitly authorized Docker update and removal of the running ai-mock container.
Startup branchcodex/integration clean, no HEAD..master commits; README/SESSION/TASKS/Claudehandoff read.
Existing gatewayint28-7b1e458 already serves compute-only/v2 against host.docker.internal8001/stub0.
No new application image build/pull required; current latestaliases resolve to the verified running images.

Changed:
- docker-compose.yml comments and .env.example make default real-AI vs explicit test/CI mock clear.
- docker-compose.mock.yml uses the same APP_IMAGE_TAG/latest convention as gateway; preserved for test/CI, not started.
- Local docker-compose.local.yml no longer defines the phantom ai-mock volumes-only service, so root+local validates with realAI.
  This existing file is intentionally ignored (.gitignore43); local change retained, not force-added or copied into shared configs.
- infra/verify_cold_start.ps1 accepts absent optional orphan containers and compares current image IDs via verifiedlatest aliases,
  supporting gatewayint28 +UI/workerint23 without requiring uniform per-service versiontags.

VERIFIED-NOW:
1. Compose rendered config (captured onlymemory, never logged secrets): root, root+local, root+explicitmock allvalid.
 Root/local have noai-mock and canonicalhost8001/stub0. ExplicitCI remains ai-mock8001/stub1. Current4app images/env unchanged.
2. Apply: `docker compose -p video-ai -f docker-compose.yml up -d --no-deps --no-build --no-recreate --pull never gateway cms client ingest-worker`.
 ActualWSL docker-desktop Compose executable /mnt/host/wsl/docker-desktop/cli-tools/usr/local/lib/docker/cli-plugins/docker-compose;
 DOCKER_HOST=unix:///proc/193/root/run/docker.raw.sock, projectdirectory /mnt/host/e/traning_ai-codex and absolutecomposefile.
 PASS, all4Running/healthy, no recreate. No fullstackdown or automatic --remove-orphans.
3. Verified labels projectvideo-ai/serviceai-mock and exact container ID before mutations.
 `docker stop --time 30 767326f4c37e1d7ac8badebbc09d9d32079fa2e6893089a336116fa6d4e9274d`
 then `docker rm 767326f4c37e1d7ac8badebbc09d9d32079fa2e6893089a336116fa6d4e9274d` PASS.
 Docker warns --time deprecated (use --timeout next time); operation succeeded. No rm-v, volume/image removal, prune, inferencecontainer action.
 Docker CLI /mnt/host/wsl/docker-desktop/cli-tools/usr/bin/docker via sameWSL socket.
4. Exact project/service mock filter returns0containers; port18001closed. AIhost PID15852 unchanged,healthstubfalse/6models/degradedempty;
 gatewayhealth200 minio/milvusok; CMS5173/Client3000 HTTP200. All16othercontainers ID/image/start/state/mount identities unchanged.
 Initial raw mount-array comparison rejected ordering differences; sorted by destination and allidentity assertionsPASS.
5. Cold-start utility PowerShell ASTsyntaxPASS; executed only the read-only preflight prefix (stopped beforeSnapshot/filewrites/stopcommands):
 services12/currentimages/env match, optionaloutsiders2(no mock) PASS. No coldboot repeated, INT-27 historical evidence not overwritten.
6. `E2E_AI_V2_VIDEO=.../int28-natural.mp4 E2E_AI_V2_FRAME=.../int28-query.jpg node node_modules/@playwright/test/cli.js test e2e/ai_v2_live.spec.ts --output=backend/.tmp/int30-e2e --reporter=list`:
 **1PASS20.7s**, aftermockremoval: realuploadprocessed/10vectors/thumbnails/3ASRsegments/145charsdraftsummary,
 ownvideoTOP1score0.9920652/feedpopularity; repeatdelete204/vector0/rawclipthumb404/Mongoanalysisempty.
7. Original99video rows fingerprintdb747ed8a7b3c6580a546b844559b309 and10categoryfingerprint2279cd784f346ec1e52ce40605752c91 unchanged;
 oneownedE2Enewvideo softdeleted, excluded frombefore/after99rowcomparison; activejobs0. No otherdata/volume deletion.
 gitdiffcheckPASS. Application source/API contract unchanged, so no redundantGo/FE builds or dependency downloads.

Evidence: INT-30-before/after/health-before/health-after/preservation/data-before/data-after/compose/apply/mock-remove/cold-preflight/real-e2e/real-counts.
Mock HTTP code/image binary retained for isolatedtest/CI, no mock runtime left. Legacy stopped inferencecontainer remains untouched.
Current AIv2DRAFT release pending remains INT-28 REVIEW; this task does not promote API readiness.

Lane: codex
Changed: root/mockCompose/envexample/coldstartutility; ignoredlocaloverride; ownedcoordination
Verified: 3Composeconfigs, readonlycoldpreflight, mockremoval/portclosed, realE2E1PASS20.7s,16container+AI+data preservation PASS
Contract touched: no (public0.4.1/AIv2DRAFT unchanged)
Next safe task: Claude v2release then normal startup/matrixpromotion; no further Docker rebuild needed for this config-only task
