package domain

import "time"

// --- Postgres entities (database_schema.md §2.1) ---

type User struct {
	ID           string
	Username     string
	Email        string
	AvatarURL    *string
	PasswordHash string
	Role         Role
	CreatedAt    time.Time
	UpdatedAt    time.Time
}

type Session struct {
	ID               string
	UserID           string
	RefreshTokenHash string
	ExpiresAt        time.Time
	CreatedAt        time.Time
}

type Video struct {
	ID              string
	Title           string
	Description     *string
	RawFilePath     string
	ThumbnailURL    *string
	DurationSeconds float64
	Status          VideoStatus
	UploadedBy      *string
	CategoryID      *string
	DeletedAt       *time.Time
	CreatedAt       time.Time
	UpdatedAt       time.Time
}

type ProcessingJob struct {
	ID           string
	VideoID      string
	QueueName    string
	Status       JobStatus
	WorkerNodeID *string
	ErrorLog     *string
	StartedAt    *time.Time
	CompletedAt  *time.Time
	UpdatedAt    time.Time
	CurrentStage *Stage
	Progress     int
}

type Clip struct {
	ID            string
	VideoID       string
	Title         string
	StartTime     float64
	EndTime       float64
	AverageScore  float64
	ClipFilePath  *string
	ThumbnailURL  *string
	Status        ClipStatus
	CreatedBy     *string
	CategoryID    *string
	CreatedAt     time.Time
	UpdatedAt     time.Time
}

type Category struct {
	ID        string
	Name      string
	CreatedAt time.Time
}

type Interaction struct {
	ID              int64
	UserID          string
	VideoID         string
	ClipID          *string
	InteractionType InteractionType
	DurationWatched int
	CreatedAt       time.Time
}

type HistoryItem struct {
	Clip            Clip
	WatchedAt       time.Time
	DurationWatched int
}

// --- Mongo documents (database_schema.md §3) ---

type Segment struct {
	SegmentIndex int
	StartTime    float64
	EndTime      float64
	Text         string
	Confidence   float64
	Warning      *string
}

type Subtitle struct {
	VideoID        string
	Language       string
	FullTranscript string
	Segments       []Segment
	CreatedAt      time.Time
}

type SubtitleMatch struct {
	VideoID   string
	Title     *string
	Timestamp float64
	Text      string
}

type SecondScore struct {
	Second int
	Score  float64 // 0-100 master plan §2.6
}

type AIClip struct {
	StartTime    float64
	EndTime      float64
	AverageScore float64 // 0-100
	Reason       *string
}

type KeyMoment struct {
	Timestamp float64
	Text      string
}

type VideoAnalysis struct {
	VideoID            string
	TimelineScores     []SecondScore
	AIClips            []AIClip
	CategorySuggestion *string
	Summary            *string
	SummaryStatus      *string // draft|approved
	SuggestedTitle     *string
	KeyMoments         []KeyMoment
	Hashtags           []string
	CreatedAt          time.Time
}

// --- Vector store payloads (database_schema.md §4) ---

type FrameEmbedding struct {
	VideoID      string
	Timestamp    float64
	Vector       []float32 // 128 dim
	ThumbnailURL string
}

type FrameHit struct {
	VideoID         string
	Timestamp       float64
	SimilarityScore float64 // 0-1 cosine
	ThumbnailURL    string
}

type VideoHit struct {
	VideoID string
	Score   float64 // 0-1 inner product
}

// --- AI results (inference-service :8001) ---

type VisionResult struct {
	CategorySuggestion string
	Embeddings256      [][]float32
}

type ASRResult struct {
	FullTranscript string
	Segments       []Segment
}

type HighlightResult struct {
	TimelineScores   []SecondScore
	RecommendedClips []AIClip
}

type SearchResult struct {
	Hits []FrameHit
}

type RecResult struct {
	Hits []VideoHit
}

type SummaryResult struct {
	Text  string
	Title string
}

type AIHealth struct {
	GpuVramUsed  float64
	GpuUtil      float64
	ModelsLoaded []string
	QueueDepth   int
	Device       string
	StubMode     bool
}
