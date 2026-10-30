package orchestrator

import (
	"context"
	"testing"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/mocks"
)

func TestFailedPreprocessingMarksVideoFailed(t *testing.T) {
	ctx := context.Background()
	videos, jobs := mocks.NewVideoRepoMem(), mocks.NewJobRepoMem()
	_ = videos.Create(ctx, &domain.Video{ID: "vid_invalid", Status: domain.VideoUploaded})
	job, _ := jobs.Create(ctx, "vid_invalid")
	r := New(videos, jobs, mocks.NewAnalysisStoreMem(), mocks.NewSubtitleStoreMem(), &mocks.AIClientMem{}, mocks.NewEventBusMem())
	if err := r.HandlePreprocessed(ctx, []byte(`{"video_id":"vid_invalid","duration":0}`)); err == nil {
		t.Fatal("invalid video accepted")
	}
	v, _ := videos.Get(ctx, "vid_invalid")
	j, _ := jobs.Get(ctx, job.ID)
	if v.Status != domain.VideoFailed || j.Status != domain.JobFailed || j.CompletedAt == nil {
		t.Fatalf("inconsistent failed ingest: video=%s job=%s completed=%v", v.Status, j.Status, j.CompletedAt)
	}
}

func TestCancelDuringLastStageCannotCompleteVideo(t *testing.T) {
	ctx := context.Background()
	videos, jobs := mocks.NewVideoRepoMem(), mocks.NewJobRepoMem()
	_ = videos.Create(ctx, &domain.Video{ID: "vid_cancel", Status: domain.VideoUploaded})
	job, _ := jobs.Create(ctx, "vid_cancel")
	ai := &mocks.AIClientMem{SummarizeFn: func(string, int) (*domain.SummaryResult, error) {
		_ = jobs.SetError(ctx, job.ID, "canceled_by_user")
		_ = jobs.SetStatus(ctx, job.ID, domain.JobFailed, false, true)
		return &domain.SummaryResult{Text: "late result"}, nil
	}}
	r := New(videos, jobs, mocks.NewAnalysisStoreMem(), mocks.NewSubtitleStoreMem(), ai, mocks.NewEventBusMem())
	if err := r.RunChain(ctx, job, preprocessed{VideoID: "vid_cancel", Duration: 8}); err == nil {
		t.Fatal("canceled final stage completed")
	}
	v, _ := videos.Get(ctx, "vid_cancel")
	j, _ := jobs.Get(ctx, job.ID)
	if v.Status != domain.VideoFailed || j.Status != domain.JobFailed || j.ErrorLog == nil || *j.ErrorLog != "canceled_by_user" {
		t.Fatalf("cancel overwritten: %+v %+v", v, j)
	}
	_ = videos.SoftDelete(ctx, "vid_cancel")
	_ = r.Fail(ctx, "vid_cancel", context.Canceled)
	v, _ = videos.Get(ctx, "vid_cancel")
	if v.Status != domain.VideoDeleted {
		t.Fatal("error handler revived deleted video")
	}
}
func TestProcessingProgressNeverMovesBackwards(t *testing.T) {
	previous := 0
	for _, stage := range StageOrder {
		progress := domain.StageProgress[stage]
		if progress < previous {
			t.Fatalf("stage %s decreased progress %d->%d", stage, previous, progress)
		}
		previous = progress
	}
}
