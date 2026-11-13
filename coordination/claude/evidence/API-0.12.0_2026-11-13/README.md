# INT-60 — CMS/Client vs latest changes + models; CMS shows running AI model versions · 2026-11-13 (Claude)

User: "hãy thiết kế và kiểm tra cập nhật code cms và client tương ứng với các thay đổi mới nhất và các models mới nhất" → AskUserQuestion → **"Làm đầy đủ"**.

## Audit (before any change)
- Active checkpoints `ai-core/checkpoints/*/best.pt` = AI_API_CONTRACT §1 SHAs (vit 192d90e4, siamese b4ded465, asr_ctc 7c497d43,
  highlight_fusion 5aecd5c4, minigpt 8a62e953, two_tower f28c3794) = files mounted in `video-ai-inference-service-1`; container started after the last
  checkpoint change (2026-11-05); `/health` 6/6 loaded, stub_mode false.
- `cms/src/api-types.ts` and `client/src/api-types.ts` regenerated from OpenAPI 0.11.1 with openapi-typescript 7.13.0 → **no diff**.
  0.11.0 added only `/api/cms/...` paths → Client needs no UI change. No model names/metrics hard-coded in CMS/Client.
- Only gap: the CMS showed "AI available / not", not which checkpoints are running.

## Change
| Layer | Commit | What |
|---|---|---|
| AI-API v3.3 | `e47c9c8` | `/health.models[] = {name, file, sha256}` of each checkpoint really loaded (hashed at load, ~2 s); remote worker via `/info.checkpoints`; additive, default `[]` |
| API 0.12.0 | `fd0161d` | `SystemHealth.ai_models` (`AIModelCheckpoint`), gateway passes it through; `[]` when AI is down / older image. oapi-codegen 2.8.0 + openapi-typescript 7.13.0 (CMS = Client) |
| CMS | `f6bc07f` | `AIModelList`: Dashboard "Model AI" (`6/6 model đang chạy` + list) and the top-bar "Trạng thái hệ thống" popover; short SHA, full SHA256 in `title` |

## Verified (VERIFIED-NOW)
- inference-service pytest **65 passed** (new `test_health_reports_loaded_checkpoints`, stub → `models == []`); real load of the 6 active checkpoints → exactly the §1 SHAs.
- backend `go vet ./...` clean, `go test -count=1 ./...` **16 packages ok** (`spec_test` 0.12.0, `operations_test` ai_models pass-through).
- CMS `tsc --noEmit` + `vite build`; Client `tsc --noEmit` (types only). CMS fixture specs `cms_design`, `cms_int59_settings_users`, `cms_auth`: **79 passed**
  (old fixtures without `ai_models` use the previous text). The fixture run rewrote INT-59 screenshots → restored from git (history kept as is).
- Deploy (overlays, `Dockerfile.*-overlay` here; C: 6.7 GB free): `video-ai-inference:ai-v3.3-f6bc07f`, `video-ai-gateway:api012-f6bc07f`,
  `video-ai-cms:api012-f6bc07f`; `up -d --no-deps --no-build` with empty `--env-file` + AI key from the inference container (not printed).
  Env hash before = after: gateway `56e23179db570721`, cms `b3f8fe29fb2cde11`, inference `d6bd130ad5872bbd`. All healthy. Pins in
  `docker-compose.inference.yml` / `docker-compose.cms-completion.yml`. Inference was previously started from the Codex worktree compose; its file is
  identical except the image tag.
- Live `e2e/cms_ai_models_live.spec.ts` (opt-in `E2E_AI_MODELS_LIVE=1`, read-only, admin@local): **2/2** at 1440 and 390 — API `ai_models` = §1 SHAs,
  6 list items, `6/6 model đang chạy`, no horizontal overflow, popover lists 6 → `live/dashboard-{1440,390}.png`, `live/popover-1440.png`, `live/health-*.json`.
  Data: no business data written. The first 2 runs logged out without a Bearer token (401) → 4 admin@local refresh sessions left; they expire with the
  session TTL (7 days). Not revoked with "revoke others" because that would also log out the user's own admin browser sessions.

Rollback: images `ai-v3.0-48735ff` / `int59-3c3b33b` (still local), revert the two compose pins.
