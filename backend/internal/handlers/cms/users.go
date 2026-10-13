package cms

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"

	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/handlers"
	"traning_ai/backend/internal/ports"
)

type UserHandlers struct {
	users ports.UserRepository
}

func NewUserHandlers(users ports.UserRepository) *UserHandlers {
	return &UserHandlers{users: users}
}

func (h *UserHandlers) List(c *gin.Context) {
	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	if page < 1 {
		page = 1
	}
	const size = 20
	items, total, _ := h.users.List(c.Request.Context(), page, size)
	out := make([]gin.H, 0, len(items))
	for i := range items {
		out = append(out, gin.H{"id": items[i].ID, "username": items[i].Username, "email": items[i].Email, "role": string(items[i].Role)})
	}
	c.JSON(http.StatusOK, gin.H{"items": out, "total": total, "page": page})
}

func (h *UserHandlers) SetRole(c *gin.Context) {
	id := c.Param("id")
	var req struct {
		Role string `json:"role" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		handlers.ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", err.Error())
		return
	}
	if req.Role != string(domain.RoleAdmin) && req.Role != string(domain.RoleEditor) && req.Role != string(domain.RoleClient) {
		handlers.ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "invalid role")
		return
	}
	u, err := h.users.SetRole(c.Request.Context(), id, domain.Role(req.Role))
	if err != nil {
		handlers.ErrorEnvelope(c, http.StatusNotFound, "USER_NOT_FOUND", err.Error())
		return
	}
	c.JSON(http.StatusOK, gin.H{"id": u.ID, "username": u.Username, "email": u.Email, "role": string(u.Role)})
}
