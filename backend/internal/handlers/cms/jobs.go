package cms

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/handlers"
	"traning_ai/backend/internal/ports"
)

type JobHandlers struct {
	jobs   ports.JobRepository
	bus    ports.EventBus
	videos ports.VideoRepository
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
	items, _ := h.jobs.List(c.Request.Context(), sp)
	out := make([]gin.H, 0, len(items))
	for i := range items {
		out = append(out, toJobCMS(&items[i]))
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
	c.JSON(http.StatusOK, toJobCMS(j))
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
