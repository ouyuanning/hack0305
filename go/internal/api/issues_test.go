package api

import (
	"testing"
	"time"

	"github.com/matrixorigin/issue-manager/internal/issue"
)

func makeTime(s string) *time.Time {
	t, _ := time.Parse(time.RFC3339, s)
	return &t
}

func sampleSnapshots() []issue.Snapshot {
	return []issue.Snapshot{
		{
			IssueNumber: 1, Title: "Bug in login", Body: "Login fails on mobile",
			State: "open", Assignee: "alice", Labels: []string{"kind/bug", "area/auth"},
			Priority: "high", CreatedAt: makeTime("2025-01-10T00:00:00Z"), UpdatedAt: makeTime("2025-01-15T00:00:00Z"),
		},
		{
			IssueNumber: 2, Title: "Add dark mode", Body: "Support dark theme",
			State: "open", Assignee: "bob", Labels: []string{"kind/feature", "area/ui"},
			Priority: "medium", CreatedAt: makeTime("2025-01-12T00:00:00Z"), UpdatedAt: makeTime("2025-01-14T00:00:00Z"),
		},
		{
			IssueNumber: 3, Title: "Fix crash on startup", Body: "App crashes when opening",
			State: "closed", Assignee: "alice", Labels: []string{"kind/bug", "area/core"},
			Priority: "critical", CreatedAt: makeTime("2025-01-05T00:00:00Z"), UpdatedAt: makeTime("2025-01-08T00:00:00Z"),
		},
		{
			IssueNumber: 4, Title: "Update docs", Body: "Documentation needs refresh",
			State: "closed", Assignee: "charlie", Labels: []string{"kind/docs"},
			Priority: "low", CreatedAt: makeTime("2025-01-01T00:00:00Z"), UpdatedAt: makeTime("2025-01-03T00:00:00Z"),
		},
	}
}

func TestFilterByState(t *testing.T) {
	all := sampleSnapshots()

	open := filterIssues(all, "open", nil, "", "", time.Time{}, time.Time{}, false, false)
	if len(open) != 2 {
		t.Errorf("expected 2 open issues, got %d", len(open))
	}

	closed := filterIssues(all, "closed", nil, "", "", time.Time{}, time.Time{}, false, false)
	if len(closed) != 2 {
		t.Errorf("expected 2 closed issues, got %d", len(closed))
	}

	allState := filterIssues(all, "all", nil, "", "", time.Time{}, time.Time{}, false, false)
	if len(allState) != 4 {
		t.Errorf("expected 4 issues for state=all, got %d", len(allState))
	}
}

func TestFilterByLabels(t *testing.T) {
	all := sampleSnapshots()

	bugOnly := filterIssues(all, "", []string{"kind/bug"}, "", "", time.Time{}, time.Time{}, false, false)
	if len(bugOnly) != 2 {
		t.Errorf("expected 2 bug issues, got %d", len(bugOnly))
	}

	bugAuth := filterIssues(all, "", []string{"kind/bug", "area/auth"}, "", "", time.Time{}, time.Time{}, false, false)
	if len(bugAuth) != 1 {
		t.Errorf("expected 1 issue with kind/bug AND area/auth, got %d", len(bugAuth))
	}
}

func TestFilterByAssignee(t *testing.T) {
	all := sampleSnapshots()

	alice := filterIssues(all, "", nil, "alice", "", time.Time{}, time.Time{}, false, false)
	if len(alice) != 2 {
		t.Errorf("expected 2 issues for alice, got %d", len(alice))
	}

	// case-insensitive
	aliceUpper := filterIssues(all, "", nil, "Alice", "", time.Time{}, time.Time{}, false, false)
	if len(aliceUpper) != 2 {
		t.Errorf("expected 2 issues for Alice (case-insensitive), got %d", len(aliceUpper))
	}
}

func TestFilterByKeyword(t *testing.T) {
	all := sampleSnapshots()

	// keyword in title
	login := filterIssues(all, "", nil, "", "login", time.Time{}, time.Time{}, false, false)
	if len(login) != 1 {
		t.Errorf("expected 1 issue matching 'login', got %d", len(login))
	}

	// keyword in body (case-insensitive)
	mobile := filterIssues(all, "", nil, "", "MOBILE", time.Time{}, time.Time{}, false, false)
	if len(mobile) != 1 {
		t.Errorf("expected 1 issue matching 'MOBILE' (case-insensitive), got %d", len(mobile))
	}

	// keyword matching nothing
	none := filterIssues(all, "", nil, "", "nonexistent", time.Time{}, time.Time{}, false, false)
	if len(none) != 0 {
		t.Errorf("expected 0 issues matching 'nonexistent', got %d", len(none))
	}
}

func TestFilterByDateRange(t *testing.T) {
	all := sampleSnapshots()

	start, _ := time.Parse(time.RFC3339, "2025-01-10T00:00:00Z")
	end, _ := time.Parse(time.RFC3339, "2025-01-15T23:59:59Z")

	result := filterIssues(all, "", nil, "", "", start, end, true, true)
	if len(result) != 2 {
		t.Errorf("expected 2 issues in date range, got %d", len(result))
	}
}

func TestFilterCombined(t *testing.T) {
	all := sampleSnapshots()

	// open + alice + keyword "login"
	result := filterIssues(all, "open", nil, "alice", "login", time.Time{}, time.Time{}, false, false)
	if len(result) != 1 {
		t.Errorf("expected 1 issue for combined filter, got %d", len(result))
	}
	if result[0].IssueNumber != 1 {
		t.Errorf("expected issue #1, got #%d", result[0].IssueNumber)
	}
}

func TestSortByIssueNumber(t *testing.T) {
	items := sampleSnapshots()

	sortIssues(items, "issue_number", "asc")
	for i := 1; i < len(items); i++ {
		if items[i-1].IssueNumber > items[i].IssueNumber {
			t.Errorf("not sorted asc by issue_number at index %d", i)
		}
	}

	sortIssues(items, "issue_number", "desc")
	for i := 1; i < len(items); i++ {
		if items[i-1].IssueNumber < items[i].IssueNumber {
			t.Errorf("not sorted desc by issue_number at index %d", i)
		}
	}
}

func TestSortByUpdatedAt(t *testing.T) {
	items := sampleSnapshots()

	sortIssues(items, "updated_at", "desc")
	for i := 1; i < len(items); i++ {
		if items[i-1].UpdatedAt.Before(*items[i].UpdatedAt) {
			t.Errorf("not sorted desc by updated_at at index %d", i)
		}
	}
}

func TestSortByPriority(t *testing.T) {
	items := sampleSnapshots()

	sortIssues(items, "priority", "desc")
	if items[0].Priority != "critical" {
		t.Errorf("expected critical first when sorted desc by priority, got %s", items[0].Priority)
	}
	if items[len(items)-1].Priority != "low" {
		t.Errorf("expected low last when sorted desc by priority, got %s", items[len(items)-1].Priority)
	}
}

func TestQueryInt(t *testing.T) {
	// queryInt is tested indirectly via handler, but we can test priorityRank
	tests := []struct {
		input string
		want  int
	}{
		{"critical", 4},
		{"high", 3},
		{"medium", 2},
		{"low", 1},
		{"unknown", 0},
		{"", 0},
	}
	for _, tt := range tests {
		got := priorityRank(tt.input)
		if got != tt.want {
			t.Errorf("priorityRank(%q) = %d, want %d", tt.input, got, tt.want)
		}
	}
}
