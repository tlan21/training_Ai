-- 0.15.0 (INT-64): CMS bell "seen" snapshot per account. The bell shows only what grew since this snapshot
-- (new failed jobs / newly uncategorized videos). Additive and repeatable.
CREATE TABLE IF NOT EXISTS cms_alert_seen (
    user_id              VARCHAR(50) PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    failed_jobs          INT NOT NULL DEFAULT 0 CHECK (failed_jobs >= 0),
    uncategorized_videos INT NOT NULL DEFAULT 0 CHECK (uncategorized_videos >= 0),
    seen_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
