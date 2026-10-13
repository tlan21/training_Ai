package handlers

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

// Stub handlers — trả mock ĐÚNG schema infra/openapi.yaml để FE code ngay (Phase 0 T0.3).
// T2.2: auth stubs đã thay bằng handlers.AuthHandlers thật; file này chỉ giữ content/search/interactions + CMS stubs.

func mockUser() gin.H {
	return gin.H{
		"id": "usr_stub01", "username": "admin", "email": "admin@local",
		"avatar_url": nil, "role": "admin", "created_at": "2026-07-01T00:00:00Z",
	}
}
func mockCategory() gin.H { return gin.H{"id": "cat_bongda", "name": "Bóng đá"} }
func mockVideo() gin.H {
	return gin.H{
		"id": "vid_stub01", "title": "Trận đấu mẫu", "description": "Video stub",
		"thumbnail_url": "https://storage.local/thumb/vid_stub01.jpg",
		"duration_seconds": 600.0, "status": "processed",
		"category": mockCategory(), "created_at": "2026-07-01T00:00:00Z",
	}
}
func mockClip() gin.H {
	return gin.H{
		"id": "clp_stub01", "video_id": "vid_stub01", "title": "Highlight mẫu",
		"start_time": 2.0, "end_time": 12.0, "average_score": 89.5,
		"thumbnail_url": "https://storage.local/thumb/clp_stub01.jpg",
		"playback_url": "https://storage.local/clips/clp_stub01.mp4",
		"status": "published", "created_at": "2026-07-01T00:00:00Z",
	}
}
func mockJob() gin.H {
	return gin.H{
		"id": "job_stub01", "video_id": "vid_stub01", "status": "completed",
		"current_stage": "completed", "progress": 100, "error_log": nil,
		"updated_at": "2026-07-01T00:00:00Z",
	}
}
func clipPage() gin.H  { return gin.H{"items": []gin.H{mockClip()}, "next_cursor": nil} }
func videoPage() gin.H { return gin.H{"items": []gin.H{mockVideo()}, "next_cursor": nil} }

// RegisterStubs gắn các route chưa làm thật vào group đã có RequireAuth (caller tự Use middleware).
// T2.2: không còn auth stubs; auth thật do AuthHandlers đảm nhiệm.
func RegisterStubs(protected *gin.RouterGroup) {
	// content (yêu cầu JWT — caller đã Use RequireAuth)
	protected.GET("/feed", func(c *gin.Context) { c.JSON(http.StatusOK, clipPage()) })
	protected.GET("/videos", func(c *gin.Context) { c.JSON(http.StatusOK, videoPage()) })
	protected.GET("/videos/:id", func(c *gin.Context) {
		v := mockVideo()
		v["clips"] = []gin.H{mockClip()}
		c.JSON(http.StatusOK, v)
	})
	protected.GET("/videos/:id/analysis", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"timeline_scores": []gin.H{{"second": 2, "score": 89.7}},
			"summary": "Tóm tắt stub", "key_moments": []gin.H{{"timestamp": 80.0, "text": "Bàn thắng"}},
			"hashtags": []string{"#bongda", "#highlight"},
		})
	})
	protected.GET("/videos/:id/subtitles", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"segments": []gin.H{{
			"segment_index": 0, "start_time": 0.0, "end_time": 3.5,
			"text": "Chào mừng các bạn", "confidence": 0.98, "warning": nil,
		}}})
	})
	protected.GET("/clips/:id", func(c *gin.Context) { c.JSON(http.StatusOK, mockClip()) })
	protected.GET("/categories", func(c *gin.Context) { c.JSON(http.StatusOK, []gin.H{mockCategory()}) })
	protected.POST("/search/visual", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"results": []gin.H{{
			"video_id": "vid_stub01", "timestamp": 45.2, "similarity_score": 0.76,
			"thumbnail_url": "https://storage.local/thumb/vid_stub01.jpg",
		}}})
	})
	protected.GET("/search", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"items": []gin.H{{
			"video_id": "vid_stub01", "title": "Trận đấu mẫu", "timestamp": 12.0, "matched_text": "khớp stub",
		}}})
	})
	protected.POST("/interactions", func(c *gin.Context) { c.Status(http.StatusCreated) })

	registerCMS(protected)
}

// Register — giữ compat cũ: tạo protected group với jwt=nil (stub check prefix) rồi gọi RegisterStubs.
func Register(r *gin.RouterGroup) {
	protected := r.Group("")
	protected.Use(RequireAuth(nil))
	RegisterStubs(protected)
}

func registerCMS(r *gin.RouterGroup) {
	cms := r.Group("/cms")
	cms.POST("/videos", func(c *gin.Context) {
		c.JSON(http.StatusCreated, gin.H{"video": mockVideo(), "job": mockJob()})
	})
	cms.GET("/videos", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"items": []gin.H{mockVideo()}, "total": 1, "page": 1})
	})
	cms.GET("/videos/:id", func(c *gin.Context) {
		v := mockVideo()
		v["clips"] = []gin.H{mockClip()}
		c.JSON(http.StatusOK, v)
	})
	cms.DELETE("/videos/:id", func(c *gin.Context) { c.Status(http.StatusNoContent) })
	cms.GET("/videos/:id/analysis", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"timeline_scores": []gin.H{{"second": 2, "score": 89.7}},
			"ai_generated_clips": []gin.H{{"start_time": 2.0, "end_time": 12.5, "average_score": 92.4, "reason": "peak audio"}},
			"category_suggestion": "cat_bongda", "summary": "Tóm tắt stub", "summary_status": "draft",
			"suggested_title": "Bàn thắng phút 89", "key_moments": []gin.H{{"timestamp": 80.0, "text": "Bàn thắng"}},
			"hashtags": []string{"#bongda"},
		})
	})
	cms.POST("/videos/:id/summary/regenerate", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"summary": "Tóm tắt mới", "suggested_title": "Tiêu đề mới"})
	})
	cms.PUT("/videos/:id/category", func(c *gin.Context) { c.Status(http.StatusOK) })
	cms.PUT("/videos/:id/summary", func(c *gin.Context) { c.Status(http.StatusOK) })
	cms.POST("/videos/:id/summary/approve", func(c *gin.Context) { c.Status(http.StatusOK) })
	cms.PUT("/videos/:id/subtitles", func(c *gin.Context) { c.Status(http.StatusOK) })
	cms.GET("/jobs", func(c *gin.Context) { c.JSON(http.StatusOK, []gin.H{mockJob()}) })
	cms.GET("/jobs/:id", func(c *gin.Context) { c.JSON(http.StatusOK, mockJob()) })
	cms.POST("/jobs/:id/retry", func(c *gin.Context) { c.Status(http.StatusOK) })
	cms.POST("/jobs/:id/cancel", func(c *gin.Context) { c.Status(http.StatusOK) })
	cms.GET("/settings", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"highlight_threshold": 75, "asr_warning_threshold": 65,
			"auto_highlight_enabled": true, "auto_subtitle_enabled": true,
			"default_subtitle_lang": "vi", "ai_service_api_key": "sk-local-••••",
		})
	})
	cms.PUT("/settings", func(c *gin.Context) { c.Status(http.StatusOK) })
	cms.GET("/system/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"gpu_vram_used": 0.0, "gpu_util": 0.0, "models_loaded": []string{}, "queue_depth": 0,
		})
	})
	cms.POST("/clips", func(c *gin.Context) { c.JSON(http.StatusCreated, mockClip()) })
	cms.GET("/clips", func(c *gin.Context) { c.JSON(http.StatusOK, []gin.H{mockClip()}) })
	cms.PUT("/clips/:id", func(c *gin.Context) { c.Status(http.StatusOK) })
	cms.DELETE("/clips/:id", func(c *gin.Context) { c.Status(http.StatusNoContent) })
	cms.POST("/clips/:id/publish", func(c *gin.Context) { c.Status(http.StatusOK) })
	cms.GET("/categories", func(c *gin.Context) { c.JSON(http.StatusOK, []gin.H{mockCategory()}) })
	cms.POST("/categories", func(c *gin.Context) { c.JSON(http.StatusCreated, mockCategory()) })
	cms.PUT("/categories/:id", func(c *gin.Context) { c.Status(http.StatusOK) })
	cms.DELETE("/categories/:id", func(c *gin.Context) { c.Status(http.StatusNoContent) })
	cms.GET("/users", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"items": []gin.H{mockUser()}, "total": 1, "page": 1})
	})
	cms.PUT("/users/:id/role", func(c *gin.Context) { c.JSON(http.StatusOK, mockUser()) })
}
