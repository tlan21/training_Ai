-- 0.14.0 (INT-62): in-app notifications, filled by the Kafka consumer `gateway-notifications` (topic clip.published).
-- Additive and repeatable. One row per (user, kind, clip): a redelivered event never duplicates a notification.
CREATE TABLE IF NOT EXISTS user_notifications (
    id         BIGSERIAL PRIMARY KEY,
    user_id    VARCHAR(50) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kind       VARCHAR(30) NOT NULL CHECK (kind IN ('clip_published')),
    clip_id    VARCHAR(50) NOT NULL REFERENCES clips(id) ON DELETE CASCADE,
    video_id   VARCHAR(50) NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    title      VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    read_at    TIMESTAMPTZ,
    UNIQUE (user_id, kind, clip_id)
);
CREATE INDEX IF NOT EXISTS idx_user_notifications_recent ON user_notifications (user_id, id DESC);
CREATE INDEX IF NOT EXISTS idx_user_notifications_unread ON user_notifications (user_id) WHERE read_at IS NULL;
