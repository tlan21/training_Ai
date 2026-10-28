package cms

import (
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"strings"
	"unicode"
	"unicode/utf8"

	"github.com/gin-gonic/gin"
	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/handlers"
)

func readMetadataJSON(c *gin.Context, target any) bool {
	decoder := json.NewDecoder(http.MaxBytesReader(c.Writer, c.Request.Body, 64<<10))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(target); err != nil {
		handlers.ErrorEnvelope(c, 422, "VALIDATION_ERROR", "Invalid metadata JSON")
		return false
	}
	if err := decoder.Decode(new(any)); err != io.EOF {
		handlers.ErrorEnvelope(c, 422, "VALIDATION_ERROR", "Expected one JSON object")
		return false
	}
	return true
}

func (h *VideoHandlers) UpdateMetadata(c *gin.Context) {
	var req struct {
		Title       *string   `json:"title"`
		Description *string   `json:"description"`
		Hashtags    *[]string `json:"hashtags"`
	}
	if !readMetadataJSON(c, &req) {
		return
	}
	if req.Title == nil || req.Description == nil || req.Hashtags == nil || strings.TrimSpace(*req.Title) == "" || utf8.RuneCountInString(*req.Title) > 255 || utf8.RuneCountInString(*req.Description) > 10000 || len(*req.Hashtags) > 30 {
		handlers.ErrorEnvelope(c, 422, "VALIDATION_ERROR", "title, description and hashtags must satisfy the metadata limits")
		return
	}
	seen := make(map[string]bool)
	for _, tag := range *req.Hashtags {
		valid := tag != "" && utf8.RuneCountInString(tag) <= 64 && !seen[tag]
		for _, char := range tag {
			if char != '_' && !unicode.IsLetter(char) && !unicode.IsNumber(char) {
				valid = false
			}
		}
		if !valid {
			handlers.ErrorEnvelope(c, 422, "VALIDATION_ERROR", "Hashtags must be unique plain letter/number/underscore tags, max64characters")
			return
		}
		seen[tag] = true
	}
	v, err := h.videos.UpdateMetadata(c.Request.Context(), c.Param("id"), *req.Title, *req.Description, *req.Hashtags)
	if errors.Is(err, domain.ErrVideoNotFound) {
		handlers.ErrorEnvelope(c, 404, "VIDEO_NOT_FOUND", "Video not found")
		return
	}
	if err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to save video metadata")
		return
	}
	c.JSON(http.StatusOK, toVideoDetailCMS(v))
}

func toVideoDetailCMS(v *domain.Video) gin.H {
	result := toVideoCMS(v)
	result["width"], result["height"], result["fps"], result["hashtags"] = v.Width, v.Height, v.FPS, v.Hashtags
	return result
}
