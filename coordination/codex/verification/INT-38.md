# INT-38 — HC-15 threshold metadata and truthful CMS (2026-10-30)

Owner CODEX. **REVIEW** (code/deployed legacy compatibility verified, new AI release gate pending). Contract INT-37 **f709b94** (public0.6.0); source **43e45a1**. AI v1.4-rc1 extension DRAFT, no readiness promotion.

Backend: AIHTTP optionally decodes clip_threshold and rejects values outside0..100. Absence/null stays unknown,0 stays valid. AnalysisStore.Put writes threshold with scores/proposals/category in one Mongo update; interfaces/Mem/callers updated. CMS analysis DTO exposes nullable metadata. No migration/backfill/reprocessing/model changes. Existing requests to AI are unchanged, full-video feature sequence remains intact.

CMS: heatmap threshold comes from that analysis, no Settings dependency. Reported0/51 used verbatim; legacy unknown shows an explicit75 display fallback disclaimer, not an assertion about AI selection. Zero proposals is valid and manual saving remains enabled. Non-football/<120s scope notice, generic heading for non-football; dismissing all suggestions has distinct text. HC-15(b): Settings slider replaced by model-owned notice; legacy API field retained/deprecated and existing persisted values untouched. Revision7 requires reported threshold, so no hardcoded50/51 seed migration. Auto-toggle orchestration remains an existing separate gap, not claimed fixed.

Verified before deployment:
- `go vet ./...`, `go test ./...`, `go build ./...` PASS. Unit cases optional/null/0/51/100, invalid-1/101, orchestrator atomic metadata, CMS DTO unknown/zero semantics. First focused run found one old test caller missing new Put argument; fixed, not counted PASS; final full run passed.
- Actual gateway: Linux Mongo test binary with TEST_MONGO_URI from existing runtime env in memory; `TestStores_RealVietnameseRoundTrip` **PASS0.07s**.51/0/null roundtrip, preserved Vietnamese summary, own temporary document cleanup checked. Original product analyses untouched.
- CMS TypeScript/build +E2E types PASS. **14 focused UI PASS12.3s**:390/1440, reported/0/legacy/short-football/long-news/short-news, legitimate empty state/manual save, Settings90 does not override AI51 (canvas red-color evidence), truthful Settings save/reset/failure behavior.
- **41 existing CMS regression PASS51.4s**, **4 fresh original Stitch Highlight/Settings reference captures PASS7.0s**. Screenshots inspected, HC-15 notes/widget change authorized in owned plan03; global INT-05 parity not promoted.
- Own production CMS QA preview5174PID21800. Data baseline:106videos/58clips,4processed analysis hashes without new metadata; existing gateway/CMS/AI images recorded. Source Git clean before task, no master delta, Release#4 received.

## Deployment and live compatibility

- Offline images `video-ai-gateway:int38-43e45a1`, `video-ai-cms:int38-43e45a1` built from cached int35 app bases using buildx --network=none/--pull=false/--load. Existing root+inference compose, `up -d --no-deps --no-build --pull never --force-recreate gateway cms`. No Client/AI/infra recreation, dependency downloads or Dockerfile/topology changes. Runtime key and required existing bind interpolation stayed in memory; no AI service/mount operation.
- Both latest aliases updated; rollback-int38 retained. Gateway full configured environment unchanged. Live binary SHA **a80b37112e9003015b83c011738c2bfb50ab4daee32b0994e1f23f4a6e682957** equals artifact; healthz200/MinIO+Milvus ok, CMS200.
- `E2E_HC15_VIDEO_ID=vid_dmh5o652juum node node_modules/@playwright/test/cli.js test e2e/hc15_live.spec.ts --reporter=list`: **2PASS5.3s**, actual CMS/API at390/1440, no route mocks. Existing analysis returns explicit null threshold; UI displays legacy disclosure, manual save enabled; Settings model-owned notice/no slider. No new account/media/clip, settings writes or original-video reprocessing.
- Own previewQA **PID21800** command identity checked/stopped;5174closed. Actual/reference screenshots inspected and captured separately from synthetic metadata UI tests.

## Scoped design check (390×844/1440×900)

Original Highlight/Settings Stitch and plan03 CẮT-list inspected; HC-15 explicitly authorizes new notes/zero state and model-owned Settings replacement. No claim that all existing INT-05 design gaps are closed.

|#|Item|Result|
|---|---|---|
|1|Layout|Existing player/timeline/proposals/manual editor and Settings sections retained; notes/widget replacement are authorized HC-15 scope.|
|2|Color|Existing tokens/badges/canvas palette; threshold51 now correctly colors score60 as a peak.|
|3|Typography|Existing heading/body/micro classes, no new font/style overrides.|
|4|Spacing/radius|Existing cards/controls/timeline geometry unchanged; text wraps at390.|
|5|Icons|Existing Material icons unchanged.|
|6|Vietnamese copy|Explicit AI/legacy distinction, valid empty-state/manual guidance, scope note; no false threshold control.|
|7|AI components|Reported51/0 used, unknown not guessed; Settings90 cannot override AI51 (actual canvas pixel test).|
|8|States|Known/0/legacy, short-football/long-news/short-news, valid zero proposals, save/reset/server-failure UI all PASS.|
|9|Responsive|390/1440 no horizontal body overflow; actual UI and fixture/reference captures inspected.|
|10|CẮT-list|No removed model/social/foreign-subtitle features restored. HC-15 changes documented in owned plan03.|

## Preservation and readiness

- Original **106 videos** hash **41e538d83f6b7f6d73faa03ae214c62e**, **58 clips** hash **9186844a706846cea3a6c3b8a17a6a67** unchanged. Four original analysis response hashes (excluding new null field) identical. No threshold backfill or fake51 values written to old data. Jobs0; Mongo test only fresh temporary test docs, cleanup checked.
- Other **14** containers retain IDs/images/start times/status/sorted mounts. Host8001 absent both before/after; Docker AI still old478052e real6, not replaced. No original source-media writes or model/checkpoint operations.
- HC-15(b): legacy Settings field/value/seed retained for compatibility, unused by new UI. Do not hardcode50/51 or overwrite existing admin configuration; current model's reported threshold wins. Existing auto_highlight/auto_subtitle orchestration wiring is not solved by this change.
- New reported-threshold inference proof remains **pending Claude v1.4 release/current immutable AI runtime and AI-19 parity fix (HO-04)**. Optional field was tested via HTTP fixtures +actual Mongo; actual product legacy compatibility verified, not model-quality or new-runtime integration. No INTEGRATED_REAL/DONE promotion; no GPU/load/soak/master/shared-status/push.

Lane: codex
Changed: reported-threshold domain/ports/HTTP/Mongo/orchestrator/DTOs; CMS truthful threshold/empty/scope UI; tests/owned docs
Verified: Go gates, actual Mongo, CMS/types/build/E2Etypes,14focused+41regression+4reference+2actual legacy UI PASS, preservation/QA stop
Contract touched: public0.6.0; AI v1.4 DRAFT consumed read-only
Next safe task: INT-39 precise single-clip cut; new model field readiness remains HO-04
