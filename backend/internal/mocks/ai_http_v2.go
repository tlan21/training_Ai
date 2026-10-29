package mocks

import (
	"encoding/base64"
	"github.com/gin-gonic/gin"
	"io"
	"math"
	"net/http"
	"strconv"
	"strings"
	"time"
	"traning_ai/backend/internal/domain"
)

// MOCK_ONLY: validates transport and shape, not media semantics or model quality.
func registerV2(r *gin.Engine, key string) {
	fail := func(c *gin.Context, status int, code, msg string) {
		c.AbortWithStatusJSON(status, gin.H{"error": gin.H{"code": code, "message": msg}})
	}
	v2 := r.Group("/v2", func(c *gin.Context) {
		if key == "" || c.GetHeader("Authorization") != "Bearer "+key {
			fail(c, 401, "UNAUTHORIZED", "Missing or invalid Bearer key")
			return
		}
		c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, 65<<20)
		c.Next()
	})
	bind := func(c *gin.Context, v any) bool {
		if err := c.ShouldBindJSON(v); err != nil {
			fail(c, 422, "VALIDATION_ERROR", err.Error())
			return false
		}
		return true
	}
	imageOK := func(s string) bool {
		if strings.HasPrefix(s, "data:") {
			_, s, _ = strings.Cut(s, ",")
		}
		b, err := base64.StdEncoding.DecodeString(s)
		return err == nil && len(b) > 0
	}
	vector := func(dim int) []float32 { v := make([]float32, dim); v[0] = 1; return v }
	response := func(object, model string) gin.H {
		return gin.H{"id": "mock_" + object, "object": object, "model": model, "created": time.Now().Unix()}
	}
	v2.POST("/vision/completions", func(c *gin.Context) {
		var req struct {
			Keyframes []string `json:"keyframes" binding:"required,min=1,max=600"`
		}
		if !bind(c, &req) {
			return
		}
		emb, vec := make([][]float32, len(req.Keyframes)), make([][]float32, len(req.Keyframes))
		for i, s := range req.Keyframes {
			if !imageOK(s) {
				fail(c, 422, "VALIDATION_ERROR", "Expected base64 image")
				return
			}
			emb[i], vec[i] = vector(256), vector(128)
		}
		res := response("vision_completion", "primitive-vit-classifier")
		res["category_suggestion"] = "bong_da"
		res["category_logit_sums"] = map[string]float64{"bong_da": float64(len(emb)), "ca_nhac": 0, "the_thao": 0, "tin_tuc": 0}
		res["embeddings_256"], res["siamese_vectors"] = emb, vec
		c.JSON(200, res)
	})
	v2.POST("/search/embeddings", func(c *gin.Context) {
		var req struct {
			Image string `json:"image" binding:"required"`
		}
		if !bind(c, &req) {
			return
		}
		if !imageOK(req.Image) {
			fail(c, 422, "VALIDATION_ERROR", "Expected base64 image")
			return
		}
		res := response("search_embedding", "primitive-siamese-vit")
		res["vector"], res["dim"], res["metric"], res["normalized"] = vector(128), 128, "COSINE", true
		c.JSON(200, res)
	})
	v2.POST("/asr/completions", func(c *gin.Context) {
		if err := c.Request.ParseMultipartForm(1 << 20); err != nil {
			fail(c, 422, "VALIDATION_ERROR", "Invalid multipart")
			return
		}
		defer c.Request.MultipartForm.RemoveAll()
		file, head, err := c.Request.FormFile("file")
		if err != nil {
			fail(c, 422, "VALIDATION_ERROR", "file required")
			return
		}
		defer file.Close()
		if head.Size > 64<<20 {
			fail(c, 413, "PAYLOAD_TOO_LARGE", "Audio too large")
			return
		}
		offset := 0.0
		if value := c.PostForm("offset_seconds"); value != "" {
			offset, err = strconv.ParseFloat(value, 64)
		}
		b, _ := io.ReadAll(io.LimitReader(file, 16))
		if err != nil || offset < 0 || math.IsNaN(offset) || math.IsInf(offset, 0) || c.DefaultPostForm("language", "vi") != "vi" || len(b) == 0 {
			fail(c, 422, "VALIDATION_ERROR", "Invalid audio/language/offset")
			return
		}
		res := response("asr_completion", "primitive-asr-transformer")
		res["full_transcript"] = "MOCK_ONLY: bản chép lời kiểm thử."
		res["segments"] = []gin.H{{"id": 0, "start_time": offset, "end_time": offset + 1, "text": res["full_transcript"], "confidence": 0.9, "warning": nil}}
		c.JSON(200, res)
	})
	v2.POST("/recommendation/embeddings", func(c *gin.Context) {
		var req domain.RecommendationFeatures
		if !bind(c, &req) {
			return
		}
		if len(req.Videos) > 1000 || len(req.Users) > 1000 {
			fail(c, 422, "VALIDATION_ERROR", "Too many features")
			return
		}
		ids := map[string]bool{}
		for _, v := range req.Videos {
			if v.VideoID == "" || (v.ContentEmbedding256 != nil && len(v.ContentEmbedding256) != 256) || v.PositiveCount < 0 {
				fail(c, 422, "VALIDATION_ERROR", "Invalid video features")
				return
			}
			ids[v.VideoID] = true
		}
		for _, u := range req.Users {
			if u.UserID == "" {
				fail(c, 422, "VALIDATION_ERROR", "user_id required")
				return
			}
			for _, id := range u.PositiveVideoIDs {
				if !ids[id] {
					fail(c, 422, "VALIDATION_ERROR", "Positive video missing")
					return
				}
			}
		}
		res := response("recommendation_embeddings", "primitive-two-tower-recommender")
		res["feature_version"], res["dim"], res["metric"], res["normalized"] = "ttv2-features-v1", 128, "IP", true
		videos, users := []gin.H{}, []gin.H{}
		for _, v := range req.Videos {
			videos = append(videos, gin.H{"video_id": v.VideoID, "vector": vector(128)})
		}
		for _, u := range req.Users {
			users = append(users, gin.H{"user_id": u.UserID, "vector": vector(128)})
		}
		res["videos"], res["users"] = videos, users
		c.JSON(200, res)
	})
}
