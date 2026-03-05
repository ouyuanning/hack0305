package api

import "github.com/matrixorigin/issue-manager/internal/issue"

// PaginatedResponse wraps a paginated list of items.
type PaginatedResponse struct {
	Total    int         `json:"total"`
	Page     int         `json:"page"`
	PageSize int         `json:"page_size"`
	Items    interface{} `json:"items"`
}

// ErrorResponse is the standard error payload.
type ErrorResponse struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Detail  string `json:"detail,omitempty"`
}

// IssueDetailResponse contains a single issue with its comments, timeline and relations.
type IssueDetailResponse struct {
	Issue     issue.Snapshot   `json:"issue"`
	Comments  []issue.Comment  `json:"comments"`
	Timeline  []map[string]any `json:"timeline"`
	Relations []issue.Relation `json:"relations"`
}

// OverviewResponse contains dashboard overview statistics.
type OverviewResponse struct {
	Total        int              `json:"total"`
	Open         int              `json:"open"`
	Closed       int              `json:"closed"`
	OpenRatio    float64          `json:"open_ratio"`
	RecentIssues []issue.Snapshot `json:"recent_issues"`
	HealthScores []HealthScore    `json:"health_scores"`
}

// HealthScore represents a customer project health metric.
type HealthScore struct {
	Customer      string  `json:"customer"`
	Score         float64 `json:"score"`
	TotalIssues   int     `json:"total_issues"`
	OpenIssues    int     `json:"open_issues"`
	BlockedIssues int     `json:"blocked_issues"`
}

// LabelStat holds the count for a single label.
type LabelStat struct {
	Label  string `json:"label"`
	Count  int    `json:"count"`
	Open   int    `json:"open"`
	Closed int    `json:"closed"`
}

// LabelsResponse groups label statistics by prefix.
type LabelsResponse struct {
	Groups map[string][]LabelStat `json:"groups"`
}

// ReportMeta describes a single report in the list response.
type ReportMeta struct {
	ID          string `json:"id"`
	Type        string `json:"type"`
	Repo        string `json:"repo"`
	GeneratedAt string `json:"generated_at"`
	Filename    string `json:"filename"`
}

// ReportListResponse wraps a list of report metadata items.
type ReportListResponse struct {
	Items []ReportMeta `json:"items"`
}

// GenerateIssueRequest is the payload for AI issue generation.
type GenerateIssueRequest struct {
	UserInput string   `json:"user_input" binding:"required"`
	Images    []string `json:"images"`
	RepoOwner string   `json:"repo_owner" binding:"required"`
	RepoName  string   `json:"repo_name" binding:"required"`
}

// CreateIssueRequest is the payload for creating an issue on GitHub.
type CreateIssueRequest struct {
	RepoOwner string   `json:"repo_owner" binding:"required"`
	RepoName  string   `json:"repo_name" binding:"required"`
	Title     string   `json:"title" binding:"required"`
	Body      string   `json:"body" binding:"required"`
	Labels    []string `json:"labels"`
	Assignees []string `json:"assignees"`
}

// TriggerWorkflowRequest is the payload for triggering a workflow execution.
type TriggerWorkflowRequest struct {
	RepoOwner string `json:"repo_owner" binding:"required"`
	RepoName  string `json:"repo_name" binding:"required"`
	FullSync  bool   `json:"full_sync"`
	Since     string `json:"since"`
}

// WorkflowStatusResponse describes the current state of a workflow execution.
type WorkflowStatusResponse struct {
	ExecutionID string         `json:"execution_id"`
	WorkflowID  string         `json:"workflow_id"`
	Status      string         `json:"status"`
	Result      map[string]any `json:"result,omitempty"`
	Error       string         `json:"error,omitempty"`
	StartedAt   string         `json:"started_at,omitempty"`
	CompletedAt string         `json:"completed_at,omitempty"`
}

// KnowledgeResponse is the response for the knowledge base endpoint.
type KnowledgeResponse struct {
	Content     string `json:"content"`
	GeneratedAt string `json:"generated_at"`
	Version     string `json:"version"`
}

// RepoInfo describes an available repository.
type RepoInfo struct {
	Owner       string `json:"owner"`
	Name        string `json:"name"`
	DisplayName string `json:"display_name"`
}
