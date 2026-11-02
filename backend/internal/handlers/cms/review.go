package cms

import (
	"errors"
	"github.com/gin-gonic/gin"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/handlers"
)

func (h *VideoHandlers) ReviewHighlights(c *gin.Context) {
	var req struct {
		Decisions *[]struct {
			Index  *int    `json:"proposal_index"`
			Status *string `json:"status"`
		} `json:"proposal_decisions"`
	}
	if !readMetadataJSON(c, &req) {
		return
	}
	if req.Decisions == nil || len(*req.Decisions) > 100 {
		handlers.ErrorEnvelope(c, 422, "VALIDATION_ERROR", "Expected at most100proposal decisions")
		return
	}
	id := c.Param("id")
	v, err := h.videos.Get(c.Request.Context(), id)
	if errors.Is(err, domain.ErrVideoNotFound) {
		handlers.ErrorEnvelope(c, 404, "VIDEO_NOT_FOUND", "Video not found")
		return
	}
	if err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to read video")
		return
	}
	if v.Status != domain.VideoProcessed {
		handlers.ErrorEnvelope(c, 409, "CONFLICT", "Review requires a processed video")
		return
	}
	a, err := h.analyses.Get(c.Request.Context(), id)
	if errors.Is(err, domain.ErrNotFound) {
		handlers.ErrorEnvelope(c, 404, "VIDEO_NOT_FOUND", "Analysis not found")
		return
	}
	if err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to read analysis")
		return
	}
	decisions := []domain.ProposalDecision{}
	seen := map[int]bool{}
	for _, d := range *req.Decisions {
		if d.Index == nil || d.Status == nil || *d.Index < 0 || *d.Index >= len(a.AIClips) || seen[*d.Index] || (*d.Status != "accepted" && *d.Status != "dismissed") {
			handlers.ErrorEnvelope(c, 422, "VALIDATION_ERROR", "Invalid or duplicate proposal decision")
			return
		}
		seen[*d.Index] = true
		decisions = append(decisions, domain.ProposalDecision{ProposalIndex: *d.Index, Status: *d.Status})
	}
	if err := h.analyses.SetProposalDecisions(c.Request.Context(), id, decisions); err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to save review")
		return
	}
	h.GetAnalysis(c)
}
