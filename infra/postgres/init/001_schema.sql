-- 001_schema.sql — DDL PostgreSQL (nguồn: .claude/database_schema.md §2). T0.2.
-- Chạy tự động khi container postgres khởi tạo (thư mục /docker-entrypoint-initdb.d).

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_salt/crypt cho seed admin (bcrypt $2a$)

-- 1. users
CREATE TABLE users (
    id VARCHAR(50) PRIMARY KEY DEFAULT 'usr_' || replace(uuid_generate_v4()::text, '-', ''),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    avatar_url VARCHAR(512),
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'client' CHECK (role IN ('admin', 'editor', 'client')),
    training_origin TEXT NOT NULL DEFAULT 'unknown' CHECK (training_origin IN ('unknown', 'product', 'test')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. videos
CREATE TABLE videos (
    id VARCHAR(50) PRIMARY KEY DEFAULT 'vid_' || replace(uuid_generate_v4()::text, '-', ''),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    raw_file_path VARCHAR(512) NOT NULL,
    thumbnail_url VARCHAR(512),
    duration_seconds NUMERIC(10, 2) NOT NULL,
    width INTEGER CHECK (width > 0),
    height INTEGER CHECK (height > 0),
    fps DOUBLE PRECISION CHECK (fps > 0 AND fps < 'Infinity'::float8),
    hashtags TEXT[] CHECK (cardinality(hashtags) <= 30),
    editorial_priority VARCHAR(8) NOT NULL DEFAULT 'normal' CHECK(editorial_priority IN ('low','normal','high')),
    category_assigned_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'uploaded'
        CHECK (status IN ('uploaded', 'processing', 'processed', 'failed', 'deleted')),
    uploaded_by VARCHAR(50) REFERENCES users(id) ON DELETE SET NULL,
    training_origin TEXT NOT NULL DEFAULT 'unknown' CHECK (training_origin IN ('unknown', 'product', 'test')),
    deleted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. video_processing_jobs
CREATE TABLE video_processing_jobs (
    id VARCHAR(50) PRIMARY KEY DEFAULT 'job_' || replace(uuid_generate_v4()::text, '-', ''),
    video_id VARCHAR(50) UNIQUE REFERENCES videos(id) ON DELETE CASCADE,
    queue_name VARCHAR(50) NOT NULL DEFAULT 'video_ingest_queue',
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    worker_node_id VARCHAR(50),
    error_log TEXT,
    current_stage VARCHAR(30)
        CHECK (current_stage IS NULL OR current_stage IN
            ('splitting_frames', 'embedding', 'asr_extracting', 'highlight_scoring', 'summarizing', 'completed')),
    progress SMALLINT NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
    processing_options JSONB,
    skipped_stages TEXT[] NOT NULL DEFAULT '{}',
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. categories (đặt trước clips/videos FK category_id)
CREATE TABLE categories (
    id VARCHAR(50) PRIMARY KEY DEFAULT 'cat_' || replace(uuid_generate_v4()::text, '-', ''),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT CHECK (char_length(description) <= 2000),
    keywords TEXT[] NOT NULL DEFAULT '{}' CHECK(cardinality(keywords)<=20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. clips
CREATE TABLE clips (
    id VARCHAR(50) PRIMARY KEY DEFAULT 'clp_' || replace(uuid_generate_v4()::text, '-', ''),
    video_id VARCHAR(50) REFERENCES videos(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    start_time NUMERIC(10, 2) NOT NULL,
    end_time NUMERIC(10, 2) NOT NULL,
    average_score NUMERIC(5, 2) NOT NULL CHECK (average_score >= 0.00 AND average_score <= 100.00),
    source_segments JSONB NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(source_segments) = 'array' AND jsonb_array_length(source_segments) <= 100),
    clip_file_path VARCHAR(512),
    thumbnail_url VARCHAR(512),
    status VARCHAR(20) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'processing', 'published', 'rejected')),
    created_by VARCHAR(50) REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. user_interactions (đầu vào Two-Tower)
CREATE TABLE user_interactions (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES users(id) ON DELETE CASCADE,
    video_id VARCHAR(50) REFERENCES videos(id) ON DELETE CASCADE,
    interaction_type VARCHAR(20) NOT NULL
        CHECK (interaction_type IN ('click', 'watch_time', 'like', 'share', 'skip', 'save')),
    duration_watched INT DEFAULT 0,
    clip_id VARCHAR(50) REFERENCES clips(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. user_sessions (JWT refresh)
CREATE TABLE user_sessions (
    id VARCHAR(50) PRIMARY KEY DEFAULT 'ses_' || replace(uuid_generate_v4()::text, '-', ''),
    user_id VARCHAR(50) REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. user_preferences (onboarding categories)
CREATE TABLE user_preferences (
    user_id VARCHAR(50) REFERENCES users(id) ON DELETE CASCADE,
    category_id VARCHAR(50) REFERENCES categories(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, category_id)
);

-- 9. category_id trên videos/clips (Admin duyệt mới ghi)
ALTER TABLE videos ADD COLUMN category_id VARCHAR(50) REFERENCES categories(id);
ALTER TABLE clips  ADD COLUMN category_id VARCHAR(50) REFERENCES categories(id);

-- 12. system_settings
CREATE TABLE system_settings (
    key VARCHAR(50) PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes (§2.2)
CREATE INDEX idx_jobs_status_queue ON video_processing_jobs (status, queue_name);
CREATE INDEX idx_clips_video_id ON clips (video_id);
CREATE INDEX idx_clips_status ON clips (status);
CREATE INDEX idx_interactions_user_video ON user_interactions (user_id, video_id);
CREATE INDEX idx_interactions_type ON user_interactions (interaction_type);
CREATE INDEX idx_user_preferences_category ON user_preferences (category_id);

-- 0.13.0 (INT-61) personal library — same as migrations/008_user_library.sql (existing DBs apply that file).

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
