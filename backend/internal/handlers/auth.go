package handlers

import (
	"context"
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"

	"traning_ai/backend/internal/domain"
	"traning_ai/backend/internal/ports"
)

// AuthHandlers — T2.2: register/login/refresh/logout + users/* (me, preferences, history, likes).

type AuthHandlers struct {
	authSvc         authService
	userRepo        userRepo
	vectorStore     vectorStoreI
	categoryRepo    categoryRepo
	interactionRepo interactionRepo
	storage         ports.ObjectStorage
}

type authService interface {
	Register(ctx context.Context, username, email, password string) (*domain.User, string, string, error)
	Login(ctx context.Context, email, password string) (*domain.User, string, string, error)
	Refresh(ctx context.Context, rawRefresh string) (string, string, error)
	Logout(ctx context.Context, rawRefresh string) error
	ForgotPassword(ctx context.Context, email string) (string, error)
	ResetPassword(ctx context.Context, token, newPassword string) error
}
type userRepo interface {
	Get(ctx context.Context, id string) (*domain.User, error)
	UpdateProfile(ctx context.Context, id string, username *string) (*domain.User, error)
	List(ctx context.Context, page, size int) ([]domain.User, int, error)
	SetRole(ctx context.Context, id string, r domain.Role) (*domain.User, error)
}
type vectorStoreI interface {
	UpsertUser(ctx context.Context, userID string, vector []float32, tags []string) error
}
type categoryRepo interface {
	List(ctx context.Context) ([]domain.Category, error)
}
type interactionRepo interface {
	History(ctx context.Context, userID string, cursor *string, limit int) ([]domain.HistoryItem, *string, error)
	Likes(ctx context.Context, userID string, cursor *string, limit int) ([]domain.Clip, *string, error)
}

func NewAuthHandlers(a authService, u userRepo, vec vectorStoreI, cat categoryRepo, inter interactionRepo, storage ports.ObjectStorage) *AuthHandlers {
	return &AuthHandlers{authSvc: a, userRepo: u, vectorStore: vec, categoryRepo: cat, interactionRepo: inter, storage: storage}
}

func (h *AuthHandlers) Register(c *gin.Context) {
	var req struct {
		Username string `json:"username" binding:"required,min=3,max=50"`
		Email    string `json:"email" binding:"required"`
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
		Email    string `json:"email" binding:"required"`
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

func (h *AuthHandlers) ForgotPassword(c *gin.Context) {
	var req struct {
		Email string `json:"email" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", err.Error())
		return
	}
	token, err := h.authSvc.ForgotPassword(c.Request.Context(), req.Email)
	if err != nil {
		handleDomainErr(c, err)
		return
	}
	resp := gin.H{"message": "Nếu email tồn tại, mã đặt lại đã được tạo"}
	if token != "" {
		resp["reset_token"] = token
	}
	c.JSON(http.StatusOK, resp)
}

func (h *AuthHandlers) ResetPassword(c *gin.Context) {
	var req struct {
		Token       string `json:"token" binding:"required"`
		NewPassword string `json:"new_password" binding:"required,min=8"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		ErrorEnvelope(c, http.StatusBadRequest, "VALIDATION_ERROR", err.Error())
		return
	}
	if err := h.authSvc.ResetPassword(c.Request.Context(), req.Token, req.NewPassword); err != nil {
		handleDomainErr(c, err)
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "Đã đặt lại mật khẩu"})
}

func (h *AuthHandlers) GetMe(c *gin.Context) {
	uid := c.GetString("user_id")
	u, err := h.userRepo.Get(c.Request.Context(), uid)
	if err != nil {
		handleDomainErr(c, err)
		return
	}
	c.JSON(http.StatusOK, toUserMe(u, []string{}))
}

func (h *AuthHandlers) UpdateMe(c *gin.Context) {
	uid := c.GetString("user_id")
	var req struct {
		Username *string `json:"username"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", err.Error())
		return
	}
	u, err := h.userRepo.UpdateProfile(c.Request.Context(), uid, req.Username)
	if err != nil {
		handleDomainErr(c, err)
		return
	}
	c.JSON(http.StatusOK, toUserMe(u, []string{}))
}

func (h *AuthHandlers) UpdatePreferences(c *gin.Context) {
	var req struct {
		CategoryIDs []string `json:"category_ids" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", err.Error())
		return
	}
	if len(req.CategoryIDs) < 3 {
		ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "category_ids must have at least 3 items")
		return
	}
	cats, err := h.categoryRepo.List(c.Request.Context())
	if err != nil {
		handleDomainErr(c, err)
		return
	}
	catSet := map[string]bool{}
	for _, cc := range cats {
		catSet[cc.ID] = true
		catSet[cc.Name] = true
	}
	for _, id := range req.CategoryIDs {
		if !catSet[id] {
			ErrorEnvelope(c, http.StatusUnprocessableEntity, "VALIDATION_ERROR", "unknown category: "+id)
			return
		}
	}
	uid := c.GetString("user_id")
	vec := make([]float32, 128)
	_ = h.vectorStore.UpsertUser(c.Request.Context(), uid, vec, req.CategoryIDs)
	c.Status(http.StatusOK)
}

func (h *AuthHandlers) History(c *gin.Context) {
	uid := c.GetString("user_id")
	limit := parseLimit(c.Query("limit"), 10)
	cursor := strPtr(c.Query("cursor"))
	if c.Query("cursor") == "" {
		cursor = nil
	}
	items, next, err := h.interactionRepo.History(c.Request.Context(), uid, cursor, limit)
	if err != nil {
		handleDomainErr(c, err)
		return
	}
	result := make([]gin.H, 0, len(items))
	for _, item := range items {
		result = append(result, gin.H{"clip": toClipH(&item.Clip, h.storage), "watched_at": item.WatchedAt.UTC(), "duration_watched": item.DurationWatched})
	}
	c.JSON(http.StatusOK, gin.H{"items": result, "next_cursor": next})
}

func (h *AuthHandlers) Likes(c *gin.Context) {
	uid := c.GetString("user_id")
	limit := parseLimit(c.Query("limit"), 10)
	cursor := strPtr(c.Query("cursor"))
	if c.Query("cursor") == "" {
		cursor = nil
	}
	items, next, err := h.interactionRepo.Likes(c.Request.Context(), uid, cursor, limit)
	if err != nil {
		handleDomainErr(c, err)
		return
	}
	result := make([]gin.H, 0, len(items))
	for _, clip := range items {
		result = append(result, toClipH(&clip, h.storage))
	}
	c.JSON(http.StatusOK, gin.H{"items": result, "next_cursor": next})
}

func handleDomainErr(c *gin.Context, err error) {
	if de, ok := err.(*domain.DomainError); ok {
		ErrorEnvelope(c, de.Status, de.Code, de.Message)
		return
	}
	ErrorEnvelope(c, http.StatusInternalServerError, "INTERNAL", err.Error())
}

func toUserMe(u *domain.User, prefs []string) gin.H {
	if prefs == nil {
		prefs = []string{}
	}
	return gin.H{"id": u.ID, "username": u.Username, "email": u.Email, "role": string(u.Role), "preferences": prefs}
}

func parseLimit(s string, def int) int {
	if s == "" {
		return def
	}
	n, err := strconv.Atoi(s)
	if err != nil || n <= 0 {
		return def
	}
	if n > 50 {
		return 50
	}
	return n
}

func strPtr(s string) *string { return &s }
