# -*- coding: utf-8 -*-
"""基础统计分析器"""

from collections import defaultdict
from typing import Dict, List
from .base_analyzer import BaseAnalyzer


class BasicStatsAnalyzer(BaseAnalyzer):
    """基础统计（状态、类型、优先级等）"""

    def analyze(self, issues: List) -> Dict:
        total = len(issues)
        by_state = defaultdict(int)
        by_type = defaultdict(int)
        by_priority = defaultdict(int)
        by_status = defaultdict(int)

        for i in issues:
            by_state[i.get("state", "unknown")] += 1
            t = i.get("issue_type") or i.get("ai_tags") or "unknown"
            if isinstance(t, list):
                t = t[0] if t else "unknown"
            by_type[str(t)] += 1
            by_priority[i.get("priority") or i.get("ai_priority") or "unknown"] += 1
            by_status[i.get("status", "未知")] += 1

        show_pct = self.config.get("show_percentages", True)
        def add_pct(d, tot):
            return {k: {"count": v, "percentage": round(v / tot * 100, 2)} if tot and show_pct else v
                    for k, v in d.items()}

        return {
            "total_issues": total,
            "by_state": dict(by_state) if not show_pct else add_pct(dict(by_state), total),
            "by_type": dict(by_type) if not show_pct else add_pct(dict(by_type), total),
            "by_priority": dict(by_priority) if not show_pct else add_pct(dict(by_priority), total),
            "by_status": dict(by_status) if not show_pct else add_pct(dict(by_status), total),
        }
