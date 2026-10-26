package cms

import (
	"context"
	"errors"
	"github.com/gin-gonic/gin"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/mocks"
)

type unavailableFrames struct{ *mocks.VectorStoreMem }

func (v unavailableFrames) DeleteFrames(context.Context, string) error {
	return errors.New("Milvus unavailable")
}

func TestDeleteKeepsVideoRetryableWhenVectorCleanupFails(t *testing.T) {
	gin.SetMode(gin.TestMode)
	videos := mocks.NewVideoRepoMem()
	_ = videos.Create(context.Background(), &domain.Video{ID: "vid_retry", Status: domain.VideoProcessed})
	h := NewVideoHandlers(videos, nil, nil, nil, unavailableFrames{mocks.NewVectorStoreMem()}, nil, nil, nil, nil, nil)
	r := gin.New()
	r.DELETE("/api/cms/videos/:id", h.Delete)
	res := httptest.NewRecorder()
	r.ServeHTTP(res, httptest.NewRequest("DELETE", "/api/cms/videos/vid_retry", nil))
	if res.Code != 503 || !strings.Contains(res.Body.String(), "AI_UNAVAILABLE") {
		t.Fatalf("%d %s", res.Code, res.Body)
	}
	if _, err := videos.GetProcessed(context.Background(), "vid_retry"); err != nil {
		t.Fatalf("delete cannot be retried: %v", err)
	}
}

func TestUpload_RejectsOversizedDeclaredBodyBeforeReading(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	handler := NewVideoHandlers(nil, nil, nil, nil, nil, nil, nil, nil, nil, nil)
	router.POST("/api/cms/videos", handler.Create)
	request := httptest.NewRequest(http.MethodPost, "/api/cms/videos", strings.NewReader("unused"))
	request.ContentLength = 2*1024*1024*1024 + 2*1024*1024
	recorder := httptest.NewRecorder()
	router.ServeHTTP(recorder, request)
	if recorder.Code != 413 || !strings.Contains(recorder.Body.String(), "PAYLOAD_TOO_LARGE") {
		t.Fatalf("unexpected response: %d %s", recorder.Code, recorder.Body.String())
	}
}

func TestCMSOriginalPlaybackExcludesDeletedVideo(t *testing.T) {
	for _, status := range []domain.VideoStatus{domain.VideoUploaded, domain.VideoProcessed, domain.VideoDeleted} {
		videos := mocks.NewVideoRepoMem()
		_ = videos.Create(context.Background(), &domain.Video{ID: "vid_original", Status: status, RawFilePath: "raw-videos/original.mp4"})
		h := NewVideoHandlers(videos, nil, nil, nil, nil, nil, nil, mocks.NewObjectStorageMem(), nil, nil)
		r := gin.New()
		r.GET("/videos/:id", h.Get)
		w := httptest.NewRecorder()
		r.ServeHTTP(w, httptest.NewRequest("GET", "/videos/vid_original", nil))
		if w.Code != 200 || strings.Contains(w.Body.String(), "raw_file_path") {
			t.Fatalf("bad CMS detail: %d %s", w.Code, w.Body)
		}
		if status == domain.VideoDeleted {
			if !strings.Contains(w.Body.String(), `"playback_url":null`) {
				t.Fatalf("deleted source issued: %s", w.Body)
			}
		} else if !strings.Contains(w.Body.String(), `"playback_url":"https://storage.local/`) {
			t.Fatalf("CMS source missing: %s", w.Body)
		}
	}
}
