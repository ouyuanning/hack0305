package api

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/matrixorigin/issue-manager/internal/issue"
)

// --- parseDraftResponse tests ---

func TestParseDraftResponse_ValidJSON(t *testing.T) {
	raw := `{"title":"Bug report","body":"Something broke","labels":["kind/bug"],"assignees":["alice"],"template_type":"bug_report","related_issues":["#1"]}`
	draft, err := parseDraftResponse(raw)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if draft.Title != "Bug report" {
		t.Errorf("expected title 'Bug report', got %q", draft.Title)
	}
	if draft.Body != "Something broke" {
		t.Errorf("expected body 'Something broke', got %q", draft.Body)
	}
	if len(draft.Labels) != 1 || draft.Labels[0] != "kind/bug" {
		t.Errorf("unexpected labels: %v", draft.Labels)
	}
}

func TestParseDraftResponse_WithCodeFence(t *testing.T) {
	raw := "```json\n{\"title\":\"Feature\",\"body\":\"Add dark mode\",\"labels\":[],\"assignees\":[]}\n```"
	draft, err := parseDraftResponse(raw)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if draft.Title != "Feature" {
		t.Errorf("expected title 'Feature', got %q", draft.Title)
	}
}

func TestParseDraftResponse_MissingTitle(t *testing.T) {
	raw := `{"title":"","body":"some body","labels":[]}`
	_, err := parseDraftResponse(raw)
	if err == nil {
		t.Fatal("expected error for missing title")
	}
}

func TestParseDraftResponse_MissingBody(t *testing.T) {
	raw := `{"title":"A title","body":"","labels":[]}`
	_, err := parseDraftResponse(raw)
	if err == nil {
		t.Fatal("expected error for missing body")
	}
}

func TestParseDraftResponse_InvalidJSON(t *testing.T) {
	raw := `not json at all`
	_, err := parseDraftResponse(raw)
	if err == nil {
		t.Fatal("expected error for invalid JSON")
	}
}

// --- extractJSON tests ---

func TestExtractJSON_Plain(t *testing.T) {
	input := `  {"key":"value"}  `
	got := extractJSON(input)
	if got != `{"key":"value"}` {
		t.Errorf("unexpected result: %q", got)
	}
}

func TestExtractJSON_CodeFence(t *testing.T) {
	input := "```json\n{\"key\":\"value\"}\n```"
	got := extractJSON(input)
	if got != `{"key":"value"}` {
		t.Errorf("unexpected result: %q", got)
	}
}

func TestExtractJSON_CodeFenceNoLang(t *testing.T) {
	input := "```\n{\"key\":\"value\"}\n```"
	got := extractJSON(input)
	if got != `{"key":"value"}` {
		t.Errorf("unexpected result: %q", got)
	}
}

// --- buildUserPrompt tests ---

func TestBuildUserPrompt_NoImages(t *testing.T) {
	got := buildUserPrompt("fix the bug", nil)
	if got != "fix the bug" {
		t.Errorf("unexpected prompt: %q", got)
	}
}

func TestBuildUserPrompt_WithImages(t *testing.T) {
	got := buildUserPrompt("fix the bug", []string{"img1", "img2"})
	if got != "fix the bug\n\n[2 image(s) attached as additional context]" {
		t.Errorf("unexpected prompt: %q", got)
	}
}

// --- handler integration tests ---

func TestHandleGenerateIssue_MissingFields(t *testing.T) {
	s := &Server{}
	r := setupTestRouter(s)

	tests := []struct {
		name string
		body string
	}{
		{"empty body", `{}`},
		{"missing user_input", `{"repo_owner":"o","repo_name":"r"}`},
		{"missing repo_owner", `{"user_input":"test","repo_name":"r"}`},
		{"missing repo_name", `{"user_input":"test","repo_owner":"o"}`},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodPost, "/api/v1/ai/generate-issue", bytes.NewReader([]byte(tt.body)))
			req.Header.Set("Content-Type", "application/json")
			w := httptest.NewRecorder()
			r.ServeHTTP(w, req)

			if w.Code != http.StatusBadRequest {
				t.Errorf("expected 400, got %d", w.Code)
			}
		})
	}
}

func TestHandleGenerateIssue_InvalidJSON(t *testing.T) {
	s := &Server{}
	r := setupTestRouter(s)

	req := httptest.NewRequest(http.MethodPost, "/api/v1/ai/generate-issue", bytes.NewReader([]byte("not json")))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", w.Code)
	}
}

func TestHandleGenerateIssue_NilLLMClient(t *testing.T) {
	// When LLM client is nil, calling Ask will panic; the handler should fail gracefully
	// This tests that the server returns 500 when LLM is not configured
	s := &Server{LLM: nil}
	r := setupTestRouter(s)

	body := `{"user_input":"test bug","repo_owner":"o","repo_name":"r"}`
	req := httptest.NewRequest(http.MethodPost, "/api/v1/ai/generate-issue", bytes.NewReader([]byte(body)))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	// Should get 500 since LLM is nil (panic recovered by middleware or runtime)
	if w.Code != http.StatusInternalServerError {
		t.Errorf("expected 500, got %d", w.Code)
	}
}

func TestNullArraysNormalization(t *testing.T) {
	// Verify that parseDraftResponse + null normalization produces empty arrays, not null
	raw := `{"title":"Test","body":"Body text"}`
	draft, err := parseDraftResponse(raw)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Simulate the normalization done in the handler
	if draft.Labels == nil {
		draft.Labels = []string{}
	}
	if draft.Assignees == nil {
		draft.Assignees = []string{}
	}
	if draft.RelatedIssues == nil {
		draft.RelatedIssues = []string{}
	}

	data, _ := json.Marshal(draft)
	var result issue.Draft
	json.Unmarshal(data, &result)

	// Verify JSON serialization produces [] not null
	var raw2 map[string]any
	json.Unmarshal(data, &raw2)

	for _, field := range []string{"labels", "assignees", "related_issues"} {
		val, ok := raw2[field]
		if !ok {
			t.Errorf("field %q missing from JSON", field)
			continue
		}
		arr, ok := val.([]interface{})
		if !ok {
			t.Errorf("field %q is not an array, got %T", field, val)
			continue
		}
		if arr == nil {
			t.Errorf("field %q is null, expected empty array", field)
		}
	}
}
