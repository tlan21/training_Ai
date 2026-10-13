package handlers

import (
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"

	"traning_ai/backend/internal/auth"
)

// ErrorEnvelope trả {"error":{"code","message"}} (master plan §2.6).
func ErrorEnvelope(c *gin.Context, status int, code, message string) {
	c.JSON(status, gin.H{"error": gin.H{"code": code, "message": message}})
}

// RequireAuth — T2.2: verify JWT HS256 nếu có *auth.JWT, else chỉ check prefix (stub).
func RequireAuth(jv *auth.JWT) gin.HandlerFunc {
	return func(c *gin.Context) {
		h := c.GetHeader("Authorization")
		if h == "" || !strings.HasPrefix(h, "Bearer ") {
			ErrorEnvelope(c, http.StatusUnauthorized, "UNAUTHORIZED", "Missing or invalid access token")
			c.Abort()
			return
		}
		token := strings.TrimPrefix(h, "Bearer ")
		if token == "" {
			ErrorEnvelope(c, http.StatusUnauthorized, "UNAUTHORIZED", "Missing or invalid access token")
			c.Abort()
			return
		}
		if jv != nil {
			claims, err := jv.Verify(token)
			if err != nil {
				ErrorEnvelope(c, http.StatusUnauthorized, "UNAUTHORIZED", "Invalid or expired access token")
				c.Abort()
				return
			}
			c.Set("user_id", claims.UserID)
			c.Set("user_role", claims.Role)
		} else {
			c.Set("user_id", "usr_stub")
		}
		c.Next()
	}
}

// RequireRole — T2.2.4 CMS admin/editor check.
func RequireRole(allowed ...string) gin.HandlerFunc {
	return func(c *gin.Context) {
		role, _ := c.Get("user_role")
		rs, _ := role.(string)
		for _, a := range allowed {
			if rs == a {
				c.Next()
				return
			}
		}
		ErrorEnvelope(c, http.StatusForbidden, "FORBIDDEN", "Insufficient permissions")
		c.Abort()
	}
}

// CORS cho dev — hỗ trợ withCredentials (refresh cookie).
// Khi có Origin (browser) thì echo lại Origin đó + Allow-Credentials, không dùng *.
func CORS() gin.HandlerFunc {
	return func(c *gin.Context) {
		origin := c.GetHeader("Origin")
		if origin != "" {
			c.Header("Access-Control-Allow-Origin", origin)
			c.Header("Access-Control-Allow-Credentials", "true")
			c.Header("Vary", "Origin")
		} else {
			c.Header("Access-Control-Allow-Origin", "*")
		}
		c.Header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Authorization,Content-Type")
		c.Header("Access-Control-Expose-Headers", "Set-Cookie")
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
