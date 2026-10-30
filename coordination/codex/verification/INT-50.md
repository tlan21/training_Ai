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


## Product migration / offline artifact checkpoint

Source commit6287454. `backend/.tmp/int50-migrate.ps1`: actual product006 applied twice with ON_ERROR_STOP, normalized original row hashes/IDs/counts identical before/after each apply (exclude only newly added columns and2new settings).119videos,61clips,51users,10categories,119jobs,67interactions,6legacy settings preserved; new flags onlytrue/false defaults. Evidence INT-50-db-before.json, INT-50-db-after006-{1,2}.json, INT-50-product-migration.log, INT-50-new-settings.json. Original Mongo analysis/subtitle id+SHA256 captured, no raw transcript or secret exported. Setup null-hash/Mongo-auth failure occurred before migration; corrected snapshot authentication uses existing container environment, never prints credentials.

`backend/.tmp/int50-build.ps1`: two offline app images built on verified currently running app bases using buildx --load --pull=false --network=none; no dependency/image downloads, container restarts or model work. Tags video-ai-gateway:int50-6287454, video-ai-cms:int50-6287454. Gateway binarySHA25656AE15A19E72491DFD998808C0003216F3E940FCC7FAF6FF2975BBD1CB63D3BA; CMSindex-BzSu-Jfr.js/index-Y6W6UZTl.css. Build logs INT-50-build-{gateway,cms}.log. Actual pre-rollout AIhealth6/stubfalse/CPU/degradedempty in INT-50-ai-before.json; runtime13projectcontainer identities/env/mount/command hashes captured in INT-50-runtime-before.json. Still pending selected gateway/CMS recreation and real acceptance; all original services remain running.


## Initial rollout / cancellation acknowledgement correction

Initial source6287454 gateway/CMS deployed with `compose ... up -d --no-deps --no-build --pull never --force-recreate gateway cms`: HTTP200/binary/bundle verified, actual AI6/stubfalse/CPU/degradedempty. Other11projectcontainers unchanged. Initial unordered Mounts hash check flagged Kafka; exact permutations of the current immutable mount objects reproduce the original hash, proving order-only serialization, not mount changes. INT-50-mount-order-proof.json / runtime-after-rollout.json / rollout.json. No second recreation used just to resolve this check.

Before live mutations, safety review reproduced immediate cancel=>failed allowing retry/delete before the current AI stage finished writing. INT-50-cancel-before.log. Corrected source: atomic RequestCancel flag (pending/running), worker acknowledges at the stage boundary, terminal failed state only after work returns; retry/delete remain guarded meanwhile; atomic completed transition excludes canceled flags, completed jobs reject a late cancellation. Queued cancel acknowledged without AI, terminal preprocessing replays do not read already-removed artifacts. UI says pending stop and disables duplicate cancel.

Go vet/test/build PASS after correction (INT-50-cancel-go.log); actual PG3PASS0.37/0.21/0.14 (INT-50-cancel-pg.log, no skips) including cancellation/finalization CAS, retry reset and sole soft-deleted FK conflict +unused-category deletion. Queue UI4PASS5.5s at390/1440; CMS/E2E types/build PASS, updatedbundleindex-BvWilaKn.js/CSSindex-Y6W6UZTl.css. Correction not yet deployed at this checkpoint; real final acceptance remains pending. No original job cancellation or user media mutation used for reproduction.
