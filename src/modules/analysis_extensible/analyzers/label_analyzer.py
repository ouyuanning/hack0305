# -*- coding: utf-8 -*-
"""标签深度分析器"""

import json
from collections import defaultdict
from typing import Dict, List
from .base_analyzer import BaseAnalyzer


class LabelAnalyzer(BaseAnalyzer):
    """标签深度分析"""

    def analyze(self, issues: List) -> Dict:
        label_counts = defaultdict(lambda: {"count": 0, "open": 0, "closed": 0})
        label_combinations = defaultdict(int)
        total = len(issues)

        for i in issues:
            labels = self._parse_labels(i.get("labels"))
            state = i.get("state", "open")
            for lb in labels:
                label_counts[lb]["count"] += 1
                label_counts[lb]["open" if state == "open" else "closed"] += 1
            if 2 <= len(labels) <= 4:
                combo = tuple(sorted(labels))
                label_combinations[combo] += 1

        for lb, st in label_counts.items():
            st["percentage"] = round(st["count"] / total * 100, 2) if total else 0

        categories = self._group_by_category(dict(label_counts))
        top_n = self.config.get("top_labels_count", 30)
        top_labels = dict(sorted(label_counts.items(), key=lambda x: -x[1]["count"])[:top_n])

        comb_n = self.config.get("top_combinations_count", 15)
        top_comb = sorted(
            [{"labels": list(c), "count": n} for c, n in label_combinations.items()],
            key=lambda x: -x["count"],
        )[:comb_n]

        return {
            "total_unique_labels": len(label_counts),
            "label_distribution": top_labels,
            "label_categories": categories,
            "top_label_combinations": top_comb,
        }

    def _group_by_category(self, label_counts: Dict) -> Dict:
        cats = self.config.get("label_categories", [])
        out = {}
        for c in cats:
            prefix = c.get("prefix", "")
            name = c.get("name", prefix)
            out[name] = {k: v["count"] for k, v in label_counts.items() if k.startswith(prefix)}
            out[name] = dict(sorted(out[name].items(), key=lambda x: -x[1]))
        return out
