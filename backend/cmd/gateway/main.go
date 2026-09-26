// gateway — Gin router :8000, prefix /api (master plan §1). Phase 0 T0.3: trả stub đúng
// OpenAPI để FE code ngay; Phase 2 thay handler bằng use-case + DB thật.
package main

import (
	"log"
	"net/http"

	"github.com/gin-gonic/gin"

	"traning_ai/backend/internal/config"
	"traning_ai/backend/internal/gen"
	"traning_ai/backend/internal/handlers"
)

func main() {
	cfg := config.Load()

	r := gin.New()
	r.Use(gin.Recovery(), handlers.CORS())
	r.NoRoute(handlers.NotFound())

	// health gateway (khác /api/cms/system/health proxy AI)
	r.GET("/healthz", func(c *gin.Context) { c.JSON(http.StatusOK, gin.H{"status": "ok"}) })

	// serve embedded OpenAPI spec (nguồn: infra/openapi.yaml)
	r.GET("/openapi.json", func(c *gin.Context) {
		swagger, err := gen.GetSwagger()
		if err != nil {
			handlers.ErrorEnvelope(c, http.StatusInternalServerError, "SPEC_ERROR", err.Error())
			return
		}
		c.JSON(http.StatusOK, swagger)
	})

	api := r.Group("/api")
	handlers.Register(api)

	log.Printf("gateway :%s (stub) → AI %s", cfg.Port, cfg.AIBaseURL)
	if err := r.Run(":" + cfg.Port); err != nil {
		log.Fatal(err)
	}
}
