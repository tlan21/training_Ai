package mocks

import (
	"context"
	"sort"
	"time"
	"traning_ai/backend/internal/domain"
)

func contentRanks(repo *InteractionRepoMem, snapshot time.Time) map[string]int64 {
	ranks := map[string]int64{}
	if repo == nil {
		return ranks
	}
	repo.mu.Lock()
	defer repo.mu.Unlock()
	for _, i := range repo.Items {
		if i.CreatedAt.After(snapshot.Add(-7*24*time.Hour)) && !i.CreatedAt.After(snapshot) {
			ranks[i.VideoID]++
		}
	}
	return ranks
}

func (r *ClipRepoMem) ListPopularPage(ctx context.Context, cursor string, limit int) ([]domain.Clip, *string, error) {
	p, err := domain.ParseContentCursor(cursor, "feed", limit)
	if err != nil {
		return nil, nil, err
	}
	ranks := contentRanks(r.Interactions, p.Snapshot)
	status := "published"
	all, err := r.List(ctx, nil, &status)
	if err != nil {
		return nil, nil, err
	}
	items := []domain.Clip{}
	for _, c := range all {
		if r.Videos != nil {
			v, err := r.Videos.GetProcessed(ctx, c.VideoID)
			if err != nil || v.DeletedAt != nil || v.CreatedAt.After(p.Snapshot) {
				continue
			}
		}
		if c.CreatedAt.IsZero() {
			c.CreatedAt = time.Unix(0, 0).UTC()
		}
		if p.After(ranks[c.VideoID], c.CreatedAt, c.ID) {
			items = append(items, c)
		}
	}
	sort.Slice(items, func(i, j int) bool {
		a, b := items[i], items[j]
		if ranks[a.VideoID] != ranks[b.VideoID] {
			return ranks[a.VideoID] > ranks[b.VideoID]
		}
		if !a.CreatedAt.Equal(b.CreatedAt) {
			return a.CreatedAt.After(b.CreatedAt)
		}
		return a.ID > b.ID
	})
	if len(items) > limit {
		items = items[:limit]
		last := items[limit-1]
		p.Rank, p.CreatedAt, p.ID = ranks[last.VideoID], last.CreatedAt, last.ID
		next, err := p.Encode()
		return items, &next, err
	}
	return items, nil, nil
}

func (r *VideoRepoMem) ListPublicPage(ctx context.Context, categoryID, order, cursor string, limit int) ([]domain.Video, *string, error) {
	if order != "newest" && order != "trending" {
		return nil, nil, domain.ErrValidation
	}
	p, err := domain.ParseContentCursor(cursor, "videos/"+order+"/"+categoryID, limit)
	if err != nil {
		return nil, nil, err
	}
	ranks := map[string]int64{}
	if order == "trending" {
		ranks = contentRanks(r.Interactions, p.Snapshot)
	}
	r.mu.Lock()
	all := []domain.Video{}
	for _, v := range r.M {
		all = append(all, *v)
	}
	r.mu.Unlock()
	items := []domain.Video{}
	for _, v := range all {
		if v.Status != domain.VideoProcessed || v.DeletedAt != nil || (categoryID != "" && (v.CategoryID == nil || *v.CategoryID != categoryID)) {
			continue
		}
		if order == "trending" && r.Clips != nil {
			clips, _ := r.Clips.ListPublishedByVideo(ctx, v.ID)
			published := false
			for _, c := range clips {
				published = published || !c.CreatedAt.After(p.Snapshot)
			}
			if !published {
				continue
			}
		}
		if v.CreatedAt.IsZero() {
			v.CreatedAt = time.Unix(0, 0).UTC()
		}
		if p.After(ranks[v.ID], v.CreatedAt, v.ID) {
			items = append(items, v)
		}
	}
	sort.Slice(items, func(i, j int) bool {
		a, b := items[i], items[j]
		if ranks[a.ID] != ranks[b.ID] {
			return ranks[a.ID] > ranks[b.ID]
		}
		if !a.CreatedAt.Equal(b.CreatedAt) {
			return a.CreatedAt.After(b.CreatedAt)
		}
		return a.ID > b.ID
	})
	if len(items) > limit {
		items = items[:limit]
		last := items[limit-1]
		p.Rank, p.CreatedAt, p.ID = ranks[last.ID], last.CreatedAt, last.ID
		next, err := p.Encode()
		return items, &next, err
	}
	return items, nil, nil
}
