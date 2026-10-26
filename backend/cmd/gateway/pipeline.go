package main

import (
	"context"
	"encoding/json"
	"log"
	"os"
	"path/filepath"
	"strings"
	"time"

	"traning_ai/backend/internal/cutter"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/orchestrator"
	"traning_ai/backend/internal/ports"
)

// Run Go consumers in the gateway process; repositories/events/files are shared persistent adapters.
func wirePipeline(videos ports.VideoRepository, jobs ports.JobRepository, clips ports.ClipRepository, analyses ports.AnalysisStore, subs ports.SubtitleStore, ai ports.AIClient, bus ports.EventBus, storage ports.ObjectStorage) {
	runner := orchestrator.New(videos, jobs, analyses, subs, ai, bus)
	cut := cutter.New(clips, videos, storage, bus, "raw-videos", "clips")
	consume := func(topic, group string, handler func(context.Context, []byte) error) {
		go func() {
			for {
				err := bus.Consume(context.Background(), topic, group, func(_ context.Context, payload []byte) error {
					ctx, cancel := context.WithTimeout(context.Background(), 2*time.Hour)
					defer cancel()
					if err := handler(ctx, payload); err != nil {
						log.Printf("%s: %v", topic, err)
					}
					return nil // Processing failures live in jobs; retry is an explicit CMS action.
				})
				log.Printf("consumer %s disconnected: %v", topic, err)
				time.Sleep(2 * time.Second)
			}
		}()
	}
	consume("video.uploaded", "gateway-uploaded", runner.HandleUploaded)
	consume("video.preprocessed", "gateway-preprocessed", func(ctx context.Context, payload []byte) error {
		var prep struct {
			VideoID       string  `json:"video_id"`
			KeyframesPath string  `json:"keyframes_path"`
			AudioPath     string  `json:"audio_path"`
			Duration      float64 `json:"duration"`
		}
		if err := json.Unmarshal(payload, &prep); err != nil {
			return err
		}
		// Only ingest-owned directories may be read/removed, never an event-provided arbitrary path.
		expected := filepath.Join("/srv/work", prep.VideoID)
		if !strings.HasPrefix(prep.VideoID, "vid_") || strings.ContainsAny(prep.VideoID, "/\\") || prep.KeyframesPath != expected {
			return domain.ErrValidation
		}
		defer os.RemoveAll(expected)
		var err error
		if prep.Duration > 0 {
			key := "audio/" + prep.VideoID + ".wav"
			defer func() {
				cleanup, cancel := context.WithTimeout(context.Background(), 10*time.Second)
				defer cancel()
				if err := storage.Delete(cleanup, "raw-videos", key); err != nil {
					log.Printf("audio cleanup %s: %v", prep.VideoID, err)
				}
			}()
			prep.AudioPath, err = uploadAIAudio(ctx, storage, filepath.Join(expected, "audio.wav"), key)
			if err == nil {
				payload, err = json.Marshal(prep)
			}
		}
		if err == nil {
			err = runner.HandlePreprocessed(ctx, payload)
		}
		if err != nil {
			if job, getErr := jobs.GetByVideo(ctx, prep.VideoID); getErr == nil {
				if job.ErrorLog == nil || *job.ErrorLog != "canceled_by_user" {
					_ = jobs.SetError(ctx, job.ID, err.Error())
					_ = jobs.SetStatus(ctx, job.ID, domain.JobFailed, false, false)
				}
			}
		}
		return err
	})
	consume("clip.cut.requested", "gateway-cutter", cut.HandleOne)
}
