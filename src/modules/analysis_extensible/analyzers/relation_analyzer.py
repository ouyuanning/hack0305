# -*- coding: utf-8 -*-
"""关联关系分析器 - 需从数据库读取 issue_relations"""

from collections import defaultdict
from typing import Dict, List, Optional
from .base_analyzer import BaseAnalyzer


class RelationAnalyzer(BaseAnalyzer):
    """关联关系分析（依赖、阻塞链、被引用最多）"""

    def __init__(self, storage, config: Dict):
        super().__init__(storage, config)
        self._repo_owner = None
        self._repo_name = None
        self._latest_time = None

    def analyze(self, issues: List) -> Dict:
        self._repo_owner = self.config.get("_repo_owner", "matrixorigin")
        self._repo_name = self.config.get("_repo_name", "matrixone")
        issue_by_id = {i.get("issue_id"): i for i in issues if i.get("issue_id")}

        relations = self._get_relations()
        referenced_count = defaultdict(int)
        for r in relations:
            referenced_count[r.get("to_issue_id")] += 1

        top_n = self.config.get("top_referenced_count", 15)
        most_ref = sorted(
            [{"issue_id": k, "count": v, "issue_number": issue_by_id.get(k, {}).get("issue_number"),
              "title": (issue_by_id.get(k) or {}).get("title", "")[:80]}
             for k, v in referenced_count.items() if v > 0],
            key=lambda x: -x["count"],
        )[:top_n]

        blocks = [r for r in relations if r.get("relation_type") == "blocks"]
        graph = defaultdict(list)
        for r in blocks:
            graph[r["to_issue_id"]].append(r["from_issue_id"])
        chains = []
        for start in graph:
            chain = [start]
            cur = start
            for _ in range(9):
                if cur not in graph:
                    break
                nxt = graph[cur][0]
                if nxt in chain:
                    break
                chain.append(nxt)
                cur = nxt
            if len(chain) > 1:
                chains.append({
                    "chain": chain,
                    "length": len(chain),
                    "issue_numbers": [issue_by_id.get(id, {}).get("issue_number") for id in chain],
                })
        chains = sorted(chains, key=lambda x: -x["length"])[:10]

        return {
            "most_referenced": most_ref,
            "blocking_chains": chains,
            "total_relations": len(relations),
        }

    def _get_relations(self) -> List:
        latest = self._get_latest_time()
        if not latest:
            return []
        sql = """
        SELECT r.from_issue_id, r.to_issue_id, r.relation_type
        FROM issue_relations r
        INNER JOIN issues_snapshot i1 ON r.from_issue_id = i1.issue_id
            AND i1.repo_owner = :owner AND i1.repo_name = :repo
            AND i1.snapshot_time = :lt
        INNER JOIN issues_snapshot i2 ON r.to_issue_id = i2.issue_id
            AND i2.repo_owner = :owner2 AND i2.repo_name = :repo2
            AND i2.snapshot_time = :lt
        WHERE r.relation_type IN ('depends_on','blocks','related','mention')
        """
        try:
            return self.storage.execute(sql, {
                "owner": self._repo_owner, "repo": self._repo_name,
                "owner2": self._repo_owner, "repo2": self._repo_name,
                "lt": latest,
            })
        except Exception:
            return []

    def _get_latest_time(self) -> Optional:
        if self._latest_time:
            return self._latest_time
        sql = """
        SELECT snapshot_time FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo
        GROUP BY snapshot_time ORDER BY COUNT(*) DESC LIMIT 1
        """
        try:
            r = self.storage.execute(sql, {"owner": self._repo_owner, "repo": self._repo_name})
            if r and r[0].get("snapshot_time"):
                self._latest_time = r[0]["snapshot_time"]
                return self._latest_time
        except Exception:
            pass
        return None
