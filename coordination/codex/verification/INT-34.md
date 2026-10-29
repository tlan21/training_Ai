# INT-34 — Compilation product contract

Owner CODEX. DONE. Startup aeecf7d; source checkpoint follows.

User explicitly authorized one highlight compilation from AI-proposed source intervals. Existing POST /api/cms/clips gains auto_highlights=true; normal start/end creation remains supported. Empty proposals return 422. Clip gains source_segments; compiled playback uses 0..total retained duration, preserving source mapping. No new endpoint or AI contract change. OpenAPI 0.5.0, generated Go embedded spec/models and CMS/Client types.

Verified: cached oapi-codegen 2.8.0, cached openapi-typescript 7.13.0, no downloads. `go test ./internal/gen -count=1` PASS 0.602s (schema validation + compilation fields); both CMS/Client `node node_modules/typescript/bin/tsc --noEmit` exit 0. First anyOf generator shape required an unnecessary new dependency; final shape uses documented conditional validation, no added dependency. Initial malformed YAML corrected before successful generations.

Lane: codex
Changed: infra/openapi.yaml, backend/internal/gen/{api.gen.go,spec_test.go}, CMS/Client api-types.ts, owned coordination
Verified: generation, Go schema test, CMS/Client types PASS
Contract touched: yes public 0.5.0; AI contract unchanged
Next safe task: INT-35 implementation
