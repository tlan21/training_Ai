package mocks

import (
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
)

// NewAIHTTP implements AI-API v0.1 DRAFT without reading files, loading models or querying vectors.
// shortcut: media references are fixture strings, use real inference for decoding and semantic checks.
func NewAIHTTP(key string) http.Handler {
	r := gin.New()
	r.Use(gin.Recovery())
	fail := func(c *gin.Context, status int, code, message string) {
		c.AbortWithStatusJSON(status, gin.H{"error": gin.H{"code": code, "message": message}})
	}
	r.NoRoute(func(c *gin.Context) { fail(c, 404, "HTTP_ERROR", "Not found") })
	r.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{"status": "ok", "gpu_vram_used": 0, "gpu_util": 0,
			"models_loaded": []string{}, "degraded": []string{}, "queue_depth": 0,
			"device": "cpu", "stub_mode": true, "load_error": nil})
	})
	v1 := r.Group("/v1", func(c *gin.Context) {
		if key == "" || c.GetHeader("Authorization") != "Bearer "+key {
			fail(c, 401, "UNAUTHORIZED", "Missing or invalid Bearer key")
			return
		}
		c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, 32<<20)
		c.Next()
	})
	bind := func(c *gin.Context, request any) bool {
		if err := c.ShouldBindJSON(request); err != nil {
			fail(c, 422, "VALIDATION_ERROR", err.Error())
			return false
		}
		return true
	}
	response := func(object, model string) gin.H {
		return gin.H{"id": "mock_" + object, "object": object, "created": time.Now().Unix(), "model": model}
	}
	v1.POST("/vision/completions", func(c *gin.Context) {
		var req struct {
			Keyframes []string `json:"keyframes" binding:"required,min=1,dive,required"`
		}
		if !bind(c, &req) {
			return
		}
		embeddings := make([][]float32, len(req.Keyframes))
		for i := range embeddings {
			embeddings[i] = make([]float32, 256)
			embeddings[i][0] = 1
		}
		res := response("vision_completion", "primitive-vit-classifier")
		res["category_suggestion"], res["embeddings_256"] = "bong_da", embeddings
		c.JSON(200, res)
	})
	v1.POST("/asr/completions", func(c *gin.Context) {
		var req struct {
			AudioURL string `json:"audio_url" binding:"required"`
			Language string `json:"language" binding:"required,eq=vi"`
		}
		if !bind(c, &req) {
			return
		}
		res := response("asr_completion", "primitive-asr-transformer")
		res["full_transcript"] = "MOCK_ONLY: bản chép lời kiểm thử."
		res["segments"] = []gin.H{{"id": 0, "start_time": 0, "end_time": 1,
			"text": res["full_transcript"], "confidence": 0.9, "warning": nil}}
		c.JSON(200, res)
	})
	v1.POST("/highlight/completions", func(c *gin.Context) {
		var req struct {
			VideoID  string `json:"video_id" binding:"required"`
			Features struct {
				Vision [][]float32 `json:"vision_embeddings" binding:"required,min=1"`
				Audio  [][]float32 `json:"audio_spectrogram_features" binding:"required,min=1"`
			} `json:"features" binding:"required"`
		}
		if !bind(c, &req) {
			return
		}
		if len(req.Features.Vision) != len(req.Features.Audio) {
			fail(c, 503, "AI_UNAVAILABLE", "Feature lengths must match")
			return
		}
		for i, frame := range req.Features.Vision {
			if len(frame) != 256 || len(req.Features.Audio[i]) != 64 {
				fail(c, 503, "AI_UNAVAILABLE", "Expected 256-d vision and 64-d audio features")
				return
			}
		}
		scores := make([]gin.H, len(req.Features.Vision))
		for i := range scores {
			scores[i] = gin.H{"second": i, "score": 80}
		}
		res := response("highlight_completion", "primitive-seq2seq-highlighter")
		res["video_id"], res["timeline_scores"] = req.VideoID, scores
		res["recommended_clips"] = []gin.H{{"clip_id": "clp_mock", "start_time": 0,
			"end_time": len(scores), "average_score": 80}}
		c.JSON(200, res)
	})
	v1.POST("/search/completions", func(c *gin.Context) {
		req := struct {
			Image     string  `json:"image" binding:"required"`
			TopK      int     `json:"top_k" binding:"min=1,max=100"`
			Threshold float64 `json:"threshold" binding:"min=0,max=1"`
		}{TopK: 5, Threshold: 0.75}
		if !bind(c, &req) {
			return
		}
		res := response("search_completion", "primitive-siamese-vit")
		res["results"], res["query_metadata"] = []gin.H{}, gin.H{}
		c.JSON(200, res)
	})
	v1.POST("/recommendation/completions", func(c *gin.Context) {
		req := struct {
			UserID  string         `json:"user_id" binding:"required"`
			Limit   int            `json:"limit" binding:"min=1"`
			Context map[string]any `json:"context"`
		}{Limit: 10}
		if !bind(c, &req) {
			return
		}
		res := response("recommendation_completion", "primitive-two-tower-recommender")
		res["recommendations"] = []gin.H{}
		c.JSON(200, res)
	})
	v1.POST("/completions", func(c *gin.Context) {
		req := struct {
			Prompt      string  `json:"prompt" binding:"required"`
			MaxTokens   int     `json:"max_tokens" binding:"min=1"`
			Temperature float64 `json:"temperature" binding:"min=0,max=2"`
		}{MaxTokens: 150, Temperature: 0.7}
		if !bind(c, &req) {
			return
		}
		res := response("text_completion", "primitive-gpt-summarizer")
		res["choices"] = []gin.H{{"text": "MOCK_ONLY: tóm tắt kiểm thử.", "index": 0, "logprobs": nil, "finish_reason": "stop"}}
		res["usage"] = gin.H{"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
		c.JSON(200, res)
	})
	return r
}
