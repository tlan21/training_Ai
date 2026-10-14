package orchestrator

import (
	"context"
	"encoding/json"
	"errors"
	"testing"
	"time"

	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/mocks"
)

func TestRunner_RetrySuccessOnThird(t *testing.T) {
	videoRepo := mocks.NewVideoRepoMem()
	jobRepo := mocks.NewJobRepoMem()
	ana := mocks.NewAnalysisStoreMem()
	sub := mocks.NewSubtitleStoreMem()
	bus := mocks.NewEventBusMem()

	vid := &domain.Video{ID: "vid_1", RawFilePath: "raw-videos/vid_1.mp4", DurationSeconds: 0, Status: domain.VideoUploaded}
	_ = videoRepo.Create(context.Background(), vid)
	job, _ := jobRepo.Create(context.Background(), "vid_1")

	// fail vision twice, succeed 3rd
	calls := 0
	ai := &mocks.AIClientMem{
		VisionFn: func(paths []string) (*domain.VisionResult, error) {
			calls++
			if calls < 3 {
				return nil, errors.New("transient")
			}
			return &domain.VisionResult{CategorySuggestion: "cat_bongda", Embeddings256: [][]float32{{0.1}}}, nil
		},
		ASRFn: func(url, lang string) (*domain.ASRResult, error) {
			return &domain.ASRResult{FullTranscript: "hello", Segments: []domain.Segment{{Text: "hello"}}}, nil
		},
		HighlightFn: func(vid string, ve [][]float32, af [][]float32) (*domain.HighlightResult, error) {
			if len(ve) != 1 || ve[0][0] != 0.1 || len(af) != 1 || af[0][0] != 7 {
				t.Fatalf("lost per-video features: vision=%v audio=%v", ve, af)
			}
			return &domain.HighlightResult{TimelineScores: []domain.SecondScore{{Second: 0, Score: 80}}}, nil
		},
		SummarizeFn: func(p string, n int) (*domain.SummaryResult, error) {
			return &domain.SummaryResult{Text: "sum", Title: "t"}, nil
		},
	}

	r := New(videoRepo, jobRepo, ana, sub, ai, bus)
	r.WithSleep(func(time.Duration) {}) // no wait

	prep := preprocessed{VideoID: "vid_1", KeyframesPath: "k", AudioPath: "a", Duration: 60, AudioFeatures: [][]float32{{7}}}
	if err := r.RunChain(context.Background(), job, prep); err != nil {
		t.Fatalf("RunChain: %v", err)
	}
	if calls != 3 {
		t.Fatalf("want 3 vision calls got %d", calls)
	}
	j2, _ := jobRepo.Get(context.Background(), job.ID)
	if j2.Status != domain.JobCompleted || *j2.CurrentStage != domain.StageCompleted {
		t.Fatalf("want completed got %v %v", j2.Status, *j2.CurrentStage)
	}
	v2, _ := videoRepo.Get(context.Background(), "vid_1")
	if v2.Status != domain.VideoProcessed {
		t.Fatalf("want processed got %v", v2.Status)
	}
}

func TestRunner_FailPermanent(t *testing.T) {
	videoRepo := mocks.NewVideoRepoMem()
	jobRepo := mocks.NewJobRepoMem()
	ana := mocks.NewAnalysisStoreMem()
	sub := mocks.NewSubtitleStoreMem()
	bus := &captureBus{EventBusMem: mocks.NewEventBusMem()}

	_ = videoRepo.Create(context.Background(), &domain.Video{ID: "vid_1", RawFilePath: "raw-videos/vid_1.mp4", Status: domain.VideoUploaded})
	job, _ := jobRepo.Create(context.Background(), "vid_1")

	ai := &mocks.AIClientMem{
		VisionFn: func(s []string) (*domain.VisionResult, error) { return nil, errors.New("perm") },
	}
	r := New(videoRepo, jobRepo, ana, sub, ai, bus)
	r.WithSleep(func(time.Duration) {})

	prep := preprocessed{VideoID: "vid_1", KeyframesPath: "k", AudioPath: "a", Duration: 10}
	err := r.RunChain(context.Background(), job, prep)
	if err == nil {
		t.Fatal("want err")
	}
	j2, _ := jobRepo.Get(context.Background(), job.ID)
	if j2.Status != domain.JobFailed {
		t.Fatalf("want failed got %v", j2.Status)
	}
	if j2.ErrorLog == nil || *j2.ErrorLog == "" {
		t.Fatal("want error_log")
	}
	if len(bus.Events) == 0 {
		t.Fatal("want ai.stage.completed failed publish")
	}
}

func TestStateMachine_Order(t *testing.T) {
	if StageOrder[0] != domain.StageSplittingFrames {
		t.Fatal("first stage")
	}
	if StageOrder[len(StageOrder)-1] != domain.StageCompleted {
		t.Fatal("last stage")
	}
	nxt, ok := NextStage(domain.StageEmbedding)
	if !ok || nxt != domain.StageAsrExtracting {
		t.Fatalf("next %v %v", nxt, ok)
	}
}

func TestRunner_CompletedReplayDoesNotNeedRemovedArtifacts(t *testing.T) {
	videos := mocks.NewVideoRepoMem()
	jobs := mocks.NewJobRepoMem()
	job, _ := jobs.Create(context.Background(), "vid_done")
	_ = jobs.SetStatus(context.Background(), job.ID, domain.JobCompleted, false, true)
	runner := New(videos, jobs, mocks.NewAnalysisStoreMem(), mocks.NewSubtitleStoreMem(), &mocks.AIClientMem{}, mocks.NewEventBusMem())
	if err := runner.HandlePreprocessed(context.Background(), []byte(`{"video_id":"vid_done","duration":8,"keyframes_path":"already-removed"}`)); err != nil {
		t.Fatalf("completed replay failed: %v", err)
	}
}

// captureBus for assert publish
type captureBus struct{ *mocks.EventBusMem }

func (c *captureBus) Publish(ctx context.Context, topic, key string, payload any) error {
	raw, _ := json.Marshal(payload)
	c.Events = append(c.Events, struct {
		Topic string
		Key   string
		Raw   []byte
	}{Topic: topic, Key: key, Raw: raw})
	return nil
}
