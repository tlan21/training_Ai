# 02 — KẾ HOẠCH TRIỂN KHAI BACKEND (GO + PYTHON AI BOUNDARY)
*Plan con của @00_master_plan.md. MỌI path/payload/topic ở đây PHẢI khớp bảng contract mục 2.1–2.6 của master plan — không thêm/bớt/đổi. Nền tảng thiết kế: @architecture.md (schema 6 AI endpoint + hexagonal), @architecture_unified.md (4 layer + conflict matrix), @auto_ai_flow_corrected.md (luồng 3 giai đoạn), @database_schema.md (DDL Postgres/Mongo/Milvus), @features.md (quy ước 1 FastAPI process cho AI).*

> Quy ước thang điểm (bất biến từ @architecture.md): điểm highlight `timeline_scores`/`average_score` thang **0–100**; `similarity_score` (Visual Search) và `score` (Recommendation) thang **0–1**.

---

## 0. RANH GIỚI NGÔN NGỮ (Python chỉ nơi dính AI)

| Service | Ngôn ngữ | Lý do |
|---|---|---|
| `gateway` | **Go 1.22+ (Gin)** | REST thuần, không dính AI |
| `orchestrator` | **Go** | Consume Kafka + gọi AI qua REST :8001 + update DB — không cần Python |
| `ffmpeg-cutter` | **Go** | `os/exec` gọi FFmpeg |
| `ingest-worker` | **Python** | Decord/PyAV chỉ có Python binding — tiền xử lý AI |
| `inference-service` | **Python** (FastAPI + PyTorch) | AI core — không đổi |

**Lý do chọn Go:** RAM footprint thấp (quan trọng khi mọi thứ chạy chung 1 máy với GPU), goroutine hợp worker/IO concurrency, binary tĩnh → Docker image nhỏ, không cần runtime.

**Nguyên tắc ranh giới:** ingest-worker Python chỉ đụng MinIO + Kafka (không đụng Postgres) — mọi ghi DB quan hệ dồn về Go. Orchestrator (Go) consume thêm `video.uploaded` (consumer group riêng) chỉ để set job `running` + stage `splitting_frames`; ingest-worker Python giữ tối thiểu.

---

## 1. CẤU TRÚC THƯ MỤC (từng file)

```
backend/                               # Go module duy nhất: go.mod (module traning_ai/backend)
├── go.mod / go.sum                    # deps: gin-gonic/gin, jackc/pgx/v5, mongo-driver,
│                                      #   milvus-sdk-go/v2, segmentio/kafka-go, minio-go/v7,
│                                      #   redis/go-redis/v9, golang-jwt/jwt/v5,
│                                      #   golang.org/x/crypto/bcrypt, oapi-codegen (tool),
│                                      #   stretchr/testify (test + mock)
├── cmd/
│   ├── gateway/main.go                # wire DI → Gin router :8000
│   ├── orchestrator/main.go           # wire DI → Kafka consumers
│   └── ffmpeg-cutter/main.go          # wire DI → consumer clip.cut.requested
├── internal/
│   ├── domain/
│   │   ├── entities.go                # struct: User, Session, Video, ProcessingJob, Clip,
│   │   │                              #   Category, Interaction, Subtitle, VideoAnalysis
│   │   ├── enums.go                   # VideoStatus, ClipStatus, JobStatus, Stage, InteractionType, Role
│   │   └── errors.go                  # DomainError{Code,Msg} + sentinel errors → HTTP map (mục 3)
│   ├── ports/                         # INTERFACE thuần Go, KHÔNG import lib hạ tầng
│   │   ├── repositories.go            # VideoRepository, ClipRepository, UserRepository,
│   │   │                              #   SessionRepository, JobRepository,
│   │   │                              #   InteractionRepository, CategoryRepository
│   │   ├── stores.go                  # AnalysisStore, SubtitleStore, VectorStore
│   │   ├── infra.go                   # EventBus, ObjectStorage, Cache
│   │   └── ai_client.go               # AIClient (gọi :8001)
│   ├── adapters/
│   │   ├── pg/                        # pgx/v5: pool.go + 7 repo (video, clip, user, session,
│   │   │                              #   job, interaction, category)
│   │   ├── mongodb/                   # mongo-go-driver: analysis_store.go, subtitle_store.go
│   │   ├── milvus/vector_store.go     # milvus-sdk-go/v2: 2 collection
│   │   ├── kafka/event_bus.go         # segmentio/kafka-go Reader/Writer
│   │   ├── minio/object_storage.go    # minio-go/v7
│   │   ├── redis/cache.go             # go-redis/v9
│   │   └── aihttp/ai_client.go        # net/http → :8001, timeout + context
│   ├── handlers/                      # Gin handlers (inbound adapter), nhóm theo router mục 3
│   │   ├── auth.go  users.go  content.go  search.go  interactions.go
│   │   ├── middleware.go              # JWT auth, require_role, error envelope, request log
│   │   └── cms/
│   │       ├── videos.go  clips.go  categories.go  jobs.go  system.go  users.go
│   ├── orchestrator/
│   │   ├── state_machine.go           # bảng chuyển stage (mục 5)
│   │   └── runner.go                  # goroutine per video, retry backoff
│   ├── cutter/cutter.go               # os/exec ffmpeg -ss -to -c copy
│   ├── gen/api.gen.go                 # oapi-codegen sinh từ infra/openapi.yaml — KHÔNG sửa tay
│   └── config/config.go               # env: DSN, brokers, minio, redis, JWT keys, AI base URL
├── workers/ingest-worker/             # PYTHON riêng biệt (Decord/PyAV)
│   ├── requirements.txt               # decord, av, aiokafka, minio, numpy
│   ├── main.py                        # consume video.uploaded → Decord 1fps + wav → MinIO
│   │                                  #   → publish video.preprocessed {..., duration}
│   └── extract.py                     # hàm Decord keyframes + PyAV wav + duration
└── tests/                             # Go: *_test.go cạnh code (testify); tách e2e/
    ├── e2e/auth_flow_test.go          # register/login/refresh rotation với mock
    ├── e2e/orchestrator_test.go       # state machine + retry (MockAIClient)
    └── e2e/contract_test.go           # mọi endpoint trả đúng schema openapi.yaml

infra/openapi.yaml                     # NGUỒN SỰ THẬT contract (đúng bảng master plan mục 2)
                                       # → oapi-codegen (Go stubs) + openapi-typescript (FE)

inference-service/                     # PYTHON — GIỮ NGUYÊN (không đổi so với bản trước)
├── pyproject.toml                     # torch, fastapi, uvicorn, pymilvus, httpx, pillow, numpy
├── main.py  config.py  gpu_queue.py  model_registry.py  schemas.py
├── routers/ (vision, asr, highlight, search, recommendation, completions, health)
└── postprocess/ (highlight_post.py: ×100 + gom clips >75; summary_mapreduce.py)
```

**Nguyên tắc hexagonal (Go):** handler (inbound adapter) → use-case logic thuần → Port (interface) → adapter thật/mock. Handler KHÔNG import `pgx`/`mongo-driver`/`milvus-sdk` trực tiếp; nhận Port qua constructor injection ở `cmd/*/main.go`. Đổi hạ tầng = đổi adapter, không đụng handler.

**OpenAPI contract-first:** `infra/openapi.yaml` viết tay theo bảng master plan mục 2 → `oapi-codegen -generate types,gin` sinh `internal/gen/api.gen.go` (request/response structs + router interface) — **không viết struct API tay**; FE chạy `openapi-typescript` trên cùng file → types khớp tuyệt đối 2 đầu.

---

## 2. HEXAGONAL — PORTS (Go interfaces) & ADAPTERS

Mỗi Port là interface Go, method nhận `context.Context`, trả `error` cuối. Mock bằng `testify/mock` (hoặc struct in-memory cho repo đơn giản). Signature dưới đây là hợp đồng bất biến.

### 2.1. VideoRepository
```go
type VideoRepository interface {
    Create(ctx context.Context, v *domain.Video) error                    // INSERT status='uploaded'
    Get(ctx context.Context, id string) (*domain.Video, error)
    GetProcessed(ctx context.Context, id string) (*domain.Video, error)   // chỉ status='processed'
    List(ctx context.Context, status *string, page, size int) ([]domain.Video, int, error)
    SetStatus(ctx context.Context, id string, s domain.VideoStatus) error
    SetCategory(ctx context.Context, id, categoryID string) error         // Admin duyệt (2.3)
    SetDuration(ctx context.Context, id string, seconds float64) error
    SoftDelete(ctx context.Context, id string) error
}
```

### 2.2. ClipRepository
```go
type ClipRepository interface {
    Create(ctx context.Context, c *domain.Clip) error                     // status='draft'
    Get(ctx context.Context, id string) (*domain.Clip, error)
    GetPublished(ctx context.Context, id string) (*domain.Clip, error)
    ListPublishedByVideo(ctx context.Context, videoID string) ([]domain.Clip, error)
    List(ctx context.Context, videoID, status *string) ([]domain.Clip, error) // CMS
    SetStatus(ctx context.Context, id string, s domain.ClipStatus) error
    SetFilePath(ctx context.Context, id, path string) error               // sau khi cut xong
    UpdateMeta(ctx context.Context, id string, title *string, start, end *float64) (*domain.Clip, error)
    HideByVideo(ctx context.Context, videoID string) error                // xóa video → 'rejected'
}
```

### 2.3. UserRepository
```go
type UserRepository interface {
    Create(ctx context.Context, u *domain.User) error                     // UNIQUE username/email
    Get(ctx context.Context, id string) (*domain.User, error)
    GetByEmail(ctx context.Context, email string) (*domain.User, error)
    UpdateProfile(ctx context.Context, id string, username *string) (*domain.User, error)
    SetRole(ctx context.Context, id string, r domain.Role) (*domain.User, error) // admin only
    List(ctx context.Context, page, size int) ([]domain.User, int, error)
}
```

### 2.4. SessionRepository — refresh rotation
```go
type SessionRepository interface {
    Create(ctx context.Context, userID, refreshHash string, expiresAt time.Time) (string, error) // → ses_id
    GetByHash(ctx context.Context, refreshHash string) (*domain.Session, error)
    Delete(ctx context.Context, sessionID string) error                   // logout / rotate cũ
    DeleteByUser(ctx context.Context, userID string) error
}
```

### 2.5. JobRepository — video_processing_jobs
```go
type JobRepository interface {
    Create(ctx context.Context, videoID string) (*domain.ProcessingJob, error) // status='pending'
    Get(ctx context.Context, id string) (*domain.ProcessingJob, error)
    GetByVideo(ctx context.Context, videoID string) (*domain.ProcessingJob, error)
    List(ctx context.Context, status *string) ([]domain.ProcessingJob, error)
    SetStatus(ctx context.Context, id string, s domain.JobStatus, started, completed bool) error
    SetStage(ctx context.Context, id string, stage domain.Stage) error    // current_stage
    SetError(ctx context.Context, id, errorLog string) error
}
```

### 2.6. InteractionRepository
```go
type InteractionRepository interface {
    Add(ctx context.Context, i *domain.Interaction) error                 // INSERT user_interactions
    History(ctx context.Context, userID string, cursor *string, limit int) ([]domain.HistoryItem, *string, error)
    Likes(ctx context.Context, userID string, cursor *string, limit int) ([]domain.Clip, *string, error)
    PopularityTop(ctx context.Context, limit int) ([]string, error)       // fallback feed: video_id
}
```

### 2.7. CategoryRepository
```go
type CategoryRepository interface {
    List(ctx context.Context) ([]domain.Category, error)
    Create(ctx context.Context, name string) (*domain.Category, error)
    Update(ctx context.Context, id, name string) (*domain.Category, error)
    Delete(ctx context.Context, id string) error
}
```

### 2.8. AnalysisStore — Mongo `video_analyses`
```go
type AnalysisStore interface {
    Put(ctx context.Context, videoID string, timelineScores []domain.SecondScore,
        aiClips []domain.AIClip, categorySuggestion *string) error        // upsert theo video_id
    Get(ctx context.Context, videoID string) (*domain.VideoAnalysis, error)
    SetSummary(ctx context.Context, videoID, summary, status string) error // draft|approved
    Delete(ctx context.Context, videoID string) error
}
```

### 2.9. SubtitleStore — Mongo `subtitles`
```go
type SubtitleStore interface {
    Put(ctx context.Context, videoID, language, fullTranscript string, segments []domain.Segment) error
    Get(ctx context.Context, videoID string) (*domain.Subtitle, error)
    UpdateSegments(ctx context.Context, videoID string, segments []domain.Segment) error // CMS bulk
    TextSearch(ctx context.Context, q string) ([]domain.SubtitleMatch, error) // text index segments.text
    Delete(ctx context.Context, videoID string) error
}
```

### 2.10. VectorStore — Milvus 2 collection
```go
type VectorStore interface {
    // video_frame_embeddings (dim 128, COSINE, HNSW M=16 efConstruction=200)
    UpsertFrames(ctx context.Context, videoID string, items []domain.FrameEmbedding) error
    SearchFrames(ctx context.Context, vector []float32, topK int, threshold float64) ([]domain.FrameHit, error)
    DeleteFrames(ctx context.Context, videoID string) error               // xóa video → xóa vectors
    // user_recommendation_embeddings (dim 128, IP, IVF_FLAT)
    UpsertUser(ctx context.Context, userID string, vector []float32, tags []string) error
    UpsertVideoVec(ctx context.Context, videoID string, vector []float32, tags []string) error
    SearchVideosForUser(ctx context.Context, userID string, limit int) ([]domain.VideoHit, error)
}
```

### 2.11. EventBus — Kafka (topics mục 2.5 master plan, bất biến)
```go
type EventBus interface {
    Publish(ctx context.Context, topic string, key string, payload any) error // JSON marshal
    // Consume chạy blocking loop, gọi handler từng message; commit offset SAU khi handler trả nil
    Consume(ctx context.Context, topic, groupID string, handler func(ctx context.Context, payload []byte) error) error
}
```
Topic hợp lệ: `video.uploaded`, `video.preprocessed`, `ai.stage.completed`, `clip.cut.requested`, `clip.cut.completed`. Mock: append vào slice, test assert payload.

### 2.12. ObjectStorage — MinIO
```go
type ObjectStorage interface {
    PutStream(ctx context.Context, bucket, key string, r io.Reader, size int64, contentType string) (string, error)
    GetPresigned(ctx context.Context, bucket, key string, ttl time.Duration) (string, error)
    GetObject(ctx context.Context, bucket, key string) (io.ReadCloser, error)
    Delete(ctx context.Context, bucket, key string) error
}
```
Bucket: `raw-videos`, `raw-audio`, `keyframes`, `thumbnails`, `clips`.

### 2.13. Cache — Redis
```go
type Cache interface {
    Get(ctx context.Context, key string) (string, bool, error)
    Set(ctx context.Context, key, value string, ttl time.Duration) error
    Delete(ctx context.Context, keys ...string) error
}
```

### 2.14. AIClient — gọi inference-service :8001 (schema @architecture.md mục 2)
```go
type AIClient interface {
    Vision(ctx context.Context, keyframePaths []string) (*domain.VisionResult, error)        // {CategorySuggestion, Embeddings256}
    ASR(ctx context.Context, audioURL, language string) (*domain.ASRResult, error)           // {FullTranscript, Segments}
    Highlight(ctx context.Context, videoID string, visionEmb [][]float32, audioFeat [][]float32) (*domain.HighlightResult, error) // {TimelineScores 0–100, RecommendedClips}
    Search(ctx context.Context, imageB64 string, topK int, threshold float64) (*domain.SearchResult, error)
    Recommendation(ctx context.Context, userID string, limit int, contextMeta map[string]string) (*domain.RecResult, error)
    Summarize(ctx context.Context, prompt string, maxTokens int) (*domain.SummaryResult, error)
    Health(ctx context.Context) (*domain.AIHealth, error)
}
```
Adapter `aihttp`: `net/http.Client{Timeout}` + context deadline, base URL `http://inference-service:8001`. **MockAIClient** (testify/mock hoặc struct cứng) trả JSON đúng schema → gateway/orchestrator test + chạy dev KHÔNG cần GPU — chìa khóa để Phase 2 không đợi Phase 1.

**Vì sao 14 Port:** mỗi Port 1 domain (Video/Clip/User/Session/Job/Interaction/Category/Analysis/Subtitle/Vector/Event/Object/Cache/AI), tránh God-interface; mock từng phần khi test.

---

## 3. ĐẶC TẢ TỪNG ENDPOINT (nhóm theo handler — KHÔNG ĐỔI so với contract)

Quy ước chung (mục 2.6 master plan):
- Auth header `Authorization: Bearer <access_jwt>` (15 phút, RAM/Zustand). Refresh 7 ngày cookie HttpOnly.
- Error envelope: `{"error":{"code":"...","message":"..."}}` — middleware map DomainError → HTTP.
- Mã lỗi: `VALIDATION_ERROR`(422), `UNAUTHORIZED`(401), `FORBIDDEN`(403), `*_NOT_FOUND`(404), `CONFLICT`/`EMAIL_TAKEN`/`USERNAME_TAKEN`/`CLIP_NOT_READY`(409), `AI_UNAVAILABLE`(503), `PAYLOAD_TOO_LARGE`(413).
- JWT: `golang-jwt/jwt/v5` HS256; password: `golang.org/x/crypto/bcrypt` cost 12; refresh token: 256-bit random, lưu SHA-256 hash vào `user_sessions`.

### Handler `auth.go` (mục 2.1)

**POST `/api/auth/register`** — Auth: không.
- Request: `{username: 3–50, email, password: ≥8}` (validate qua oapi-codegen types + binding).
- Trùng → `409 EMAIL_TAKEN`/`USERNAME_TAKEN`.
- Xử lý: bcrypt hash → `UserRepository.Create` (role `client`) → access JWT 15' + refresh random → `SessionRepository.Create(sha256(refresh), now+7d)`.
- Response `201`: `{user:{id,username,email,role,preferences:[]}, access_token}` + `Set-Cookie: refresh=<token>; HttpOnly; Secure; SameSite=Lax; Max-Age=604800`.
- DB: `users`, `user_sessions`.

**POST `/api/auth/login`** — `{email,password}`. Sai → `401` (không lộ email tồn tại). Xử lý: `GetByEmail` → bcrypt compare → cấp access + refresh mới. `200` như register.

**POST `/api/auth/refresh`** — cookie refresh. ROTATION: `GetByHash` hợp lệ → `Delete(cũ)` + `Create(mới)` → access mới. `200 {access_token}` + Set-Cookie mới. Token đã xoay dùng lại → `GetByHash`=nil → `401` (chống replay).

**POST `/api/auth/logout`** — JWT. Xóa cookie + `SessionRepository.Delete`. `204`.

### Handler `users.go` (mục 2.1) — JWT

**GET `/api/users/me`** → `200 {id,username,email,role,preferences:[category_id]}` (preferences từ Milvus tags user).
**PUT `/api/users/me`** — `{username?}` unique → `200 user`.
**PUT `/api/users/me/preferences`** — `{category_ids}` **≥3** + tồn tại, sai → `422`. Cold-start: user vector = trung bình vector video các category chọn → `VectorStore.UpsertUser`. `200`.
**GET `/api/users/me/history`** → `200 {items:[{clip,watched_at,duration_watched}],next_cursor}` (cursor). DB: `user_interactions` JOIN `clips`.
**GET `/api/users/me/likes`** → `200 {items:[clip],next_cursor}`. DB: `user_interactions(type='like')` JOIN `clips`.

### Handler `content.go` (mục 2.2) — JWT

**GET `/api/feed?cursor&limit=10`**
- Cache `feed:{user_id}:{cursor}` TTL 60s → hit trả luôn.
- Đủ tương tác & AI ok: `AIClient.Recommendation` → nạp clips published của videos processed. User mới: dùng onboarding vector; vẫn thiếu HOẶC AI lỗi → `PopularityTop` (cache `feed:pop:{cursor}` TTL 120s).
- `200 {items:[clip],next_cursor}`. DB: `clips`,`videos`,`user_interactions`; AI: `/v1/recommendation/completions`.

**GET `/api/videos/{id}`** — chỉ processed, khác → `404 VIDEO_NOT_FOUND` → `200` meta + category + clips published.
**GET `/api/videos/{id}/analysis`** → `200 {timeline_scores(0–100), summary}` — summary chỉ khi `summary_status='approved'`, chưa duyệt → `summary:null`. DB: `videos` + Mongo.
**GET `/api/videos/{id}/subtitles`** → `200 {segments}`. Cache `subs:{video_id}` TTL 300s.
**GET `/api/clips/{id}`** — published, khác → `404 CLIP_NOT_FOUND` → `200 {clip, video_ref}`.
**GET `/api/categories`** → `200 [category]`. Cache `categories:all` TTL 600s.

### Handler `search.go` (mục 2.2) — JWT

**POST `/api/search/visual`** — multipart `image` jpg/png ≤5MB, sai → `422`. Bytes → base64 → `AIClient.Search(b64, 5, 0.75)`. `200 {results:[{video_id,timestamp,similarity_score(0–1),thumbnail_url}]}`. Mục tiêu <2s (flow 4c).
**GET `/api/search?q=`** — `SubtitleStore.TextSearch` (Mongo text index) + `videos.title` (Postgres ILIKE) → `200 {results:[{video_id,title,matched_segments:[{start_time,text}]}]}`. Cache `search:txt:{q}` TTL 120s.

### Handler `interactions.go` — JWT

**POST `/api/interactions`** — `{video_id, clip_id?, interaction_type: click|watch_time|like|share|skip, duration_watched?}`. `watch_time` cần `duration_watched≥0`. `201`. DB: `user_interactions` (nguồn train Two-Tower).

### Handler `cms/videos.go` (mục 2.3) — role `admin|editor`

**POST `/api/cms/videos`** — multipart ≤2GB (>2GB → `413`; mp4/mkv). `PutStream('raw-videos')` → `Create video(uploaded)` → `Create job(pending)` → `Publish('video.uploaded',{video_id,raw_file_path})`. `201 {video, job}`.
**GET `/api/cms/videos?status&page`** → `200 {items,total,page}` (page-based).
**GET `/api/cms/videos/{id}`** → `200` meta + job + analysis refs.
**DELETE `/api/cms/videos/{id}`** — flow 4f: `SoftDelete` + `DeleteFrames` + `HideByVideo` + `AnalysisStore.Delete` + `SubtitleStore.Delete` + xóa cache. `204`.
**GET `/api/cms/videos/{id}/analysis`** → `200 {timeline_scores, ai_generated_clips, category_suggestion, summary, summary_status}`.
**PUT `/api/cms/videos/{id}/category`** — `{category_id}` tồn tại. Nguyên tắc 6.3.3: Admin duyệt → `SetCategory` ghi Postgres. `200`.
**PUT `/api/cms/videos/{id}/summary`** — `{summary}` → `SetSummary(draft)`. `200`.
**POST `/api/cms/videos/{id}/summary/approve`** → `SetSummary(approved)` — Client mới thấy. `200`.
**PUT `/api/cms/videos/{id}/subtitles`** — `{segments}` bulk → `UpdateSegments` + xóa cache `subs:{id}`. `200`.

### Handler `cms/jobs.go`
**GET `/api/cms/jobs?status`** → `200 [{job, current_stage}]`. **GET `/api/cms/jobs/{id}`** → `200 {job, error_log, current_stage}`.

### Handler `cms/system.go`
**GET `/api/cms/system/health`** → `AIClient.Health()` proxy `:8001/health` → `200 {gpu_vram_used,gpu_util,models_loaded,queue_depth}`. Lỗi → `503 AI_UNAVAILABLE`.

### Handler `cms/clips.go`
**POST `/api/cms/clips`** — `{video_id,title,start_time,end_time}` (`end>start`, trong duration). `Create(draft→processing)` → `Publish('clip.cut.requested')`. `201 {clip}`.
**POST `/api/cms/clips/{id}/publish`** — chỉ khi `clip_file_path` set, else `409 CLIP_NOT_READY` → `SetStatus(published)`. `200`.
**PUT `/api/cms/clips/{id}`** — `UpdateMeta`. **DELETE** → `SetStatus(rejected)`.
**GET `/api/cms/clips?video_id&status`** → `200 [clip]`.

### Handler `cms/categories.go` — CRUD `/api/cms/categories`; xóa cache `categories:all` khi ghi.
### Handler `cms/users.go` — admin only: **GET `/api/cms/users`**, **PUT `/api/cms/users/{id}/role`** `{role}`.

---

## 4. SEQUENCE FLOWS (giữ nguyên logic — chú thích ngôn ngữ mỗi hộp)

### 4a. Upload → Ingest (Py) → Orchestrator (Go) chain 4 stage GĐ2 + Mini-GPT GĐ3 → processed

```
CMS ──POST /api/cms/videos──► GATEWAY (Go)
  PutStream(raw-videos/vid_X.mp4) → Create video(uploaded) + job(pending)
  Publish('video.uploaded', {video_id, raw_file_path})
        │
        ├────────────────────────────► ORCHESTRATOR (Go, group "orch-uploaded")
        │                                JobRepository: running + stage='splitting_frames'
        ▼
INGEST-WORKER (PYTHON — Decord/PyAV, chỉ MinIO + Kafka)
  Decord đọc raw-videos/vid_X.mp4, sample 1 fps → keyframes → MinIO keyframes/vid_X/*.jpg
  PyAV tách audio 16kHz mono → MinIO raw-audio/vid_X.wav; tính duration
  Publish('video.preprocessed', {video_id, keyframes_path, audio_path, duration})
        │
        ▼
ORCHESTRATOR (Go)  consume 'video.preprocessed' → SetDuration(vid_X) → state machine (mục 5)
  STAGE vision:    stage='embedding';  AIClient.Vision(keyframes) → {category_suggestion, embeddings_256}
                   AnalysisStore.Put(category_suggestion) ; Publish ai.stage.completed{vision,ok}
  STAGE asr:       stage='asr_extracting'; AIClient.ASR(audio_url) → {full_transcript, segments}
                   SubtitleStore.Put ; Publish {asr,ok}
  STAGE highlight: stage='highlight_scoring'; AIClient.Highlight(vid_X, vision_emb, audio_feat)
                   → {timeline_scores(0–100), recommended_clips}
                   AnalysisStore.Put(timeline_scores, ai_generated_clips) ; Publish {highlight,ok}
  STAGE embedding: (frame embeddings 128d từ vision stage) VectorStore.UpsertFrames ; Publish {embedding,ok}
  STAGE summary:   stage='summarizing'; AIClient.Summarize(full_transcript) → summary
                   AnalysisStore.SetSummary(draft) ; Publish {summary,ok}
  Đủ 4 stage GĐ2 + summary → SetStatus(vid_X,'processed'); job completed
```
GPU chạy TUẦN TỰ qua queue :8001 (1 worker) dù logic song song; `vision` trước `highlight` (cần vision_embeddings); `summary` sau `asr`.

### 4b. CMS duyệt highlight → cut clip (Go) → publish

```
CMS review (GET /api/cms/videos/{id}/analysis → ai_generated_clips, chỉnh start/end)
  ──POST /api/cms/clips──► GATEWAY (Go): Create clip(processing) + Publish('clip.cut.requested')
        ▼
FFMPEG-CUTTER (Go)  consume 'clip.cut.requested'
  GetObject(raw-videos/vid_X.mp4) → temp file
  exec.CommandContext("ffmpeg","-ss",start,"-to",end,"-i",in,"-c","copy",out)   # không re-encode
  PutStream(clips/clp_Y.mp4) → Publish('clip.cut.completed', {clip_id, clip_file_path, ok})
        ▼
GATEWAY handler (Go, group "clip-completed")  consume 'clip.cut.completed'
  SetFilePath + SetStatus('draft')   # sẵn sàng publish
CMS ──POST /api/cms/clips/{id}/publish──► SetStatus('published') → Client feed thấy
```

### 4c. Visual search end-to-end < 2s
```
Client ──POST /api/search/visual──► GATEWAY (Go): validate ≤5MB → base64
  AIClient.Search ──HTTP──► :8001 (PYTHON): Siamese encode 128d (nhẹ, ngoài queue nặng)
     → Milvus HNSW COSINE top_k → [{video_id,timestamp,similarity_score(0–1),thumbnail_url}]
  → 200 {results}. Ngân sách: encode ~150ms + Milvus <200ms + mạng nội bộ.
```

### 4d. Feed + fallback + cold-start
```
GET /api/feed → cache hit? trả || AIClient.Recommendation (Two-Tower IP search Milvus)
  ├─ user mới: onboarding vector (PUT /preferences đã UpsertUser) ; vẫn thiếu → PopularityTop
  └─ AI lỗi 503 → PopularityTop
  → nạp clips published → cache 60s → 200 {items,next_cursor}
```

### 4e. Auth refresh rotation
```
POST /api/auth/refresh (cookie) → GetByHash(sha256(cookie))
  nil/expired → 401 || hợp lệ → Delete(cũ) + Create(mới) → access mới + Set-Cookie mới
Token cũ dùng lại → nil → 401 (chống replay)
```

### 4f. Xóa video
```
DELETE /api/cms/videos/{id} → SoftDelete + DeleteFrames(Milvus) + HideByVideo(clips→rejected)
  + AnalysisStore.Delete + SubtitleStore.Delete + Cache.Delete → 204
Conflict matrix #1: Client chỉ đọc processed+published → ẩn hoàn toàn.
```

---

## 5. ORCHESTRATOR LOGIC (Go — state machine + retry)

`runner.go`: mỗi video 1 goroutine chạy tuần tự các stage (đơn giản, đủ 1 máy — `ponytail:` không cần saga engine; nâng cấp event-sourced khi scale nhiều node). Consume 2 topic: `video.preprocessed` (khởi động) + `video.uploaded` (chỉ set job running/stage đầu).

### Bảng state machine (`current_stage` → `video_processing_jobs`)
| Từ stage | Hành động | AI endpoint | Ghi DB | → stage kế | Điều kiện |
|---|---|---|---|---|---|
| `pending` | nhận `video.uploaded` | — | job running, started_at | `splitting_frames` | — |
| `splitting_frames` | ingest Python làm | — | duration (khi preprocessed) | `embedding` | keyframes+wav sẵn |
| `embedding` (vision) | encode keyframes | `/v1/vision/completions` | analyses.category_suggestion; Milvus frames | `asr_extracting` | vision ok |
| `asr_extracting` | ASR | `/v1/asr/completions` | subtitles | `highlight_scoring` | asr ok |
| `highlight_scoring` | fusion | `/v1/highlight/completions` | analyses.timeline_scores + ai_generated_clips | `summarizing` | highlight ok (cần vision_emb) |
| `summarizing` (GĐ3) | Mini-GPT | `/v1/completions` | analyses.summary(draft) | `completed` | asr đã xong |
| `completed` | finalize | — | videos='processed'; job completed_at | — | đủ 4 stage GĐ2 + summary |

Thứ tự cứng: `vision → asr → highlight → embedding → summary`. Publish `ai.stage.completed` sau mỗi stage với `stage` ∈ {vision, asr, highlight, embedding, summary} đúng topic contract.

### Retry policy
- Mỗi stage: **3 lần**, backoff `2s, 4s, 8s` + jitter (context-aware). Chỉ retry lỗi tạm (timeout/503); 4xx → fail ngay.
- Hết 3 lần → `SetError("stage=<x>: <err>")`, `SetStatus(failed)`, publish `{stage, ok:false, error}`. Video giữ `processing`. CMS xem `error_log` qua `GET /api/cms/jobs/{id}`.
- Idempotent: mọi store ghi upsert theo `video_id` → retry/replay không nhân bản.

### Test: `orchestrator_test.go` — MockAIClient 1 stage lỗi 2 lần rồi ok → assert retry 3, `current_stage` đúng thứ tự, cuối `processed`; 1 case fail vĩnh viễn → job failed + error_log.

---

## 6. INFERENCE-SERVICE (:8001) — PYTHON, GIỮ NGUYÊN

Không đổi gì so với thiết kế trước (Python là bắt buộc — PyTorch):
- **Startup**: lifespan nạp 6 checkpoint ai-core (~120MB VRAM), `model.eval()` + `torch.no_grad()`, kết nối Milvus, khởi động `gpu_queue` (asyncio.Queue + **1** GPU worker — không bao giờ 2 forward pass chồng nhau trên RTX 3060).
- **Bảng xử lý endpoint** (tiền xử lý → model → hậu xử lý): vision (patchify → ViT → category + embeddings_256), asr (wav → Mel FFT → CTC decode → transcript + segments), highlight (ghép features → Fusion → sigmoid **×100** → gom `recommended_clips` giây liên tiếp **>75**), search (b64 → Siamese 128d → Milvus COSINE, ngoài queue nặng), recommendation (user vector → IP search), completions (BPE → Mini-GPT KV-cache; >1024 token → **map-reduce** 900 token/đoạn), health (`torch.cuda.memory_allocated` + pynvml + `queue.qsize()`).
- Gateway Go gọi qua `AIClient` (mục 2.14); MockAIClient thay thế khi dev/test.

---

## 7. TASK BREAKDOWN (Phase 2 master plan: T2.1–T2.6)

Sub-task ≤0.5 ngày. DoD = Definition of Done. "Sau" = phụ thuộc.

### T2.1 — Go module + domain + ports + adapters + mocks
| Sub | Việc | DoD | Sau |
|---|---|---|---|
| 2.1.0 | `go.mod` + `infra/openapi.yaml` (bảng contract mục 2) + oapi-codegen sinh `gen/api.gen.go`; FE chạy openapi-typescript | `go build ./...` pass; TS types sinh ok | — |
| 2.1.1 | `domain/`: entities.go + enums.go + errors.go | struct 9 entity + enum + map lỗi→HTTP compile | — |
| 2.1.2 | `ports/`: 14 interface (mục 2) | `go vet` pass | 2.1.1 |
| 2.1.3 | mocks (testify/mock hoặc in-memory) cho 14 Port | unit test CRUD pass | 2.1.2 |
| 2.1.4 | adapter pgx: pool + 7 repo | test với Postgres docker: CRUD pass | 2.1.2, T0.1 |
| 2.1.5 | adapter mongo (analysis, subtitle) + text index | Put/Get/TextSearch pass | 2.1.2 |
| 2.1.6 | adapter milvus (2 collection HNSW/IVF_FLAT) | upsert+search+delete pass | 2.1.2 |
| 2.1.7 | adapter kafka/minio/redis/aihttp | publish/consume roundtrip; presign; get/set; MockAI health | 2.1.2 |
| 2.1.8 | `config.go` + wire DI trong `cmd/*/main.go` (real/mock theo env) | cả 3 binary khởi động 2 chế độ | 2.1.3–2.1.7 |

### T2.2 — Auth (JWT + refresh rotation)
| Sub | Việc | DoD | Sau |
|---|---|---|---|
| 2.2.1 | bcrypt + JWT HS256 + refresh hash helpers | unit test hash/verify + exp | T2.1 |
| 2.2.2 | handler register/login | 201/200 + Set-Cookie; trùng → 409 | 2.2.1 |
| 2.2.3 | refresh rotation + logout | token cũ xoay → 401; logout xóa session | 2.2.2 |
| 2.2.4 | middleware JWT + require_role | 401 thiếu, 403 sai role | 2.2.1 |
| 2.2.5 | handler users (me/profile/preferences≥3/history/likes) | <3 → 422; onboarding vector ghi Milvus | 2.2.4, 2.1.6 |

### T2.3 — Ingest-worker (Python) + Orchestrator (Go)
| Sub | Việc | DoD | Sau |
|---|---|---|---|
| 2.3.1 | Python `extract.py`: Decord 1fps keyframes → MinIO | keyframes đúng; test 1 video mẫu | T0.1 |
| 2.3.2 | Python `main.py`: consume uploaded, wav + duration, publish preprocessed | event đúng payload; KHÔNG đụng Postgres | 2.3.1 |
| 2.3.3 | Go `state_machine.go` (bảng mục 5) | chuyển stage đúng thứ tự (MockAI) | T2.1 |
| 2.3.4 | Go `runner.go` chain 5 stage + ghi Mongo/Milvus + SetDuration | video→processed khi đủ stage | 2.3.3, 2.1.5, 2.1.6 |
| 2.3.5 | retry 3 lần backoff + failed→error_log | orchestrator_test 2 case pass | 2.3.4 |

### T2.4 — FFmpeg cutter (Go)
| Sub | Việc | DoD | Sau |
|---|---|---|---|
| 2.4.1 | consume cut.requested, `exec` ffmpeg `-ss -to -c copy` | clip vào MinIO, không re-encode | T2.1 |
| 2.4.2 | publish cut.completed + handler update clips | SetFilePath; flow 4b pass | 2.4.1 |

### T2.5 — Endpoints thật + Redis cache
| Sub | Việc | DoD | Sau |
|---|---|---|---|
| 2.5.1 | content.go (feed+fallback, videos, clips, categories) | feed AIClient + fallback popularity | T2.2, 2.1.7 |
| 2.5.2 | search.go (visual + text) | visual gọi AI; text Mongo+PG | 2.1.5, 2.1.7 |
| 2.5.3 | interactions.go | 201 ghi user_interactions | T2.2 |
| 2.5.4 | cms/* (videos, clips, jobs, categories, users, system) | mọi endpoint 2.3 đúng schema/role | T2.2–T2.4 |
| 2.5.5 | Redis cache + invalidation | hit/miss test; xóa cache khi ghi | 2.5.1, 2.5.2 |
| 2.5.6 | error middleware + contract_test so với openapi.yaml | mọi lỗi đúng envelope; response khớp schema | 2.5.1–2.5.4 |

### T2.6 — Inference-service (Python, checkpoint thật)
| Sub | Việc | DoD | Sau |
|---|---|---|---|
| 2.6.1 | model_registry nạp 6 checkpoint | startup <30s, VRAM ~120MB | Phase 1 checkpoint |
| 2.6.2 | gpu_queue 1 worker tuần tự | 2 request đồng thời không OOM | 2.6.1 |
| 2.6.3 | 6 router + schemas khớp @architecture.md | validate đúng schema | 2.6.1 |
| 2.6.4 | highlight_post (×100 + gom >75) | timeline 0–100; clips đúng | 2.6.3 |
| 2.6.5 | summary_mapreduce + KV-cache | transcript >1024 token ok | 2.6.3 |
| 2.6.6 | /health gpu stats + queue depth | proxy CMS trả đủ field | 2.6.2 |

**Thứ tự tổng:** T0.1 → T2.1 (kèm 2.1.0 openapi trước tiên) → {T2.2, T2.3, T2.4} song song → T2.5 → T2.6 (ghép checkpoint sau Phase 1; trước đó MockAIClient nên không bị chặn).
