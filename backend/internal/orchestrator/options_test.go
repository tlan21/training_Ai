package orchestrator

import (
	"context"
	"fmt"
	"strings"
	"testing"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/mocks"
)

func TestProcessingSnapshotControlsActualCallsAndRetry(t *testing.T) {
	for _, highlight := range []bool{false, true} {
		for _, subtitles := range []bool{false, true} {
			t.Run(fmt.Sprintf("highlight_%t_subtitles_%t", highlight, subtitles), func(t *testing.T) {
				ctx := context.Background()
				videos, jobs, analysis, subs := mocks.NewVideoRepoMem(), mocks.NewJobRepoMem(), mocks.NewAnalysisStoreMem(), mocks.NewSubtitleStoreMem()
				_ = videos.Create(ctx, &domain.Video{ID: "vid_policy", Status: domain.VideoUploaded})
				job, _ := jobs.Create(ctx, "vid_policy")
				options := domain.ProcessingOptions{AutoHighlightEnabled: highlight, AutoSubtitleEnabled: subtitles}
				_ = jobs.SetProcessingOptions(ctx, job.ID, options)
				job, _ = jobs.Get(ctx, job.ID)
				calls := map[string]int{}
				ai := &mocks.AIClientMem{
					VisionFn: func([]string) (*domain.VisionResult, error) { calls["vision"]++; return &domain.VisionResult{}, nil },
					ASRFn: func(string, string) (*domain.ASRResult, error) {
						calls["asr"]++
						return &domain.ASRResult{FullTranscript: strings.Repeat("xin chào ", 10), Segments: []domain.Segment{{Text: "xin chào"}}}, nil // ≥ MinSummaryWords
					},
					HighlightFn: func(string, [][]float32, [][]float32) (*domain.HighlightResult, error) {
						calls["highlight"]++
						return &domain.HighlightResult{TimelineScores: []domain.SecondScore{{Second: 0, Score: 80}}, RecommendedClips: []domain.AIClip{{StartTime: 0, EndTime: 2}}}, nil
					},
					SummarizeFn: func(string, int) (*domain.SummaryResult, error) {
						calls["summary"]++
						return &domain.SummaryResult{Text: "bản nháp"}, nil
					},
				}
				r := New(videos, jobs, analysis, subs, ai, mocks.NewEventBusMem())
				for attempt := 1; attempt <= 2; attempt++ {
					if err := r.RunChain(ctx, job, preprocessed{VideoID: "vid_policy", Duration: 8}); err != nil {
						t.Fatal(err)
					}
					if calls["vision"] != attempt || calls["asr"] != boolCount(subtitles)*attempt || calls["summary"] != boolCount(subtitles)*attempt || calls["highlight"] != boolCount(highlight)*attempt {
						t.Fatalf("disabled model called: %+v", calls)
					}
					a, _ := analysis.Get(ctx, "vid_policy")
					s, _ := subs.Get(ctx, "vid_policy")
					stored, _ := jobs.Get(ctx, job.ID)
					v, _ := videos.Get(ctx, "vid_policy")
					if stored.Status != domain.JobCompleted || v.Status != domain.VideoProcessed || len(stored.SkippedStages) != len(options.SkippedStages()) {
						t.Fatalf("job state: %+v %+v", stored, v)
					}
					if !highlight && (len(a.AIClips) != 0 || len(a.TimelineScores) != 0) {
						t.Fatal("disabled highlight fabricated output")
					}
					if !subtitles && (s.FullTranscript != "" || len(s.Segments) != 0 || a.Summary == nil || *a.Summary != "") {
						t.Fatal("disabled ASR/summary retained output")
					}
				}
			})
		}
	}
}
func boolCount(value bool) int {
	if value {
		return 1
	}
	return 0
}
func TestCategoryRulesOverrideVisionWithoutChangingSourceMetadata(t *testing.T) {
	suggestion := "tin_tuc"
	cats := []domain.Category{{ID: "cat_news", Name: "Tin tức"}, {ID: "cat_tech", Name: "Công nghệ", Keywords: []string{"máy tính"}}}
	match := matchCategory(cats, &suggestion, "Tin về MÁY TÍNH", true, true)
	if match == nil || match.CategoryID != "cat_tech" || match.Source != "keyword" {
		t.Fatalf("keyword rule: %+v", match)
	}
	match = matchCategory(cats, &suggestion, "Tin về máy tính", true, false)
	if match == nil || match.CategoryID != "cat_news" || match.Source != "vision" {
		t.Fatalf("vision mapping: %+v", match)
	}
	if match := matchCategory(cats, &suggestion, "Tin về máy tính", false, false); match != nil {
		t.Fatalf("disabled rules: %+v", match)
	}
	unknown := "unmapped"
	if match := matchCategory(cats, &unknown, "", true, false); match != nil {
		t.Fatalf("invented category: %+v", match)
	}
}
