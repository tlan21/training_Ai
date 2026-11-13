# INT-64 — Notification read state, AI categories, CMS bell "seen", feed player + up next · 2026-11-13 (Claude)

User: "các thông báo khi đọc chưa được đánh dấu là đã đọc và khi đọc tất cả các số hiện thông báo không mất ở cả client lẫn cms và các
video hiện theo chủ đề trong khám phá theo các tag category cũng chưa hiển thị các hightlight mới, đang thịnh hành, phổ biến có vẻ api trả null
và kiểm tra có phải đang dùng AI model gợi ý không. Phần trang chủ mục sắp phát tiếp hơi thô … frame video cần thêm play pause mặc định là
tự động phát và khi hết tự động chuyển sang reels khác và reels cần mặc định bật âm thanh hãy kiểm tra logic".

## Findings (before changing anything)
| # | Report | Root cause |
|---|---|---|
| 1 | Client notifications not marked read | API + UI correct in a fresh browser (4→3→0). The user's account was hit by the INT-63 shared-cookie bug: after logging into the CMS as admin, the Client tab refreshed into the admin session, so "read" ran for admin. Fixed by INT-63; re-verified below with both apps signed in. |
| 2 | CMS bell number never clears | The CMS bell is a live count (failed jobs + uncategorized videos) with no read state. |
| 3 | Discover by category empty | APIs return `[]`, not null: 0 of the 4 videos with public clips had a category. The ViT suggested correctly (football → bong_da, news → tin_tuc) but the design required an editor to confirm and nobody had. |
| 4 | Is the AI recommender used? | No. Feed `recommendation_mode = popularity`; the Two-Tower recommender stays off by decision D18 until the v2 production gate passes. |
| 5 | Feed | `<video loop>` (never ends → no next reel), `muted` default true, play button hidden while playing, "Sắp phát tiếp" = tall portrait links that leave the feed. |

User decisions: auto-apply AI category (setting, default on) + "approve all suggestions" button run on existing videos; CMS bell "seen" = only new, stored per account on the server.

## Changes
- API 0.15.0 (additive): `Settings.category_auto_apply`; `POST /api/cms/videos/apply-category-suggestions` → `{applied, skipped}`;
  `GET/PUT /api/cms/me/alerts-seen` (`AlertsSeen`). Migration `010_cms_alert_seen.sql` (applied twice, data unchanged: `manifest_*`).
- Orchestrator: after storing the category match, assigns it when `category_auto_apply` and the video has no category (editor choice kept).
- CMS: bell badge = sum of max(0, live − seen); opening the bell saves the snapshot but keeps the "+n mới" labels visible while open;
  Settings › Cấu hình AI "Tự gán danh mục AI"; Danh mục "Duyệt tất cả gợi ý AI".
- Client feed (fork, `55eaa9a`): autoplay with sound (muted fallback + "Bật âm thanh" when the browser blocks it), one tab-wide sound
  preference, play/pause in the controls row, no loop → next reel on end, compact "Sắp phát tiếp" queue that scrolls the feed.
- Data: "Duyệt tất cả gợi ý AI" run once on the live stack: applied 6 / skipped 0 (`categories_before.txt` → `categories_after.txt`:
  4 football videos → Bóng đá, 2 news videos → Tin tức).

## Commits
`2aae90d` scope · `cb2200b` contract · `55eaa9a` client feed · `90f2387` + `bf3cab8` backend · `9c20edf` + `3d9b54c` CMS ·
`bbd47fd` specs, evidence, pins, tracker.

## Verified (VERIFIED-NOW)
- Go vet clean, all packages ok (new `TestSuggestCategoryAutoApply`, `TestApplyCategorySuggestions`); real-PG **17/17** (new CMS alerts repo test).
- CMS tsc + build; fixtures cms_design + cms_int59_settings_users + cms_auth **79/79** (INT-59 spec updated for the "+n mới" labels,
  the seen snapshot and the new AI-group field). Client tsc/lint/build; fixtures client_design + feed_layout + client_player +
  client_onboarding_layout **94/94**. INT-59 evidence screenshots rewritten by the fixture run were restored from git.
- Live `e2e/int64_live.spec.ts` **2/2** (one browser, both apps signed in): client read-one 2→1, read-all 1→0 and still 0 after reload;
  CMS badge "(1)" for one new uncategorized QA video → open → reload → no badge; Khám phá › Bóng đá 2 clips at 1440 and 390; feed
  autoplays (muted=false in Chromium), loop=false, pause/play works, reel 1 end → reel 2 plays (`live/steps.json`, screenshots).
- QA data: 2 QA client accounts (one from the investigation) + 1 QA video deleted; the admin bell snapshot created by the test deleted;
  final counts users 51 (50 client + 1 admin), notifications 100, alert_seen 0.

## Deploy
gateway `int64-9c20edf` (overlay of int63-193bcfe), CMS `int64-3d9b54c`, client `int64-9c20edf` (overlay of int11-843a56e);
env hashes unchanged; pins in `docker-compose.cms-completion.yml`; rollback = int63 / int62 tags.

## Limits
- Browsers may block autoplay with sound until the first user interaction; the feed then plays muted with a "Bật âm thanh" button.
- The recommender is still popularity-based (D18); category tabs depend on videos having a category (now automatic for new videos).
