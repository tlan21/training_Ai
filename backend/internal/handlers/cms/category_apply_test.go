package cms

import (
	"context"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/mocks"
)

type alertsFake struct {
	ids  []string
	seen [2]int
}

func (f *alertsFake) Seen(context.Context, string) (int, int, *time.Time, error) {
	return f.seen[0], f.seen[1], nil, nil
}
func (f *alertsFake) MarkSeen(_ context.Context, _ string, a, b int) error {
	f.seen = [2]int{a, b}
	return nil
}
func (f *alertsFake) UncategorizedProcessed(context.Context) ([]string, error) { return f.ids, nil }

// INT-64: bulk apply uses the stored match, falls back to mapping the ViT class, and skips videos without a usable suggestion.
func TestApplyCategorySuggestions(t *testing.T) {
	ctx := context.Background()
	videos, analysis, cats := mocks.NewVideoRepoMem(), mocks.NewAnalysisStoreMem(), mocks.NewCategoryRepoMem()
	football, _ := cats.Create(ctx, "Bóng đá", nil, nil)
	news, _ := cats.Create(ctx, "Tin tức", nil, nil)
	for _, id := range []string{"vid_match", "vid_class", "vid_none", "vid_unknown"} {
		videos.M[id] = &domain.Video{ID: id, Status: domain.VideoProcessed}
	}
	bong, tin, other := "bong_da", "tin_tuc", "the_thao"
	_ = analysis.Put(ctx, "vid_match", nil, nil, &bong, nil)
	_ = analysis.SetCategoryMatch(ctx, "vid_match", &domain.CategoryMatch{CategoryID: football.ID, Name: "Bóng đá", Source: "vision"})
	_ = analysis.Put(ctx, "vid_class", nil, nil, &tin, nil)     // no stored match: mapped now
	_ = analysis.Put(ctx, "vid_unknown", nil, nil, &other, nil) // no "Thể thao" category in this fixture
	alerts := &alertsFake{ids: []string{"vid_match", "vid_class", "vid_none", "vid_unknown"}}
	r := gin.New()
	r.Use(func(c *gin.Context) { c.Set("user_id", "usr_admin") })
	h := NewCategoryApplyHandlers(alerts, videos, analysis, cats)
	r.POST("/apply", h.ApplySuggestions)
	r.PUT("/seen", h.PutSeen)
	r.GET("/seen", h.GetSeen)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest("POST", "/apply", nil))
	if w.Code != 200 || !strings.Contains(w.Body.String(), `"applied":2`) || !strings.Contains(w.Body.String(), `"skipped":2`) {
		t.Fatalf("apply: %d %s", w.Code, w.Body)
	}
	if *videos.M["vid_match"].CategoryID != football.ID || *videos.M["vid_class"].CategoryID != news.ID ||
		videos.M["vid_none"].CategoryID != nil || videos.M["vid_unknown"].CategoryID != nil {
		t.Fatalf("assignments wrong")
	}
	for _, body := range []string{`{}`, `{"failed_jobs":-1,"uncategorized_videos":0}`, `{"failed_jobs":1}`, `nope`} {
		w := httptest.NewRecorder()
		r.ServeHTTP(w, httptest.NewRequest("PUT", "/seen", strings.NewReader(body)))
		if w.Code != 422 {
			t.Fatalf("%s accepted: %d", body, w.Code)
		}
	}
	w = httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest("PUT", "/seen", strings.NewReader(`{"failed_jobs":3,"uncategorized_videos":0}`)))
	if w.Code != 204 || alerts.seen != [2]int{3, 0} {
		t.Fatalf("seen put: %d %v", w.Code, alerts.seen)
	}
	w = httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest("GET", "/seen", nil))
	if w.Code != 200 || !strings.Contains(w.Body.String(), `"failed_jobs":3`) {
		t.Fatalf("seen get: %d %s", w.Code, w.Body)
	}
}
