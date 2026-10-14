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

Compose starts PostgreSQL/MongoDB/Redis/MinIO/Kafka, initializes the five topics, and starts the inference service with all six mounted checkpoints. FORCE_STUB is 0; startup fails if a checkpoint is missing. Go Orchestrator/cutter consumers run in the gateway process with persistent adapters; Python ingest runs separately. The old standalone Go worker binaries are not part of this runtime. Milvus remains a T4.2 dependency; do not enable profile full to claim visual search is ready.

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

Only Vision/ASR/Highlight/Summary inference is wired for this task. Visual search and vector recommendation require a real Milvus index and currently return 503 rather than synthetic hits; gateway feed falls back to real published clips. Preferences/vector state, interactions and dev reset tokens still use memory adapters. Mini-GPT retains its documented T1.6c quality limitation.

Polling follows Playwright [expect.poll](https://playwright.dev/docs/test-assertions#expectpoll).


## T3.2 — Client UI and playback checks

`client_design.spec.ts` and `client_player.spec.ts` cover Stitch layouts at 390×844 and 1440×900, SVG path coverage, auth/errors, onboarding, media controls, transcript/filter/download/rate, search payload/validation, profile and refresh. These are isolated UI fixtures; only `video_flow.spec.ts` uses the real pipeline. Defaults: Client :3000 (`E2E_CLIENT_UI_URL` override).

```powershell
npx playwright test e2e/client_design.spec.ts e2e/client_player.spec.ts e2e/video_flow.spec.ts --output=test-results/client-release --reporter=list
```

Latest verification: 42 passed (1.7 minutes), full Client lint/tsc/Next build and Docker build passed. Real E2E checks feed playback, detail Range seek/playback and approved summary, in addition to upload/processing/privacy/publish. See `docs/T3.2_client_design_parity.md` for source/render screenshots and the remaining contract gaps. UI does not claim original-video playback, saved-list reading, fake counts or real visual-search results when their APIs are unavailable.
