package handlers

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http/httptest"
	"net/url"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/gen"
	"traning_ai/backend/internal/mocks"
)

func TestContentPagesContinueAndValidate(t *testing.T) {
	ctx := context.Background()
	videos, clips, interactions := mocks.NewVideoRepoMem(), mocks.NewClipRepoMem(), mocks.NewInteractionRepoMem()
	clips.Videos, clips.Interactions = videos, interactions
	videos.Clips, videos.Interactions = clips, interactions
	cat := "cat_a"
	for i := 0; i < 7; i++ {
		id := fmt.Sprintf("vid_page_%02d", i)
		v := &domain.Video{ID: id, Title: id, Status: domain.VideoProcessed, CategoryID: &cat, CreatedAt: time.Now().Add(-time.Hour)}
		if i == 6 {
			v.Status = domain.VideoDeleted
		}
		if err := videos.Create(ctx, v); err != nil {
			t.Fatal(err)
		}
		for j := 0; j < 2; j++ {
			if err := clips.Create(ctx, &domain.Clip{ID: fmt.Sprintf("clp_%02d_%d", i, j), VideoID: id, Status: domain.ClipPublished, CreatedAt: v.CreatedAt}); err != nil {
				t.Fatal(err)
			}
		}
	}
	h := NewContentHandlers(videos, clips, nil, interactions, nil, nil, nil, nil, nil)
	r := gin.New()
	r.GET("/feed", h.Feed)
	r.GET("/videos", h.ListVideos)
	for _, route := range []string{"/feed", "/videos?category_id=cat_a&sort=newest", "/videos?category_id=cat_a&sort=trending"} {
		want := 6
		if route == "/feed" {
			want = 12
		}
		seen := map[string]bool{}
		cursor := ""
		for page := 0; page < 10; page++ {
			endpoint, err := url.Parse(route)
			if err != nil {
				t.Fatal(err)
			}
			params := endpoint.Query()
			params.Set("limit", "3")
			if cursor != "" {
				params.Set("cursor", cursor)
			}
			endpoint.RawQuery = params.Encode()
			w := httptest.NewRecorder()
			r.ServeHTTP(w, httptest.NewRequest("GET", endpoint.String(), nil))
			var data gen.FeedPage
			if w.Code != 200 || json.Unmarshal(w.Body.Bytes(), &data) != nil {
				t.Fatalf("%d %s", w.Code, w.Body)
			}
			if data.Items == nil || len(*data.Items) > 3 {
				t.Fatal("invalid page size")
			}
			for _, item := range *data.Items {
				if item.Id == nil || seen[*item.Id] {
					t.Fatal("duplicate or missing ID", item)
				}
				seen[*item.Id] = true
			}
			if data.NextCursor == nil {
				break
			}
			if *data.NextCursor == cursor {
				t.Fatal("cursor did not advance")
			}
			cursor = *data.NextCursor
		}
		if len(seen) != want {
			t.Fatalf("%s: %d items, want%d", route, len(seen), want)
		}
		other := "/feed"
		if route == "/feed" {
			other = "/videos"
		}
		w := httptest.NewRecorder()
		r.ServeHTTP(w, httptest.NewRequest("GET", other+"?cursor="+url.QueryEscape(cursor), nil))
		if w.Code != 422 {
			t.Fatal("cross-route cursor accepted", w.Code)
		}
	}
	for _, endpoint := range []string{"/feed?cursor=bad!", "/feed?limit=51", "/feed?limit=0", "/feed?limit=text", "/videos?sort=invalid", "/videos?limit=-1", "/videos?cursor=bad!"} {
		w := httptest.NewRecorder()
		r.ServeHTTP(w, httptest.NewRequest("GET", endpoint, nil))
		var body struct{ Error struct{ Code string } }
		if json.Unmarshal(w.Body.Bytes(), &body) != nil || w.Code != 422 || body.Error.Code != "VALIDATION_ERROR" {
			t.Fatalf("%s: %d %s", endpoint, w.Code, w.Body)
		}
	}
}
