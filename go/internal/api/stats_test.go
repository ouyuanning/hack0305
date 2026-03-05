package api

import (
	"math"
	"testing"
	"time"

	"github.com/matrixorigin/issue-manager/internal/issue"
)

func statsSnapshots() []issue.Snapshot {
	return []issue.Snapshot{
		{
			IssueNumber: 1, State: "open", Labels: []string{"kind/bug", "area/auth", "customer/acme"},
			UpdatedAt: makeTime("2025-06-10T10:00:00Z"), IsBlocked: false,
		},
		{
			IssueNumber: 2, State: "open", Labels: []string{"kind/feature", "area/ui", "customer/acme"},
			UpdatedAt: makeTime("2025-06-09T10:00:00Z"), IsBlocked: true,
		},
		{
			IssueNumber: 3, State: "closed", Labels: []string{"kind/bug", "area/core", "customer/acme"},
			UpdatedAt: makeTime("2025-06-08T10:00:00Z"), IsBlocked: false,
		},
		{
			IssueNumber: 4, State: "closed", Labels: []string{"kind/docs", "customer/beta"},
			UpdatedAt: makeTime("2025-05-01T10:00:00Z"), IsBlocked: false,
		},
		{
			IssueNumber: 5, State: "open", Labels: []string{"kind/bug", "customer/beta"},
			UpdatedAt: makeTime("2025-06-11T10:00:00Z"), IsBlocked: true,
		},
	}
}

func TestComputeOverviewStats(t *testing.T) {
	snaps := statsSnapshots()
	total, open, closed, openRatio := computeOverviewStats(snaps)

	if total != 5 {
		t.Errorf("total: got %d, want 5", total)
	}
	if open != 3 {
		t.Errorf("open: got %d, want 3", open)
	}
	if closed != 2 {
		t.Errorf("closed: got %d, want 2", closed)
	}
	if total != open+closed {
		t.Errorf("total (%d) != open (%d) + closed (%d)", total, open, closed)
	}
	expectedRatio := math.Round(float64(3)/float64(5)*10000) / 100
	if openRatio != expectedRatio {
		t.Errorf("openRatio: got %f, want %f", openRatio, expectedRatio)
	}
}

func TestComputeOverviewStatsEmpty(t *testing.T) {
	total, open, closed, openRatio := computeOverviewStats(nil)
	if total != 0 || open != 0 || closed != 0 || openRatio != 0 {
		t.Errorf("expected all zeros for empty input, got total=%d open=%d closed=%d ratio=%f", total, open, closed, openRatio)
	}
}

func TestComputeRecentIssues(t *testing.T) {
	snaps := statsSnapshots()
	now, _ := time.Parse(time.RFC3339, "2025-06-12T00:00:00Z")

	recent := computeRecentIssues(snaps, now, 7, 20)

	// Issues updated within [2025-06-05, 2025-06-12]: #1 (Jun 10), #2 (Jun 9), #3 (Jun 8), #5 (Jun 11)
	if len(recent) != 4 {
		t.Errorf("expected 4 recent issues, got %d", len(recent))
	}

	// Should be sorted by updated_at descending
	for i := 1; i < len(recent); i++ {
		if recent[i-1].UpdatedAt.Before(*recent[i].UpdatedAt) {
			t.Errorf("recent issues not sorted desc at index %d", i)
		}
	}

	// First should be #5 (Jun 11)
	if len(recent) > 0 && recent[0].IssueNumber != 5 {
		t.Errorf("expected first recent issue to be #5, got #%d", recent[0].IssueNumber)
	}
}

func TestComputeRecentIssuesLimit(t *testing.T) {
	snaps := statsSnapshots()
	now, _ := time.Parse(time.RFC3339, "2025-06-12T00:00:00Z")

	recent := computeRecentIssues(snaps, now, 7, 2)
	if len(recent) != 2 {
		t.Errorf("expected 2 recent issues (limit), got %d", len(recent))
	}
}

func TestComputeRecentIssuesEmpty(t *testing.T) {
	now, _ := time.Parse(time.RFC3339, "2025-06-12T00:00:00Z")
	recent := computeRecentIssues(nil, now, 7, 20)
	if len(recent) != 0 {
		t.Errorf("expected 0 recent issues for nil input, got %d", len(recent))
	}
}

func TestComputeHealthScores(t *testing.T) {
	snaps := statsSnapshots()
	scores := computeHealthScores(snaps)

	// We have customer/acme (3 issues: 2 open, 1 blocked) and customer/beta (2 issues: 1 open, 1 blocked)
	if len(scores) != 2 {
		t.Fatalf("expected 2 health scores, got %d", len(scores))
	}

	// Sorted by customer name: acme first, beta second
	acme := scores[0]
	beta := scores[1]

	if acme.Customer != "customer/acme" {
		t.Errorf("expected first customer to be customer/acme, got %s", acme.Customer)
	}
	if acme.TotalIssues != 3 {
		t.Errorf("acme total: got %d, want 3", acme.TotalIssues)
	}
	if acme.OpenIssues != 2 {
		t.Errorf("acme open: got %d, want 2", acme.OpenIssues)
	}
	if acme.BlockedIssues != 1 {
		t.Errorf("acme blocked: got %d, want 1", acme.BlockedIssues)
	}
	// Score = 100 - (2/3 * 50) - (1/3 * 50) = 100 - 33.33 - 16.67 = 50.0
	expectedAcmeScore := math.Round((100.0-(2.0/3.0*50.0)-(1.0/3.0*50.0))*100) / 100
	if acme.Score != expectedAcmeScore {
		t.Errorf("acme score: got %f, want %f", acme.Score, expectedAcmeScore)
	}

	if beta.Customer != "customer/beta" {
		t.Errorf("expected second customer to be customer/beta, got %s", beta.Customer)
	}
	if beta.TotalIssues != 2 {
		t.Errorf("beta total: got %d, want 2", beta.TotalIssues)
	}
	if beta.OpenIssues != 1 {
		t.Errorf("beta open: got %d, want 1", beta.OpenIssues)
	}
	if beta.BlockedIssues != 1 {
		t.Errorf("beta blocked: got %d, want 1", beta.BlockedIssues)
	}
	// Score = 100 - (1/2 * 50) - (1/2 * 50) = 100 - 25 - 25 = 50.0
	if beta.Score != 50.0 {
		t.Errorf("beta score: got %f, want 50.0", beta.Score)
	}

	// All scores should be in [0, 100]
	for _, s := range scores {
		if s.Score < 0 || s.Score > 100 {
			t.Errorf("score for %s out of range: %f", s.Customer, s.Score)
		}
	}
}

func TestComputeHealthScoresEmpty(t *testing.T) {
	scores := computeHealthScores(nil)
	if len(scores) != 0 {
		t.Errorf("expected 0 health scores for nil input, got %d", len(scores))
	}
}

func TestComputeHealthScoresNoCustomerLabels(t *testing.T) {
	snaps := []issue.Snapshot{
		{IssueNumber: 1, State: "open", Labels: []string{"kind/bug"}},
		{IssueNumber: 2, State: "closed", Labels: []string{"area/core"}},
	}
	scores := computeHealthScores(snaps)
	if len(scores) != 0 {
		t.Errorf("expected 0 health scores when no customer labels, got %d", len(scores))
	}
}

func TestComputeLabelGroupsDefault(t *testing.T) {
	snaps := statsSnapshots()
	groups := computeLabelGroups(snaps, "")

	// Should have kind/, area/, customer/ groups
	if len(groups) != 3 {
		t.Errorf("expected 3 groups, got %d", len(groups))
	}

	kindGroup := groups["kind/"]
	if kindGroup == nil {
		t.Fatal("kind/ group is nil")
	}
	// kind/bug appears in issues #1, #3, #5 = 3 times
	// kind/feature appears in issue #2 = 1 time
	// kind/docs appears in issue #4 = 1 time
	if len(kindGroup) != 3 {
		t.Errorf("expected 3 kind labels, got %d", len(kindGroup))
	}
	// Sorted by count desc, so kind/bug should be first
	if kindGroup[0].Label != "kind/bug" || kindGroup[0].Count != 3 {
		t.Errorf("expected kind/bug with count 3 first, got %s with count %d", kindGroup[0].Label, kindGroup[0].Count)
	}

	// Verify open/closed counts for kind/bug: 2 open (#1, #5), 1 closed (#3)
	if kindGroup[0].Open != 2 || kindGroup[0].Closed != 1 {
		t.Errorf("kind/bug: got open=%d closed=%d, want open=2 closed=1", kindGroup[0].Open, kindGroup[0].Closed)
	}
}

func TestComputeLabelGroupsWithPrefix(t *testing.T) {
	snaps := statsSnapshots()
	groups := computeLabelGroups(snaps, "customer/")

	if len(groups) != 1 {
		t.Errorf("expected 1 group for prefix filter, got %d", len(groups))
	}

	customerGroup := groups["customer/"]
	if customerGroup == nil {
		t.Fatal("customer/ group is nil")
	}
	// customer/acme: 3 issues, customer/beta: 2 issues
	if len(customerGroup) != 2 {
		t.Errorf("expected 2 customer labels, got %d", len(customerGroup))
	}
	if customerGroup[0].Label != "customer/acme" || customerGroup[0].Count != 3 {
		t.Errorf("expected customer/acme with count 3 first, got %s with count %d", customerGroup[0].Label, customerGroup[0].Count)
	}
}

func TestComputeLabelGroupsEmpty(t *testing.T) {
	groups := computeLabelGroups(nil, "")
	for _, p := range defaultPrefixes {
		if groups[p] == nil {
			t.Errorf("expected empty slice for prefix %s, got nil", p)
		}
		if len(groups[p]) != 0 {
			t.Errorf("expected 0 labels for prefix %s, got %d", p, len(groups[p]))
		}
	}
}
