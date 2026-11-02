package cms

import (
	"errors"
	"math"
	"net/http"
	"strconv"
	"strings"
	"time"
	"unicode/utf8"

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
	settings ports.SettingsRepository
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
	options := domain.ProcessingOptions{AutoHighlightEnabled: true, AutoSubtitleEnabled: true}
	if h.settings != nil {
		settings, err := h.settings.Get(c.Request.Context())
		if err != nil {
			handlers.ErrorEnvelope(c, 503, "SERVICE_UNAVAILABLE", "Unable to read processing settings")
			return
		}
		options.AutoHighlightEnabled = settings.AutoHighlightEnabled
		options.AutoSubtitleEnabled = settings.AutoSubtitleEnabled
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
		_ = h.videos.SetStatus(c.Request.Context(), v.ID, domain.VideoFailed)
		handlers.ErrorEnvelope(c, 500, "INTERNAL", err.Error())
		return
	}
	if err := h.jobs.SetProcessingOptions(c.Request.Context(), job.ID, options); err != nil {
		_ = h.jobs.SetError(c.Request.Context(), job.ID, "Unable to store processing settings")
		_ = h.jobs.SetStatus(c.Request.Context(), job.ID, domain.JobFailed, false, true)
		_ = h.videos.SetStatus(c.Request.Context(), v.ID, domain.VideoFailed)
		handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to store processing settings")
		return
	}
	job.ProcessingOptions = &options
	job.SkippedStages = options.SkippedStages()
	if err := h.bus.Publish(c.Request.Context(), "video.uploaded", v.ID, gin.H{"video_id": v.ID, "raw_file_path": path}); err != nil {
		_ = h.jobs.SetError(c.Request.Context(), job.ID, err.Error())
		_ = h.jobs.SetStatus(c.Request.Context(), job.ID, domain.JobFailed, false, true)
		_ = h.videos.SetStatus(c.Request.Context(), v.ID, domain.VideoFailed)
		handlers.ErrorEnvelope(c, 503, "INTERNAL", err.Error())
		return
	}
	c.JSON(http.StatusCreated, gin.H{"video": toVideoCMS(v, h.storage), "job": toJobCMS(job)})
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
	if status != "" && status != "uploaded" && status != "processing" && status != "processed" && status != "failed" && status != "deleted" {
		handlers.ErrorEnvelope(c, 422, "VALIDATION_ERROR", "Invalid video status")
		return
	}
	if utf8.RuneCountInString(c.Query("q")) > 200 {
		handlers.ErrorEnvelope(c, 422, "VALIDATION_ERROR", "Search too long")
		return
	}
	includeDeleted, err := strconv.ParseBool(c.DefaultQuery("include_deleted", "false"))
	if err != nil {
		handlers.ErrorEnvelope(c, 422, "VALIDATION_ERROR", "Invalid include_deleted")
		return
	}
	filter := domain.CMSVideoFilter{Status: statusPtr, Query: c.Query("q"), CategoryID: c.Query("category_id"), IncludeDeleted: includeDeleted, Page: page, Size: size}
	for _, key := range []string{"date_from", "date_to"} {
		if value := c.Query(key); value != "" {
			date, err := time.Parse("2006-01-02", value)
			if err != nil {
				handlers.ErrorEnvelope(c, 422, "VALIDATION_ERROR", "Invalid date")
				return
			}
			if key == "date_from" {
				filter.From = &date
			} else {
				date = date.AddDate(0, 0, 1)
				filter.To = &date
			}
		}
	}
	if filter.From != nil && filter.To != nil && !filter.From.Before(*filter.To) {
		handlers.ErrorEnvelope(c, 422, "VALIDATION_ERROR", "Invalid date range")
		return
	}
	items, total, err := h.videos.ListCMS(c.Request.Context(), filter)
	if err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to list videos")
		return
	}
	out := make([]gin.H, 0, len(items))
	for i := range items {
		out = append(out, toVideoCMS(&items[i], h.storage))
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
	result := toVideoDetailCMS(v, h.storage)
	result["playback_url"] = nil
	if v.Status != domain.VideoDeleted && v.RawFilePath != "" {
		url, err := h.storage.GetPresigned(c.Request.Context(), "raw-videos", v.RawFilePath, time.Hour)
		if err != nil {
			handlers.ErrorEnvelope(c, 503, "STORAGE_UNAVAILABLE", "Original video unavailable")
			return
		}
		result["playback_url"] = url
	}
	c.JSON(http.StatusOK, result)
}

func (h *VideoHandlers) Delete(c *gin.Context) {
	id := c.Param("id")
	ctx := c.Request.Context()
	video, err := h.videos.Get(ctx, id)
	if err != nil {
		handlers.ErrorEnvelope(c, 404, "VIDEO_NOT_FOUND", "Video not found")
		return
	}
	if h.jobs != nil {
		if job, err := h.jobs.GetByVideo(ctx, id); err == nil && (job.Status == domain.JobRunning || job.Status == domain.JobPending) {
			handlers.ErrorEnvelope(c, 409, "CONFLICT", "Wait for the active job before deleting")
			return
		}
	}
	clips, err := h.clips.List(ctx, &id, nil)
	if err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", err.Error())
		return
	}
	for _, clip := range clips {
		if clip.Status == domain.ClipProcessing {
			handlers.ErrorEnvelope(c, 409, "CONFLICT", "Wait for clip processing before deleting")
			return
		}
	}
	if err := h.vecs.DeleteFrames(ctx, id); err != nil {
		handlers.ErrorEnvelope(c, 503, "SERVICE_UNAVAILABLE", "Vector cleanup failed; retry deletion: "+err.Error())
		return
	}
	if err := h.clips.HideByVideo(ctx, id); err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", err.Error())
		return
	}
	// All operations are idempotent. Keep the row retryable if a storage deletion fails.
	cleanup := func() error {
		if video.RawFilePath != "" {
			key := strings.TrimPrefix(video.RawFilePath, "raw-videos/")
			if err := h.storage.Delete(ctx, "raw-videos", key); err != nil {
				return err
			}
		}
		if err := h.storage.Delete(ctx, "raw-videos", "audio/"+id+".wav"); err != nil {
			return err
		}
		if err := h.storage.DeletePrefix(ctx, "thumbnails", id+"/"); err != nil {
			return err
		}
		for _, clip := range clips {
			if clip.ClipFilePath != nil && *clip.ClipFilePath != "" {
				if err := h.storage.Delete(ctx, "clips", strings.TrimPrefix(*clip.ClipFilePath, "clips/")); err != nil {
					return err
				}
			}
		}
		if err := h.analyses.Delete(ctx, id); err != nil {
			return err
		}
		if err := h.subs.Delete(ctx, id); err != nil {
			return err
		}
		return nil
	}
	if err := cleanup(); err != nil {
		handlers.ErrorEnvelope(c, 503, "SERVICE_UNAVAILABLE", "Storage cleanup failed; retry deletion: "+err.Error())
		return
	}
	if video.Status != domain.VideoDeleted {
		if err := h.videos.SoftDelete(ctx, id); err != nil {
			handlers.ErrorEnvelope(c, 500, "INTERNAL", err.Error())
			return
		}
	}
	if h.cache != nil {
		_ = h.cache.Delete(ctx, "subs:"+id)
		_ = h.cache.Set(ctx, "feed:revision", newID(), 24*time.Hour)
	}
	c.Status(http.StatusNoContent)
}

func (h *VideoHandlers) GetAnalysis(c *gin.Context) {
	id := c.Param("id")
	if _, err := h.videos.Get(c.Request.Context(), id); err != nil {
		handlers.ErrorEnvelope(c, http.StatusNotFound, "VIDEO_NOT_FOUND", "Video not found")
		return
	}
	a, err := h.analyses.Get(c.Request.Context(), id)
	if err != nil && !errors.Is(err, domain.ErrNotFound) {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to read analysis")
		return
	}
	if a == nil {
		c.JSON(http.StatusOK, gin.H{
			"timeline_scores": []gin.H{}, "ai_generated_clips": []gin.H{}, "clip_threshold": nil,
			"category_suggestion": nil, "summary": nil, "summary_status": nil,
			"suggested_title": nil, "key_moments": []gin.H{}, "hashtags": []string{}, "proposal_decisions": []domain.ProposalDecision{},
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
	result := gin.H{
		"timeline_scores": scores, "ai_generated_clips": clips, "clip_threshold": a.ClipThreshold,
		"category_suggestion": a.CategorySuggestion, "summary": a.Summary, "summary_status": a.SummaryStatus,
		"suggested_title": a.SuggestedTitle, "key_moments": kms, "hashtags": hs, "proposal_decisions": append([]domain.ProposalDecision{}, a.ProposalDecisions...),
	}
	if a.CategoryMatch != nil {
		result["category_match"] = a.CategoryMatch
	}
	c.JSON(http.StatusOK, result)
}

func (h *VideoHandlers) RegenerateSummary(c *gin.Context) {
	id := c.Param("id")
	_, ok := h.editableVideo(c)
	if !ok {
		return
	}
	sub, err := h.subs.Get(c.Request.Context(), id)
	if err != nil {
		handlers.ErrorEnvelope(c, http.StatusNotFound, "VIDEO_NOT_FOUND", "Video not found")
		return
	}
	if strings.TrimSpace(sub.FullTranscript) == "" {
		handlers.ErrorEnvelope(c, 422, "VALIDATION_ERROR", "No transcript available for AI summary")
		return
	}
	res, err := h.ai.Summarize(c.Request.Context(), sub.FullTranscript, 256)
	if err != nil {
		handlers.ErrorEnvelope(c, http.StatusServiceUnavailable, "AI_UNAVAILABLE", err.Error())
		return
	}
	if err := h.analyses.SetSummary(c.Request.Context(), id, res.Text, "draft"); err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to save AI draft")
		return
	}
	c.JSON(http.StatusOK, gin.H{"summary": res.Text, "suggested_title": res.Title})
}

func (h *VideoHandlers) SetCategory(c *gin.Context) {
	id := c.Param("id")
	_, ok := h.editableVideo(c)
	if !ok {
		return
	}
	var req struct {
		CategoryID string `json:"category_id" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		handlers.ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", err.Error())
		return
	}
	if err := h.videos.SetCategory(c.Request.Context(), id, req.CategoryID); err != nil {
		if errors.Is(err, domain.ErrVideoNotFound) || errors.Is(err, domain.ErrCategoryNotFound) {
			handlers.ErrorEnvelope(c, 404, "NOT_FOUND", "Video or category not found")
		} else {
			handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to save category")
		}
		return
	}
	if h.cache != nil {
		_ = h.cache.Set(c.Request.Context(), "feed:revision", newID(), 24*time.Hour)
	}
	c.Status(http.StatusOK)
}

func (h *VideoHandlers) SetSummary(c *gin.Context) {
	id := c.Param("id")
	_, ok := h.editableVideo(c)
	if !ok {
		return
	}
	var req struct {
		Summary *string `json:"summary" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		handlers.ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", err.Error())
		return
	}
	if err := h.analyses.SetSummary(c.Request.Context(), id, *req.Summary, "draft"); err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to save summary")
		return
	}
	c.Status(http.StatusOK)
}

func (h *VideoHandlers) ApproveSummary(c *gin.Context) {
	id := c.Param("id")
	_, ok := h.editableVideo(c)
	if !ok {
		return
	}
	a, err := h.analyses.Get(c.Request.Context(), id)
	if errors.Is(err, domain.ErrNotFound) || (err == nil && (a.Summary == nil || strings.TrimSpace(*a.Summary) == "")) {
		handlers.ErrorEnvelope(c, http.StatusNotFound, "VIDEO_NOT_FOUND", "Video not found")
		return
	}
	if err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to read summary")
		return
	}
	if err := h.analyses.SetSummary(c.Request.Context(), id, *a.Summary, "approved"); err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to approve summary")
		return
	}
	c.Status(http.StatusOK)
}

func (h *VideoHandlers) UpdateSubtitles(c *gin.Context) {
	id := c.Param("id")
	video, ok := h.editableVideo(c)
	if !ok {
		return
	}
	var req struct {
		Segments []domain.Segment `json:"segments" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		handlers.ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", err.Error())
		return
	}
	seen := map[int]bool{}
	for _, segment := range req.Segments {
		if segment.SegmentIndex < 0 || seen[segment.SegmentIndex] || math.IsNaN(segment.StartTime) || math.IsNaN(segment.EndTime) || segment.StartTime < 0 || segment.EndTime <= segment.StartTime || segment.EndTime > video.DurationSeconds+0.1 || segment.Confidence < 0 || segment.Confidence > 1 {
			handlers.ErrorEnvelope(c, 422, "VALIDATION_ERROR", "Invalid subtitle index, timing or confidence")
			return
		}
		seen[segment.SegmentIndex] = true
	}
	if err := h.subs.UpdateSegments(c.Request.Context(), id, req.Segments); err != nil {
		if errors.Is(err, domain.ErrNotFound) {
			handlers.ErrorEnvelope(c, 404, "VIDEO_NOT_FOUND", "Subtitles not found")
		} else {
			handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to save subtitles")
		}
		return
	}
	if h.cache != nil {
		_ = h.cache.Delete(c.Request.Context(), "subs:"+id)
	}
	c.Status(http.StatusOK)
}

func toVideoCMS(v *domain.Video, storage ports.ObjectStorage) gin.H {
	result := gin.H{
		"id": v.ID, "title": v.Title, "description": v.Description,
		"thumbnail_url": handlers.ThumbnailURL(handlers.VideoThumbnailReference(v), storage), "duration_seconds": v.DurationSeconds,
		"editorial_priority": editorialPriority(v.EditorialPriority), "uploaded_by": v.UploadedBy, "uploaded_by_name": v.UploadedByName,
		"status": string(v.Status), "created_at": v.CreatedAt.UTC().Format(time.RFC3339),
	}
	if v.CategoryID != nil {
		category := gin.H{"id": *v.CategoryID}
		if v.CategoryName != nil {
			category["name"] = *v.CategoryName
		}
		result["category"] = category
	}
	return result
}
func toJobCMS(j *domain.ProcessingJob) gin.H {
	if j == nil {
		return gin.H{}
	}
	result := gin.H{"id": j.ID, "video_id": j.VideoID, "status": string(j.Status), "current_stage": j.CurrentStage, "progress": j.Progress, "error_log": j.ErrorLog, "updated_at": j.UpdatedAt.UTC().Format(time.RFC3339), "skipped_stages": append([]string{}, j.SkippedStages...)}
	if j.ProcessingOptions != nil {
		result["processing_options"] = j.ProcessingOptions
	}
	return result
}
func strPtr(s string) *string { return &s }
func newID() string {
	// short random hex (avoid import crypto/rand in cms pkg circular)
	return strconv.FormatInt(time.Now().UnixNano(), 36)
}

func editorialPriority(value string) string {
	if value == "" {
		return "normal"
	}
	return value
}

func (h *VideoHandlers) WithSettings(settings ports.SettingsRepository) *VideoHandlers {
	h.settings = settings
	return h
}

func (h *VideoHandlers) editableVideo(c *gin.Context) (*domain.Video, bool) {
	v, err := h.videos.GetProcessed(c.Request.Context(), c.Param("id"))
	if errors.Is(err, domain.ErrVideoNotFound) {
		handlers.ErrorEnvelope(c, 404, "VIDEO_NOT_FOUND", "Processed video not found")
		return nil, false
	}
	if err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to read video")
		return nil, false
	}
	return v, true
}
