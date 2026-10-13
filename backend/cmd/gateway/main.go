package main

import (
	"log"
	"net/http"

	"github.com/gin-gonic/gin"

	"traning_ai/backend/internal/auth"
	"traning_ai/backend/internal/config"
	"traning_ai/backend/internal/gen"
	"traning_ai/backend/internal/handlers"
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

	// Seed vài category để PUT /preferences ≥3 pass ngay
	for _, name := range []string{"Bóng đá", "Thể thao", "Ca nhạc", "Tin tức", "Game", "Phim"} {
		_, _ = categoryRepo.Create(nil, name)
	}

	authSvc := auth.New(userRepo, sessionRepo, jwtSvc)
	authH := handlers.NewAuthHandlers(authSvc, userRepo, vectorStore, categoryRepo, interactionRepo)

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

	// --- stubs còn lại (vẫn sau JWT) ---
	handlers.RegisterStubs(protected)

	log.Printf("gateway :%s (auth wired, stubs rest) → AI %s", cfg.Port, cfg.AIBaseURL)
	if err := r.Run(":" + cfg.Port); err != nil {
		log.Fatal(err)
	}
}
