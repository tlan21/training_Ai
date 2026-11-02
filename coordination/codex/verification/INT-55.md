# INT-55 — HC-17 production runtime legacy AI path confirmation (2026-11-02)

Owner CODEX. User permits **remove or confirm** gateway/ingest no longer call /v1/vision|asr|search|recommendation. Selected confirmation-only: production already migrated; no application code deletion, endpoint change, gateway/worker recreation or product-data write is necessary. Keep permitted /v1/highlight/completions and /v1/completions.

## Source reachability and deployed provenance — VERIFIED-NOW

| Production flow | Actual call / behavior | Evidence |
|---|---|---|
| Gateway → Kafka orchestrator vision/backfill | IndexVideoFrames→VisionV2; fallback without storage also VisionV2 | backend/internal/orchestrator/frames.go:21; runner.go:261; aihttp/v2.go posts /v2/vision/completions |
| Gateway orchestrator ASR | Downloads existing backend-owned audio, ASRV2 sends PCM/WAV multipart with600s chunks/offset | runner.go:304; aihttp/v2.go posts /v2/asr/completions |
| Gateway visual search | SearchEmbedding→backend Milvus COSINE search→PG privacy→presign | handlers/search.go:102; aihttp/v2.go posts /v2/search/embeddings |
| Gateway feed | NewContentHandlers constructor's AI argument is **nil**, Feed returns immediately to PostgreSQL popularity | cmd/gateway/main.go:77; handlers/content.go:59; no AI recommendation request |
| Python ingest | Local PyAV/audio DSP, MinIO and Kafka only; no model HTTP endpoint/auth configured | packaged main.py matches Git blob; AST imports contain no requests/httpx/urllib/aiohttp; no AI endpoint/key environment |
| Retained AI stages | Highlight→/v1/highlight/completions, summary/regenerate→/v1/completions, health→/health | expected permitted contract paths, unchanged |

- Actual running gateway **video-ai-gateway:int50-74344bb**, /usr/local/bin/gateway SHA256 **4bf998f5d44aeaa87715d22a76e17e8eba5e687c66fa20d17c98680f33720392**, equals committed INT-50-rollout.json binary proof. `git diff 74344bb HEAD -- backend` **empty**. Current inspected source is therefore the deployed source, not a newer unrolled wiring fix.
- Actual running ingest **video-ai-ingest-worker:int23-fa8a382**: /srv/ingest-worker/main.py normalized Git blob equals HEAD:backend/ingest-worker/main.py. No AI base URL or service key environment variables. Source SHA256 manifest retained for every relevant call-chain file.
- All non-test legacy Go method callers enumerated: one ContentHandlers.Recommendation call in a branch unreachable with production nilAI injection, plus two **in-memory mock** VisionV2/ASRV2 helper delegations. No production Vision/ASR/Search legacy call site. ContentHandlers.ai is not reassigned after construction.
- Four v1 HTTP methods in aihttp/ai_client.go and old mock routes remain **compatibility/test-only**. Concrete method existence is not an outgoing request. The disabled experimental feed branch is not claimed removed; any future personalization wiring must use released v2 features and AI-12 gates.

## Runtime log window

Captured current-container-start logs, capped at10000lines, reduced to path/counts only (no raw request data/keys retained):

| Container | Lines examined | Observed outgoing/served model paths | Four deprecated path calls |
|---|---:|---|---:|
| gateway | 111 | /health13 | **0** |
| ingest-worker | 11 | none (no AI HTTP client) | **0** |
| inference-service (new HC-18 image) | 62 | /health38, /v1/highlight/completions4, /openapi.json1 | **0** |

These counts support the source/provenance proof; they are **not a newly executed upload/search E2E workload**. The four live highlight requests are INT-54 full parity. Old full raw-upload/search/deletion real E2E evidence remains VERIFIED-HIST under INT-28/31. Current primary gateway has no recent new-video requests in this bounded log window; do not mislabel absence of traffic as new ingest acceptance.

## Focused verification

```text
cd backend
GOPROXY=off GOMAXPROCS=1
go vet ./...
go test ./...
go build ./...
go test -count=1 -v ./internal/adapters/aihttp -run '^TestV2'
go test -count=1 -v ./internal/orchestrator -run 'Test(IndexVideoFrames|PreprocessedMetadata|Chain)'
go test -count=1 -v ./internal/handlers -run '(Feed|Visual)'
```

All PASS, exit0, **HC17_GO_GATES_PASS**. Four v2 HTTP tests4.062s: real httptest roundtrip for vision/search/recommendation endpoints; vision600+1 batching; actual FFmpeg600.1s audio fixture creates exact600s PCM multipart chunks with offsets0/600; MODEL_NOT_READY preserved. Two indexing/metadata pipeline groups0.186s; four feed/visual groups0.367s (primary popularity/no AI calls, fallback/cached privacy/invalid-input checks). Full backend suite includes cached results; focused tests forced uncached. Mock server Gin registration lines for old routes in the log are not runtime AI traffic. No frontend/product source changed, so no unrelated FE rebuild.

Artifacts: INT-55-source-runtime.json (binary/source/ingest/caller proof), INT-55-runtime-paths.json (bounded real log counters), INT-55-go.log. No credentials or tokens logged.

## Conclusion / handoff

**Current production gateway/ingest do not call the four deprecated paths.** Claude can proceed with its D24 step3 removal/release planning under HC-17; this confirmation does not delete AI paths/dependencies or authorize changes to AI-owned files. Existing compatibility test helpers are intentionally retained; no gateway/worker deployment required.

Master479f5d5 has now published v2vision/search/ASR API_READY. Existing successful real E2E proofs from INT-28/31 remain valid VERIFIED-HIST (coordination README§4); matrix readiness metadata can consume that release without inventing new raw-upload results. Recommendation remains DRAFT/popularity. INT-50 full CMS QA/flags approval blocker and model quality/GPU/load/soak constraints remain independent.

Lane: codex
Changed: owned source/runtime/test proof, tracker/session/matrix/handoff only
Verified: deployed gateway SHA +unchanged source +packaged ingest blob, call-chain inspection, actual log0deprecated calls, Go gates/focused tests PASS
Contract touched: no (consumes v1.5/v2API_READY; no removed AI route)
Next safe task: Claude D24 step3/release and separate approved CMS QA; no old-media reprocess
