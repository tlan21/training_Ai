# INT-35 — One AI highlight compilation video

Owner: CODEX. **DONE (scoped compilation feature)**. Contract INT-34 commit **6e1e6ad** (public 0.5.0); implementation **fbeeb50**, final Client labels **8918060**; AI API unchanged.

Existing POST /api/cms/clips with auto_highlights=true reads persisted AI proposals. Backend clamps source bounds, drops invalid/empty intervals, sorts chronologically and merges overlaps/touching intervals. No invented highlight when AI returns none: 422. Maximum 100 merged segments. One output timeline starts at 0 and ends at total retained duration; weighted score excludes removed gaps. JSON source map is persisted and returned in existing Clip DTOs, including feed/history queries.

FFmpeg trims video/audio and resets each interval's timestamps, then concat filter produces one H.264/AAC MP4 (silent videos supported). 15-minute bounded job timeout, temp files cleaned. Existing single-range clips retain old behavior. Original source video/objects untouched. CMS uses existing auth/create/review/publish flow, adds approved compilation action and preview/selector. No automatic publishing. Client remaps subtitles, heatmap and key moments to compiled timeline; feed maps playback back to source for subtitles.

Verified source gates:
- Go vet/test/build ./... PASS; host cutter real test skips if ffmpeg unavailable, separately executed in real gateway below.
- Actual gateway FFmpeg: TestCompilationRealFFmpeg PASS 2.53s, audio and silent inputs, output 2.000s within 0.1s; retained source frame pairs match (MAE <15), removed gap absent.
- Actual Postgres: TestClipThumbnailReferenceRealPersistence now also verifies source map (PASS 0.03s). Real feed 0.08s and catalog 0.12s with session TEMP tables PASS, no public row writes. Initial invocation lacked existing SQL fixture; copied owned 004 migration into isolated /tmp test workspace and reran successfully.
- Migration infra/postgres/migrations/005_clip_compilation.sql additive JSONB default [], applied on current Postgres twice; second is safe no-op. Fresh schema updated. No data backfill or new AI dependencies.
- CMS types/build PASS, Client types/lint PASS, E2E types PASS. Client production webpack build PASS; first direct Next invocation used default Turbopack and failed existing /fonts/fonts.css import, corrected using project build's existing --webpack flag, no CSS workaround/dependency.
- Compilation timeline Playwright pure mapping test PASS 19ms: gap boundary/legacy offset/source seeking/clipped subtitle intervals/removed heatmap samples.

## Deployment

Offline artifact overlays built with `docker-buildx build --network=none --pull=false --load` on existing cached gateway/CMS/Client images. No dependency or image download. Runtime images: gateway/CMS **int35-fbeeb50**, Client **int35-8918060** (final labels), also latest aliases. Old images retained as rollback-int35, Client intermediate rollback-int35-final. Existing Dockerfiles/Compose service topology needed no changes.

Commands (Docker Desktop WSL CLI/socket, correct existing project and both compose files):
```text
docker-compose -p video-ai --project-directory /mnt/host/e/traning_ai-codex -f /mnt/host/e/traning_ai-codex/docker-compose.yml -f /mnt/host/e/traning_ai-codex/docker-compose.inference.yml up -d --no-deps --no-build --pull never --force-recreate gateway cms client
# Final Client labels only:
docker-compose ... up -d --no-deps --no-build --pull never --force-recreate client
```
Required existing key/bind interpolation values stayed in memory. Full gateway environment compared unchanged. No AI service recreation/mount changes; no other service restart/down/volume deletion. Gateway live binary SHA **4f0b9a627ef59bf4dbdfab9451b02e4a9507c74c44163931ed95d0f6c5a855a6**, final Client BUILD_ID **jBLHEZwKfzQvS7Jxe2jdX** match host artifacts. Gateway healthz200/MinIO+Milvus ok; CMS/Client200; four app/AI health states healthy.

## Real acceptance

```powershell
$env:E2E_COMPILATION_VIDEO_ID='vid_dmh4b8ymqbtw'
node node_modules/@playwright/test/cli.js test e2e/compilation_live.spec.ts --output=backend/.tmp/int35-live --reporter=list
```
**1 PASS36.4s**, no mocks, retries or new video uploads. Uses stored real-AI analysis of sample_01.mp4 (60s):

- **9** intervals: 0–12,17–19,21–24,28–29,34–37,38–43,46–47,52–56,57–60 → one **34.000s** MP4 with original audio.
- CMS button sends auto_highlights=true, response processing and source map. Public clip route404 while private draft. Actual cutter produces draft and usable private playback URL; browser metadata duration agrees within0.15s.
- CMS preview at1440×900/390×844, no horizontal body overflow. Reload + selector preserves ability to review existing draft. Admin explicitly clicks publish; public clip/source map available, actual deployed Client plays the output video.
- Finally own clip **clp_dmh7dapvqjn1** rejected via existing DELETE CMS clip API; public route404 confirmed. File retained, no original video/media deletion. No enduring test publication.
- Screenshots inspected in INT-35-screens; JSON evidence excludes credentials/signed URLs.

Regression command: `node node_modules/@playwright/test/cli.js test e2e/cms_design.spec.ts e2e/client_design.spec.ts e2e/client_player.spec.ts e2e/compilation_timeline.spec.ts --reporter=list` → **112 PASS4.3m**, covering existing CMS/Client/player behavior. Fixture-based UI regression is distinct from the real acceptance above.

Final Client label refinement deployed separately: compiled H1/title/notice are accurate and no false unavailable-source message. `... test e2e/client_design.spec.ts e2e/compilation_timeline.spec.ts -g 'INT-35 compilation|compilation playback maps' --reporter=list` → **2 PASS2.4s** on final bundle. First focused UI assertion matched both H1 and related-card H3; corrected selector to heading level1, no product code change needed. Initial failed log retained. Final Client webpack build/lint and E2E types PASS.

## Scoped Design Parity Check (1440×900 and390×844)

Compared original read-only Stitch Highlight HTML/cached INT-05 reference screenshots, current live screenshots, plan03 CẮT-list and user-approved addition recorded in plan03/CONTRACT_DECISIONS. This checks the compilation addition and regressions; existing global INT-05/06 parity is not promoted.

| # | Item | Finding |
|---|---|---|
|1|Layout|Existing player/heatmap/proposal columns retained; new compilation preview below editing controls, explicitly requested. Mobile remains existing single-column layout.|
|2|Colors|Existing card/input/button/status tokens reused; only video canvas black. No global palette changes.|
|3|Typography|Existing heading/body/micro/mono styles inherited, no font/size overrides.|
|4|Spacing/radius|Existing card radius/border,16px panel padding,12px video spacing; added panel is approved feature content.|
|5|Icons|Existing Material auto_awesome system, no replacement icon set/library.|
|6|Vietnamese copy|Existing labels unchanged; new create/select/preview/draft instructions describe actual behavior.|
|7|AI UI|Actual stored scores, inherited heatmap/status badge; explicit draft review label, no fabricated model confidence.|
|8|States|No-proposal button disabled/backend422; processing→draft preview→explicit published verified, failed/rejected status handled. Selection after reload verified.|
|9|Responsive|Live390×844/1440×900 previews usable, buttons wrap, body scrollWidth<=viewport. Original desktop Stitch at390 is itself overflowing; existing responsive baseline is retained, not a new parity claim.|
|10|CẮT-list|No tracking/detection/face/foreign-subtitle/logo features added. New action/preview is explicit user-authorized scope.|

## Preservation and limits

- Original **106 videos** hash **41e538d83f6b7f6d73faa03ae214c62e**, original **56 clips** hash **e6810835e055c262d7c39314279cb35d** unchanged. Before/after clip projection omits the newly added source_segments column; old rows have default[]. Cutoff in preservation JSON selects the original rows. One new own test compilation retained/rejected, TEMP test clip absent (0).
- Other **13** containers retain IDs/images/start times/sorted mounts. Host Claude AI PID **14896** unchanged for this task; Docker AI real six models, no degraded models, CPU; no mock container. Pending/running video jobs0.
- AI creation step reuses existing analysis rather than rerunning inference. Existing Docker AI remains pinned **ai-v2-478052e**; Claude host Fusion5 release does not automatically upgrade it. No AI code, checkpoint or runtime configuration changes by this task; no /v2 API_READY promotion.
- No fixed target summary duration, transitions/music generation or automatic publication. All valid stored AI proposals are used (maximum100 merged intervals), no invented segments when none exist. Selection quality depends on current AI model. Sentence-boundary snapping/asr_segments and legacy single-clip precise-cut improvements remain HC-14 scope; compilation trims are accurately re-encoded, but may still end mid-sentence.
- No GPU/load/soak/model-quality certification, no master/shared-status edit or push.

Lane: codex
Changed: backend compilation/domain/PG/cutter/DTOs; additive SQL; CMS action/review; Client timeline mapping; tests and owned docs/evidence
Verified: Go vet/test/build, actual PG/FFmpeg, FE types/build/lint, 112 regression +1 real E2E +2 final focused tests, data/container/health checks
Contract touched: yes public0.5.0 (6e1e6ad); AI contract unchanged
Next safe task: remaining assigned INT-05/06 work; compilation request complete.
