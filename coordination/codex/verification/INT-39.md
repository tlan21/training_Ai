# INT-39 — HC-14 precise single-range cuts (2026-10-30)

Owner CODEX. **DONE (backend cut precision only)**. Predecessor INT-38 deployment checkpoint **8979a49**; source **5ce29db**. Independent backend part of HC-14, no new AI/API/DB field.

Root cause verified against actual gateway FFmpeg: old `realExec` input seek +stream-copy produced **2.040s** video/container for requested **0.52..2.36s =1.840s** (audio1.848s). Baseline test exit1 retained, not PASS.

Minimal change: normal single-range execution delegates to existing exact trim/concat engine from INT-35. All encoded jobs bounded15minutes; lifecycle/events/storage paths/source offsets unchanged. No recut of already stored files. Removed forced setsar=1 from shared video trim path: all branches come from one source, so preserve original sample/display aspect ratio instead of distorting non-square-pixel sources. Output H.264/AAC (silent sources supported), existing image codecs reused.

Verification before deployment:
- Grepped all realExec/execFn/realCompilation callers, kept test injection and unchanged single-clip source timeline semantics.
- `go vet ./...`, `go test ./...`, `go build ./...` PASS; Linux cutter test and gateway builds PASS, cached dependencies/no downloads.
- Actual gateway FFmpeg Linux binary test **PASS3.58s**, four cases: single audio/silent each **1.840s**; compilation audio/silent each **2.000s**. Format duration within0.1s, retained source RGB frames match MAE<15, audio presence correct and source **SAR4:3** retained in output.
- Disposable6s/25fps generated media only; no product upload, clip creation, settings/analysis rewrite or model call. Test cleanup uses Go temp directories.

## Deployment and preservation

- Offline gateway overlay built on cached int38-43e45a1, `docker-buildx build --network=none --pull=false --load`, image **video-ai-gateway:int39-5ce29db**, latest alias updated; rollback-int39 retained. No downloads or image/service topology/Dockerfile changes needed.
- Existing root+inference compose, `up -d --no-deps --no-build --pull never --force-recreate gateway`, after verifying0active video/cut writers. Only gateway recreated, full configured environment unchanged. Required existing runtime key/bind interpolation stayed in memory; AI not restarted or mounted by this operation.
- Live binary SHA **055be3feaf50f0d242872bd8501fec5752d817799f647fa73a4f50cce29b2ae9** matches artifact; healthz200/MinIO+Milvus ok. CMSint38/Clientint36/AIold478052e remain healthy. Other **15** containers retain IDs/images/start times/status/sorted mounts.
- Original **106 videos** hash **41e538d83f6b7f6d73faa03ae214c62e**, **58 clips** hash **9186844a706846cea3a6c3b8a17a6a67**, **4 original analysis hashes** unchanged; no threshold backfill, jobs0. No original/product-media upload, recut, clip creation or settings mutation by this task. Own prior CMS QA closed; no mock container, no host AI listener started.
- Initial read-only audit proof writer used reserved PowerShell Host variable and failed after comparisons; corrected variable and completed audit. No app/data mutation or test failure was hidden.

## Limits and next work

Precision bounded by source frame resolution; fixture25fps verifies requested timestamps/duration within0.1s, not universal sub-frame precision. Re-encoding costs CPU and new clips may take longer than stream-copy; bounded15m deadline/2FFmpeg encoding threads. Already stored clips remain untouched. Existing lifecycle behavior retained; this is not an audit of all cancellation/retry races.

No UI/source-offset/API/schema/AI request/model/checkpoint edits. No sentence-safe boundary claim: ASR segment snapping/new AI runtime and AI-19 feature-parity proof remain HO-04/HC-14 dependencies. No full production AI quality/GPU/load/soak acceptance, master/shared status edit or push.

Lane: codex
Changed: shared cutter execution and aspect handling, meaningful duration/frame/SAR/audio tests, owned docs/evidence
Verified: Go vet/test/build, Linux binaries, actual FFmpeg before/fixed4cases, live gateway binary/health/data/analysis/container preservation
Contract touched: no (public0.6.0 and current AI contract unchanged)
Next safe task: remaining assigned app backlog/INT-05/06; AI runtime and sentence boundary parts remain blocked separately
