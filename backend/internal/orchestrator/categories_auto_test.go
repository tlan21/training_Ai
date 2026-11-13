package orchestrator

import (
	"context"
	"testing"

	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/mocks"
)

type settingsFake struct{ s domain.SystemSettings }

func (f settingsFake) Get(context.Context) (*domain.SystemSettings, error) { s := f.s; return &s, nil }
func (f settingsFake) Update(context.Context, map[string]string) error   { return nil }

// INT-64: with category_auto_apply on, the ViT suggestion becomes the video's category at the end of processing,
// but an editor's existing choice is never overwritten; with it off, only the suggestion is stored.
func TestSuggestCategoryAutoApply(t *testing.T) {
	ctx := context.Background()
	for _, tc := range []struct {
		name         string
		auto, editor bool
		want         string
	}{
		{"auto on assigns", true, false, "football"},
		{"auto off keeps suggestion only", false, false, ""},
		{"editor choice kept", true, true, "music"},
	} {
		videos, analysis, cats := mocks.NewVideoRepoMem(), mocks.NewAnalysisStoreMem(), mocks.NewCategoryRepoMem()
		football, _ := cats.Create(ctx, "Bóng đá", nil, nil)
		music, _ := cats.Create(ctx, "Ca nhạc", nil, nil)
		var existing *string
		if tc.editor {
			existing = &music.ID
		}
		videos.M["vid_a"] = &domain.Video{ID: "vid_a", Title: "trận đấu", Status: domain.VideoProcessed, CategoryID: existing}
		suggestion := "bong_da"
		if err := analysis.Put(ctx, "vid_a", nil, nil, &suggestion, nil); err != nil {
			t.Fatal(err)
		}
		r := New(videos, mocks.NewJobRepoMem(), analysis, mocks.NewSubtitleStoreMem(), nil, mocks.NewEventBusMem())
		r.WithCategories(settingsFake{domain.SystemSettings{CategorySuggestionEnabled: true, CategoryAutoApply: tc.auto}}, cats)
		if err := r.suggestCategory(ctx, "vid_a"); err != nil {
			t.Fatalf("%s: %v", tc.name, err)
		}
		got := ""
		if id := videos.M["vid_a"].CategoryID; id != nil {
			got = map[string]string{football.ID: "football", music.ID: "music"}[*id]
		}
		a, _ := analysis.Get(ctx, "vid_a")
		if got != tc.want || a.CategoryMatch == nil || a.CategoryMatch.CategoryID != football.ID {
			t.Fatalf("%s: category %q, match %+v", tc.name, got, a.CategoryMatch)
		}
	}
}
