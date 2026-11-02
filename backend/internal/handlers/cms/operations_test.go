package cms

import (
	"context"
	"encoding/json"
	"errors"
	"github.com/gin-gonic/gin"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
	"traning_ai/backend/internal/adapters/aihttp"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/mocks"
)

type metricsFixture struct {
	month time.Time
	fail  bool
}

func TestHealthAcceptsComputeOnlyInferenceWithoutStorageDependencies(t *testing.T) {
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/health" {
			t.Fatalf("unexpected inference path: %s", r.URL.Path)
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"status":"ok","models_loaded":["vit","siamese","asr_ctc","highlight_fusion","minigpt","two_tower"],"stub_mode":false,"dependencies":{},"device":"cpu"}`))
	}))
	defer upstream.Close()
	r := gin.New()
	r.GET("/health", NewSystemHandlers(aihttp.New(upstream.URL, "test"), nil).Health)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest("GET", "/health", nil))
	var response struct {
		Available bool     `json:"ai_available"`
		Error     *string  `json:"ai_error"`
		Models    []string `json:"models_loaded"`
	}
	if err := json.Unmarshal(w.Body.Bytes(), &response); err != nil || w.Code != 200 || !response.Available || response.Error != nil || len(response.Models) != 6 {
		t.Fatalf("compute-only inference rejected: %d %s (%v)", w.Code, w.Body, err)
	}
}

func (f *metricsFixture) Overview(_ context.Context, month time.Time) (*domain.CMSMetrics, error) {
	f.month = month
	if f.fail {
		return nil, errors.New("private database detail")
	}
	return &domain.CMSMetrics{TotalVideos: 17, DailyProcessing: []domain.DailyProcessing{}}, nil
}
func TestHealthKeepsRealCMSMetricsDuringAIOutage(t *testing.T) {
	metrics := &metricsFixture{}
	storage := mocks.NewObjectStorageMem()
	storage.Objs["thumbnails/vid_x/00000001.jpg"] = []byte{1, 2, 3}
	ai := &mocks.AIClientMem{HealthFn: func() (*domain.AIHealth, error) { return nil, errors.New("private upstream detail") }}
	h := NewSystemHandlers(ai, nil).WithOverview(metrics, storage, nil)
	r := gin.New()
	r.GET("/health", h.Health)
	for _, tc := range []struct {
		query  string
		status int
	}{{"?include_metrics=true&month=2026-10", 200}, {"?month=2026-13", 422}, {"?include_metrics=no", 422}} {
		w := httptest.NewRecorder()
		r.ServeHTTP(w, httptest.NewRequest("GET", "/health"+tc.query, nil))
		if w.Code != tc.status {
			t.Fatalf("%s: %d %s", tc.query, w.Code, w.Body)
		}
		if w.Code == 200 {
			var out struct {
				AIAvailable bool                `json:"ai_available"`
				Metrics     domain.CMSMetrics   `json:"metrics"`
				Storage     domain.StorageUsage `json:"storage"`
			}
			if json.Unmarshal(w.Body.Bytes(), &out) != nil || out.AIAvailable || out.Metrics.TotalVideos != 17 || out.Storage.TotalBytes != 3 || len(out.Storage.Buckets) != 3 || metrics.month.Month() != time.October || strings.Contains(w.Body.String(), "private") {
				t.Fatalf("dependency results: %s", w.Body)
			}
		}
	}
	metrics.fail = true
	w := httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest("GET", "/health?include_metrics=true", nil))
	if w.Code != 200 || !strings.Contains(w.Body.String(), `"metrics_error":"Unable to read CMS metrics"`) || strings.Contains(w.Body.String(), "private") {
		t.Fatalf("metric failure hidden: %d %s", w.Code, w.Body)
	}
}
func TestCPUCountersExcludeGuestDoubleCount(t *testing.T) {
	total, idle, err := cpuCounters("cpu 10 20 30 40 50 60 70 80 90 100\ncpu0 0")
	if err != nil || total != 360 || idle != 90 {
		t.Fatalf("%d %d %v", total, idle, err)
	}
	for _, bad := range []string{"", "cpu x 1 2 3", "cpu0 1 2 3 4"} {
		if _, _, err := cpuCounters(bad); err == nil {
			t.Fatalf("accepted %q", bad)
		}
	}
}
func TestCMSVideoFiltersAreGlobalAndDeletedExplicit(t *testing.T) {
	repo := mocks.NewVideoRepoMem()
	ctx := context.Background()
	date := time.Date(2026, 10, 2, 12, 0, 0, 0, time.UTC)
	for _, v := range []domain.Video{{ID: "vid_1", Title: "News", Status: domain.VideoProcessed, CreatedAt: date}, {ID: "vid_2", Title: "News", Status: domain.VideoDeleted, CreatedAt: date}, {ID: "vid_3", Title: "Other", Status: domain.VideoProcessed, CreatedAt: date.AddDate(0, 0, -2)}} {
		copy := v
		_ = repo.Create(ctx, &copy)
	}
	h := NewVideoHandlers(repo, nil, nil, nil, nil, nil, nil, nil, nil, nil)
	r := gin.New()
	r.GET("/videos", h.List)
	for _, tc := range []struct {
		query         string
		total, status int
	}{{"?q=News&date_from=2026-10-02&date_to=2026-10-02", 1, 200}, {"?status=deleted", 1, 200}, {"?include_deleted=true", 3, 200}, {"?date_from=2026-10-03&date_to=2026-10-02", 0, 422}, {"?date_from=bad", 0, 422}, {"?status=unknown", 0, 422}} {
		w := httptest.NewRecorder()
		r.ServeHTTP(w, httptest.NewRequest("GET", "/videos"+tc.query, nil))
		if w.Code != tc.status {
			t.Fatalf("%s: %d %s", tc.query, w.Code, w.Body)
		}
		if tc.status == 200 {
			var out struct {
				Total int `json:"total"`
			}
			_ = json.Unmarshal(w.Body.Bytes(), &out)
			if out.Total != tc.total {
				t.Fatalf("%s: %s", tc.query, w.Body)
			}
		}
	}
}

type summaryFailure struct{ *mocks.AnalysisStoreMem }

func (s summaryFailure) SetSummary(context.Context, string, string, string) error {
	return errors.New("private database failure")
}
func TestEditorialWritesValidateSourceAndReportFailures(t *testing.T) {
	ctx := context.Background()
	videos, analysis, subs := mocks.NewVideoRepoMem(), mocks.NewAnalysisStoreMem(), mocks.NewSubtitleStoreMem()
	_ = videos.Create(ctx, &domain.Video{ID: "vid_editorial", Status: domain.VideoProcessed, DurationSeconds: 8})
	_ = analysis.SetSummary(ctx, "vid_editorial", "reviewed text", "draft")
	_ = subs.Put(ctx, "vid_editorial", "vi", "old text", nil)
	h := NewVideoHandlers(videos, nil, analysis, subs, nil, nil, nil, nil, &mocks.AIClientMem{}, nil)
	r := gin.New()
	r.PUT("/videos/:id/summary", h.SetSummary)
	r.PUT("/videos/:id/subtitles", h.UpdateSubtitles)
	r.POST("/videos/:id/regenerate", h.RegenerateSummary)
	call := func(method, path, body string, status int) {
		t.Helper()
		w := httptest.NewRecorder()
		r.ServeHTTP(w, httptest.NewRequest(method, path, strings.NewReader(body)))
		if w.Code != status || strings.Contains(w.Body.String(), "private") {
			t.Fatalf("%s: %d %s", path, w.Code, w.Body)
		}
	}
	call("PUT", "/videos/vid_missing/summary", `{"summary":"orphan"}`, 404)
	if _, err := analysis.Get(ctx, "vid_missing"); err == nil {
		t.Fatal("created orphan analysis")
	}
	call("PUT", "/videos/vid_editorial/subtitles", `{"segments":[{"segment_index":0,"start_time":0,"end_time":2,"text":"new text","confidence":0.9}]}`, 200)
	stored, _ := subs.Get(ctx, "vid_editorial")
	if stored.FullTranscript != "new text" {
		t.Fatalf("regeneration transcript stale: %+v", stored)
	}
	for _, body := range []string{`{"segments":[{"start_time":-1,"end_time":2}]}`, `{"segments":[{"start_time":0,"end_time":9}]}`, `{"segments":[{"start_time":0,"end_time":0}]}`} {
		call("PUT", "/videos/vid_editorial/subtitles", body, 422)
	}
	failed := NewVideoHandlers(videos, nil, summaryFailure{analysis}, subs, nil, nil, nil, nil, nil, nil)
	r.PUT("/failed/:id/summary", failed.SetSummary)
	r.POST("/failed/:id/approve", failed.ApproveSummary)
	call("PUT", "/failed/vid_editorial/summary", `{"summary":"not saved"}`, 500)
	call("POST", "/failed/vid_editorial/approve", `{}`, 500)
	_ = subs.UpdateSegments(ctx, "vid_editorial", []domain.Segment{})
	call("POST", "/videos/vid_editorial/regenerate", `{}`, 422)
}
