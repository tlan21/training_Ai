package cms

import (
	"errors"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"

	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/handlers"
	"traning_ai/backend/internal/ports"
)

type VideoHandlers struct {
	videos   ports.VideoRepository
	jobs     ports.JobRepository
	analyses ports.AnalysisStore
	subs     ports.SubtitleStore
	vecs     ports.VectorStore
	cache    ports.Cache
	bus      ports.EventBus
	storage  ports.ObjectStorage
	ai       ports.AIClient
	clips    ports.ClipRepository
}

func NewVideoHandlers(
	videos ports.VideoRepository, jobs ports.JobRepository,
	analyses ports.AnalysisStore, subs ports.SubtitleStore, vecs ports.VectorStore,
	cache ports.Cache, bus ports.EventBus, storage ports.ObjectStorage, ai ports.AIClient, clips ports.ClipRepository,
) *VideoHandlers {
	return &VideoHandlers{
		videos: videos, jobs: jobs, analyses: analyses, subs: subs,
		vecs: vecs, cache: cache, bus: bus, storage: storage, ai: ai, clips: clips,
	}
}

// POST /api/cms/videos — multipart ≤2GB → MinIO + rows + Kafka video.uploaded (admin|editor)
func (h *VideoHandlers) Create(c *gin.Context) {
	const maxFileSize = 2 * 1024 * 1024 * 1024
	if c.Request.ContentLength > maxFileSize+1024*1024 {
		handlers.ErrorEnvelope(c, 413, "PAYLOAD_TOO_LARGE", "file too large (max 2GB)")
		return
	}
	c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, maxFileSize+1024*1024)
	if err := c.Request.ParseMultipartForm(8 * 1024 * 1024); err != nil {
		var sizeError *http.MaxBytesError
		if errors.As(err, &sizeError) {
			handlers.ErrorEnvelope(c, 413, "PAYLOAD_TOO_LARGE", "file too large (max 2GB)")
		} else {
			handlers.ErrorEnvelope(c, 422, "VALIDATION_ERROR", err.Error())
		}
		return
	}
	defer c.Request.MultipartForm.RemoveAll()
	title := c.PostForm("title")
	if title == "" {
		handlers.ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "title required")
		return
	}
	file, hdr, err := c.Request.FormFile("file")
	if err != nil {
		handlers.ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "file required")
		return
	}
	defer file.Close()
	if hdr.Size > maxFileSize {
		handlers.ErrorEnvelope(c, http.StatusRequestEntityTooLarge, "PAYLOAD_TOO_LARGE", "file too large (max 2GB)")
		return
	}
	desc := c.PostForm("description")
	var descPtr *string
	if desc != "" {
		descPtr = &desc
	}
	uid := c.GetString("user_id")
	v := &domain.Video{
		ID: `vid_` + newID(), Title: title, Description: descPtr,
		RawFilePath: "", DurationSeconds: 0,
		Status: domain.VideoUploaded, UploadedBy: strPtr(uid),
		CreatedAt: time.Now(), UpdatedAt: time.Now(),
	}
	ct := hdr.Header.Get("Content-Type")
	if ct == "" {
		ct = "video/mp4"
	}
	path, err := h.storage.PutStream(c.Request.Context(), "raw-videos", v.ID+".mp4", file, hdr.Size, ct)
	if err != nil {
		handlers.ErrorEnvelope(c, http.StatusInternalServerError, "INTERNAL", err.Error())
		return
	}
	v.RawFilePath = path
	if err := h.videos.Create(c.Request.Context(), v); err != nil {
		_ = h.storage.Delete(c.Request.Context(), "raw-videos", v.ID+".mp4")
		handlers.ErrorEnvelope(c, 500, "INTERNAL", err.Error())
		return
	}
	job, err := h.jobs.Create(c.Request.Context(), v.ID)
	if err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", err.Error())
		return
	}
	if err := h.bus.Publish(c.Request.Context(), "video.uploaded", v.ID, gin.H{"video_id": v.ID, "raw_file_path": path}); err != nil {
		_ = h.jobs.SetError(c.Request.Context(), job.ID, err.Error())
		_ = h.jobs.SetStatus(c.Request.Context(), job.ID, domain.JobFailed, false, false)
		handlers.ErrorEnvelope(c, 503, "INTERNAL", err.Error())
		return
	}
	c.JSON(http.StatusCreated, gin.H{"video": toVideoCMS(v), "job": toJobCMS(job)})
}

// GET /api/cms/videos?status&page
func (h *VideoHandlers) List(c *gin.Context) {
	status := c.Query("status")
	var statusPtr *string
	if status != "" {
		statusPtr = &status
	}
	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	if page < 1 {
		page = 1
	}
	const size = 20
	items, total, _ := h.videos.List(c.Request.Context(), statusPtr, page, size)
	out := make([]gin.H, 0, len(items))
	for i := range items {
		out = append(out, toVideoCMS(&items[i]))
	}
	c.JSON(http.StatusOK, gin.H{"items": out, "total": total, "page": page})
}

func (h *VideoHandlers) Get(c *gin.Context) {
	id := c.Param("id")
	v, err := h.videos.Get(c.Request.Context(), id)
	if err != nil {
		handlers.ErrorEnvelope(c, http.StatusNotFound, "VIDEO_NOT_FOUND", "Video not found")
		return
	}
	c.JSON(http.StatusOK, toVideoCMS(v))
}

func (h *VideoHandlers) Delete(c *gin.Context) {
	id := c.Param("id")
	if _, err := h.videos.Get(c.Request.Context(), id); err != nil {
		handlers.ErrorEnvelope(c, http.StatusNotFound, "VIDEO_NOT_FOUND", "Video not found")
		return
	}
	if err := h.vecs.DeleteFrames(c.Request.Context(), id); err != nil {
		handlers.ErrorEnvelope(c, 503, "AI_UNAVAILABLE", "Vector cleanup failed; retry deletion: "+err.Error())
		return
	}
	if err := h.videos.SoftDelete(c.Request.Context(), id); err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", err.Error())
		return
	}
	if err := h.clips.HideByVideo(c.Request.Context(), id); err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", err.Error())
		return
	}
	_ = h.analyses.Delete(c.Request.Context(), id)
	_ = h.subs.Delete(c.Request.Context(), id)
	if h.cache != nil {
		_ = h.cache.Delete(c.Request.Context(), "subs:"+id)
		_ = h.cache.Set(c.Request.Context(), "feed:revision", newID(), 24*time.Hour)
	}
	c.Status(http.StatusNoContent)
}

func (h *VideoHandlers) GetAnalysis(c *gin.Context) {
	id := c.Param("id")
	if _, err := h.videos.Get(c.Request.Context(), id); err != nil {
		handlers.ErrorEnvelope(c, http.StatusNotFound, "VIDEO_NOT_FOUND", "Video not found")
		return
	}
	a, _ := h.analyses.Get(c.Request.Context(), id)
	if a == nil {
		c.JSON(http.StatusOK, gin.H{
			"timeline_scores": []gin.H{}, "ai_generated_clips": []gin.H{},
			"category_suggestion": nil, "summary": nil, "summary_status": nil,
			"suggested_title": nil, "key_moments": []gin.H{}, "hashtags": []string{},
		})
		return
	}
	scores := make([]gin.H, 0, len(a.TimelineScores))
	for _, s := range a.TimelineScores {
		scores = append(scores, gin.H{"second": s.Second, "score": s.Score})
	}
	clips := make([]gin.H, 0, len(a.AIClips))
	for _, cl := range a.AIClips {
		clips = append(clips, gin.H{"start_time": cl.StartTime, "end_time": cl.EndTime, "average_score": cl.AverageScore, "reason": cl.Reason})
	}
	kms := make([]gin.H, 0, len(a.KeyMoments))
	for _, k := range a.KeyMoments {
		kms = append(kms, gin.H{"timestamp": k.Timestamp, "text": k.Text})
	}
	hs := a.Hashtags
	if hs == nil {
		hs = []string{}
	}
	c.JSON(http.StatusOK, gin.H{
		"timeline_scores": scores, "ai_generated_clips": clips,
		"category_suggestion": a.CategorySuggestion, "summary": a.Summary, "summary_status": a.SummaryStatus,
		"suggested_title": a.SuggestedTitle, "key_moments": kms, "hashtags": hs,
	})
}

func (h *VideoHandlers) RegenerateSummary(c *gin.Context) {
	id := c.Param("id")
	sub, err := h.subs.Get(c.Request.Context(), id)
	if err != nil {
		handlers.ErrorEnvelope(c, http.StatusNotFound, "VIDEO_NOT_FOUND", "Video not found")
		return
	}
	res, err := h.ai.Summarize(c.Request.Context(), sub.FullTranscript, 256)
	if err != nil {
		handlers.ErrorEnvelope(c, http.StatusServiceUnavailable, "AI_UNAVAILABLE", err.Error())
		return
	}
	_ = h.analyses.SetSummary(c.Request.Context(), id, res.Text, "draft")
	c.JSON(http.StatusOK, gin.H{"summary": res.Text, "suggested_title": res.Title})
}

func (h *VideoHandlers) SetCategory(c *gin.Context) {
	id := c.Param("id")
	var req struct {
		CategoryID string `json:"category_id" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		handlers.ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", err.Error())
		return
	}
	if err := h.videos.SetCategory(c.Request.Context(), id, req.CategoryID); err != nil {
		handlers.ErrorEnvelope(c, http.StatusNotFound, "VIDEO_NOT_FOUND", err.Error())
		return
	}
	c.Status(http.StatusOK)
}

func (h *VideoHandlers) SetSummary(c *gin.Context) {
	id := c.Param("id")
	var req struct {
		Summary string `json:"summary" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		handlers.ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", err.Error())
		return
	}
	_ = h.analyses.SetSummary(c.Request.Context(), id, req.Summary, "draft")
	c.Status(http.StatusOK)
}

func (h *VideoHandlers) ApproveSummary(c *gin.Context) {
	id := c.Param("id")
	a, err := h.analyses.Get(c.Request.Context(), id)
	if err != nil || a.Summary == nil {
		handlers.ErrorEnvelope(c, http.StatusNotFound, "VIDEO_NOT_FOUND", "Video not found")
		return
	}
	_ = h.analyses.SetSummary(c.Request.Context(), id, *a.Summary, "approved")
	c.Status(http.StatusOK)
}

func (h *VideoHandlers) UpdateSubtitles(c *gin.Context) {
	id := c.Param("id")
	var req struct {
		Segments []domain.Segment `json:"segments" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		handlers.ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", err.Error())
		return
	}
	if err := h.subs.UpdateSegments(c.Request.Context(), id, req.Segments); err != nil {
		handlers.ErrorEnvelope(c, http.StatusNotFound, "VIDEO_NOT_FOUND", err.Error())
		return
	}
	if h.cache != nil {
		_ = h.cache.Delete(c.Request.Context(), "subs:"+id)
	}
	c.Status(http.StatusOK)
}

func toVideoCMS(v *domain.Video) gin.H {
	return gin.H{
		"id": v.ID, "title": v.Title, "description": v.Description,
		"thumbnail_url": v.ThumbnailURL, "duration_seconds": v.DurationSeconds,
		"status": string(v.Status), "created_at": v.CreatedAt.UTC().Format(time.RFC3339),
	}
}
func toJobCMS(j *domain.ProcessingJob) gin.H {
	if j == nil {
		return gin.H{}
	}
	return gin.H{
		"id": j.ID, "video_id": j.VideoID, "status": string(j.Status),
		"current_stage": j.CurrentStage, "progress": j.Progress, "error_log": j.ErrorLog,
		"updated_at": j.UpdatedAt.UTC().Format(time.RFC3339),
	}
}
func strPtr(s string) *string { return &s }
func newID() string {
	// short random hex (avoid import crypto/rand in cms pkg circular)
	return strconv.FormatInt(time.Now().UnixNano(), 36)
}
