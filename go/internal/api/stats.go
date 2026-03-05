package api

import (
	"math"
	"net/http"
	"sort"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/matrixorigin/issue-manager/internal/issue"
)

// handleStatsOverview handles GET /api/v1/stats/overview.
// It returns total/open/closed counts, open ratio, recent issues, and health scores.
func (s *Server) handleStatsOverview(c *gin.Context) {
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

	snapshots, err := s.Analyzer.LoadLatestSnapshots(c.Request.Context(), repoOwner, repoName)
	if err != nil {
		snapshots = []issue.Snapshot{}
	}

	total, open, closed, openRatio := computeOverviewStats(snapshots)
	recentIssues := computeRecentIssues(snapshots, time.Now(), 7, 20)
	healthScores := computeHealthScores(snapshots)

	c.JSON(http.StatusOK, OverviewResponse{
		Total:        total,
		Open:         open,
		Closed:       closed,
		OpenRatio:    openRatio,
		RecentIssues: recentIssues,
		HealthScores: healthScores,
	})
}

// handleStatsLabels handles GET /api/v1/stats/labels.
// It returns label statistics grouped by prefix (kind/, area/, customer/, etc.).
func (s *Server) handleStatsLabels(c *gin.Context) {
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

	snapshots, err := s.Analyzer.LoadLatestSnapshots(c.Request.Context(), repoOwner, repoName)
	if err != nil {
		snapshots = []issue.Snapshot{}
	}

	prefix := c.Query("prefix")
	groups := computeLabelGroups(snapshots, prefix)

	c.JSON(http.StatusOK, LabelsResponse{Groups: groups})
}

// ---------- pure computation helpers (exported for testing) ----------

// computeOverviewStats calculates total, open, closed counts and open ratio.
func computeOverviewStats(snapshots []issue.Snapshot) (total, open, closed int, openRatio float64) {
	total = len(snapshots)
	for _, s := range snapshots {
		if strings.EqualFold(s.State, "open") {
			open++
		} else {
			closed++
		}
	}
	if total > 0 {
		openRatio = math.Round(float64(open)/float64(total)*10000) / 100 // two decimal places
	}
	return
}

// computeRecentIssues returns issues updated within the last `days` days from `now`,
// sorted by updated_at descending, capped at `limit`.
func computeRecentIssues(snapshots []issue.Snapshot, now time.Time, days int, limit int) []issue.Snapshot {
	cutoff := now.AddDate(0, 0, -days)
	var recent []issue.Snapshot
	for _, s := range snapshots {
		if s.UpdatedAt != nil && !s.UpdatedAt.Before(cutoff) && !s.UpdatedAt.After(now) {
			recent = append(recent, s)
		}
	}

	// Sort by updated_at descending
	sort.SliceStable(recent, func(i, j int) bool {
		if recent[i].UpdatedAt == nil {
			return false
		}
		if recent[j].UpdatedAt == nil {
			return true
		}
		return recent[i].UpdatedAt.After(*recent[j].UpdatedAt)
	})

	if len(recent) > limit {
		recent = recent[:limit]
	}
	return recent
}

// computeHealthScores groups issues by customer/ label and calculates health scores.
// Score = 100 - (open_issues/total_issues * 50) - (blocked_issues/total_issues * 50), clamped to [0, 100].
func computeHealthScores(snapshots []issue.Snapshot) []HealthScore {
	type customerData struct {
		total   int
		open    int
		blocked int
	}
	customers := make(map[string]*customerData)

	for _, s := range snapshots {
		for _, label := range s.Labels {
			if strings.HasPrefix(label, "customer/") {
				name := label
				d, ok := customers[name]
				if !ok {
					d = &customerData{}
					customers[name] = d
				}
				d.total++
				if strings.EqualFold(s.State, "open") {
					d.open++
				}
				if s.IsBlocked {
					d.blocked++
				}
			}
		}
	}

	scores := make([]HealthScore, 0, len(customers))
	for name, d := range customers {
		score := 100.0
		if d.total > 0 {
			score = 100.0 - (float64(d.open)/float64(d.total))*50.0 - (float64(d.blocked)/float64(d.total))*50.0
		}
		// Clamp to [0, 100]
		if score < 0 {
			score = 0
		}
		if score > 100 {
			score = 100
		}
		score = math.Round(score*100) / 100 // two decimal places

		scores = append(scores, HealthScore{
			Customer:      name,
			Score:         score,
			TotalIssues:   d.total,
			OpenIssues:    d.open,
			BlockedIssues: d.blocked,
		})
	}

	// Sort by customer name for deterministic output
	sort.Slice(scores, func(i, j int) bool {
		return scores[i].Customer < scores[j].Customer
	})

	return scores
}

// defaultPrefixes are the label prefixes used when no specific prefix is requested.
var defaultPrefixes = []string{"kind/", "area/", "customer/"}

// computeLabelGroups groups label statistics by prefix.
// If prefix is empty, all default prefixes are used.
// If prefix is specified, only that prefix group is returned.
func computeLabelGroups(snapshots []issue.Snapshot, prefix string) map[string][]LabelStat {
	prefixes := defaultPrefixes
	if prefix != "" {
		prefixes = []string{prefix}
	}

	// Initialize groups
	groups := make(map[string][]LabelStat)
	for _, p := range prefixes {
		groups[p] = nil
	}

	// label -> prefix -> counts
	type labelCounts struct {
		count  int
		open   int
		closed int
	}
	labelMap := make(map[string]*labelCounts)

	for _, s := range snapshots {
		for _, label := range s.Labels {
			for _, p := range prefixes {
				if strings.HasPrefix(label, p) {
					lc, ok := labelMap[label]
					if !ok {
						lc = &labelCounts{}
						labelMap[label] = lc
					}
					lc.count++
					if strings.EqualFold(s.State, "open") {
						lc.open++
					} else {
						lc.closed++
					}
				}
			}
		}
	}

	// Build result groups
	for label, lc := range labelMap {
		for _, p := range prefixes {
			if strings.HasPrefix(label, p) {
				groups[p] = append(groups[p], LabelStat{
					Label:  label,
					Count:  lc.count,
					Open:   lc.open,
					Closed: lc.closed,
				})
			}
		}
	}

	// Sort each group by count descending for consistent output
	for p := range groups {
		if groups[p] == nil {
			groups[p] = []LabelStat{}
		}
		sort.Slice(groups[p], func(i, j int) bool {
			if groups[p][i].Count != groups[p][j].Count {
				return groups[p][i].Count > groups[p][j].Count
			}
			return groups[p][i].Label < groups[p][j].Label
		})
	}

	return groups
}
