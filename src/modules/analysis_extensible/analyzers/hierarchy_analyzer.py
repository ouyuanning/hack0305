# -*- coding: utf-8 -*-
"""层级结构分析器"""

from collections import defaultdict
from typing import Dict, List
from .base_analyzer import BaseAnalyzer


class HierarchyAnalyzer(BaseAnalyzer):
    """L1/L2/L3/L4 层级分析"""

    def analyze(self, issues: List) -> Dict:
        by_level = {"L1": {"total": 0, "closed": 0}, "L2": {"total": 0, "closed": 0},
                    "L3": {"total": 0, "closed": 0}, "L4": {"total": 0, "closed": 0}}
        orphan = 0

        for i in issues:
            level = self._identify_level(i)
            by_level[level]["total"] += 1
            if i.get("state") == "closed":
                by_level[level]["closed"] += 1
            if level == "L3" and not self._has_hierarchy_indicator(i):
                orphan += 1

        for lv, d in by_level.items():
            d["rate"] = round(d["closed"] / d["total"], 2) if d["total"] else 0

        return {"level_distribution": by_level, "orphan_issues_approx": orphan}

    def _identify_level(self, i: Dict) -> str:
        title = (i.get("title") or "").lower()
        labels = [str(x).lower() for x in self._parse_labels(i.get("labels"))]
        for lb in labels:
            if "level/l1" in lb or "project" in lb:
                return "L1"
            if "level/l2" in lb or "test" in lb:
                return "L2"
            if "level/l3" in lb or "feature" in lb:
                return "L3"
            if "level/l4" in lb or "task" in lb or "subtask" in lb or "bug" in lb:
                return "L4"
        l1_kw = ["客户项目", "customer project", "项目需求"]
        l2_kw = ["测试", "test", "qa"]
        l3_kw = ["feature", "功能", "需求"]
        l4_kw = ["bug", "task", "任务", "缺陷", "subtask"]
        if any(k in title for k in l1_kw):
            return "L1"
        if any(k in title for k in l2_kw):
            return "L2"
        if any(k in title for k in l4_kw):
            return "L4"
        return "L3"

    def _has_hierarchy_indicator(self, i: Dict) -> bool:
        labels = [str(x).lower() for x in self._parse_labels(i.get("labels"))]
        return any("level/" in lb or "project" in lb or "test" in lb for lb in labels)
