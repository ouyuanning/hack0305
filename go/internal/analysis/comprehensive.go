package analysis

import (
	"context"
	"fmt"
	"sort"
	"strings"
	"time"

	"github.com/matrixorigin/issue-manager/internal/issue"
)

func (g *Generator) ComprehensiveReport(ctx context.Context, owner, repo string) (map[string]any, map[string]any, map[string]any, map[string]map[string]any, error) {
	bundle, err := g.LoadLatestBundle(ctx, owner, repo)
	if err != nil {
		return nil, nil, nil, nil, err
	}
	issues := bundle.Snapshots

	customers := getAllCustomers(issues)
	customerReports := map[string]map[string]any{}
	for _, c := range customers {
		customerReports[c] = analyzeCustomerProject(issues, c)
	}
	sharedFeatures := findSharedFeatures(bundle.Relations, issues)
	blockingChains := analyzeBlockingChains(bundle.Relations, issues)

	summary := map[string]any{
		"total_issues":   len(issues),
		"open_issues":    countState(issues, "open"),
		"closed_issues":  countState(issues, "closed"),
		"blocked_issues": countBlocked(issues),
		"customer_count": len(customers),
	}

	comprehensive := map[string]any{
		"repo":             fmt.Sprintf("%s/%s", owner, repo),
		"generated_at":     time.Now().Format(time.RFC3339Nano),
		"summary":          summary,
		"customers":        customers,
		"customer_reports": customerReports,
		"shared_features":  sharedFeatures,
		"blocking_chains":  blockingChains,
	}

	sharedReport := buildSharedFeaturesReport(sharedFeatures)
	riskReport := buildRiskReport(customerReports, sharedFeatures)

	return comprehensive, sharedReport, riskReport, customerReports, nil
}

func getAllCustomers(issues []issue.Snapshot) []string {
	set := map[string]bool{}
	for _, it := range issues {
		for _, lb := range parseLabels(it.Labels) {
			if strings.HasPrefix(lb, "customer/") {
				set[strings.TrimPrefix(lb, "customer/")] = true
			}
		}
	}
	list := []string{}
	for c := range set {
		list = append(list, c)
	}
	sort.Strings(list)
	return list
}

func analyzeCustomerProject(issues []issue.Snapshot, customer string) map[string]any {
	subset := []issue.Snapshot{}
	for _, it := range issues {
		if hasLabel(parseLabels(it.Labels), "customer/"+customer) {
			subset = append(subset, it)
		}
	}
	if len(subset) == 0 {
		return map[string]any{"customer": customer, "error": "没有找到该客户的Issue"}
	}
	byState := map[string]int{}
	byType := map[string]int{}
	byPriority := map[string]int{}
	byStatus := map[string]int{}
	blocked := []map[string]any{}
	for _, it := range subset {
		state := it.State
		if state == "" {
			state = "unknown"
		}
		byState[state]++
		issueType := it.IssueType
		if issueType == "" && len(it.AITags) > 0 {
			issueType = it.AITags[0]
		}
		if issueType == "" {
			issueType = "unknown"
		}
		byType[issueType]++
		priority := it.Priority
		if priority == "" {
			priority = it.AIPriority
		}
		if priority == "" {
			priority = "P3"
		}
		byPriority[priority]++
		status := it.Status
		if status == "" {
			status = "未知"
		}
		byStatus[status]++
		if it.IsBlocked {
			blocked = append(blocked, map[string]any{
				"issue_number": it.IssueNumber,
				"title":        it.Title,
				"reason":       fallbackString(it.BlockedReason, "未知原因"),
			})
		}
	}
	closedCount := byState["closed"]
	completion := 0.0
	if len(subset) > 0 {
		completion = float64(closedCount) / float64(len(subset))
	}
	risks := identifyCustomerRisks(subset)
	return map[string]any{
		"customer":        customer,
		"total_issues":    len(subset),
		"by_state":        byState,
		"by_type":         byType,
		"by_priority":     byPriority,
		"by_status":       byStatus,
		"completion_rate": round(completion, 2),
		"blocked_issues":  blocked,
		"risks":           risks,
		"analyzed_at":     time.Now().Format(time.RFC3339Nano),
	}
}

func analyzeHierarchyProgress(issues []issue.Snapshot, customer string) map[string]any {
	subset := []issue.Snapshot{}
	for _, it := range issues {
		if hasLabel(parseLabels(it.Labels), "customer/"+customer) {
			subset = append(subset, it)
		}
	}
	byLevel := map[string]map[string]any{
		"L1": {"total": 0, "closed": 0},
		"L2": {"total": 0, "closed": 0},
		"L3": {"total": 0, "closed": 0},
		"L4": {"total": 0, "closed": 0},
	}
	for _, it := range subset {
		level := identifyIssueLevelMD(it)
		byLevel[level]["total"] = byLevel[level]["total"].(int) + 1
		if it.State == "closed" {
			byLevel[level]["closed"] = byLevel[level]["closed"].(int) + 1
		}
	}
	result := map[string]any{"customer": customer}
	for level, data := range byLevel {
		total := data["total"].(int)
		closed := data["closed"].(int)
		rate := 0.0
		if total > 0 {
			rate = round(float64(closed)/float64(total), 2)
		}
		result[level] = map[string]any{
			"total":  total,
			"closed": closed,
			"rate":   rate,
		}
	}
	return result
}

func HierarchyProgress(issues []issue.Snapshot, customer string) map[string]any {
	return analyzeHierarchyProgress(issues, customer)
}

func identifyCustomerRisks(issues []issue.Snapshot) map[string]any {
	risks := map[string]any{
		"high_priority_open": []map[string]any{},
		"long_time_open":     []map[string]any{},
		"blocked_chain":      []map[string]any{},
		"low_progress":       []map[string]any{},
	}
	now := time.Now()
	for _, it := range issues {
		priority := it.Priority
		if priority == "" {
			priority = it.AIPriority
		}
		if it.State == "open" && (priority == "P0" || priority == "P1") {
			daysOpen := 0
			if it.CreatedAt != nil {
				daysOpen = int(now.Sub(*it.CreatedAt).Hours() / 24)
			}
			risks["high_priority_open"] = append(risks["high_priority_open"].([]map[string]any), map[string]any{
				"issue_number": it.IssueNumber,
				"title":        it.Title,
				"priority":     priority,
				"days_open":    daysOpen,
			})
		}
		if it.State == "open" && it.CreatedAt != nil {
			days := int(now.Sub(*it.CreatedAt).Hours() / 24)
			if days > 30 {
				risks["long_time_open"] = append(risks["long_time_open"].([]map[string]any), map[string]any{
					"issue_number": it.IssueNumber,
					"title":        it.Title,
					"days_open":    days,
				})
			}
		}
		if it.IsBlocked {
			risks["blocked_chain"] = append(risks["blocked_chain"].([]map[string]any), map[string]any{
				"issue_number": it.IssueNumber,
				"title":        it.Title,
				"reason":       fallbackString(it.BlockedReason, "未知"),
			})
		}
		if it.Status == "处理中" {
			if it.ProgressPercentage < 30 {
				risks["low_progress"] = append(risks["low_progress"].([]map[string]any), map[string]any{
					"issue_number": it.IssueNumber,
					"title":        it.Title,
					"progress":     it.ProgressPercentage,
				})
			}
		}
	}
	return risks
}

func identifyIssueLevelMD(issue issue.Snapshot) string {
	title := strings.ToLower(issue.Title)
	labels := []string{}
	for _, lb := range parseLabels(issue.Labels) {
		labels = append(labels, strings.ToLower(lb))
	}
	for _, lb := range labels {
		switch {
		case strings.Contains(lb, "level/l1") || strings.Contains(lb, "project"):
			return "L1"
		case strings.Contains(lb, "level/l2") || strings.Contains(lb, "test"):
			return "L2"
		case strings.Contains(lb, "level/l3") || strings.Contains(lb, "feature"):
			return "L3"
		case strings.Contains(lb, "level/l4") || strings.Contains(lb, "task") || strings.Contains(lb, "subtask"):
			return "L4"
		}
	}
	l1 := []string{"客户项目", "customer project", "项目需求", "总项目"}
	l2 := []string{"测试需求", "test request", "qa", "测试任务"}
	l3 := []string{"feature", "功能", "需求", "epic"}
	l4 := []string{"bug", "task", "任务", "缺陷", "subtask", "子任务"}
	if containsAny(title, l1) {
		return "L1"
	}
	if containsAny(title, l2) {
		return "L2"
	}
	if containsAny(title, l3) {
		return "L3"
	}
	if containsAny(title, l4) {
		return "L4"
	}
	return "L3"
}

func analyzeBlockingChains(relations []issue.Relation, issues []issue.Snapshot) []map[string]any {
	blocks := []issue.Relation{}
	for _, r := range relations {
		if r.RelationType == "blocks" {
			blocks = append(blocks, r)
		}
	}
	graph := map[int64][]int64{}
	for _, rel := range blocks {
		graph[rel.ToIssueID] = append(graph[rel.ToIssueID], rel.FromIssueID)
	}
	issueByID := map[int64]issue.Snapshot{}
	for _, it := range issues {
		issueByID[it.IssueID] = it
	}

	chains := []map[string]any{}
	visited := map[int64]bool{}
	for start := range graph {
		if visited[start] {
			continue
		}
		chain := []int64{start}
		current := start
		for len(chain) < 10 {
			blockers := graph[current]
			if len(blockers) == 0 {
				break
			}
			blocker := blockers[0]
			if containsID(chain, blocker) {
				break
			}
			chain = append(chain, blocker)
			visited[blocker] = true
			current = blocker
		}
		if len(chain) > 1 {
			numbers := []int{}
			for _, id := range chain {
				numbers = append(numbers, issueByID[id].IssueNumber)
			}
			chains = append(chains, map[string]any{
				"chain":       numbers,
				"length":      len(numbers),
				"description": buildChainDesc(numbers),
			})
		}
	}
	return chains
}

func buildChainDesc(nums []int) string {
	parts := []string{}
	for _, n := range nums {
		parts = append(parts, fmt.Sprintf("#%d", n))
	}
	return strings.Join(parts, " ← ")
}

func findSharedFeatures(relations []issue.Relation, issues []issue.Snapshot) []map[string]any {
	issueByID := map[int64]issue.Snapshot{}
	for _, it := range issues {
		issueByID[it.IssueID] = it
	}
	featureCustomers := map[int64]map[string]bool{}
	for _, rel := range relations {
		if rel.RelationType != "depends_on" && rel.RelationType != "reference" && rel.RelationType != "related" && rel.RelationType != "mention" {
			continue
		}
		from := issueByID[rel.FromIssueID]
		customer := extractCustomer(from.Labels)
		if customer == "" {
			continue
		}
		if featureCustomers[rel.ToIssueID] == nil {
			featureCustomers[rel.ToIssueID] = map[string]bool{}
		}
		featureCustomers[rel.ToIssueID][customer] = true
	}
	shared := []map[string]any{}
	for featureID, customers := range featureCustomers {
		if len(customers) <= 1 {
			continue
		}
		feature := issueByID[featureID]
		custList := []string{}
		for c := range customers {
			custList = append(custList, c)
		}
		sort.Strings(custList)
		shared = append(shared, map[string]any{
			"feature_number": feature.IssueNumber,
			"feature_title":  feature.Title,
			"customers":      custList,
			"customer_count": len(custList),
			"risk_level": func() string {
				if len(custList) >= 3 {
					return "high"
				}
				return "medium"
			}(),
		})
	}
	sort.Slice(shared, func(i, j int) bool { return shared[i]["customer_count"].(int) > shared[j]["customer_count"].(int) })
	return shared
}

func buildSharedFeaturesReport(shared []map[string]any) map[string]any {
	high := 0
	medium := 0
	for _, f := range shared {
		if f["risk_level"] == "high" {
			high++
		} else if f["risk_level"] == "medium" {
			medium++
		}
	}
	return map[string]any{
		"title":        "跨项目共用Feature分析",
		"generated_at": time.Now().Format(time.RFC3339Nano),
		"summary": map[string]any{
			"total_shared_features": len(shared),
			"high_risk":             high,
			"medium_risk":           medium,
		},
		"features": shared,
	}
}

func buildRiskReport(customerReports map[string]map[string]any, shared []map[string]any) map[string]any {
	allRisks := map[string]any{
		"high_priority_open": []map[string]any{},
		"long_time_open":     []map[string]any{},
		"blocked_chain":      []map[string]any{},
		"shared_features":    shared,
	}
	for customer, report := range customerReports {
		risks, _ := report["risks"].(map[string]any)
		for _, key := range []string{"high_priority_open", "long_time_open", "blocked_chain"} {
			if list, ok := risks[key].([]map[string]any); ok {
				for _, r := range list {
					r["customer"] = customer
					allRisks[key] = append(allRisks[key].([]map[string]any), r)
				}
			}
		}
	}
	// sort by days_open
	if list, ok := allRisks["high_priority_open"].([]map[string]any); ok {
		sort.Slice(list, func(i, j int) bool { return intValAny(list[i]["days_open"]) > intValAny(list[j]["days_open"]) })
		allRisks["high_priority_open"] = list
	}
	if list, ok := allRisks["long_time_open"].([]map[string]any); ok {
		sort.Slice(list, func(i, j int) bool { return intValAny(list[i]["days_open"]) > intValAny(list[j]["days_open"]) })
		allRisks["long_time_open"] = list
	}
	return map[string]any{
		"title":        "风险汇总分析",
		"generated_at": time.Now().Format(time.RFC3339Nano),
		"summary": map[string]any{
			"total_high_priority_open": len(allRisks["high_priority_open"].([]map[string]any)),
			"total_long_time_open":     len(allRisks["long_time_open"].([]map[string]any)),
			"total_blocked":            len(allRisks["blocked_chain"].([]map[string]any)),
			"total_shared_features":    len(shared),
		},
		"risks": allRisks,
	}
}

func extractCustomer(labels []string) string {
	for _, lb := range parseLabels(labels) {
		if strings.HasPrefix(lb, "customer/") {
			return strings.TrimPrefix(lb, "customer/")
		}
	}
	return ""
}

func fallbackString(v, def string) string {
	if strings.TrimSpace(v) == "" {
		return def
	}
	return v
}

func intValAny(v any) int {
	switch t := v.(type) {
	case int:
		return t
	case int64:
		return int(t)
	case float64:
		return int(t)
	}
	return 0
}
