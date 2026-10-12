package handlers

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"traning_ai/backend/internal/domain"
)

// AuthHandlers — T2.2: register/login/refresh/logout + users/* (me, preferences, history, likes).

type AuthHandlers struct {
	authSvc    authService
	userRepo   userRepo
	sessionRepo sessionRepo
	vectorStore vectorStoreI
	categoryRepo categoryRepo
	interactionRepo interactionRepo
}

type authService interface {
	Register(ctx interface{}, username, email, password string) (*domain.User, string, string, error)
	Login(ctx interface{}, email, password string) (*domain.User, string, string, error)
	Refresh(ctx interface{}, rawRefresh string) (string, string, error)
	Logout(ctx interface{}, rawRefresh string) error
}
type userRepo interface {
	Get(ctx interface{}, id string) (*domain.User, error)
	UpdateProfile(ctx interface{}, id string, username *string) (*domain.User, error)
	List(ctx interface{}, page, size int) ([]domain.User, int, error)
	SetRole(ctx interface{}, id string, r domain.Role) (*domain.User, error)
}
type sessionRepo interface{}
type vectorStoreI interface {
	UpsertUser(ctx interface{}, userID string, vector []float32, tags []string) error
}
type categoryRepo interface {
	List(ctx interface{}) ([]domain.Category, error)
}
type interactionRepo interface {
	History(ctx interface{}, userID string, cursor *string, limit int) ([]domain.HistoryItem, *string, error)
	Likes(ctx interface{}, userID string, cursor *string, limit int) ([]domain.Clip, *string, error)
}

var _ = NewAuthHandlers // mark used; wired in cmd/gateway/main.go T2.2

func NewAuthHandlers(a authService, u userRepo, vec vectorStoreI, cat categoryRepo, inter interactionRepo) *AuthHandlers {
	return &AuthHandlers{authSvc: a, userRepo: u, vectorStore: vec, categoryRepo: cat, interactionRepo: inter}
}

func (h *AuthHandlers) Register(c *gin.Context) {
	var req struct {
		Username string `json:"username" binding:"required,min=3,max=50"`
		Email    string `json:"email" binding:"required,email"`
		Password string `json:"password" binding:"required,min=8"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", err.Error())
		return
	}
	u, access, refresh, err := h.authSvc.Register(c.Request.Context(), req.Username, req.Email, req.Password)
	if err != nil {
		handleDomainErr(c, err)
		return
	}
	c.SetCookie("refresh", refresh, 604800, "/", "", false, true)
	c.JSON(http.StatusCreated, gin.H{"user": toUserMe(u, nil), "access_token": access})
}

func (h *AuthHandlers) Login(c *gin.Context) {
	var req struct {
		Email    string `json:"email" binding:"required,email"`
		Password string `json:"password" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", err.Error())
		return
	}
	u, access, refresh, err := h.authSvc.Login(c.Request.Context(), req.Email, req.Password)
	if err != nil {
		handleDomainErr(c, err)
		return
	}
	c.SetCookie("refresh", refresh, 604800, "/", "", false, true)
	c.JSON(http.StatusOK, gin.H{"user": toUserMe(u, nil), "access_token": access})
}

func (h *AuthHandlers) Refresh(c *gin.Context) {
	raw, _ := c.Cookie("refresh")
	if raw == "" {
		ErrorEnvelope(c, http.StatusUnauthorized, "UNAUTHORIZED", "Missing refresh token")
		return
	}
	access, refresh, err := h.authSvc.Refresh(c.Request.Context(), raw)
	if err != nil {
		ErrorEnvelope(c, http.StatusUnauthorized, "UNAUTHORIZED", "Invalid refresh token")
		return
	}
	c.SetCookie("refresh", refresh, 604800, "/", "", false, true)
	c.JSON(http.StatusOK, gin.H{"access_token": access})
}

func (h *AuthHandlers) Logout(c *gin.Context) {
	raw, _ := c.Cookie("refresh")
	_ = h.authSvc.Logout(c.Request.Context(), raw)
	c.SetCookie("refresh", "", -1, "/", "", false, true)
	c.Status(http.StatusNoContent)
}

func handleDomainErr(c *gin.Context, err error) {
	if de, ok := err.(*domain.DomainError); ok {
		ErrorEnvelope(c, de.Status, de.Code, de.Message)
		return
	}
	ErrorEnvelope(c, http.StatusInternalServerError, "INTERNAL", err.Error())
}

func toUserMe(u *domain.User, prefs []string) gin.H {
	return gin.H{"id": u.ID, "username": u.Username, "email": u.Email, "role": string(u.Role), "preferences": prefs}
}
