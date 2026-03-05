# -*- coding: utf-8 -*-
"""时间趋势分析器"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List
from .base_analyzer import BaseAnalyzer


class TrendAnalyzer(BaseAnalyzer):
    """时间窗口内的新建/关闭趋势"""

    def analyze(self, issues: List) -> Dict:
        now = datetime.utcnow()
        windows = self.config.get("time_windows", [7, 30, 90])
        out = {}
        for d in windows:
            cutoff = now - timedelta(days=d)
            new_cnt = 0
            closed_cnt = 0
            resolution_times = []
            for i in issues:
                created = i.get("created_at")
                closed = i.get("closed_at")
                if created and created >= cutoff:
                    new_cnt += 1
                if closed and closed >= cutoff:
                    closed_cnt += 1
                if closed and created and closed >= cutoff:
                    try:
                        resolution_times.append((closed - created).days)
                    except Exception:
                        pass
            avg_res = sum(resolution_times) / len(resolution_times) if resolution_times else 0
            out[f"last_{d}d"] = {
                "new_issues": new_cnt,
                "closed_issues": closed_cnt,
                "net_change": new_cnt - closed_cnt,
                "avg_resolution_days": round(avg_res, 1),
            }
        return {"by_window": out}
