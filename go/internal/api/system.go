package api

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"path/filepath"

	"github.com/gin-gonic/gin"
)

// SystemResetRequest is the request body for system reset.
type SystemResetRequest struct {
	Confirm bool `json:"confirm" binding:"required"`
}

// SystemResetResponse is the response for system reset.
type SystemResetResponse struct {
	Success       bool     `json:"success"`
	Message       string   `json:"message"`
	DeletedPaths  []string `json:"deleted_paths,omitempty"`
	DeletedVolume bool     `json:"deleted_volume"`
}

// handleSystemReset handles POST /api/v1/system/reset.
// This endpoint clears all local data and optionally resets the MOI volume.
func (s *Server) handleSystemReset(c *gin.Context) {
	var req SystemResetRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Code:    http.StatusBadRequest,
			Message: "invalid request body",
			Detail:  err.Error(),
		})
		return
	}

	if !req.Confirm {
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Code:    http.StatusBadRequest,
			Message: "confirmation required",
			Detail:  "set confirm=true to proceed with reset",
		})
		return
	}

	ctx := context.Background()
	deletedPaths := []string{}

	// 1. Clear local mirror data (if configured)
	localDataPaths := []string{
		"data/reports",
		"go/data/reports",
	}

	for _, p := range localDataPaths {
		absPath, err := filepath.Abs(p)
		if err != nil {
			continue
		}
		if _, err := os.Stat(absPath); err == nil {
			if err := os.RemoveAll(absPath); err == nil {
				deletedPaths = append(deletedPaths, absPath)
				// Recreate the directory
				_ = os.MkdirAll(absPath, 0755)
			}
		}
	}

	// 2. Clear MOI volume data (if store is available)
	deletedVolume := false
	if s.Store != nil {
		// Delete all files in the volume by listing and deleting
		// For now, we'll just mark it as attempted
		// A full implementation would iterate through all files and delete them
		// or recreate the volume
		if err := s.Store.ClearAllData(ctx); err == nil {
			deletedVolume = true
		}
	}

	c.JSON(http.StatusOK, SystemResetResponse{
		Success:       true,
		Message:       fmt.Sprintf("系统已重置，共清理 %d 个本地路径", len(deletedPaths)),
		DeletedPaths:  deletedPaths,
		DeletedVolume: deletedVolume,
	})
}
