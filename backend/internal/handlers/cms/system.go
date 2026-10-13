package cms

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"traning_ai/backend/internal/handlers"
	"traning_ai/backend/internal/ports"
)

type SystemHandlers struct {
	ai ports.AIClient
}

func NewSystemHandlers(ai ports.AIClient) *SystemHandlers {
	return &SystemHandlers{ai: ai}
}

// GET /api/cms/system/health — proxy :8001/health
func (h *SystemHandlers) Health(c *gin.Context) {
	res, err := h.ai.Health(c.Request.Context())
	if err != nil {
		handlers.ErrorEnvelope(c, http.StatusServiceUnavailable, "AI_UNAVAILABLE", err.Error())
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"gpu_vram_used": res.GpuVramUsed, "gpu_util": res.GpuUtil,
		"models_loaded": res.ModelsLoaded, "queue_depth": res.QueueDepth,
	})
}

func (h *SystemHandlers) GetSettings(c *gin.Context) {
	// T0.2 seed defaults; real DB later — return mocked masked
	c.JSON(http.StatusOK, gin.H{
		"highlight_threshold": 75, "asr_warning_threshold": 65,
		"auto_highlight_enabled": true, "auto_subtitle_enabled": true,
		"default_subtitle_lang": "vi", "ai_service_api_key": "sk-local-••••",
	})
}

func (h *SystemHandlers) UpdateSettings(c *gin.Context) {
	var req struct {
		HighlightThreshold    *int    `json:"highlight_threshold"`
		AsrWarningThreshold   *int    `json:"asr_warning_threshold"`
		AutoHighlightEnabled  *bool   `json:"auto_highlight_enabled"`
		AutoSubtitleEnabled   *bool   `json:"auto_subtitle_enabled"`
		AiServiceApiKey       *string `json:"ai_service_api_key"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		handlers.ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", err.Error())
		return
	}
	if req.HighlightThreshold != nil && (*req.HighlightThreshold < 0 || *req.HighlightThreshold > 100) {
		handlers.ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "highlight_threshold 0..100")
		return
	}
	if req.AsrWarningThreshold != nil && (*req.AsrWarningThreshold < 0 || *req.AsrWarningThreshold > 100) {
		handlers.ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "asr_warning_threshold 0..100")
		return
	}
	c.Status(http.StatusOK)
}
