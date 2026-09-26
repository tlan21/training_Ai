-- 002_seed.sql — dữ liệu khởi tạo bắt buộc (T0.2). Chạy sau 001_schema.sql.

-- 10 danh mục (khớp ViT 10 lớp — model_spec §2, dataset_spec §3.1)
INSERT INTO categories (name) VALUES
    ('Bóng đá'),
    ('Thể thao'),
    ('Game'),
    ('Ca nhạc'),
    ('Tin tức'),
    ('Giải trí'),
    ('Giáo dục'),
    ('Du lịch'),
    ('Ẩm thực'),
    ('Công nghệ')
ON CONFLICT (name) DO NOTHING;

-- Admin mặc định. Mật khẩu 'admin123' băm bcrypt qua pgcrypto (tương thích golang.org/x/crypto/bcrypt).
-- ĐỔI mật khẩu ngay sau lần đăng nhập đầu ở môi trường thật.
INSERT INTO users (username, email, password_hash, role) VALUES
    ('admin', 'admin@local', crypt('admin123', gen_salt('bf', 10)), 'admin')
ON CONFLICT (email) DO NOTHING;

-- system_settings (database_schema §2 dòng 154-160)
-- ai_service_api_key: PLACEHOLDER — thay bằng key thật (python -m app.gen_key) trước khi chạy production.
INSERT INTO system_settings (key, value) VALUES
    ('highlight_threshold',   '75'),
    ('asr_warning_threshold', '65'),
    ('auto_highlight_enabled','true'),
    ('auto_subtitle_enabled', 'true'),
    ('default_subtitle_lang', 'vi'),
    ('ai_service_api_key',    'sk-local-CHANGE-ME')
ON CONFLICT (key) DO NOTHING;
