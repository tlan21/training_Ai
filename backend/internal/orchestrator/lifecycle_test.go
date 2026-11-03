package orchestrator

import (
	"context"
	"strings"
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
	ai := &mocks.AIClientMem{ASRFn: func(string, string) (*domain.ASRResult, error) {
		return &domain.ASRResult{FullTranscript: strings.Repeat("lời thoại ", 10), Segments: []domain.Segment{{Text: "lời thoại"}}}, nil
	}, SummarizeFn: func(string, int) (*domain.SummaryResult, error) {
		_ = jobs.RequestCancel(ctx, job.ID)
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

func TestQueuedCancellationIsAcknowledgedWithoutStartingAI(t *testing.T) {
	ctx := context.Background()
	videos, jobs := mocks.NewVideoRepoMem(), mocks.NewJobRepoMem()
	_ = videos.Create(ctx, &domain.Video{ID: "vid_queued_cancel", Status: domain.VideoUploaded})
	job, _ := jobs.Create(ctx, "vid_queued_cancel")
	_ = jobs.RequestCancel(ctx, job.ID)
	r := New(videos, jobs, mocks.NewAnalysisStoreMem(), mocks.NewSubtitleStoreMem(), &mocks.AIClientMem{}, mocks.NewEventBusMem())
	if err := r.HandleUploaded(ctx, []byte(`{"video_id":"vid_queued_cancel"}`)); err == nil {
		t.Fatal("queued cancellation not handled")
	}
	j, _ := jobs.Get(ctx, job.ID)
	v, _ := videos.Get(ctx, job.VideoID)
	if j.Status != domain.JobFailed || v.Status != domain.VideoFailed || j.CompletedAt == nil {
		t.Fatalf("cancellation acknowledgement: %+v %+v", j, v)
	}
}
