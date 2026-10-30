# INT-50 — eight-screen operational completion (2026-10-30)

Owner CODEX, IN_PROGRESS. User-approved CMS simplification and completion; public OpenAPI0.8 consumed, no AI contract/model/source changes.

## Source checkpoint before product migration/deployment

- Dashboard actual PG counts, job success/processing times/UTC completed_at chart/report, click counts, active15min and MinIO bytes; dependency availability explicit, no fabricated accuracy/online/storage/GPU values.
- Video and library global search/paging/deleted visibility and selection safety; hydrated category/creator/uploader/open count/updated time. CMS playback uses CMS presigned URLs, including actual draft previews. Deleted-source jobs/clips hidden from default operational catalogs, records remain stored.
- Queue real hydrated metadata/policy snapshot/skips/CPU, source-specific result navigation, terminal failure/cancel/retry guards. Source snapshot execution INT-41 and lifecycle INT-42 retained.
- Highlight persisted accept/dismiss/restore, reviewed compilation filtering, no unrelated compilation when no source selected; full video picker search and pagination.
- Subtitle edits persist full transcript used by AI regeneration; missing/deleted source cannot create orphan analyses. Summary save/approval and clip-hide failures return errors, clip category actually persists and feed cache invalidates. Subtitle timing/index/confidence validation. Editorial priority persists without claiming scheduling. Category true counts/keywords and independently saved vision/keyword suggestion switches; admin confirms category.
- Settings AI flags apply to new uploads, retries retain snapshot, real3buckets shown, dirty leave/reload warning. CMS Users/read-only/shared management capability from INT-47; public viewers still excluded. No account-delete implementation found, no user data deleted. Shared Client recovery still consumed and not removed without scope answer.
- Fresh DB init/seed now includes006 fields/settings; existing DB requires additive006, not an init replay.

## Verification before rollout

- Go vet/test/build ./... PASS; Linux gateway and PG/Mongo test binaries compile. After final deleted-source job filter, CMS+gateway tests PASS; final PG query change verified below.
- Real Linux PG via existing gateway `/tmp/int49/pg.test` with actual POSTGRES_DSN:3PASS0.15s/0.17s/0.08s, no skips. TEMP-only write targets, migration twice, fresh schema+seed in TEMP tables, reset preserves policy, clip title/category reload, counters/filter/visibility. INT-50-pg-final.log (earlier3PASS INT-50-pg.log).
- Real Mongo roundtrip1PASS0.03s incl edited full transcript/review/category; unique owned documents cleaned. INT-50-mongo.log.
- CMS tsc, E2E tsc, CMS Vite build PASS. Client generated contract compatibility tsc (--incremental false) PASS.
- Fixture Playwright:73PASS1.3m (INT-50-ui-regression.log), zero skips in that run. Includes18layout captures at390/1440, auth/session, editorial/category/settings/failure states, persisted proposal review and global search. Final small layout/copy corrections8PASS11.5s; picker search/paging2PASS3.8s. INT-50-ui-layout-final.log / INT-50-picker.log. Fixture checks are not real AI acceptance.
- Retained failures: initial category server-backed checkbox immediate check assumption (4PASS2FAIL; changed test to click then await response state); first regression70PASS3FAIL4SKIP (old videos-only auth fixture and old public-only playback fixture, plus terminated own stale test worker after observing disabled-source wait). Updated affected fixtures to current APIs; full73 rerun above PASS. Historical attempts retained, not counted as product PASS.

## Pending final acceptance

Product baseline/hash capture; apply006 twice and compare old columns/values; build/recreate only owned gateway/CMS, preserve all other runtime/env/volumes/AI; actual health/MinIO+CPU and policy HTTP proof; browser/API flows across8screens, fault checks and full10item Stitch review, restore settings and clean only own QA artifacts; stop own preview PID3392. Old AI Docker release remains real6/stubfalse historically, AI-19/quality upgrade stays Claude-owned HO-04; no claim of new model quality or v2 API_READY promotion.
