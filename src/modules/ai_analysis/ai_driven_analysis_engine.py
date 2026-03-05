#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI驱动的Issue智能分析系统
基于实际业务需求设计：
1. 项目推进分析（每日/每周）
2. 横向关联分析（每周/每月）

依赖：通用 AI API（使用 config 配置的 AI_PROVIDER，默认千问）
适用于 matrixflow 等含 customer/xxx 标签的仓库
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict


class AIAnalysisEngine:
    """AI驱动的分析引擎（使用项目统一的 LLM 调用，支持千问/Claude/OpenAI 等）"""

    def __init__(self, storage):
        self.storage = storage
        self._latest_snapshot_cache = {}
        from modules.llm_parser.llm_parser import LLMParser
        self.llm = LLMParser()

    def _call_ai(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """调用 AI（使用项目配置的提供商，如千问）"""
        return self.llm._call_ai(system_prompt, user_prompt)

    def _get_latest_snapshot_time(self, repo_owner: str, repo_name: str) -> Optional[datetime]:
        """获取最新快照时间（避免子查询，MatrixOne 兼容）"""
        cache_key = f"{repo_owner}/{repo_name}"
        if cache_key in self._latest_snapshot_cache:
            return self._latest_snapshot_cache[cache_key]
        try:
            sql = """
            SELECT MAX(snapshot_time) as latest_time
            FROM issues_snapshot
            WHERE repo_owner = :owner AND repo_name = :repo
            """
            result = self.storage.execute(sql, {"owner": repo_owner, "repo": repo_name})
            if result and result[0].get("latest_time"):
                latest_time = result[0]["latest_time"]
                self._latest_snapshot_cache[cache_key] = latest_time
                return latest_time
        except Exception as e:
            print(f"⚠️  获取最新快照时间失败: {e}")
        return None

    # ========================================================================
    # 第1条线：项目推进分析（高频）
    # ========================================================================

    def analyze_project_progress(self, repo_owner: str, repo_name: str) -> Dict:
        """
        项目推进分析
        1. 识别所有客户项目（customer/xxx 标签）
        2. 构建层级关系：Project → Feature → Task → Bug
        3. 识别堵塞点
        4. 使用AI分析堵塞原因和建议
        """
        print("\n" + "=" * 70)
        print("📊 第1条线：项目推进分析")
        print("=" * 70)

        issues = self._load_issues(repo_owner, repo_name)
        print(f"\n加载了 {len(issues)} 个Issue")

        customers = self._group_by_customer(issues)
        print(f"识别出 {len(customers)} 个客户项目")

        project_analysis = {}
        for customer, customer_issues in customers.items():
            print(f"\n分析客户: {customer} ({len(customer_issues)} 个Issue)")
            hierarchy = self._build_hierarchy(customer_issues)
            blockages = self._identify_blockages(customer_issues)
            ai_insights = self._ai_analyze_project_status(customer, hierarchy, blockages)
            project_analysis[customer] = {
                "total_issues": len(customer_issues),
                "hierarchy": hierarchy,
                "blockages": blockages,
                "ai_insights": ai_insights,
                "last_update": datetime.now().isoformat(),
            }

        return {
            "analysis_type": "项目推进分析",
            "total_customers": len(customers),
            "customers": project_analysis,
            "generated_at": datetime.now().isoformat(),
        }

    def _group_by_customer(self, issues: List[Dict]) -> Dict[str, List[Dict]]:
        """按客户分组Issue"""
        customers = defaultdict(list)
        for issue in issues:
            labels = self._parse_labels(issue.get("labels", []))
            customer_labels = [
                label.replace("customer/", "").replace("/customer/", "")
                for label in labels
                if "customer" in label.lower()
            ]
            for customer in customer_labels:
                customers[customer].append(issue)
        return dict(customers)

    def _build_hierarchy(self, issues: List[Dict]) -> Dict:
        """构建层级结构 L1 项目 → L2 Feature → L3 Task → L4 Bug"""
        hierarchy = {
            "L1_projects": [],
            "L2_features": [],
            "L3_tasks": [],
            "L4_bugs": [],
        }
        for issue in issues:
            title = issue.get("title", "")
            labels = self._parse_labels(issue.get("labels", []))
            if self._is_customer_project(title, labels):
                hierarchy["L1_projects"].append(self._format_issue_summary(issue))
            elif self._is_feature(title, labels):
                hierarchy["L2_features"].append(self._format_issue_summary(issue))
            elif self._is_task(title, labels):
                hierarchy["L3_tasks"].append(self._format_issue_summary(issue))
            elif self._is_bug(title, labels):
                hierarchy["L4_bugs"].append(self._format_issue_summary(issue))

        for level in list(hierarchy.keys()):
            items = hierarchy[level]
            open_count = sum(1 for i in items if i.get("state") == "open")
            hierarchy[f"{level}_stats"] = {
                "total": len(items),
                "open": open_count,
                "closed": len(items) - open_count,
                "completion_rate": round((len(items) - open_count) / len(items), 2) if items else 0,
            }
        return hierarchy

    def _is_customer_project(self, title: str, labels: List[str]) -> bool:
        return any(kw in title.lower() for kw in ["customer project", "客户项目", "project"])

    def _is_feature(self, title: str, labels: List[str]) -> bool:
        return (
            any("feature" in label.lower() for label in labels)
            or "[feature]" in title.lower()
            or "[moi feature]" in title.lower()
        )

    def _is_task(self, title: str, labels: List[str]) -> bool:
        return (
            any("task" in label.lower() for label in labels)
            or "[task]" in title.lower()
            or "[test request]" in title.lower()
        )

    def _is_bug(self, title: str, labels: List[str]) -> bool:
        return any("bug" in label.lower() for label in labels)

    def _format_issue_summary(self, issue: Dict) -> Dict:
        created = issue.get("created_at")
        return {
            "number": issue.get("issue_number", 0),
            "title": issue.get("title", ""),
            "state": issue.get("state", "unknown"),
            "labels": self._parse_labels(issue.get("labels", [])),
            "created_at": str(created) if created else "",
            "is_blocked": issue.get("is_blocked", False),
        }

    def _identify_blockages(self, issues: List[Dict]) -> List[Dict]:
        """识别堵塞点（开放超14天）"""
        blockages = []
        for issue in issues:
            if issue.get("is_blocked") or issue.get("state") == "open":
                created_at = issue.get("created_at")
                if created_at:
                    if hasattr(created_at, "days"):
                        days_open = (datetime.now() - created_at).days
                    else:
                        try:
                            dt = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
                            days_open = (datetime.now(dt.tzinfo) - dt).days if dt.tzinfo else (datetime.now() - dt.replace(tzinfo=None)).days
                        except Exception:
                            days_open = 0
                    if days_open > 14:
                        blockages.append({
                            "issue_number": issue.get("issue_number", 0),
                            "title": issue.get("title", ""),
                            "days_open": days_open,
                            "labels": self._parse_labels(issue.get("labels", [])),
                            "blocked_reason": issue.get("blocked_reason", "未知"),
                        })
        blockages.sort(key=lambda x: x["days_open"], reverse=True)
        return blockages[:10]

    def _ai_analyze_project_status(self, customer: str, hierarchy: Dict, blockages: List[Dict]) -> Dict:
        """使用 AI 分析项目状态（调用项目配置的 AI，如千问）"""
        try:
            system_prompt = """你是一个项目管理专家。请分析客户项目状态，用中文回答，并以JSON格式返回。"""
            user_prompt = f"""
**客户**: {customer}

**层级统计**:
- L1 (Customer Project): {hierarchy.get('L1_projects_stats', {}).get('total', 0)} 个，完成率 {hierarchy.get('L1_projects_stats', {}).get('completion_rate', 0)*100:.1f}%
- L2 (Feature): {hierarchy.get('L2_features_stats', {}).get('total', 0)} 个，完成率 {hierarchy.get('L2_features_stats', {}).get('completion_rate', 0)*100:.1f}%
- L3 (Task): {hierarchy.get('L3_tasks_stats', {}).get('total', 0)} 个，完成率 {hierarchy.get('L3_tasks_stats', {}).get('completion_rate', 0)*100:.1f}%
- L4 (Bug): {hierarchy.get('L4_bugs_stats', {}).get('total', 0)} 个，完成率 {hierarchy.get('L4_bugs_stats', {}).get('completion_rate', 0)*100:.1f}%

**堵塞的Issue** (Top 5):
{json.dumps([b for b in blockages[:5]], indent=2, ensure_ascii=False)}

请用JSON格式返回:
{{
  "health_score": 0-100,
  "health_level": "健康" | "一般" | "风险" | "严重",
  "key_findings": ["发现1", "发现2", "发现3"],
  "blockage_analysis": "堵塞原因分析",
  "recommendations": ["建议1", "建议2", "建议3"],
  "urgent_actions": ["需要立即处理的问题"]
}}
"""
            response_text = self._call_ai(system_prompt, user_prompt)
            if not response_text:
                return {"error": "AI调用失败", "fallback_analysis": "请人工检查项目状态"}
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"error": "AI返回格式错误", "raw": response_text}
        except Exception as e:
            return {"error": f"AI分析失败: {str(e)}", "fallback_analysis": "请人工检查项目状态"}

    # ========================================================================
    # 第2条线：横向关联分析（低频）
    # ========================================================================

    def analyze_cross_customer_patterns(self, repo_owner: str, repo_name: str) -> Dict:
        """横向关联分析：共性Feature、高Bug Feature、AI模式识别"""
        print("\n" + "=" * 70)
        print("🔗 第2条线：横向关联分析")
        print("=" * 70)

        issues = self._load_issues(repo_owner, repo_name)
        shared_features = self._find_shared_features(issues)
        print(f"\n识别出 {len(shared_features)} 个跨客户共用的Feature")
        high_bug_features = self._find_high_bug_features(issues)
        print(f"识别出 {len(high_bug_features)} 个高Bug数的Feature")
        ai_patterns = self._ai_analyze_patterns(shared_features, high_bug_features)

        return {
            "analysis_type": "横向关联分析",
            "shared_features": shared_features,
            "high_bug_features": high_bug_features,
            "ai_patterns": ai_patterns,
            "generated_at": datetime.now().isoformat(),
        }

    def _find_shared_features(self, issues: List[Dict]) -> List[Dict]:
        """识别被多个客户共用的Feature"""
        feature_customers = defaultdict(set)
        for issue in issues:
            labels = self._parse_labels(issue.get("labels", []))
            if self._is_feature(issue.get("title", ""), labels):
                customers = [
                    label.replace("customer/", "").replace("/customer/", "")
                    for label in labels
                    if "customer" in label.lower()
                ]
                for customer in customers:
                    feature_customers[issue.get("issue_number")].add(customer)
        shared = []
        for feature_number, customers in feature_customers.items():
            if len(customers) >= 2:
                feature_issue = next((i for i in issues if i.get("issue_number") == feature_number), None)
                if feature_issue:
                    shared.append({
                        "feature_number": feature_number,
                        "feature_title": feature_issue.get("title", ""),
                        "customers": sorted(list(customers)),
                        "customer_count": len(customers),
                        "state": feature_issue.get("state", "unknown"),
                    })
        shared.sort(key=lambda x: x["customer_count"], reverse=True)
        return shared

    def _find_high_bug_features(self, issues: List[Dict]) -> List[Dict]:
        """识别Bug最多的Feature"""
        features = [
            i
            for i in issues
            if self._is_feature(i.get("title", ""), self._parse_labels(i.get("labels", [])))
        ]
        feature_bugs = []
        for feature in features:
            feature_labels = set(self._parse_labels(feature.get("labels", [])))
            related_bugs = [
                i
                for i in issues
                if self._is_bug(i.get("title", ""), self._parse_labels(i.get("labels", [])))
                and len(set(self._parse_labels(i.get("labels", []))) & feature_labels) > 0
            ]
            if related_bugs:
                affected_customers = set()
                for bug in related_bugs:
                    for label in self._parse_labels(bug.get("labels", [])):
                        if "customer" in label.lower():
                            affected_customers.add(label.replace("customer/", "").replace("/customer/", ""))
                feature_bugs.append({
                    "feature_number": feature.get("issue_number"),
                    "feature_title": feature.get("title", ""),
                    "bug_count": len(related_bugs),
                    "open_bug_count": sum(1 for b in related_bugs if b.get("state") == "open"),
                    "affected_customers": sorted(list(affected_customers)),
                    "severity": "high" if len(related_bugs) > 5 else "medium" if len(related_bugs) > 2 else "low",
                })
        feature_bugs.sort(key=lambda x: x["bug_count"], reverse=True)
        return feature_bugs[:10]

    def _ai_analyze_patterns(self, shared_features: List[Dict], high_bug_features: List[Dict]) -> Dict:
        """使用 AI 分析模式（调用项目配置的 AI，如千问）"""
        try:
            system_prompt = """你是产品策略专家。请分析数据，识别产品和开发的关键模式，用中文回答，并以JSON格式返回。"""
            user_prompt = f"""
**跨客户共用Feature** (Top 5):
{json.dumps(shared_features[:5], indent=2, ensure_ascii=False)}

**高Bug数Feature** (Top 5):
{json.dumps(high_bug_features[:5], indent=2, ensure_ascii=False)}

请用JSON格式返回:
{{
  "common_needs_pattern": "共性需求的模式总结",
  "high_bug_reasons": "高Bug功能的可能原因",
  "strategic_recommendations": ["战略建议1", "战略建议2"],
  "resource_allocation": {{
    "should_prioritize": ["应该优先投入的功能"],
    "should_stabilize": ["应该稳定的功能"]
  }},
  "customer_impact_analysis": "对客户的影响分析"
}}
"""
            response_text = self._call_ai(system_prompt, user_prompt)
            if not response_text:
                return {"error": "AI调用失败"}
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"error": "AI返回格式错误", "raw": response_text}
        except Exception as e:
            return {"error": f"AI分析失败: {str(e)}"}

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def _load_issues(self, repo_owner: str, repo_name: str) -> List[Dict]:
        """加载Issue数据（MatrixOne兼容：避免子查询）"""
        latest_time = self._get_latest_snapshot_time(repo_owner, repo_name)
        if not latest_time:
            return []
        sql = """
        SELECT *
        FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo
        AND snapshot_time = :latest_time
        """
        result = self.storage.execute(
            sql,
            {"owner": repo_owner, "repo": repo_name, "latest_time": latest_time},
        )
        return result if result else []

    def _parse_labels(self, labels) -> List:
        """解析labels字段"""
        if isinstance(labels, str):
            try:
                labels = json.loads(labels)
            except Exception:
                return []
        return labels if isinstance(labels, list) else []
