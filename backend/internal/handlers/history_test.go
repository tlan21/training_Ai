package handlers

import (
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/mocks"
)

func TestHistoryAndLikesSerializePublicPlayback(t *testing.T) {
	repo := mocks.NewInteractionRepoMem()
	file := "test.mp4"
	repo.Clips["vid_test"] = &domain.Clip{ID: "clp_test", VideoID: "vid_test", ClipFilePath: &file, Status: domain.ClipPublished}
	repo.Items = []domain.Interaction{{UserID: "usr_test", VideoID: "vid_test", InteractionType: domain.InteractLike}}
	h := NewAuthHandlers(nil, nil, nil, nil, repo, mocks.NewObjectStorageMem())
	r := gin.New()
	r.Use(func(c *gin.Context) { c.Set("user_id", "usr_test") })
	r.GET("/history", h.History)
	r.GET("/likes", h.Likes)
	for _, path := range []string{"/history", "/likes"} {
		w := httptest.NewRecorder()
		r.ServeHTTP(w, httptest.NewRequest("GET", path, nil))
		if w.Code != 200 || !strings.Contains(w.Body.String(), `"playback_url":"https://storage.local/test.mp4"`) || strings.Contains(w.Body.String(), `"clip_file_path"`) {
			t.Fatalf("public clip schema mismatch: %d %s", w.Code, w.Body)
		}
	}
}
