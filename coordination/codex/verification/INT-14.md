# INT-14 — product popularity and honest recommendation mode (2026-10-26)

Owner CODEX. HC-06 scope uses INT-14 because INT-12 already owns CMS auth. Public OpenAPI0.3.0, AI-API v1.3 consumed.

## Implemented
- Contract-first FeedPage adds required `recommendation_mode: popularity|personalized|fallback`; Go/CMS/Client types regenerated (0a86a14).
- D18 MVP wires primary Postgres popularity. It does not wait for v2 training. Only processed videos with published clips enter ranking;
  rank remains interaction count over7days, metadata/playback URLs hydrated from current product repositories.
- Optional recommender path consumes v1.3 mode. Only `personalized` plus valid product IDs/public clips yields that label.
  Unknown/MovieLens/private IDs, missing/legacy/stub mode, errors and empty results fall back to PG. No upstream title/thumbnail accepted.
- AI cache retains candidates for60s, not serialized product metadata; every response rechecks current visibility/title/playback URL.
  Duplicate video candidates omitted and clip limit enforced. Existing single-page `next_cursor=null` behavior retained, documented shortcut.
- Client feed/discovery map all3modes; legacy missing mode says “Đề xuất”. D18 overrides personalized copy only for popularity/fallback.
  Build workers limited to1 in Next config to fit shared workstation memory. No new library or AI source change.

## VERIFIED-NOW
- Go vet/test/build all PASS; final Linux gateway cross-build PASS. Handler tests cover5mode cases, cached deletion/current metadata,
  deduplication/limit and unknown product IDs. HTTP client test decodes v1.3 mode+nullable metadata.
- Real Postgres5tests PASS, no skips (`INT-14-pg.log`). New visibility case excludes videos with no published clips.
  Initial host localhost DSN authentication failed; final verification used the gateway's actual DSN inside its container (passed via environment, not logged).
- Client `tsc --noEmit`, `npm run lint`, `npm run build`: PASS, 14pages. CMS tsc/generated Go model compile PASS.
- E2E types PASS. Client design/regression **46 PASS** (1.4m, `INT-14-client-playwright.log`); focused mode screenshots **8 PASS**
  (21.7s, `INT-14-mode-playwright.log`) for390×844 and1440×900, including legacy missing field.
- Live mock-AI/business stack initially verified optional fallback: `INT-14-business.log` reports mode=fallback.
  Final D18 primary wiring verified separately: `INT-14-primary-business.log` + updated `INT-02-persistence.json`, mode=popularity,
  preferences/history/likes/settings survive gateway restart; published clip/feed, playback206 and deletion privacy PASS.
- Test script now uses IPv4 gateway/default15s HTTP timeout. A localhost request hung after restart while127001/CMS proxy worked;
  interrupted only task-owned test session after restoring its threshold76→75 and soft-deleting only its video `vid_dmeozywpnbl4`.
  Final IPv4 run completes cleanup successfully. No original user data deleted or credentials/config rewritten.

## Design Parity Check — mode change scope

Reference read-only short_video_feed/discovery mobile+desktop HTML; plan04§8.2 CẮT-list; D18 overrides recommendation copy.
Reference auth guard uses a browser-only design fixture; no source file edited. Images `INT-14-design/stitch-*` and `client-*` inspected.

| # | Block | Reference / result | Status |
|---|---|---|---|
| 1 | Layout | labels remain in existing feed span/discovery h2; full-page nav/card positions have inherited differences | Scope preserved; full parity INT-06 pending |
| 2 | Colors | no CSS/token change for modes | Preserved |
| 3 | Typography | existing span/h2 classes, no new font/style | Preserved; whole-page metrics belong INT-06 |
| 4 | Spacing/radius | unchanged by this task; inherited nav/search spacing differs from reference | Full parity pending INT-06 |
| 5 | Icons | no mode icon added/replaced | Preserved |
| 6 | Vietnamese copy | original personalized labels retained; popularity/fallback/legacy mapped explicitly under D18 | PASS scoped override |
| 7 | AI elements | metadata from PG; no personalized claim from HTTP200 or unknown/stub mode | PASS |
| 8 | States | all3modes+legacy tested; existing loading/error/empty regression passes | PASS |
| 9 | Responsive | required390/1440 views, mode strings fit, no body overflow | PASS |
| 10 | CẮT | no follow/comment/translation reintroduced | PASS |

**Full-screen Design Parity is not PASS**; existing INT-06 gaps remain. This checkpoint verifies mode behavior, not overall UI completion.

## Remaining
- Live browser Client→`localhost:8000` login also times out (8s abort); IPv4 gateway and CMS proxy work.
  INT-16 will make Client use the same-origin API proxy pattern so cookies and local transport work together.
- Real AI pipeline/search remains HO-03 (Docker→host8001 timeout); no new INTEGRATED_REAL or personalized production claim.
- Existing feed pagination and full Client design parity remain unfinished. MVP primary popularity behavior is verified independently of v2.

Lane: codex
Changed: public feed contract/generated types; gateway/PG/AI adapter/domain/tests; Client labels/hook/build config; E2E/trackers
Verified: Go checks;5realPG;46Client E2E+8focused modes; FE build/lint/types; live primary/fallback business persistence checks
Contract touched: yes (public OpenAPI0.3.0); AI-API v1.3 consumed unchanged
Next safe task: INT-16 live Client API transport; INT-15 interactions/export

## Latest follow-up2026-10-27
- Earlier transport blockers above are historical: INT-16/17 Client same-origin/security/live sessions verified; INT-11 realAI integration verified.
- INT-19/213aaa9 public0.3.2 cursor/error clarification +e476005 primary/fallback feed/newest/trending cursor implementation complete and deployed.
  Go vet/test/build, generated/schema/FE/E2Etypes, explicit realPG3scenarios/no skips PASS; **4realE2E PASS1.6m** including pagination and original video/search regressions.
- Client scroll loads10→12unique clips, feed3pages, categorynewest/trending2pages each, invalid/mismatched cursor422, no duplicates/exhaustionnull.
  Healthy gateway keeps real6model/stub0/popularity;3pagination videos softdeleted/12clips public404. Full evidence INT-14-pagination.md and accompanying logs/JSON.
- Pagination shortcut in the original report is removed. Overall INT-14 remainsPARTIAL for full Client parity dependencyINT-06; personalized production still INT-03/AI-12.
  No UI style/source changes, no full parity/model-quality/load/soak claim, no master release/push.
