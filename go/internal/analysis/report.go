package analysis

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/matrixorigin/issue-manager/internal/issue"
	"github.com/matrixorigin/issue-manager/internal/storage"
)

type Generator struct {
	store *storage.VolumeStore
}

func New(store *storage.VolumeStore) *Generator {
	return &Generator{store: store}
}

func (g *Generator) LoadLatestSnapshots(ctx context.Context, owner, repo string) ([]issue.Snapshot, error) {
	m, err := g.loadLatestManifest(ctx, owner, repo)
	if err != nil {
		return nil, err
	}
	ref, ok := m.Files["issues"]
	if !ok {
		return nil, fmt.Errorf("manifest missing issues file")
	}
	data, err := g.store.Download(ctx, ref.ID)
	if err != nil {
		return nil, err
	}
	return decodeSnapshots(data)
}

func decodeSnapshots(data []byte) ([]issue.Snapshot, error) {
	sc := bufio.NewScanner(strings.NewReader(string(data)))
	sc.Buffer(make([]byte, 0, 64*1024), 10*1024*1024)
	var out []issue.Snapshot
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" {
			continue
		}
		var s issue.Snapshot
		if err := json.Unmarshal([]byte(line), &s); err != nil {
			return nil, err
		}
		out = append(out, s)
	}
	if err := sc.Err(); err != nil {
		return nil, err
	}
	return out, nil
}

func (g *Generator) DailyReport(ctx context.Context, owner, repo string, date time.Time) (map[string]any, error) {
	issues, err := g.LoadLatestSnapshots(ctx, owner, repo)
	if err != nil {
		return nil, err
	}
	day := date.Format("2006-01-02")
	newCount := 0
	closedCount := 0
	var total, openCount, closedTotal, blocked int
	for _, it := range issues {
		total++
		if it.State == "open" {
			openCount++
		}
		if it.State == "closed" {
			closedTotal++
		}
		if it.IsBlocked {
			blocked++
		}
		if it.CreatedAt != nil && it.CreatedAt.Format("2006-01-02") == day {
			newCount++
		}
		if it.ClosedAt != nil && it.ClosedAt.Format("2006-01-02") == day {
			closedCount++
		}
	}
	report := map[string]any{
		"date": day,
		"repo": fmt.Sprintf("%s/%s", owner, repo),
		"summary": map[string]any{
			"total_issues":   total,
			"open_issues":    openCount,
			"closed_issues":  closedTotal,
			"blocked_issues": blocked,
			"new_today":      newCount,
			"closed_today":   closedCount,
		},
		"generated_at": time.Now().Format(time.RFC3339),
	}
	return report, nil
}

func (g *Generator) ProgressReport(ctx context.Context, owner, repo string) (map[string]any, error) {
	issues, err := g.LoadLatestSnapshots(ctx, owner, repo)
	if err != nil {
		return nil, err
	}
	byStatus := map[string]int{}
	byType := map[string]int{}
	byPriority := map[string]int{}
	for _, it := range issues {
		byStatus[it.Status]++
		byType[it.IssueType]++
		byPriority[it.Priority]++
	}
	report := map[string]any{
		"repo":         fmt.Sprintf("%s/%s", owner, repo),
		"generated_at": time.Now().Format(time.RFC3339),
		"by_status":    byStatus,
		"by_type":      byType,
		"by_priority":  byPriority,
	}
	return report, nil
}
