package handlers

import (
	"context"
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"

	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/gen"
	"traning_ai/backend/internal/ports"
)

// ContentHandlers — T2.5.1: feed + videos + clips + categories (real, not stub).
type ContentHandlers struct {
	videos       ports.VideoRepository
	clips        ports.ClipRepository
	categories   ports.CategoryRepository
	interactions ports.InteractionRepository
	analyses     ports.AnalysisStore
	subs         ports.SubtitleStore
	cache        ports.Cache
	ai           ports.AIClient
	storage      ports.ObjectStorage
}

func NewContentHandlers(
	videos ports.VideoRepository,
	clips ports.ClipRepository,
	categories ports.CategoryRepository,
	interactions ports.InteractionRepository,
	analyses ports.AnalysisStore,
	subs ports.SubtitleStore,
	cache ports.Cache,
	ai ports.AIClient,
	storage ports.ObjectStorage,
) *ContentHandlers {
	return &ContentHandlers{
		videos: videos, clips: clips, categories: categories,
		interactions: interactions, analyses: analyses, subs: subs,
		cache: cache, ai: ai, storage: storage,
	}
}

// GET /api/feed — cache AI candidates, hydrate current published metadata on every request.
func (h *ContentHandlers) Feed(c *gin.Context) {
	ctx := c.Request.Context()
	uid := c.GetString("user_id")
	limit, err := contentLimit(c.Query("limit"))
	if err != nil {
		handleDomainErr(c, err)
		return
	}
	if h.ai == nil {
		h.popularityFeed(c, gen.Popularity, limit)
		return
	}
	items := []gin.H{}
	seen := map[string]bool{}
	appendVideo := func(id string) error {
		if seen[id] || len(items) >= limit {
			return nil
		}
		seen[id] = true
		if _, err := h.videos.GetProcessed(ctx, id); err != nil {
			if errors.Is(err, domain.ErrVideoNotFound) {
				return nil
			}
			return err
		}
		clips, err := h.clips.ListPublishedByVideo(ctx, id)
		if err != nil {
			return err
		}
		for i := range clips {
			if len(items) >= limit {
				break
			}
			items = append(items, toClipH(&clips[i], h.storage))
		}
		return nil
	}
	fail := func() { ErrorEnvelope(c, 500, "INTERNAL", "Unable to load feed") }
	mode := gen.Popularity
	if h.ai != nil {
		mode = gen.Fallback
		revision := ""
		if h.cache != nil {
			revision, _, _ = h.cache.Get(ctx, "feed:revision")
		}
		key := "feed:ai:v1:" + revision + ":" + uid + ":" + c.Query("cursor") + ":" + c.DefaultQuery("limit", "10")
		var rec domain.RecResult
		hit := false
		if h.cache != nil {
			if value, ok, _ := h.cache.Get(ctx, key); ok {
				hit = json.Unmarshal([]byte(value), &rec) == nil
			}
		}
		if !hit {
			result, err := h.ai.Recommendation(ctx, uid, limit, nil)
			if err != nil {
				log.Printf("recommendation unavailable: %v", err)
			} else if result != nil {
				rec = *result
			}
			if h.cache != nil {
				if value, err := json.Marshal(rec); err == nil {
					_ = h.cache.Set(ctx, key, string(value), 60*time.Second)
				}
			}
		}
		if rec.RecommendationMode == "personalized" {
			for _, candidate := range rec.Hits {
				if err := appendVideo(candidate.VideoID); err != nil {
					fail()
					return
				}
			}
			if len(items) > 0 {
				mode = gen.Personalized
			}
		}
	}
	if len(items) == 0 {
		h.popularityFeed(c, mode, limit)
		return
	}
	// shortcut: personalized remains single-page and production-disabled until INT-03/AI-12 acceptance.
	if c.Query("cursor") != "" {
		handleDomainErr(c, domain.ErrValidation)
		return
	}
	c.JSON(http.StatusOK, gin.H{"items": items, "next_cursor": nil, "recommendation_mode": mode})
}

func (h *ContentHandlers) popularityFeed(c *gin.Context, mode gen.FeedPageRecommendationMode, limit int) {
	clips, next, err := h.clips.ListPopularPage(c.Request.Context(), c.Query("cursor"), limit)
	if err != nil {
		contentPageError(c, err)
		return
	}
	items := make([]gin.H, 0, len(clips))
	for i := range clips {
		items = append(items, toClipH(&clips[i], h.storage))
	}
	c.JSON(http.StatusOK, gin.H{"items": items, "next_cursor": next, "recommendation_mode": mode})
}

// GET /api/videos?category_id&sort&cursor&limit — stable creation/ranking cursor.
func (h *ContentHandlers) ListVideos(c *gin.Context) {
	limit, err := contentLimit(c.Query("limit"))
	if err != nil {
		handleDomainErr(c, err)
		return
	}
	catID := c.Query("category_id")
	sort := c.Query("sort")
	if sort == "" {
		sort = "newest"
	}
	vids, next, err := h.videos.ListPublicPage(c.Request.Context(), catID, sort, c.Query("cursor"), limit)
	if err != nil {
		contentPageError(c, err)
		return
	}
	items := make([]gin.H, 0, len(vids))
	for i := range vids {
		items = append(items, toVideoH(&vids[i], h.categories))
	}
	c.JSON(http.StatusOK, gin.H{"items": items, "next_cursor": next})
}

func contentLimit(raw string) (int, error) {
	if raw == "" {
		return 10, nil
	}
	limit, err := strconv.Atoi(raw)
	if err != nil || limit < 1 || limit > 50 {
		return 0, domain.ErrValidation
	}
	return limit, nil
}

func contentPageError(c *gin.Context, err error) {
	if errors.Is(err, domain.ErrValidation) {
		handleDomainErr(c, domain.ErrValidation)
		return
	}
	log.Printf("content page unavailable: %v", err)
	ErrorEnvelope(c, 500, "INTERNAL", "Unable to load content")
}

// GET /api/videos/:id — only processed
func (h *ContentHandlers) GetVideo(c *gin.Context) {
	id := c.Param("id")
	v, err := h.videos.GetProcessed(c.Request.Context(), id)
	if err != nil {
		handleDomainErr(c, err)
		return
	}
	cls, _ := h.clips.ListPublishedByVideo(c.Request.Context(), id)
	clipHs := make([]gin.H, 0, len(cls))
	for i := range cls {
		clipHs = append(clipHs, toClipH(&cls[i], h.storage))
	}
	vh := toVideoH(v, h.categories)
	vh["playback_url"] = nil
	if v.RawFilePath != "" {
		url, err := h.storage.GetPresigned(c.Request.Context(), "raw-videos", v.RawFilePath, time.Hour)
		if err != nil {
			ErrorEnvelope(c, 503, "STORAGE_UNAVAILABLE", "Original video unavailable")
			return
		}
		vh["playback_url"] = url
	}
	vh["clips"] = clipHs
	c.JSON(http.StatusOK, vh)
}

// GET /api/videos/:id/analysis — summary only when approved
func (h *ContentHandlers) GetVideoAnalysis(c *gin.Context) {
	id := c.Param("id")
	if _, err := h.videos.GetProcessed(c.Request.Context(), id); err != nil {
		handleDomainErr(c, err)
		return
	}
	a, err := h.analyses.Get(c.Request.Context(), id)
	if err != nil {
		// no analysis yet → empty
		c.JSON(http.StatusOK, gin.H{"timeline_scores": []gin.H{}, "summary": nil, "key_moments": []gin.H{}, "hashtags": []string{}})
		return
	}
	var summary any
	if a.SummaryStatus != nil && *a.SummaryStatus == "approved" {
		summary = a.Summary
	}
	scores := make([]gin.H, 0, len(a.TimelineScores))
	for _, s := range a.TimelineScores {
		scores = append(scores, gin.H{"second": s.Second, "score": s.Score})
	}
	kms := make([]gin.H, 0, len(a.KeyMoments))
	for _, k := range a.KeyMoments {
		kms = append(kms, gin.H{"timestamp": k.Timestamp, "text": k.Text})
	}
	hs := a.Hashtags
	if hs == nil {
		hs = []string{}
	}
	c.JSON(http.StatusOK, gin.H{
		"timeline_scores": scores,
		"summary":         summary,
		"key_moments":     kms,
		"hashtags":        hs,
	})
}

// GET /api/videos/:id/subtitles — cache subs:{id} 300s
func (h *ContentHandlers) GetVideoSubtitles(c *gin.Context) {
	id := c.Param("id")
	if _, err := h.videos.GetProcessed(c.Request.Context(), id); err != nil {
		handleDomainErr(c, err)
		return
	}
	cacheKey := "subs:" + id
	if h.cache != nil {
		if v, ok, _ := h.cache.Get(c.Request.Context(), cacheKey); ok {
			var cached gin.H
			if json.Unmarshal([]byte(v), &cached) == nil {
				c.JSON(http.StatusOK, cached)
				return
			}
		}
	}
	sub, err := h.subs.Get(c.Request.Context(), id)
	if err != nil {
		handleDomainErr(c, err)
		return
	}
	segs := make([]gin.H, 0, len(sub.Segments))
	for _, s := range sub.Segments {
		segs = append(segs, gin.H{
			"segment_index": s.SegmentIndex, "start_time": s.StartTime, "end_time": s.EndTime,
			"text": s.Text, "confidence": s.Confidence, "warning": s.Warning,
		})
	}
	resp := gin.H{"segments": segs}
	if h.cache != nil {
		if b, err := json.Marshal(resp); err == nil {
			_ = h.cache.Set(c.Request.Context(), cacheKey, string(b), 300*time.Second)
		}
	}
	c.JSON(http.StatusOK, resp)
}

// GET /api/clips/:id — only published
func (h *ContentHandlers) GetClip(c *gin.Context) {
	id := c.Param("id")
	cl, err := h.clips.GetPublished(c.Request.Context(), id)
	if err != nil {
		handleDomainErr(c, err)
		return
	}
	c.JSON(http.StatusOK, toClipH(cl, h.storage))
}

// GET /api/categories — cache categories:all 600s
func (h *ContentHandlers) ListCategories(c *gin.Context) {
	cacheKey := "categories:all"
	if h.cache != nil {
		if v, ok, _ := h.cache.Get(c.Request.Context(), cacheKey); ok {
			var cached []gin.H
			if json.Unmarshal([]byte(v), &cached) == nil {
				c.JSON(http.StatusOK, cached)
				return
			}
		}
	}
	cats, _ := h.categories.List(c.Request.Context())
	out := make([]gin.H, 0, len(cats))
	for _, cc := range cats {
		out = append(out, gin.H{"id": cc.ID, "name": cc.Name})
	}
	if h.cache != nil {
		if b, err := json.Marshal(out); err == nil {
			_ = h.cache.Set(c.Request.Context(), cacheKey, string(b), 600*time.Second)
		}
	}
	c.JSON(http.StatusOK, out)
}

func toVideoH(v *domain.Video, catRepo ports.CategoryRepository) gin.H {
	var cat any
	if v.CategoryID != nil {
		cat = gin.H{"id": *v.CategoryID, "name": *v.CategoryID}
		// best-effort: try fetch names (not critical for T2.5.1)
		if catRepo != nil {
			if cats, err := catRepo.List(context.Background()); err == nil {
				for _, cc := range cats {
					if cc.ID == *v.CategoryID {
						cat = gin.H{"id": cc.ID, "name": cc.Name}
						break
					}
				}
			}
		}
	}
	return gin.H{
		"id": v.ID, "title": v.Title, "description": v.Description,
		"thumbnail_url": v.ThumbnailURL, "duration_seconds": v.DurationSeconds,
		"status": string(v.Status), "category": cat, "created_at": v.CreatedAt.UTC().Format(time.RFC3339),
	}
}

func toClipH(cl *domain.Clip, storage ports.ObjectStorage) gin.H {
	var playback any
	if cl.ClipFilePath != nil {
		playback = *cl.ClipFilePath
		// try presign if storage available (mem returns https://storage.local/...)
		if storage != nil {
			if u, err := storage.GetPresigned(nil, "clips", *cl.ClipFilePath, time.Hour); err == nil {
				playback = u
			}
		}
	}
	return gin.H{
		"id": cl.ID, "video_id": cl.VideoID, "title": cl.Title,
		"start_time": cl.StartTime, "end_time": cl.EndTime, "average_score": cl.AverageScore,
		"thumbnail_url": cl.ThumbnailURL, "playback_url": playback,
		"status": string(cl.Status), "created_at": cl.CreatedAt.UTC().Format(time.RFC3339),
	}
}
