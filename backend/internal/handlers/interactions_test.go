package handlers

import (
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
	"traning_ai/backend/internal/mocks"
)

func TestInteractionClientBoundary(t *testing.T) {
	for _, tc := range []struct {
		role, body string
		status     int
	}{
		{"client", `{"video_id":"vid_test","clip_id":"clp_test","interaction_type":"watch_time","duration_watched":5}`, 201},
		{"client", `{"video_id":"vid_test","interaction_type":"click"}`, 201},
		{"admin", `{"video_id":"vid_test","interaction_type":"click"}`, 403},
		{"editor", `{"video_id":"vid_test","interaction_type":"click"}`, 403},
		{"", `{"video_id":"vid_test","interaction_type":"click"}`, 403},
		{"client", `{"video_id":"123","interaction_type":"click"}`, 422},
		{"client", `{"video_id":"vid_test","clip_id":"123","interaction_type":"click"}`, 422},
		{"client", `{"video_id":"vid_test","interaction_type":"like","duration_watched":1}`, 422},
		{"client", `{"video_id":"vid_test","interaction_type":"watch_time","duration_watched":-1}`, 422},
		{"client", `{"video_id":"vid_test","interaction_type":"watch_time","duration_watched":2147483648}`, 422},
		{"client", `{"video_id":"vid_test","interaction_type":"watch_time","duration_watched":1.5}`, 422},
		{"client", `{"video_id":"vid_test","interaction_type":"view"}`, 422},
	} {
		t.Run(tc.role+tc.body, func(t *testing.T) {
			repo := mocks.NewInteractionRepoMem()
			r := gin.New()
			r.Use(func(c *gin.Context) { c.Set("user_id", "usr_test"); c.Set("user_role", tc.role) })
			r.POST("/api/interactions", NewInteractionHandlers(repo).Create)
			w := httptest.NewRecorder()
			req := httptest.NewRequest("POST", "/api/interactions", strings.NewReader(tc.body))
			req.Header.Set("Content-Type", "application/json")
			r.ServeHTTP(w, req)
			if w.Code != tc.status || (tc.status != 201 && (len(repo.Items) != 0 || !strings.Contains(w.Body.String(), `"error":`))) {
				t.Fatalf("status=%d body=%s writes=%d", w.Code, w.Body, len(repo.Items))
			}
		})
	}
}
