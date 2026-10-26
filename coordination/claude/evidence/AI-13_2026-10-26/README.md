# AI-13 evidence — 2026-10-26 (VERIFIED-NOW)

- RED: tests/test_api.py 2 failed (metadata giả `Video <id>`/`https://storage.local/...`, chưa có recommendation_mode) → GREEN; suite inference 53 passed / 7 skipped.
- Live :8011 tạm trỏ sandbox: `reco_sandbox.json` — 200, recommendation_mode=personalized, title/thumbnail_url null.
- Live :8001 product (restart, PID 16808): recommendation 503 AI_UNAVAILABLE (collection product chưa có → gateway popularity/fallback); smoke 6/6 (`smoke_8001.txt`).
- OpenAPI: Recommendation.title/thumbnail_url nullable, không còn required; RecommendationResponse thêm recommendation_mode (required).
