# INT-28 — D24 / HC-13 v2 cutover (2026-10-29)

Owner CODEX. IN_PROGRESS, runtime acceptance pending. AI-API v2.0 is DRAFT on Claude branch; not INTEGRATED_REAL/API_READY.

Startup: branch codex/integration, clean, no HEAD..master commits; master26c2346 received.
Read coordination README/SESSION/TASKS/HC-13/V2 contract; skill backend_endpoint +Ponytail. No AI source/runtime/checkpoint change.
INT-29 ef8162b documents deletion409/storage503, regenerates Go/CMS/Client types; both FE tsc/schema tests PASS.

Implemented HC-13 steps1–11:
- Four authenticated mock/v2 routes; Go VisionV2 batches<=600 and sums4class logits; search128 COSINE;
 ASRV2 multipart file/language/offset, PCM16 mono16k, exact600s segmentation; RecommendationEmbeddings with MODEL_NOT_READY preserved.
- Backend JSON payload Milvus REST delete-before-insert batches600, HNSW COSINE ef=max64/topK, Session search,
 threshold filtering/clampedscore, safe quoted delete; both base64JSON (actual2.4) and object payload decoded.
- Existing scalar initializer corrected to payload JSON; no drop/migration/copy of collection. Default init no recommendation collection untilAI-12.
- Shared live/backfill frame indexing uploads JPEG thumbnails/{vid}/{sec:08d}.jpg to backend MinIO; persists Siamese vectors.
 Runner uses v2 and existing256features for v1highlight; audio is stored/re-read in backend, never sent as URL to inference.
- Search route v2embedding->backend ANN->existing publication/privacy recheck and presign; v2cache namespace.
 D18 feed stays primary Postgres popularity; no fake recommendation vectors.
- frame-backfill defaults to read-only inventory, --apply indexes only processed videos absent from frame inventory;
 asserts existing per-video counts unchanged. It changes no metadata. Image includes command.
- Unified DELETE refuses active jobs/cuts, retries storage failures, deletes own vector/raw/audio/thumbprefix/clip/Mongo, hidesclips and softdeletes;
 repeated deletion204. Other video objects preserved. Gateway /healthz probes Milvus/MinIO (503 when unavailable).
 Compose gateway waits healthyMilvus; only optionalfull orchestrator gets missingMILVUS vars/dependency. No AI worker config.

VERIFIED-NOW:
- go vet ./... +go test ./... +go build ./... PASS (INT-28-go-vet-final/final2/build.log).
- Focused final HTTP/Milvus/CMS tests PASS (go-last.log), final ASR boundary test PASS4.364s (asr-boundary.log):
 48kHz input converted to16k, firstWAV data exactly600*16000*2bytes; second requestoffset600, transcriptconcat/segmentIDrenumber.
- Unit checks cover601frames/logitaggregation/unnormalizedViT preservation, multipart/auth/errors422+503,
 JSONpayload parsing/ef100/thresholdclamp/validate-before-delete, thumbnail/vector idempotency,
 activewriter409/storagefailure503/retry/delete scopes/publication-cache recheck.
- E2E TypeScript noEmit and git diff --check PASS. Two initial Go failures retained: missing strings import fixed;
 contract test read oldembedded version during concurrent regen, fixed thenfullgate PASS.
- Real oneframe/v2 smoke: ViT256 normSquared252.20748 (preserve raw for Fusion), Siamese128 normSquared0.99999987.
 This clarifies contract normalized-vector shorthand; no AI behavior change.

Precutover inventory:
- Milvus411 live /49videos, collectionID469752598629451124, JSONpayload128COSINE, original IDs+payload saved
 in INT-28-milvus-before.json and schema-before.json. Full vectors private ignored backup backend/.tmp/int28-milvus-full-before.json
 SHA25614285c13a40729ef2d8224aa9aafab1a1fc83cdddeec66a6594f69d4c9a1ba72.
 REST2.4 JSON field arrives base64; decoded count49 confirmed. No mutation yet.
- PostgreSQL95rows (93deleted/2processed), hashbbcbd9556b3aab1625c2705069565907, activejobs0.
 Processed originals vid_dm3nf6fi23us +vid_dm46jsx30bah. No metadata rewrite.
- MinIO inventory private ignored backend/.tmp/int28-minio-before.json:95raw/47clips/460thumbnails.
- RealAI health stubfalse/6models/degradedempty. C1.98GiB/E1.38GiB; no large dependency/image download.

Next: build offline artifact overlay on current int23-fa8a382 image; recreate gateway only after env/data guards;
 run backfill inventory/apply and real E2E with existing natural speech clip (hue-transformed copy for unique search),
 compare every original vector/object and PostgreSQL rowhash, record RE:HC-13. No push/master release.

## Final live acceptance — PASS (2026-10-29)

Source7b1e458, public contractef8162b. Built five Linux/amd64 CGO0 artifacts with cachedGo1.26.0
(`GOMAXPROCS=1 GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -ldflags='-s -w' -o .tmp/int28-image/<name> ./cmd/<name>`).
Offline overlay recipe/hashes: INT-28-artifacts.json; build --network=none --pull=false, local baseint23-fa8a382, no installs/downloads.
Livegateway binarySHA cd741e3fe2ac4d68794a5c36f989d2cffe729dc133d111c0fc8901eed8a68d85 matches hostartifact.
Image int28-7b1e458 (+verifiedlatest alias); oldint23-fa8a382/rollback-int28 retained.

Commands below used WSL docker-desktop direct clients, DOCKER_HOST=unix:///proc/193/root/run/docker.raw.sock;
Docker CLI /mnt/host/wsl/docker-desktop/cli-tools/usr/bin/docker,
Compose /mnt/host/wsl/docker-desktop/cli-tools/usr/local/lib/docker/cli-plugins/docker-compose.
Compose base arguments `-p video-ai --project-directory /mnt/host/e/traning_ai-codex -f /mnt/host/e/traning_ai-codex/docker-compose.yml`.
Credential read-only from Claude.env into memory; compared every Compose gateway env to current container, no value changed or logged.
AI URL http://host.docker.internal:8001 /AI_ALLOW_STUB0; activejobs0 before mutation.

- `compose ... up -d --no-deps --no-build --pull never --force-recreate gateway`: PASS; onlygateway recreated.
 `/healthz`200 statusok dependenciesminio/milvusok. INT-28-gateway-recreate/deploy/health evidence.
- `docker exec video-ai-gateway-1 frame-backfill --apply`: PASS; all2processed originals already indexed, missing=[] /backfilled=[];
 everyexisting per-video count unchanged411/49. No unnecessary reindex. Default without--apply is read-only.
- `E2E_AI_V2_VIDEO=E:/traning_ai-codex/backend/.tmp/int28-natural.mp4 E2E_AI_V2_FRAME=.../int28-query.jpg
 node node_modules/@playwright/test/cli.js test e2e/ai_v2_live.spec.ts --output=backend/.tmp/int28-e2e --reporter=list`:
 **1PASS14.8s**. Natural speech from documented user original (INT-25), hue37 on an owned copy for unique search; audio copied unchanged.
 Realuploadprocessed, backend10vectors/thumbnails, categoryca_nhac, ASR3nonemptysegments, draftsummary279chars, mainv2ASR multipartoffset0;
 published clip +visualsearch ownvideoTOP1 **0.9920652**; primaryfeedpopularity.
 RepeatedDELETE204; ownMilvus0, raw/clip/thumbnail signedGETs404, Mongoanalysis/subtitle counts0. No editorial writes before AI content checks.
- `node node_modules/@playwright/test/cli.js test e2e/video_flow.spec.ts e2e/visual_search.spec.ts --output=backend/.tmp/int28-regression --reporter=list`:
 **3PASS43.3s**, realCMSedit/approve/publish/Clientplayback, invalidvideo private, realANN/search/privacy/cache/latency/Client.
- Read-only compatibility check outside primarypipeline (completed04:02:36Z): real/v2recommendation503MODEL_NOT_READY;
 /v1search vs/v2embedding+REST ANN identical48video/timestamp hits, maxscoredelta9.754e-9. No fake recommendation collection.
 **One intentional direct /v1/search request** belongs to this comparison, not gateway traffic. INT-28-compatibility.json.
- `docker logs --since 2026-10-29T03:59:35Z video-ai-gateway-1` filteredAIHTTP:
 POST/v2vision,/v2asr,/v2search; only retained/v1highlight and/v1completions. **Zero main/v1vision|search|asr|recommendation calls**.
 INT-28-ai-requests-final.log. RuntimeAI accesslog itself owned by Claude; no reading/editing it required.
- Final all-original Milvus411vectors/49videos have identicalIDs/vectorvalues/payloads against full private precutover backup.
 Collection preserved in place, no drop/copy/compaction; five decodedpayload samples before/after.
 MinIO alloriginal keys/sizes/ETags identical:95raw/47clips/460thumbs, alltestobjects cleaned.
 PostgreSQL original95rowshash bbcbd9556b3aab1625c2705069565907 unchanged;10categoryhash2279cd784f346ec1e52ce40605752c91 unchanged.
 Fourtestuploads nowsoftdeleted/training_origin=test; total99rows(97deleted/2processed), activejobs0.
- Other16containers IDs/images/StartedAt/mount identities unchanged (Client3000/CMS5173/CPUworker/DB/orphanmock/legacyinference/Faktory).
 AI PID15852 unchanged,6real/stubfalse/degradedempty. INT-28-preservation.json validates bothsnapshots.
 Initial PowerShelltimestamp validator encountered string/DateTime type differences; reran snapshot assertions with normalizedUTC timestamps and PASS.
- Fresh initializer nowcreatesJSONpayload +loadsframecollection; skips existingdata and does not create recommendation collection.
 `python -X utf8 -m unittest discover -s infra/milvus -p test_init_collections.py`:1PASS(mockedSDK,no servermutation).
 Existinglive collections only video_frame_embeddings and sandbox_two_tower_ai09_20261026.

Limitations: real speechfixture10.08s;600.1s split/48k->16k alignment verified with synthetic audio, not long natural speech.
Backfill found0missing; no old video was artificially deleted/reindexed just to exercise it. Fresh DB bootstrap validated at schemaunit level, no secondstack.
CMS/Client generatedtypes checked, product UI images unchanged; no fullUIparity/GPU/load/soak/modelquality claim.

Lane: codex
Changed: AIv2mock/client+backendstorage/orchestrator/search/cleanup/health; schema/compose/Dockerfile; focused E2E +ownedcoordination
Verified: Go vet/test/build, focusedboundary/schema/typechecks, real1+3E2E, v1/v2parity, vector/object/PG/runtimepreservation PASS
Contract touched: yes public0.4.1(INT-29); consumedClaudeAIv2.0DRAFT and retainedv1highlight/text, no AI contract edit
Next safe task: Claude release/v2API_READY and/v1fourpathsDEPRECATED; then Codex startup merge+matrix promotion. INT-28 REVIEW, not INTEGRATED_REAL/DONE.
