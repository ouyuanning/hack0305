#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重复 Issue 检测器
使用 AI 理解判断，不依赖向量库
规则过滤 + AI 判断
"""
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class DuplicateDetector:
    """重复 Issue 检测器（规则 + AI）"""

    def __init__(self, storage=None):
        if storage is None:
            from modules.database_storage.mo_client import MOStorage
            storage = MOStorage()
        self.storage = storage
        self._llm = None

    def _get_llm(self):
        if self._llm is None:
            from modules.llm_parser.llm_parser import LLMParser
            self._llm = LLMParser()
        return self._llm

    def check_duplicate(
        self,
        new_issue_draft: Dict[str, Any],
        repo_owner: str = "",
        repo_name: str = "",
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        检查新 Issue 是否与已有 Issue 重复或相关

        Args:
            new_issue_draft: {"title", "body", "labels"}
            repo_owner, repo_name: 可选，指定仓库
            limit: 查询最近 open Issue 数量

        Returns:
            {
                "is_duplicate": bool,
                "similar_issues": [number, ...],
                "similar_issue_objects": [...],
                "recommendation": "create"|"link"|"merge",
                "reason": str,
                "confidence": float,
                "suggested_action": str
            }
        """
        recent = self._load_recent_open_issues(repo_owner, repo_name, limit)
        if not recent:
            return {
                "is_duplicate": False,
                "similar_issues": [],
                "similar_issue_objects": [],
                "recommendation": "create",
                "reason": "无历史 Issue 可比较",
                "confidence": 0.0,
                "suggested_action": "正常创建",
            }

        candidates = self._rule_based_filter(new_issue_draft, recent)
        if not candidates:
            return {
                "is_duplicate": False,
                "similar_issues": [],
                "similar_issue_objects": [],
                "recommendation": "create",
                "reason": "规则过滤后无相似 Issue",
                "confidence": 0.0,
                "suggested_action": "正常创建",
            }

        return self._ai_based_match(new_issue_draft, candidates)

    def _load_recent_open_issues(
        self, repo_owner: str, repo_name: str, limit: int
    ) -> List[Dict]:
        """从 MO 库加载最近 open Issue"""
        # 兼容 MatrixOne：先查 latest_time，避免子查询
        sql_latest = "SELECT MAX(snapshot_time) as latest FROM issues_snapshot"
        params: Dict[str, Any] = {"limit": limit}
        if repo_owner and repo_name:
            sql_latest += " WHERE repo_owner = :owner AND repo_name = :name"
            params["owner"] = repo_owner
            params["name"] = repo_name

        try:
            rows = self.storage.execute(sql_latest, params)
            latest = rows[0]["latest"] if rows else None
            if not latest:
                return []
        except Exception:
            return []

        sql = """
        SELECT issue_number, title, body, labels, state, created_at, updated_at
        FROM issues_snapshot
        WHERE state = 'open' AND snapshot_time = :latest
        """
        if repo_owner and repo_name:
            sql += " AND repo_owner = :owner AND repo_name = :name"
        sql += " ORDER BY updated_at DESC LIMIT :limit"

        params["latest"] = latest
        try:
            return self.storage.execute(sql, params) or []
        except Exception:
            return []

    def _rule_based_filter(
        self, new_issue: Dict[str, Any], all_issues: List[Dict]
    ) -> List[Dict]:
        """规则过滤：标签、关键词"""
        new_labels = set(new_issue.get("labels") or [])
        if isinstance(new_labels, str):
            new_labels = set(x.strip() for x in new_labels.split(",") if x.strip())
        new_title = (new_issue.get("title") or "").lower()
        new_keywords = self._extract_keywords(new_title)

        scored = []
        for issue in all_issues:
            score = 0
            issue_labels_raw = issue.get("labels") or ""
            if isinstance(issue_labels_raw, str):
                try:
                    issue_labels = set(json.loads(issue_labels_raw)) if issue_labels_raw.startswith("[") else set(x.strip() for x in issue_labels_raw.split(",") if x.strip())
                except Exception:
                    issue_labels = set(x.strip() for x in str(issue_labels_raw).split(",") if x.strip())
            else:
                issue_labels = set(issue_labels_raw) if issue_labels_raw else set()
            common_labels = new_labels & issue_labels
            if common_labels:
                score += len(common_labels) * 10

            issue_title = (issue.get("title") or "").lower()
            issue_keywords = self._extract_keywords(issue_title)
            common_kw = new_keywords & issue_keywords
            if common_kw:
                score += len(common_kw) * 5

            if new_title in issue_title or issue_title in new_title:
                score += 20

            if score > 0:
                scored.append({"issue": issue, "score": score})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return [s["issue"] for s in scored[:10]]

    def _extract_keywords(self, text: str) -> set:
        """简单关键词提取（避免依赖 jieba）"""
        import re as re_mod
        words = re_mod.findall(r"[\u4e00-\u9fff\w]{2,}", text)
        stop = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "issue"}
        return {w for w in words if w.lower() not in stop}

    def _ai_based_match(
        self, new_issue: Dict[str, Any], candidates: List[Dict]
    ) -> Dict[str, Any]:
        """AI 判断是否重复"""
        prompt = f"""
你是 Issue 管理专家。请判断新 Issue 是否与已有 Issue 重复或相关。

新 Issue：
标题：{new_issue.get("title", "")}
描述：{(new_issue.get("body") or "")[:500]}
标签：{", ".join(new_issue.get("labels") or [])}

已有相似 Issue：
"""
        for i, issue in enumerate(candidates[:5], 1):
            body = (issue.get("body") or "")[:200]
            prompt += f"""
{i}. Issue #{issue.get("issue_number")}
   标题：{issue.get("title")}
   描述：{body or "(无描述)"}
   标签：{issue.get("labels")}
   状态：{issue.get("state")}
"""

        prompt += """
请分析并只返回一行合法 JSON（不要 markdown 代码块）：
{
  "is_duplicate": true/false,
  "confidence": 0.95,
  "similar_issues": [8404, 8320],
  "recommendation": "create/link/merge",
  "reason": "简短判断原因",
  "suggested_action": "建议操作"
}

判断标准：
- 完全相同的问题 → merge
- 相关但不同 → link
- 全新问题 → create
"""

        try:
            llm = self._get_llm()
            resp = llm._call_ai("只输出合法 JSON，不要其他文字。", prompt)
            m = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", resp or "")
            if m:
                result = json.loads(m.group(0))
                result.setdefault("similar_issue_objects", [])
                for num in result.get("similar_issues", []):
                    for c in candidates:
                        if c.get("issue_number") == num:
                            result["similar_issue_objects"].append(c)
                            break
                return result
        except Exception as e:
            pass

        return {
            "is_duplicate": False,
            "similar_issues": [],
            "similar_issue_objects": [],
            "recommendation": "create",
            "reason": f"AI 判断失败，降级为规则。候选数：{len(candidates)}",
            "confidence": 0.0,
            "suggested_action": "建议正常创建",
        }
