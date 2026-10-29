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
	h := NewVideoHandlers(videos, nil, nil, nil, unavailableFrames{mocks.NewVectorStoreMem()}, nil, nil, nil, nil, mocks.NewClipRepoMem())
	r := gin.New()
	r.DELETE("/api/cms/videos/:id", h.Delete)
	res := httptest.NewRecorder()
	r.ServeHTTP(res, httptest.NewRequest("DELETE", "/api/cms/videos/vid_retry", nil))
	if res.Code != 503 || !strings.Contains(res.Body.String(), "SERVICE_UNAVAILABLE") {
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

func TestDeleteCleansOwnedStoresAndCanBeRepeated(t *testing.T) {
	ctx := context.Background()
	videos, jobs, clips := mocks.NewVideoRepoMem(), mocks.NewJobRepoMem(), mocks.NewClipRepoMem()
	ana, subs, vec, storage := mocks.NewAnalysisStoreMem(), mocks.NewSubtitleStoreMem(), mocks.NewVectorStoreMem(), mocks.NewObjectStorageMem()
	_ = videos.Create(ctx, &domain.Video{ID: "vid_delete", Status: domain.VideoProcessed, RawFilePath: "raw-videos/vid_delete.mp4"})
	path := "clips/clips/clp_delete.mp4"
	_ = clips.Create(ctx, &domain.Clip{ID: "clp_delete", VideoID: "vid_delete", Status: domain.ClipPublished, ClipFilePath: &path})
	_ = ana.Put(ctx, "vid_delete", nil, nil, nil)
	_ = subs.Put(ctx, "vid_delete", "vi", "hello", nil)
	_ = vec.UpsertFrames(ctx, "vid_delete", nil)
	for _, key := range []string{"raw-videos/vid_delete.mp4", "raw-videos/audio/vid_delete.wav", "thumbnails/vid_delete/00000000.jpg", "clips/clips/clp_delete.mp4", "thumbnails/vid_other/00000000.jpg"} {
		storage.Objs[key] = []byte("owned")
	}
	h := NewVideoHandlers(videos, jobs, ana, subs, vec, mocks.NewCacheMem(), nil, storage, nil, clips)
	r := gin.New()
	r.DELETE("/:id", h.Delete)
	for range 2 {
		res := httptest.NewRecorder()
		r.ServeHTTP(res, httptest.NewRequest("DELETE", "/vid_delete", nil))
		if res.Code != 204 {
			t.Fatalf("delete %d %s", res.Code, res.Body)
		}
	}
	if len(storage.Objs) != 1 || storage.Objs["thumbnails/vid_other/00000000.jpg"] == nil {
		t.Fatal("wrong object scope", storage.Objs)
	}
	if _, err := ana.Get(ctx, "vid_delete"); err == nil {
		t.Fatal("analysis remains")
	}
	if _, err := subs.Get(ctx, "vid_delete"); err == nil {
		t.Fatal("subtitles remain")
	}
	if v, _ := videos.Get(ctx, "vid_delete"); v.Status != domain.VideoDeleted {
		t.Fatal(v)
	}
}

type failingPrefixStorage struct {
	*mocks.ObjectStorageMem
	fail bool
}

func (s *failingPrefixStorage) DeletePrefix(ctx context.Context, b, p string) error {
	if s.fail {
		return errors.New("MinIO unavailable")
	}
	return s.ObjectStorageMem.DeletePrefix(ctx, b, p)
}
func TestDeleteStorageFailureAndActiveJobAreRetryable(t *testing.T) {
	ctx := context.Background()
	videos, jobs, clips := mocks.NewVideoRepoMem(), mocks.NewJobRepoMem(), mocks.NewClipRepoMem()
	_ = videos.Create(ctx, &domain.Video{ID: "vid_retry", Status: domain.VideoProcessed})
	job, _ := jobs.Create(ctx, "vid_retry")
	storage := &failingPrefixStorage{ObjectStorageMem: mocks.NewObjectStorageMem(), fail: true}
	h := NewVideoHandlers(videos, jobs, mocks.NewAnalysisStoreMem(), mocks.NewSubtitleStoreMem(), mocks.NewVectorStoreMem(), nil, nil, storage, nil, clips)
	r := gin.New()
	r.DELETE("/:id", h.Delete)
	call := func() int {
		w := httptest.NewRecorder()
		r.ServeHTTP(w, httptest.NewRequest("DELETE", "/vid_retry", nil))
		return w.Code
	}
	if call() != 409 {
		t.Fatal("active writer allowed")
	}
	_ = jobs.SetStatus(ctx, job.ID, domain.JobCompleted, false, true)
	if call() != 503 {
		t.Fatal("storage failure swallowed")
	}
	if _, err := videos.GetProcessed(ctx, "vid_retry"); err != nil {
		t.Fatal("cleanup cannot be retried")
	}
	storage.fail = false
	if call() != 204 {
		t.Fatal("retry failed")
	}
}
