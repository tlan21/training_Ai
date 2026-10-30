# INT-46 — CMS account simplification contract

User override2026-10-30: no CMS password recovery/account deletion/role-management; pre-provisioned CMS accounts share one management capability. Viewer authentication boundary remains.

- Public OpenAPI0.7.0 removes `PUT /api/cms/users/{id}/role`, makes `GET /api/cms/users?page&q` explicitly read-only/searchable; Settings writes describe CMS management access, not an admin/editor permission matrix. User.role remains an internal account-type/legacy login field, not editable from CMS.
- No CMS account-delete endpoint/implementation exists. No user data/schema deletion.
- Shared Client forgot/reset consumers confirmed. CMS UI removal and backend denial of recovery for management accounts is implementation scope; retain still-used Client API until user clarification. No broken Client links introduced by this contract.
- Regenerated Go embedded spec and CMS/Client types using cached oapi-codegen2.8.0/openapi-typescript7.13.0, no downloads.
- `go test ./internal/gen -run 'TestCMS|TestSingleCMS' -count=1` PASS0.566s, schema validation included. CMS `tsc --noEmit` PASS; Client `tsc --noEmit --incremental false` PASS.

Lane: codex
Changed: OpenAPI, generated3types, spec gate, owned scope/checkpoint docs
Verified: schema test and both frontend typechecks
Contract touched: yes public0.7.0, no AI contract change
Next safe task: INT-47 actual cleanup; then INT-48 operational contract and existing41..44
