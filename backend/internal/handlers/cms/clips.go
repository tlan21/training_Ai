package cms

import (
	"net/http"
	"time"

	"github.com/gin-gonic/gin"

	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/handlers"
	"traning_ai/backend/internal/ports"
)

type ClipHandlers struct {
	clips  ports.ClipRepository
	videos ports.VideoRepository
	bus    ports.EventBus
}

func NewClipHandlers(clips ports.ClipRepository, videos ports.VideoRepository, bus ports.EventBus) *ClipHandlers {
	return &ClipHandlers{clips: clips, videos: videos, bus: bus}
}

// POST /api/cms/clips — {video_id,title,start_time,end_time} → draft→processing + Kafka clip.cut.requested
func (h *ClipHandlers) Create(c *gin.Context) {
	var req struct {
		VideoID   string  `json:"video_id" binding:"required"`
		Title     string  `json:"title" binding:"required"`
		StartTime float64 `json:"start_time"`
		EndTime   float64 `json:"end_time"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		handlers.ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", err.Error())
		return
	}
	if req.EndTime <= req.StartTime {
		handlers.ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "end_time must be > start_time")
		return
	}
	v, err := h.videos.Get(c.Request.Context(), req.VideoID)
	if err != nil {
		handlers.ErrorEnvelope(c, http.StatusNotFound, "VIDEO_NOT_FOUND", "Video not found")
		return
	}
	if req.EndTime > v.DurationSeconds+0.5 && v.DurationSeconds > 0 {
		handlers.ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "end_time beyond video duration")
		return
	}
	cl := &domain.Clip{
		ID: `clp_` + newID(), VideoID: req.VideoID, Title: req.Title,
		StartTime: req.StartTime, EndTime: req.EndTime,
		AverageScore: 0, Status: domain.ClipProcessing,
		CreatedAt: time.Now(), UpdatedAt: time.Now(),
	}
	_ = h.clips.Create(c.Request.Context(), cl)
	_ = h.bus.Publish(c.Request.Context(), "clip.cut.requested", cl.ID, gin.H{
		"clip_id": cl.ID, "video_id": cl.VideoID, "start_time": cl.StartTime, "end_time": cl.EndTime,
	})
	c.JSON(http.StatusCreated, toClipCMS(cl))
}

// GET /api/cms/clips?video_id&status
func (h *ClipHandlers) List(c *gin.Context) {
	vid := c.Query("video_id")
	status := c.Query("status")
	var vp, sp *string
	if vid != "" {
		vp = &vid
	}
	if status != "" {
		sp = &status
	}
	items, _ := h.clips.List(c.Request.Context(), vp, sp)
	out := make([]gin.H, 0, len(items))
	for i := range items {
		out = append(out, toClipCMS(&items[i]))
	}
	c.JSON(http.StatusOK, out)
}

func (h *ClipHandlers) Update(c *gin.Context) {
	id := c.Param("id")
	var req struct {
		Title      *string `json:"title"`
		CategoryID *string `json:"category_id"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		handlers.ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", err.Error())
		return
	}
	// load to apply category separately
	cl, err := h.clips.Get(c.Request.Context(), id)
	if err != nil {
		handlers.ErrorEnvelope(c, http.StatusNotFound, "CLIP_NOT_FOUND", "Clip not found")
		return
	}
	if req.CategoryID != nil {
		cl.CategoryID = req.CategoryID
	}
	updated, err := h.clips.UpdateMeta(c.Request.Context(), id, req.Title, nil, nil)
	if err != nil {
		handlers.ErrorEnvelope(c, http.StatusNotFound, "CLIP_NOT_FOUND", err.Error())
		return
	}
	// preserve category_id change in mem (UpdateMeta doesn't touch it, but Get returns mutated ref in mem)
	if req.CategoryID != nil {
		updated.CategoryID = req.CategoryID
	}
	c.JSON(http.StatusOK, toClipCMS(updated))
}

func (h *ClipHandlers) Delete(c *gin.Context) {
	id := c.Param("id")
	if _, err := h.clips.Get(c.Request.Context(), id); err != nil {
		handlers.ErrorEnvelope(c, http.StatusNotFound, "CLIP_NOT_FOUND", "Clip not found")
		return
	}
	_ = h.clips.SetStatus(c.Request.Context(), id, domain.ClipRejected)
	c.Status(http.StatusNoContent)
}

// POST /api/cms/clips/:id/publish — only when clip_file_path set else 409
func (h *ClipHandlers) Publish(c *gin.Context) {
	id := c.Param("id")
	cl, err := h.clips.Get(c.Request.Context(), id)
	if err != nil {
		handlers.ErrorEnvelope(c, http.StatusNotFound, "CLIP_NOT_FOUND", "Clip not found")
		return
	}
	if cl.ClipFilePath == nil || *cl.ClipFilePath == "" {
		handlers.ErrorEnvelope(c, http.StatusConflict, "CLIP_NOT_READY", "Clip not ready for publish")
		return
	}
	_ = h.clips.SetStatus(c.Request.Context(), id, domain.ClipPublished)
	c.Status(http.StatusOK)
}

func toClipCMS(cl *domain.Clip) gin.H {
	return gin.H{
		"id": cl.ID, "video_id": cl.VideoID, "title": cl.Title,
		"start_time": cl.StartTime, "end_time": cl.EndTime, "average_score": cl.AverageScore,
		"status": string(cl.Status), "created_at": cl.CreatedAt.UTC().Format(time.RFC3339),
	}
}
