package cms

import (
	"context"
	"github.com/gin-gonic/gin"
	"net/http/httptest"
	"testing"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/mocks"
)

func TestJobCancelRetryPreservePolicyAndDeletedGuard(t *testing.T) {
	ctx := context.Background()
	videos, jobs, bus := mocks.NewVideoRepoMem(), mocks.NewJobRepoMem(), mocks.NewEventBusMem()
	_ = videos.Create(ctx, &domain.Video{ID: "vid_job", Status: domain.VideoProcessing, RawFilePath: "raw-videos/test.mp4"})
	job, _ := jobs.Create(ctx, "vid_job")
	_ = jobs.SetProcessingOptions(ctx, job.ID, domain.ProcessingOptions{AutoHighlightEnabled: false, AutoSubtitleEnabled: true})
	_ = jobs.SetStatus(ctx, job.ID, domain.JobRunning, true, false)
	_ = jobs.SetStage(ctx, job.ID, domain.StageHighlightScoring)
	h := NewJobHandlers(jobs, bus, videos)
	r := gin.New()
	r.GET("/jobs", h.List)
	r.POST("/jobs/:id/cancel", h.Cancel)
	r.POST("/jobs/:id/retry", h.Retry)
	call := func(action string, status int) {
		t.Helper()
		w := httptest.NewRecorder()
		r.ServeHTTP(w, httptest.NewRequest("POST", "/jobs/"+job.ID+"/"+action, nil))
		if w.Code != status {
			t.Fatalf("%s: %d %s", action, w.Code, w.Body)
		}
	}
	call("cancel", 200)
	stored, _ := jobs.Get(ctx, job.ID)
	v, _ := videos.Get(ctx, "vid_job")
	if stored.CompletedAt == nil || stored.ErrorLog == nil || *stored.ErrorLog != "canceled_by_user" || v.Status != domain.VideoFailed {
		t.Fatalf("cancel: %+v %+v", stored, v)
	}
	call("retry", 200)
	stored, _ = jobs.Get(ctx, job.ID)
	v, _ = videos.Get(ctx, "vid_job")
	if stored.Status != domain.JobPending || stored.StartedAt != nil || stored.CompletedAt != nil || stored.CurrentStage != nil || stored.ErrorLog != nil || stored.Progress != 0 || stored.ProcessingOptions == nil || stored.ProcessingOptions.AutoHighlightEnabled || v.Status != domain.VideoUploaded || len(bus.Events) != 1 {
		t.Fatalf("retry: %+v %+v", stored, v)
	}
	call("retry", 409)
	_ = jobs.SetStatus(ctx, job.ID, domain.JobFailed, false, true)
	_ = videos.SoftDelete(ctx, v.ID)
	call("retry", 409)
	v, _ = videos.Get(ctx, v.ID)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest("GET", "/jobs", nil))
	if w.Code != 200 || w.Body.String() != "[]" {
		t.Fatalf("deleted video job still listed: %d %s", w.Code, w.Body)
	}
	if v.Status != domain.VideoDeleted || len(bus.Events) != 1 {
		t.Fatal("retry revived deleted media")
	}
}
