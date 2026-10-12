package domain

// Enums khớp api.gen.go + database_schema.md + openapi.yaml.

type Role string

const (
	RoleAdmin  Role = "admin"
	RoleEditor Role = "editor"
	RoleClient Role = "client"
)

type VideoStatus string

const (
	VideoUploaded   VideoStatus = "uploaded"
	VideoProcessing VideoStatus = "processing"
	VideoProcessed  VideoStatus = "processed"
	VideoFailed     VideoStatus = "failed"
	VideoDeleted    VideoStatus = "deleted"
)

type ClipStatus string

const (
	ClipDraft      ClipStatus = "draft"
	ClipProcessing ClipStatus = "processing"
	ClipPublished  ClipStatus = "published"
	ClipRejected   ClipStatus = "rejected"
)

type JobStatus string

const (
	JobPending   JobStatus = "pending"
	JobRunning   JobStatus = "running"
	JobCompleted JobStatus = "completed"
	JobFailed    JobStatus = "failed"
)

type Stage string

const (
	StageSplittingFrames  Stage = "splitting_frames"
	StageEmbedding        Stage = "embedding"
	StageAsrExtracting    Stage = "asr_extracting"
	StageHighlightScoring Stage = "highlight_scoring"
	StageSummarizing      Stage = "summarizing"
	StageCompleted        Stage = "completed"
)

var StageProgress = map[Stage]int{
	StageSplittingFrames:  20,
	StageAsrExtracting:    40,
	StageHighlightScoring: 60,
	StageEmbedding:        80,
	StageSummarizing:      90,
	StageCompleted:        100,
}

type InteractionType string

const (
	InteractClick     InteractionType = "click"
	InteractWatchTime InteractionType = "watch_time"
	InteractLike      InteractionType = "like"
	InteractShare     InteractionType = "share"
	InteractSkip      InteractionType = "skip"
	InteractSave      InteractionType = "save"
)
