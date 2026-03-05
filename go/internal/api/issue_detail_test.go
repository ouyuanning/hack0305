package api

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/matrixorigin/issue-manager/internal/github"
)

func init() {
	gin.SetMode(gin.TestMode)
}

// setupTestRouter creates a Gin engine with the given Server's routes registered.
func setupTestRouter(s *Server) *gin.Engine {
	r := gin.New()
	s.RegisterRoutes(r)
	return r
}

// --- handleGetIssue tests ---

func TestHandleGetIssue_InvalidNumber(t *testing.T) {
	s := &Server{}
	r := setupTestRouter(s)

	tests := []struct {
		name   string
		path   string
		status int
	}{
		{"non-numeric", "/api/v1/issues/abc", http.StatusBadRequest},
		{"zero", "/api/v1/issues/0", http.StatusBadRequest},
		{"negative", "/api/v1/issues/-1", http.StatusBadRequest},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodGet, tt.path+"?repo_owner=o&repo_name=r", nil)
			w := httptest.NewRecorder()
			r.ServeHTTP(w, req)

			if w.Code != tt.status {
				t.Errorf("expected status %d, got %d", tt.status, w.Code)
			}
			var resp ErrorResponse
			if err := json.Unmarshal(w.Body.Bytes(), &resp); err != nil {
				t.Fatalf("failed to decode response: %v", err)
			}
			if resp.Code != tt.status {
				t.Errorf("expected error code %d, got %d", tt.status, resp.Code)
			}
		})
	}
}

func TestHandleGetIssue_MissingRepoParams(t *testing.T) {
	s := &Server{}
	r := setupTestRouter(s)

	tests := []struct {
		name  string
		query string
	}{
		{"missing both", ""},
		{"missing repo_name", "?repo_owner=o"},
		{"missing repo_owner", "?repo_name=r"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodGet, "/api/v1/issues/1"+tt.query, nil)
			w := httptest.NewRecorder()
			r.ServeHTTP(w, req)

			if w.Code != http.StatusBadRequest {
				t.Errorf("expected 400, got %d", w.Code)
			}
		})
	}
}

// --- handleCreateIssue tests ---

func TestHandleCreateIssue_Success(t *testing.T) {
	// Mock GitHub API server
	ghServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			t.Errorf("expected POST, got %s", r.Method)
		}
		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(map[string]any{
			"number":   42,
			"html_url": "https://github.com/test/repo/issues/42",
		})
	}))
	defer ghServer.Close()

	s := &Server{
		GitHub: github.New(ghServer.URL, "test-token"),
	}
	r := setupTestRouter(s)

	body := CreateIssueRequest{
		RepoOwner: "test",
		RepoName:  "repo",
		Title:     "Test Issue",
		Body:      "This is a test issue body",
		Labels:    []string{"bug"},
		Assignees: []string{"alice"},
	}
	data, _ := json.Marshal(body)

	req := httptest.NewRequest(http.MethodPost, "/api/v1/issues", bytes.NewReader(data))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Fatalf("expected 201, got %d: %s", w.Code, w.Body.String())
	}

	var resp map[string]any
	if err := json.Unmarshal(w.Body.Bytes(), &resp); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if int(resp["issue_number"].(float64)) != 42 {
		t.Errorf("expected issue_number 42, got %v", resp["issue_number"])
	}
	if resp["html_url"] != "https://github.com/test/repo/issues/42" {
		t.Errorf("unexpected html_url: %v", resp["html_url"])
	}
}

func TestHandleCreateIssue_MissingRequiredFields(t *testing.T) {
	s := &Server{}
	r := setupTestRouter(s)

	tests := []struct {
		name string
		body map[string]any
	}{
		{"missing title", map[string]any{"repo_owner": "o", "repo_name": "r", "body": "b"}},
		{"missing body", map[string]any{"repo_owner": "o", "repo_name": "r", "title": "t"}},
		{"missing repo_owner", map[string]any{"repo_name": "r", "title": "t", "body": "b"}},
		{"missing repo_name", map[string]any{"repo_owner": "o", "title": "t", "body": "b"}},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			data, _ := json.Marshal(tt.body)
			req := httptest.NewRequest(http.MethodPost, "/api/v1/issues", bytes.NewReader(data))
			req.Header.Set("Content-Type", "application/json")
			w := httptest.NewRecorder()
			r.ServeHTTP(w, req)

			if w.Code != http.StatusBadRequest {
				t.Errorf("expected 400, got %d: %s", w.Code, w.Body.String())
			}
		})
	}
}

func TestHandleCreateIssue_GitHubError(t *testing.T) {
	// Mock GitHub API that returns an error
	ghServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusUnprocessableEntity)
		fmt.Fprint(w, `{"message":"Validation Failed"}`)
	}))
	defer ghServer.Close()

	s := &Server{
		GitHub: github.New(ghServer.URL, "test-token"),
	}
	r := setupTestRouter(s)

	body := CreateIssueRequest{
		RepoOwner: "test",
		RepoName:  "repo",
		Title:     "Test",
		Body:      "Body",
	}
	data, _ := json.Marshal(body)

	req := httptest.NewRequest(http.MethodPost, "/api/v1/issues", bytes.NewReader(data))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusInternalServerError {
		t.Errorf("expected 500, got %d", w.Code)
	}
}

func TestHandleCreateIssue_NilLabelsAndAssignees(t *testing.T) {
	// Verify that nil labels/assignees are normalized to empty arrays
	var receivedPayload map[string]any
	ghServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		json.NewDecoder(r.Body).Decode(&receivedPayload)
		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(map[string]any{
			"number":   1,
			"html_url": "https://github.com/o/r/issues/1",
		})
	}))
	defer ghServer.Close()

	s := &Server{
		GitHub: github.New(ghServer.URL, "test-token"),
	}
	r := setupTestRouter(s)

	// Send request without labels and assignees fields
	data := []byte(`{"repo_owner":"o","repo_name":"r","title":"t","body":"b"}`)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/issues", bytes.NewReader(data))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Fatalf("expected 201, got %d: %s", w.Code, w.Body.String())
	}

	// Verify the payload sent to GitHub has arrays (not null)
	if receivedPayload["labels"] == nil {
		t.Error("expected labels to be an empty array, got nil")
	}
	if receivedPayload["assignees"] == nil {
		t.Error("expected assignees to be an empty array, got nil")
	}
}

func TestHandleCreateIssue_InvalidJSON(t *testing.T) {
	s := &Server{}
	r := setupTestRouter(s)

	req := httptest.NewRequest(http.MethodPost, "/api/v1/issues", bytes.NewReader([]byte("not json")))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", w.Code)
	}
}
