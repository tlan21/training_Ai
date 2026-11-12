-- INT-59 read-only manifest (AI key masked)
SELECT 'setting', key, CASE WHEN key = 'ai_service_api_key' THEN '<masked>' ELSE value END FROM system_settings ORDER BY key;
SELECT 'count', 'users', count(*)::text FROM users;
SELECT 'count', 'admins', count(*)::text FROM users WHERE role = 'admin';
SELECT 'count', 'editors', count(*)::text FROM users WHERE role = 'editor';
SELECT 'count', 'sessions', count(*)::text FROM user_sessions;
SELECT 'count', 'qa_int59_users', count(*)::text FROM users WHERE email LIKE '%@int59-qa.invalid';
SELECT 'fingerprint', 'users_pw', md5(string_agg(id || password_hash || role, ',' ORDER BY id)) FROM users WHERE email NOT LIKE '%@int59-qa.invalid';
