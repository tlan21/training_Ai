-- INT-59 cleanup: only rows created by this QA run (manifest: qa_manifest.json). One transaction.
BEGIN;
-- settings keys did not exist before the run (manifest_before.txt); API already put defaults back, now restore exact absence
DELETE FROM system_settings WHERE key IN ('system_name', 'display_timezone', 'notify_failed_jobs', 'notify_uncategorized_videos', 'session_ttl_days');
-- QA accounts (sessions/interactions/preferences cascade); guarded by the reserved .invalid QA domain
DELETE FROM users WHERE email LIKE 'int59-%@int59-qa.invalid' RETURNING id, email;
COMMIT;
