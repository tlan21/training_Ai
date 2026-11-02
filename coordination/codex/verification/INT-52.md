# INT-52 — HC-16 official Docker inference image (2026-11-02)

Owner: CODEX. Status: DONE (scoped deployment, not full CMS E2E). Task start873beb7; deployment/evidence **537f6b1**; handoff/closure commit follows. User explicitly authorized consuming HC-16, changing the existing inference-service compose image without building, preserving the read-only checkpoint bind, recreating only that service, and checking health/clip_threshold.

## Change and deployment

- Branch codex/integration; clean startup; no HEAD..master commits. Task start873beb7. Read current coordination rules, Codex resume/tasks, Claude HC-16/AI-22 and AI-API v1.4 through git show.
- Actual service definition is **docker-compose.inference.yml**, not the root compose. Changed only its image tag and two stale comments. No environment/volume/healthcheck/dependency/port change in YAML.
- Existing local image **video-ai-inference:ai-v1.4-62b7e05**, ID **sha256:53e24af8806570abb38e20b55622e97348ebbc33669f6590a5f319f3c4186254**, revision **62b7e0501cba80edcebaf3d7aad0a764d6494a9f** matches HC-16 exactly. No image build, pull, retag, checkpoint copy or AI source edit.
- Docker Engine28.4.0 already running; no engine repair/start, host inference process action or alternate port/container launcher. Baseline captures16existing containers, active video jobs0.
- Existing configured credentials read from the running container into child-process memory only. Compose config JSON captured in RAM and reduced to sanitized assertions; no key/raw environment committed or printed.
- Effective config validation: pinned image, no build, no published port, same configured env/command, checkpoint host directory **E:/traning_ai/ai-core/checkpoints**, target **/srv/ai-core/checkpoints**, read_only=true and create_host_path=false.

Executed in E:/traning_ai-codex:

```text
docker compose -p video-ai -f docker-compose.yml -f docker-compose.inference.yml -f docker-compose.cms-completion.yml config --format json
docker compose -p video-ai -f docker-compose.yml -f docker-compose.inference.yml -f docker-compose.cms-completion.yml up -d --no-deps --no-build --pull never --force-recreate inference-service
```

The first command's raw output is deliberately not logged because it contains resolved credentials. The second exited0 and reported Recreate/Recreated/Starting/Started for **video-ai-inference-service-1 only** (INT-52-recreate.log).

## VERIFIED-NOW results

| Check | Result / evidence |
|---|---|
| Docker health + actual GET http://127.0.0.1:8001/health inside inference container | PASS: healthy, status=ok, stub_mode=false, six models asr_ctc/highlight_fusion/minigpt/siamese/two_tower/vit, degraded=[], load_error=null, device=cpu, visual_index=ok |
| Authenticated HTTP POST /v1/highlight/completions | **200, clip_threshold=51.0**, three timeline seconds, zero recommended clips. Input is the published master highlight.request.json fixture with diagnostic video_id only; API service performs real inference, no product record/analysis write. Zero proposals is expected for this <120s request. |
| Pinned source integrity | **103 files** in container app/ai_core match git blobs at image revision62b7e05, no missing/extra/mismatch; CRLF normalized as in Claude parity.py. |
| Checkpoint/recipe integrity | **10 files SHA256 match Claude AI-22 parity report exactly**: six best.pt plus vocabulary, postproc recipe and two ensemble members. Existing bind remains read-only; no weights copied/changed. |
| Other containers | **15 unchanged**: IDs, image IDs/tags, start times, state, env hashes, commands, mounts and published ports match baseline. Only inference container ID replaced. Includes existing gateway/CMS/Client/worker/databases and outsiders/exited containers. |
| Configured inference environment | All configured keys/values unchanged, including credentials, FORCE_STUB=0, INFER_DEVICE=cpu, CHECKPOINT_DIR and existing compatibility dependencies. Old full env reconstructed from old image defaults+same configured values matches baseline hash exactly. |
| Gateway health / job safety | GET http://127.0.0.1:8000/healthz **200**; active jobs before/after0. Gateway not recreated. |
| Compose diff/whitespace | Same service mount/env/command preserved; git diff --check PASS. |

Evidence: INT-52-before.json, INT-52-config.json, INT-52-recreate.log, INT-52-runtime.json, INT-52-after.json. Commands/assertions executed via standard-library Python subprocess/docker exec; keys never passed in printed command arguments. Internal HTTP checks use the container's own AI_SERVICE_KEY environment.

## Representation differences and corrected verification attempts

- First config guard stopped **before recreation** because Compose JSON omits false create_host_path. Corrected the guard to accept the omitted false value; YAML remains explicitly false. Deployment ran once after guards passed.
- Initial post-deployment whole-env/mount equality was stricter than effective configuration. The new pinned image's **PYTHON_VERSION3.11.17→3.11.18 and PYTHON_SHA256** metadata differ from its old base. These are image defaults, not changed Compose settings; no attempt was made to falsify them or rebuild the parity-verified image. Reconstructed baseline proves all application-configured env unchanged.
- Windows Compose reports source **E:/traning_ai/ai-core/checkpoints** where the old WSL-created container reported **/run/desktop/mnt/host/e/traning_ai/ai-core/checkpoints**. Canonical host directory/target/RW=false and all ten actual file hashes match. No directory/weight copy or new mount target. Other-container preservation compares actual values without this target-only alias normalization.

## Limits and next action

This closes the **runtime image/code/recipe mismatch portion of HO-04**. Claude already proved four real-video host/container parity for this exact image and identical checkpoint hashes (HC-16/AI-22); Codex did **not rerun the full four-video in-process host parity.py**. Current proof is actual service health, real authenticated highlight threshold, source and mounted-file integrity. This fixture is not a model-quality, long-video E2E or GPU/load/soak acceptance.

No stored scores/proposals or old videos were reprocessed. Existing recommendation_index=missing_collection remains expected; no personalized recommendation or /v2 API_READY promotion. Public OpenAPI and AI API schema unchanged.

Docker Engine blocker from INT-50 is now resolved, but explicit approval for its previously policy-rejected real-QA creation/run is still pending. Title correction7c7dd74 is still not deployed (CMS74344bb left untouched). Full new-threshold backend persistence/CMS checks belong to approved new QA work, never automatic reprocessing of original media. No new master release/push in this scoped deployment task.

Lane: codex
Changed: docker-compose.inference.yml image/comments; owned tracker/session/matrix/handoff/evidence
Verified: actual six-real-model health, authenticated clip_threshold51, 103source/10checkpoint recipe parity, 15other containers unchanged, gateway200/jobs0
Contract touched: no (published AI-APIv1.4 consumed; v2DRAFT remains)
Next safe task: INT-50 after explicit approval of its rejected real-QA action; retain existing data/quality gates
