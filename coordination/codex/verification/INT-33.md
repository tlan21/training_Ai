# INT-33 — missing video thumbnails (2026-10-29)

OwnerCODEX. IN_PROGRESS, source/unit/realPG gatespassed, deployment/livebrowser pending.
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

Next: offlineGatewayoverlay/currentruntime, gateway-onlyrecreate, runrealexisting3imageGET/API/CMS1440+390 tests andbrowserproof;
 preserveallmetadata hashes/othercontainers/AIhost+Docker; no CMS/Clientrebuild necessary becauseexistingimagecomponent supportsURLs.
