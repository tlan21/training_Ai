package cms

import (
	"context"
	"encoding/json"
	"github.com/gin-gonic/gin"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/mocks"
)

func TestCMSVideoListResolvesProcessedThumbnailAndKeepsDeletedPlaceholder(t *testing.T) {
	ctx := context.Background()
	videos := mocks.NewVideoRepoMem()
	for _, v := range []domain.Video{{ID: "vid_active", Status: domain.VideoProcessed, CreatedAt: time.Now()}, {ID: "vid_deleted", Status: domain.VideoDeleted, CreatedAt: time.Now()}} {
		_ = videos.Create(ctx, &v)
	}
	h := NewVideoHandlers(videos, nil, nil, nil, nil, nil, nil, mocks.NewObjectStorageMem(), nil, nil)
	r := gin.New()
	r.GET("/videos", h.List)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest(http.MethodGet, "/videos", nil))
	if w.Code != 200 {
		t.Fatal(w.Code)
	}
	var result struct {
		Items []struct {
			ID        string  `json:"id"`
			Thumbnail *string `json:"thumbnail_url"`
		} `json:"items"`
	}
	if err := json.Unmarshal(w.Body.Bytes(), &result); err != nil {
		t.Fatal(err)
	}
	for _, v := range result.Items {
		if v.ID == "vid_active" && (v.Thumbnail == nil || !strings.Contains(*v.Thumbnail, "vid_active/00000000.jpg")) {
			t.Fatal("missing processed thumbnail", w.Body)
		}
		if v.ID == "vid_deleted" && v.Thumbnail != nil {
			t.Fatal("deleted thumbnail exposed")
		}
	}
}
