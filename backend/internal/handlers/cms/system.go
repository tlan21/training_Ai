package cms

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"

	"traning_ai/backend/internal/gen"
	"traning_ai/backend/internal/handlers"
	"traning_ai/backend/internal/ports"
)

type SystemHandlers struct {
	ai       ports.AIClient
	settings ports.SettingsRepository
}

func NewSystemHandlers(ai ports.AIClient, settings ports.SettingsRepository) *SystemHandlers {
	return &SystemHandlers{ai: ai, settings: settings}
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
	s, err := h.settings.Get(c.Request.Context())
	if err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to read settings")
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"highlight_threshold": s.HighlightThreshold, "asr_warning_threshold": s.ASRWarningThreshold,
		"auto_highlight_enabled": s.AutoHighlightEnabled, "auto_subtitle_enabled": s.AutoSubtitleEnabled,
		"default_subtitle_lang": s.DefaultSubtitleLang, "ai_service_api_key": "sk-local-••••",
	})
}

func (h *SystemHandlers) UpdateSettings(c *gin.Context) {
	var req gen.SettingsUpdate
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
	values := map[string]string{}
	if req.HighlightThreshold != nil {
		values["highlight_threshold"] = strconv.Itoa(*req.HighlightThreshold)
	}
	if req.AsrWarningThreshold != nil {
		values["asr_warning_threshold"] = strconv.Itoa(*req.AsrWarningThreshold)
	}
	if req.AutoHighlightEnabled != nil {
		values["auto_highlight_enabled"] = strconv.FormatBool(*req.AutoHighlightEnabled)
	}
	if req.AutoSubtitleEnabled != nil {
		values["auto_subtitle_enabled"] = strconv.FormatBool(*req.AutoSubtitleEnabled)
	}
	if req.AiServiceApiKey != nil && *req.AiServiceApiKey != "sk-local-••••" {
		values["ai_service_api_key"] = *req.AiServiceApiKey
	}
	if err := h.settings.Update(c.Request.Context(), values); err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to save settings")
		return
	}
	c.Status(http.StatusOK)
}
