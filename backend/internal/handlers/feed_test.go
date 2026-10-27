package handlers

import (
	"context"
	"encoding/json"
	"errors"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/gen"
	"traning_ai/backend/internal/mocks"
	"traning_ai/backend/internal/ports"
)

func TestFeedModeMetadataLimitAndCachedVisibility(t *testing.T) {
	for _, test := range []struct {
		name, upstream string
		unavailable    bool
		mode           gen.FeedPageRecommendationMode
	}{
		{name: "primary popularity", mode: gen.Popularity},
		{name: "AI unavailable", unavailable: true, mode: gen.Fallback},
		{name: "stub never personalized", upstream: "stub", mode: gen.Fallback},
		{name: "legacy missing mode", upstream: "legacy", mode: gen.Fallback},
		{name: "verified personalized", upstream: "personalized", mode: gen.Personalized},
	} {
		t.Run(test.name, func(t *testing.T) {
			ctx := context.Background()
			videos, clips, cache := mocks.NewVideoRepoMem(), mocks.NewClipRepoMem(), mocks.NewCacheMem()
			file := "real.mp4"
			for _, v := range []domain.Video{{ID: "vid_public", Status: domain.VideoProcessed}, {ID: "vid_private", Status: domain.VideoDeleted}} {
				if err := videos.Create(ctx, &v); err != nil {
					t.Fatal(err)
				}
			}
			for _, clip := range []domain.Clip{
				{ID: "clp_real_a", VideoID: "vid_public", Title: "Postgres title", Status: domain.ClipPublished, ClipFilePath: &file},
				{ID: "clp_real_b", VideoID: "vid_public", Title: "Second real title", Status: domain.ClipPublished, ClipFilePath: &file},
				{ID: "clp_hidden", VideoID: "vid_private", Title: "Hidden", Status: domain.ClipPublished},
			} {
				if err := clips.Create(ctx, &clip); err != nil {
					t.Fatal(err)
				}
			}
			interactions := mocks.NewInteractionRepoMem()
			clips.Videos, clips.Interactions = videos, interactions
			interactions.Items = []domain.Interaction{{VideoID: "vid_public"}, {VideoID: "vid_private"}}
			calls := 0
			var ai ports.AIClient
			if test.upstream != "" || test.unavailable {
				ai = &mocks.AIClientMem{RecommendationFn: func(_ string, _ int, _ map[string]string) (*domain.RecResult, error) {
					calls++
					if test.unavailable {
						return nil, errors.New("AI timeout")
					}
					return &domain.RecResult{RecommendationMode: test.upstream, Hits: []domain.VideoHit{
						{VideoID: "ml100k_i_1"}, {VideoID: "vid_private"},
						{VideoID: "vid_public"}, {VideoID: "vid_public"},
					}}, nil
				}}
			}
			h := NewContentHandlers(videos, clips, nil, interactions, nil, nil, cache, ai, mocks.NewObjectStorageMem())
			r := gin.New()
			r.GET("/feed", h.Feed)
			fetch := func(limit string) gen.FeedPage {
				t.Helper()
				w := httptest.NewRecorder()
				r.ServeHTTP(w, httptest.NewRequest("GET", "/feed?limit="+limit, nil))
				var page gen.FeedPage
				if w.Code != 200 {
					t.Fatalf("%d %s", w.Code, w.Body)
				}
				if err := json.Unmarshal(w.Body.Bytes(), &page); err != nil {
					t.Fatal(err)
				}
				return page
			}
			for i := 0; i < 2; i++ {
				page := fetch("1")
				if page.RecommendationMode != test.mode || len(*page.Items) != 1 {
					t.Fatalf("mode/limit: %+v", page)
				}
				clip := (*page.Items)[0]
				if clip.Title == nil || *clip.Title == "FAKE" || clip.PlaybackUrl == nil || clip.VideoId == nil || *clip.VideoId != "vid_public" {
					t.Fatalf("metadata/visibility: %+v", clip)
				}
			}
			updatedTitle := "Current database title"
			for _, id := range []string{"clp_real_a", "clp_real_b"} {
				if _, err := clips.UpdateMeta(ctx, id, &updatedTitle, nil, nil); err != nil {
					t.Fatal(err)
				}
			}
			updated := fetch("1")
			if *(*updated.Items)[0].Title != updatedTitle {
				t.Fatal("cached metadata was not hydrated again")
			}
			if ai != nil && calls != 1 {
				t.Fatalf("AI cache missed: %d", calls)
			}
			wide := fetch("3")
			if len(*wide.Items) != 2 || *(*wide.Items)[0].Id == *(*wide.Items)[1].Id {
				t.Fatalf("duplicate candidates leaked: %+v", wide)
			}
			_ = videos.SoftDelete(ctx, "vid_public")
			page := fetch("1")
			if len(*page.Items) != 0 || page.RecommendationMode == gen.Personalized {
				t.Fatalf("cached private content leaked: %+v", page)
			}
		})
	}
}

func TestFeedRejectsPersonalizedWhenOnlyUnknownProductIDs(t *testing.T) {
	ai := &mocks.AIClientMem{RecommendationFn: func(_ string, _ int, _ map[string]string) (*domain.RecResult, error) {
		return &domain.RecResult{RecommendationMode: "personalized", Hits: []domain.VideoHit{{VideoID: "ml100k_i_1"}}}, nil
	}}
	h := NewContentHandlers(mocks.NewVideoRepoMem(), mocks.NewClipRepoMem(), nil, nil, nil, nil, nil, ai, nil)
	r := gin.New()
	r.GET("/feed", h.Feed)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest("GET", "/feed", nil))
	var page gen.FeedPage
	if err := json.Unmarshal(w.Body.Bytes(), &page); err != nil {
		t.Fatal(err)
	}
	if w.Code != 200 || page.RecommendationMode != gen.Fallback || len(*page.Items) != 0 {
		t.Fatalf("fake product recommendation accepted: %d %s", w.Code, w.Body)
	}
}
