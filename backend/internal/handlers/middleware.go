package handlers

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

// ErrorEnvelope trả {"error":{"code","message"}} (master plan §2.6).
func ErrorEnvelope(c *gin.Context, status int, code, message string) {
	c.JSON(status, gin.H{"error": gin.H{"code": code, "message": message}})
}

// RequireAuth (skeleton): chỉ kiểm có Bearer token, chưa verify JWT thật (Phase 2 T2.2).
// Cho phép FE code ngay; sai/thiếu → 401 đúng error envelope.
func RequireAuth() gin.HandlerFunc {
	return func(c *gin.Context) {
		auth := c.GetHeader("Authorization")
		if len(auth) < 8 || auth[:7] != "Bearer " {
			ErrorEnvelope(c, http.StatusUnauthorized, "UNAUTHORIZED", "Missing or invalid access token")
			c.Abort()
			return
		}
		c.Set("user_id", "usr_stub")
		c.Next()
	}
}

// CORS đơn giản cho dev (CMS :5173, Client :3000).
func CORS() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Authorization,Content-Type")
		if c.Request.Method == http.MethodOptions {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}
		c.Next()
	}
}

// NotFound trả error envelope cho route không khớp.
func NotFound() gin.HandlerFunc {
	return func(c *gin.Context) {
		ErrorEnvelope(c, http.StatusNotFound, "NOT_FOUND", "Route not found")
	}
}
