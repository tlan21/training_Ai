package mocks

import (
	"context"
	"sort"
	"strings"
	"traning_ai/backend/internal/domain"
)

func (r *VideoRepoMem) ListCMS(_ context.Context, f domain.CMSVideoFilter) ([]domain.Video, int, error) {
	r.mu.Lock()
	defer r.mu.Unlock()
	all := []domain.Video{}
	for _, v := range r.M {
		if f.Status != nil && string(v.Status) != *f.Status {
			continue
		}
		if !f.IncludeDeleted && v.Status == domain.VideoDeleted && (f.Status == nil || *f.Status != "deleted") {
			continue
		}
		if !strings.Contains(strings.ToLower(v.Title), strings.ToLower(strings.TrimSpace(f.Query))) {
			continue
		}
		if f.CategoryID != "" && (v.CategoryID == nil || *v.CategoryID != f.CategoryID) {
			continue
		}
		if f.From != nil && v.CreatedAt.Before(*f.From) || f.To != nil && !v.CreatedAt.Before(*f.To) {
			continue
		}
		all = append(all, *v)
	}
	sort.Slice(all, func(i, j int) bool {
		if all[i].CreatedAt.Equal(all[j].CreatedAt) {
			return all[i].ID > all[j].ID
		}
		return all[i].CreatedAt.After(all[j].CreatedAt)
	})
	total := len(all)
	start := (f.Page - 1) * f.Size
	if start >= total {
		return []domain.Video{}, total, nil
	}
	end := start + f.Size
	if end > total {
		end = total
	}
	return all[start:end], total, nil
}
func (r *ClipRepoMem) ListCMS(ctx context.Context, videoID, status *string, query string) ([]domain.Clip, error) {
	all, err := r.List(ctx, videoID, status)
	if err != nil {
		return nil, err
	}
	out := []domain.Clip{}
	for _, c := range all {
		if strings.Contains(strings.ToLower(c.Title), strings.ToLower(strings.TrimSpace(query))) {
			out = append(out, c)
		}
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].CreatedAt.Equal(out[j].CreatedAt) {
			return out[i].ID > out[j].ID
		}
		return out[i].CreatedAt.After(out[j].CreatedAt)
	})
	return out, nil
}
func (r *JobRepoMem) SetProcessingOptions(_ context.Context, id string, options domain.ProcessingOptions) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	j, ok := r.M[id]
	if !ok {
		return domain.ErrJobNotFound
	}
	j.ProcessingOptions = &options
	j.SkippedStages = options.SkippedStages()
	return nil
}
func (s *AnalysisStoreMem) SetProposalDecisions(_ context.Context, id string, decisions []domain.ProposalDecision) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	v, ok := s.M[id]
	if !ok {
		return domain.ErrNotFound
	}
	v.ProposalDecisions = append([]domain.ProposalDecision{}, decisions...)
	return nil
}
func (s *AnalysisStoreMem) SetCategoryMatch(_ context.Context, id string, match *domain.CategoryMatch) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	v, ok := s.M[id]
	if !ok {
		return domain.ErrNotFound
	}
	v.CategoryMatch = match
	return nil
}
func (s *ObjectStorageMem) Usage(_ context.Context) (*domain.StorageUsage, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	usage := &domain.StorageUsage{Buckets: []domain.BucketUsage{}}
	for _, name := range []string{"raw-videos", "clips", "thumbnails"} {
		b := domain.BucketUsage{Name: name}
		for key, data := range s.Objs {
			if strings.HasPrefix(key, name+"/") {
				b.Objects++
				b.Bytes += int64(len(data))
			}
		}
		usage.TotalBytes += b.Bytes
		usage.Buckets = append(usage.Buckets, b)
	}
	return usage, nil
}
