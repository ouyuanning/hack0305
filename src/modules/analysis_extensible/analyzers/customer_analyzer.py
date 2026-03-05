# -*- coding: utf-8 -*-
"""客户维度分析器"""

from collections import defaultdict
from typing import Dict, List
from .base_analyzer import BaseAnalyzer


class CustomerAnalyzer(BaseAnalyzer):
    """按 customer/ 标签分析客户"""

    def analyze(self, issues: List) -> Dict:
        customers = set()
        for i in issues:
            for lb in self._parse_labels(i.get("labels")):
                if str(lb).startswith("customer/"):
                    customers.add(str(lb).replace("customer/", "").strip())
        customers = sorted(customers)

        by_customer = {}
        for c in customers:
            subset = [x for x in issues if any(
                str(lb).startswith(f"customer/{c}") or str(lb) == f"customer/{c}"
                for lb in self._parse_labels(x.get("labels"))
            )]
            total = len(subset)
            closed = sum(1 for x in subset if x.get("state") == "closed")
            by_type = defaultdict(int)
            by_priority = defaultdict(int)
            for x in subset:
                t = x.get("issue_type") or "unknown"
                if isinstance(t, list):
                    t = t[0] if t else "unknown"
                by_type[str(t)] += 1
                by_priority[x.get("priority") or x.get("ai_priority") or "unknown"] += 1

            by_customer[c] = {
                "total_issues": total,
                "closed": closed,
                "completion_rate": round(closed / total, 2) if total else 0,
                "by_type": dict(by_type),
                "by_priority": dict(by_priority),
            }

        return {"customers": customers, "by_customer": by_customer}
