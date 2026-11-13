package cms

import (
	"context"
	"errors"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"

	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/handlers"
	"traning_ai/backend/internal/orchestrator"
	"traning_ai/backend/internal/ports"
)

// INT-64 (API 0.15.0): bulk-approve AI category suggestions + the CMS bell "seen" snapshot.

type cmsAlerts interface {
	Seen(ctx context.Context, userID string) (int, int, *time.Time, error)
	MarkSeen(ctx context.Context, userID string, failed, uncategorized int) error
	UncategorizedProcessed(ctx context.Context) ([]string, error)
}

type CategoryApplyHandlers struct {
	alerts     cmsAlerts
	videos     ports.VideoRepository
	analyses   ports.AnalysisStore
	categories ports.CategoryRepository
}

func NewCategoryApplyHandlers(alerts cmsAlerts, videos ports.VideoRepository, analyses ports.AnalysisStore, categories ports.CategoryRepository) *CategoryApplyHandlers {
	return &CategoryApplyHandlers{alerts: alerts, videos: videos, analyses: analyses, categories: categories}
}

// ApplySuggestions assigns, for every processed video without a category, the stored category match (or the ViT class
// mapped now). Videos without a usable suggestion are counted as skipped and left untouched.
func (h *CategoryApplyHandlers) ApplySuggestions(c *gin.Context) {
	ctx := c.Request.Context()
	ids, err := h.alerts.UncategorizedProcessed(ctx)
	if err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to list videos")
		return
	}
	categories, err := h.categories.List(ctx)
	if err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to list categories")
		return
	}
	applied, skipped := 0, 0
	for _, id := range ids {
		a, err := h.analyses.Get(ctx, id)
		if err != nil && !errors.Is(err, domain.ErrNotFound) {
			handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to read analysis")
			return
		}
		var match *domain.CategoryMatch
		if a != nil {
			match = a.CategoryMatch
			if match == nil {
				match = orchestrator.MatchCategory(categories, a.CategorySuggestion, "", true, false)
			}
		}
		if match == nil {
			skipped++
			continue
		}
		if err := h.videos.SetCategory(ctx, id, match.CategoryID); err != nil {
			if errors.Is(err, domain.ErrVideoNotFound) || errors.Is(err, domain.ErrCategoryNotFound) {
				skipped++ // deleted meanwhile, or the matched category was removed
				continue
			}
			handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to assign category")
			return
		}
		applied++
	}
	c.JSON(http.StatusOK, gin.H{"applied": applied, "skipped": skipped})
}

func (h *CategoryApplyHandlers) GetSeen(c *gin.Context) {
	failed, uncategorized, at, err := h.alerts.Seen(c.Request.Context(), c.GetString("user_id"))
	if err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to read alerts")
		return
	}
	c.JSON(http.StatusOK, gin.H{"failed_jobs": failed, "uncategorized_videos": uncategorized, "seen_at": at})
}

func (h *CategoryApplyHandlers) PutSeen(c *gin.Context) {
	var body struct {
		FailedJobs          *int `json:"failed_jobs"`
		UncategorizedVideos *int `json:"uncategorized_videos"`
	}
	if err := c.ShouldBindJSON(&body); err != nil || body.FailedJobs == nil || body.UncategorizedVideos == nil ||
		*body.FailedJobs < 0 || *body.UncategorizedVideos < 0 || *body.FailedJobs > 1_000_000 || *body.UncategorizedVideos > 1_000_000 {
		handlers.ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "failed_jobs and uncategorized_videos must be integers >= 0")
		return
	}
	if err := h.alerts.MarkSeen(c.Request.Context(), c.GetString("user_id"), *body.FailedJobs, *body.UncategorizedVideos); err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to save alerts")
		return
	}
	c.Status(http.StatusNoContent)
}
