# INT-37 — HC-15 product threshold metadata contract (2026-10-30)

Owner CODEX. DONE. Startup7722f10; contract checkpoint follows.

Public OpenAPI0.6.0: existing GET /api/cms/videos/{id}/analysis gains nullable clip_threshold (double0..100), reported by AI for that specific analysis; null when absent/legacy, never inferred from Settings. Legacy Settings/SettingsUpdate.highlight_threshold retained/deprecated with truthful description (not an AI control). No endpoint/AI contract change, no client runtime UI change.

Cached oapi-codegen2.8.0/GOPROXYoff and openapi-typescript7.13.0 generated backend embedded spec/models plus CMS/Client types, no downloads. `go test ./internal/gen -count=1` PASS0.600s including schema validation/nullable/bounds/deprecated assertion. CMS/Client `node node_modules/typescript/bin/tsc --noEmit` exit0. Source field from Claude AI-APIv1.4-rc1 DRAFT; no readiness promotion.

Lane: codex
Changed: infra/openapi.yaml, generated Go/CMS/Client types, Go spec test, owned coordination
Verified: cached generation, Go schema test, both FE typechecks PASS
Contract touched: yes public0.6.0; AI schema consumed read-only
Next safe task: INT-38 implementation/compatibility QA
