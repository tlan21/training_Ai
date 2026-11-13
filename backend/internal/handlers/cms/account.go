package cms

import (
	"context"
	"errors"
	"net/http"

	"github.com/gin-gonic/gin"

	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/gen"
	"traning_ai/backend/internal/handlers"
)

// INT-59: own-account security for every CMS account, password reset by admin. No role/lock/delete.
type accountService interface {
	ChangePassword(ctx context.Context, userID, rawRefresh, current, next string) error
	AdminResetPassword(ctx context.Context, actorID, targetID, next string) error
	RevokeOtherSessions(ctx context.Context, userID, rawRefresh string) (int, error)
}

type AccountHandlers struct{ svc accountService }

func NewAccountHandlers(svc accountService) *AccountHandlers { return &AccountHandlers{svc: svc} }

func accountError(c *gin.Context, err error) {
	var de *domain.DomainError
	if errors.As(err, &de) {
		handlers.ErrorEnvelope(c, de.Status, de.Code, de.Message)
		return
	}
	handlers.ErrorEnvelope(c, http.StatusInternalServerError, "INTERNAL", "Unable to update account")
}

func (h *AccountHandlers) ChangePassword(c *gin.Context) {
	var req gen.ChangePasswordRequest
	if err := c.ShouldBindJSON(&req); err != nil || req.CurrentPassword == "" {
		handlers.ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "current_password and new_password are required")
		return
	}
	raw, _ := c.Cookie(handlers.RefreshCookie(c))
	if err := h.svc.ChangePassword(c.Request.Context(), c.GetString("user_id"), raw, req.CurrentPassword, req.NewPassword); err != nil {
		accountError(c, err)
		return
	}
	c.Status(http.StatusNoContent)
}

func (h *AccountHandlers) RevokeOtherSessions(c *gin.Context) {
	raw, _ := c.Cookie(handlers.RefreshCookie(c))
	n, err := h.svc.RevokeOtherSessions(c.Request.Context(), c.GetString("user_id"), raw)
	if err != nil {
		accountError(c, err)
		return
	}
	c.JSON(http.StatusOK, gin.H{"revoked": n})
}

// ResetUserPassword is mounted behind RequireRole("admin").
func (h *AccountHandlers) ResetUserPassword(c *gin.Context) {
	var req gen.AdminPasswordReset
	if err := c.ShouldBindJSON(&req); err != nil || req.NewPassword == "" {
		handlers.ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "new_password is required")
		return
	}
	if err := h.svc.AdminResetPassword(c.Request.Context(), c.GetString("user_id"), c.Param("id"), req.NewPassword); err != nil {
		accountError(c, err)
		return
	}
	c.Status(http.StatusNoContent)
}
