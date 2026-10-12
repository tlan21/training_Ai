package ports

import (
	"context"

	"traning_ai/backend/internal/domain"
)

// 02_backend_plan.md §2.8–2.10 — stores.

type AnalysisStore interface {
	Put(ctx context.Context, videoID string, timelineScores []domain.SecondScore, aiClips []domain.AIClip, categorySuggestion *string) error
	Get(ctx context.Context, videoID string) (*domain.VideoAnalysis, error)
	SetSummary(ctx context.Context, videoID, summary, status string) error
	Delete(ctx context.Context, videoID string) error
}

type SubtitleStore interface {
	Put(ctx context.Context, videoID, language, fullTranscript string, segments []domain.Segment) error
	Get(ctx context.Context, videoID string) (*domain.Subtitle, error)
	UpdateSegments(ctx context.Context, videoID string, segments []domain.Segment) error
	TextSearch(ctx context.Context, q string) ([]domain.SubtitleMatch, error)
	Delete(ctx context.Context, videoID string) error
}

type VectorStore interface {
	UpsertFrames(ctx context.Context, videoID string, items []domain.FrameEmbedding) error
	SearchFrames(ctx context.Context, vector []float32, topK int, threshold float64) ([]domain.FrameHit, error)
	DeleteFrames(ctx context.Context, videoID string) error
	UpsertUser(ctx context.Context, userID string, vector []float32, tags []string) error
	UpsertVideoVec(ctx context.Context, videoID string, vector []float32, tags []string) error
	SearchVideosForUser(ctx context.Context, userID string, limit int) ([]domain.VideoHit, error)
}
