package handlers

import (
	"bytes"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"image"
	_ "image/jpeg"
	_ "image/png"
	"io"
	"math"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"

	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/ports"
)

type SearchHandlers struct {
	videos  ports.VideoRepository
	subs    ports.SubtitleStore
	cache   ports.Cache
	ai      ports.AIClient
	clips   ports.ClipRepository
	storage ports.ObjectStorage
}

func NewSearchHandlers(videos ports.VideoRepository, subs ports.SubtitleStore, cache ports.Cache, ai ports.AIClient, clips ports.ClipRepository, storage ports.ObjectStorage) *SearchHandlers {
	return &SearchHandlers{videos: videos, subs: subs, cache: cache, ai: ai, clips: clips, storage: storage}
}

// POST /api/search/visual — multipart image ≤5MB → base64 → AI Search → filter min_similarity
func (h *SearchHandlers) Visual(c *gin.Context) {
	c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, 8*1024*1024)
	defer func() {
		if c.Request.MultipartForm != nil {
			_ = c.Request.MultipartForm.RemoveAll()
		}
	}()
	if err := c.Request.ParseMultipartForm(1024 * 1024); err != nil {
		ErrorEnvelope(c, 422, "VALIDATION_ERROR", "invalid multipart image (max 5MB)")
		return
	}
	f, hdr, err := c.Request.FormFile("image")
	if err != nil {
		ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "image required")
		return
	}
	defer f.Close()
	if hdr.Size > 5*1024*1024 {
		ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "image too large (max 5MB)")
		return
	}
	buf, err := io.ReadAll(io.LimitReader(f, 5*1024*1024+1))
	if err != nil || len(buf) == 0 || len(buf) > 5*1024*1024 {
		ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "read image failed")
		return
	}
	kind := http.DetectContentType(buf)
	if kind != "image/jpeg" && kind != "image/png" && kind != "image/webp" {
		ErrorEnvelope(c, 422, "VALIDATION_ERROR", "image must be JPEG, PNG or WebP")
		return
	}
	if kind != "image/webp" {
		cfg, _, err := image.DecodeConfig(bytes.NewReader(buf))
		if err != nil || cfg.Width <= 0 || cfg.Height <= 0 || int64(cfg.Width)*int64(cfg.Height) > 20_000_000 {
			ErrorEnvelope(c, 422, "VALIDATION_ERROR", "invalid image or more than 20 megapixels")
			return
		}
	}
	threshold := 0.5
	if v := c.PostForm("min_similarity"); v != "" {
		parsed, perr := strconv.ParseFloat(v, 64)
		if perr != nil || math.IsNaN(parsed) || math.IsInf(parsed, 0) || parsed < 0 || parsed > 1 {
			ErrorEnvelope(c, 422, "VALIDATION_ERROR", "min_similarity must be between 0 and 1")
			return
		}
		threshold = parsed
	}
	ctx := c.Request.Context()
	revision := ""
	if h.cache != nil {
		revision, _, _ = h.cache.Get(ctx, "feed:revision")
	}
	cacheKey := fmt.Sprintf("search:visual:%s:%x:%g", revision, sha256.Sum256(buf), threshold)
	var res domain.SearchResult
	hit := false
	if h.cache != nil {
		if value, ok, _ := h.cache.Get(ctx, cacheKey); ok {
			hit = json.Unmarshal([]byte(value), &res) == nil
		}
	}
	if !hit {
		// shortcut: filter the best 100 frames after search; move visibility into the index when private frames crowd out public hits.
		fresh, err := h.ai.Search(ctx, base64.StdEncoding.EncodeToString(buf), 100, threshold)
		if err != nil {
			handleDomainErr(c, err)
			return
		}
		res = *fresh
		if h.cache != nil {
			if value, err := json.Marshal(res); err == nil {
				_ = h.cache.Set(ctx, cacheKey, string(value), 120*time.Second)
			}
		}
	}
	results := make([]gin.H, 0)
	allowed := map[string]bool{}
	for _, hit := range res.Hits {
		if hit.SimilarityScore < threshold {
			continue
		}
		// Recheck publication on cache hits; never expose stale/deleted/draft media.
		if _, checked := allowed[hit.VideoID]; !checked {
			if _, err := h.videos.GetProcessed(ctx, hit.VideoID); err == nil {
				published, err := h.clips.ListPublishedByVideo(ctx, hit.VideoID)
				allowed[hit.VideoID] = err == nil && len(published) > 0
			} else {
				allowed[hit.VideoID] = false
			}
		}
		if !allowed[hit.VideoID] {
			continue
		}
		thumbnail := hit.ThumbnailURL
		if h.storage != nil {
			parts := strings.SplitN(thumbnail, "/", 2)
			if len(parts) != 2 || parts[0] != "thumbnails" {
				continue
			}
			var err error
			thumbnail, err = h.storage.GetPresigned(ctx, parts[0], parts[1], time.Hour)
			if err != nil {
				handleDomainErr(c, err)
				return
			}
		}
		results = append(results, gin.H{
			"video_id": hit.VideoID, "timestamp": hit.Timestamp,
			"similarity_score": hit.SimilarityScore, "thumbnail_url": thumbnail,
		})
		if len(results) == 10 {
			break
		}
	}
	c.JSON(http.StatusOK, gin.H{"results": results})
}

// GET /api/search?q= — subtitles text index + videos.title ILIKE, cache 120s
func (h *SearchHandlers) Text(c *gin.Context) {
	q := c.Query("q")
	if q == "" {
		ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "q required")
		return
	}
	cacheKey := "search:txt:" + q
	if h.cache != nil {
		if v, ok, _ := h.cache.Get(c.Request.Context(), cacheKey); ok {
			var cached gin.H
			if json.Unmarshal([]byte(v), &cached) == nil {
				c.JSON(http.StatusOK, cached)
				return
			}
		}
	}
	matches, _ := h.subs.TextSearch(c.Request.Context(), q)
	// also scan video titles (mem fallback: linear scan)
	var titleHits []gin.H
	if h.videos != nil {
		all, _, _ := h.videos.List(c.Request.Context(), nil, 1, 1000)
		for _, vv := range all {
			if containsFold(vv.Title, q) {
				titleHits = append(titleHits, gin.H{"video_id": vv.ID, "title": vv.Title})
			}
		}
	}
	items := make([]gin.H, 0, len(matches)+len(titleHits))
	for _, m := range matches {
		var title any
		if v, err := h.videos.Get(c.Request.Context(), m.VideoID); err == nil {
			title = v.Title
		}
		items = append(items, gin.H{
			"video_id": m.VideoID, "title": title,
			"timestamp": m.Timestamp, "matched_text": m.Text,
		})
	}
	for _, th := range titleHits {
		items = append(items, th)
	}
	resp := gin.H{"items": items}
	if h.cache != nil {
		if b, err := json.Marshal(resp); err == nil {
			_ = h.cache.Set(c.Request.Context(), cacheKey, string(b), 120*time.Second)
		}
	}
	c.JSON(http.StatusOK, resp)
}

func containsFold(s, sub string) bool {
	if len(sub) == 0 {
		return true
	}
	// ASCII-ish fold (vi titles mostly ascii); good enough for mem fallback
	ls := toLower(s)
	lsub := toLower(sub)
	return containsRaw(ls, lsub)
}

func toLower(s string) string {
	b := []byte(s)
	for i, c := range b {
		if c >= 'A' && c <= 'Z' {
			b[i] = c + 32
		}
	}
	return string(b)
}

func containsRaw(s, sub string) bool {
	for i := 0; i+len(sub) <= len(s); i++ {
		if s[i:i+len(sub)] == sub {
			return true
		}
	}
	return false
}
