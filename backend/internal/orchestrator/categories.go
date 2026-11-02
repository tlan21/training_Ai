package orchestrator

import (
	"context"
	"errors"
	"sort"
	"strings"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/ports"
)

func (r *Runner) WithCategories(settings ports.SettingsRepository, categories ports.CategoryRepository) {
	r.settings, r.categories = settings, categories
}

// Category rules suggest metadata; the CMS editor still confirms the video's category.
func (r *Runner) suggestCategory(ctx context.Context, videoID string) error {
	if r.settings == nil || r.categories == nil {
		return nil
	}
	settings, err := r.settings.Get(ctx)
	if err != nil {
		return err
	}
	a, err := r.analysis.Get(ctx, videoID)
	if err != nil {
		return err
	}
	if !settings.CategorySuggestionEnabled && !settings.CategoryKeywordEnabled {
		return r.analysis.SetCategoryMatch(ctx, videoID, nil)
	}
	categories, err := r.categories.List(ctx)
	if err != nil {
		return err
	}
	v, err := r.videos.Get(ctx, videoID)
	if err != nil {
		return err
	}
	text := v.Title
	if v.Description != nil {
		text += "\n" + *v.Description
	}
	if settings.CategoryKeywordEnabled {
		sub, err := r.subs.Get(ctx, videoID)
		if err == nil {
			text += "\n" + sub.FullTranscript
		} else if !errors.Is(err, domain.ErrNotFound) {
			return err
		}
	}
	return r.analysis.SetCategoryMatch(ctx, videoID, matchCategory(categories, a.CategorySuggestion, text, settings.CategorySuggestionEnabled, settings.CategoryKeywordEnabled))
}
func matchCategory(categories []domain.Category, suggestion *string, text string, vision, keywords bool) *domain.CategoryMatch {
	sort.Slice(categories, func(i, j int) bool {
		if categories[i].Name == categories[j].Name {
			return categories[i].ID < categories[j].ID
		}
		return categories[i].Name < categories[j].Name
	})
	text = strings.ToLower(text)
	if keywords {
		for _, c := range categories {
			for _, word := range c.Keywords {
				key := strings.TrimSpace(word)
				if key != "" && strings.Contains(text, strings.ToLower(key)) {
					return &domain.CategoryMatch{CategoryID: c.ID, Name: c.Name, Source: "keyword", Keyword: &key}
				}
			}
		}
	}
	if vision && suggestion != nil {
		names := map[string]string{"bong_da": "Bóng đá", "the_thao": "Thể thao", "ca_nhac": "Ca nhạc", "tin_tuc": "Tin tức"}
		expected := names[*suggestion]
		for _, c := range categories {
			if c.ID == *suggestion || strings.EqualFold(c.Name, *suggestion) || (expected != "" && strings.EqualFold(c.Name, expected)) {
				return &domain.CategoryMatch{CategoryID: c.ID, Name: c.Name, Source: "vision"}
			}
		}
	}
	return nil
}
