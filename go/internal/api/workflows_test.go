package api

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
)

func setupWorkflowRouter() (*gin.Engine, *Server) {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	srv := &Server{
		Workflows: NewWorkflowManager(),
	}
	srv.RegisterRoutes(r)
	return r, srv
}

func TestListWorkflows(t *testing.T) {
	r, _ := setupWorkflowRouter()

	req := httptest.NewRequest(http.MethodGet, "/api/v1/workflows", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}

	var defs []WorkflowDef
	if err := json.Unmarshal(w.Body.Bytes(), &defs); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if len(defs) != 7 {
		t.Errorf("expected 7 workflow definitions, got %d", len(defs))
	}

	// Verify WF-001 through WF-007 IDs exist
	ids := map[string]bool{}
	for _, d := range defs {
		ids[d.ID] = true
	}
	for i := 1; i <= 7; i++ {
		wfID := "WF-00" + string(rune('0'+i))
		if !ids[wfID] {
			t.Errorf("missing workflow %s", wfID)
		}
	}
}

func TestTriggerWorkflow(t *testing.T) {
	r, _ := setupWorkflowRouter()

	body, _ := json.Marshal(TriggerWorkflowRequest{
		RepoOwner: "matrixorigin",
		RepoName:  "matrixone",
	})
	req := httptest.NewRequest(http.MethodPost, "/api/v1/workflows/WF-001/trigger", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusAccepted {
		t.Fatalf("expected 202, got %d: %s", w.Code, w.Body.String())
	}

	var resp map[string]string
	if err := json.Unmarshal(w.Body.Bytes(), &resp); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}
	if resp["execution_id"] == "" {
		t.Error("expected non-empty execution_id")
	}
	if resp["status"] != "queued" {
		t.Errorf("expected status=queued, got %s", resp["status"])
	}
}

func TestTriggerWorkflowNotFound(t *testing.T) {
	r, _ := setupWorkflowRouter()

	body, _ := json.Marshal(TriggerWorkflowRequest{
		RepoOwner: "owner",
		RepoName:  "repo",
	})
	req := httptest.NewRequest(http.MethodPost, "/api/v1/workflows/WF-999/trigger", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", w.Code)
	}
}

func TestTriggerWorkflowBadRequest(t *testing.T) {
	r, _ := setupWorkflowRouter()

	// Missing required fields
	body := []byte(`{}`)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/workflows/WF-001/trigger", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d: %s", w.Code, w.Body.String())
	}
}

func TestTriggerWorkflowConflict(t *testing.T) {
	r, srv := setupWorkflowRouter()

	// First trigger should succeed
	body, _ := json.Marshal(TriggerWorkflowRequest{
		RepoOwner: "matrixorigin",
		RepoName:  "matrixone",
	})
	req1 := httptest.NewRequest(http.MethodPost, "/api/v1/workflows/WF-001/trigger", bytes.NewReader(body))
	req1.Header.Set("Content-Type", "application/json")
	w1 := httptest.NewRecorder()
	r.ServeHTTP(w1, req1)

	if w1.Code != http.StatusAccepted {
		t.Fatalf("first trigger: expected 202, got %d", w1.Code)
	}

	// Manually keep it running by marking it running (the goroutine may complete quickly)
	var firstResp map[string]string
	json.Unmarshal(w1.Body.Bytes(), &firstResp)
	// Force it to running state to test conflict
	srv.Workflows.mu.Lock()
	if exec, ok := srv.Workflows.executions[firstResp["execution_id"]]; ok {
		exec.Status = "running"
	}
	srv.Workflows.running["WF-001"] = firstResp["execution_id"]
	srv.Workflows.mu.Unlock()

	// Second trigger should return 409
	body2, _ := json.Marshal(TriggerWorkflowRequest{
		RepoOwner: "matrixorigin",
		RepoName:  "matrixone",
	})
	req2 := httptest.NewRequest(http.MethodPost, "/api/v1/workflows/WF-001/trigger", bytes.NewReader(body2))
	req2.Header.Set("Content-Type", "application/json")
	w2 := httptest.NewRecorder()
	r.ServeHTTP(w2, req2)

	if w2.Code != http.StatusConflict {
		t.Fatalf("second trigger: expected 409, got %d: %s", w2.Code, w2.Body.String())
	}
}

func TestWorkflowStatus(t *testing.T) {
	r, _ := setupWorkflowRouter()

	// Trigger a workflow first
	body, _ := json.Marshal(TriggerWorkflowRequest{
		RepoOwner: "matrixorigin",
		RepoName:  "matrixone",
	})
	triggerReq := httptest.NewRequest(http.MethodPost, "/api/v1/workflows/WF-001/trigger", bytes.NewReader(body))
	triggerReq.Header.Set("Content-Type", "application/json")
	tw := httptest.NewRecorder()
	r.ServeHTTP(tw, triggerReq)

	var triggerResp map[string]string
	json.Unmarshal(tw.Body.Bytes(), &triggerResp)
	execID := triggerResp["execution_id"]

	// Wait for async execution to complete
	time.Sleep(300 * time.Millisecond)

	// Query status
	statusReq := httptest.NewRequest(http.MethodGet, "/api/v1/workflows/WF-001/status?execution_id="+execID, nil)
	sw := httptest.NewRecorder()
	r.ServeHTTP(sw, statusReq)

	if sw.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", sw.Code, sw.Body.String())
	}

	var status WorkflowStatusResponse
	if err := json.Unmarshal(sw.Body.Bytes(), &status); err != nil {
		t.Fatalf("failed to decode status: %v", err)
	}
	if status.ExecutionID != execID {
		t.Errorf("expected execution_id=%s, got %s", execID, status.ExecutionID)
	}
	if status.WorkflowID != "WF-001" {
		t.Errorf("expected workflow_id=WF-001, got %s", status.WorkflowID)
	}
	if status.Status != "completed" {
		t.Errorf("expected status=completed, got %s", status.Status)
	}
}

func TestWorkflowStatusMissingExecutionID(t *testing.T) {
	r, _ := setupWorkflowRouter()

	req := httptest.NewRequest(http.MethodGet, "/api/v1/workflows/WF-001/status", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", w.Code)
	}
}

func TestWorkflowStatusNotFoundWorkflow(t *testing.T) {
	r, _ := setupWorkflowRouter()

	req := httptest.NewRequest(http.MethodGet, "/api/v1/workflows/WF-999/status?execution_id=abc", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", w.Code)
	}
}

func TestWorkflowStatusNotFoundExecution(t *testing.T) {
	r, _ := setupWorkflowRouter()

	req := httptest.NewRequest(http.MethodGet, "/api/v1/workflows/WF-001/status?execution_id=nonexistent", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", w.Code)
	}
}

func TestNewUUID(t *testing.T) {
	id1 := newUUID()
	id2 := newUUID()
	if id1 == "" {
		t.Error("expected non-empty UUID")
	}
	if id1 == id2 {
		t.Error("expected unique UUIDs")
	}
	// Basic format check: 8-4-4-4-12
	if len(id1) != 36 {
		t.Errorf("expected UUID length 36, got %d: %s", len(id1), id1)
	}
}

func TestWorkflowManagerLifecycle(t *testing.T) {
	wm := NewWorkflowManager()

	// Initially not running
	if wm.isRunning("WF-001") {
		t.Error("expected WF-001 not running initially")
	}

	// Start
	execID := wm.start("WF-001")
	if execID == "" {
		t.Fatal("expected non-empty execution ID")
	}
	if !wm.isRunning("WF-001") {
		t.Error("expected WF-001 running after start")
	}

	// Duplicate start should fail
	dup := wm.start("WF-001")
	if dup != "" {
		t.Error("expected empty ID for duplicate start")
	}

	// Mark running
	wm.markRunning(execID)
	exec := wm.get(execID)
	if exec.Status != "running" {
		t.Errorf("expected status=running, got %s", exec.Status)
	}
	if exec.StartedAt == "" {
		t.Error("expected non-empty started_at")
	}

	// Mark completed
	wm.markCompleted(execID, map[string]any{"count": 42})
	exec = wm.get(execID)
	if exec.Status != "completed" {
		t.Errorf("expected status=completed, got %s", exec.Status)
	}
	if exec.CompletedAt == "" {
		t.Error("expected non-empty completed_at")
	}

	// Should no longer be running
	if wm.isRunning("WF-001") {
		t.Error("expected WF-001 not running after completion")
	}

	// Can start again after completion
	execID2 := wm.start("WF-001")
	if execID2 == "" {
		t.Error("expected to start WF-001 again after completion")
	}
}

func TestWorkflowManagerFailure(t *testing.T) {
	wm := NewWorkflowManager()

	execID := wm.start("WF-002")
	wm.markRunning(execID)
	wm.markFailed(execID, "something went wrong")

	exec := wm.get(execID)
	if exec.Status != "failed" {
		t.Errorf("expected status=failed, got %s", exec.Status)
	}
	if exec.Error != "something went wrong" {
		t.Errorf("expected error message, got %s", exec.Error)
	}

	// Should no longer be running
	if wm.isRunning("WF-002") {
		t.Error("expected WF-002 not running after failure")
	}
}
