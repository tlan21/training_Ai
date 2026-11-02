# INT-33 — missing video thumbnails (2026-10-29)

Owner: CODEX. **DONE** — source, real Postgres, deployed API and real CMS browser gates passed.
Startupcodex/integrationclean/noHEAD..master; README/SESSION/TASKS/Claudehandoff read. Skillbackend_endpoint +Ponytail;
existing contractGET/api/cms/videos,GET/api/cms/videos/{id},GET/api/videos(+detail),Clip.thumbnail_url alreadynullable string.
No newendpoint/responsefield/schema/migration/AI edit.

Rootcause: backendv2alreadywritesJPEGs to privateMinIO `thumbnails/{vid}/00000000.jpg`, but oldvideoDTOs forwardednullablePGthumbnail_url.
All3activeprocessedrows hadNULL, so CMS/Clientrenderedplaceholder; sampleobjectexists14290bytes/imagejpeg.
Additionalclipgap: CMSDTOomitted existingthumbnailfield andClipRepoINSERT ignoredthecolumn.

Small completebackendfix:
- Sharedhandlers.VideoThumbnailReference respects explicitstoredreference, derivesfirstframe forprocessedmissingref only,
 hidesdeleted/deleted_at rows andneverinventskeyforunprocessedvideo. Canonicalv2frameexists beforejobcanbeprocessed.
- ThumbnailURLpresigns privatekey for1h; keepslegacypublichttp(s)URLs; badbucket/traversal/key/signingerrorreturnsnil, neverrawprivatekey.
- CMSlist/detail/metadata response andpublicvideo list/detail use sharedmapping; publicfeed/history/likes clipmapping signs thumbnailreferences.
- Newclip inheritsvideo'scanonicalreference; PGclipINSERT persists key(notexpiringURL), CMSclipresponses signittoo.
 Existingmetadata/objects untouched, no reindex/backfill/modelcall or publicbucketpolicy change.

VERIFIED-NOW:
- `go vet ./...`, `go test ./...`, `go build ./...` PASS (Go1.26/GOMAXPROCS1/cacheddeps).
 Newunitcases: processedNULLfallback/privatepresignbucketkey/TTL, preserveexplicitref/noDBmutation,
 deleted/deleted_at/unprocessednil, unsafe/privatekey/signfailurehandling, CMSrowmapping, clipcreationthumbnail+score.
- `go test -c -o .tmp/int33-pg.test ./internal/adapters/pg` LinuxCGO0; copiedintorunninggateway/tmp then
 `TEST_POSTGRES_DSN="$POSTGRES_DSN" /tmp/int33-pg.test -test.v -test.run '^TestClipThumbnailReferenceRealPersistence$'`:
 **PASS0.07s** againstactualPostgres, TEMPclips LIKE public INCLUDINGALL onisolatedsingleconnection; no producttablewrites.
 Verifies freshClipRepo.Get reads samecanonicalthumbnailkey. DefaultGo runskipsDBtestswithoutDSN, separateactualPGPASS recorded.
- E2ETypeScriptnoEmit PASS. Newread-onlyexisting-video liveCMS test2viewports ready(no video/clip creation).
- LinuxgatewaybuiltSHA25691D008EF5960041BA7BC5AA46A93A3EE0DD91FCC4048FFAE2D11540A981E3554.

## Deployment and acceptance

- Source: **40b8bdc**; task startup **a5663df**. Offline image `video-ai-gateway:int33-40b8bdc`, also tagged latest; rollback-int33 retained.
- Built using cached int28 gateway base and the compiled binary, `docker-buildx build --network=none --pull=false --load ...`; no dependency/image download.
- Compose command: `docker-compose -p video-ai --project-directory /mnt/host/e/traning_ai-codex -f /mnt/host/e/traning_ai-codex/docker-compose.yml -f /mnt/host/e/traning_ai-codex/docker-compose.inference.yml up -d --no-deps --no-build --pull never --force-recreate gateway`.
  Docker Desktop WSL CLI/socket used as in existing runtime. Required key and current bind interpolation values stayed in memory; full gateway environment compared unchanged before recreation. No other service recreated.
- Live binary SHA256 equals compiled artifact: `91d008ef5960041ba7bc5aa46a93a3ee0dd91fcc4048ffae2d11540a981e3554`.
  `GET http://127.0.0.1:8000/healthz` **200**, status ok, MinIO/Milvus ok. See deployment JSON/log and image-build log.

Real browser command (existing media only):
```powershell
$env:E2E_THUMBNAIL_VIDEO_ID='vid_dmh4b8ymqbtw'
node node_modules/@playwright/test/cli.js test e2e/thumbnails_live.spec.ts --output=backend/.tmp/int33-live --reporter=list
```
**2 PASS, 23.7s**, no mocks, no retry. CMS 1440×900 and 390×844:

- All **4** current processed video thumbnails returned signed private URLs and HTTP 200 image/jpeg with nonempty bytes.
- CMS list/detail and public video list/detail carry the signed thumbnail. `sample_01.mp4` is decoded in the actual CMS table, naturalWidth 224.
- Deleted rows retain placeholder. Browser test does not upload, create clips or publish.
- Desktop/mobile screenshots inspected: `INT-33-screens/cms-thumbnail-1440.png`, `cms-thumbnail-390.png`; count JSONs contain no tokens or signed URLs.
- This is a backend data-mapping repair; no CSS, component, copy, spacing or layout changes. Full Stitch parity remains tracked separately in INT-06; screenshots verify the repaired image state only. No FE rebuild was needed.

## Preservation and limits

- Other **15** containers retain IDs, images, start times, status and sorted mounts. Gateway runtime environment unchanged. No ai-mock container returned.
- Host Claude AI listener remains PID **15852**. Docker AI health: stub_mode=false, all six models, degraded empty, CPU. This task does not change AI source, weights, runtime configuration or API release status.
- Original **106 video rows** retain hash `41e538d83f6b7f6d73faa03ae214c62e`; original **55 clip rows** retain hash `c2ee1e8cffb042acdc0c921df98da4e5`.
- A concurrent new draft `clp_dmh5oswbre9l` for the sample video was created at **07:50:04 UTC**, after the **07:49:48 UTC** snapshot. It remains intact. The full clip aggregate therefore changed to 56 rows; filtering only this new ID reproduces the original 55-row hash exactly. No claim that the whole live dataset was static.
- First aggregate verification used nonexistent `jobs` table and failed; corrected query uses `video_processing_jobs`. Active pending/running jobs **0**. Retained initial output in data-after.log; authoritative corrected output in data-preservation.log and preservation.json.
- Persistence test's `clp_thumbnail` is absent from public clips (count 0); it used a session-local TEMP table. No test media or public product rows were created by the live browser/persistence checks.
- Existing JPEG objects were read only; no metadata migration, reindexing, public bucket policy, source media or checkpoint changes. No AI quality/GPU/soak retest; AI v2 DRAFT status is unchanged.

Lane: codex
Changed: shared thumbnail mapping, CMS/public DTO callers, new clip reference persistence, focused Go and live browser tests, owned coordination/evidence
Verified: Go vet/test/build PASS; real Postgres TEMP persistence PASS; E2E types PASS; real CMS 2 PASS; deployed binary/health/data/container checks
Contract touched: no (existing nullable thumbnail_url; public 0.4.1 / current AI contract unchanged)
Next safe task: remaining INT-05/06 scope; no further action for this thumbnail bug.
