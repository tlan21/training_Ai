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
	handler := NewClipHandlers(mocks.NewClipRepoMem(), videos, mocks.NewEventBusMem(), mocks.NewCacheMem(), analyses)
	router := gin.New()
	router.POST("/api/cms/clips", handler.Create)
	request := httptest.NewRequest("POST", "/api/cms/clips", strings.NewReader(`{"video_id":"vid_score","title":"test","start_time":0.5,"end_time":1.5}`))
	request.Header.Set("Content-Type", "application/json")
	recorder := httptest.NewRecorder()
	router.ServeHTTP(recorder, request)
	var result struct {
		AverageScore float64 `json:"average_score"`
	}
	_ = json.Unmarshal(recorder.Body.Bytes(), &result)
	if recorder.Code != 201 || result.AverageScore != 85 {
		t.Fatalf("wrong actual clip score: %d %s", recorder.Code, recorder.Body.String())
	}
}
