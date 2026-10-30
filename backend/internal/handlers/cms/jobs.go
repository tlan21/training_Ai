package cms

import (
	"context"
	"net/http"
	"strings"
	"unicode/utf8"

	"github.com/gin-gonic/gin"

	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/handlers"
	"traning_ai/backend/internal/ports"
)

type JobHandlers struct {
	jobs    ports.JobRepository
	bus     ports.EventBus
	videos  ports.VideoRepository
	storage ports.ObjectStorage
}

func NewJobHandlers(jobs ports.JobRepository, bus ports.EventBus, videos ports.VideoRepository) *JobHandlers {
	return &JobHandlers{jobs: jobs, bus: bus, videos: videos}
}

func (h *JobHandlers) List(c *gin.Context) {
	status := c.Query("status")
	var sp *string
	if status != "" {
		sp = &status
	}
	if status != "" && status != "pending" && status != "running" && status != "completed" && status != "failed" {
		handlers.ErrorEnvelope(c, 422, "VALIDATION_ERROR", "Invalid job status")
		return
	}
	query := strings.ToLower(strings.TrimSpace(c.Query("q")))
	if utf8.RuneCountInString(query) > 200 {
		handlers.ErrorEnvelope(c, 422, "VALIDATION_ERROR", "Search too long")
		return
	}
	items, err := h.jobs.List(c.Request.Context(), sp)
	if err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to load jobs")
		return
	}
	out := make([]gin.H, 0, len(items))
	for i := range items {
		if id := c.Query("video_id"); id != "" && items[i].VideoID != id {
			continue
		}
		dto, err := h.jobDTO(c.Request.Context(), &items[i])
		if err != nil {
			handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to load job video")
			return
		}
		title, _ := dto["video_title"].(string)
		if query != "" && !strings.Contains(strings.ToLower(title), query) && !strings.Contains(strings.ToLower(items[i].VideoID), query) {
			continue
		}
		out = append(out, dto)
	}
	c.JSON(http.StatusOK, out)
}

func (h *JobHandlers) Get(c *gin.Context) {
	id := c.Param("id")
	j, err := h.jobs.Get(c.Request.Context(), id)
	if err != nil {
		handlers.ErrorEnvelope(c, http.StatusNotFound, "JOB_NOT_FOUND", "Job not found")
		return
	}
	dto, err := h.jobDTO(c.Request.Context(), j)
	if err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to load job video")
		return
	}
	c.JSON(http.StatusOK, dto)
}

func (h *JobHandlers) Retry(c *gin.Context) {
	id := c.Param("id")
	j, err := h.jobs.Get(c.Request.Context(), id)
	if err != nil {
		handlers.ErrorEnvelope(c, http.StatusNotFound, "JOB_NOT_FOUND", "Job not found")
		return
	}
	if j.Status != domain.JobFailed {
		handlers.ErrorEnvelope(c, http.StatusConflict, "CONFLICT", "only failed jobs can be retried")
		return
	}
	v, err := h.videos.Get(c.Request.Context(), j.VideoID)
	if err != nil {
		handlers.ErrorEnvelope(c, 404, "VIDEO_NOT_FOUND", "Video not found")
		return
	}
	if err := h.jobs.SetStatus(c.Request.Context(), id, domain.JobPending, false, false); err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", err.Error())
		return
	}
	if err := h.bus.Publish(c.Request.Context(), "video.uploaded", j.VideoID, gin.H{"video_id": j.VideoID, "raw_file_path": v.RawFilePath}); err != nil {
		_ = h.jobs.SetStatus(c.Request.Context(), id, domain.JobFailed, false, false)
		handlers.ErrorEnvelope(c, 503, "INTERNAL", err.Error())
		return
	}
	c.Status(http.StatusOK)
}

func (h *JobHandlers) Cancel(c *gin.Context) {
	id := c.Param("id")
	j, err := h.jobs.Get(c.Request.Context(), id)
	if err != nil {
		handlers.ErrorEnvelope(c, http.StatusNotFound, "JOB_NOT_FOUND", "Job not found")
		return
	}
	if j.Status != domain.JobPending && j.Status != domain.JobRunning {
		handlers.ErrorEnvelope(c, http.StatusConflict, "CONFLICT", "only pending/running jobs can be canceled")
		return
	}
	_ = h.jobs.SetStatus(c.Request.Context(), id, domain.JobFailed, false, false)
	_ = h.jobs.SetError(c.Request.Context(), id, "canceled_by_user")
	c.Status(http.StatusOK)
}

func (h *JobHandlers) jobDTO(ctx context.Context, j *domain.ProcessingJob) (gin.H, error) {
	dto := toJobCMS(j)
	v, err := h.videos.Get(ctx, j.VideoID)
	if err != nil {
		return nil, err
	}
	dto["video_title"] = v.Title
	dto["thumbnail_url"] = handlers.ThumbnailURL(handlers.VideoThumbnailReference(v), h.storage)
	dto["duration_seconds"] = v.DurationSeconds
	dto["uploaded_by_name"] = v.UploadedByName
	dto["editorial_priority"] = editorialPriority(v.EditorialPriority)
	return dto, nil
}

func (h *JobHandlers) WithStorage(storage ports.ObjectStorage) *JobHandlers {
	h.storage = storage
	return h
}
