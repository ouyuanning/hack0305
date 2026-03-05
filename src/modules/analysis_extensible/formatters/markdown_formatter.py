# -*- coding: utf-8 -*-
"""Markdown 报告"""

from pathlib import Path
from datetime import datetime
from typing import Dict


class MarkdownFormatter:
    def __init__(self, results: Dict, format_config: Dict, sections: list = None):
        self.results = results
        self.config = format_config or {}
        self.sections = sections or []

    def save(self, output_path: Path):
        path = str(output_path)
        if "{date}" in path:
            path = path.replace("{date}", datetime.now().strftime("%Y%m%d"))
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        md = self._build_md()
        with open(out, "w", encoding="utf-8") as f:
            f.write(md)
        return out

    def _build_md(self) -> str:
        repo = self.results.get("repo", "")
        total = self.results.get("total_issues", 0)
        ar = self.results.get("analysis_results", {})

        lines = [
            f"# GitHub Issue 可扩展分析报告",
            "",
            f"**仓库**: {repo}  ",
            f"**生成时间**: {datetime.now().isoformat()}  ",
            f"**总 Issue 数**: {total}",
            "",
            "---",
            "",
        ]

        # 基础统计
        if "basic_stats" in ar:
            bs = ar["basic_stats"]
            lines.extend(["## 📈 基础统计", ""])
            for k, v in bs.items():
                if k == "total_issues":
                    continue
                if isinstance(v, dict):
                    lines.append(f"### {k}")
                    for k2, v2 in v.items():
                        lines.append(f"- **{k2}**: {v2}")
                else:
                    lines.append(f"- **{k}**: {v}")
            lines.append("")

        # 标签分析
        if "label_analysis" in ar:
            la = ar["label_analysis"]
            lines.extend(["## 🏷️ 标签分析", ""])
            lines.append(f"唯一标签数: {la.get('total_unique_labels', 0)}")
            if "label_categories" in la:
                for cat, items in la["label_categories"].items():
                    if items:
                        lines.append(f"### {cat}")
                        for lb, cnt in list(items.items())[:15]:
                            lines.append(f"- {lb}: {cnt}")
            lines.append("")

        # 模块分析
        if "module_analysis" in ar:
            ma = ar["module_analysis"]
            lines.extend(["## 🔧 功能模块", ""])
            for m in ma.get("top_modules", [])[:15]:
                lines.append(f"- **{m['module']}**: {m['total_issues']} issues, bug比例{m['bug_ratio']}, 热度{m['hot_level']}")
            lines.append("")

        # 客户
        if "customer_analysis" in ar:
            ca = ar["customer_analysis"]
            lines.extend(["## 👥 客户维度", ""])
            for c, d in ca.get("by_customer", {}).items():
                lines.append(f"- **{c}**: {d['total_issues']} issues, 完成率 {d['completion_rate']*100:.1f}%")
            lines.append("")

        # 关联
        if "relation_analysis" in ar:
            ra = ar["relation_analysis"]
            lines.extend(["## 🔗 关联分析", ""])
            lines.append(f"关系总数: {ra.get('total_relations', 0)}")
            for r in ra.get("most_referenced", [])[:5]:
                lines.append(f"- #{r.get('issue_number','?')} 被引用 {r.get('count',0)} 次")
            lines.append("")

        return "\n".join(lines)
