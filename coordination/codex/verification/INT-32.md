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
