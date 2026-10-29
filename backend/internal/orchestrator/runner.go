package orchestrator

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"math"
	"math/rand"
	"os"
	"path/filepath"
	"strings"
	"time"

	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/ports"
)

// payloads (§4a, §2.5)
type preprocessed struct {
	VideoID       string      `json:"video_id"`
	KeyframesPath string      `json:"keyframes_path"`
	AudioPath     string      `json:"audio_path"`
	Duration      float64     `json:"duration"`
	Width         *int        `json:"width"`
	Height        *int        `json:"height"`
	FPS           *float64    `json:"fps"`
	AudioFeatures [][]float32 `json:"-"`
}

type stageDone struct {
	VideoID string `json:"video_id"`
	Stage   string `json:"stage"`
	Ok      bool   `json:"ok"`
	Error   string `json:"error,omitempty"`
}

// Runner chain 5 stage (Go, 1 goroutine/video — §5).
type Runner struct {
	storage  ports.ObjectStorage
	vectors  ports.VectorStore
	videos   ports.VideoRepository
	jobs     ports.JobRepository
	analysis ports.AnalysisStore
	subs     ports.SubtitleStore
	ai       ports.AIClient
	bus      ports.EventBus
	// sleep allows test to skip backoff
	sleep func(time.Duration)
}

func New(videos ports.VideoRepository, jobs ports.JobRepository, analysis ports.AnalysisStore, subs ports.SubtitleStore, ai ports.AIClient, bus ports.EventBus) *Runner {
	return &Runner{videos: videos, jobs: jobs, analysis: analysis, subs: subs, ai: ai, bus: bus, sleep: time.Sleep}
}

func (r *Runner) WithStorage(storage ports.ObjectStorage, vectors ports.VectorStore) {
	r.storage = storage
	r.vectors = vectors
}

func (r *Runner) WithSleep(fn func(time.Duration)) { r.sleep = fn }

// HandleUploaded: consume video.uploaded → job running + splitting_frames (ingest Python làm tiếp).
func (r *Runner) HandleUploaded(ctx context.Context, payload []byte) error {
	var p struct {
		VideoID string `json:"video_id"`
	}
	if err := json.Unmarshal(payload, &p); err != nil {
		return err
	}
	job, err := r.jobs.GetByVideo(ctx, p.VideoID)
	if err != nil {
		return err
	}
	if job.Status != domain.JobPending {
		return nil
	}
	if err := r.jobs.SetStatus(ctx, job.ID, domain.JobRunning, true, false); err != nil {
		return err
	}
	return r.jobs.SetStage(ctx, job.ID, domain.StageSplittingFrames)
}

// HandlePreprocessed: consume video.preprocessed → source metadata → RunChain.
func (r *Runner) HandlePreprocessed(ctx context.Context, payload []byte) error {
	var p preprocessed
	if err := json.Unmarshal(payload, &p); err != nil {
		return err
	}
	job, err := r.jobs.GetByVideo(ctx, p.VideoID)
	if err != nil {
		return err
	}
	if job.Status == domain.JobCompleted || (job.ErrorLog != nil && *job.ErrorLog == "canceled_by_user") {
		return nil
	}
	if p.Duration <= 0 || math.IsNaN(p.Duration) || math.IsInf(p.Duration, 0) || (p.Width != nil && *p.Width <= 0) || (p.Height != nil && *p.Height <= 0) || (p.FPS != nil && (*p.FPS <= 0 || math.IsNaN(*p.FPS) || math.IsInf(*p.FPS, 0))) {
		message, _ := os.ReadFile(filepath.Join(p.KeyframesPath, "error.txt"))
		err := fmt.Errorf("preprocess: invalid video: %s", message)
		_ = r.jobs.SetError(ctx, job.ID, err.Error())
		_ = r.jobs.SetStatus(ctx, job.ID, domain.JobFailed, false, false)
		return err
	}
	data, err := os.ReadFile(filepath.Join(p.KeyframesPath, "audio_features.json"))
	if err != nil {
		return err
	}
	if err := json.Unmarshal(data, &p.AudioFeatures); err != nil {
		return err
	}
	if err := r.videos.SetMediaMetadata(ctx, p.VideoID, p.Duration, p.Width, p.Height, p.FPS); err != nil {
		return err
	}
	return r.RunChain(ctx, job, p)
}

// RunChain chạy tuần tự embedding→asr→highlight→summarizing (mỗi stage retry 3, backoff 2s/4s/8s).
func (r *Runner) RunChain(ctx context.Context, job *domain.ProcessingJob, prep preprocessed) error {
	// ensure video is processing
	if err := r.videos.SetStatus(ctx, prep.VideoID, domain.VideoProcessing); err != nil {
		return err
	}
	if err := r.jobs.SetStatus(ctx, job.ID, domain.JobRunning, true, false); err != nil {
		return err
	}
	var visionEmb [][]float32

	stages := []struct {
		stage domain.Stage
		name  string
		fn    func(ctx context.Context) error
	}{
		{domain.StageEmbedding, "vision", func(ctx context.Context) error {
			var err error
			visionEmb, err = r.doVision(ctx, prep.VideoID, prep.KeyframesPath)
			return err
		}},
		{domain.StageAsrExtracting, "asr", func(ctx context.Context) error { return r.doASR(ctx, prep.VideoID, prep.AudioPath) }},
		{domain.StageHighlightScoring, "highlight", func(ctx context.Context) error {
			return r.doHighlight(ctx, prep.VideoID, visionEmb, prep.AudioFeatures, prep.Duration)
		}},
		{domain.StageSummarizing, "summary", func(ctx context.Context) error { return r.doSummary(ctx, prep.VideoID) }},
	}

	for _, st := range stages {
		current, err := r.jobs.Get(ctx, job.ID)
		if err != nil {
			return err
		}
		if current.ErrorLog != nil && *current.ErrorLog == "canceled_by_user" {
			return context.Canceled
		}
		if err := r.jobs.SetStage(ctx, job.ID, st.stage); err != nil {
			return err
		}
		if err := r.retry(ctx, string(st.stage), st.fn); err != nil {
			msg := fmt.Sprintf("stage=%s: %v", st.stage, err)
			_ = r.jobs.SetError(ctx, job.ID, msg)
			_ = r.jobs.SetStatus(ctx, job.ID, domain.JobFailed, false, false)
			_ = r.bus.Publish(ctx, "ai.stage.completed", prep.VideoID, stageDone{VideoID: prep.VideoID, Stage: st.name, Ok: false, Error: err.Error()})
			return err
		}
		_ = r.bus.Publish(ctx, "ai.stage.completed", prep.VideoID, stageDone{VideoID: prep.VideoID, Stage: st.name, Ok: true})
	}

	if err := r.videos.SetStatus(ctx, prep.VideoID, domain.VideoProcessed); err != nil {
		return err
	}
	if err := r.jobs.SetStage(ctx, job.ID, domain.StageCompleted); err != nil {
		return err
	}
	return r.jobs.SetStatus(ctx, job.ID, domain.JobCompleted, false, true)
}

func (r *Runner) retry(ctx context.Context, stage string, fn func(context.Context) error) error {
	backoffs := []time.Duration{2 * time.Second, 4 * time.Second, 8 * time.Second}
	var last error
	for attempt := 0; attempt < 3; attempt++ {
		if err := fn(ctx); err == nil {
			return nil
		} else {
			last = err
			var de *domain.DomainError
			if errors.As(err, &de) && de.Status >= 400 && de.Status < 500 {
				return err
			}
			// only retry transient (5xx/timeout); for mem/mocks all errors retry — simple
			if attempt < 2 {
				jitter := time.Duration(rand.Int63n(int64(500 * time.Millisecond)))
				d := backoffs[attempt] + jitter
				// ceil jitter via math to avoid import drift — use float
				_ = math.Max(1, float64(d))
				select {
				case <-ctx.Done():
					return ctx.Err()
				default:
				}
				r.sleep(d)
			}
		}
		_ = stage // keep for error_log
	}
	return last
}

func (r *Runner) doVision(ctx context.Context, videoID, keyframesPath string) ([][]float32, error) {
	var res *domain.VisionResult
	var err error
	if r.storage != nil && r.vectors != nil {
		res, err = IndexVideoFrames(ctx, r.ai, r.storage, r.vectors, videoID, keyframesPath)
	} else {
		res, err = r.ai.VisionV2(ctx, []string{keyframesPath})
	}
	if err != nil {
		return nil, err
	}
	cat := res.CategorySuggestion
	var catPtr *string
	if cat != "" {
		catPtr = &cat
	}
	// store category suggestion + empty scores (highlight will fill)
	if err := r.analysis.Put(ctx, videoID, nil, nil, catPtr); err != nil {
		return nil, err
	}
	// Fusion still consumes the 256-d features; backend persists the separate Siamese vectors.
	return res.Embeddings256, nil
}

func (r *Runner) doASR(ctx context.Context, videoID, audioPath string) error {
	if r.storage != nil {
		if !strings.HasPrefix(audioPath, "raw-videos/audio/"+videoID+".") {
			return domain.ErrValidation
		}
		object, err := r.storage.GetObject(ctx, "raw-videos", strings.TrimPrefix(audioPath, "raw-videos/"))
		if err != nil {
			return err
		}
		defer object.Close()
		file, err := os.CreateTemp("", "asr-source-*.wav")
		if err != nil {
			return err
		}
		defer os.Remove(file.Name())
		_, copyErr := io.Copy(file, object)
		closeErr := file.Close()
		if copyErr != nil {
			return copyErr
		}
		if closeErr != nil {
			return closeErr
		}
		audioPath = file.Name()
	}
	res, err := r.ai.ASRV2(ctx, audioPath, "vi")
	if err != nil {
		return err
	}
	return r.subs.Put(ctx, videoID, "vi", res.FullTranscript, res.Segments)
}

func (r *Runner) doHighlight(ctx context.Context, videoID string, vision, audio [][]float32, duration float64) error {
	res, err := r.ai.Highlight(ctx, videoID, vision, audio)
	if err != nil {
		return err
	}
	for i := range res.RecommendedClips {
		res.RecommendedClips[i].EndTime = math.Min(res.RecommendedClips[i].EndTime, duration)
	}
	var cat *string
	if a, err2 := r.analysis.Get(ctx, videoID); err2 == nil {
		cat = a.CategorySuggestion
	}
	return r.analysis.Put(ctx, videoID, res.TimelineScores, res.RecommendedClips, cat)
}

func (r *Runner) doSummary(ctx context.Context, videoID string) error {
	sub, err := r.subs.Get(ctx, videoID)
	if err != nil {
		return err
	}
	res, err := r.ai.Summarize(ctx, sub.FullTranscript, 256)
	if err != nil {
		return err
	}
	return r.analysis.SetSummary(ctx, videoID, res.Text, "draft")
}
