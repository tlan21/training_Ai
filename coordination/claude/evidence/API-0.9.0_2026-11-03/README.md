# Product API 0.9.0 — discovery/category additions · 2026-11-03 (Claude)

User 2026-11-03: "hãy làm mục A trước" (do all four contract items). OpenAPI-first: contract + regenerated types committed first (83cd1ae),
then backend (85436a3), then UI (32083e5).

## Contract (`infra/openapi.yaml` 0.8.0 → 0.9.0)
- `GET /api/feed?category_id=` — popularity-ranked clips whose own category, else their video's category, matches; cursor bound to the category.
- Popularity feed pages include `view_count` (same definition as CMS: clicks by `client` users).
- `GET /api/cms/videos?sort=newest|category_assigned` — latest category assignment first, unrecorded last; invalid value → 422.
- `Video.category_assigned_at` — nullable, read-only, CMS only; null for assignments made before 0.9.0 (not backfilled).
- Types regenerated with cached oapi-codegen 2.8.0 (Go) and openapi-typescript 7.13.0 (CMS = Client, identical). Enum constants for
  `/api/videos` sort were renamed by the generator (`GetApiVideosParamsSort*`); unused in code.

## Backend / DB
- Migration `infra/postgres/migrations/007_category_assigned_at.sql` (additive `ADD COLUMN IF NOT EXISTS`, nullable) + `001_schema.sql` for fresh
  installs. Applied twice to the live DB: rows 194 → 194, data fingerprint md5 `50964b14…` unchanged, 0 non-null values
  (`mig007_before.txt` / `mig007_after.txt`). Old gateway was unaffected (explicit column lists).
- `SetCategory` stamps `now()` only when the category actually changes; category delete (deleted videos only) clears it.
- Feed: `JOIN videos` replaces the `EXISTS`, category filter `coalesce(clips.category_id, v.category_id)`, `view_count` sub-select;
  category requests always use popularity (personalized stays single-page, INT-03). `view_count` is added only to popularity pages.

## UI
- CMS Categories "Gán video gần đây": `sort=category_assigned`, Stitch "• N phút trước" (vừa xong / phút / giờ / ngày) only when recorded.
- Client Discover: clip rows request `/api/feed?category_id=` (replaces the client-side approximation by loaded video ids).
- Client feed up-next shows real "N lượt xem" now that the feed returns `view_count`.
- Client header: inline suggestions (top 5 `/api/search` text matches with timestamp + matched text, Escape/blur closes, "Xem tất cả kết quả"
  → `/search`; Enter still opens the full page). No Stitch design for the dropdown → Stitch tokens (white card, outline-variant, 12px, shadow-lg).

## Verified (VERIFIED-NOW 2026-11-03)
- Go vet + `go test ./...` PASS; new `TestDiscoveryCategoryContract` (spec), real-PG in gateway container (TEMP tables):
  `TestContentPages_*` incl. new `RealFeedCategoryAndViewCount` (own-category override, client-only clicks = 2, cursor rejected across
  categories), `TestCMSOperationsRealPersistence` (assigned_at set on change, kept on same save, NULL for old rows, sort), `TestCMSFreshSchemaAndSeed`,
  `TestSettingsRepository_RealAtomicPatch` — 7/7 PASS.
- Live read checks on gateway `int09-85436a3` (env hash unchanged): CMS list returns 200 with `sort=category_assigned`, `sort=x` → 422,
  `/api/feed` items carry `view_count`, `/api/feed?category_id=` 200 (popularity).
- CMS + Client images (`int09-32083e5`; Client Dockerfile runs lint + tsc + build). Regression: Client 5 specs + CMS 5 fixture specs
  **175 passed / 4 skipped** (new: header suggestions, discover feed `category_id` request, Categories "• 5 phút trước").
- No live upload/QA data created (UI-only scope); category assignment times will appear as editors assign categories from now on.
