# INT-20 — approved CMS planA contract, 2026-10-28

Owner CODEX. User approved the CMS-only planA after API clarification; four Client library routes remain unapproved.
Release#4 merged without conflict; AI-APIv1.3/checkpoints unchanged. No release/push/shared-plan edit.

OpenAPI0.4.0 adds admin/editor PUT /api/cms/videos/{id} with complete required title/description/editorial hashtags;
validated lengths1–255/10000/30x64, unique Unicode letter/number/underscore tags, explicit empty strings/list for clearing.
No file/status/AI overwrite. Deleted videos404. Adds nullable/read-only source width/height/fps and nullable editorial override tags to VideoDetail.
CategoryWrite extends existing routes with optional description(max2000), preserving name-only callers and omitted/null descriptions on update.
AI proposals remain separate from editorial metadata. Approved deferrals recorded in CONTRACT_DECISIONS.md.

Verified: cached openapi-typescript7.13.0 regenerated CMS/Client types; both direct TypeScript --noEmit PASS.
Cached oapi-codegen2.8.0 regenerated Go models/embedded spec. `go test ./internal/gen -count=1` PASS0.484s;
TestCMSPlanAContract validates the full embedded OpenAPI schema, version, update422/requiredfields/limits and added metadata.
`git diff --check` PASS. Temporary Go generator config points to absolute owned output; no installs/large downloads.

Changed: infra/openapi.yaml; backend/internal/gen/api.gen.go +spec_test.go; CMS/Client api-types.ts; owned coordination.
Next: INT-21 implementation. No runtime or application implementation change in this contract checkpoint.

Lane: codex
Changed: public contract0.4.0 +3generatedtypes +contract check +ownedcoordination
Verified: embedded spec/schema test PASS; CMS/Clienttsc PASS; diffcheck
Contract touched: yes public0.4.0; AI-APIv1.3 unchanged
Next safe task: INT-21
