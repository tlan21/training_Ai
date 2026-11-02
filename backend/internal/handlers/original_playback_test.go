package handlers

import (
	"context"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/mocks"
)

func TestOriginalPlaybackOnlyForProcessedDetail(t *testing.T) {
	for _, status := range []domain.VideoStatus{domain.VideoUploaded, domain.VideoProcessing, domain.VideoProcessed, domain.VideoDeleted} {
		t.Run(string(status), func(t *testing.T) {
			videos := mocks.NewVideoRepoMem()
			_ = videos.Create(context.Background(), &domain.Video{ID: "vid_original", Status: status, RawFilePath: "raw-videos/original.mp4"})
			h := NewContentHandlers(videos, mocks.NewClipRepoMem(), mocks.NewCategoryRepoMem(), nil, nil, nil, nil, nil, mocks.NewObjectStorageMem())
			r := gin.New()
			r.GET("/videos/:id", h.GetVideo)
			w := httptest.NewRecorder()
			r.ServeHTTP(w, httptest.NewRequest("GET", "/videos/vid_original", nil))
			if status != domain.VideoProcessed {
				if w.Code != 404 || strings.Contains(w.Body.String(), "playback_url") {
					t.Fatalf("private video source leaked: %d %s", w.Code, w.Body)
				}
				return
			}
			if w.Code != 200 || !strings.Contains(w.Body.String(), `"playback_url":"https://storage.local/`) || strings.Contains(w.Body.String(), "raw_file_path") {
				t.Fatalf("bad original source: %d %s", w.Code, w.Body)
			}
		})
	}
}
