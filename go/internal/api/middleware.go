package api

import (
	"log"
	"net/http"
	"runtime/debug"
	"strings"

	"github.com/gin-gonic/gin"
)

// CORSConfig holds the configuration for the CORS middleware.
type CORSConfig struct {
	// AllowedOrigins is the list of origins that are allowed to make requests.
	// Use "*" to allow all origins (not recommended for production).
	AllowedOrigins []string
}

// DefaultCORSConfig returns a CORSConfig suitable for local development,
// allowing common localhost origins.
func DefaultCORSConfig() CORSConfig {
	return CORSConfig{
		AllowedOrigins: []string{
			"http://localhost:3000",
			"http://localhost:5173",
			"http://127.0.0.1:3000",
			"http://127.0.0.1:5173",
		},
	}
}

// CORSMiddleware returns a Gin middleware that handles Cross-Origin Resource
// Sharing. It sets the appropriate headers and responds to preflight OPTIONS
// requests.
func CORSMiddleware(cfg CORSConfig) gin.HandlerFunc {
	allowed := make(map[string]struct{}, len(cfg.AllowedOrigins))
	allowAll := false
	for _, o := range cfg.AllowedOrigins {
		if o == "*" {
			allowAll = true
		}
		allowed[o] = struct{}{}
	}

	return func(c *gin.Context) {
		origin := c.GetHeader("Origin")

		if allowAll {
			c.Header("Access-Control-Allow-Origin", "*")
		} else if _, ok := allowed[origin]; ok {
			c.Header("Access-Control-Allow-Origin", origin)
			c.Header("Vary", "Origin")
		}

		c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Content-Type, Authorization")
		c.Header("Access-Control-Max-Age", "86400")

		// Handle preflight requests.
		if c.Request.Method == http.MethodOptions {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}

		c.Next()
	}
}

// ErrorMiddleware returns a Gin middleware that recovers from panics and
// formats any accumulated Gin errors into a consistent ErrorResponse JSON
// payload. It should be registered before route handlers.
func ErrorMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		defer func() {
			if r := recover(); r != nil {
				log.Printf("panic recovered: %v\n%s", r, debug.Stack())
				c.AbortWithStatusJSON(http.StatusInternalServerError, ErrorResponse{
					Code:    http.StatusInternalServerError,
					Message: "内部服务错误",
				})
			}
		}()

		c.Next()

		// If handlers added errors via c.Error(), format the last one.
		if len(c.Errors) > 0 {
			lastErr := c.Errors.Last()
			// Determine status code: use the already-written status if it
			// indicates an error, otherwise default to 500.
			status := c.Writer.Status()
			if status < 400 {
				status = http.StatusInternalServerError
			}

			msg := lastErr.Error()
			detail := ""
			// If the error string contains a colon, split into message and detail.
			if idx := strings.Index(msg, ": "); idx > 0 {
				detail = msg[idx+2:]
				msg = msg[:idx]
			}

			c.JSON(status, ErrorResponse{
				Code:    status,
				Message: msg,
				Detail:  detail,
			})
		}
	}
}
