package cms

import (
	"context"
	"encoding/json"
	"github.com/gin-gonic/gin"
	"net/http/httptest"
	"strings"
	"testing"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/mocks"
)

func TestCreateClip_AveragesActualScoresForFractionalRange(t *testing.T) {
	gin.SetMode(gin.TestMode)
	videos := mocks.NewVideoRepoMem()
	analyses := mocks.NewAnalysisStoreMem()
	_ = videos.Create(context.Background(), &domain.Video{ID: "vid_score", Status: domain.VideoProcessed, DurationSeconds: 2})
	_ = analyses.Put(context.Background(), "vid_score", []domain.SecondScore{{Second: 0, Score: 80}, {Second: 1, Score: 90}}, nil, nil)
	handler := NewClipHandlers(mocks.NewClipRepoMem(), videos, mocks.NewEventBusMem(), mocks.NewCacheMem(), analyses, mocks.NewObjectStorageMem())
	router := gin.New()
	router.POST("/api/cms/clips", handler.Create)
	request := httptest.NewRequest("POST", "/api/cms/clips", strings.NewReader(`{"video_id":"vid_score","title":"test","start_time":0.5,"end_time":1.5}`))
	request.Header.Set("Content-Type", "application/json")
	recorder := httptest.NewRecorder()
	router.ServeHTTP(recorder, request)
	var result struct {
		AverageScore float64 `json:"average_score"`
		ThumbnailURL string  `json:"thumbnail_url"`
	}
	_ = json.Unmarshal(recorder.Body.Bytes(), &result)
	if recorder.Code != 201 || result.AverageScore != 85 || result.ThumbnailURL != "https://storage.local/vid_score/00000000.jpg" {
		t.Fatalf("wrong actual clip score: %d %s", recorder.Code, recorder.Body.String())
	}
}

func TestCreateCompilation_StoredAIAndEmpty(t *testing.T) {
	gin.SetMode(gin.TestMode)
	ctx := context.Background()
	videos, analyses, clips := mocks.NewVideoRepoMem(), mocks.NewAnalysisStoreMem(), mocks.NewClipRepoMem()
	_ = videos.Create(ctx, &domain.Video{ID: "vid_comp", Status: domain.VideoProcessed, DurationSeconds: 10})
	_ = analyses.Put(ctx, "vid_comp", []domain.SecondScore{{Second: 1, Score: 80}, {Second: 2, Score: 90}, {Second: 8, Score: 60}}, []domain.AIClip{{StartTime: 8, EndTime: 9}, {StartTime: 1, EndTime: 3}, {StartTime: 2, EndTime: 3}}, nil)
	h := NewClipHandlers(clips, videos, mocks.NewEventBusMem(), mocks.NewCacheMem(), analyses, mocks.NewObjectStorageMem())
	r := gin.New()
	r.POST("/clips", h.Create)
	send := func(body string) *httptest.ResponseRecorder {
		req := httptest.NewRequest("POST", "/clips", strings.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		r.ServeHTTP(w, req)
		return w
	}
	w := send(`{"video_id":"vid_comp","title":"combined","auto_highlights":true}`)
	var result domain.Clip
	_ = json.Unmarshal(w.Body.Bytes(), &result)
	if w.Code != 201 || result.StartTime != 0 || result.EndTime != 3 || len(result.SourceSegments) != 2 || result.AverageScore != 76.67 || result.Status != domain.ClipProcessing {
		t.Fatalf("%d %s", w.Code, w.Body.String())
	}
	stored, _ := clips.Get(ctx, result.ID)
	if len(stored.SourceSegments) != 2 || stored.SourceSegments[0].StartTime != 1 {
		t.Fatal("source mapping lost")
	}
	_ = analyses.Put(ctx, "vid_comp", nil, nil, nil)
	if w := send(`{"video_id":"vid_comp","title":"empty","auto_highlights":true}`); w.Code != 422 {
		t.Fatalf("empty %d", w.Code)
	}
	if w := send(`{"video_id":"vid_comp","title":"missing"}`); w.Code != 422 {
		t.Fatalf("missing %d", w.Code)
	}
}
