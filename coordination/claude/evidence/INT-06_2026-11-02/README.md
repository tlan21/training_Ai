# INT-06 / INT-04 / INT-14 — Client Design Parity vs Stitch · 2026-11-03 (Claude)

Method: `my-agent/agent/skills/ui_design_review.md`. Reference = `coordination/codex/verification/INT-06-comparison/<screen>-<w>-stitch.png`
+ `stitch_ai_video_platform_vietnamese/<screen>/code.html`. Current = live Client captures (`e2e/client_parity_capture.spec.ts`, opt-in
`E2E_CLIENT_PARITY=1`, one QA viewer `CLAUDE-QA-viewer`, videos paused for stills) in `after/` (client `int06-7d0bd83`, gateway `int06-d41fe71`;
final client `int06-a52a911` only changes the feed up-next meta text). Four read-only review agents produced per-screen tables
(block | Stitch value | current file:line); batch applied in 2a8f9e1 + follow-ups d41fe71, 7d0bd83, a52a911.

## Applied
- Shared: official Material Symbols paths `forward_10`, `download`, `add_photo_alternate` + filled `movie_edit`; duplicate mobile fullscreen
  button fixed (`.icon-button` beat `.desktop-only`).
- Video detail / player (INT-04): mobile center controls `replay_10` 30 · `play_circle` 48 filled · `forward_10` 30 (new, +10 s) · fullscreen 24;
  heatmap 24px with Stitch low/mid/peak colours per breakpoint and peak pulse (on `::after`, so the seek target stays still); desktop 8/4 grid,
  toolbar icons 24, "Tự động phát Highlight" 14px filled icon, quick-action/metadata spacing.
- Feed: every subtitle overlay labelled "Bản nháp phụ đề AI" (HC-12/D23); desktop promo box removed (not in Stitch); up-next meta
  "VidsAI • N lượt xem" only when the API returns `view_count` (public feed does not → clip duration, as before); action colours, desktop sizes.
- Discover (INT-14 presentation): hero "Xem tất cả" is a real link to `/feed` (was fetching a page the 3-item hero never shows);
  "Xem ngay" arrow icon; trending/pill typography; meta line drops the empty category separator.
- Search: desktop upload icon `add_photo_alternate`, Stitch info copy per breakpoint, desktop badge "Khớp: X.X%" (mobile keeps "N% TƯƠNG ĐỒNG").
- Profile/Library: invented sample folders replaced by honest "Chưa có danh sách" (playlists are not an approved feature); desktop title from tab label.
- Onboarding: progress grows with selection, "Đang cá nhân hóa...", per-breakpoint icons, done colour on count.
- Auth: input icons 24, underlined legal terms, "Đang xử lý...".

## Bug found and fixed on the way
- `/api/videos` returned HTTP 500 "Unable to load content" since gateway 74344bb: `ListPublicPage` scanned one column fewer than `videoColumns`
  (migration 006 added `editorial_priority`). Fix 1b719aa; Go vet/test + real-PG `TestContentPages` (TEMP tables, in gateway container) PASS;
  deployed gateway `int06-d41fe71` (env hash unchanged). Discover on real data now loads (`after/current-discover-*.png`).

## Verified (VERIFIED-NOW 2026-11-03)
- Client image build (Dockerfile runs lint + tsc + next build) PASS for 2a8f9e1, d41fe71, 7d0bd83, a52a911.
- Regression: `client_design`, `client_player`, `feed_layout`, `client_onboarding_layout`, `discovery_live` → **96/96 PASS** on the final images
  (first run after 2a8f9e1: 6 failures — heatmap pulse made the seek button unstable ×2, search copy expectation ×1, `/api/videos` 500 ×3; all fixed).
- Not run: `content_pagination_live` (uploads videos → AI jobs) and `client_auth_live` (registers extra users) — outside the approved QA scope;
  `discovery_live` covers the real `/api/videos` path.
- QA data: viewer `usr_81420df3ae2d0d22` deleted (cascade, 25 own interactions); after: users 51, user_interactions 70 (= before QA), no `CLAUDE-QA*` user.
- Preservation (`preservation_report.json`, INT-50 baseline 2026-11-02T07:58Z): all 671 baseline vectors and original rows unchanged. Residuals:
  3 user_interactions by a real user (already noted in INT-50) and 10 vectors of `vid_dmkgihquce5o` (Codex `e2e-int28`, ingested 04:57Z, before
  the baseline) — the baseline Milvus query under-counted. Script fixed: base64 JSON payloads decoded, vectors compared by hash.

## Owner decisions applied (user 2026-11-03: "hãy làm theo đề xuất của bạn")
- Kept and approved: (1) disabled quick-login "Digital Creator", (2) feed mute button + mobile play overlay, (3) "Xem video gốc",
  (5) library per-clip score semantics.
- (4) Follow Stitch (73b13e3, client `int06-73b13e3`): avatar already circular; sizes now match every screen (feed 36, discover 40 + 2px
  `surface-variant` border, library/profile/detail/search 32, mobile header 32). Bottom nav already matched Stitch structure (centre "+" only on
  the feed, 16px lift); now label 11/14px 500 +0.02em, item padding 4×12, nav padding 16, active bold + scale .95, FAB `shadow-lg`.
  Regression 96/96 PASS after the change.
- Deferred (need API changes): (6) inline header search results, (7) category filter for clips.
- Not adopted: Stitch feed creator avatar with "+" follow badge (follow is not an approved feature).

## Still open (INT-06 / INT-04 / INT-14 stay PARTIAL)
Original owner-decision list (for reference):
1. Login quick-login "Digital Creator" (Stitch) — shown disabled; no such auth method.
2. Feed mute button and mobile play overlay — not in Stitch; needed for muted autoplay / paused state.
3. "Xem video gốc" link on feed clips — not in Stitch; links clip → source video.
4. Avatar shape and bottom-nav centre "+" vs Stitch nav.
5. Library heatmap semantics (Stitch shows a per-video heatmap; data is per-clip scores).
6. Header search: Stitch implies inline results; current navigates to `/search`.
7. Discover category chips filter only the video list (clips have no category filter in the public API).
Larger items (L): player seek bar position/tooltip/thumb per Stitch; mobile caption overlaps center controls when paused (390);
public feed `view_count` (OpenAPI change); remaining per-screen micro spacing.
AI lane note: Vietnamese ASR drafts in the captures are low quality (dropped letters) — model issue (AI-05/AI-12), not UI.

## L items (2026-11-03) — client `int06-387ec2a` (+ INT-17 lockfile fix e33e956)
- Player (INT-04) per Stitch: on mobile the AI-draft subtitle (max 2 lines) and the controls row (replay_10 · play_circle · forward_10 left,
  fullscreen right) are stacked in the bottom block above the heatmap — no overlap at 390 (asserted in `client_design`); thin 3px seek line with
  primary fill and 12px thumb with a white ring; "Độ nóng: X%" tooltip on heatmap hover/focus (primary chip on mobile, white card on desktop).
- Regression 96/96 PASS on `int06-387ec2a`.
- Still open: public feed `view_count` (OpenAPI change), header inline search (6) and clip category filter (7) — deferred by the owner.

