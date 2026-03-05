package issue

import "time"

type Snapshot struct {
	IssueID            int64      `json:"issue_id"`
	IssueNumber        int        `json:"issue_number"`
	RepoOwner          string     `json:"repo_owner"`
	RepoName           string     `json:"repo_name"`
	Title              string     `json:"title"`
	Body               string     `json:"body"`
	State              string     `json:"state"`
	IssueType          string     `json:"issue_type"`
	Priority           string     `json:"priority"`
	Assignee           string     `json:"assignee,omitempty"`
	Labels             []string   `json:"labels"`
	Milestone          string     `json:"milestone,omitempty"`
	CreatedAt          *time.Time `json:"created_at,omitempty"`
	UpdatedAt          *time.Time `json:"updated_at,omitempty"`
	ClosedAt           *time.Time `json:"closed_at,omitempty"`
	AISummary          string     `json:"ai_summary"`
	AITags             []string   `json:"ai_tags"`
	AIPriority         string     `json:"ai_priority"`
	Status             string     `json:"status"`
	ProgressPercentage float64    `json:"progress_percentage"`
	IsBlocked          bool       `json:"is_blocked"`
	BlockedReason      string     `json:"blocked_reason,omitempty"`
	SnapshotTime       time.Time  `json:"snapshot_time"`
}

type Comment struct {
	IssueID     int64      `json:"issue_id"`
	IssueNumber int        `json:"issue_number"`
	CommentID   int64      `json:"comment_id"`
	User        string     `json:"user"`
	Body        string     `json:"body"`
	CreatedAt   *time.Time `json:"created_at,omitempty"`
	UpdatedAt   *time.Time `json:"updated_at,omitempty"`
}

type Relation struct {
	FromIssueID      int64     `json:"from_issue_id"`
	ToIssueID        int64     `json:"to_issue_id"`
	ToIssueNumber    int       `json:"to_issue_number"`
	RelationType     string    `json:"relation_type"`
	RelationSemantic string    `json:"relation_semantic"`
	CreatedAt        time.Time `json:"created_at"`
	Source           string    `json:"source"`
	ContextText      string    `json:"context_text"`
}

type Draft struct {
	Title         string   `json:"title"`
	Body          string   `json:"body"`
	Labels        []string `json:"labels"`
	Assignees     []string `json:"assignees"`
	TemplateType  string   `json:"template_type"`
	RelatedIssues []string `json:"related_issues"`
}
