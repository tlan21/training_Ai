package cms

import (
	"errors"
	"net/http"
	"strings"
	"unicode/utf8"

	"github.com/gin-gonic/gin"

	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/gen"
	"traning_ai/backend/internal/handlers"
	"traning_ai/backend/internal/ports"
)

type CategoryHandlers struct {
	cats  ports.CategoryRepository
	cache ports.Cache
}

func NewCategoryHandlers(cats ports.CategoryRepository, cache ports.Cache) *CategoryHandlers {
	return &CategoryHandlers{cats: cats, cache: cache}
}

func (h *CategoryHandlers) List(c *gin.Context) {
	items, err := h.cats.List(c.Request.Context())
	if err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to load categories")
		return
	}
	out := make([]gin.H, 0, len(items))
	for _, cc := range items {
		out = append(out, categoryDTO(&cc))
	}
	c.JSON(http.StatusOK, out)
}

func (h *CategoryHandlers) Create(c *gin.Context) {
	var req gen.CategoryWrite
	if !readCategory(c, &req) {
		return
	}
	cc, err := h.cats.Create(c.Request.Context(), req.Name, req.Description, categoryKeywords(req))
	if err != nil {
		categoryError(c, err)
		return
	}
	if h.cache != nil {
		_ = h.cache.Delete(c.Request.Context(), "categories:all")
	}
	c.JSON(http.StatusCreated, categoryDTO(cc))
}

func (h *CategoryHandlers) Update(c *gin.Context) {
	id := c.Param("id")
	var req gen.CategoryWrite
	if !readCategory(c, &req) {
		return
	}
	cc, err := h.cats.Update(c.Request.Context(), id, req.Name, req.Description, categoryKeywords(req))
	if err != nil {
		categoryError(c, err)
		return
	}
	if h.cache != nil {
		_ = h.cache.Delete(c.Request.Context(), "categories:all")
	}
	c.JSON(http.StatusOK, categoryDTO(cc))
}

func categoryError(c *gin.Context, err error) {
	if errors.Is(err, domain.ErrCategoryNotFound) {
		handlers.ErrorEnvelope(c, 404, "CATEGORY_NOT_FOUND", "Category not found")
	} else if errors.Is(err, domain.ErrConflict) {
		handlers.ErrorEnvelope(c, 409, "CONFLICT", "Category name already exists")
	} else {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to save category")
	}
}

func readCategory(c *gin.Context, req *gen.CategoryWrite) bool {
	if !readMetadataJSON(c, req) {
		return false
	}
	if strings.TrimSpace(req.Name) == "" || utf8.RuneCountInString(req.Name) > 100 || (req.Description != nil && utf8.RuneCountInString(*req.Description) > 2000) {
		handlers.ErrorEnvelope(c, 422, "VALIDATION_ERROR", "Category name/description exceeds limits or name is blank")
		return false
	}
	if req.Keywords != nil {
		if len(*req.Keywords) > 20 {
			handlers.ErrorEnvelope(c, 422, "VALIDATION_ERROR", "At most 20 keywords")
			return false
		}
		seen := map[string]bool{}
		for i, keyword := range *req.Keywords {
			keyword = strings.TrimSpace(keyword)
			key := strings.ToLower(keyword)
			if keyword == "" || utf8.RuneCountInString(keyword) > 100 || seen[key] {
				handlers.ErrorEnvelope(c, 422, "VALIDATION_ERROR", "Keywords must be nonblank, unique and at most100characters")
				return false
			}
			seen[key] = true
			(*req.Keywords)[i] = keyword
		}
	}
	return true
}

func (h *CategoryHandlers) Delete(c *gin.Context) {
	id := c.Param("id")
	if err := h.cats.Delete(c.Request.Context(), id); err != nil {
		if errors.Is(err, domain.ErrConflict) {
			handlers.ErrorEnvelope(c, 409, "CONFLICT", "Category is still used by videos, clips or user preferences")
		} else {
			categoryError(c, err)
		}
		return
	}
	if h.cache != nil {
		_ = h.cache.Delete(c.Request.Context(), "categories:all")
	}
	c.Status(http.StatusNoContent)
}

func categoryKeywords(req gen.CategoryWrite) []string {
	if req.Keywords == nil {
		return nil
	}
	return append([]string{}, (*req.Keywords)...)
}
func categoryDTO(c *domain.Category) gin.H {
	return gin.H{"id": c.ID, "name": c.Name, "description": c.Description, "keywords": append([]string{}, c.Keywords...), "video_count": c.VideoCount}
}
