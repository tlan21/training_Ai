package handlers

import (
	"context"
	"fmt"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
	"traning_ai/backend/internal/ports"
)

type notifyFake struct {
	ports.NotificationRepository
	fanned []string
	marked [][]int64
}

func (f *notifyFake) FanOutClipPublished(_ context.Context, clipID string) (int64, error) {
	f.fanned = append(f.fanned, clipID)
	return 2, nil
}
func (f *notifyFake) MarkRead(_ context.Context, _ string, ids []int64) error {
	f.marked = append(f.marked, ids)
	return nil
}

func TestClipPublishedConsumerDropsMalformedEvents(t *testing.T) {
	repo := &notifyFake{}
	handle := ClipPublishedConsumer(repo)
	for _, payload := range []string{`not json`, `{}`, `{"clip_id":"vid_x"}`, `{"clip_id":"clp_` + strings.Repeat("x", 60) + `"}`} {
		if err := handle(context.Background(), []byte(payload)); err != nil {
			t.Fatalf("%s must be dropped, not retried: %v", payload, err)
		}
	}
	if err := handle(context.Background(), []byte(`{"clip_id":"clp_ok","video_id":"vid_ok","published_at":"2026-11-13T05:00:00Z"}`)); err != nil {
		t.Fatal(err)
	}
	if len(repo.fanned) != 1 || repo.fanned[0] != "clp_ok" {
		t.Fatalf("fan-out calls: %v", repo.fanned)
	}
}

func TestNotificationMarkReadValidation(t *testing.T) {
	repo := &notifyFake{}
	r := gin.New()
	r.Use(func(c *gin.Context) { c.Set("user_id", "usr_t") })
	r.POST("/read", NewNotificationHandlers(repo, nil).MarkRead)
	ids := make([]string, 101)
	for i := range ids {
		ids[i] = fmt.Sprintf(`"%d"`, i+1)
	}
	for _, body := range []string{`{"ids":["abc"]}`, `{"ids":["0"]}`, `{"ids":[` + strings.Join(ids, ",") + `]}`, `not json`} {
		if w := do(r, "POST", "/read", body); w.Code != 422 {
			t.Fatalf("%.40s accepted: %d", body, w.Code)
		}
	}
	if w := do(r, "POST", "/read", ""); w.Code != 204 {
		t.Fatalf("empty body (mark all): %d", w.Code)
	}
	if w := do(r, "POST", "/read", `{"ids":["7","9"]}`); w.Code != 204 {
		t.Fatalf("ids: %d", w.Code)
	}
	if len(repo.marked) != 2 || len(repo.marked[0]) != 0 || fmt.Sprint(repo.marked[1]) != "[7 9]" {
		t.Fatalf("mark calls: %v", repo.marked)
	}
}
