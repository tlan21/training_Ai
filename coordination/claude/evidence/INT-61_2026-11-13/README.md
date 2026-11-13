# INT-61 — Client likes / watch later / user lists / share / playback speed / full library · 2026-11-13 (Claude)

User: "hoàn thành các tính năng phía client … trang chủ: yêu thích, lưu danh sách xem sau, chia sẻ; khám phá: frame video thiếu tốc độ
phát, thêm vào xem sau; lịch sử xem: video đã thích, danh sách xem sau, lịch sử xem, Danh sách của tôi … hoàn thiện toàn bộ các tính năng".
Decisions (AskUserQuestion): unlike / unsave / remove-from-history **keep `user_interactions` events (Two-Tower data), only hide**; user lists **full**.

## Commits
`6849b08` scope · `5792686` API 0.13.0 contract + types (Go + TS, CMS = Client) · `017d1c6` backend (migration 008, repo, handlers, tests) ·
`00b3624` client (data layer, ListPicker, feed / detail / discover / library) · `b307c29` 7 missing icons + discover 390px overflow ·
`07c0002` live spec + fixture mocks + list-count contrast · `dd57b6c` evidence, compose pins, tracker.

## Contract / data
- API 0.13.0, additive: PUT/DELETE `/users/me/likes|saved/{clip_id}`, GET `/users/me/saved`, GET `/users/me/clip-states`, DELETE
  `/users/me/history[/{clip_id}]`, CRUD `/users/me/lists`, `/lists/{id}/items[/{clip_id}]`. `/users/me/likes` keeps its shape; source = like state.
- Migration `008_user_library.sql` (also appended to `init/001_schema.sql` for fresh installs): `user_clip_marks`, `user_history_hidden`,
  `user_history_cleared`, `user_lists` (unique lower(name) per user), `user_list_items`. Applied twice to the live DB:
  `manifest_before.txt` → `manifest_after_migration.txt` — users 51 / videos 197 / clips 79 / interactions 70 and the interactions md5 unchanged;
  8 marks backfilled = the 8 distinct existing like/save pairs.
- First like/save of a clip logs one `like`/`save` interaction (role client) for Two-Tower; the client no longer posts them itself.

## Verified (VERIFIED-NOW)
- Go: vet clean, `go test ./...` 16 packages ok (new `library_test.go` handler tests); real-PG **15/15** in the stack network
  (`pg_real_tests.txt`; new `TestLibraryRepository_RealStateHistoryAndLists`; a real bug found and fixed: `$1` type inference in CreateList).
- Client: `tsc --noEmit` 0 errors, `lint` 0 errors (1 pre-existing warning `AppNav.tsx:51`), `next build` OK — also inside the Linux image build.
- Fixture E2E (mocked API, real client container): `client_design` + `feed_layout` + `client_player` + `client_onboarding_layout` **94/94**
  (2 tests updated for the new behaviour: "Xem sau" + PUT state instead of posted like/save events; watch-later tab now lists saved clips).
- Live E2E `e2e/client_library_live.spec.ts` (opt-in `E2E_INT61_LIVE=1`) **3/3**: API (state, idempotency, 404, 422, history hide/clear, lists:
  trim, case-insensitive 409, cursor pages, rename count, remove) + UI at 1440 and 390 (feed like persists across reload, watch-later tab,
  opening a list, discover speed 1.5× applied to `<video>`, no horizontal overflow) → `live/*.png`, `live/steps.json`.
  Live found two real UI bugs, fixed in `b307c29`: 7 icons missing from the Icon map (fallback "!" glyph) and a long unspaced clip title
  overflowing discover at 390 px (pre-existing, data-dependent).
- The live stack has exactly **2 public clips** (published 2 / draft 7 / rejected 70), so the live spec uses 2.
- QA data: 7 accounts `int61-*@int61-qa.invalid` (one per run) + their 72 events deleted by FK cascade; `live_manifest_before.txt` =
  `live_manifest_after.txt` (incl. sessions 382).

## Deploy
- Gateway `video-ai-gateway:int61-017d1c6` (overlay of `api012-f6bc07f`, host-built binary). Client `video-ai-client:int61-07c0002`
  (`Dockerfile.client-overlay`: source copied onto `int11-843a56e`, lockfile unchanged since then, `.next` rebuilt in Linux with lint + build + tsc).
  Pins in `docker-compose.cms-completion.yml`; rollback = `api012-f6bc07f` / `int11-843a56e` (still local).
- Env hash: gateway `56e23179db570721` before = after. Client differs only by the two build-time variables now in the image config
  (`NEXT_PUBLIC_API_BASE=` empty, `GATEWAY_INTERNAL_URL=http://gateway:8000`, the client/Dockerfile defaults); compose env unchanged.

## Not done / limits
- Client notification bell stays disabled (no API) — out of scope. "Phổ biến nhất" search sort unchanged.
- List cap check and insert are not one lock (two concurrent creates at 49 lists can reach 51) — accepted for a personal cap.
- Library rename/create in the sidebar uses `window.prompt`, delete uses `confirm()` (no new modal component).
