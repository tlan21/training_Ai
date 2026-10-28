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
		out = append(out, gin.H{"id": cc.ID, "name": cc.Name, "description": cc.Description})
	}
	c.JSON(http.StatusOK, out)
}

func (h *CategoryHandlers) Create(c *gin.Context) {
	var req gen.CategoryWrite
	if !readCategory(c, &req) {
		return
	}
	cc, err := h.cats.Create(c.Request.Context(), req.Name, req.Description)
	if err != nil {
		categoryError(c, err)
		return
	}
	if h.cache != nil {
		_ = h.cache.Delete(c.Request.Context(), "categories:all")
	}
	c.JSON(http.StatusCreated, gin.H{"id": cc.ID, "name": cc.Name, "description": cc.Description})
}

func (h *CategoryHandlers) Update(c *gin.Context) {
	id := c.Param("id")
	var req gen.CategoryWrite
	if !readCategory(c, &req) {
		return
	}
	cc, err := h.cats.Update(c.Request.Context(), id, req.Name, req.Description)
	if err != nil {
		categoryError(c, err)
		return
	}
	if h.cache != nil {
		_ = h.cache.Delete(c.Request.Context(), "categories:all")
	}
	c.JSON(http.StatusOK, gin.H{"id": cc.ID, "name": cc.Name, "description": cc.Description})
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
	return true
}

func (h *CategoryHandlers) Delete(c *gin.Context) {
	id := c.Param("id")
	if err := h.cats.Delete(c.Request.Context(), id); err != nil {
		handlers.ErrorEnvelope(c, http.StatusNotFound, "CATEGORY_NOT_FOUND", err.Error())
		return
	}
	if h.cache != nil {
		_ = h.cache.Delete(c.Request.Context(), "categories:all")
	}
	c.Status(http.StatusNoContent)
}
