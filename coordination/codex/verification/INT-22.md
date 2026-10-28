# INT-22 — product database migration004, 2026-10-28

Owner CODEX. User explicitly requested applying migration to product DB; approval/start commit f7fcc0e.
Target: existing video-ai-postgres-1, PostgreSQL16.15, database video_ai, owner app, public.videos/public.categories.
Migration source: infra/postgres/migrations/004_cms_metadata.sql from aad0c75.
SHA256 A47CE01255010990B82C3C0293E06447CB447CC961444F0D887171BA3CBAD7D5.

## Applied and verified

- Preflight: DB9018391bytes,79videos/10categories, all5target columns absent; no transaction older30s.
- Consistent full custom-format pg_dump backup created before DDL, TOC verified contains both table data sections.
  Private ignored file: `backend/.tmp/db-backups/int22-20261028T095827Z-before.dump`,50278bytes.
  SHA256 7C1BB172BD45A524259DE40E947CD1B46A7FD570C59BD7737119D835078A4E89.
  Archive is deliberately not tracked; backup metadata is in INT-22-backup.json. No restore/down migration performed.
- Exact five source ALTER statements executed in INT-22-apply.sql with a guarded transaction, lock_timeout5s,
  statement_timeout30s and ACCESS EXCLUSIVE locks on both targets. Only the source BEGIN/COMMIT markers were replaced
  by the guarded transaction wrapper; no extra product DML, defaults, backfill, schema rewrite or service deployment.
- Before/after row counts and ordered full-row fingerprints matched while locks were held. jsonb_strip_nulls ignores
  newly added null properties so schema-only additions compare equal; existing nonnull data/arrays/timestamps remain included.
  Data/schema mismatch would raise and roll back before COMMIT.
- videos.width/height int4, fps float8, hashtags text[]; categories.description text. All nullable, no defaults.
  All5CHECK constraints exist and are validated; exact definitions preserved in INT-22-verified.json.
- Repeat execution PASS:5already-exists notices, no data change, same counts/fingerprints, COMMIT.
- Verified2026-10-28T10:00:15Z:79videos/10categories; all new metadata values still NULL, as intended for existing records.
- Read-only HTTP checks: gateway /healthz ok; CMS5173 HTTP200; Client3000/login HTTP200. No service recreated/restarted.

Fingerprints on both runs:

| Table | Rows | MD5 of ordered normalized rows |
|---|---:|---|
| public.videos |79|caaadd6588f7f8f4a2da381f51577b9a|
| public.categories |10|2279cd784f346ec1e52ce40605752c91|

Evidence: INT-22-apply.log, INT-22-repeat.log, INT-22-verified.json, INT-22-health.json and INT-22-backup.json.
Guard runner SHA25665908FA2B1A399113D219305D732C1456B6821EEEC054971D5F93DF82950B5B1.
Container /tmp backup/runner copies removed after validation; private host backup retained. Credentials/data rows never printed.
Commands used existing Docker193 daemon and psql Unix socket; no package/image downloads or password changes.

## Current boundary

The live product DB now has004. Gateway/orchestrator/worker/CMS/Client application source remains the prior deployment.
New business endpoints/UI/metadata population still require deploying the verified INT-21 application builds.
No automatic video reprocessing or backfill; old metadata remains unknown. No AI API/model/checkpoint change, master release or push.
No application builds/tests rerun for this DB-only operation; current schema/data checks, repeat test and live health are the relevant gates.

Lane: codex
Changed: live public DB5nullable columns/5checks +owned migration evidence/session/tracker
Verified: backup TOC/hash; guarded apply COMMIT; repeat COMMIT;79/10rows/fingerprints unchanged;5schema/checks;HTTPhealth
Contract touched: no (existing public0.4.0/AI-APIv1.3 unchanged)
Next safe task: INT-05 visuals; application deployment requires its own instruction
