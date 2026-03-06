package api

import (
	"net/http"
	"regexp"
	"sort"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
)

// knowledgeDateRegex matches knowledge base filenames with a date suffix.
// Pattern: {owner}_{repo}_knowledge_{YYYYMMDD}.md
var knowledgeDateRegex = regexp.MustCompile(`_knowledge_(\d{8})\.md$`)

// extractKnowledgeVersion extracts the date version string from a knowledge base filename.
// Returns the date string (e.g. "20260225") and true if found, or "" and false otherwise.
func extractKnowledgeVersion(filename string) (string, bool) {
	matches := knowledgeDateRegex.FindStringSubmatch(filename)
	if len(matches) < 2 {
		return "", false
	}
	return matches[1], true
}

// generatedAtFromVersion converts a version string like "20260225" to an ISO8601 timestamp.
func generatedAtFromVersion(version string) string {
	t, err := time.Parse("20060102", version)
	if err != nil {
		return ""
	}
	return t.Format(time.RFC3339)
}

// handleGetKnowledge handles GET /api/v1/knowledge.
// Query params: repo_owner (required), repo_name (required).
// Returns the latest knowledge base content, generated_at, and version.
func (s *Server) handleGetKnowledge(c *gin.Context) {
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

	prefix := s.Store.PathForRepo(repoOwner, repoName) + "/knowledge/"
	files, err := s.Store.ListByPrefix(c.Request.Context(), prefix)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Code:    http.StatusInternalServerError,
			Message: "failed to list knowledge base files",
			Detail:  err.Error(),
		})
		return
	}

	// Find the latest dated knowledge base file (skip _latest.md).
	type kbEntry struct {
		fileID  string
		version string
	}
	var entries []kbEntry
	for _, f := range files {
		filename := f.GetName()
		if !strings.HasSuffix(filename, ".md") {
			continue
		}
		// Skip the _latest.md symlink-style file; prefer dated versions.
		if strings.HasSuffix(filename, "_latest.md") {
			continue
		}
		version, ok := extractKnowledgeVersion(filename)
		if !ok {
			continue
		}
		entries = append(entries, kbEntry{fileID: f.GetId(), version: version})
	}

	// If no dated files found, fall back to the _latest.md file.
	if len(entries) == 0 {
		for _, f := range files {
			filename := f.GetName()
			if strings.HasSuffix(filename, "_latest.md") {
				data, err := s.Store.Download(c.Request.Context(), f.GetId())
				if err != nil {
					c.JSON(http.StatusInternalServerError, ErrorResponse{
						Code:    http.StatusInternalServerError,
						Message: "failed to download knowledge base",
						Detail:  err.Error(),
					})
					return
				}
				c.JSON(http.StatusOK, KnowledgeResponse{
					Content:     string(data),
					GeneratedAt: "",
					Version:     "latest",
				})
				return
			}
		}
		// No knowledge base files at all.
		c.JSON(http.StatusNotFound, ErrorResponse{
			Code:    http.StatusNotFound,
			Message: "knowledge base not found",
			Detail:  "no knowledge base has been generated for this repository",
		})
		return
	}

	// Sort by version descending to pick the latest.
	sort.Slice(entries, func(i, j int) bool {
		return entries[i].version > entries[j].version
	})
	latest := entries[0]

	data, err := s.Store.Download(c.Request.Context(), latest.fileID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Code:    http.StatusInternalServerError,
			Message: "failed to download knowledge base",
			Detail:  err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, KnowledgeResponse{
		Content:     string(data),
		GeneratedAt: generatedAtFromVersion(latest.version),
		Version:     latest.version,
	})
}
