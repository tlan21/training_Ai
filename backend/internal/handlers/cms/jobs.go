package cms

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/handlers"
	"traning_ai/backend/internal/ports"
)

type JobHandlers struct {
	jobs ports.JobRepository
	bus  ports.EventBus
}

func NewJobHandlers(jobs ports.JobRepository, bus ports.EventBus) *JobHandlers {
	return &JobHandlers{jobs: jobs, bus: bus}
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
	_ = h.jobs.SetStatus(c.Request.Context(), id, domain.JobPending, false, false)
	_ = h.bus.Publish(c.Request.Context(), "video.uploaded", j.VideoID, gin.H{"video_id": j.VideoID})
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
