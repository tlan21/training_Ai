package handlers

import (
	"bytes"
	"context"
	"github.com/gin-gonic/gin"
	"image"
	"image/png"
	"mime/multipart"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/mocks"
)

func searchImage(t *testing.T) []byte {
	t.Helper()
	var data bytes.Buffer
	if err := png.Encode(&data, image.NewRGBA(image.Rect(0, 0, 3, 3))); err != nil {
		t.Fatal(err)
	}
	return data.Bytes()
}

func visualRequest(t *testing.T, router *gin.Engine, data []byte, threshold string) *httptest.ResponseRecorder {
	t.Helper()
	var body bytes.Buffer
	w := multipart.NewWriter(&body)
	f, err := w.CreateFormFile("image", "query.png")
	if err != nil {
		t.Fatal(err)
	}
	if _, err := f.Write(data); err != nil {
		t.Fatal(err)
	}
	if err := w.WriteField("min_similarity", threshold); err != nil {
		t.Fatal(err)
	}
	if err := w.Close(); err != nil {
		t.Fatal(err)
	}
	req := httptest.NewRequest(http.MethodPost, "/api/search/visual", &body)
	req.Header.Set("Content-Type", w.FormDataContentType())
	res := httptest.NewRecorder()
	router.ServeHTTP(res, req)
	return res
}

func TestVisualValidationBeforeAI(t *testing.T) {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.POST("/api/search/visual", NewSearchHandlers(nil, nil, nil, nil, nil, nil, nil).Visual)
	for _, threshold := range []string{"-0.1", "1.01", "NaN", "+Inf", "abc"} {
		t.Run(threshold, func(t *testing.T) {
			res := visualRequest(t, r, searchImage(t), threshold)
			if res.Code != 422 || !strings.Contains(res.Body.String(), "VALIDATION_ERROR") {
				t.Fatalf("%d %s", res.Code, res.Body)
			}
		})
	}
	for _, data := range [][]byte{nil, []byte("fake image"), append([]byte{137, 80, 78, 71, 13, 10, 26, 10}, bytes.Repeat([]byte{0}, 16)...), bytes.Repeat([]byte{0}, 5*1024*1024+1)} {
		if res := visualRequest(t, r, data, "0.5"); res.Code != 422 {
			t.Fatalf("image of %d bytes accepted: %d", len(data), res.Code)
		}
	}
}

func TestVisualCacheRechecksPublicationAndDeletion(t *testing.T) {
	gin.SetMode(gin.TestMode)
	ctx := context.Background()
	videos, clips, cache := mocks.NewVideoRepoMem(), mocks.NewClipRepoMem(), mocks.NewCacheMem()
	for _, id := range []string{"vid_public", "vid_draft", "vid_processing"} {
		status := domain.VideoProcessed
		if id == "vid_processing" {
			status = domain.VideoProcessing
		}
		_ = videos.Create(ctx, &domain.Video{ID: id, Status: status})
	}
	_ = clips.Create(ctx, &domain.Clip{ID: "clp_public", VideoID: "vid_public", Status: domain.ClipPublished})
	calls := 0
	ai := &mocks.AIClientMem{SearchEmbeddingFn: func(_ string) ([]float32, error) { calls++; v := make([]float32, 128); v[0] = 1; return v, nil }}
	vectors := mocks.NewVectorStoreMem()
	for _, id := range []string{"vid_draft", "vid_processing", "vid_public"} {
		v := make([]float32, 128)
		v[0] = 1
		_ = vectors.UpsertFrames(ctx, id, []domain.FrameEmbedding{{VideoID: id, Vector: v, ThumbnailURL: "thumbnails/" + id + "/0.jpg"}})
	}

	r := gin.New()
	r.POST("/api/search/visual", NewSearchHandlers(videos, nil, cache, ai, clips, nil, vectors).Visual)
	data := searchImage(t)
	for i := 0; i < 2; i++ {
		res := visualRequest(t, r, data, "0.75")
		if res.Code != 200 || !strings.Contains(res.Body.String(), "vid_public") || strings.Contains(res.Body.String(), "vid_draft") || strings.Contains(res.Body.String(), "vid_processing") {
			t.Fatalf("%d %s", res.Code, res.Body)
		}
	}
	if calls != 1 {
		t.Fatalf("cache missed: %d calls", calls)
	}
	_ = clips.SetStatus(ctx, "clp_public", domain.ClipRejected)
	if res := visualRequest(t, r, data, "0.75"); res.Body.String() != `{"results":[]}` {
		t.Fatal(res.Body.String())
	}
	_ = clips.SetStatus(ctx, "clp_public", domain.ClipPublished)
	_ = videos.SoftDelete(ctx, "vid_public")
	if res := visualRequest(t, r, data, "0.75"); res.Body.String() != `{"results":[]}` {
		t.Fatal(res.Body.String())
	}
	_ = cache.Set(ctx, "feed:revision", "new", 0)
	_ = visualRequest(t, r, data, "0.75")
	if calls != 2 {
		t.Fatalf("revision failed to invalidate: %d calls", calls)
	}
}
