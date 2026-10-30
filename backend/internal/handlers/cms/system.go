package cms

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"
	"traning_ai/backend/internal/domain"

	"github.com/gin-gonic/gin"

	"traning_ai/backend/internal/gen"
	"traning_ai/backend/internal/handlers"
	"traning_ai/backend/internal/ports"
)

type SystemHandlers struct {
	ai                ports.AIClient
	settings          ports.SettingsRepository
	metrics           ports.CMSMetricsRepository
	storage           ports.ObjectStorage
	cache             ports.Cache
	mu                sync.Mutex
	cpuTotal, cpuIdle uint64
}

func NewSystemHandlers(ai ports.AIClient, settings ports.SettingsRepository) *SystemHandlers {
	return &SystemHandlers{ai: ai, settings: settings}
}

func (h *SystemHandlers) WithOverview(metrics ports.CMSMetricsRepository, storage ports.ObjectStorage, cache ports.Cache) *SystemHandlers {
	h.metrics, h.storage, h.cache = metrics, storage, cache
	return h
}

// Each dependency reports its own availability; an AI outage must not hide CMS data.
func (h *SystemHandlers) Health(c *gin.Context) {
	month := time.Now().UTC()
	month = time.Date(month.Year(), month.Month(), 1, 0, 0, 0, 0, time.UTC)
	if value := c.Query("month"); value != "" {
		parsed, err := time.Parse("2006-01", value)
		if err != nil {
			handlers.ErrorEnvelope(c, 422, "VALIDATION_ERROR", "Invalid month")
			return
		}
		month = parsed
	}
	include, err := strconv.ParseBool(c.DefaultQuery("include_metrics", "false"))
	if err != nil {
		handlers.ErrorEnvelope(c, 422, "VALIDATION_ERROR", "Invalid include_metrics")
		return
	}
	ctx, cancel := context.WithTimeout(c.Request.Context(), 15*time.Second)
	defer cancel()
	out := gin.H{"ai_available": false, "ai_error": nil, "device": nil, "cpu_util": h.cpuUsage()}
	aiCtx, aiCancel := context.WithTimeout(ctx, 5*time.Second)
	res, err := h.ai.Health(aiCtx)
	aiCancel()
	if err != nil {
		out["ai_error"] = "AI service unavailable"
	} else {
		out["ai_available"] = !res.StubMode
		out["device"] = res.Device
		out["gpu_vram_used"] = res.GpuVramUsed
		out["gpu_util"] = res.GpuUtil
		out["models_loaded"] = res.ModelsLoaded
		out["queue_depth"] = res.QueueDepth
		if res.StubMode {
			out["ai_error"] = "AI service is running in stub mode"
		}
	}
	if include {
		out["metrics_error"], out["storage_error"] = nil, nil
		if h.metrics == nil {
			out["metrics_error"] = "CMS metrics unavailable"
		} else if m, err := h.metrics.Overview(ctx, month); err != nil {
			out["metrics_error"] = "Unable to read CMS metrics"
		} else {
			out["metrics"] = m
		}
		if usage, err := h.storageUsage(ctx); err != nil {
			out["storage_error"] = "Unable to read storage usage"
		} else {
			out["storage"] = usage
		}
	}
	c.JSON(http.StatusOK, out)
}
func (h *SystemHandlers) storageUsage(ctx context.Context) (*domain.StorageUsage, error) {
	if h.storage == nil {
		return nil, fmt.Errorf("storage unavailable")
	}
	if h.cache != nil {
		if value, ok, err := h.cache.Get(ctx, "cms:storage-usage"); err == nil && ok {
			var usage domain.StorageUsage
			if json.Unmarshal([]byte(value), &usage) == nil {
				return &usage, nil
			}
		}
	}
	usage, err := h.storage.Usage(ctx)
	if err != nil {
		return nil, err
	}
	if h.cache != nil {
		if encoded, err := json.Marshal(usage); err == nil {
			_ = h.cache.Set(ctx, "cms:storage-usage", string(encoded), 30*time.Second)
		}
	}
	return usage, nil
}
func cpuCounters(data string) (total, idle uint64, err error) {
	fields := strings.Fields(strings.SplitN(data, "\n", 2)[0])
	if len(fields) < 5 || fields[0] != "cpu" {
		return 0, 0, fmt.Errorf("invalid CPU counters")
	}
	// Linux guest counters are already included in user/nice.
	for i := 1; i < len(fields) && i <= 8; i++ {
		value, e := strconv.ParseUint(fields[i], 10, 64)
		if e != nil {
			return 0, 0, e
		}
		total += value
		if i == 4 || i == 5 {
			idle += value
		}
	}
	return total, idle, nil
}
func (h *SystemHandlers) cpuUsage() *float64 {
	data, err := os.ReadFile("/proc/stat")
	if err != nil {
		return nil
	}
	total, idle, err := cpuCounters(string(data))
	if err != nil {
		return nil
	}
	h.mu.Lock()
	defer h.mu.Unlock()
	previous, oldIdle := h.cpuTotal, h.cpuIdle
	h.cpuTotal, h.cpuIdle = total, idle
	if previous == 0 || total <= previous || idle < oldIdle || idle-oldIdle > total-previous {
		return nil
	}
	value := 100 * (1 - float64(idle-oldIdle)/float64(total-previous))
	return &value
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
		"category_suggestion_enabled": s.CategorySuggestionEnabled, "category_keyword_enabled": s.CategoryKeywordEnabled,
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
	if req.CategorySuggestionEnabled != nil {
		values["category_suggestion_enabled"] = strconv.FormatBool(*req.CategorySuggestionEnabled)
	}
	if req.CategoryKeywordEnabled != nil {
		values["category_keyword_enabled"] = strconv.FormatBool(*req.CategoryKeywordEnabled)
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
