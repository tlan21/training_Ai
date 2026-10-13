package handlers

import (
	"encoding/base64"
	"encoding/json"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"

	"traning_ai/backend/internal/ports"
)

type SearchHandlers struct {
	videos ports.VideoRepository
	subs   ports.SubtitleStore
	cache  ports.Cache
	ai     ports.AIClient
}

func NewSearchHandlers(videos ports.VideoRepository, subs ports.SubtitleStore, cache ports.Cache, ai ports.AIClient) *SearchHandlers {
	return &SearchHandlers{videos: videos, subs: subs, cache: cache, ai: ai}
}

// POST /api/search/visual — multipart image ≤5MB → base64 → AI Search → filter min_similarity
func (h *SearchHandlers) Visual(c *gin.Context) {
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
	buf := make([]byte, hdr.Size)
	if _, err := f.Read(buf); err != nil {
		ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "read image failed")
		return
	}
	b64 := base64.StdEncoding.EncodeToString(buf)
	res, err := h.ai.Search(c.Request.Context(), b64, 10, 0.5)
	if err != nil {
		handleDomainErr(c, err)
		return
	}
	threshold := 0.5
	if v := c.PostForm("min_similarity"); v != "" {
		if parsed, perr := parseFloat(v); perr == nil {
			threshold = parsed
		}
	}
	results := make([]gin.H, 0)
	for _, hit := range res.Hits {
		if hit.SimilarityScore < threshold {
			continue
		}
		results = append(results, gin.H{
			"video_id": hit.VideoID, "timestamp": hit.Timestamp,
			"similarity_score": hit.SimilarityScore, "thumbnail_url": hit.ThumbnailURL,
		})
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

func parseFloat(s string) (float64, error) {
	var f float64
	_, err := parseFloatScan(s, &f)
	return f, err
}

func parseFloatScan(s string, out *float64) (int, error) {
	// small helper avoiding strconv import churn — use std
	n, err := scanFloat(s)
	if err == nil {
		*out = n
	}
	return 0, err
}

func scanFloat(s string) (float64, error) {
	// delegate to standard library via json number trick
	var v float64
	if err := json.Unmarshal([]byte(s), &v); err != nil {
		return 0, err
	}
	return v, nil
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
