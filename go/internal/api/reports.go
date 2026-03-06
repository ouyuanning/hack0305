package api

import (
	"encoding/json"
	"net/http"
	"sort"
	"strings"

	"github.com/gin-gonic/gin"
)

// reportTypeFromFilename extracts the report type from a report filename.
// Examples:
//
//	daily_report_matrixorigin_matrixone_20260225.json → daily
//	progress_report_matrixorigin_matrixone_20260225.json → progress
//	comprehensive_report_20260223.json → comprehensive
//	extensible_analysis_20260225.json → extensible
//	shared_features_20260223.json → shared
//	risk_analysis_20260223.json → risk
func reportTypeFromFilename(filename string) string {
	switch {
	case strings.HasPrefix(filename, "daily_report_"):
		return "daily"
	case strings.HasPrefix(filename, "progress_report_"):
		return "progress"
	case strings.HasPrefix(filename, "comprehensive_report_"):
		return "comprehensive"
	case strings.HasPrefix(filename, "extensible_analysis_"):
		return "extensible"
	case strings.HasPrefix(filename, "shared_features_"):
		return "shared"
	case strings.HasPrefix(filename, "risk_analysis_"):
		return "risk"
	default:
		// customer reports: {customer}_report_{date}.json
		if strings.HasSuffix(filename, ".json") && strings.Contains(filename, "_report_") {
			return "customer"
		}
		return "unknown"
	}
}

// repoFromReportJSON attempts to extract the "repo" field from report JSON data.
// Falls back to constructing it from owner/name if not present.
func repoFromReportJSON(data []byte, owner, name string) string {
	var partial struct {
		Repo string `json:"repo"`
	}
	if err := json.Unmarshal(data, &partial); err == nil && partial.Repo != "" {
		return partial.Repo
	}
	return owner + "/" + name
}

// generatedAtFromJSON extracts the "generated_at" field from report JSON data.
func generatedAtFromJSON(data []byte) string {
	var partial struct {
		GeneratedAt string `json:"generated_at"`
	}
	if err := json.Unmarshal(data, &partial); err == nil && partial.GeneratedAt != "" {
		return partial.GeneratedAt
	}
	return ""
}

// sortReportsByGeneratedAt sorts report metadata by generated_at in descending order.
func sortReportsByGeneratedAt(items []ReportMeta) {
	sort.Slice(items, func(i, j int) bool {
		return items[i].GeneratedAt > items[j].GeneratedAt
	})
}

// handleListReports handles GET /api/v1/reports.
// Query params: repo_owner (required), repo_name (required), type (optional).
func (s *Server) handleListReports(c *gin.Context) {
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

	reportType := c.Query("type")

	prefix := s.Store.PathForRepo(repoOwner, repoName) + "/reports/"
	files, err := s.Store.ListByPrefix(c.Request.Context(), prefix)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Code:    http.StatusInternalServerError,
			Message: "failed to list reports",
			Detail:  err.Error(),
		})
		return
	}

	// The volume uses flat filenames like "repos__matrixorigin__matrixone__reports__daily_report_...json".
	// Strip the flat prefix so reportTypeFromFilename sees just "daily_report_...json".
	flatPrefix := strings.ReplaceAll(prefix, "/", "__")

	var items []ReportMeta
	for _, f := range files {
		flatName := f.GetName()

		// Only include JSON files, skip markdown and subdirectories
		if !strings.HasSuffix(flatName, ".json") {
			continue
		}

		// Strip the flat prefix to get the short filename
		shortName := strings.TrimPrefix(flatName, flatPrefix)

		rType := reportTypeFromFilename(shortName)
		if reportType != "" && rType != reportType {
			continue
		}

		id := strings.TrimSuffix(shortName, ".json")

		// Download file to extract generated_at and repo
		data, err := s.Store.Download(c.Request.Context(), f.GetId())
		generatedAt := ""
		repo := repoOwner + "/" + repoName
		if err == nil {
			generatedAt = generatedAtFromJSON(data)
			repo = repoFromReportJSON(data, repoOwner, repoName)
		}

		items = append(items, ReportMeta{
			ID:          id,
			Type:        rType,
			Repo:        repo,
			GeneratedAt: generatedAt,
			Filename:    shortName,
		})
	}

	// Sort by generated_at descending
	sortReportsByGeneratedAt(items)

	if items == nil {
		items = []ReportMeta{}
	}

	c.JSON(http.StatusOK, ReportListResponse{Items: items})
}

// handleGetReport handles GET /api/v1/reports/:id.
// The :id parameter is the filename without .json extension.
func (s *Server) handleGetReport(c *gin.Context) {
	id := c.Param("id")
	if id == "" {
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Code:    http.StatusBadRequest,
			Message: "missing report id",
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

	filename := id + ".json"
	prefix := s.Store.PathForRepo(repoOwner, repoName) + "/reports/"
	flatPrefix := strings.ReplaceAll(prefix, "/", "__")

	// Find the file by listing and matching the short filename
	files, err := s.Store.ListByPrefix(c.Request.Context(), prefix)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Code:    http.StatusInternalServerError,
			Message: "failed to list reports",
			Detail:  err.Error(),
		})
		return
	}

	var fileID string
	for _, f := range files {
		fn := f.GetName()
		shortName := strings.TrimPrefix(fn, flatPrefix)
		if shortName == filename {
			fileID = f.GetId()
			break
		}
	}

	if fileID == "" {
		c.JSON(http.StatusNotFound, ErrorResponse{
			Code:    http.StatusNotFound,
			Message: "report not found",
			Detail:  "no report found with id: " + id,
		})
		return
	}

	data, err := s.Store.Download(c.Request.Context(), fileID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Code:    http.StatusInternalServerError,
			Message: "failed to download report",
			Detail:  err.Error(),
		})
		return
	}

	// Parse the raw JSON content
	var content any
	if err := json.Unmarshal(data, &content); err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Code:    http.StatusInternalServerError,
			Message: "failed to parse report content",
			Detail:  err.Error(),
		})
		return
	}

	// Build metadata
	rType := reportTypeFromFilename(filename)
	generatedAt := generatedAtFromJSON(data)
	repo := repoFromReportJSON(data, repoOwner, repoName)

	c.JSON(http.StatusOK, ReportDetailResponse{
		Metadata: ReportMeta{
			ID:          id,
			Type:        rType,
			Repo:        repo,
			GeneratedAt: generatedAt,
			Filename:    filename,
		},
		Data: content,
	})
}
