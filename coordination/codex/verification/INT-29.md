# INT-29 — HC-13 deletion contract (2026-10-29)

Public OpenAPI0.4.1: existing DELETE /api/cms/videos/{id} documents idempotent backend cleanup,
409 active-writer conflict and 503 backend-storage retry. No new route/response fields or AI contract edits.
Generated Go embedded spec/models and CMS/Client types from source contract.

Verified: cached openapi-typescript7.13.0 two generations; cached oapi-codegen2.8.0 run with
`go run -mod=readonly ./cmd/oapi-codegen -config E:/traning_ai-codex/backend/.tmp/oapi-pagination.yaml E:/traning_ai-codex/infra/openapi.yaml`
from its read-only module cache (GOPROXY=off). Versioned go-run initially refused offline deprecation lookup;
no download, exact cached source invocation succeeded. `go test ./internal/gen -count=1` PASS1.967s
(schema validation +204/409/503 assertions); CMS and Client `node node_modules/typescript/bin/tsc --noEmit` both exit0.

Lane: codex
Changed: infra/openapi.yaml +three generatedtypes +spec_test.go +ownedcoordination
Verified: generation, schema test and both FE types PASS
Contract touched: yes public0.4.1; AI-APIv2.0 consumed read-only
Next safe task: INT-28 implementation/live cutover
