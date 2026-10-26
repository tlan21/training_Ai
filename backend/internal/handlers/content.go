package handlers

import (
	"context"
	"encoding/json"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"

	"traning_ai/backend/internal/domain"
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

// GET /api/feed?cursor&limit=10 — cache 60s, AI Recommendation fallback PopularityTop
func (h *ContentHandlers) Feed(c *gin.Context) {
	uid := c.GetString("user_id")
	cursor := c.Query("cursor")
	limit := parseLimit(c.Query("limit"), 10)
	revision := ""
	if h.cache != nil {
		revision, _, _ = h.cache.Get(c.Request.Context(), "feed:revision")
	}
	cacheKey := "feed:" + revision + ":" + uid + ":" + cursor + ":" + c.DefaultQuery("limit", "10")
	if h.cache != nil {
		if v, ok, _ := h.cache.Get(c.Request.Context(), cacheKey); ok {
			var cached gin.H
			if json.Unmarshal([]byte(v), &cached) == nil {
				c.JSON(http.StatusOK, cached)
				return
			}
		}
	}
	var clipItems []gin.H
	// try AI
	if h.ai != nil {
		if rec, err := h.ai.Recommendation(c.Request.Context(), uid, limit, nil); err == nil && len(rec.Hits) > 0 {
			for _, hit := range rec.Hits {
				if hit.VideoID == "" {
					continue
				}
				cls, _ := h.clips.ListPublishedByVideo(c.Request.Context(), hit.VideoID)
				for _, cl := range cls {
					clipItems = append(clipItems, toClipH(&cl, h.storage))
					if len(clipItems) >= limit {
						break
					}
				}
				if len(clipItems) >= limit {
					break
				}
			}
		}
	}
	// fallback popularity or direct clip scan
	if len(clipItems) == 0 {
		// try popularity
		var ids []string
		if h.interactions != nil {
			ids, _ = h.interactions.PopularityTop(c.Request.Context(), limit)
		}
		if len(ids) > 0 {
			for _, vid := range ids {
				cls, _ := h.clips.ListPublishedByVideo(c.Request.Context(), vid)
				for _, cl := range cls {
					clipItems = append(clipItems, toClipH(&cl, h.storage))
					if len(clipItems) >= limit {
						break
					}
				}
			}
		}
		// still empty → just list published clips (mem fallback)
		if len(clipItems) == 0 && h.clips != nil {
			all, _ := h.clips.List(c.Request.Context(), nil, strPtr(string(domain.ClipPublished)))
			for i, cl := range all {
				if i >= limit {
					break
				}
				clipItems = append(clipItems, toClipH(&cl, h.storage))
			}
		}
	}
	if clipItems == nil {
		clipItems = []gin.H{}
	}
	resp := gin.H{"items": clipItems, "next_cursor": nil}
	if h.cache != nil {
		if b, err := json.Marshal(resp); err == nil {
			_ = h.cache.Set(c.Request.Context(), cacheKey, string(b), 60*time.Second)
		}
	}
	c.JSON(http.StatusOK, resp)
}

// GET /api/videos?category_id&sort&cursor&limit — cursor as offset string, trending via PopularityTop
func (h *ContentHandlers) ListVideos(c *gin.Context) {
	limit := parseLimit(c.Query("limit"), 10)
	catID := c.Query("category_id")
	sort := c.Query("sort")
	if sort == "" {
		sort = "newest"
	}
	var vids []domain.Video
	if sort == "trending" && h.interactions != nil {
		ids, _ := h.interactions.PopularityTop(c.Request.Context(), 100)
		for _, id := range ids {
			v, err := h.videos.Get(c.Request.Context(), id)
			if err != nil || v.Status != domain.VideoProcessed {
				continue
			}
			if catID != "" && (v.CategoryID == nil || *v.CategoryID != catID) {
				continue
			}
			vids = append(vids, *v)
			if len(vids) >= limit {
				break
			}
		}
	} else {
		// newest fallback: list all processed
		all, _, _ := h.videos.List(c.Request.Context(), strPtr(string(domain.VideoProcessed)), 1, 1000)
		for _, v := range all {
			if catID != "" && (v.CategoryID == nil || *v.CategoryID != catID) {
				continue
			}
			vids = append(vids, v)
			if len(vids) >= limit {
				break
			}
		}
	}
	items := make([]gin.H, 0, len(vids))
	for i := range vids {
		items = append(items, toVideoH(&vids[i], h.categories))
	}
	c.JSON(http.StatusOK, gin.H{"items": items, "next_cursor": nil})
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
