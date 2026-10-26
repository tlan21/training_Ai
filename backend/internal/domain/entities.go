package domain

import "time"

// --- Postgres entities (database_schema.md §2.1) ---

type User struct {
	ID           string    `json:"id" bson:"id"`
	Username     string    `json:"username" bson:"username"`
	Email        string    `json:"email" bson:"email"`
	AvatarURL    *string   `json:"avatar_url" bson:"avatar_url"`
	PasswordHash string    `json:"-" bson:"password_hash"`
	Role         Role      `json:"role" bson:"role"`
	CreatedAt    time.Time `json:"created_at" bson:"created_at"`
	UpdatedAt    time.Time `json:"updated_at" bson:"updated_at"`
}

type Session struct {
	ID               string    `json:"id" bson:"id"`
	UserID           string    `json:"user_id" bson:"user_id"`
	RefreshTokenHash string    `json:"-" bson:"refresh_token_hash"`
	ExpiresAt        time.Time `json:"expires_at" bson:"expires_at"`
	CreatedAt        time.Time `json:"created_at" bson:"created_at"`
}

type PasswordReset struct {
	ID        string    `json:"id" bson:"id"`
	UserID    string    `json:"user_id" bson:"user_id"`
	TokenHash string    `json:"-" bson:"token_hash"`
	ExpiresAt time.Time `json:"expires_at" bson:"expires_at"`
	CreatedAt time.Time `json:"created_at" bson:"created_at"`
}

type Video struct {
	ID              string      `json:"id" bson:"id"`
	Title           string      `json:"title" bson:"title"`
	Description     *string     `json:"description" bson:"description"`
	RawFilePath     string      `json:"raw_file_path" bson:"raw_file_path"`
	ThumbnailURL    *string     `json:"thumbnail_url" bson:"thumbnail_url"`
	DurationSeconds float64     `json:"duration_seconds" bson:"duration_seconds"`
	Status          VideoStatus `json:"status" bson:"status"`
	UploadedBy      *string     `json:"uploaded_by" bson:"uploaded_by"`
	CategoryID      *string     `json:"category_id" bson:"category_id"`
	DeletedAt       *time.Time  `json:"deleted_at" bson:"deleted_at"`
	CreatedAt       time.Time   `json:"created_at" bson:"created_at"`
	UpdatedAt       time.Time   `json:"updated_at" bson:"updated_at"`
}

type ProcessingJob struct {
	ID           string     `json:"id" bson:"id"`
	VideoID      string     `json:"video_id" bson:"video_id"`
	QueueName    string     `json:"queue_name" bson:"queue_name"`
	Status       JobStatus  `json:"status" bson:"status"`
	WorkerNodeID *string    `json:"worker_node_id" bson:"worker_node_id"`
	ErrorLog     *string    `json:"error_log" bson:"error_log"`
	StartedAt    *time.Time `json:"started_at" bson:"started_at"`
	CompletedAt  *time.Time `json:"completed_at" bson:"completed_at"`
	UpdatedAt    time.Time  `json:"updated_at" bson:"updated_at"`
	CurrentStage *Stage     `json:"current_stage" bson:"current_stage"`
	Progress     int        `json:"progress" bson:"progress"`
}

type Clip struct {
	ID           string     `json:"id" bson:"id"`
	VideoID      string     `json:"video_id" bson:"video_id"`
	Title        string     `json:"title" bson:"title"`
	StartTime    float64    `json:"start_time" bson:"start_time"`
	EndTime      float64    `json:"end_time" bson:"end_time"`
	AverageScore float64    `json:"average_score" bson:"average_score"`
	ClipFilePath *string    `json:"clip_file_path" bson:"clip_file_path"`
	ThumbnailURL *string    `json:"thumbnail_url" bson:"thumbnail_url"`
	Status       ClipStatus `json:"status" bson:"status"`
	CreatedBy    *string    `json:"created_by" bson:"created_by"`
	CategoryID   *string    `json:"category_id" bson:"category_id"`
	CreatedAt    time.Time  `json:"created_at" bson:"created_at"`
	UpdatedAt    time.Time  `json:"updated_at" bson:"updated_at"`
}

type Category struct {
	ID        string    `json:"id" bson:"id"`
	Name      string    `json:"name" bson:"name"`
	CreatedAt time.Time `json:"created_at" bson:"created_at"`
}

type Interaction struct {
	ID              int64           `json:"id" bson:"id"`
	UserID          string          `json:"user_id" bson:"user_id"`
	VideoID         string          `json:"video_id" bson:"video_id"`
	ClipID          *string         `json:"clip_id" bson:"clip_id"`
	InteractionType InteractionType `json:"interaction_type" bson:"interaction_type"`
	DurationWatched int             `json:"duration_watched" bson:"duration_watched"`
	CreatedAt       time.Time       `json:"created_at" bson:"created_at"`
}

type SystemSettings struct {
	HighlightThreshold   int
	ASRWarningThreshold  int
	AutoHighlightEnabled bool
	AutoSubtitleEnabled  bool
	DefaultSubtitleLang  string
	AIServiceAPIKey      string
}

type HistoryItem struct {
	Clip            Clip      `json:"clip" bson:"clip"`
	WatchedAt       time.Time `json:"watched_at" bson:"watched_at"`
	DurationWatched int       `json:"duration_watched" bson:"duration_watched"`
}

// --- Mongo documents (database_schema.md §3) ---

type Segment struct {
	SegmentIndex int     `json:"segment_index" bson:"segment_index"`
	StartTime    float64 `json:"start_time" bson:"start_time"`
	EndTime      float64 `json:"end_time" bson:"end_time"`
	Text         string  `json:"text" bson:"text"`
	Confidence   float64 `json:"confidence" bson:"confidence"`
	Warning      *string `json:"warning" bson:"warning"`
}

type Subtitle struct {
	VideoID        string    `json:"video_id" bson:"video_id"`
	Language       string    `json:"language" bson:"language"`
	FullTranscript string    `json:"full_transcript" bson:"full_transcript"`
	Segments       []Segment `json:"segments" bson:"segments"`
	CreatedAt      time.Time `json:"created_at" bson:"created_at"`
}

type SubtitleMatch struct {
	VideoID   string  `json:"video_id" bson:"video_id"`
	Title     *string `json:"title" bson:"title"`
	Timestamp float64 `json:"timestamp" bson:"timestamp"`
	Text      string  `json:"text" bson:"text"`
}

type SecondScore struct {
	Second int     `json:"second" bson:"second"`
	Score  float64 `json:"score" bson:"score"` // 0-100 master plan §2.6
}

type AIClip struct {
	StartTime    float64 `json:"start_time" bson:"start_time"`
	EndTime      float64 `json:"end_time" bson:"end_time"`
	AverageScore float64 `json:"average_score" bson:"average_score"` // 0-100
	Reason       *string `json:"reason" bson:"reason"`
}

type KeyMoment struct {
	Timestamp float64 `json:"timestamp" bson:"timestamp"`
	Text      string  `json:"text" bson:"text"`
}

type VideoAnalysis struct {
	VideoID            string        `json:"video_id" bson:"video_id"`
	TimelineScores     []SecondScore `json:"timeline_scores" bson:"timeline_scores"`
	AIClips            []AIClip      `json:"ai_generated_clips" bson:"ai_generated_clips"`
	CategorySuggestion *string       `json:"category_suggestion" bson:"category_suggestion"`
	Summary            *string       `json:"summary" bson:"summary"`
	SummaryStatus      *string       `json:"summary_status" bson:"summary_status"` // draft|approved
	SuggestedTitle     *string       `json:"suggested_title" bson:"suggested_title"`
	KeyMoments         []KeyMoment   `json:"key_moments" bson:"key_moments"`
	Hashtags           []string      `json:"hashtags" bson:"hashtags"`
	CreatedAt          time.Time     `json:"created_at" bson:"created_at"`
}

// --- Vector store payloads (database_schema.md §4) ---

type FrameEmbedding struct {
	VideoID      string    `json:"video_id" bson:"video_id"`
	Timestamp    float64   `json:"timestamp" bson:"timestamp"`
	Vector       []float32 `json:"vector" bson:"vector"` // 128 dim
	ThumbnailURL string    `json:"thumbnail_url" bson:"thumbnail_url"`
}

type FrameHit struct {
	VideoID         string  `json:"video_id" bson:"video_id"`
	Timestamp       float64 `json:"timestamp" bson:"timestamp"`
	SimilarityScore float64 `json:"similarity_score" bson:"similarity_score"` // 0-1 cosine
	ThumbnailURL    string  `json:"thumbnail_url" bson:"thumbnail_url"`
}

type VideoHit struct {
	VideoID string  `json:"video_id" bson:"video_id"`
	Score   float64 `json:"score" bson:"score"` // 0-1 inner product
}

// --- AI results (inference-service :8001) ---

type VisionResult struct {
	CategorySuggestion string      `json:"category_suggestion" bson:"category_suggestion"`
	Embeddings256      [][]float32 `json:"embeddings_256" bson:"embeddings_256"`
}

type ASRResult struct {
	FullTranscript string    `json:"full_transcript" bson:"full_transcript"`
	Segments       []Segment `json:"segments" bson:"segments"`
}

type HighlightResult struct {
	TimelineScores   []SecondScore `json:"timeline_scores" bson:"timeline_scores"`
	RecommendedClips []AIClip      `json:"recommended_clips" bson:"recommended_clips"`
}

type SearchResult struct {
	Hits []FrameHit `json:"hits" bson:"hits"`
}

type RecResult struct {
	Hits               []VideoHit `json:"hits" bson:"hits"`
	RecommendationMode string     `json:"recommendation_mode" bson:"recommendation_mode"`
}

type SummaryResult struct {
	Text  string `json:"text" bson:"text"`
	Title string `json:"title" bson:"title"`
}

type AIHealth struct {
	GpuVramUsed  float64  `json:"gpu_vram_used" bson:"gpu_vram_used"`
	GpuUtil      float64  `json:"gpu_util" bson:"gpu_util"`
	ModelsLoaded []string `json:"models_loaded" bson:"models_loaded"`
	QueueDepth   int      `json:"queue_depth" bson:"queue_depth"`
	Device       string   `json:"device" bson:"device"`
	StubMode     bool     `json:"stub_mode" bson:"stub_mode"`
}
