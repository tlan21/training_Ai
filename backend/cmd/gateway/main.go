package main

import (
	"context"
	"log"
	"net/http"

	"github.com/gin-gonic/gin"

	"traning_ai/backend/internal/auth"
	"traning_ai/backend/internal/config"
	"traning_ai/backend/internal/gen"
	"traning_ai/backend/internal/handlers"
	"traning_ai/backend/internal/handlers/cms"
	"traning_ai/backend/internal/mocks"
)

func main() {
	cfg := config.Load()
	jwtSvc := auth.NewJWT(cfg.JWTSecret)

	// T2.1 mocks mem — đủ chạy E2E không cần PG/Mongo thật; sau này thay bằng pg/mongo adapter theo env.
	userRepo := mocks.NewUserRepoMem()
	sessionRepo := mocks.NewSessionRepoMem()
	vectorStore := mocks.NewVectorStoreMem()
	categoryRepo := mocks.NewCategoryRepoMem()
	interactionRepo := mocks.NewInteractionRepoMem()
	videoRepo := mocks.NewVideoRepoMem()
	clipRepo := mocks.NewClipRepoMem()
	jobRepo := mocks.NewJobRepoMem()
	analysisStore := mocks.NewAnalysisStoreMem()
	subtitleStore := mocks.NewSubtitleStoreMem()
	cache := mocks.NewCacheMem()
	eventBus := mocks.NewEventBusMem()
	objectStorage := mocks.NewObjectStorageMem()
	aiClient := &mocks.AIClientMem{}

	// Seed vài category để PUT /preferences ≥3 pass ngay
	for _, name := range []string{"Bóng đá", "Thể thao", "Ca nhạc", "Tin tức", "Game", "Phim"} {
		_, _ = categoryRepo.Create(context.Background(), name)
	}

	authSvc := auth.New(userRepo, sessionRepo, jwtSvc)
	authH := handlers.NewAuthHandlers(authSvc, userRepo, vectorStore, categoryRepo, interactionRepo)
	contentH := handlers.NewContentHandlers(videoRepo, clipRepo, categoryRepo, interactionRepo, analysisStore, subtitleStore, cache, aiClient, objectStorage)
	searchH := handlers.NewSearchHandlers(videoRepo, subtitleStore, cache, aiClient)
	interH := handlers.NewInteractionHandlers(interactionRepo)

	videoCMS := cms.NewVideoHandlers(videoRepo, jobRepo, analysisStore, subtitleStore, vectorStore, cache, eventBus, objectStorage, aiClient)
	jobCMS := cms.NewJobHandlers(jobRepo, eventBus)
	clipCMS := cms.NewClipHandlers(clipRepo, videoRepo, eventBus)
	catCMS := cms.NewCategoryHandlers(categoryRepo, cache)
	userCMS := cms.NewUserHandlers(userRepo)
	sysCMS := cms.NewSystemHandlers(aiClient)

	r := gin.New()
	r.Use(gin.Recovery(), handlers.CORS())
	r.NoRoute(handlers.NotFound())

	r.GET("/healthz", func(c *gin.Context) { c.JSON(http.StatusOK, gin.H{"status": "ok"}) })
	r.GET("/openapi.json", func(c *gin.Context) {
		swagger, err := gen.GetSwagger()
		if err != nil {
			handlers.ErrorEnvelope(c, http.StatusInternalServerError, "SPEC_ERROR", err.Error())
			return
		}
		c.JSON(http.StatusOK, swagger)
	})

	api := r.Group("/api")

	// --- auth public (no JWT) ---
	api.POST("/auth/register", authH.Register)
	api.POST("/auth/login", authH.Login)
	api.POST("/auth/refresh", authH.Refresh)

	// --- protected (JWT) ---
	protected := api.Group("")
	protected.Use(handlers.RequireAuth(jwtSvc))
	protected.POST("/auth/logout", authH.Logout)
	protected.GET("/users/me", authH.GetMe)
	protected.PUT("/users/me", authH.UpdateMe)
	protected.PUT("/users/me/preferences", authH.UpdatePreferences)
	protected.GET("/users/me/history", authH.History)
	protected.GET("/users/me/likes", authH.Likes)

	// --- T2.5.1 content (real) ---
	protected.GET("/feed", contentH.Feed)
	protected.GET("/videos", contentH.ListVideos)
	protected.GET("/videos/:id", contentH.GetVideo)
	protected.GET("/videos/:id/analysis", contentH.GetVideoAnalysis)
	protected.GET("/videos/:id/subtitles", contentH.GetVideoSubtitles)
	protected.GET("/clips/:id", contentH.GetClip)
	protected.GET("/categories", contentH.ListCategories)

	// --- T2.5.2 search + interactions (real) ---
	protected.POST("/search/visual", searchH.Visual)
	protected.GET("/search", searchH.Text)
	protected.POST("/interactions", interH.Create)

	// --- T2.5.3 CMS (admin|editor) ---
	cmsGroup := protected.Group("/cms")
	cmsGroup.Use(handlers.RequireRole(string("admin"), string("editor")))
	cmsGroup.POST("/videos", videoCMS.Create)
	cmsGroup.GET("/videos", videoCMS.List)
	cmsGroup.GET("/videos/:id", videoCMS.Get)
	cmsGroup.DELETE("/videos/:id", videoCMS.Delete)
	cmsGroup.GET("/videos/:id/analysis", videoCMS.GetAnalysis)
	cmsGroup.POST("/videos/:id/summary/regenerate", videoCMS.RegenerateSummary)
	cmsGroup.PUT("/videos/:id/category", videoCMS.SetCategory)
	cmsGroup.PUT("/videos/:id/summary", videoCMS.SetSummary)
	cmsGroup.POST("/videos/:id/summary/approve", videoCMS.ApproveSummary)
	cmsGroup.PUT("/videos/:id/subtitles", videoCMS.UpdateSubtitles)

	cmsGroup.GET("/jobs", jobCMS.List)
	cmsGroup.GET("/jobs/:id", jobCMS.Get)
	cmsGroup.POST("/jobs/:id/retry", jobCMS.Retry)
	cmsGroup.POST("/jobs/:id/cancel", jobCMS.Cancel)

	cmsGroup.GET("/settings", sysCMS.GetSettings)
	cmsGroup.PUT("/settings", handlers.RequireRole(string("admin")), sysCMS.UpdateSettings)
	cmsGroup.GET("/system/health", sysCMS.Health)

	cmsGroup.POST("/clips", clipCMS.Create)
	cmsGroup.GET("/clips", clipCMS.List)
	cmsGroup.PUT("/clips/:id", clipCMS.Update)
	cmsGroup.DELETE("/clips/:id", clipCMS.Delete)
	cmsGroup.POST("/clips/:id/publish", clipCMS.Publish)

	cmsGroup.GET("/categories", catCMS.List)
	cmsGroup.POST("/categories", catCMS.Create)
	cmsGroup.PUT("/categories/:id", catCMS.Update)
	cmsGroup.DELETE("/categories/:id", catCMS.Delete)

	// cms/users — admin only (narrow)
	cmsUsers := protected.Group("/cms/users")
	cmsUsers.Use(handlers.RequireRole(string("admin")))
	cmsUsers.GET("", userCMS.List)
	cmsUsers.PUT("/:id/role", userCMS.SetRole)

	log.Printf("gateway :%s (T2.5 wired, no stubs) → AI %s", cfg.Port, cfg.AIBaseURL)
	if err := r.Run(":" + cfg.Port); err != nil {
		log.Fatal(err)
	}
}
