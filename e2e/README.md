# Runtime sau Release #1 (2026-10-26)

Claude sở hữu inference thật :8001 và checkpoint. Compose của Codex không dựng inference;
`AI_BASE_URL=http://host.docker.internal:8001`, `AI_ALLOW_STUB=0` mặc định.
Dùng `docker-compose.mock.yml` cho phát triển độc lập (MOCK_ONLY, không nghiệm thu AI thật):

```powershell
docker compose -f docker-compose.yml -f docker-compose.mock.yml config --quiet
docker compose -f docker-compose.yml -f docker-compose.mock.yml up -d --build gateway ingest-worker cms client
```

Giữ project hiện hữu `video-ai` và volume `video-ai_*`. Đo C:/E: trước build/pull;
không chạy build khi không đủ chỗ. Xem `coordination/codex/verification/INT-00.md` cho cách dùng image cũ + binary mới
trong môi trường thiếu tài nguyên. Ingest tạm dùng image preprocessing cũ đã cache, không khởi chạy inference hoặc mount checkpoint.
`docker-compose.gpu.yml` là override cũ đã nghỉ; GPU của runtime thật do Claude cấu hình ở worktree của Claude.
Các lệnh `inference-service`/GPU ở phần lịch sử bên dưới không áp dụng cho stack Codex hiện tại.

E2E AI thật T4.1/T4.2 chờ AI-01 API_READY + AI-07; test đi qua mock chỉ là bằng chứng MOCK_ONLY.

---

# T4.1 — Real video pipeline

Run from the repository root in PowerShell:

```powershell
docker compose --env-file .env -f docker-compose.yml up -d --build gateway cms client ingest-worker
docker compose --env-file .env -f docker-compose.yml ps
npm ci
npx playwright install chromium
npm run test:e2e:types
npm run test:e2e -- e2e/video_flow.spec.ts
./e2e/verify_persistence.ps1
```

Compose starts PostgreSQL/MongoDB/Redis/MinIO/Kafka, initializes the five topics, and starts the inference service with all six mounted checkpoints. FORCE_STUB is 0; startup fails if a checkpoint is missing. Go Orchestrator/cutter consumers run in the gateway process with persistent adapters; Python ingest runs separately. The old standalone Go worker binaries are not part of this runtime. T4.2 now starts etcd/Milvus by default; its real visual-search verification is documented below.

Targets: gateway http://localhost:8000, CMS http://localhost:5173, Client http://localhost:3000. E2E_GATEWAY_URL, E2E_CMS_URL, E2E_CLIENT_URL can override these. E2E_PROCESS_TIMEOUT_MS defaults to 90000.

The browser test logs in, onboards a unique viewer, uploads a valid 8-second MP4 padded to over 16 MiB, waits for real processing, checks draft privacy, approves the edited summary, cuts/publishes a clip, and checks the same viewer's cached feed. It fetches 1024 bytes from the real MinIO playback URL and expects HTTP 206. The second test uploads invalid bytes, expects a failed job, and checks public video/analysis return 404. No HTTP interception or processed/published state seeding is used.

Real AI may produce no recommended peaks above 75. The test then uses an editor-selected 0–5 second range; it does not invent an AI recommendation. Clip average_score comes from the real timeline, weighted for fractional seconds.

verify_persistence.ps1 uploads a clearly named T4.1-REAL-AI-SMOKE sample, waits for processing, restarts only gateway, and asserts video/timeline/subtitles/summary and the CMS proxy still work. It intentionally keeps this draft for inspection and writes evidence without auth tokens into ignored test-results/persistence-smoke.json.

Other E2E runs reject only their own clips and soft-delete only their own videos on completion/failure. Test viewers remain because the contract has no user-delete endpoint. MinIO objects remain under soft deletion. HTML reports/traces are gitignored and may contain test auth tokens.

Fixture fixtures/video.mp4 is a synthetic 8-second 160×90 pattern with a 440Hz tone, H.264/AAC, 79,723 bytes. Regenerate:

```powershell
ffmpeg -f lavfi -i testsrc=size=160x90:rate=10 -f lavfi -i sine=frequency=440:sample_rate=16000 -t 8 -c:v libx264 -pix_fmt yuv420p -g 10 -c:a aac -movflags +faststart -y e2e/fixtures/video.mp4
```

Limits: upload file maximum is 2 GiB. Nginx allows 2049 MiB request bodies for multipart overhead; gateway enforces file size, keeps at most 8 MiB of multipart data in memory, and streams to MinIO. Processing still needs temporary disk space. The current machine runs CPU inference; this is not a CUDA/VRAM or full 2-GiB stress test.

T4.1 originally wired Vision/ASR/Highlight/Summary only. T4.2 now wires real Siamese/Milvus visual search (see below). Vector recommendation still returns 503 rather than synthetic hits; gateway feed falls back to real published clips. Preferences/recommendation vectors, interactions and dev reset tokens still use memory adapters. Mini-GPT retains its documented T1.6c quality limitation.

Polling follows Playwright [expect.poll](https://playwright.dev/docs/test-assertions#expectpoll).


## T3.2 — Client UI and playback checks

`client_design.spec.ts` and `client_player.spec.ts` cover Stitch layouts at 390×844 and 1440×900, SVG path coverage, auth/errors, onboarding, media controls, transcript/filter/download/rate, search payload/validation, profile and refresh. These are isolated UI fixtures; only `video_flow.spec.ts` uses the real pipeline. Defaults: Client :3000 (`E2E_CLIENT_UI_URL` override).

```powershell
npx playwright test e2e/client_design.spec.ts e2e/client_player.spec.ts e2e/video_flow.spec.ts --output=test-results/client-release --reporter=list
```

Latest verification: 42 passed (1.7 minutes), full Client lint/tsc/Next build and Docker build passed. Real E2E checks feed playback, detail Range seek/playback and approved summary, in addition to upload/processing/privacy/publish. See `docs/T3.2_client_design_parity.md` for source/render screenshots and the remaining contract gaps. UI does not claim original-video playback, saved-list reading, fake counts or real visual-search results when their APIs are unavailable.

## T4.2 — Real visual search

Default Compose now starts etcd/Milvus; no `--profile full` is needed. Six mounted checkpoints and the same `AI_SERVICE_KEY` in gateway/inference are required. Inference loads the Siamese 128d HNSW COSINE index before becoming healthy. Ports 19530/9091 are bound to localhost. The Go gateway retains the existing public OpenAPI/ports.

```powershell
docker compose --env-file .env -f docker-compose.yml up -d --build gateway inference-service ingest-worker cms client
npm run test:e2e:types
npx playwright test e2e/visual_search.spec.ts e2e/video_flow.spec.ts --output=test-results/t42-final --reporter=list
```

`visual_search.spec.ts` uploads its own distinctive 8-second test video, waits for actual Vision/Siamese/ASR/Fusion/Mini-GPT processing, checks it is hidden before clip publication, publishes a real FFmpeg clip, and uploads an actual matching frame through the API/Client. It validates similarity, real MinIO thumbnail bytes, mobile/desktop results, reject/delete privacy, and 20 cache misses + 20 cache hits all under 2 seconds. Metrics and screenshots are written to the test output directory. It cleans up only its own test data. Fixtures `visual-video.mp4`/`visual-query.png` are a hue-shifted testsrc2 H.264/AAC video and its first PNG frame; they are test data, not model-generated evidence of semantic accuracy.

New canonical ingest keyframes are indexed inside the existing Vision stage; index failure fails/retries that stage. For **explicit processed IDs obtained from CMS** already present before T4.2:

```powershell
docker compose --env-file .env -f docker-compose.yml exec inference-service python -m app.index_frames vid_...
```

The backfill tool reads MinIO originals if scratch frames were removed, reuses ingest sampling, replaces that video's vectors without changing its metadata/summary, and removes its own temporary files. Do not supply deleted/processing IDs. It does not publish content. Results require a processed video with at least one published clip; no such clip means no public search hit.

Unit tests use stub/mocks separately from real E2E. Run the real, read-only HNSW sweep on the retained corpus:

```powershell
docker compose --env-file .env -f docker-compose.yml run --rm --no-deps -e T42_INTEGRATION=1 -v E:/traning_ai/inference-service/tests:/srv/inference-service/tests:ro inference-service sh -c 'pip install --quiet pytest httpx && python -m pytest tests/test_milvus_integration.py -q -s'
```

This flushes/loads the collection, compares HNSW with exact cosine on stored vectors, and checks real index progress. It does not insert/delete user data. See `docs/T4.2_bao_cao.md` for the measured corpus, consistency choice, cache policy and limits. Original-video/saved-list API gaps and T4.3 VRAM/load tests remain separate tasks.

## T4.3 — Sequential inference memory

`inference_memory.spec.ts` is opt-in (`E2E_MEMORY_RUN=1`), with two warmups and twenty sequential private uploads. It samples inference/gateway/ingest RSS and process high-water marks, verifies real completed jobs/analysis, and cleans only its own uploads/vectors. Container ID/start-time/restart-count must stay unchanged. `INFERENCE_MEMORY_TRACE=1` must be enabled before starting the inference container so per-stage peaks can be collected; no API schema extension is used.

```powershell
$env:INFERENCE_MEMORY_TRACE='1'
docker compose --env-file .env -f docker-compose.yml up -d --build --wait --wait-timeout 60 inference-service ingest-worker
$env:E2E_MEMORY_RUN='1'
npx playwright test e2e/inference_memory.spec.ts --output=test-results/t43-memory --reporter=list
Remove-Item Env:INFERENCE_MEMORY_TRACE
docker compose --env-file .env -f docker-compose.yml up -d --no-deps --wait --wait-timeout 60 inference-service
```

`E2E_MEMORY_VIDEO` can supply a local real video instead of the second synthetic 8-second fixture. The recorded local run alternated an 8-second fixture and a private copy of the user's existing 10.08-second source. The original user upload is unchanged. Tests intentionally reuse fixed shapes, do not publish content, and leave soft-deleted DB/MinIO test objects according to the existing cleanup policy.

Local result (2026-10-14): **CPU 20/20 PASS, VRAM NOT_MEASURED**; Intel UHD 630 only, Docker NVIDIA probe fails. Inference RSS first/last five median 569.26/569.87 MiB, OS peak 589.51 MiB; 27 Python tests PASS and real T4.1/T4.2 regressions 3 PASS. These finite short-video measurements do not establish GPU or long-video memory safety. See `docs/T4.3_bao_cao.md` and JSON metrics.

On an NVIDIA host, use the validated `docker-compose.gpu.yml` override (CUDA image build/execution remains unverified on this CPU host):

```powershell
docker compose --env-file .env -f docker-compose.yml -f docker-compose.gpu.yml up -d --build --wait inference-service ingest-worker
$env:E2E_MEMORY_RUN='1'
$env:E2E_REQUIRE_CUDA='1'
npx playwright test e2e/inference_memory.spec.ts --output=test-results/t43-cuda --reporter=list
```

The CUDA guard fails before uploads if health is CPU. Metrics keep allocated/reserved/peak CUDA memory separate and also sample NVIDIA card usage. Never treat CPU `gpu_vram_used=0` as a pass of the 4-GiB requirement. T4.3 remains PARTIAL until actual GPU evidence is available.
