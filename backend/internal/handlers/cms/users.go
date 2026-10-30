package cms

import (
	"net/http"
	"strconv"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/gin-gonic/gin"

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
	query := strings.TrimSpace(c.Query("q"))
	if utf8.RuneCountInString(query) > 200 {
		handlers.ErrorEnvelope(c, 422, "VALIDATION_ERROR", "Search is limited to 200 characters")
		return
	}
	items, total, err := h.users.List(c.Request.Context(), page, size, query)
	if err != nil {
		handlers.ErrorEnvelope(c, 500, "INTERNAL", "Unable to read users")
		return
	}
	out := make([]gin.H, 0, len(items))
	for i := range items {
		out = append(out, gin.H{"id": items[i].ID, "username": items[i].Username, "email": items[i].Email, "created_at": items[i].CreatedAt.UTC().Format(time.RFC3339)})
	}
	c.JSON(http.StatusOK, gin.H{"items": out, "total": total, "page": page})
}
