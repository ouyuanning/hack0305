package api

import (
	"net/http"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/matrixorigin/issue-manager/internal/issue"
)

// handleListIssues handles GET /api/v1/issues with filtering, search, sorting and pagination.
func (s *Server) handleListIssues(c *gin.Context) {
	// --- required params ---
	repoOwner := c.Query("repo_owner")
	repoName := c.Query("repo_name")
	if repoOwner == "" || repoName == "" {
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Code:    http.StatusBadRequest,
			Message: "missing required parameters",
			Detail:  "repo_owner and repo_name are required",
		})
		return
	}

	// --- pagination params ---
	page := queryInt(c, "page", 1)
	pageSize := queryInt(c, "page_size", 20)
	if page < 1 {
		page = 1
	}
	if pageSize < 1 {
		pageSize = 20
	}
	if pageSize > 100 {
		pageSize = 100
	}

	// --- filter params ---
	state := strings.ToLower(c.Query("state"))
	labelsRaw := c.Query("labels")
	assignee := c.Query("assignee")
	startDateStr := c.Query("start_date")
	endDateStr := c.Query("end_date")
	keyword := strings.ToLower(c.Query("keyword"))
	sortField := c.Query("sort_field")
	sortOrder := strings.ToLower(c.Query("sort_order"))

	var labels []string
	if labelsRaw != "" {
		for _, l := range strings.Split(labelsRaw, ",") {
			l = strings.TrimSpace(l)
			if l != "" {
				labels = append(labels, l)
			}
		}
	}

	var startDate, endDate time.Time
	var hasStartDate, hasEndDate bool
	if startDateStr != "" {
		if t, err := time.Parse(time.RFC3339, startDateStr); err == nil {
			startDate = t
			hasStartDate = true
		}
	}
	if endDateStr != "" {
		if t, err := time.Parse(time.RFC3339, endDateStr); err == nil {
			endDate = t
			hasEndDate = true
		}
	}

	// --- load snapshots ---
	snapshots, err := s.Analyzer.LoadLatestSnapshots(c.Request.Context(), repoOwner, repoName)
	if err != nil {
		// No data synced yet — return empty list instead of 500
		snapshots = []issue.Snapshot{}
	}

	// --- filter ---
	filtered := filterIssues(snapshots, state, labels, assignee, keyword, startDate, endDate, hasStartDate, hasEndDate)

	// --- sort ---
	sortIssues(filtered, sortField, sortOrder)

	// --- paginate ---
	total := len(filtered)
	offset := (page - 1) * pageSize
	if offset > total {
		offset = total
	}
	end := offset + pageSize
	if end > total {
		end = total
	}
	items := filtered[offset:end]

	c.JSON(http.StatusOK, PaginatedResponse{
		Total:    total,
		Page:     page,
		PageSize: pageSize,
		Items:    items,
	})
}

// filterIssues applies all filter criteria to the snapshot list.
func filterIssues(
	snapshots []issue.Snapshot,
	state string,
	labels []string,
	assignee string,
	keyword string,
	startDate, endDate time.Time,
	hasStartDate, hasEndDate bool,
) []issue.Snapshot {
	result := make([]issue.Snapshot, 0, len(snapshots))
	for _, s := range snapshots {
		if !matchState(s, state) {
			continue
		}
		if !matchLabels(s, labels) {
			continue
		}
		if assignee != "" && !strings.EqualFold(s.Assignee, assignee) {
			continue
		}
		if !matchDateRange(s, startDate, endDate, hasStartDate, hasEndDate) {
			continue
		}
		if keyword != "" && !matchKeyword(s, keyword) {
			continue
		}
		result = append(result, s)
	}
	return result
}

// matchState checks if the issue matches the requested state filter.
func matchState(s issue.Snapshot, state string) bool {
	if state == "" || state == "all" {
		return true
	}
	return strings.EqualFold(s.State, state)
}

// matchLabels checks if the issue has ALL of the requested labels.
func matchLabels(s issue.Snapshot, labels []string) bool {
	if len(labels) == 0 {
		return true
	}
	labelSet := make(map[string]struct{}, len(s.Labels))
	for _, l := range s.Labels {
		labelSet[strings.ToLower(l)] = struct{}{}
	}
	for _, required := range labels {
		if _, ok := labelSet[strings.ToLower(required)]; !ok {
			return false
		}
	}
	return true
}

// matchDateRange checks if the issue's updated_at falls within the date range.
func matchDateRange(s issue.Snapshot, start, end time.Time, hasStart, hasEnd bool) bool {
	if !hasStart && !hasEnd {
		return true
	}
	if s.UpdatedAt == nil {
		return false
	}
	t := *s.UpdatedAt
	if hasStart && t.Before(start) {
		return false
	}
	if hasEnd && t.After(end) {
		return false
	}
	return true
}

// matchKeyword checks if the issue title or body contains the keyword (case-insensitive).
func matchKeyword(s issue.Snapshot, keyword string) bool {
	kw := strings.ToLower(keyword)
	return strings.Contains(strings.ToLower(s.Title), kw) ||
		strings.Contains(strings.ToLower(s.Body), kw)
}

// sortIssues sorts the snapshot slice in place by the given field and order.
func sortIssues(items []issue.Snapshot, field, order string) {
	if field == "" {
		field = "issue_number"
	}
	desc := order == "desc"

	sort.SliceStable(items, func(i, j int) bool {
		cmp := compareIssues(items[i], items[j], field)
		if desc {
			return cmp > 0
		}
		return cmp < 0
	})
}

// compareIssues returns -1, 0, or 1 comparing a and b by the given field.
func compareIssues(a, b issue.Snapshot, field string) int {
	switch field {
	case "issue_number":
		return compareInt(a.IssueNumber, b.IssueNumber)
	case "updated_at":
		return compareTimePtr(a.UpdatedAt, b.UpdatedAt)
	case "created_at":
		return compareTimePtr(a.CreatedAt, b.CreatedAt)
	case "priority":
		return comparePriority(a.Priority, b.Priority)
	default:
		return compareInt(a.IssueNumber, b.IssueNumber)
	}
}

// compareInt returns -1, 0, or 1.
func compareInt(a, b int) int {
	if a < b {
		return -1
	}
	if a > b {
		return 1
	}
	return 0
}

// compareTimePtr compares two *time.Time values. nil is treated as the zero time.
func compareTimePtr(a, b *time.Time) int {
	ta := time.Time{}
	tb := time.Time{}
	if a != nil {
		ta = *a
	}
	if b != nil {
		tb = *b
	}
	if ta.Before(tb) {
		return -1
	}
	if ta.After(tb) {
		return 1
	}
	return 0
}

// comparePriority compares priority strings by their known ordering.
// Known priorities: critical > high > medium > low > "" (unknown).
func comparePriority(a, b string) int {
	return compareInt(priorityRank(a), priorityRank(b))
}

func priorityRank(p string) int {
	switch strings.ToLower(p) {
	case "critical":
		return 4
	case "high":
		return 3
	case "medium":
		return 2
	case "low":
		return 1
	default:
		return 0
	}
}

// queryInt reads an integer query parameter with a default value.
func queryInt(c *gin.Context, key string, defaultVal int) int {
	s := c.Query(key)
	if s == "" {
		return defaultVal
	}
	v, err := strconv.Atoi(s)
	if err != nil {
		return defaultVal
	}
	return v
}

// handleGetIssue handles GET /api/v1/issues/:number.
// It returns the issue snapshot, comments, timeline events and relations.
func (s *Server) handleGetIssue(c *gin.Context) {
	numberStr := c.Param("number")
	number, err := strconv.Atoi(numberStr)
	if err != nil || number <= 0 {
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Code:    http.StatusBadRequest,
			Message: "invalid issue number",
			Detail:  "number must be a positive integer",
		})
		return
	}

	repoOwner := c.Query("repo_owner")
	repoName := c.Query("repo_name")
	if repoOwner == "" || repoName == "" {
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Code:    http.StatusBadRequest,
			Message: "missing required parameters",
			Detail:  "repo_owner and repo_name are required",
		})
		return
	}

	// Load bundle (snapshots + relations)
	bundle, err := s.Analyzer.LoadLatestBundle(c.Request.Context(), repoOwner, repoName)
	if err != nil {
		c.JSON(http.StatusNotFound, ErrorResponse{
			Code:    http.StatusNotFound,
			Message: "no issue data available",
			Detail:  "run WF-001 to sync issue data first",
		})
		return
	}

	// Find the snapshot by issue number
	var found *issue.Snapshot
	for i := range bundle.Snapshots {
		if bundle.Snapshots[i].IssueNumber == number {
			found = &bundle.Snapshots[i]
			break
		}
	}
	if found == nil {
		c.JSON(http.StatusNotFound, ErrorResponse{
			Code:    http.StatusNotFound,
			Message: "issue not found",
			Detail:  "no issue with number " + numberStr,
		})
		return
	}

	// Collect relations for this issue
	var relations []issue.Relation
	for _, r := range bundle.Relations {
		if r.FromIssueID == found.IssueID || r.ToIssueID == found.IssueID {
			relations = append(relations, r)
		}
	}
	if relations == nil {
		relations = []issue.Relation{}
	}

	// Fetch comments from GitHub
	comments, err := s.GitHub.FetchComments(c.Request.Context(), repoOwner, repoName, number)
	var issueComments []issue.Comment
	if err == nil {
		issueComments = make([]issue.Comment, 0, len(comments))
		for _, gc := range comments {
			ic := issue.Comment{
				IssueID:     found.IssueID,
				IssueNumber: number,
				CommentID:   gc.ID,
				User:        gc.User.Login,
				Body:        gc.Body,
			}
			if t, e := time.Parse(time.RFC3339, gc.CreatedAt); e == nil {
				ic.CreatedAt = &t
			}
			if t, e := time.Parse(time.RFC3339, gc.UpdatedAt); e == nil {
				ic.UpdatedAt = &t
			}
			issueComments = append(issueComments, ic)
		}
	}
	if issueComments == nil {
		issueComments = []issue.Comment{}
	}

	// Fetch timeline from GitHub
	timeline, err := s.GitHub.FetchTimeline(c.Request.Context(), repoOwner, repoName, number)
	if timeline == nil {
		timeline = []map[string]any{}
	}

	c.JSON(http.StatusOK, IssueDetailResponse{
		Issue:     *found,
		Comments:  issueComments,
		Timeline:  timeline,
		Relations: relations,
	})
}

// handleCreateIssue handles POST /api/v1/issues.
// It creates an issue on GitHub via the GitHub Client and returns the issue number and URL.
func (s *Server) handleCreateIssue(c *gin.Context) {
	var req CreateIssueRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Code:    http.StatusBadRequest,
			Message: "invalid request body",
			Detail:  err.Error(),
		})
		return
	}

	if req.Labels == nil {
		req.Labels = []string{}
	}
	if req.Assignees == nil {
		req.Assignees = []string{}
	}

	result, err := s.GitHub.CreateIssue(
		c.Request.Context(),
		req.RepoOwner,
		req.RepoName,
		req.Title,
		req.Body,
		req.Labels,
		req.Assignees,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Code:    http.StatusInternalServerError,
			Message: "failed to create issue",
			Detail:  err.Error(),
		})
		return
	}

	// Extract issue number and html_url from GitHub response
	issueNumber := 0
	if n, ok := result["number"].(float64); ok {
		issueNumber = int(n)
	}
	htmlURL := ""
	if u, ok := result["html_url"].(string); ok {
		htmlURL = u
	}

	c.JSON(http.StatusCreated, gin.H{
		"issue_number": issueNumber,
		"html_url":     htmlURL,
	})
}
