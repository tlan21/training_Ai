# INT-38 — HC-15 threshold metadata and truthful CMS (2026-10-30)

Owner CODEX. IN_PROGRESS. Contract INT-37 **f709b94** (public0.6.0); source checkpoint follows. AI v1.4-rc1 extension DRAFT, no readiness promotion.

Backend: AIHTTP optionally decodes clip_threshold and rejects values outside0..100. Absence/null stays unknown,0 stays valid. AnalysisStore.Put writes threshold with scores/proposals/category in one Mongo update; interfaces/Mem/callers updated. CMS analysis DTO exposes nullable metadata. No migration/backfill/reprocessing/model changes. Existing requests to AI are unchanged, full-video feature sequence remains intact.

CMS: heatmap threshold comes from that analysis, no Settings dependency. Reported0/51 used verbatim; legacy unknown shows an explicit75 display fallback disclaimer, not an assertion about AI selection. Zero proposals is valid and manual saving remains enabled. Non-football/<120s scope notice, generic heading for non-football; dismissing all suggestions has distinct text. HC-15(b): Settings slider replaced by model-owned notice; legacy API field retained/deprecated and existing persisted values untouched. Revision7 requires reported threshold, so no hardcoded50/51 seed migration. Auto-toggle orchestration remains an existing separate gap, not claimed fixed.

Verified before deployment:
- `go vet ./...`, `go test ./...`, `go build ./...` PASS. Unit cases optional/null/0/51/100, invalid-1/101, orchestrator atomic metadata, CMS DTO unknown/zero semantics. First focused run found one old test caller missing new Put argument; fixed, not counted PASS; final full run passed.
- Actual gateway: Linux Mongo test binary with TEST_MONGO_URI from existing runtime env in memory; `TestStores_RealVietnameseRoundTrip` **PASS0.07s**.51/0/null roundtrip, preserved Vietnamese summary, own temporary document cleanup checked. Original product analyses untouched.
- CMS TypeScript/build +E2E types PASS. **14 focused UI PASS12.3s**:390/1440, reported/0/legacy/short-football/long-news/short-news, legitimate empty state/manual save, Settings90 does not override AI51 (canvas red-color evidence), truthful Settings save/reset/failure behavior.
- **41 existing CMS regression PASS51.4s**, **4 fresh original Stitch Highlight/Settings reference captures PASS7.0s**. Screenshots inspected, HC-15 notes/widget change authorized in owned plan03; global INT-05 parity not promoted.
- Own production CMS QA preview5174PID21800. Data baseline:106videos/58clips,4processed analysis hashes without new metadata; existing gateway/CMS/AI images recorded. Source Git clean before task, no master delta, Release#4 received.

Pending: offline gateway/CMS artifacts and deployment, actual legacy null-field/UI read-only acceptance, preservation/QA stop, final handoff. New reported field still requires Claude current image/source release and real inference proof (HO-04); current old Docker AI is not silently upgraded, host8001 absent at startup. No fake INTEGRATED_REAL claim.
