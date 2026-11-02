# INT-32 — Feed empty-state CSS regression (2026-10-29)

User screenshotlocalhost3000/feed showed emptyblackpanel stretched across7gridcolumns with left-aligned CTA.
Startupcodex/integration clean/no newmaster; skillsclient_screen +ui_design_review/Ponytail; UIUXtargetedsearch generic,
no exactaspect-ratio match, so originalStitch CSS is the authoritative layout source (no generateddesign applied).

Root cause: loadedfeed .feed-scroll had desktop9:16/maxheight/border/centering, but .feed-empty only hadgridspan/background/radius.
Mobileempty likewise collapsed to198px while the loadedviewport was788px. Shared PageState150px minheight separated icon/text from CTA.

Small fix in client/src/app/globals.css only:
- Share desktopportraitframe styling for .feed-scroll and .feed-empty, with minwidth0/centeralignment and definiteheight.
- Empty/loading/error flexcolumn centers status+CTA; resetPageStateinternalpadding/minheight within thisframe only.
- Preserve colors/copy/controls, loadedplayback/swipe/tracking/API/data. No invented content or UI outsideStitch/cutlist.

VERIFIED-NOW (source checkpoint; deployment still pending):
- BeforeactualClient3000: all3newempty-layout tests FAIL reproduced bug; desktop1440frame785x804,1877frame1039.921875x804,
 mobileframe390x198 andCTAleft0. Screenshots/bounds/log retained, nevercountedPASS.
- Fixed productionbuild `GATEWAY_INTERNAL_URL=http://gateway:8000 node node_modules/next/dist/bin/next build --webpack` PASS;
 buildIDeqhNJmAsXQNOLhmwmgMGu. Client tsc --noEmit --incrementalfalse /eslintsrc andE2E tsc PASS.
 An initial wrongworkingdir edit did not apply, firstbuildwasoldsource; actualCSSpatched then fixedbuildrerun. A simultaneoustsc hitNextgeneratedtypes
 beingrebuilt; reran sequentially afterfixedbuild andPASS. No applicationruntime changed during these tool corrections.
- ExactapprovedQAstart `node node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3100` fromClient, ownedPID22188.
- New feed_layout.spec.ts: **12PASS25.5s**:390x844/1440x900/1877x900 xempty/loading/error/loaded; viewportbounds/aspectratio/centeredCTA/nooverflow,
 mobilefullheight andnextpanelwithinviewport. Fixtures are isolatedUI mocks, no productvideo uploads.
 Fixeddesktopframe438.75x780 at y92 (centerwithinremainingviewport); mobile390x788. Allstates use sameframe.
- ExistingClientdesign/player/onboarding regression: **71PASS1.4m**, playback/autoscroll/interactions/keyboard/auth/draftcaptions/downloads unchanged.
- OriginalStitch feedreferencecapture: **2PASS5.9s**,390x844 and1440x900 using unmodifiedHTML/cachedTailwind+images;
 screenshots inINT-32-screens. Visuallyinspected mobile/desktop/wideempty +desktopreference; source .video-container aspect9/16,maxheightH-120,
 6pxborder/32pxradius and .sectionitemscenter align with fixedframe.

Scoped Design Parity Check10items (feedframe/status bugfix only; globalINT-06 remainsPARTIAL):
| # | Check | Result/evidence |
|---|---|---|
|1|Layout|PASS: desktop1/7/4columns, centeredportraitframe; mobilefullscreen; before/afterbounds|
|2|Colors|PASS unchangedStitchtokens/backgroundblack/white status text; frameborder --surface-container-high|
|3|Typography|PASS unchangedInter/14pxstatus and existingbutton; scopedchange no font overrides|
|4|Spacing/radius|PASS shared6pxborder/32pxradius/9:16/maxheightH-120; centeredgap16 statecontent|
|5|Icons|PASS unchangedMaterialSymbols; emptyvideo_library is existingPageState vocabulary|
|6|Vietnamese copy|PASS unchangedstatus/CTA/labels; data differsfromStitch onlyasallowed|
|7|AI controls|PASS loadedfeedcontrols/heatmap unchanged,71regressions; no fakeAIresults introduced|
|8|States|PASS empty/loading/error/loaded sameframe, action remainsvisible/centered;12tests|
|9|Responsive|PASS390/1440/1877 nooverflow/frame/panelbounds; screenshots|
|10|Cuts|PASS no translate/follow/comments or othercutfeatures added|

Image contextstaging backend/.tmp/int32-image contains3.29MB rebuilt .next (cache/dev/types/diagnostics excluded)
+unchanged next.config.mjs; routes-manifest asserts /api ->http://gateway:8000.
Deploy onlyClient usingcachedint23-fa8a382 base, preserveGateway/DockerAI/hostAI/allDB. CurrentapprovedHC12Clientdraftlabels fromsource
will also be included (CMS5173 image unchanged); fullsource71QA covers them. Do not promote globalUIparity or unrelatedsettings functionality.

Lane: codex
Changed: ClientfeedCSS +focusedlayouttest +ownedcoordination
Verified: fixedbuild/types/lint,12newUI+71regression+2originalreference testsPASS; live deployment pending
Contract touched: no
Next safe task: offlineClientimagebuild/client-onlyrecreate then actualClient3000 emptyfeed verification/stopownedQA

## Final Client3000 deployment — PASS

Source **16bfad7**, rebuilt productionartifacteqhNJmAsXQNOLhmwmgMGu (Dockerrewritegateway8000).
Offline image `video-ai-client:int32-16bfad7` built from cachedint23-fa8a382 +3.29MB .next; --network=none/--pull=false,
 no package/image download. Latestalias nownewimage, rollback-int32 retained.

ActualWSL commands used existingDockerDesktop socket unix:///proc/193/root/run/docker.raw.sock, docker CLI
/mnt/host/wsl/docker-desktop/cli-tools/usr/bin/docker and Compose
/mnt/host/wsl/docker-desktop/cli-tools/usr/local/lib/docker/cli-plugins/docker-compose.
Compose `-p video-ai --project-directory /mnt/host/e/traning_ai-codex -f /mnt/host/e/traning_ai-codex/docker-compose.yml
 -f /mnt/host/e/traning_ai-codex/docker-compose.inference.yml up -d --no-deps --no-build --pull never --force-recreate client` PASS.
CurrentDockerAI key/bind onlymemory forrequiredComposeinterpolation, unchanged/restored; no secrets printed orstored.
OnlyClientrecreated; buildIDincontainer matcheshost exactly, ClientHTTP200/healthy.

Realbrowser+API verification at **localhost3000** (no routemocks): adminlogin/refresh/feed200,
 actualfeed0published/popularity; realemptyframes measured1440/1877x900 and390x844 exactlymatchQA.
 Desktop438.75x780/y92, wideX491.984375, mobile390x788; CTAcenter/nooverflow PASS.
 Live screenshots live-1440/1877/390 saved anddesktopvisuallyinspected, alongsidebefore/after/reference captures.
 No productvideo/clip creation orpublishaction performed bytheseUI tests; currentemptyfeed isactualAPIstate.

Preservation: other15containers IDs/images/start/state/mounts unchanged; DockerAIstubfalse6real andhostPID15852 unchanged.
 Original105video rows fingerprintba617c6dcef5d5c4471684ad534c3214 +10categoryfingerprint2279cd784f346ec1e52ce40605752c91
 unchanged acrossdeploy, activejobs0. Gateway/AI/CMS/DB not restarted; no weights/models/inferencecode changes.
 ExactownedQA PID22188 identity+creationUTCticks verified beforestop, port3100closed. No othernodeprocess stopped.
 Logs normalized trailingwhitespace only; no testoutput/content changes.

Includes alreadyapproved HC12Clientdraftlabels fromcurrentSource; full71testregressioncovers them. CMS5173 stilloldimage,
 INT-24/INT-05/06globalstatuses unchanged. No settingspipeline behavior addressed inthisCSS-onlytask.

Lane: codex
Changed: ClientfeedCSS,12-state layouttest, ownedcoordination/evidence; ClientDockerimageonly
Verified: build/types/lint,12newUI+71regression+2Stitchreferences PASS, actualClient3000 API/browser3sizesPASS, preservation/QAstopPASS
Contract touched: no (public0.4.1/AIv2DRAFT unchanged)
Next safe task: none forfeedbug; globalparity/settingsfunctional gaps remainseparate; no push/master release
