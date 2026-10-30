package cms

import (
	"math"
	"net/http"
	"time"
	"unicode/utf8"

	"github.com/gin-gonic/gin"

	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/handlers"
	"traning_ai/backend/internal/ports"
)

type ClipHandlers struct {
	storage  ports.ObjectStorage
	clips    ports.ClipRepository
	videos   ports.VideoRepository
	bus      ports.EventBus
	cache    ports.Cache
	analyses ports.AnalysisStore
}

func NewClipHandlers(clips ports.ClipRepository, videos ports.VideoRepository, bus ports.EventBus, cache ports.Cache, analyses ports.AnalysisStore, storage ports.ObjectStorage) *ClipHandlers {
	return &ClipHandlers{clips: clips, videos: videos, bus: bus, cache: cache, analyses: analyses, storage: storage}
}

// POST /api/cms/clips — {video_id,title,start_time,end_time} → draft→processing + Kafka clip.cut.requested
func (h *ClipHandlers) Create(c *gin.Context) {
	var req struct {
		AutoHighlights bool     `json:"auto_highlights"`
		VideoID        string   `json:"video_id" binding:"required"`
		Title          string   `json:"title" binding:"required"`
		StartTime      *float64 `json:"start_time"`
		EndTime        *float64 `json:"end_time"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		handlers.ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", err.Error())
		return
	}
	if !req.AutoHighlights && (req.StartTime == nil || req.EndTime == nil || *req.StartTime < 0 || *req.EndTime <= *req.StartTime) {
		handlers.ErrorEnvelope(c, 422, "VALIDATION_ERROR", "Cần khoảng bắt đầu/kết thúc hợp lệ hoặc auto_highlights=true")
		return
	}
	v, err := h.videos.Get(c.Request.Context(), req.VideoID)
	if err != nil {
		handlers.ErrorEnvelope(c, http.StatusNotFound, "VIDEO_NOT_FOUND", "Video not found")
		return
	}
	if v.Status != domain.VideoProcessed {
		handlers.ErrorEnvelope(c, 409, "CONFLICT", "Video has not finished processing")
		return
	}
	analysis, err := h.analyses.Get(c.Request.Context(), req.VideoID)
	if err != nil {
		handlers.ErrorEnvelope(c, 503, "AI_UNAVAILABLE", "Video analysis is not available")
		return
	}
	var source []domain.ClipSourceSegment
	start, end := 0.0, 0.0
	if req.AutoHighlights {
		source = domain.CompilationSegments(analysis.ReviewedClips(), v.DurationSeconds)
		if !domain.ValidSourceSegments(source, v.DurationSeconds) {
			handlers.ErrorEnvelope(c, 422, "VALIDATION_ERROR", "Chưa có đoạn AI hợp lệ để tổng hợp (tối đa 100 đoạn). Bạn vẫn có thể cắt thủ công.")
			return
		}
		for _, segment := range source {
			end += segment.EndTime - segment.StartTime
		}
	} else {
		start, end = *req.StartTime, *req.EndTime
		if end > v.DurationSeconds+0.5 && v.DurationSeconds > 0 {
			handlers.ErrorEnvelope(c, 422, "VALIDATION_ERROR", "end_time beyond video duration")
			return
		}
	}
	cl := &domain.Clip{
		ID: "clp_" + newID(), VideoID: req.VideoID, Title: req.Title,
		ThumbnailURL: handlers.VideoThumbnailReference(v), SourceSegments: source,
		CreatedBy: strPtr(c.GetString("user_id")),
		StartTime: start, EndTime: end, Status: domain.ClipProcessing,
		CreatedAt: time.Now(), UpdatedAt: time.Now(),
	}
	if cl.CreatedBy != nil && *cl.CreatedBy == "" {
		cl.CreatedBy = nil
	}
	ranges := source
	if len(ranges) == 0 {
		ranges = []domain.ClipSourceSegment{{StartTime: start, EndTime: end}}
	}
	var total, weight float64
	for _, segment := range ranges {
		for _, score := range analysis.TimelineScores {
			overlap := math.Max(0, math.Min(float64(score.Second+1), segment.EndTime)-math.Max(float64(score.Second), segment.StartTime))
			total += overlap * score.Score
			weight += overlap
		}
	}
	if weight > 0 {
		cl.AverageScore = math.Round(total/weight*100) / 100
	}
	if err := h.clips.Create(c.Request.Context(), cl); err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", err.Error())
		return
	}
	if err := h.bus.Publish(c.Request.Context(), "clip.cut.requested", cl.ID, gin.H{
		"clip_id": cl.ID, "video_id": cl.VideoID, "start_time": cl.StartTime, "end_time": cl.EndTime,
	}); err != nil {
		_ = h.clips.SetStatus(c.Request.Context(), cl.ID, domain.ClipRejected)
		handlers.ErrorEnvelope(c, 503, "INTERNAL", err.Error())
		return
	}
	c.JSON(http.StatusCreated, toClipCMS(cl, h.storage))
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
	if status != "" && status != "draft" && status != "processing" && status != "published" && status != "rejected" {
		handlers.ErrorEnvelope(c, 422, "VALIDATION_ERROR", "Invalid clip status")
		return
	}
	if utf8.RuneCountInString(c.Query("q")) > 200 {
		handlers.ErrorEnvelope(c, 422, "VALIDATION_ERROR", "Search too long")
		return
	}
	items, err := h.clips.ListCMS(c.Request.Context(), vp, sp, c.Query("q"))
	if err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to load clips")
		return
	}
	out := make([]gin.H, 0, len(items))
	for i := range items {
		out = append(out, toClipCMS(&items[i], h.storage))
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
	c.JSON(http.StatusOK, toClipCMS(updated, h.storage))
}

func (h *ClipHandlers) Delete(c *gin.Context) {
	id := c.Param("id")
	if _, err := h.clips.Get(c.Request.Context(), id); err != nil {
		handlers.ErrorEnvelope(c, http.StatusNotFound, "CLIP_NOT_FOUND", "Clip not found")
		return
	}
	_ = h.clips.SetStatus(c.Request.Context(), id, domain.ClipRejected)
	h.invalidateFeed(c)
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
	if cl.ClipFilePath == nil || *cl.ClipFilePath == "" || (cl.Status != domain.ClipDraft && cl.Status != domain.ClipPublished) {
		handlers.ErrorEnvelope(c, http.StatusConflict, "CLIP_NOT_READY", "Clip not ready for publish")
		return
	}
	v, err := h.videos.GetProcessed(c.Request.Context(), cl.VideoID)
	if err != nil || v == nil {
		handlers.ErrorEnvelope(c, 409, "CLIP_NOT_READY", "Source video is not available for publishing")
		return
	}
	if err := h.clips.SetStatus(c.Request.Context(), id, domain.ClipPublished); err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", err.Error())
		return
	}
	h.invalidateFeed(c)
	c.Status(http.StatusOK)
}

func (h *ClipHandlers) invalidateFeed(c *gin.Context) {
	if h.cache != nil {
		// Change the shared revision so every user's cached feed expires on the next read.
		_ = h.cache.Set(c.Request.Context(), "feed:revision", newID(), 24*time.Hour)
	}
}

func toClipCMS(cl *domain.Clip, storage ports.ObjectStorage) gin.H {
	var playback *string
	if cl.ClipFilePath != nil && storage != nil {
		if url, err := storage.GetPresigned(nil, "clips", *cl.ClipFilePath, time.Hour); err == nil {
			playback = &url
		}
	}
	return gin.H{
		"playback_url": playback, "source_segments": append([]domain.ClipSourceSegment{}, cl.SourceSegments...),
		"id": cl.ID, "video_id": cl.VideoID, "title": cl.Title,
		"start_time": cl.StartTime, "end_time": cl.EndTime, "average_score": cl.AverageScore,
		"thumbnail_url": handlers.ThumbnailURL(cl.ThumbnailURL, storage),
		"view_count":    cl.ViewCount, "created_by_name": cl.CreatedByName, "category_name": cl.CategoryName, "updated_at": cl.UpdatedAt.UTC().Format(time.RFC3339),
		"status": string(cl.Status), "created_at": cl.CreatedAt.UTC().Format(time.RFC3339),
	}
}
