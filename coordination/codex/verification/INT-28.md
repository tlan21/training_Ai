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
