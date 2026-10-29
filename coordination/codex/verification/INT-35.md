# INT-35 — One AI highlight compilation video

Owner: CODEX. IN_PROGRESS. Contract INT-34 commit 6e1e6ad (public 0.5.0); AI API unchanged.

Existing POST /api/cms/clips with auto_highlights=true reads persisted AI proposals. Backend clamps source bounds, drops invalid/empty intervals, sorts chronologically and merges overlaps/touching intervals. No invented highlight when AI returns none: 422. Maximum 100 merged segments. One output timeline starts at 0 and ends at total retained duration; weighted score excludes removed gaps. JSON source map is persisted and returned in existing Clip DTOs, including feed/history queries.

FFmpeg trims video/audio and resets each interval's timestamps, then concat filter produces one H.264/AAC MP4 (silent videos supported). 15-minute bounded job timeout, temp files cleaned. Existing single-range clips retain old behavior. Original source video/objects untouched. CMS uses existing auth/create/review/publish flow, adds approved compilation action and preview/selector. No automatic publishing. Client remaps subtitles, heatmap and key moments to compiled timeline; feed maps playback back to source for subtitles.

Verified source gates:
- Go vet/test/build ./... PASS; host cutter real test skips if ffmpeg unavailable, separately executed in real gateway below.
- Actual gateway FFmpeg: TestCompilationRealFFmpeg PASS 2.53s, audio and silent inputs, output 2.000s within 0.1s; retained source frame pairs match (MAE <15), removed gap absent.
- Actual Postgres: TestClipThumbnailReferenceRealPersistence now also verifies source map (PASS 0.03s). Real feed 0.08s and catalog 0.12s with session TEMP tables PASS, no public row writes. Initial invocation lacked existing SQL fixture; copied owned 004 migration into isolated /tmp test workspace and reran successfully.
- Migration infra/postgres/migrations/005_clip_compilation.sql additive JSONB default [], applied on current Postgres twice; second is safe no-op. Fresh schema updated. No data backfill or new AI dependencies.
- CMS types/build PASS, Client types/lint PASS, E2E types PASS. Client production webpack build PASS; first direct Next invocation used default Turbopack and failed existing /fonts/fonts.css import, corrected using project build's existing --webpack flag, no CSS workaround/dependency.
- Compilation timeline Playwright pure mapping test PASS 19ms: gap boundary/legacy offset/source seeking/clipped subtitle intervals/removed heatmap samples.

Pending: source checkpoint, offline runtime app images, actual CMS draft-preview/publish/Client playback and cleanup; screenshots and scoped UI review; preservation audit. Do not mark DONE until those gates pass. Docker AI remains pinned ai-v2-478052e; Claude host Fusion5 announcement does not upgrade Docker automatically, no AI source/checkpoint/runtime edits in this task.
