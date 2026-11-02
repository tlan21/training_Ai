# INT-57 — HC-19 compute-only v3.0 runtime + real gateway acceptance

Owner CODEX. DONE, 2026-11-02. Task startb148b6f; deployment/test/parity source **11584c5**; actual E2E/preservation/handoff closure in this commit. User explicitly authorized receiving master8e6fd39, replacing only inference-service with the provided image without build, removing its storage env/dependencies, full parity and actual new-upload/search gateway checks. This is separate from the earlier blocked broad INT-50/global-flag/eight-screen QA action.

Startup: fetched origin, clean codex/integration fast-forward36b8a1f→8e6fd39 (release#7), no incoming Codex source changes. Read current coordination rules/Claude handoff/AI contracts. Existing inference definition is docker-compose.inference.yml, not root; only that service is edited. No manual Claude-file change.

## Completed rollout/parity checkpoint

- Exact existing image **video-ai-inference:ai-v3.0-48735ff**, ID **sha256:f62671e78fd8bb4ba9fad3fb743ea4ab3aeb76723e76abd821afe0c336837b81**, revision **48735ffbfda20914976b4206f6ca91f0ecda5ca9** verified before deployment. No build/pull/retag.
- Removed only inference MILVUS_HOST/MILVUS_PORT/MINIO_ENDPOINT/MINIO_ACCESS_KEY/MINIO_SECRET_KEY and its depends_on milvus/minio. Kept AI key, CPU/device/checkpoint/stub0, exact existing read-only checkpoint directory, command and healthcheck. Gateway/backend storage env and dependencies are untouched.
- Captured read-only originals:119videos/61clips/51users/10categories/119jobs/67interactions/8settings; Mongo5analyses+5subtitles; MinIO97raw/52clips/550thumbobjects; Milvus671vectors;16containers including outsiders/exited; activejobs0. Fingerprints contain row/document/object/vector hashes, no credentials/media/text. INT-57-preservation.py asserts original rows and only new own tombstones after cleanup.
- Guarded effective config in RAM; raw resolved env never logged. Command exited0 and recreated **inference-service only**:

```text
docker compose -p video-ai -f docker-compose.yml -f docker-compose.inference.yml -f docker-compose.cms-completion.yml up -d --no-deps --no-build --pull never --force-recreate inference-service
```

- Actual /health:6models/stub_modefalse/degraded[]/load_errornull/CPU/**dependencies={}**. Four removed paths absent from current OpenAPI; no negative endpoint probes were sent, so later pipeline log counters can assert zero calls.
- Full official parity.py from master (Gitblob unchanged versus the existing INT-54 transport runner) executed with Claude venv/host reference computation and existing-container HTTP, no host server/newport/newcontainer/checkpoint copy. **101source files**,10checkpoint/recipe/vocabfiles match; news1245/1480s and soccer2700/2700s allmaxdiff**0.0**, identical clip intervals/threshold**51**. Both full reports/logs retained as INT-57-parity-news/soccer.json/log.
- Health client/CMS already ignore removed index keys; no production fix needed. Added a regression upstreamHTTP→realGoAIclient→CMShealth proving dependencies{} still ai_availabletrue/sixmodels. Focused tests2PASS0.258s; full Go vet/test/build PASS (INT-57-go.log); E2E types PASS. No gateway/CMS/Client/worker recreation or new app build required.
- Updated existing ai_v2_live.spec.ts to use current cross-platform dockerCLI, optional compute-only health/threshold checks, actualCMSsystemhealth, owned evidence path and logout of its own session. Existing natural-speech/query fixtures reused; no new dependencies. Legacy Go compatibility methods/mocks intentionally retained (optional cleanup), production caller proof INT-55 remains.

Corrected early verification attempts: baseline initially queried nonexistent interactions table; readonly query failed before any deploy/QA and was fixed to actual user_interactions before baseline capture. Initial immediate health check encountered connection-refused while Docker health=starting; bounded retry then passed, no additional recreation. No falsePASS recorded for those attempts.

## Actual real gateway E2E — VERIFIED-NOW

Ran the existing updated test against current gateway8000 and v3DockerAI; no browser/API response mocks, no new QA server or other service restart:

```text
E2E_GATEWAY_URL=http://127.0.0.1:8000
E2E_AI_DOCKER_CONTAINER=video-ai-inference-service-1
E2E_AI_EXPECT_COMPUTE_ONLY=1
E2E_AI_V2_VIDEO=E:/traning_ai-codex/backend/.tmp/int28-natural.mp4
E2E_AI_V2_FRAME=E:/traning_ai-codex/backend/.tmp/int28-query.jpg
E2E_AI_EVIDENCE_FILE=E:/traning_ai-codex/coordination/codex/verification/INT-57-e2e-counts.json
node node_modules/@playwright/test/cli.js test e2e/ai_v2_live.spec.ts --output=backend/.tmp/int57-e2e --reporter=list
```

**1 PASS16.8s**, test15.5s, no retry. Natural-speech10.08s fixture uploaded as new **vid_dmkgihquce5o** → job completed/video processed. Actual CMS/systemhealth200/ai_availabletrue/sixmodels with AIdependencies{}. Categoryca_nhac, **3nonempty ASRsegments**, summary204characters/statusdraft, timeline populated/**clip_threshold51**, **10backend-written vectors** and private thumbnail/raw/clip URLs200.

Own manual3sclip created/reviewed/published only to satisfy real search visibility; visualsearch by fixtureframe returns ownvideo **top1score0.99206525** through /v2/search/embeddings and backendMilvus. Feedmodepopularity. This is a fresh actual upload/persistence/search/cleanup check, not the historical feature-only parity proof and not model-quality acceptance.

## Cleanup, original-data preservation and HTTP paths

- Test deletes only its own newvideo, repeatsDELETE204, verifies ownvectors0, all3ownmediaURLs404 and ownMongoanalysis empty; own auth session logged out204. Newmetadata tombstones retained by product design: video vid_dmkgihquce5o, clip clp_dmkgimbbupej and its job; no manual SQL deletion.
- After counts:120videos/62clips/51users/10categories/120jobs/67interactions/8settings. **Every pre-existing row hash/ID in the seven monitored business/settings tables unchanged**; only ownvideo/clip/job rows added. No setting/role/category/globalflag change.
- Both Mongo collections return to **5+5original documents**, hashes equal. All original MinIO **97raw/52clip/550thumbnail** key/size/ETags identical, no extra QAobjects. All **671original Milvus vector IDs/values/payloads identical**, no extra QA vector, no drop/reindex.
- **15other containers unchanged**: IDs/images/start/state/envhash/command/mounts/ports. Only inferenceID replaced; its remaining envhash equals oldenv minus the5explicitly removed storage keys, same command/checkpointbindRO/ports. Activejobs0before/after. No gateway/CMS/Client/worker/database recreation.
- Actual gateway log since ready: **one each** /v2/vision/completions, /v2/asr/completions, /v1/highlight/completions, /v1/completions and /v2/search/embeddings; /health1. Inference logs include the same plus4official parity highlight calls. **0 calls to all four removed paths** in gateway/ingest/currentAI logs, not merely absence in source. No negative404probes were mixed into that window.

Artifacts: INT-57-e2e-counts.json, -real-e2e.log, -after.json, -runtime-paths.json and the earlier baseline/config/runtime/fullparity/Go logs. Preservation helper reads only; assertions checked. The source changes between tested11584c5 and closure are evidence/coordination only. No full CMS UI/flag-matrix/GPU/load/soak acceptance or checkpoint/oldanalysis reprocess, and no remote push. Optional legacy Go client/mock cleanup deferred because current production has no callers (INT-55 and actualv3E2E prove it); future API removals in tests can be scoped separately.

Lane: codex
Changed: inference compose image/env/dependency cleanup; CMS health regression; existing realE2E verifier; owned coordination/evidence
Verified: source101/checkpoint10/full4video parity, compute-only CMS/AIhealth, Go gates/E2Etypes, actualnewgatewayE2E1PASS16.8s, originaldata/15othercontainers/HTTPpath proof PASS
Contract touched: no (consumes publishedAIv3.0, public0.8.0 unchanged)
Next safe task: separate approved CMS QA or future versioned AI handoff; HC-19 scoped acceptance complete
