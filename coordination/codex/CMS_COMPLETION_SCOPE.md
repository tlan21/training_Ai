# CMS completion — user scope 2026-10-30

User: remove CMS forgot-password/account deletion/role assignment, use provisioned CMS accounts; complete operational features of Dashboard, Videos, Queue, Highlight, Subtitles/Summary, Published library, Categories, Users. Work persists across checkpoints until actual app/E2E acceptance; not another audit-only task.

## Decisions and scope

- Keep authenticated CMS-vs-public-account boundary; no editable permission matrix. No deleting existing users or role values. Shared public Client recovery still consumed: remove CMS entry/deny CMS reset, pending optional user clarification before deleting Client feature/backend.
- No AI source/checkpoint/runtime upgrade or AI contract changes. Existing old Docker real AI can be used for transport/function tests, not new model-quality acceptance. HO-04 remains Claude dependency.
- No external libraries/services, detection, face recognition, translation or non-Vietnamese ASR. No fake metrics. Missing dependency metrics must be nullable/explicit unavailable.
- Existing endpoint families only. Public0.7.0 auth contract is f3d6080; source cleanup677ee6a (PARTIAL pending real deployment). Public0.8.0 operational contract INT-48 before implementation.

## Planned implementation

1. Read models/storage (INT-49 after48): additive006 migration: categories.keywords, videos.editorial_priority, jobs.processing_options/skipped_stages; additional2category setting defaults. Real PG overview metrics and global filters; MinIO usage; Linux CPU sample; row metadata/name/counts/views; Mongo review and category match setters. No row/value backfill or destructive migration.
2. INT-41: snapshot auto-highlight/subtitle settings before upload event; existing jobs keep original snapshot. Vision still runs for classification/search; ASRoff stores explicit empty transcript/summary without calling ASR/completions; highlightoff stores empty score/proposals without calling highlight; stage skips shown. Defaults/legacy jobs remain compatible. Persist2category rule flags, keyword suggestion outranks mapped AI category, editor confirms category (no automatic publishing).
3. INT-42: failed ingest/job/video consistent; retry clears obsolete failure and timing/progress, rejects deleted source; cancel consistent and stage-bound, not claimed hard-kill of model. All status writes preserve deleted guard.
4. INT-44: category FK23503 becomes clear409 conflict, no raw SQL; keep referenced data. Unused category CRUD works with keyword persistence.
5. Highlight review: existing analysis path gets PUT decisions; accepted/dismissed persist, original AI proposals immutable. Auto compilation excludes dismissed proposals; restore dismissed available. No-video page must not offer unrelated compiled clips. Manual trim remains; bounded preview already exact, do not redo cutter.
6. Eight-screen UI: Dashboard actual counts/success rate/bytes/active15min/UTC-month chart/report; Videos global q/category/dates/status with deleted explicit; Queue hydrated video/uploader/priority/snapshot/skips/CPU and source-specific navigation; Highlight review/compile flows; Subtitles correct regeneration copy, metadata editorial-priority (label explicitly editorial, no Kafka/GPU scheduling claim), validation/dirty/approval preservation; Library global clip/original q, real opening-count/creator/category/updated time and bulk safety; Categories true repository counts/rules; Users searchable readonly dates already source implemented.
7. Settings scope needed for above: flags execute, actual bucket display includes thumbnails, dirty navigation guard; readonly MinIO/Vietnamese/model-owned threshold remain intentional. Other3Settings tabs not auto-expanded into email/security infrastructure under this request.

## Metrics definitions

- total_videos excludes deleted; processed is an actual status count. No accuracy percentage invented: success_rate = completed/(completed+failed) for real jobs; unknown denominator =>null.
- active_users = distinct Client users with validated interactions in last15minutes (not websocket online count).
- views = validated click/open interaction count; UI labels opening count so checkpoint watch-time rows do not inflate it.
- average_processing_seconds from real started/completed times; UTC month daily chart uses completed_at.
- MinIO usage counts actual objects/bytes across raw-videos/clips/thumbnails, cached30s; no invented capacity/quota.
- CPU is Docker/Linux host sample between reads, not Windows-host or GPU capacity; initial unavailable sample =>null.
- Category counts across entire non-deleted repository, not only current list page.

## Validation and preservation

- Go vet/test/build; CMS/Client/E2E types, relevant builds; real PG TEMP-table/migration idempotence and Mongo roundtrip; native+actual container execution where required.
- Playwright fixtures cover validation/error/states separately; live actual AI upload/processing/mixed policy flags/manual/compiled publishing/drafts/editorial/rules/search/delete with only owned test artifacts. No mock accepted as real AI.
- Existing all data baseline before006; compare old columns excluding added schema fields afterward, keep counts/IDs original rows, no overwrite original analyses/media or role values. Added default fields documented rather than falsely claiming whole-row hash unchanged across a schema extension.
- Deploy only owned gateway/CMS (Client only if source changes); preserve all other containers/AI/mounts/volumes/env. Existing Docker stack remains, no model mount/restart.
- QA preview only own PID3392 port5174 for now, stop exact process at final checkpoint. Client3000 unchanged. E disk~440MB, D cache7GB available; no downloads/prune/cleanup of user data.
- Old opt-in INT-40/45 audit scripts contain retired role/reset and pre-fix flag expectations: update them or retire obsolete blocks before final E2E, preserve their committed historical evidence.
