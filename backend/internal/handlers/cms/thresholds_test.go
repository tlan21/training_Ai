package cms

import (
	"context"
	"encoding/json"
	"github.com/gin-gonic/gin"
	"net/http/httptest"
	"testing"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/mocks"
)

func TestCMSAnalysisReportedThresholdAndLegacyUnknown(t *testing.T) {
	gin.SetMode(gin.TestMode)
	ctx := context.Background()
	videos, analysis := mocks.NewVideoRepoMem(), mocks.NewAnalysisStoreMem()
	_ = videos.Create(ctx, &domain.Video{ID: "vid_threshold", Status: domain.VideoProcessed})
	h := NewVideoHandlers(videos, nil, analysis, nil, nil, nil, nil, nil, nil, nil)
	r := gin.New()
	r.GET("/analysis/:id", h.GetAnalysis)
	threshold := 51.0
	for _, value := range []*float64{&threshold, new(float64), nil} {
		_ = analysis.Put(ctx, "vid_threshold", nil, nil, nil, value)
		w := httptest.NewRecorder()
		r.ServeHTTP(w, httptest.NewRequest("GET", "/analysis/vid_threshold", nil))
		var body map[string]json.RawMessage
		_ = json.Unmarshal(w.Body.Bytes(), &body)
		var got *float64
		_ = json.Unmarshal(body["clip_threshold"], &got)
		if w.Code != 200 || body["clip_threshold"] == nil || (got == nil) != (value == nil) {
			t.Fatalf("%d %s", w.Code, w.Body)
		}
		if value != nil && *got != *value {
			t.Fatalf("reported threshold changed: %s", w.Body)
		}
	}
}
