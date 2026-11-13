-- 0.13.0 (INT-61): personal library state. Additive and repeatable. user_interactions stays the append-only event log
-- (Two-Tower input); these tables only hold what the user currently sees. User decision 2026-11-13: unlike / unsave /
-- remove-from-history only change visibility, the events are kept.

CREATE TABLE IF NOT EXISTS user_clip_marks (
    user_id    VARCHAR(50) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    clip_id    VARCHAR(50) NOT NULL REFERENCES clips(id) ON DELETE CASCADE,
    kind       VARCHAR(10) NOT NULL CHECK (kind IN ('like', 'save')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, kind, clip_id)
);
CREATE INDEX IF NOT EXISTS idx_user_clip_marks_recent ON user_clip_marks (user_id, kind, created_at DESC, clip_id DESC);

-- Existing likes/saves were only events; keep them visible (latest event time per user/clip/kind).
INSERT INTO user_clip_marks (user_id, clip_id, kind, created_at)
SELECT user_id, clip_id, interaction_type, max(created_at)
FROM user_interactions
WHERE interaction_type IN ('like', 'save') AND user_id IS NOT NULL AND clip_id IS NOT NULL
GROUP BY user_id, clip_id, interaction_type
ON CONFLICT DO NOTHING;

-- History views at or before hidden_at are not listed; watching again later shows the clip again.
CREATE TABLE IF NOT EXISTS user_history_hidden (
    user_id   VARCHAR(50) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    clip_id   VARCHAR(50) NOT NULL REFERENCES clips(id) ON DELETE CASCADE,
    hidden_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, clip_id)
);
CREATE TABLE IF NOT EXISTS user_history_cleared (
    user_id    VARCHAR(50) PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    cleared_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_lists (
    id         VARCHAR(50) PRIMARY KEY DEFAULT 'lst_' || replace(uuid_generate_v4()::text, '-', ''),
    user_id    VARCHAR(50) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name       VARCHAR(60) NOT NULL CHECK (char_length(btrim(name)) BETWEEN 1 AND 60),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_user_lists_name ON user_lists (user_id, lower(name));
CREATE INDEX IF NOT EXISTS idx_user_lists_recent ON user_lists (user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS user_list_items (
    list_id  VARCHAR(50) NOT NULL REFERENCES user_lists(id) ON DELETE CASCADE,
    clip_id  VARCHAR(50) NOT NULL REFERENCES clips(id) ON DELETE CASCADE,
    added_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (list_id, clip_id)
);
CREATE INDEX IF NOT EXISTS idx_user_list_items_recent ON user_list_items (list_id, added_at DESC, clip_id DESC);
