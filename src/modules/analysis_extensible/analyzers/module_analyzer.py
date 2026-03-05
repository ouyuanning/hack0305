# -*- coding: utf-8 -*-
"""功能模块分析器"""

import re
from collections import defaultdict
from typing import Dict, List, Set
from .base_analyzer import BaseAnalyzer


class ModuleAnalyzer(BaseAnalyzer):
    """功能模块深度分析"""

    MODULE_KEYWORDS = {"storage", "sql", "parser", "optimizer", "executor", "planner", "catalog", "txn", "transaction"}

    def analyze(self, issues: List) -> Dict:
        module_stats = defaultdict(
            lambda: {"total": 0, "open": 0, "closed": 0, "bugs": 0, "p0": 0, "p1": 0, "resolution_times": []}
        )

        for i in issues:
            mods = self._extract_modules(i)
            for m in mods:
                s = module_stats[m]
                s["total"] += 1
                s["open" if i.get("state") == "open" else "closed"] += 1
                if (i.get("issue_type") or "").lower() == "bug":
                    s["bugs"] += 1
                p = i.get("priority") or i.get("ai_priority") or ""
                if p == "P0":
                    s["p0"] += 1
                elif p == "P1":
                    s["p1"] += 1
                if i.get("state") == "closed" and i.get("created_at") and i.get("closed_at"):
                    try:
                        delta = i["closed_at"] - i["created_at"]
                        s["resolution_times"].append(delta.days)
                    except Exception:
                        pass

        top_n = self.config.get("top_modules_count", 20)
        top_modules = []
        for mod, s in module_stats.items():
            bug_ratio = s["bugs"] / s["total"] if s["total"] else 0
            avg_res = sum(s["resolution_times"]) / len(s["resolution_times"]) if s["resolution_times"] else 0
            hot = self._hot_level(s)
            top_modules.append({
                "module": mod,
                "total_issues": s["total"],
                "open_issues": s["open"],
                "bug_count": s["bugs"],
                "bug_ratio": round(bug_ratio, 2),
                "p0_count": s["p0"],
                "avg_resolution_days": round(avg_res, 1),
                "hot_level": hot,
            })
        top_modules = sorted(top_modules, key=lambda x: -x["total_issues"])[:top_n]

        return {
            "total_modules": len(module_stats),
            "top_modules": top_modules,
        }

    def _extract_modules(self, issue: Dict) -> Set[str]:
        mods = set()
        for lb in self._parse_labels(issue.get("labels")):
            if lb.startswith("area/"):
                mods.add(lb.replace("area/", ""))
        if self.config.get("extract_from_ai_tags", True):
            tags = self._parse_json_field(issue.get("ai_tags")) or []
            for t in tags:
                if isinstance(t, str) and t.lower() in self.MODULE_KEYWORDS:
                    mods.add(t.lower())
        if self.config.get("extract_from_title", True):
            title = (issue.get("title") or "").lower()
            m = re.search(r"\[([^\]]+)\]", title)
            if m:
                mods.add(m.group(1).lower())
        return mods if mods else {"unknown"}

    def _hot_level(self, s: Dict) -> str:
        score = 0
        if s["total"] > 100:
            score += 3
        elif s["total"] > 50:
            score += 2
        elif s["total"] > 20:
            score += 1
        if s["p0"] > 5:
            score += 2
        elif s["p0"] > 2:
            score += 1
        br = s["bugs"] / s["total"] if s["total"] else 0
        if br > 0.5:
            score += 2
        elif br > 0.3:
            score += 1
        return "high" if score >= 5 else ("medium" if score >= 3 else "low")
