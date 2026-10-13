package cms

import (
	"net/http"

	"github.com/gin-gonic/gin"

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
	items, _ := h.cats.List(c.Request.Context())
	out := make([]gin.H, 0, len(items))
	for _, cc := range items {
		out = append(out, gin.H{"id": cc.ID, "name": cc.Name})
	}
	c.JSON(http.StatusOK, out)
}

func (h *CategoryHandlers) Create(c *gin.Context) {
	var req struct {
		Name string `json:"name" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		handlers.ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", err.Error())
		return
	}
	cc, err := h.cats.Create(c.Request.Context(), req.Name)
	if err != nil {
		handlers.ErrorEnvelope(c, http.StatusConflict, "CONFLICT", err.Error())
		return
	}
	if h.cache != nil {
		_ = h.cache.Delete(c.Request.Context(), "categories:all")
	}
	c.JSON(http.StatusCreated, gin.H{"id": cc.ID, "name": cc.Name})
}

func (h *CategoryHandlers) Update(c *gin.Context) {
	id := c.Param("id")
	var req struct {
		Name string `json:"name" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		handlers.ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", err.Error())
		return
	}
	cc, err := h.cats.Update(c.Request.Context(), id, req.Name)
	if err != nil {
		handlers.ErrorEnvelope(c, http.StatusNotFound, "CATEGORY_NOT_FOUND", err.Error())
		return
	}
	if h.cache != nil {
		_ = h.cache.Delete(c.Request.Context(), "categories:all")
	}
	c.JSON(http.StatusOK, gin.H{"id": cc.ID, "name": cc.Name})
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
