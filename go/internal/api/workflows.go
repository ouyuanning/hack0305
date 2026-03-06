package api

import (
	"context"
	"crypto/rand"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/matrixflow/moi-core/model/mowl"
)

// WorkflowDef describes a workflow definition shown in the list endpoint.
type WorkflowDef struct {
	ID          string          `json:"id"`
	Name        string          `json:"name"`
	Description string          `json:"description"`
	Implemented bool            `json:"implemented"`
	Params      []WorkflowParam `json:"params"`
}

// WorkflowParam describes a single parameter for a workflow.
type WorkflowParam struct {
	Name         string `json:"name"`
	Label        string `json:"label"`
	Required     bool   `json:"required"`
	Type         string `json:"type"`
	DefaultValue string `json:"default_value,omitempty"`
}

// workflowExecution tracks the runtime state of a single workflow execution.
type workflowExecution struct {
	ExecutionID string         `json:"execution_id"`
	WorkflowID  string         `json:"workflow_id"`
	Status      string         `json:"status"` // queued | running | completed | failed
	Result      map[string]any `json:"result,omitempty"`
	Error       string         `json:"error,omitempty"`
	StartedAt   string         `json:"started_at,omitempty"`
	CompletedAt string         `json:"completed_at,omitempty"`
}

// workflowRegistry holds the hardcoded workflow definitions.
var workflowRegistry = []WorkflowDef{
	{
		ID: "WF-001", Name: "Issue 数据采集", Description: "从 GitHub 采集 Issue 数据并存储快照",
		Implemented: true,
		Params: []WorkflowParam{
			{Name: "repo_owner", Label: "仓库所有者", Required: true, Type: "string"},
			{Name: "repo_name", Label: "仓库名称", Required: true, Type: "string"},
			{Name: "full_sync", Label: "全量同步", Required: false, Type: "boolean", DefaultValue: "false"},
			{Name: "since", Label: "起始时间", Required: false, Type: "datetime"},
		},
	},
	{
		ID: "WF-002", Name: "知识库生成", Description: "基于 Issue 数据生成产品知识库",
		Implemented: true,
		Params: []WorkflowParam{
			{Name: "repo_owner", Label: "仓库所有者", Required: true, Type: "string"},
			{Name: "repo_name", Label: "仓库名称", Required: true, Type: "string"},
		},
	},
	{
		ID: "WF-003", Name: "自动提 Issue", Description: "AI 智能生成 Issue 草稿",
		Implemented: true,
		Params: []WorkflowParam{
			{Name: "repo_owner", Label: "仓库所有者", Required: true, Type: "string"},
			{Name: "repo_name", Label: "仓库名称", Required: true, Type: "string"},
		},
	},
	{
		ID: "WF-004", Name: "创建 Issue", Description: "将 Issue 草稿提交到 GitHub",
		Implemented: true,
		Params: []WorkflowParam{
			{Name: "repo_owner", Label: "仓库所有者", Required: true, Type: "string"},
			{Name: "repo_name", Label: "仓库名称", Required: true, Type: "string"},
		},
	},
	{
		ID: "WF-005", Name: "历史数据清洗", Description: "清洗和补全历史 Issue 数据的 AI 分析字段",
		Implemented: true,
		Params: []WorkflowParam{
			{Name: "repo_owner", Label: "仓库所有者", Required: true, Type: "string"},
			{Name: "repo_name", Label: "仓库名称", Required: true, Type: "string"},
		},
	},
	{
		ID: "WF-006", Name: "特殊 Issue 状态记录", Description: "记录 Issue 状态变更日志",
		Implemented: true,
		Params: []WorkflowParam{
			{Name: "repo_owner", Label: "仓库所有者", Required: true, Type: "string"},
			{Name: "repo_name", Label: "仓库名称", Required: true, Type: "string"},
		},
	},
	{
		ID: "WF-007", Name: "分析报告生成", Description: "生成多维度 Issue 分析报告",
		Implemented: true,
		Params: []WorkflowParam{
			{Name: "repo_owner", Label: "仓库所有者", Required: true, Type: "string"},
			{Name: "repo_name", Label: "仓库名称", Required: true, Type: "string"},
		},
	},
}

// workflowDefByID returns the workflow definition for the given ID, or nil.
func workflowDefByID(id string) *WorkflowDef {
	for i := range workflowRegistry {
		if workflowRegistry[i].ID == id {
			return &workflowRegistry[i]
		}
	}
	return nil
}

// WorkflowManager manages in-memory workflow execution state.
type WorkflowManager struct {
	mu         sync.RWMutex
	executions map[string]*workflowExecution // keyed by execution_id
	running    map[string]string             // workflow_id -> execution_id (only for queued/running)
}

// NewWorkflowManager creates a new WorkflowManager.
func NewWorkflowManager() *WorkflowManager {
	return &WorkflowManager{
		executions: make(map[string]*workflowExecution),
		running:    make(map[string]string),
	}
}

// isRunning checks if a workflow is currently queued or running.
func (wm *WorkflowManager) isRunning(workflowID string) bool {
	wm.mu.RLock()
	defer wm.mu.RUnlock()
	_, ok := wm.running[workflowID]
	return ok
}

// start creates a new execution in queued state and returns its ID.
// Returns empty string if the workflow is already running.
func (wm *WorkflowManager) start(workflowID string) string {
	wm.mu.Lock()
	defer wm.mu.Unlock()
	if _, ok := wm.running[workflowID]; ok {
		return ""
	}
	execID := newUUID()
	exec := &workflowExecution{
		ExecutionID: execID,
		WorkflowID:  workflowID,
		Status:      "queued",
	}
	wm.executions[execID] = exec
	wm.running[workflowID] = execID
	return execID
}

// markRunning transitions an execution to running state.
func (wm *WorkflowManager) markRunning(execID string) {
	wm.mu.Lock()
	defer wm.mu.Unlock()
	if exec, ok := wm.executions[execID]; ok {
		exec.Status = "running"
		exec.StartedAt = time.Now().Format(time.RFC3339)
	}
}

// markCompleted transitions an execution to completed state.
func (wm *WorkflowManager) markCompleted(execID string, result map[string]any) {
	wm.mu.Lock()
	defer wm.mu.Unlock()
	if exec, ok := wm.executions[execID]; ok {
		exec.Status = "completed"
		exec.Result = result
		exec.CompletedAt = time.Now().Format(time.RFC3339)
		delete(wm.running, exec.WorkflowID)
	}
}

// markFailed transitions an execution to failed state.
func (wm *WorkflowManager) markFailed(execID string, errMsg string) {
	wm.mu.Lock()
	defer wm.mu.Unlock()
	if exec, ok := wm.executions[execID]; ok {
		exec.Status = "failed"
		exec.Error = errMsg
		exec.CompletedAt = time.Now().Format(time.RFC3339)
		delete(wm.running, exec.WorkflowID)
	}
}

// get returns a copy of the execution state.
func (wm *WorkflowManager) get(execID string) *workflowExecution {
	wm.mu.RLock()
	defer wm.mu.RUnlock()
	exec, ok := wm.executions[execID]
	if !ok {
		return nil
	}
	// return a copy
	cp := *exec
	return &cp
}

// newUUID generates a v4 UUID string without external dependencies.
func newUUID() string {
	var buf [16]byte
	_, _ = rand.Read(buf[:])
	buf[6] = (buf[6] & 0x0f) | 0x40 // version 4
	buf[8] = (buf[8] & 0x3f) | 0x80 // variant 10
	return fmt.Sprintf("%08x-%04x-%04x-%04x-%012x",
		buf[0:4], buf[4:6], buf[6:8], buf[8:10], buf[10:16])
}

// ---------- HTTP Handlers ----------

// handleListWorkflows handles GET /api/v1/workflows.
func (s *Server) handleListWorkflows(c *gin.Context) {
	c.JSON(http.StatusOK, workflowRegistry)
}

// handleTriggerWorkflow handles POST /api/v1/workflows/:id/trigger.
func (s *Server) handleTriggerWorkflow(c *gin.Context) {
	wfID := c.Param("id")
	def := workflowDefByID(wfID)
	if def == nil {
		c.JSON(http.StatusNotFound, ErrorResponse{
			Code:    http.StatusNotFound,
			Message: "workflow not found",
			Detail:  "unknown workflow id: " + wfID,
		})
		return
	}

	var req TriggerWorkflowRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Code:    http.StatusBadRequest,
			Message: "invalid request body",
			Detail:  err.Error(),
		})
		return
	}

	execID := s.Workflows.start(wfID)
	if execID == "" {
		c.JSON(http.StatusConflict, ErrorResponse{
			Code:    http.StatusConflict,
			Message: "workflow is already running",
			Detail:  "workflow " + wfID + " has an active execution",
		})
		return
	}

	// Launch async execution
	go s.executeWorkflow(execID, wfID, req)

	c.JSON(http.StatusAccepted, gin.H{
		"execution_id": execID,
		"status":       "queued",
	})
}

// handleWorkflowStatus handles GET /api/v1/workflows/:id/status.
func (s *Server) handleWorkflowStatus(c *gin.Context) {
	wfID := c.Param("id")
	if workflowDefByID(wfID) == nil {
		c.JSON(http.StatusNotFound, ErrorResponse{
			Code:    http.StatusNotFound,
			Message: "workflow not found",
			Detail:  "unknown workflow id: " + wfID,
		})
		return
	}

	execID := c.Query("execution_id")
	if execID == "" {
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Code:    http.StatusBadRequest,
			Message: "missing required parameter",
			Detail:  "execution_id query parameter is required",
		})
		return
	}

	exec := s.Workflows.get(execID)
	if exec == nil {
		c.JSON(http.StatusNotFound, ErrorResponse{
			Code:    http.StatusNotFound,
			Message: "execution not found",
			Detail:  "no execution found with id: " + execID,
		})
		return
	}

	c.JSON(http.StatusOK, WorkflowStatusResponse{
		ExecutionID: exec.ExecutionID,
		WorkflowID:  exec.WorkflowID,
		Status:      exec.Status,
		Result:      exec.Result,
		Error:       exec.Error,
		StartedAt:   exec.StartedAt,
		CompletedAt: exec.CompletedAt,
	})
}

// executeWorkflow runs the workflow asynchronously in a goroutine.
func (s *Server) executeWorkflow(execID, wfID string, req TriggerWorkflowRequest) {
	s.Workflows.markRunning(execID)

	ctx := context.Background()
	var err error
	var result map[string]any

	if s.WorkflowEnv == nil {
		s.Workflows.markFailed(execID, "workflow engine not initialized")
		return
	}

	switch wfID {
	case "WF-001":
		result, err = s.runWF001(ctx, req)
	case "WF-002":
		result, err = s.runWF002(ctx, req)
	case "WF-003":
		result, err = s.runWF003(ctx, req)
	case "WF-004":
		err = fmt.Errorf("WF-004 需要先通过 WF-003 生成草稿，请使用「创建 Issue」页面操作")
	case "WF-005":
		result, err = s.runWF005(ctx, req)
	case "WF-006":
		result, err = s.runWF006(ctx, req)
	case "WF-007":
		result, err = s.runWF007(ctx, req)
	default:
		err = fmt.Errorf("workflow %s not yet implemented for direct execution", wfID)
	}

	if err != nil {
		s.Workflows.markFailed(execID, err.Error())
		return
	}
	s.Workflows.markCompleted(execID, result)
}

// msgFrom encodes v as a MowlMessage.
func msgFrom(v any) (*mowl.MowlMessage, error) {
	data, err := json.Marshal(v)
	if err != nil {
		return nil, err
	}
	return &mowl.MowlMessage{Data: string(data)}, nil
}

// runWF001 runs: collect → parse → relations → store
func (s *Server) runWF001(ctx context.Context, req TriggerWorkflowRequest) (map[string]any, error) {
	in := map[string]any{
		"repo_owner": req.RepoOwner,
		"repo_name":  req.RepoName,
		"full_sync":  req.FullSync,
		"since":      req.Since,
	}
	msg, err := msgFrom(in)
	if err != nil {
		return nil, err
	}
	msg, err = s.WorkflowEnv.HandleCollect(ctx, msg)
	if err != nil {
		return nil, fmt.Errorf("collect: %w", err)
	}

	// Extract issue count from collect output for summary
	var collectOut struct {
		Issues []json.RawMessage `json:"issues"`
	}
	_ = json.Unmarshal([]byte(msg.Data), &collectOut)
	issueCount := len(collectOut.Issues)

	msg, err = s.WorkflowEnv.HandleParse(ctx, msg)
	if err != nil {
		return nil, fmt.Errorf("parse: %w", err)
	}

	// Extract parse stats
	var parseOut struct {
		Snapshots []json.RawMessage `json:"snapshots"`
		Comments  []json.RawMessage `json:"comments"`
		AIParse   []json.RawMessage `json:"ai_parse"`
	}
	_ = json.Unmarshal([]byte(msg.Data), &parseOut)

	msg, err = s.WorkflowEnv.HandleRelations(ctx, msg)
	if err != nil {
		return nil, fmt.Errorf("relations: %w", err)
	}

	// Extract relations count
	var relOut struct {
		Relations []json.RawMessage `json:"relations"`
	}
	_ = json.Unmarshal([]byte(msg.Data), &relOut)

	msg, err = s.WorkflowEnv.HandleStore(ctx, msg)
	if err != nil {
		return nil, fmt.Errorf("store: %w", err)
	}

	return map[string]any{
		"workflow_type":  "WF-001",
		"issue_count":    issueCount,
		"comment_count":  len(parseOut.Comments),
		"ai_parsed":      len(parseOut.AIParse),
		"relation_count": len(relOut.Relations),
		"repo":           req.RepoOwner + "/" + req.RepoName,
	}, nil
}

// runWF002 runs: knowledge.build
func (s *Server) runWF002(ctx context.Context, req TriggerWorkflowRequest) (map[string]any, error) {
	in := map[string]any{"repo_owner": req.RepoOwner, "repo_name": req.RepoName}
	msg, err := msgFrom(in)
	if err != nil {
		return nil, err
	}
	msg, err = s.WorkflowEnv.HandleKnowledge(ctx, msg)
	if err != nil {
		return nil, err
	}
	// Count approximate sections in the generated knowledge base markdown
	sectionCount := 0
	for _, line := range splitLines(msg.Data) {
		if len(line) > 0 && line[0] == '#' {
			sectionCount++
		}
	}
	return map[string]any{
		"workflow_type":  "WF-002",
		"content_length": len(msg.Data),
		"section_count":  sectionCount,
		"repo":           req.RepoOwner + "/" + req.RepoName,
	}, nil
}

// runWF003 runs: draft.generate (auto-generate issue draft from existing data)
func (s *Server) runWF003(ctx context.Context, req TriggerWorkflowRequest) (map[string]any, error) {
	in := map[string]any{
		"repo_owner":        req.RepoOwner,
		"repo_name":         req.RepoName,
		"user_input":        "根据现有 Issue 数据，自动发现并生成新的 Issue 草稿",
		"browser_issue_url": "",
	}
	msg, err := msgFrom(in)
	if err != nil {
		return nil, err
	}
	msg, err = s.WorkflowEnv.HandleDraft(ctx, msg)
	if err != nil {
		return nil, err
	}
	var draft struct {
		Title        string   `json:"title"`
		Body         string   `json:"body"`
		Labels       []string `json:"labels"`
		Assignees    []string `json:"assignees"`
		TemplateType string   `json:"template_type"`
	}
	_ = json.Unmarshal([]byte(msg.Data), &draft)
	return map[string]any{
		"workflow_type":   "WF-003",
		"draft_title":     draft.Title,
		"draft_body":      draft.Body,
		"draft_labels":    draft.Labels,
		"draft_assignees": draft.Assignees,
		"label_count":     len(draft.Labels),
		"template_type":   draft.TemplateType,
		"repo":            req.RepoOwner + "/" + req.RepoName,
	}, nil
}

// runWF005 runs: cleanup
func (s *Server) runWF005(ctx context.Context, req TriggerWorkflowRequest) (map[string]any, error) {
	in := map[string]any{"repo_owner": req.RepoOwner, "repo_name": req.RepoName}
	msg, err := msgFrom(in)
	if err != nil {
		return nil, err
	}

	// Load snapshots before cleanup to count how many need AI enrichment
	issues, _ := s.Analyzer.LoadLatestSnapshots(ctx, req.RepoOwner, req.RepoName)
	totalCount := len(issues)
	needCleanup := 0
	for _, it := range issues {
		if it.AISummary == "" {
			needCleanup++
		}
	}

	if _, err = s.WorkflowEnv.HandleCleanup(ctx, msg); err != nil {
		return nil, err
	}
	return map[string]any{
		"workflow_type": "WF-005",
		"total_issues":  totalCount,
		"cleaned_count": needCleanup,
		"repo":          req.RepoOwner + "/" + req.RepoName,
	}, nil
}

// runWF006 runs: state.track
func (s *Server) runWF006(ctx context.Context, req TriggerWorkflowRequest) (map[string]any, error) {
	in := map[string]any{"repo_owner": req.RepoOwner, "repo_name": req.RepoName}
	msg, err := msgFrom(in)
	if err != nil {
		return nil, err
	}

	// Load snapshots to count tracked issues
	issues, _ := s.Analyzer.LoadLatestSnapshots(ctx, req.RepoOwner, req.RepoName)
	statusCounts := map[string]int{}
	for _, it := range issues {
		statusCounts[it.State]++
	}

	if _, err = s.WorkflowEnv.HandleStateTrack(ctx, msg); err != nil {
		return nil, err
	}
	return map[string]any{
		"workflow_type": "WF-006",
		"tracked_count": len(issues),
		"open_count":    statusCounts["open"],
		"closed_count":  statusCounts["closed"],
		"repo":          req.RepoOwner + "/" + req.RepoName,
	}, nil
}

// runWF007 runs: report.generate
func (s *Server) runWF007(ctx context.Context, req TriggerWorkflowRequest) (map[string]any, error) {
	in := map[string]any{"repo_owner": req.RepoOwner, "repo_name": req.RepoName}
	msg, err := msgFrom(in)
	if err != nil {
		return nil, err
	}
	if _, err = s.WorkflowEnv.HandleReport(ctx, msg); err != nil {
		return nil, err
	}
	reportTypes := []string{"daily", "progress", "extensible", "comprehensive", "shared_features", "risk_analysis"}
	return map[string]any{
		"workflow_type": "WF-007",
		"report_count":  len(reportTypes),
		"report_types":  reportTypes,
		"repo":          req.RepoOwner + "/" + req.RepoName,
	}, nil
}

// splitLines splits a string by newline characters.
func splitLines(s string) []string {
	return strings.Split(s, "\n")
}
