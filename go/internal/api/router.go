package api

import (
	"github.com/gin-gonic/gin"
	"github.com/matrixorigin/issue-manager/internal/analysis"
	"github.com/matrixorigin/issue-manager/internal/github"
	"github.com/matrixorigin/issue-manager/internal/llm"
	"github.com/matrixorigin/issue-manager/internal/storage"
)

// Server holds the dependencies shared across all API handlers.
type Server struct {
	Store     *storage.VolumeStore
	Analyzer  *analysis.Generator
	GitHub    *github.Client
	LLM       *llm.Client
	Repos     []RepoInfo // configured repositories
	Workflows *WorkflowManager
}

// RegisterRoutes sets up all API routes under /api/v1/.
func (s *Server) RegisterRoutes(r *gin.Engine) {
	v1 := r.Group("/api/v1")

	// Issue endpoints
	v1.GET("/issues", s.handleListIssues)
	v1.GET("/issues/:number", s.handleGetIssue)
	v1.POST("/issues", s.handleCreateIssue)

	// Statistics endpoints
	v1.GET("/stats/overview", s.handleStatsOverview)
	v1.GET("/stats/labels", s.handleStatsLabels)

	// Report endpoints
	v1.GET("/reports", s.handleListReports)
	v1.GET("/reports/:id", s.handleGetReport)

	// Workflow endpoints
	v1.GET("/workflows", s.handleListWorkflows)
	v1.POST("/workflows/:id/trigger", s.handleTriggerWorkflow)
	v1.GET("/workflows/:id/status", s.handleWorkflowStatus)

	// Knowledge base endpoint
	v1.GET("/knowledge", s.handleGetKnowledge)

	// AI endpoint
	v1.POST("/ai/generate-issue", s.handleGenerateIssue)

	// Repository list endpoint
	v1.GET("/repos", s.handleListRepos)
}

// ---------- placeholder handlers (implemented in dedicated files) ----------

// handleListIssues is implemented in issues.go
// handleGetIssue is implemented in issues.go
// handleCreateIssue is implemented in issues.go
// handleStatsOverview is implemented in stats.go
// handleStatsLabels is implemented in stats.go

// handleListReports is implemented in reports.go
// handleGetReport is implemented in reports.go

// handleListWorkflows is implemented in workflows.go
// handleTriggerWorkflow is implemented in workflows.go
// handleWorkflowStatus is implemented in workflows.go

// handleGetKnowledge is implemented in knowledge.go

// handleGenerateIssue is implemented in ai.go

func (s *Server) handleListRepos(c *gin.Context) {
	c.JSON(200, s.Repos)
}
