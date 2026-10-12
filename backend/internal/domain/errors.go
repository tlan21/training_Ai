package domain

import "net/http"

// DomainError → HTTP envelope {"error":{"code","message"}} (master plan §2.6).
type DomainError struct {
	Code    string
	Message string
	Status  int
}

func (e *DomainError) Error() string { return e.Code + ": " + e.Message }

func NewError(code, msg string, status int) *DomainError {
	return &DomainError{Code: code, Message: msg, Status: status}
}

var (
	ErrUnauthorized      = NewError("UNAUTHORIZED", "Missing or invalid access token", http.StatusUnauthorized)
	ErrForbidden         = NewError("FORBIDDEN", "Insufficient permissions", http.StatusForbidden)
	ErrNotFound          = NewError("NOT_FOUND", "Resource not found", http.StatusNotFound)
	ErrVideoNotFound     = NewError("VIDEO_NOT_FOUND", "Video not found", http.StatusNotFound)
	ErrClipNotFound      = NewError("CLIP_NOT_FOUND", "Clip not found", http.StatusNotFound)
	ErrClipNotReady      = NewError("CLIP_NOT_READY", "Clip not ready for publish", http.StatusConflict)
	ErrJobNotFound       = NewError("JOB_NOT_FOUND", "Job not found", http.StatusNotFound)
	ErrUserNotFound      = NewError("USER_NOT_FOUND", "User not found", http.StatusNotFound)
	ErrCategoryNotFound  = NewError("CATEGORY_NOT_FOUND", "Category not found", http.StatusNotFound)
	ErrEmailTaken        = NewError("EMAIL_TAKEN", "Email already in use", http.StatusConflict)
	ErrUsernameTaken     = NewError("USERNAME_TAKEN", "Username already in use", http.StatusConflict)
	ErrValidation        = NewError("VALIDATION_ERROR", "Validation failed", http.StatusUnprocessableEntity)
	ErrTooManyRequests   = NewError("PAYLOAD_TOO_LARGE", "Payload too large", http.StatusRequestEntityTooLarge)
	ErrAIUnavailable     = NewError("AI_UNAVAILABLE", "AI service unavailable", http.StatusServiceUnavailable)
	ErrConflict          = NewError("CONFLICT", "Conflict", http.StatusConflict)
)
