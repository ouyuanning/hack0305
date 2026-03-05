package analysis

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/matrixorigin/issue-manager/internal/issue"
	"gopkg.in/yaml.v3"
)

type ExtensibleConfig struct {
	Analyzers []struct {
		Name    string         `yaml:"name"`
		Enabled bool           `yaml:"enabled"`
		Config  map[string]any `yaml:"config"`
	} `yaml:"analyzers"`
	Output struct {
		BaseDir string `yaml:"base_dir"`
		Formats []struct {
			Type     string `yaml:"type"`
			Enabled  bool   `yaml:"enabled"`
			Filename string `yaml:"filename"`
		} `yaml:"formats"`
	} `yaml:"output"`
}

func loadExtensibleConfig() (*ExtensibleConfig, error) {
	path := filepath.Join("src", "config", "analysis_config.yaml")
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var cfg ExtensibleConfig
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}
	return &cfg, nil
}

func (g *Generator) ExtensibleReport(ctx context.Context, owner, repo string) (map[string]any, error) {
	bundle, err := g.LoadLatestBundle(ctx, owner, repo)
	if err != nil {
		return nil, err
	}
	issues := bundle.Snapshots
	cfg, _ := loadExtensibleConfig()

	results := map[string]any{
		"repo":             fmt.Sprintf("%s/%s", owner, repo),
		"generated_at":     time.Now().Format(time.RFC3339Nano),
		"total_issues":     len(issues),
		"analysis_results": map[string]any{},
	}
	ar := results["analysis_results"].(map[string]any)

	if cfg != nil {
		for _, a := range cfg.Analyzers {
			if !a.Enabled {
				continue
			}
			switch a.Name {
			case "basic_stats":
				ar[a.Name] = analyzeBasicStats(issues, a.Config)
			case "label_analysis":
				ar[a.Name] = analyzeLabels(issues, a.Config)
			case "module_analysis":
				ar[a.Name] = analyzeModules(issues, a.Config)
			case "hierarchy_analysis":
				ar[a.Name] = analyzeHierarchy(issues, a.Config)
			case "customer_analysis":
				ar[a.Name] = analyzeCustomers(issues)
			case "relation_analysis":
				ar[a.Name] = analyzeRelations(issues, bundle.Relations, a.Config)
			case "trend_analysis":
				ar[a.Name] = analyzeTrend(issues, a.Config)
			}
		}
	} else {
		ar["basic_stats"] = analyzeBasicStats(issues, map[string]any{"show_percentages": true})
	}

	return results, nil
}

// ---------- analyzers (python-aligned) ----------

func analyzeBasicStats(issues []issue.Snapshot, cfg map[string]any) map[string]any {
	total := len(issues)
	byState := map[string]int{}
	byType := map[string]int{}
	byPriority := map[string]int{}
	byStatus := map[string]int{}
	for _, i := range issues {
		state := i.State
		if state == "" {
			state = "unknown"
		}
		byState[state]++
		t := i.IssueType
		if t == "" && len(i.AITags) > 0 {
			t = i.AITags[0]
		}
		if t == "" {
			t = "unknown"
		}
		byType[t]++
		p := i.Priority
		if p == "" {
			p = i.AIPriority
		}
		if p == "" {
			p = "unknown"
		}
		byPriority[p]++
		status := i.Status
		if status == "" {
			status = "未知"
		}
		byStatus[status]++
	}
	showPct := true
	if v, ok := cfg["show_percentages"].(bool); ok {
		showPct = v
	}
	addPct := func(d map[string]int) map[string]any {
		out := map[string]any{}
		for k, v := range d {
			if total == 0 || !showPct {
				out[k] = v
				continue
			}
			out[k] = map[string]any{
				"count":      v,
				"percentage": round(float64(v)/float64(total)*100, 2),
			}
		}
		return out
	}
	return map[string]any{
		"total_issues": total,
		"by_state":     addPct(byState),
		"by_type":      addPct(byType),
		"by_priority":  addPct(byPriority),
		"by_status":    addPct(byStatus),
	}
}

func analyzeLabels(issues []issue.Snapshot, cfg map[string]any) map[string]any {
	total := len(issues)
	labelCounts := map[string]map[string]int{}
	labelCombos := map[string]int{}
	for _, i := range issues {
		labels := parseLabels(i.Labels)
		state := i.State
		if state == "" {
			state = "open"
		}
		for _, lb := range labels {
			if _, ok := labelCounts[lb]; !ok {
				labelCounts[lb] = map[string]int{"count": 0, "open": 0, "closed": 0}
			}
			labelCounts[lb]["count"]++
			if state == "open" {
				labelCounts[lb]["open"]++
			} else {
				labelCounts[lb]["closed"]++
			}
		}
		if len(labels) >= 2 && len(labels) <= 4 {
			sorted := append([]string{}, labels...)
			sort.Strings(sorted)
			key := strings.Join(sorted, "|")
			labelCombos[key]++
		}
	}
	// percentage is computed when building output
	// top labels
	topN := intVal(cfg, "top_labels_count", 30)
	labelsSorted := sortLabelCounts(labelCounts)
	if len(labelsSorted) > topN {
		labelsSorted = labelsSorted[:topN]
	}
	topLabels := map[string]any{}
	for _, kv := range labelsSorted {
		st := labelCounts[kv]
		stOut := map[string]any{"count": st["count"], "open": st["open"], "closed": st["closed"]}
		pct := 0.0
		if total > 0 {
			pct = round(float64(st["count"])/float64(total)*100, 2)
		}
		stOut["percentage"] = pct
		topLabels[kv] = stOut
	}
	// categories
	cats := map[string]map[string]int{}
	if arr, ok := cfg["label_categories"].([]any); ok {
		for _, c := range arr {
			m, _ := c.(map[string]any)
			prefix := strVal(m, "prefix")
			name := strVal(m, "name")
			if name == "" {
				name = prefix
			}
			items := map[string]int{}
			for lb, st := range labelCounts {
				if strings.HasPrefix(lb, prefix) {
					items[lb] = st["count"]
				}
			}
			// sort by count
			keys := make([]string, 0, len(items))
			for k := range items {
				keys = append(keys, k)
			}
			sort.Slice(keys, func(i, j int) bool { return items[keys[i]] > items[keys[j]] })
			sorted := map[string]int{}
			for _, k := range keys {
				sorted[k] = items[k]
			}
			cats[name] = sorted
		}
	}
	// combinations
	combN := intVal(cfg, "top_combinations_count", 15)
	combList := []map[string]any{}
	for k, v := range labelCombos {
		labels := strings.Split(k, "|")
		combList = append(combList, map[string]any{"labels": labels, "count": v})
	}
	sort.Slice(combList, func(i, j int) bool { return combList[i]["count"].(int) > combList[j]["count"].(int) })
	if len(combList) > combN {
		combList = combList[:combN]
	}

	return map[string]any{
		"total_unique_labels":    len(labelCounts),
		"label_distribution":     topLabels,
		"label_categories":       cats,
		"top_label_combinations": combList,
	}
}

func analyzeModules(issues []issue.Snapshot, cfg map[string]any) map[string]any {
	moduleStats := map[string]*moduleStat{}
	for _, i := range issues {
		mods := extractModules(i, cfg)
		for _, m := range mods {
			st := moduleStats[m]
			if st == nil {
				st = &moduleStat{}
				moduleStats[m] = st
			}
			st.total++
			if i.State == "open" {
				st.open++
			} else {
				st.closed++
			}
			if strings.EqualFold(i.IssueType, "bug") {
				st.bugs++
			}
			p := i.Priority
			if p == "" {
				p = i.AIPriority
			}
			if p == "P0" {
				st.p0++
			}
			if p == "P1" {
				st.p1++
			}
			if i.State == "closed" && i.CreatedAt != nil && i.ClosedAt != nil {
				st.resolution = append(st.resolution, int(i.ClosedAt.Sub(*i.CreatedAt).Hours()/24))
			}
		}
	}
	modules := []map[string]any{}
	for mod, s := range moduleStats {
		bugRatio := 0.0
		if s.total > 0 {
			bugRatio = float64(s.bugs) / float64(s.total)
		}
		avgRes := 0.0
		if len(s.resolution) > 0 {
			sum := 0
			for _, d := range s.resolution {
				sum += d
			}
			avgRes = float64(sum) / float64(len(s.resolution))
		}
		modules = append(modules, map[string]any{
			"module":              mod,
			"total_issues":        s.total,
			"open_issues":         s.open,
			"bug_count":           s.bugs,
			"bug_ratio":           round(bugRatio, 2),
			"p0_count":            s.p0,
			"avg_resolution_days": round(avgRes, 1),
			"hot_level":           moduleHotLevel(s),
		})
	}
	sort.Slice(modules, func(i, j int) bool { return modules[i]["total_issues"].(int) > modules[j]["total_issues"].(int) })
	topN := intVal(cfg, "top_modules_count", 20)
	if len(modules) > topN {
		modules = modules[:topN]
	}
	return map[string]any{
		"total_modules": len(moduleStats),
		"top_modules":   modules,
	}
}

func analyzeHierarchy(issues []issue.Snapshot, _ map[string]any) map[string]any {
	byLevel := map[string]map[string]float64{
		"L1": {"total": 0, "closed": 0},
		"L2": {"total": 0, "closed": 0},
		"L3": {"total": 0, "closed": 0},
		"L4": {"total": 0, "closed": 0},
	}
	orphan := 0
	for _, i := range issues {
		lvl := identifyLevel(i)
		byLevel[lvl]["total"]++
		if i.State == "closed" {
			byLevel[lvl]["closed"]++
		}
		if lvl == "L3" && !hasHierarchyIndicator(i) {
			orphan++
		}
	}
	for lv, d := range byLevel {
		if d["total"] > 0 {
			d["rate"] = round(d["closed"]/d["total"], 2)
		} else {
			d["rate"] = 0
		}
		byLevel[lv] = d
	}
	return map[string]any{
		"level_distribution":   byLevel,
		"orphan_issues_approx": orphan,
	}
}

func analyzeCustomers(issues []issue.Snapshot) map[string]any {
	customers := map[string]bool{}
	for _, i := range issues {
		for _, lb := range parseLabels(i.Labels) {
			if strings.HasPrefix(lb, "customer/") {
				customers[strings.TrimPrefix(lb, "customer/")] = true
			}
		}
	}
	list := []string{}
	for c := range customers {
		list = append(list, c)
	}
	sort.Strings(list)
	byCustomer := map[string]any{}
	for _, c := range list {
		subset := []issue.Snapshot{}
		for _, x := range issues {
			for _, lb := range parseLabels(x.Labels) {
				if lb == "customer/"+c || strings.HasPrefix(lb, "customer/"+c) {
					subset = append(subset, x)
					break
				}
			}
		}
		total := len(subset)
		closed := 0
		byType := map[string]int{}
		byPriority := map[string]int{}
		for _, x := range subset {
			if x.State == "closed" {
				closed++
			}
			t := x.IssueType
			if t == "" {
				t = "unknown"
			}
			byType[t]++
			p := x.Priority
			if p == "" {
				p = x.AIPriority
			}
			if p == "" {
				p = "unknown"
			}
			byPriority[p]++
		}
		byCustomer[c] = map[string]any{
			"total_issues":    total,
			"closed":          closed,
			"completion_rate": round(float64(closed)/float64(max(1, total)), 2),
			"by_type":         byType,
			"by_priority":     byPriority,
		}
	}
	return map[string]any{"customers": list, "by_customer": byCustomer}
}

func analyzeRelations(issues []issue.Snapshot, relations []issue.Relation, cfg map[string]any) map[string]any {
	issueByID := map[int64]issue.Snapshot{}
	for _, i := range issues {
		issueByID[i.IssueID] = i
	}
	referenced := map[int64]int{}
	for _, r := range relations {
		if r.ToIssueID != 0 {
			referenced[r.ToIssueID]++
		}
	}
	topN := intVal(cfg, "top_referenced_count", 15)
	most := []map[string]any{}
	for id, cnt := range referenced {
		if cnt == 0 {
			continue
		}
		it := issueByID[id]
		most = append(most, map[string]any{
			"issue_id":     id,
			"count":        cnt,
			"issue_number": it.IssueNumber,
			"title":        trimTitle(it.Title),
		})
	}
	sort.Slice(most, func(i, j int) bool { return most[i]["count"].(int) > most[j]["count"].(int) })
	if len(most) > topN {
		most = most[:topN]
	}

	blocks := []issue.Relation{}
	for _, r := range relations {
		if r.RelationType == "blocks" {
			blocks = append(blocks, r)
		}
	}
	graph := map[int64][]int64{}
	for _, r := range blocks {
		graph[r.ToIssueID] = append(graph[r.ToIssueID], r.FromIssueID)
	}
	chains := []map[string]any{}
	for start := range graph {
		chain := []int64{start}
		cur := start
		for i := 0; i < 9; i++ {
			nexts := graph[cur]
			if len(nexts) == 0 {
				break
			}
			nxt := nexts[0]
			if containsID(chain, nxt) {
				break
			}
			chain = append(chain, nxt)
			cur = nxt
		}
		if len(chain) > 1 {
			numbers := []any{}
			for _, id := range chain {
				numbers = append(numbers, issueByID[id].IssueNumber)
			}
			chains = append(chains, map[string]any{
				"chain":         chain,
				"length":        len(chain),
				"issue_numbers": numbers,
			})
		}
	}
	sort.Slice(chains, func(i, j int) bool { return chains[i]["length"].(int) > chains[j]["length"].(int) })
	if len(chains) > 10 {
		chains = chains[:10]
	}

	return map[string]any{
		"most_referenced": most,
		"blocking_chains": chains,
		"total_relations": len(relations),
	}
}

func analyzeTrend(issues []issue.Snapshot, cfg map[string]any) map[string]any {
	windows := []int{7, 30, 90}
	if arr, ok := cfg["time_windows"].([]any); ok {
		windows = []int{}
		for _, v := range arr {
			if n, ok := v.(int); ok {
				windows = append(windows, n)
			}
			if n, ok := v.(int64); ok {
				windows = append(windows, int(n))
			}
		}
	}
	now := time.Now().UTC()
	out := map[string]any{}
	for _, d := range windows {
		cutoff := now.Add(-time.Duration(d) * 24 * time.Hour)
		newCnt := 0
		closedCnt := 0
		var res []int
		for _, i := range issues {
			if i.CreatedAt != nil && i.CreatedAt.After(cutoff) {
				newCnt++
			}
			if i.ClosedAt != nil && i.ClosedAt.After(cutoff) {
				closedCnt++
			}
			if i.ClosedAt != nil && i.CreatedAt != nil && i.ClosedAt.After(cutoff) {
				res = append(res, int(i.ClosedAt.Sub(*i.CreatedAt).Hours()/24))
			}
		}
		avg := 0.0
		if len(res) > 0 {
			sum := 0
			for _, v := range res {
				sum += v
			}
			avg = float64(sum) / float64(len(res))
		}
		out[fmt.Sprintf("last_%dd", d)] = map[string]any{
			"new_issues":          newCnt,
			"closed_issues":       closedCnt,
			"net_change":          newCnt - closedCnt,
			"avg_resolution_days": round(avg, 1),
		}
	}
	return map[string]any{"by_window": out}
}

// ---------- helpers ----------

type moduleStat struct {
	total      int
	open       int
	closed     int
	bugs       int
	p0         int
	p1         int
	resolution []int
}

var moduleKeywords = map[string]bool{
	"storage": true, "sql": true, "parser": true, "optimizer": true,
	"executor": true, "planner": true, "catalog": true, "txn": true, "transaction": true,
}

func extractModules(i issue.Snapshot, cfg map[string]any) []string {
	mods := map[string]bool{}
	for _, lb := range parseLabels(i.Labels) {
		if strings.HasPrefix(lb, "area/") {
			mods[strings.TrimPrefix(lb, "area/")] = true
		}
	}
	if boolVal(cfg, "extract_from_ai_tags", true) {
		for _, t := range i.AITags {
			lt := strings.ToLower(t)
			if moduleKeywords[lt] {
				mods[lt] = true
			}
		}
	}
	if boolVal(cfg, "extract_from_title", true) {
		if strings.HasPrefix(i.Title, "[") {
			if idx := strings.Index(i.Title, "]"); idx > 1 {
				mods[strings.ToLower(strings.TrimSpace(i.Title[1:idx]))] = true
			}
		}
	}
	if len(mods) == 0 {
		mods["unknown"] = true
	}
	out := []string{}
	for m := range mods {
		out = append(out, m)
	}
	return out
}

func moduleHotLevel(s *moduleStat) string {
	score := 0
	if s.total > 100 {
		score += 3
	} else if s.total > 50 {
		score += 2
	} else if s.total > 20 {
		score += 1
	}
	if s.p0 > 5 {
		score += 2
	} else if s.p0 > 2 {
		score += 1
	}
	br := 0.0
	if s.total > 0 {
		br = float64(s.bugs) / float64(s.total)
	}
	if br > 0.5 {
		score += 2
	} else if br > 0.3 {
		score += 1
	}
	if score >= 5 {
		return "high"
	}
	if score >= 3 {
		return "medium"
	}
	return "low"
}

func identifyLevel(i issue.Snapshot) string {
	title := strings.ToLower(i.Title)
	labels := []string{}
	for _, lb := range parseLabels(i.Labels) {
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
		case strings.Contains(lb, "level/l4") || strings.Contains(lb, "task") || strings.Contains(lb, "subtask") || strings.Contains(lb, "bug"):
			return "L4"
		}
	}
	l1 := []string{"客户项目", "customer project", "项目需求"}
	l2 := []string{"测试", "test", "qa"}
	l4 := []string{"bug", "task", "任务", "缺陷", "subtask"}
	if containsAny(title, l1) {
		return "L1"
	}
	if containsAny(title, l2) {
		return "L2"
	}
	if containsAny(title, l4) {
		return "L4"
	}
	return "L3"
}

func hasHierarchyIndicator(i issue.Snapshot) bool {
	for _, lb := range parseLabels(i.Labels) {
		lb = strings.ToLower(lb)
		if strings.Contains(lb, "level/") || strings.Contains(lb, "project") || strings.Contains(lb, "test") {
			return true
		}
	}
	return false
}

func intVal(cfg map[string]any, key string, def int) int {
	if v, ok := cfg[key]; ok {
		switch t := v.(type) {
		case int:
			return t
		case int64:
			return int(t)
		case float64:
			return int(t)
		}
	}
	return def
}

func strVal(cfg map[string]any, key string) string {
	if v, ok := cfg[key].(string); ok {
		return v
	}
	return ""
}

func boolVal(cfg map[string]any, key string, def bool) bool {
	if v, ok := cfg[key]; ok {
		if b, ok := v.(bool); ok {
			return b
		}
	}
	return def
}

func sortLabelCounts(m map[string]map[string]int) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Slice(keys, func(i, j int) bool { return m[keys[i]]["count"] > m[keys[j]]["count"] })
	return keys
}

func trimTitle(t string) string {
	if len(t) > 80 {
		return t[:80]
	}
	return t
}

func containsID(list []int64, v int64) bool {
	for _, x := range list {
		if x == v {
			return true
		}
	}
	return false
}
