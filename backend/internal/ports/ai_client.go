package ports

import (
	"context"

	"traning_ai/backend/internal/domain"
)

// 02_backend_plan.md §2.14 — AIClient gọi :8001.

type AIClient interface {
	Vision(ctx context.Context, keyframePaths []string) (*domain.VisionResult, error)
	ASR(ctx context.Context, audioURL, language string) (*domain.ASRResult, error)
	Highlight(ctx context.Context, videoID string, visionEmb [][]float32, audioFeat [][]float32) (*domain.HighlightResult, error)
	Search(ctx context.Context, imageB64 string, topK int, threshold float64) (*domain.SearchResult, error)
	Recommendation(ctx context.Context, userID string, limit int, contextMeta map[string]string) (*domain.RecResult, error)
	Summarize(ctx context.Context, prompt string, maxTokens int) (*domain.SummaryResult, error)
	Health(ctx context.Context) (*domain.AIHealth, error)
}
