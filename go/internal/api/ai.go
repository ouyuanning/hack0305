package api

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/matrixorigin/issue-manager/internal/issue"
)

func (s *Server) handleGenerateIssue(c *gin.Context) {
	var req GenerateIssueRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Code:    http.StatusBadRequest,
			Message: "invalid request body",
			Detail:  err.Error(),
		})
		return
	}

	if s.LLM == nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Code:    http.StatusInternalServerError,
			Message: "LLM service not configured",
		})
		return
	}

	systemPrompt := buildIssueGenerationPrompt(req.RepoOwner, req.RepoName)
	userPrompt := buildUserPrompt(req.UserInput, req.Images)

	raw, err := s.LLM.Ask(c.Request.Context(), systemPrompt, userPrompt)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Code:    http.StatusInternalServerError,
			Message: "failed to generate issue",
			Detail:  err.Error(),
		})
		return
	}

	draft, err := parseDraftResponse(raw)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Code:    http.StatusInternalServerError,
			Message: "failed to parse LLM response",
			Detail:  err.Error(),
		})
		return
	}

	// Ensure arrays are never null
	if draft.Labels == nil {
		draft.Labels = []string{}
	}
	if draft.Assignees == nil {
		draft.Assignees = []string{}
	}
	if draft.RelatedIssues == nil {
		draft.RelatedIssues = []string{}
	}

	c.JSON(http.StatusOK, draft)
}

func buildIssueGenerationPrompt(repoOwner, repoName string) string {
	return fmt.Sprintf(`You are an AI assistant that helps create GitHub Issues for the repository %s/%s.
Based on the user's description, generate a well-structured GitHub Issue.

You MUST respond with a valid JSON object containing these fields:
{
  "title": "concise issue title",
  "body": "detailed issue body in Markdown format",
  "labels": ["relevant", "labels"],
  "assignees": ["suggested_assignee"],
  "template_type": "bug_report or feature_request or task",
  "related_issues": ["#123"]
}

Guidelines:
- Title should be clear and concise
- Body should include context, steps to reproduce (for bugs), or detailed description
- Labels should use the repository's label conventions (kind/bug, kind/feature, area/*, customer/*)
- Only suggest assignees if clearly relevant
- template_type should be one of: bug_report, feature_request, task
- related_issues should reference existing issues if mentioned

Respond ONLY with the JSON object, no additional text.`, repoOwner, repoName)
}

func buildUserPrompt(userInput string, images []string) string {
	if len(images) == 0 {
		return userInput
	}
	return fmt.Sprintf("%s\n\n[%d image(s) attached as additional context]", userInput, len(images))
}

// parseDraftResponse extracts a JSON Draft from the LLM response,
// handling possible markdown code fences.
func parseDraftResponse(raw string) (*issue.Draft, error) {
	cleaned := extractJSON(raw)
	var draft issue.Draft
	if err := json.Unmarshal([]byte(cleaned), &draft); err != nil {
		return nil, fmt.Errorf("invalid JSON in LLM response: %w", err)
	}
	if draft.Title == "" {
		return nil, fmt.Errorf("LLM response missing required field: title")
	}
	if draft.Body == "" {
		return nil, fmt.Errorf("LLM response missing required field: body")
	}
	return &draft, nil
}

// extractJSON strips markdown code fences and leading/trailing whitespace
// to isolate the JSON payload from an LLM response.
func extractJSON(s string) string {
	s = strings.TrimSpace(s)
	// Strip ```json ... ``` fences
	if strings.HasPrefix(s, "```") {
		if idx := strings.Index(s, "\n"); idx != -1 {
			s = s[idx+1:]
		}
		if idx := strings.LastIndex(s, "```"); idx != -1 {
			s = s[:idx]
		}
	}
	return strings.TrimSpace(s)
}
