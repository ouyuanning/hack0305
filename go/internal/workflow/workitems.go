package workflow

import (
	"context"
	"encoding/json"
	"fmt"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/matrixorigin/issue-manager/internal/analysis"
	"github.com/matrixorigin/issue-manager/internal/browser"
	"github.com/matrixorigin/issue-manager/internal/email"
	"github.com/matrixorigin/issue-manager/internal/github"
	"github.com/matrixorigin/issue-manager/internal/issue"
	"github.com/matrixorigin/issue-manager/internal/llm"
	"github.com/matrixorigin/issue-manager/internal/storage"
	"github.com/matrixorigin/issue-manager/internal/templates"

	moi "github.com/matrixflow/moi-core/go-sdk"
	"github.com/matrixflow/moi-core/model/catalog"
	"github.com/matrixflow/moi-core/model/mowl"
)

type Env struct {
	GitHub            *github.Client
	LLM               *llm.Client
	Store             *storage.VolumeStore
	Analyzer          *analysis.Generator
	WorkspaceID       string
	Client            *moi.Client
	BrowserCDP        string
	BrowserCDPEnabled bool
	Templates         *templates.Store
	MirrorLocal       bool
	MirrorPath        string
	SMTPConfig        email.Config
	EmailTo           string
}

// ---------- Input/Output types ----------

type CollectInput struct {
	RepoOwner string `json:"repo_owner"`
	RepoName  string `json:"repo_name"`
	FullSync  bool   `json:"full_sync"`
	Since     string `json:"since"`
}

type IssueWithComments struct {
	Issue    github.Issue     `json:"issue"`
	Comments []github.Comment `json:"comments"`
}

type CollectOutput struct {
	RepoOwner string              `json:"repo_owner"`
	RepoName  string              `json:"repo_name"`
	Snapshot  time.Time           `json:"snapshot_time"`
	Issues    []IssueWithComments `json:"issues"`
}

type ParseOutput struct {
	RepoOwner string              `json:"repo_owner"`
	RepoName  string              `json:"repo_name"`
	Snapshot  time.Time           `json:"snapshot_time"`
	Snapshots []issue.Snapshot    `json:"snapshots"`
	Comments  []issue.Comment     `json:"comments"`
	AIParse   []map[string]any    `json:"ai_parse"`
	RawIssues []IssueWithComments `json:"raw_issues"`
}

type RelationsOutput struct {
	RepoOwner string           `json:"repo_owner"`
	RepoName  string           `json:"repo_name"`
	Snapshot  time.Time        `json:"snapshot_time"`
	Snapshots []issue.Snapshot `json:"snapshots"`
	Comments  []issue.Comment  `json:"comments"`
	AIParse   []map[string]any `json:"ai_parse"`
	Relations []issue.Relation `json:"relations"`
}

type StoreOutput struct {
	Manifest storage.Manifest `json:"manifest"`
}

// ---------- WorkItem handlers ----------

func RegisterWorkItems(worker *moi.WorkerClient, env *Env) error {
	specs := []struct {
		Name    string
		ID      string
		Handler moi.ExternalWorkItemFunc
	}{
		{"github.collect", "issue:github.collect", env.handleCollect},
		{"ai.parse", "issue:ai.parse", env.handleParse},
		{"relations.extract", "issue:relations.extract", env.handleRelations},
		{"store.snapshot", "issue:store.snapshot", env.handleStore},
		{"knowledge.build", "issue:knowledge.build", env.handleKnowledge},
		{"draft.generate", "issue:draft.generate", env.handleDraft},
		{"issue.create", "issue:create", env.handleCreateIssue},
		{"cleanup", "issue:cleanup", env.handleCleanup},
		{"state.track", "issue:state.track", env.handleStateTrack},
		{"report.generate", "issue:report.generate", env.handleReport},
	}
	for _, s := range specs {
		md := &mowl.WorkItemMetadata{Description: s.Name}
		if err := worker.RegisterWorkItem(s.ID, md, s.Handler); err != nil {
			return err
		}
	}
	return nil
}

func (e *Env) handleCollect(ctx context.Context, _ moi.WorkItemContext, msg *mowl.MowlMessage) (*mowl.MowlMessage, error) {
	var in CollectInput
	if err := json.Unmarshal([]byte(msg.Data), &in); err != nil {
		return nil, err
	}
	var since *time.Time
	if strings.TrimSpace(in.Since) != "" {
		if t, err := time.Parse(time.RFC3339, in.Since); err == nil {
			since = &t
		}
	}
	// FetchIssues now handles all pagination internally via since-cursor
	allIssues, _, err := e.GitHub.FetchIssues(ctx, in.RepoOwner, in.RepoName, "all", since, 1, 100)
	if err != nil {
		return nil, err
	}
	issues := make([]IssueWithComments, 0, len(allIssues))
	for _, it := range allIssues {
		comments, _ := e.GitHub.FetchComments(ctx, in.RepoOwner, in.RepoName, it.Number)
		issues = append(issues, IssueWithComments{Issue: it, Comments: comments})
	}
	out := CollectOutput{RepoOwner: in.RepoOwner, RepoName: in.RepoName, Snapshot: time.Now(), Issues: issues}
	data, _ := json.Marshal(out)
	return &mowl.MowlMessage{Data: string(data)}, nil
}

func (e *Env) handleParse(ctx context.Context, _ moi.WorkItemContext, msg *mowl.MowlMessage) (*mowl.MowlMessage, error) {
	var in CollectOutput
	if err := json.Unmarshal([]byte(msg.Data), &in); err != nil {
		return nil, err
	}
	var snapshots []issue.Snapshot
	var comments []issue.Comment
	var aiParse []map[string]any

	for _, it := range in.Issues {
		issueData := it.Issue
		title := safe(issueData.Title)
		body := safe(issueData.Body)
		classification := e.classifyIssue(ctx, title, body)
		summary := classification.Summary
		priority := classification.Priority
		tags := classification.Tags
		issueType := classification.Type
		blocked := classification.BlockedReason

		snap := issue.Snapshot{
			IssueID:            issueData.ID,
			IssueNumber:        issueData.Number,
			RepoOwner:          in.RepoOwner,
			RepoName:           in.RepoName,
			Title:              title,
			Body:               body,
			State:              issueData.State,
			IssueType:          issueType,
			Priority:           priority,
			Assignee:           getAssignee(issueData.Assignee),
			Labels:             extractLabels(issueData.Labels),
			Milestone:          getMilestone(issueData.Milestone),
			CreatedAt:          parseTime(issueData.CreatedAt),
			UpdatedAt:          parseTime(issueData.UpdatedAt),
			ClosedAt:           parseTimePtr(issueData.ClosedAt),
			AISummary:          summary,
			AITags:             tags,
			AIPriority:         priority,
			Status:             inferStatus(issueData.State, issueData.Assignee),
			ProgressPercentage: inferProgress(issueData.State),
			IsBlocked:          blocked != "",
			BlockedReason:      blocked,
			SnapshotTime:       in.Snapshot,
		}
		snapshots = append(snapshots, snap)
		aiParse = append(aiParse, map[string]any{
			"issue_id":       issueData.ID,
			"issue_number":   issueData.Number,
			"type":           issueType,
			"priority":       priority,
			"tags":           tags,
			"summary":        summary,
			"blocked_reason": blocked,
		})

		for _, c := range it.Comments {
			comments = append(comments, issue.Comment{
				IssueID:     issueData.ID,
				IssueNumber: issueData.Number,
				CommentID:   c.ID,
				User:        c.User.Login,
				Body:        c.Body,
				CreatedAt:   parseTime(c.CreatedAt),
				UpdatedAt:   parseTime(c.UpdatedAt),
			})
		}
	}

	out := ParseOutput{RepoOwner: in.RepoOwner, RepoName: in.RepoName, Snapshot: in.Snapshot, Snapshots: snapshots, Comments: comments, AIParse: aiParse, RawIssues: in.Issues}
	data, _ := json.Marshal(out)
	return &mowl.MowlMessage{Data: string(data)}, nil
}

func (e *Env) handleRelations(ctx context.Context, _ moi.WorkItemContext, msg *mowl.MowlMessage) (*mowl.MowlMessage, error) {
	var in ParseOutput
	if err := json.Unmarshal([]byte(msg.Data), &in); err != nil {
		return nil, err
	}
	rels := []issue.Relation{}
	for _, it := range in.RawIssues {
		rels = append(rels, extractRelations(it.Issue.ID, it.Issue.Number, it.Issue.Body, it.Comments)...)
	}
	// fill to_issue_id by number map
	numToID := map[int]int64{}
	for _, s := range in.Snapshots {
		numToID[s.IssueNumber] = s.IssueID
	}
	for i := range rels {
		if id, ok := numToID[rels[i].ToIssueNumber]; ok {
			rels[i].ToIssueID = id
		}
	}
	out := RelationsOutput{RepoOwner: in.RepoOwner, RepoName: in.RepoName, Snapshot: in.Snapshot, Snapshots: in.Snapshots, Comments: in.Comments, AIParse: in.AIParse, Relations: rels}
	data, _ := json.Marshal(out)
	return &mowl.MowlMessage{Data: string(data)}, nil
}

func (e *Env) handleStore(ctx context.Context, _ moi.WorkItemContext, msg *mowl.MowlMessage) (*mowl.MowlMessage, error) {
	var in RelationsOutput
	if err := json.Unmarshal([]byte(msg.Data), &in); err != nil {
		return nil, err
	}
	base := e.Store.SnapshotPath(in.RepoOwner, in.RepoName, in.Snapshot)
	files := map[string]*catalog.File{}

	issuesLines := mustNDJSON(in.Snapshots)
	commentsLines := mustNDJSON(in.Comments)
	relationsLines := mustNDJSON(in.Relations)
	aiLines := mustNDJSON(in.AIParse)

	f1, err := e.Store.UploadNDJSON(ctx, base+"/issues.ndjson", issuesLines)
	if err != nil {
		return nil, err
	}
	f2, err := e.Store.UploadNDJSON(ctx, base+"/comments.ndjson", commentsLines)
	if err != nil {
		return nil, err
	}
	f3, err := e.Store.UploadNDJSON(ctx, base+"/relations.ndjson", relationsLines)
	if err != nil {
		return nil, err
	}
	f4, err := e.Store.UploadNDJSON(ctx, base+"/ai_parse.ndjson", aiLines)
	if err != nil {
		return nil, err
	}

	files["issues"] = f1
	files["comments"] = f2
	files["relations"] = f3
	files["ai_parse"] = f4

	manifest := storage.Manifest{SnapshotTime: in.Snapshot.Format(time.RFC3339), Files: map[string]storage.ManifestRef{}}
	for k, f := range files {
		manifest.Files[k] = storage.ManifestRef{ID: f.GetId(), Name: f.GetName(), Size: f.GetSize()}
	}

	_, err = e.Store.UploadJSON(ctx, base+"/manifest.json", manifest)
	if err != nil {
		return nil, err
	}
	_, err = e.Store.UploadJSON(ctx, e.Store.LatestPath(in.RepoOwner, in.RepoName)+"/manifest.json", manifest)
	if err != nil {
		return nil, err
	}

	out := StoreOutput{Manifest: manifest}
	data, _ := json.Marshal(out)
	return &mowl.MowlMessage{Data: string(data)}, nil
}

func (e *Env) handleKnowledge(ctx context.Context, _ moi.WorkItemContext, msg *mowl.MowlMessage) (*mowl.MowlMessage, error) {
	var in CollectInput
	if err := json.Unmarshal([]byte(msg.Data), &in); err != nil {
		return nil, err
	}
	issues, err := e.Analyzer.LoadLatestSnapshots(ctx, in.RepoOwner, in.RepoName)
	if err != nil {
		return nil, err
	}
	// sample up to 200
	sample := issues
	if len(sample) > 200 {
		sample = sample[:200]
	}
	labels := map[string]int{}
	for _, it := range issues {
		for _, l := range it.Labels {
			labels[l]++
		}
	}
	topLabels := topN(labels, 30)

	prompt := buildKnowledgePrompt(sample, topLabels)
	resp, err := e.LLM.Ask(ctx, knowledgeSystemPrompt(), prompt)
	if err != nil {
		return nil, err
	}
	kbName := fmt.Sprintf("issue-kb-%s-%s", in.RepoOwner, in.RepoName)
	ts := time.Now().Format("20060102")
	base := e.Store.PathForRepo(in.RepoOwner, in.RepoName) + "/knowledge"
	path := base + fmt.Sprintf("/%s_%s_knowledge_%s.md", in.RepoOwner, in.RepoName, ts)
	latestPath := base + fmt.Sprintf("/%s_%s_knowledge_latest.md", in.RepoOwner, in.RepoName)
	file, err := e.Store.UploadBytes(ctx, path, []byte(resp), "text/markdown")
	if err != nil {
		return nil, err
	}
	if _, err := e.Store.UploadBytes(ctx, latestPath, []byte(resp), "text/markdown"); err != nil {
		return nil, err
	}
	if e.MirrorLocal {
		localBase := fmt.Sprintf("%s/knowledge_base", e.MirrorPath)
		_ = analysis.WriteLocal(fmt.Sprintf("%s/%s_%s_knowledge_%s.md", localBase, in.RepoOwner, in.RepoName, ts), []byte(resp))
		_ = analysis.WriteLocal(fmt.Sprintf("%s/%s_%s_knowledge_latest.md", localBase, in.RepoOwner, in.RepoName), []byte(resp))
	}

	kbFiles := &catalog.KnowledgeBaseFiles{FileIds: []string{file.GetId()}}
	kbSvc := e.Client.KnowledgeBases(e.WorkspaceID)
	list, err := kbSvc.List(ctx)
	if err != nil {
		return nil, err
	}
	var existing *catalog.KnowledgeBase
	for _, kb := range list.Items {
		if kb.GetName() == kbName {
			existing = kb
			break
		}
	}
	if existing == nil {
		_, err = kbSvc.Create(ctx, kbName, moi.WithKnowledgeBaseUsageNotes("auto-generated"), moi.WithKnowledgeBaseFiles(kbFiles))
	} else {
		_, err = kbSvc.Update(ctx, existing.GetId(), moi.WithKnowledgeBaseFilesUpdate(kbFiles))
	}
	if err != nil {
		return nil, err
	}
	return &mowl.MowlMessage{Data: string(resp)}, nil
}

func (e *Env) handleDraft(ctx context.Context, _ moi.WorkItemContext, msg *mowl.MowlMessage) (*mowl.MowlMessage, error) {
	var in map[string]any
	if err := json.Unmarshal([]byte(msg.Data), &in); err != nil {
		return nil, err
	}
	repoOwner := fmt.Sprintf("%v", in["repo_owner"])
	repoName := fmt.Sprintf("%v", in["repo_name"])
	userInput := fmt.Sprintf("%v", in["user_input"])
	images := ""
	if v, ok := in["images"]; ok {
		images = fmt.Sprintf("%v", v)
	}
	issueURL := fmt.Sprintf("%v", in["browser_issue_url"])
	if strings.TrimSpace(issueURL) == "" {
		if url, _ := browser.DetectIssueURLWithCDP(ctx, e.BrowserCDP, e.BrowserCDPEnabled); url != "" {
			issueURL = url
		}
	}
	issues, _ := e.Analyzer.LoadLatestSnapshots(ctx, repoOwner, repoName)
	related := findRelated(issues, userInput, 5)

	templateText := ""
	if e.Templates != nil {
		templateText = e.Templates.Pick(guessTemplateType(userInput))
	}
	prompt := buildDraftPrompt(userInput, related, issueURL, templateText, images)
	resp, err := e.LLM.Ask(ctx, draftSystemPrompt(), prompt)
	if err != nil {
		return nil, err
	}
	var draft issue.Draft
	if err := json.Unmarshal([]byte(resp), &draft); err != nil {
		// fallback to raw text
		draft = issue.Draft{Title: "", Body: resp}
	}
	if draft.TemplateType == "" {
		draft.TemplateType = guessTemplateType(userInput)
	}
	data, _ := json.Marshal(draft)
	ts := time.Now().Format("20060102_150405")
	base := e.Store.PathForRepo(repoOwner, repoName) + "/drafts"
	jsonPath := base + fmt.Sprintf("/draft_%s.json", ts)
	htmlPath := base + fmt.Sprintf("/preview_%s.html", ts)
	_, _ = e.Store.UploadBytes(ctx, jsonPath, data, "application/json")
	preview := renderDraftHTML(draft, issueURL)
	_, _ = e.Store.UploadBytes(ctx, htmlPath, []byte(preview), "text/html")
	if e.MirrorLocal {
		_ = analysis.WriteLocal(fmt.Sprintf("%s/drafts/draft_%s.json", e.MirrorPath, ts), data)
		_ = analysis.WriteLocal(fmt.Sprintf("%s/drafts/preview_%s.html", e.MirrorPath, ts), []byte(preview))
	}
	return &mowl.MowlMessage{Data: string(data)}, nil
}

func (e *Env) handleCreateIssue(ctx context.Context, _ moi.WorkItemContext, msg *mowl.MowlMessage) (*mowl.MowlMessage, error) {
	var in map[string]any
	if err := json.Unmarshal([]byte(msg.Data), &in); err != nil {
		return nil, err
	}
	owner := fmt.Sprintf("%v", in["repo_owner"])
	repo := fmt.Sprintf("%v", in["repo_name"])
	title := fmt.Sprintf("%v", in["title"])
	body := fmt.Sprintf("%v", in["body"])
	labels := toStringSlice(in["labels"])
	assignees := toStringSlice(in["assignees"])
	out, err := e.GitHub.CreateIssue(ctx, owner, repo, title, body, labels, assignees)
	if err != nil {
		return nil, err
	}
	data, _ := json.Marshal(out)
	return &mowl.MowlMessage{Data: string(data)}, nil
}

func (e *Env) handleCleanup(ctx context.Context, _ moi.WorkItemContext, msg *mowl.MowlMessage) (*mowl.MowlMessage, error) {
	var in CollectInput
	if err := json.Unmarshal([]byte(msg.Data), &in); err != nil {
		return nil, err
	}
	issues, err := e.Analyzer.LoadLatestSnapshots(ctx, in.RepoOwner, in.RepoName)
	if err != nil {
		return nil, err
	}
	var updated []issue.Snapshot
	for _, it := range issues {
		if it.AISummary == "" {
			c := e.classifyIssue(ctx, it.Title, it.Body)
			it.AISummary = c.Summary
			it.AITags = c.Tags
			it.AIPriority = c.Priority
			it.IssueType = c.Type
			it.BlockedReason = c.BlockedReason
			it.IsBlocked = c.BlockedReason != ""
		}
		updated = append(updated, it)
	}
	// write as new snapshot
	base := e.Store.SnapshotPath(in.RepoOwner, in.RepoName, time.Now())
	lines := mustNDJSON(updated)
	file, err := e.Store.UploadNDJSON(ctx, base+"/issues.ndjson", lines)
	if err != nil {
		return nil, err
	}
	manifest := storage.Manifest{SnapshotTime: time.Now().Format(time.RFC3339), Files: map[string]storage.ManifestRef{"issues": {ID: file.GetId(), Name: file.GetName(), Size: file.GetSize()}}}
	_, err = e.Store.UploadJSON(ctx, base+"/manifest.json", manifest)
	if err != nil {
		return nil, err
	}
	return &mowl.MowlMessage{Data: "ok"}, nil
}

func (e *Env) handleStateTrack(ctx context.Context, _ moi.WorkItemContext, msg *mowl.MowlMessage) (*mowl.MowlMessage, error) {
	var in CollectInput
	if err := json.Unmarshal([]byte(msg.Data), &in); err != nil {
		return nil, err
	}
	issues, err := e.Analyzer.LoadLatestSnapshots(ctx, in.RepoOwner, in.RepoName)
	if err != nil {
		return nil, err
	}
	logEntries := []map[string]any{}
	for _, it := range issues {
		logEntries = append(logEntries, map[string]any{
			"issue_number": it.IssueNumber,
			"status":       it.Status,
			"state":        it.State,
			"assignee":     it.Assignee,
			"updated_at":   it.UpdatedAt,
		})
	}
	path := e.Store.PathForRepo(in.RepoOwner, in.RepoName) + "/state/state_log_" + time.Now().Format("20060102") + ".json"
	_, err = e.Store.UploadJSON(ctx, path, logEntries)
	if err != nil {
		return nil, err
	}
	return &mowl.MowlMessage{Data: "ok"}, nil
}

func (e *Env) handleReport(ctx context.Context, _ moi.WorkItemContext, msg *mowl.MowlMessage) (*mowl.MowlMessage, error) {
	var in CollectInput
	if err := json.Unmarshal([]byte(msg.Data), &in); err != nil {
		return nil, err
	}
	day := time.Now()
	daily, err := e.Analyzer.DailyReport(ctx, in.RepoOwner, in.RepoName, day)
	if err != nil {
		return nil, err
	}
	progress, err := e.Analyzer.ProgressReport(ctx, in.RepoOwner, in.RepoName)
	if err != nil {
		return nil, err
	}
	extensible, err := e.Analyzer.ExtensibleReport(ctx, in.RepoOwner, in.RepoName)
	if err != nil {
		return nil, err
	}
	extMD := analysis.ExtensibleMarkdown(extensible)
	comprehensive, sharedReport, riskReport, customerReports, err := e.Analyzer.ComprehensiveReport(ctx, in.RepoOwner, in.RepoName)
	if err != nil {
		return nil, err
	}
	compMD := analysis.ComprehensiveMarkdown(comprehensive)
	base := e.Store.PathForRepo(in.RepoOwner, in.RepoName) + "/reports/"
	bundle, _ := e.Analyzer.LoadLatestBundle(ctx, in.RepoOwner, in.RepoName)
	issues := []issue.Snapshot{}
	if bundle != nil {
		issues = bundle.Snapshots
	}
	dayStr := day.Format("20060102")
	_, err = e.Store.UploadJSON(ctx, base+fmt.Sprintf("daily_report_%s_%s_%s.json", in.RepoOwner, in.RepoName, dayStr), daily)
	if err != nil {
		return nil, err
	}
	_, err = e.Store.UploadJSON(ctx, base+fmt.Sprintf("progress_report_%s_%s_%s.json", in.RepoOwner, in.RepoName, dayStr), progress)
	if err != nil {
		return nil, err
	}
	_, _ = e.Store.UploadJSON(ctx, base+fmt.Sprintf("extensible_analysis_%s.json", dayStr), extensible)
	_, _ = e.Store.UploadBytes(ctx, base+fmt.Sprintf("extensible_analysis_%s.md", dayStr), []byte(extMD), "text/markdown")
	_, _ = e.Store.UploadJSON(ctx, base+fmt.Sprintf("comprehensive_report_%s.json", dayStr), comprehensive)
	_, _ = e.Store.UploadBytes(ctx, base+fmt.Sprintf("comprehensive_report_%s.md", dayStr), []byte(compMD), "text/markdown")
	_, _ = e.Store.UploadJSON(ctx, base+fmt.Sprintf("shared_features_%s.json", dayStr), sharedReport)
	_, _ = e.Store.UploadBytes(ctx, base+fmt.Sprintf("shared_features_%s.md", dayStr), []byte(sharedFeaturesMarkdown(sharedReport)), "text/markdown")
	_, _ = e.Store.UploadJSON(ctx, base+fmt.Sprintf("risk_analysis_%s.json", dayStr), riskReport)

	// customer reports
	for customer, report := range customerReports {
		report["hierarchy_progress"] = analysis.HierarchyProgress(issues, customer)
		cjson := base + fmt.Sprintf("customer_reports/%s_report_%s.json", customer, dayStr)
		cmd := analysis.CustomerMarkdown(customer, report)
		cmdPath := base + fmt.Sprintf("customer_reports/%s_report_%s.md", customer, dayStr)
		_, _ = e.Store.UploadJSON(ctx, cjson, report)
		_, _ = e.Store.UploadBytes(ctx, cmdPath, []byte(cmd), "text/markdown")
	}

	if e.MirrorLocal {
		_ = analysis.WriteLocal(fmt.Sprintf("%s/daily_report_%s_%s_%s.json", e.MirrorPath, in.RepoOwner, in.RepoName, dayStr), mustJSON(daily))
		_ = analysis.WriteLocal(fmt.Sprintf("%s/progress_report_%s_%s_%s.json", e.MirrorPath, in.RepoOwner, in.RepoName, dayStr), mustJSON(progress))
		_ = analysis.WriteLocal(fmt.Sprintf("%s/extensible_analysis_%s.json", e.MirrorPath, dayStr), mustJSON(extensible))
		_ = analysis.WriteLocal(fmt.Sprintf("%s/extensible_analysis_%s.md", e.MirrorPath, dayStr), []byte(extMD))
		_ = analysis.WriteLocal(fmt.Sprintf("%s/comprehensive_report_%s.json", e.MirrorPath, dayStr), mustJSON(comprehensive))
		_ = analysis.WriteLocal(fmt.Sprintf("%s/comprehensive_report_%s.md", e.MirrorPath, dayStr), []byte(compMD))
		_ = analysis.WriteLocal(fmt.Sprintf("%s/shared_features_%s.json", e.MirrorPath, dayStr), mustJSON(sharedReport))
		_ = analysis.WriteLocal(fmt.Sprintf("%s/shared_features_%s.md", e.MirrorPath, dayStr), []byte(sharedFeaturesMarkdown(sharedReport)))
		_ = analysis.WriteLocal(fmt.Sprintf("%s/risk_analysis_%s.json", e.MirrorPath, dayStr), mustJSON(riskReport))
		for customer, report := range customerReports {
			_ = analysis.WriteLocal(fmt.Sprintf("%s/customer_reports/%s_report_%s.json", e.MirrorPath, customer, dayStr), mustJSON(report))
			_ = analysis.WriteLocal(fmt.Sprintf("%s/customer_reports/%s_report_%s.md", e.MirrorPath, customer, dayStr), []byte(analysis.CustomerMarkdown(customer, report)))
		}
	}
	if strings.TrimSpace(e.EmailTo) != "" && e.SMTPConfig.Host != "" {
		subject := fmt.Sprintf("Issue Report %s/%s %s", in.RepoOwner, in.RepoName, dayStr)
		body := fmt.Sprintf("Daily: %v\nProgress: %v\nExtensible: %v\nComprehensive: %v\n", daily, progress, extensible, comprehensive)
		_ = email.Send(e.SMTPConfig, []string{e.EmailTo}, subject, body)
	}
	return &mowl.MowlMessage{Data: "ok"}, nil
}

// ---------- helpers ----------

type classification struct {
	Type          string
	Priority      string
	Tags          []string
	Summary       string
	BlockedReason string
}

func (e *Env) classifyIssue(ctx context.Context, title, body string) classification {
	system := "You are an assistant that classifies GitHub issues. Respond with JSON only."
	user := fmt.Sprintf(`Analyze the issue and return JSON with fields: type, priority, tags (array), summary, blocked_reason.
Title: %s
Body: %s`, title, body)
	resp, err := e.LLM.Ask(ctx, system, user)
	if err == nil {
		var out struct {
			Type          string   `json:"type"`
			Priority      string   `json:"priority"`
			Tags          []string `json:"tags"`
			Summary       string   `json:"summary"`
			BlockedReason string   `json:"blocked_reason"`
		}
		if json.Unmarshal([]byte(resp), &out) == nil {
			return classification{Type: fallback(out.Type, "task"), Priority: fallback(out.Priority, "P2"), Tags: out.Tags, Summary: out.Summary, BlockedReason: out.BlockedReason}
		}
	}
	// fallback
	return classification{Type: inferType(title, body), Priority: inferPriority(title, body), Tags: []string{}, Summary: title, BlockedReason: ""}
}

func inferType(title, body string) string {
	text := strings.ToLower(title + " " + body)
	switch {
	case strings.Contains(text, "bug") || strings.Contains(text, "error") || strings.Contains(text, "失败"):
		return "bug"
	case strings.Contains(text, "feature") || strings.Contains(text, "需求"):
		return "feature"
	default:
		return "task"
	}
}

func inferPriority(title, body string) string {
	text := strings.ToLower(title + " " + body)
	switch {
	case strings.Contains(text, "p0") || strings.Contains(text, "紧急"):
		return "P0"
	case strings.Contains(text, "p1") || strings.Contains(text, "高"):
		return "P1"
	case strings.Contains(text, "p2"):
		return "P2"
	default:
		return "P3"
	}
}

func extractLabels(labels []github.Label) []string {
	out := make([]string, 0, len(labels))
	for _, l := range labels {
		out = append(out, l.Name)
	}
	sort.Strings(out)
	return out
}

func getAssignee(u *github.User) string {
	if u == nil {
		return ""
	}
	return u.Login
}

func getMilestone(m *github.Milestone) string {
	if m == nil {
		return ""
	}
	return m.Title
}

func parseTime(val string) *time.Time {
	t, err := time.Parse(time.RFC3339, val)
	if err != nil {
		return nil
	}
	return &t
}

func parseTimePtr(val *string) *time.Time {
	if val == nil {
		return nil
	}
	return parseTime(*val)
}

func inferStatus(state string, assignee *github.User) string {
	if state == "closed" {
		return "已关闭"
	}
	if assignee != nil {
		return "处理中"
	}
	return "待处理"
}

func inferProgress(state string) float64 {
	if state == "closed" {
		return 100
	}
	return 0
}

func safe(s string) string {
	return strings.TrimSpace(s)
}

var issuePattern = regexp.MustCompile(`#(\d+)`)

func extractRelations(issueID int64, issueNumber int, body string, comments []github.Comment) []issue.Relation {
	rels := []issue.Relation{}
	texts := []struct{ source, text string }{{"body", body}}
	for _, c := range comments {
		texts = append(texts, struct{ source, text string }{"comment", c.Body})
	}
	for _, t := range texts {
		if t.text == "" {
			continue
		}
		matches := issuePattern.FindAllStringSubmatchIndex(t.text, -1)
		for _, m := range matches {
			numStr := t.text[m[2]:m[3]]
			num, _ := strconv.Atoi(numStr)
			if num == issueNumber {
				continue
			}
			ctxStart := max(0, m[0]-50)
			ctxEnd := min(len(t.text), m[1]+50)
			context := strings.ToLower(t.text[ctxStart:ctxEnd])
			relType, relSem := "mention", "提及"
			switch {
			case strings.Contains(context, "fixes") || strings.Contains(context, "修复"):
				relType, relSem = "fixes", "修复"
			case strings.Contains(context, "duplicate") || strings.Contains(context, "重复"):
				relType, relSem = "duplicate", "重复"
			case strings.Contains(context, "related") || strings.Contains(context, "相关"):
				relType, relSem = "related", "相关"
			case strings.Contains(context, "blocks") || strings.Contains(context, "阻塞"):
				relType, relSem = "blocks", "阻塞"
			case strings.Contains(context, "depends on") || strings.Contains(context, "依赖"):
				relType, relSem = "depends_on", "依赖"
			}
			rels = append(rels, issue.Relation{
				FromIssueID:      issueID,
				ToIssueNumber:    num,
				RelationType:     relType,
				RelationSemantic: relSem,
				CreatedAt:        time.Now(),
				Source:           t.source,
				ContextText:      strings.TrimSpace(t.text[ctxStart:ctxEnd]),
			})
		}
	}
	return rels
}

func mustNDJSON(items any) [][]byte {
	var lines [][]byte
	switch v := items.(type) {
	case []issue.Snapshot:
		for _, it := range v {
			b, _ := json.Marshal(it)
			lines = append(lines, b)
		}
	case []issue.Comment:
		for _, it := range v {
			b, _ := json.Marshal(it)
			lines = append(lines, b)
		}
	case []issue.Relation:
		for _, it := range v {
			b, _ := json.Marshal(it)
			lines = append(lines, b)
		}
	case []map[string]any:
		for _, it := range v {
			b, _ := json.Marshal(it)
			lines = append(lines, b)
		}
	default:
		b, _ := json.Marshal(v)
		lines = append(lines, b)
	}
	return lines
}

func fallback(v, def string) string {
	if strings.TrimSpace(v) == "" {
		return def
	}
	return v
}

func topN(m map[string]int, n int) []string {
	type kv struct {
		k string
		v int
	}
	var list []kv
	for k, v := range m {
		list = append(list, kv{k, v})
	}
	sort.Slice(list, func(i, j int) bool { return list[i].v > list[j].v })
	if len(list) > n {
		list = list[:n]
	}
	out := make([]string, 0, len(list))
	for _, kv := range list {
		out = append(out, kv.k)
	}
	return out
}

func buildKnowledgePrompt(sample []issue.Snapshot, labels []string) string {
	b, _ := json.Marshal(sample)
	return fmt.Sprintf("Sample issues: %s\nTop labels: %v\nGenerate a knowledge base markdown.", string(b), labels)
}

func knowledgeSystemPrompt() string {
	return "You are a product analyst. Produce a markdown knowledge base summarizing modules, labels, and common issues."
}

func buildDraftPrompt(input string, related []issue.Snapshot, issueURL, template, images string) string {
	b, _ := json.Marshal(related)
	return fmt.Sprintf("User input: %s\nBrowser issue URL: %s\nImages: %s\nTemplate:\n%s\nRelated issues: %s\nGenerate issue draft JSON.", input, issueURL, images, template, string(b))
}

func draftSystemPrompt() string {
	return "Generate a JSON issue draft with fields: title, body, labels, assignees, template_type, related_issues."
}

func findRelated(issues []issue.Snapshot, input string, limit int) []issue.Snapshot {
	input = strings.ToLower(input)
	var matches []issue.Snapshot
	for _, it := range issues {
		if strings.Contains(strings.ToLower(it.Title), input) || strings.Contains(strings.ToLower(it.Body), input) {
			matches = append(matches, it)
		}
		if len(matches) >= limit {
			break
		}
	}
	return matches
}

func toStringSlice(v any) []string {
	out := []string{}
	switch val := v.(type) {
	case []string:
		return val
	case []any:
		for _, it := range val {
			out = append(out, fmt.Sprintf("%v", it))
		}
	}
	return out
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func mustJSON(v any) []byte {
	data, _ := json.MarshalIndent(v, "", "  ")
	return data
}

func renderDraftHTML(d issue.Draft, issueURL string) string {
	return fmt.Sprintf(`<!doctype html>
<html>
<head><meta charset="utf-8"><title>Issue Preview</title></head>
<body>
<h1>%s</h1>
<p><strong>Issue URL:</strong> %s</p>
<p><strong>Labels:</strong> %s</p>
<p><strong>Assignees:</strong> %s</p>
<pre>%s</pre>
</body>
</html>`,
		escapeHTML(d.Title),
		escapeHTML(issueURL),
		escapeHTML(strings.Join(d.Labels, ", ")),
		escapeHTML(strings.Join(d.Assignees, ", ")),
		escapeHTML(d.Body),
	)
}

func escapeHTML(s string) string {
	replacer := strings.NewReplacer(
		"&", "&amp;",
		"<", "&lt;",
		">", "&gt;",
		"\"", "&quot;",
		"'", "&#39;",
	)
	return replacer.Replace(s)
}

func guessTemplateType(input string) string {
	text := strings.ToLower(input)
	switch {
	case strings.Contains(text, "bug") || strings.Contains(text, "错误") || strings.Contains(text, "异常"):
		return "bug"
	case strings.Contains(text, "feature") || strings.Contains(text, "需求"):
		return "feature"
	default:
		return "task"
	}
}

func sharedFeaturesMarkdown(report map[string]any) string {
	gen := fmt.Sprintf("%v", report["generated_at"])
	summary, _ := report["summary"].(map[string]any)
	features, _ := report["features"].([]map[string]any)
	lines := []string{
		"# 跨项目共用Feature分析报告",
		"",
		fmt.Sprintf("**生成时间**: %s", gen),
		"",
		"---",
		"",
		"## 📊 总体情况",
		"",
		fmt.Sprintf("- **共用Feature总数**: %v", summary["total_shared_features"]),
		fmt.Sprintf("- **高风险（3+客户）**: %v", summary["high_risk"]),
		fmt.Sprintf("- **中风险（2客户）**: %v", summary["medium_risk"]),
		"",
		"---",
		"",
		"## 📋 详细列表",
		"",
	}
	for i, f := range features {
		risk := fmt.Sprintf("%v", f["risk_level"])
		emoji := "🟡"
		if risk == "high" {
			emoji = "🔴"
		}
		customers := []string{}
		if c, ok := f["customers"].([]string); ok {
			customers = c
		} else if c, ok := f["customers"].([]any); ok {
			for _, v := range c {
				customers = append(customers, fmt.Sprintf("%v", v))
			}
		}
		lines = append(lines,
			fmt.Sprintf("### %d. %s Feature #%v", i+1, emoji, f["feature_number"]),
			"",
			fmt.Sprintf("**标题**: %v  ", f["feature_title"]),
			fmt.Sprintf("**涉及客户**: %s  ", strings.Join(customers, ", ")),
			fmt.Sprintf("**客户数量**: %v  ", f["customer_count"]),
			fmt.Sprintf("**风险等级**: %v", f["risk_level"]),
			"",
			fmt.Sprintf("**风险说明**: 此Feature被%v个客户项目依赖，需求可能存在差异，建议：", f["customer_count"]),
			"- 明确各客户的具体需求差异",
			"- 评估是否需要拆分为多个Feature",
			"- 协调开发优先级",
			"",
			"---",
			"",
		)
	}
	return strings.Join(lines, "\n")
}

// ---------- Public wrappers for direct invocation from API layer ----------

// HandleCollect is the public wrapper for handleCollect.
func (e *Env) HandleCollect(ctx context.Context, msg *mowl.MowlMessage) (*mowl.MowlMessage, error) {
	return e.handleCollect(ctx, nil, msg)
}

// HandleParse is the public wrapper for handleParse.
func (e *Env) HandleParse(ctx context.Context, msg *mowl.MowlMessage) (*mowl.MowlMessage, error) {
	return e.handleParse(ctx, nil, msg)
}

// HandleRelations is the public wrapper for handleRelations.
func (e *Env) HandleRelations(ctx context.Context, msg *mowl.MowlMessage) (*mowl.MowlMessage, error) {
	return e.handleRelations(ctx, nil, msg)
}

// HandleStore is the public wrapper for handleStore.
func (e *Env) HandleStore(ctx context.Context, msg *mowl.MowlMessage) (*mowl.MowlMessage, error) {
	return e.handleStore(ctx, nil, msg)
}

// HandleKnowledge is the public wrapper for handleKnowledge.
func (e *Env) HandleKnowledge(ctx context.Context, msg *mowl.MowlMessage) (*mowl.MowlMessage, error) {
	return e.handleKnowledge(ctx, nil, msg)
}

// HandleCleanup is the public wrapper for handleCleanup.
func (e *Env) HandleCleanup(ctx context.Context, msg *mowl.MowlMessage) (*mowl.MowlMessage, error) {
	return e.handleCleanup(ctx, nil, msg)
}

// HandleStateTrack is the public wrapper for handleStateTrack.
func (e *Env) HandleStateTrack(ctx context.Context, msg *mowl.MowlMessage) (*mowl.MowlMessage, error) {
	return e.handleStateTrack(ctx, nil, msg)
}

// HandleReport is the public wrapper for handleReport.
func (e *Env) HandleReport(ctx context.Context, msg *mowl.MowlMessage) (*mowl.MowlMessage, error) {
	return e.handleReport(ctx, nil, msg)
}
