package domain

import "time"

type CMSVideoFilter struct {
	Status            *string
	Query, CategoryID string
	From, To          *time.Time
	IncludeDeleted    bool
	SortAssigned      bool // newest category assignment first (Categories "recent")
	Page, Size        int
}

type ProcessingOptions struct {
	AutoHighlightEnabled bool `json:"auto_highlight_enabled" bson:"auto_highlight_enabled"`
	AutoSubtitleEnabled  bool `json:"auto_subtitle_enabled" bson:"auto_subtitle_enabled"`
}

func (o ProcessingOptions) SkippedStages() []string {
	stages := []string{}
	if !o.AutoSubtitleEnabled {
		stages = append(stages, string(StageAsrExtracting), string(StageSummarizing))
	}
	if !o.AutoHighlightEnabled {
		stages = append(stages, string(StageHighlightScoring))
	}
	return stages
}

type ProposalDecision struct {
	ProposalIndex int    `json:"proposal_index" bson:"proposal_index"`
	Status        string `json:"status" bson:"status"`
}
type CategoryMatch struct {
	CategoryID string  `json:"category_id" bson:"category_id"`
	Name       string  `json:"name" bson:"name"`
	Source     string  `json:"source" bson:"source"`
	Keyword    *string `json:"keyword,omitempty" bson:"keyword,omitempty"`
}

type BucketUsage struct {
	Name    string `json:"name"`
	Bytes   int64  `json:"bytes"`
	Objects int64  `json:"objects"`
}
type StorageUsage struct {
	TotalBytes int64         `json:"total_bytes"`
	Buckets    []BucketUsage `json:"buckets"`
}
type DailyProcessing struct {
	Date  string `json:"date"`
	Count int    `json:"count"`
}
type CMSMetrics struct {
	TotalVideos              int               `json:"total_videos"`
	ProcessedVideos          int               `json:"processed_videos"`
	FailedVideos             int               `json:"failed_videos"`
	DeletedVideos            int               `json:"deleted_videos"`
	PublishedClips           int               `json:"published_clips"`
	PendingJobs              int               `json:"pending_jobs"`
	RunningJobs              int               `json:"running_jobs"`
	CompletedJobs            int               `json:"completed_jobs"`
	FailedJobs               int               `json:"failed_jobs"`
	TotalUsers               int               `json:"total_users"`
	ActiveUsers              int               `json:"active_users"`
	ViewsMonth               int64             `json:"views_month"`
	TotalViews               int64             `json:"total_views"`
	SuccessRate              *float64          `json:"success_rate"`
	AverageProcessingSeconds *float64          `json:"average_processing_seconds"`
	DailyProcessing          []DailyProcessing `json:"daily_processing"`
}

// ReviewedClips preserves original proposal indices while excluding editor-dismissed ranges.
func (a *VideoAnalysis) ReviewedClips() []AIClip {
	dismissed := map[int]bool{}
	for _, d := range a.ProposalDecisions {
		if d.Status == "dismissed" {
			dismissed[d.ProposalIndex] = true
		}
	}
	out := []AIClip{}
	for i, c := range a.AIClips {
		if !dismissed[i] {
			out = append(out, c)
		}
	}
	return out
}
