# INTEGRATION_MATRIX — AI endpoint × nơi tích hợp (owner: Codex)

Trạng thái: `MOCK_ONLY` (chỉ chạy với mock/stub) · `REAL_PENDING` (code gọi thật nhưng chưa có integration test thật PASS) ·
`INTEGRATED_REAL` (integration test gọi :8001 thật, `stub_mode=false`, PASS — ghi lệnh + ngày) · `(HIST)` = bằng chứng trước tách làn.
Chỉ `INTEGRATED_REAL` với endpoint `API_READY` trên `master` mới được tính DONE (README mục 5).

Bản đầu do Claude khởi tạo 2026-10-26 từ INVENTORY; từ đây Codex tự cập nhật.

| AI endpoint | Contract | Nơi gọi (Go) | Màn/flow | Trạng thái | Bằng chứng |
|---|---|---|---|---|---|
| `POST /v1/vision/completions` | v1.3 API_READY | Legacy HTTP client only; gateway runtime removed under INT-28 | Upload → category suggestion (CMS Highlight/Video) | HIST — retired from runtime (Claude deprecation pending) | 2026-10-27 T4.1 real upload/category PASS; `verification/INT-11-real-e2e.log` |
| `POST /v1/asr/completions` | v1.3 API_READY | Legacy HTTP client only; gateway runtime removed under INT-28 | Subtitles CMS + Client video detail | HIST — retired from runtime (Claude deprecation pending) | 2026-10-27 T4.1 real pipeline/subtitles PASS; same log |
| `POST /v1/highlight/completions` | v1.3 API_READY | orchestrator stage highlight (`runner.go` clamp clip ≤ duration) | Heatmap CMS/Client, AI clips | INTEGRATED_REAL | 2026-10-27 T4.1 real timeline/publish/playback PASS; same log |
| `POST /v1/completions` | v1.3 API_READY | orchestrator stage summary; `handlers/cms/videos.go` regenerate | Summary review CMS, Client (chỉ approved) | INTEGRATED_REAL — model quality remains AI-03 | 2026-10-27 T4.1 real draft/editor approval/privacy PASS; regenerate route not separately exercised |
| `POST /v1/search/completions` | v1.3 API_READY | Legacy HTTP client only; gateway runtime removed under INT-28 | Client visual search | HIST — retired from runtime (Claude deprecation pending) | 2026-10-27 T4.2 real index/search/privacy/cache/Client PASS; same log + `INT-11-visual-latency.json` |
| `POST /v1/recommendation/completions` | v1.3 DRAFT | Legacy HTTP client only; gateway runtime removed under INT-28 | Client feed | HIST — retired from runtime (Claude deprecation pending) | INT-03/AI-12 product vectors and production gate pending; live `recommendation_mode=popularity` verified |
| `GET /health` | v1.3 API_READY | `handlers/cms/system.go` (`/api/cms/system/health`); gateway startup check | CMS Dashboard/Settings | INTEGRATED_REAL | 2026-10-27 startup/authenticated system health6 + host stubfalse PASS; `INT-11-live-health.json`, `INT-11-final-runtime.json` |
Release#3 AI-API v1.3 đã nhận từ masterfee83b2 qua merge35cd1a9. Six API_READY endpoints now have real HTTP integration evidence; recommendation remains DRAFT. Public OpenAPI0.3.1 unchanged.

Latest regression2026-10-27 after public0.3.2 cursor contract +gateway e476005: **4realE2E PASS1.6m** (new pagination +all3video/search cases).
Gateway keeps canonicalreal/stub0/6models; primary feed remains popularity. Allsix real endpoint rows retained; no personalized/model quality promotion.
Evidence verification/INT-14-pagination-real-e2e.log +INT-14-pagination-runtime.json. Earlier public0.3.1 references below describe prior checkpoints.

## Current real gate — 2026-10-27
- User explicitly approved switching to real AI. Gateway only recreated, canonical `http://host.docker.internal:8001`, `AI_ALLOW_STUB=0`, shared Bearer key passed in process environment only; no Claude code/checkpoint/mount changes.
- `E2E_GATEWAY_URL=http://127.0.0.1:8000 E2E_AI_URL=http://127.0.0.1:8001 node node_modules/@playwright/test/cli.js test e2e/video_flow.spec.ts e2e/visual_search.spec.ts --reporter=list`: **3 PASS / 54.3s**, no retry/mock.
- Host health stubfalse/6models/degradedempty, authenticated gateway health6, missing Bearer401. Real Kafka/own CPU worker/MinIO/AI/Milvus/cutter/CMS/Client used.
- Cold visual20: p95 150.87ms/max178.14ms; warm20: p95 11.74ms/max13.97ms. All below2s; this small sequential sample is not load/soak acceptance.
- Final gateway healthy/real; all3 exact fixture videos softdeleted, publication/cache privacy tests PASS. Real model quality/GPU/personalized readiness not claimed.
- Sections below retain historical mock/transport checkpoints and are superseded by this current gate.

## INT-00 hiện tại (2026-10-26)
- Unit HTTP round-trip đủ 6 endpoint + health với mock: `cd backend; $env:GOMAXPROCS='2'; go test -p 1 ./...` PASS.
- Health mock: `stub_mode=true`, `models_loaded=[]`; chỉ client opt-in `AI_ALLOW_STUB=1` chấp nhận.
- Bằng chứng HIST giữ nguyên; không có tích hợp thật mới. Stack/gateway smoke đang chuẩn bị; xem `verification/INT-00.md`.

## Latest gate checkpoint —2026-10-26
- v1.2 optional video_id consumed atfae980c; latest gateway binary rebuilt/deployed. Media transport + recommendation503 fallback,
  runtime preferences/history/likes/settings persistence + restart/playback206/privacy PASS with MOCK_ONLY.
- Host :8001 health200/stub_mode=false/6models; missing-Bearer401 PASS. Release#2 on master and consumed, so contract gate is satisfied.
- Actual real gateway deployment failed startup health: host.docker.internal:8001 timeout. Independent ingest-worker TCP request likewise times out.
  Both Windows Desktop named pipes also hang; direct daemon Linux CLI works. HO-03/user Desktop restart decision pending.
- Gateway restored explicit mock health200. Real upload/search E2E NOT_RUN (preflight blocked), no new INTEGRATED_REAL entry.
  Evidence verification/INT-11-real-health.json + INT-11-real-blocker.json.

## 2026-10-29 verification refresh — no API/model-quality status inflation
- Canonical gateway/key matched read-only Claude env; realAIstubfalse6/degraded[] and startup realURL verified; no repeated switch/recreate.
- Real10.08s existing user-media content gate1PASS24.6s before ANY editor writes: categoryca_nhac,10timeline seconds, summary123chars/draft,
  ASR3nonempty segments. Evidence verification/INT-25.md /INT-25-user-content-counts.json /INT-25-user-content-final.log.
  Synthetic nonspeech content failures retained separately; they do not invalidate successful protocol HTTP responses or count as contentPASS.
- Actual protocol/publish/Client flow1PASS42.9s after cold startup. Search keeps its existing historical real evidence; not separately rerun today.
- Real recommendation503 and live feedprimarypopularity verified separately; optional fallback modes5unit subcases PASS, not a live personalized-ready claim.
- Existing six API_READY INTEGRATED_REAL rows remain supported; recommendation staysDRAFT/REAL_PENDING. Human review/modelquality gates unchanged (D23).


## D24 / INT-28 live v2 cutover — 2026-10-29

| AI endpoint | Contract | Runtime | Status | Evidence |
|---|---|---|---|---|
| POST /v2/vision/completions | v2.0 DRAFT | runner +backend MinIO/Milvus | REAL_PENDING — live PASS, awaiting API_READY/master | INT-28 real1+3E2E,10vectors/thumbnail,411oldvectors preserved |
| POST /v2/search/embeddings | v2.0 DRAFT | gateway->backend COSINE ANN->PG privacy->presign | REAL_PENDING — live PASS, awaiting API_READY/master | ownTOP1 .9920652; same48hits asv1/maxdelta9.754e-9; searchprivacy/cacheClientPASS |
| POST /v2/asr/completions | v2.0 DRAFT | backend MinIO bytes->PCM16/16k/mono600s multipart | REAL_PENDING — live PASS, awaiting API_READY/master |3nonempty naturalspeechsegments; exact600s/offset testPASS |
| POST /v2/recommendation/embeddings | v2.0 DRAFT/AI-12 pending | typed client only; MVPfeed PGpopularity | REAL_PENDING — MODEL_NOT_READY503 | nofakecollection/vectors; actualfeedpopularity |

Retained v1highlight/text +health API_READY remain INTEGRATED_REAL, refreshed by INT-28 real regression.
Four legacy v1 clients retained for compatibility tests only; no primaryruntime calls aftercutover.
V2mocktested and actualrealcheckpoint E2E passed, but **not INTEGRATED_REAL/DONE** until Claude releases API_READY onmaster.
Backendhealth nowowns MinIO/Milvus; AI dependencies can be removed by Claude afterrelease. No AI contract/checkpoint change byCodex.


Runtime update2026-10-29 INT-31: user-requested realDockerAI nowprimary viahttp://inference-service:8001;
 unmodifiedClaude478052e,6checkpointSHAs unchanged, Dockerstubfalse6CPU/degradedempty, strictDockerhealth +4realE2E PASS1.2m.
 Evidence verification/INT-31.md/counts/runtime/log/preservation. HostClaude8001 untouched, no runtime mock.
 /v2 rows remainREAL_PENDING awaitingClaudeAPI_READY release; retainedv1highlight/text refreshed onDocker. No AI contract/quality promotion.
