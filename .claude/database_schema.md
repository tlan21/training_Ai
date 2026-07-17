# ĐẶC TẢ THIẾT KẾ CƠ SỞ DỮ LIỆU (DATABASE SPECIFICATION)
## HỆ THỐNG PHÂN TÍCH VIDEO, CẮT HIGHLIGHT VÀ GỢI Ý NỘI DUNG TỰ HUẤN LUYỆN
*Tài liệu thiết kế chi tiết cơ sở dữ liệu quan hệ (PostgreSQL), phi quan hệ (MongoDB) và cơ sở dữ liệu Vector (Milvus).*

---

## 1. Kiến trúc Tổng quan & Phân bổ Lưu trữ (Storage Strategy)

Để đáp ứng hiệu năng xử lý video thời gian thực, lưu trữ hàng triệu vector embedding và đồng bộ dữ liệu phi cấu trúc (phụ đề ASR, timeline heatmap), hệ thống sử dụng kiến trúc cơ sở dữ liệu lai (Hybrid Database Architecture):

```
                                  ┌──────────────────────────┐
                                  │      Client / CMS        │
                                  └────┬──────┬─────────┬────┘
                                       │      │         │
                ┌──────────────────────┘      │         └──────────────────────┐
                ▼ (Dữ liệu quan hệ, ACID)     ▼ (Dữ liệu phi cấu trúc)         ▼ (Tìm kiếm vector đa chiều)
     ┌────────────────────────────┐  ┌────────────────────────────┐  ┌────────────────────────────┐
     │        PostgreSQL          │  │          MongoDB           │  │            Milvus          │
     │ - Thông tin người dùng     │  │ - Phụ đề thô (Full text)   │  │ - Vector đặc trưng ảnh     │
     │ - Siêu dữ liệu video, clip │  │ - Điểm số Highlight chi tiết│  │   (Vision Embeddings)      │
     │ - Trạng thái Job Queue     │  │   (Timeline heatmap JSON)  │  │ - Vector sở thích User     │
     │ - Nhật ký phê duyệt        │  │ - Tóm tắt văn bản thô      │  │   (User Profile Vector)    │
     └────────────────────────────┘  └────────────────────────────┘  └────────────────────────────┘
```

---

## 2. Đặc tả Chi tiết Cơ sở dữ liệu Quan hệ (PostgreSQL Schema)

PostgreSQL đóng vai trò là "Nguồn sự thật" (Source of Truth) cho các thực thể mang tính giao dịch, bảo đảm toàn vẹn dữ liệu thông qua ràng buộc khóa ngoại (Foreign Key) và quy chuẩn ACID.

### 2.1. Sơ đồ các Bảng (DDL SQL)

```sql
-- Kích hoạt extension để sinh UUID tự động nếu cần
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. BẢNG NGƯỜI DÙNG (users)
CREATE TABLE users (
    id VARCHAR(50) PRIMARY KEY DEFAULT 'usr_' || replace(uuid_generate_v4()::text, '-', ''),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    avatar_url VARCHAR(512),
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'client' CHECK (role IN ('admin', 'editor', 'client')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. BẢNG VIDEO GỐC (videos)
CREATE TABLE videos (
    id VARCHAR(50) PRIMARY KEY DEFAULT 'vid_' || replace(uuid_generate_v4()::text, '-', ''),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    raw_file_path VARCHAR(512) NOT NULL, -- Đường dẫn lưu trên Object Storage (MinIO)
    thumbnail_url VARCHAR(512), -- URL/đường dẫn thumbnail cho CMS/Client
    duration_seconds NUMERIC(10, 2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'uploaded' CHECK (status IN ('uploaded', 'processing', 'processed', 'failed', 'deleted')),
    uploaded_by VARCHAR(50) REFERENCES users(id) ON DELETE SET NULL,
    deleted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. BẢNG TIẾN TRÌNH XỬ LÝ (video_processing_jobs)
-- Quản lý hàng đợi Kafka điều phối GPU/CPU worker
CREATE TABLE video_processing_jobs (
    id VARCHAR(50) PRIMARY KEY DEFAULT 'job_' || replace(uuid_generate_v4()::text, '-', ''),
    video_id VARCHAR(50) UNIQUE REFERENCES videos(id) ON DELETE CASCADE,
    queue_name VARCHAR(50) NOT NULL DEFAULT 'video_ingest_queue',
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    worker_node_id VARCHAR(50),
    error_log TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. BẢNG PHÂN PHỐI CLIP HIGHLIGHT (clips)
-- Lưu thông tin các phân đoạn highlight được cắt tự động hoặc tinh chỉnh bởi Admin
CREATE TABLE clips (
    id VARCHAR(50) PRIMARY KEY DEFAULT 'clp_' || replace(uuid_generate_v4()::text, '-', ''),
    video_id VARCHAR(50) REFERENCES videos(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    start_time NUMERIC(10, 2) NOT NULL,
    end_time NUMERIC(10, 2) NOT NULL,
    average_score NUMERIC(5, 2) NOT NULL CHECK (average_score >= 0.00 AND average_score <= 100.00),
    clip_file_path VARCHAR(512), -- Video segment (.mp4) đã cắt và xuất bản
    thumbnail_url VARCHAR(512), -- Thumbnail/feed card; nếu NULL backend dùng thumbnail video gốc
    status VARCHAR(20) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'processing', 'published', 'rejected')),
    created_by VARCHAR(50) REFERENCES users(id) ON DELETE SET NULL, -- Admin/Editor hoặc hệ thống AI
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. BẢNG TƯƠNG TÁC NGƯỜI DÙNG (user_interactions)
-- Cơ sở dữ liệu đầu vào cho mô hình Two-Tower Recommendation
CREATE TABLE user_interactions (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(50) REFERENCES users(id) ON DELETE CASCADE,
    video_id VARCHAR(50) REFERENCES videos(id) ON DELETE CASCADE,
    interaction_type VARCHAR(20) NOT NULL CHECK (interaction_type IN ('click', 'watch_time', 'like', 'share', 'skip', 'save')),
    duration_watched INT DEFAULT 0, -- Thời lượng đã xem bằng giây (cho watch_time)
    clip_id VARCHAR(50) REFERENCES clips(id) ON DELETE CASCADE, -- Feed hiển thị clip; NULL nếu tương tác trên video gốc
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. BẢNG DANH MỤC (categories) — kien_truc mục 6.2 yêu cầu, bổ sung để đủ FK
CREATE TABLE categories (
    id VARCHAR(50) PRIMARY KEY DEFAULT 'cat_' || replace(uuid_generate_v4()::text, '-', ''),
    name VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. BẢNG PHIÊN ĐĂNG NHẬP (user_sessions) — JWT Refresh Token (kien_truc mục 6.2)
CREATE TABLE user_sessions (
    id VARCHAR(50) PRIMARY KEY DEFAULT 'ses_' || replace(uuid_generate_v4()::text, '-', ''),
    user_id VARCHAR(50) REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. BẢNG SỞ THÍCH NGƯỜI DÙNG (user_preferences)
-- Lưu category onboarding để GET /api/users/me không phải đọc ngược từ Milvus.
CREATE TABLE user_preferences (
    user_id VARCHAR(50) REFERENCES users(id) ON DELETE CASCADE,
    category_id VARCHAR(50) REFERENCES categories(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, category_id)
);

-- 9. Cột danh mục: AI chỉ ghi category_suggestion (MongoDB);
--    Admin phê duyệt tại CMS mới ghi cột này (nguyên tắc kien_truc 6.3.3)
ALTER TABLE videos ADD COLUMN category_id VARCHAR(50) REFERENCES categories(id);
ALTER TABLE clips  ADD COLUMN category_id VARCHAR(50) REFERENCES categories(id);

-- 10. Giai đoạn chi tiết cho Job Queue Monitor của CMS
--    ('splitting_frames', 'asr_extracting', 'highlight_scoring', 'embedding', 'summarizing')
ALTER TABLE video_processing_jobs ADD COLUMN current_stage VARCHAR(30)
    CHECK (current_stage IS NULL OR current_stage IN ('splitting_frames', 'embedding', 'asr_extracting', 'highlight_scoring', 'summarizing', 'completed'));

-- 11. Tiến độ % thô cho Job Queue Monitor (UI Stitch hiển thị %)
--     Orchestrator cập nhật theo stage: splitting_frames=20, asr=40, highlight=60, embedding=80, summarizing=90, completed=100
ALTER TABLE video_processing_jobs ADD COLUMN progress SMALLINT NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100);

-- 12. BẢNG CẤU HÌNH HỆ THỐNG (system_settings) — màn Cài đặt CMS, tab "Cấu hình AI"
CREATE TABLE system_settings (
    key VARCHAR(50) PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
-- Seed bắt buộc (T0.2):
--   'highlight_threshold'      = '75'   (ngưỡng gợi ý AI, slider 0–100 ở Settings; dùng cho vùng đỏ heatmap + gom clip)
--   'asr_warning_threshold'    = '65'   (dưới ngưỡng % này segment phụ đề gắn warning low_confidence)
--   'auto_highlight_enabled'   = 'true'
--   'auto_subtitle_enabled'    = 'true'
--   'default_subtitle_lang'    = 'vi'   (chỉ 'vi' — ASR from-scratch chỉ train tiếng Việt)
--   'ai_service_api_key'       = 'sk-local-<random>' (key của inference-service :8001 TỰ DỰNG — không phải OpenAI; API GET trả masked)

-- Field trả API nhưng không lưu DB:
-- playback_url được backend sinh từ raw_file_path/clip_file_path bằng MinIO presigned URL.
```

### 2.2. Chiến lược Tự động Lập chỉ mục (Auto-Indexing & Optimization Strategy)

Để đảm bảo truy vấn tối ưu khi hệ thống mở rộng, các chỉ mục (Indexes) sau bắt buộc phải được tạo:

```sql
-- 1. Index tìm kiếm nhanh công việc xử lý video của Worker
CREATE INDEX idx_jobs_status_queue ON video_processing_jobs (status, queue_name);

-- 2. Index liên kết khóa ngoại phục vụ các câu truy vấn JOIN
CREATE INDEX idx_clips_video_id ON clips (video_id);
CREATE INDEX idx_clips_status ON clips (status);

-- 3. Index phục vụ gom nhóm phân tích hành vi của Two-Tower Recommendation
CREATE INDEX idx_interactions_user_video ON user_interactions (user_id, video_id);
CREATE INDEX idx_interactions_type ON user_interactions (interaction_type);

-- 4. Index sở thích onboarding
CREATE INDEX idx_user_preferences_category ON user_preferences (category_id);
```

---

## 3. Đặc tả Cơ sở dữ liệu Phi quan hệ (MongoDB Schema)

MongoDB được sử dụng để lưu các tài liệu lớn, có cấu trúc lồng nhau (nested JSON) thay đổi liên tục, giúp tránh việc phình to cơ sở dữ liệu quan hệ PostgreSQL và tăng tốc độ đọc dữ liệu đồng bộ (Sync Engine) phía Client.

### 3.1. Collection `subtitles` (Phụ đề chi tiết từ ASR Transformer)
Mỗi document lưu trữ kết quả phân tích giọng nói của một Video nguyên thủy.

```json
{
  "_id": "sub_video001_1783584000",
  "video_id": "vid_abc123xyz",
  "language": "vi",
  "full_transcript": "Chào mừng các bạn đã quay trở lại với trận đấu siêu kinh điển ngày hôm nay...",
  "segments": [
    {
      "segment_index": 0,
      "start_time": 0.00,
      "end_time": 3.50,
      "text": "Chào mừng các bạn đã quay trở lại",
      "confidence": 0.98
    },
    {
      "segment_index": 1,
      "start_time": 3.60,
      "end_time": 7.20,
      "text": "với trận đấu siêu kinh điển ngày hôm nay",
      "confidence": 0.62,
      "warning": "low_confidence"
    }
  ],
  "created_at": "2026-07-10T14:30:00Z"
}
```
* **Chỉ mục cần tạo:** `{ "video_id": 1 }` (Unique Index), `{ "segments.text": "text" }` (Text Index phục vụ tìm kiếm phụ đề).
* **`confidence` (0–1):** trung bình xác suất posterior CTC của segment (@model_spec.md §2). **`warning`** (optional): `low_confidence` khi `confidence × 100 < system_settings.asr_warning_threshold`; `blacklist` khi text khớp wordlist từ nhạy cảm (rule backend, không phải model). UI hiển thị %.

### 3.2. Collection `video_analyses` (Điểm số Highlight & Tóm tắt AI)
Lưu trữ thông tin phân tích thô từ các mô hình AI nguyên thủy: điểm số highlight từng giây và văn bản tóm tắt tự hồi quy.

```json
{
  "_id": "anal_video001_1783584000",
  "video_id": "vid_abc123xyz",
  "summary": "Nội dung tóm tắt video được tự động tạo ra từ mô hình Transformer Decoder-only (mini-GPT) tự huấn luyện...",
  "summary_status": "draft",
  "suggested_title": "Bàn thắng quyết định phút 89",
  "key_moments": [
    { "timestamp": 80.0, "text": "Bàn thắng mở tỉ số sau pha phản công nhanh" },
    { "timestamp": 285.0, "text": "Pha cứu thua xuất sắc của thủ môn" }
  ],
  "hashtags": ["#bongda", "#highlight"],
  "category_suggestion": "cat_bong_da",
  "timeline_scores": [
    { "second": 0, "score": 12.5 },
    { "second": 1, "score": 24.3 },
    { "second": 2, "score": 89.7 }, 
    { "second": 3, "score": 95.2 }  
  ],
  "ai_generated_clips": [
    {
      "start_time": 2.00,
      "end_time": 12.50,
      "average_score": 92.45,
      "reason": "High visual motion and peak audio pitch"
    }
  ],
  "created_at": "2026-07-10T14:30:00Z"
}
```
* **Chỉ mục cần tạo:** `{ "video_id": 1 }` (Unique Index), `{ "summary_status": 1 }`.
* **`key_moments`:** sinh từ `ai_generated_clips` (mốc = start_time từng clip đề xuất) + caption 1 câu do Mini-GPT sinh từ transcript quanh mốc (@model_spec.md §2). **`suggested_title`:** Mini-GPT (regenerate qua `POST /api/cms/videos/{id}/summary/regenerate`). **`hashtags`:** TF-IDF keyword trên transcript + tên category — thuật toán đếm, KHÔNG phải model (@dataset_spec.md §0).

---

## 4. Đặc tả Cơ sở dữ liệu Vector (Milvus Schema)

Milvus đóng vai trò then chốt cho tính năng **Tìm kiếm bằng Hình ảnh (Visual Search)** và **Hệ gợi ý (Two-Tower Recommendation System)** sử dụng các vector embedding trích xuất từ mô hình AI nguyên thủy tự huấn luyện. Không triển khai adapter vector DB thứ hai để model/codegen yếu hơn không phải chọn hướng.

### 4.1. Collection `video_frame_embeddings` (Visual Search)
* **Số chiều Vector (Dimension):** 128 (được sinh ra từ mô hình Siamese Vision Transformer tự viết).
* **Khoảng cách so khớp (Metric Type):** `COSINE` (Cosine Similarity).
* **Schema cấu trúc:**

```json
{
  "id": "INT64 (Primary Key Auto-Increment)",
  "vector": "FLOAT_VECTOR (Dimension: 128)",
  "payload": {
    "video_id": "VARCHAR(50)",
    "timestamp": "FLOAT",
    "thumbnail_url": "VARCHAR(512)"
  }
}
```
* **Thuật toán Index khuyến nghị:** `HNSW` (Hierarchical Navigable Small World) để đạt tốc độ tìm kiếm dưới 2 giây. Các tham số cấu hình:
  * `M = 16` (Độ kết nối tối đa của nút trong đồ thị).
  * `efConstruction = 200` (Kích thước mảng tìm kiếm trong lúc dựng index).

### 4.2. Collection `user_recommendation_embeddings` (Two-Tower Recommendation)
* **Số chiều Vector (Dimension):** 128 (được sinh ra từ User Tower và Video Tower).
* **Khoảng cách so khớp (Metric Type):** `IP` (Inner Product - Tích vô hướng).
* **Schema cấu trúc:**

```json
{
  "id": "VARCHAR(50) (Khớp với User_ID/Video_ID trong Postgres)",
  "vector": "FLOAT_VECTOR (Dimension: 128)",
  "payload": {
    "type": "VARCHAR(10)", 
    "tags": "ARRAY(VARCHAR)"
  }
}
```
* **Thuật toán Index khuyến nghị:** `IVF_FLAT` để tối ưu bộ nhớ RAM với thời gian tìm kiếm thời gian thực.
