package cms

import (
	"encoding/json"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/mocks"
)

// INT-62: the first publish (draft → published) emits exactly one Kafka clip.published; re-publishing emits nothing.
func TestPublishEmitsClipPublishedOnce(t *testing.T) {
	videos, clips, bus := mocks.NewVideoRepoMem(), mocks.NewClipRepoMem(), mocks.NewEventBusMem()
	videos.M["vid_n"] = &domain.Video{ID: "vid_n", Status: domain.VideoProcessed}
	file := "clips/clp_n.mp4"
	clips.M["clp_n"] = &domain.Clip{ID: "clp_n", VideoID: "vid_n", Title: "Bàn thắng", ClipFilePath: &file, Status: domain.ClipDraft}
	r := gin.New()
	r.POST("/clips/:id/publish", NewClipHandlers(clips, videos, bus, nil, nil, nil).Publish)
	for i := 0; i < 2; i++ {
		w := httptest.NewRecorder()
		r.ServeHTTP(w, httptest.NewRequest("POST", "/clips/clp_n/publish", nil))
		if w.Code != 200 {
			t.Fatalf("publish %d: %d %s", i, w.Code, w.Body)
		}
	}
	var events []domain.ClipPublishedEvent
	for _, e := range bus.Events {
		if e.Topic == domain.TopicClipPublished {
			var ev domain.ClipPublishedEvent
			if err := json.Unmarshal(e.Raw, &ev); err != nil || e.Key != "clp_n" {
				t.Fatalf("event %s %s: %v", e.Key, e.Raw, err)
			}
			events = append(events, ev)
		}
	}
	if len(events) != 1 || events[0].ClipID != "clp_n" || events[0].VideoID != "vid_n" || events[0].PublishedAt.IsZero() {
		t.Fatalf("clip.published events: %+v", events)
	}
}
