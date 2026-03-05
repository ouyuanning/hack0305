package analysis

import (
	"fmt"
	"sort"
	"strings"
	"time"
)

func ExtensibleMarkdown(results map[string]any) string {
	repo := fmt.Sprintf("%v", results["repo"])
	total := fmt.Sprintf("%v", results["total_issues"])
	ar, _ := results["analysis_results"].(map[string]any)
	lines := []string{
		"# GitHub Issue 可扩展分析报告",
		"",
		fmt.Sprintf("**仓库**: %s  ", repo),
		fmt.Sprintf("**生成时间**: %s  ", time.Now().Format(time.RFC3339Nano)),
		fmt.Sprintf("**总 Issue 数**: %s", total),
		"",
		"---",
		"",
	}

	if bs, ok := ar["basic_stats"].(map[string]any); ok {
		lines = append(lines, "## 📈 基础统计", "")
		for _, k := range []string{"by_state", "by_type", "by_priority", "by_status"} {
			v, ok := bs[k]
			if !ok {
				continue
			}
			if m, ok := v.(map[string]any); ok {
				lines = append(lines, fmt.Sprintf("### %s", k))
				for k2, v2 := range m {
					lines = append(lines, fmt.Sprintf("- **%s**: %s", k2, formatPyValue(v2)))
				}
			}
		}
		lines = append(lines, "")
	}

	if la, ok := ar["label_analysis"].(map[string]any); ok {
		lines = append(lines, "## 🏷️ 标签分析", "")
		lines = append(lines, fmt.Sprintf("唯一标签数: %v", la["total_unique_labels"]))
		if cats, ok := la["label_categories"].(map[string]any); ok {
			order := []string{"Issue类型", "功能模块", "客户", "严重程度"}
			for _, cat := range order {
				items, ok := cats[cat]
				if !ok {
					continue
				}
				if m, ok := items.(map[string]any); ok {
					if len(m) == 0 {
						continue
					}
					lines = append(lines, fmt.Sprintf("### %s", cat))
					count := 0
					for lb, cnt := range m {
						lines = append(lines, fmt.Sprintf("- %s: %v", lb, cnt))
						count++
						if count >= 15 {
							break
						}
					}
				}
			}
		}
		lines = append(lines, "")
	}

	if ma, ok := ar["module_analysis"].(map[string]any); ok {
		lines = append(lines, "## 🔧 功能模块", "")
		if list, ok := ma["top_modules"].([]any); ok {
			for i, item := range list {
				if i >= 15 {
					break
				}
				m, _ := item.(map[string]any)
				lines = append(lines, fmt.Sprintf("- **%v**: %v issues, bug比例%v, 热度%v", m["module"], m["total_issues"], m["bug_ratio"], m["hot_level"]))
			}
		}
		lines = append(lines, "")
	}

	if ca, ok := ar["customer_analysis"].(map[string]any); ok {
		lines = append(lines, "## 👥 客户维度", "")
		if by, ok := ca["by_customer"].(map[string]any); ok {
			keys := make([]string, 0, len(by))
			for k := range by {
				keys = append(keys, k)
			}
			sort.Strings(keys)
			for _, c := range keys {
				d := by[c]
				m, _ := d.(map[string]any)
				lines = append(lines, fmt.Sprintf("- **%v**: %v issues, 完成率 %v%%", c, m["total_issues"], round(float64From(m["completion_rate"])*100, 1)))
			}
		}
		lines = append(lines, "")
	}

	if ra, ok := ar["relation_analysis"].(map[string]any); ok {
		lines = append(lines, "## 🔗 关联分析", "")
		lines = append(lines, fmt.Sprintf("关系总数: %v", ra["total_relations"]))
		if list, ok := ra["most_referenced"].([]any); ok {
			for i, item := range list {
				if i >= 5 {
					break
				}
				m, _ := item.(map[string]any)
				lines = append(lines, fmt.Sprintf("- #%v 被引用 %v 次", m["issue_number"], m["count"]))
			}
		}
		lines = append(lines, "")
	}

	return strings.Join(lines, "\n")
}

func ComprehensiveMarkdown(report map[string]any) string {
	summary, _ := report["summary"].(map[string]any)
	lines := []string{
		"# GitHub Issue 综合分析报告",
		"",
		fmt.Sprintf("**仓库**: %v  ", report["repo"]),
		fmt.Sprintf("**生成时间**: %v", report["generated_at"]),
		"",
		"---",
		"",
		"## 📊 总体概览",
		"",
		fmt.Sprintf("- **总Issue数**: %v", summary["total_issues"]),
		fmt.Sprintf("- **Open**: %v", summary["open_issues"]),
		fmt.Sprintf("- **Closed**: %v", summary["closed_issues"]),
		fmt.Sprintf("- **被阻塞**: %v", summary["blocked_issues"]),
		fmt.Sprintf("- **客户项目数**: %v", summary["customer_count"]),
		"",
		"---",
		"",
		"## 👥 各客户项目情况",
		"",
		"| 客户 | 总Issue | 完成率 | Open | Closed | 被阻塞 |",
		"|------|---------|--------|------|--------|--------|",
	}
	if cr, ok := report["customer_reports"].(map[string]any); ok {
		keys := make([]string, 0, len(cr))
		for k := range cr {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		for _, customer := range keys {
			r := cr[customer]
			m, _ := r.(map[string]any)
			byState, _ := m["by_state"].(map[string]any)
			blocked, _ := m["blocked_issues"].([]any)
			lines = append(lines, fmt.Sprintf("| %v | %v | %.1f%% | %v | %v | %d |", customer, m["total_issues"], float64From(m["completion_rate"])*100, byState["open"], byState["closed"], len(blocked)))
		}
	}

	if shared, ok := report["shared_features"].([]any); ok && len(shared) > 0 {
		lines = append(lines, "", "---", "", fmt.Sprintf("## 🔗 跨项目共用Feature (%d个)", len(shared)), "")
		for i, item := range shared {
			if i >= 10 {
				break
			}
			m, _ := item.(map[string]any)
			lines = append(lines, fmt.Sprintf("- **#%v**: %v", m["feature_number"], m["feature_title"]))
			if cust, ok := m["customers"].([]any); ok {
				lines = append(lines, fmt.Sprintf("  - 涉及客户: %s", joinAny(cust)))
			}
		}
	}

	if chains, ok := report["blocking_chains"].([]any); ok && len(chains) > 0 {
		lines = append(lines, "", "---", "", fmt.Sprintf("## ⛓️ 阻塞链分析 (%d条)", len(chains)), "")
		for i, item := range chains {
			if i >= 10 {
				break
			}
			m, _ := item.(map[string]any)
			lines = append(lines, fmt.Sprintf("- %v (长度: %v)", m["description"], m["length"]))
		}
	}

	lines = append(lines, "", "---", "", "## 📝 说明", "", "详细的客户报告请查看 `customer_reports/` 目录。")
	return strings.Join(lines, "\n")
}

func CustomerMarkdown(customer string, data map[string]any) string {
	lines := []string{
		fmt.Sprintf("# %s 项目分析报告", customer),
		"",
		fmt.Sprintf("**生成时间**: %v", data["analyzed_at"]),
		"",
		"---",
		"",
		"## 📊 项目概览",
		"",
		fmt.Sprintf("- **总Issue数**: %v", data["total_issues"]),
		fmt.Sprintf("- **完成率**: %.1f%%", float64From(data["completion_rate"])*100),
		"",
		"### 状态分布",
		"",
		"| 状态 | 数量 |",
		"|------|------|",
	}
	if byState, ok := data["by_state"].(map[string]any); ok {
		keys := make([]string, 0, len(byState))
		for k := range byState {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		for _, k := range keys {
			lines = append(lines, fmt.Sprintf("| %s | %v |", k, byState[k]))
		}
	}
	lines = append(lines, "", "### 类型分布", "", "| 类型 | 数量 |", "|------|------|")
	if byType, ok := data["by_type"].(map[string]any); ok {
		keys := make([]string, 0, len(byType))
		for k := range byType {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		for _, k := range keys {
			lines = append(lines, fmt.Sprintf("| %s | %v |", k, byType[k]))
		}
	}
	lines = append(lines, "", "### 优先级分布", "", "| 优先级 | 数量 |", "|------|------|")
	if byP, ok := data["by_priority"].(map[string]any); ok {
		keys := make([]string, 0, len(byP))
		for k := range byP {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		for _, k := range keys {
			lines = append(lines, fmt.Sprintf("| %s | %v |", k, byP[k]))
		}
	}
	if hierarchy, ok := data["hierarchy_progress"].(map[string]any); ok {
		lines = append(lines, "", "## 📈 层级进度", "", "| 层级 | 总数 | 已完成 | 完成率 |", "|------|------|--------|--------|")
		for _, level := range []string{"L1", "L2", "L3", "L4"} {
			if h, ok := hierarchy[level].(map[string]any); ok {
				lines = append(lines, fmt.Sprintf("| %s | %v | %v | %.1f%% |", level, h["total"], h["closed"], float64From(h["rate"])*100))
			}
		}
	}

	if risks, ok := data["risks"].(map[string]any); ok {
		lines = append(lines, "", "---", "", "## ⚠️ 风险提示", "")
		if hp, ok := risks["high_priority_open"].([]any); ok {
			lines = append(lines, fmt.Sprintf("### 高优先级未关闭 (%d)", len(hp)))
			for _, r := range hp {
				m, _ := r.(map[string]any)
				lines = append(lines, fmt.Sprintf("- **#%v**: %v (%v, 已开%v天)", m["issue_number"], m["title"], m["priority"], m["days_open"]))
			}
		}
		if bc, ok := risks["blocked_chain"].([]any); ok {
			lines = append(lines, "", "### 被阻塞的Issue", "")
			for _, r := range bc {
				m, _ := r.(map[string]any)
				lines = append(lines, fmt.Sprintf("- **#%v**: %v - %v", m["issue_number"], m["title"], m["reason"]))
			}
		}
		if lo, ok := risks["long_time_open"].([]any); ok {
			lines = append(lines, "", "### 长时间未关闭Issue", "")
			for _, r := range lo {
				m, _ := r.(map[string]any)
				lines = append(lines, fmt.Sprintf("- **#%v**: %v (已开%v天)", m["issue_number"], m["title"], m["days_open"]))
			}
		}
	}
	return strings.Join(lines, "\n")
}

func joinAny(items []any) string {
	parts := []string{}
	for _, v := range items {
		parts = append(parts, fmt.Sprintf("%v", v))
	}
	return strings.Join(parts, ", ")
}

func float64From(v any) float64 {
	switch t := v.(type) {
	case float64:
		return t
	case float32:
		return float64(t)
	case int:
		return float64(t)
	case int64:
		return float64(t)
	}
	return 0
}

func formatPyValue(v any) string {
	switch t := v.(type) {
	case map[string]any:
		keys := make([]string, 0, len(t))
		for k := range t {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		parts := []string{}
		for _, k := range keys {
			parts = append(parts, fmt.Sprintf("'%s': %v", k, t[k]))
		}
		return "{" + strings.Join(parts, ", ") + "}"
	default:
		return fmt.Sprintf("%v", t)
	}
}
