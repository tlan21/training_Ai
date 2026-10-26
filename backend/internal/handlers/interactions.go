package handlers

import (
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"

	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/ports"
)

type InteractionHandlers struct {
	interactions ports.InteractionRepository
}

func NewInteractionHandlers(interactions ports.InteractionRepository) *InteractionHandlers {
	return &InteractionHandlers{interactions: interactions}
}

// POST /api/interactions — {video_id, clip_id?, interaction_type, duration_watched?}
func (h *InteractionHandlers) Create(c *gin.Context) {
	if c.GetString("user_role") != string(domain.RoleClient) {
		ErrorEnvelope(c, http.StatusForbidden, "FORBIDDEN", "Only client accounts can record interactions")
		return
	}
	var req struct {
		VideoID         string  `json:"video_id" binding:"required"`
		ClipID          *string `json:"clip_id"`
		InteractionType string  `json:"interaction_type" binding:"required"`
		DurationWatched *int    `json:"duration_watched"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", err.Error())
		return
	}
	allowed := map[string]bool{"click": true, "watch_time": true, "like": true, "share": true, "skip": true, "save": true}
	if !allowed[req.InteractionType] {
		ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "invalid interaction_type")
		return
	}
	if req.DurationWatched != nil && (*req.DurationWatched < 0 || int64(*req.DurationWatched) > 2147483647) {
		ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "duration_watched must be 0..2147483647")
		return
	}
	uid := c.GetString("user_id")
	dw := 0
	if req.DurationWatched != nil {
		dw = *req.DurationWatched
	}
	if !strings.HasPrefix(req.VideoID, "vid_") || (req.ClipID != nil && !strings.HasPrefix(*req.ClipID, "clp_")) || (req.InteractionType != "watch_time" && dw != 0) {
		ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "invalid product ID or non-watch duration")
		return
	}
	it := &domain.Interaction{
		UserID: uid, VideoID: req.VideoID, ClipID: req.ClipID,
		InteractionType: domain.InteractionType(req.InteractionType),
		DurationWatched: dw,
	}
	if err := h.interactions.Add(c.Request.Context(), it); err != nil {
		handleDomainErr(c, err)
		return
	}
	c.Status(http.StatusCreated)
}
