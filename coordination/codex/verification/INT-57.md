# INT-57 — HC-19 compute-only v3.0 runtime + real gateway acceptance

Owner CODEX. IN_PROGRESS, 2026-11-02. Task startb148b6f. User explicitly authorized receiving master8e6fd39, replacing only inference-service with the provided image without build, removing its storage env/dependencies, full parity and actual new-upload/search gateway checks. This is separate from the earlier blocked broad INT-50/global-flag/eight-screen QA action.

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

## Remaining before DONE

Run actual Playwright newownedupload→processed/v2vision+ASR/retainedhighlight/summary, CMShealth/threshold, backend MinIO+Milvus/search, own publication only as required for search privacy, delete own test video/media/vectors/documents and logout. Then original-data/othercontainer fingerprints and model HTTP path counters must PASS; add RE:HC-19 with evidence+commit. No original-video reprocess/globalflag change/checkpoint change/remote push. Broad CMS full feature/quality acceptance is not implied.

Lane: codex
Changed: inference compose image/env/dependency cleanup; CMS health regression; existing realE2E verifier; owned coordination/evidence
Verified: source/checkpoint/full4video parity, actual compute-only health, Go gates/E2Etypes PASS; new gatewayE2E/preservation pending
Contract touched: no (consumes publishedAIv3.0, public0.8.0 unchanged)
Next safe task: run user-authorized bounded HC-19 real E2E and preservation, then handoff/closure
