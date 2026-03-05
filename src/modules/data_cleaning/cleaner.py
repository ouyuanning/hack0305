#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WF-005: 历史数据清洗模块
对MatrixOne库中的历史Issue数据进行清洗、规范化、AI重新打标签，存入实验库。
"""

import json
import re
import time
import random
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import yaml


class DataCleaner:
    """历史数据清洗器"""

    def __init__(self, storage, llm=None, config_path: str = None):
        self.storage = storage
        self.llm = llm
        self.config = self._load_config(config_path)
        self._ensure_tables()

    # ------------------------------------------------------------------
    # 配置加载
    # ------------------------------------------------------------------

    def _load_config(self, config_path: str = None) -> Dict:
        if config_path:
            p = Path(config_path)
        else:
            p = Path(__file__).parent.parent.parent / "config" / "cleaning_rules.yaml"
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    # ------------------------------------------------------------------
    # 表初始化
    # ------------------------------------------------------------------

    def _ensure_tables(self):
        """创建 experimental_issues 和 data_cleaning_log 表（如不存在）"""
        ddl_experimental = """
        CREATE TABLE IF NOT EXISTS experimental_issues (
            id INT AUTO_INCREMENT PRIMARY KEY,
            issue_id BIGINT NOT NULL,
            issue_number INT NOT NULL,
            repo_owner VARCHAR(100) NOT NULL,
            repo_name VARCHAR(100) NOT NULL,
            title VARCHAR(500) NOT NULL,
            body TEXT,
            state VARCHAR(20) NOT NULL,
            labels JSON,
            assignee VARCHAR(100),
            milestone VARCHAR(100),
            ai_issue_type VARCHAR(50),
            ai_priority VARCHAR(10),
            ai_labels JSON,
            ai_corrected BOOLEAN DEFAULT FALSE,
            quality_score FLOAT DEFAULT 0.0,
            validation_passed BOOLEAN DEFAULT TRUE,
            cleaned_at DATETIME NOT NULL,
            cleaning_version VARCHAR(50),
            source_snapshot_time DATETIME,
            created_at DATETIME,
            updated_at DATETIME,
            closed_at DATETIME,
            INDEX idx_exp_issue_id (issue_id),
            INDEX idx_exp_repo (repo_owner, repo_name),
            INDEX idx_exp_cleaned (cleaned_at),
            UNIQUE KEY uk_exp_issue (issue_id, cleaning_version)
        )
        """

        ddl_log = """
        CREATE TABLE IF NOT EXISTS data_cleaning_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            issue_id BIGINT NOT NULL,
            cleaning_version VARCHAR(50) NOT NULL,
            action_type VARCHAR(50),
            field_name VARCHAR(100),
            old_value TEXT,
            new_value TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_log_issue (issue_id),
            INDEX idx_log_version (cleaning_version)
        )
        """
        try:
            self.storage.execute(ddl_experimental)
            self.storage.execute(ddl_log)
        except Exception as e:
            print(f"⚠️  建表跳过（可能已存在）: {e}")

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    def run(
        self,
        repo_owner: str,
        repo_name: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict:
        """执行完整清洗流程，返回统计信息"""
        start_time = datetime.now()
        version = datetime.now().strftime("%Y%m%d%H%M%S")

        print("=" * 60)
        print(f"WF-005 历史数据清洗 - {repo_owner}/{repo_name}")
        print(f"清洗版本: {version}")
        print("=" * 60)

        # 步骤1: 读取数据
        print("\n📥 步骤1: 读取历史Issue数据...")
        raw_issues = self.load_issues(repo_owner, repo_name, start_date, end_date)
        print(f"  读取到 {len(raw_issues)} 条Issue")
        if not raw_issues:
            return {"total_issues_read": 0, "status": "no_data"}

        # 步骤2: 清洗规范化
        print("\n🧹 步骤2: 数据清洗和规范化...")
        cleaned, clean_stats = self.clean_data(raw_issues)
        print(f"  去重后: {len(cleaned)} 条")
        print(f"  字段规范化: {clean_stats.get('normalized', 0)} 条")

        # 步骤3: AI重新打标签
        print("\n🤖 步骤3: AI重新打标签...")
        relabeled, ai_stats = self.ai_relabel(cleaned, version)
        print(f"  AI处理成功: {ai_stats.get('success', 0)} 条")
        print(f"  AI处理失败: {ai_stats.get('failed', 0)} 条")

        # 步骤4: 质量验证
        print("\n✅ 步骤4: 质量验证...")
        passed, failed, quality_report = self.validate_quality(relabeled)
        print(f"  通过: {len(passed)} 条, 未达标: {len(failed)} 条")
        print(f"  平均质量分: {quality_report.get('average_quality_score', 0):.2f}")

        # 步骤5: 存入实验库
        print("\n💾 步骤5: 存入实验库...")
        save_stats = self.save_to_experimental(passed, version)
        print(f"  成功: {save_stats['success_count']}, 失败: {save_stats['error_count']}")

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # 生成报告
        result = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": round(duration, 1),
            "repo_owner": repo_owner,
            "repo_name": repo_name,
            "cleaning_version": version,
            "total_issues_read": len(raw_issues),
            "duplicates_removed": clean_stats.get("duplicates_removed", 0),
            "records_cleaned": len(cleaned),
            "ai_success": ai_stats.get("success", 0),
            "ai_failed": ai_stats.get("failed", 0),
            "quality_passed": len(passed),
            "quality_failed": len(failed),
            "average_quality_score": quality_report.get("average_quality_score", 0),
            "saved_count": save_stats["success_count"],
            "status": "completed",
        }

        report_md = self._generate_report(result)
        report_dir = Path(__file__).parent.parent.parent / "data" / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / f"cleaning_report_{version}.md"
        report_file.write_text(report_md, encoding="utf-8")
        print(f"\n📄 清洗报告已保存: {report_file}")

        print(f"\n✅ 清洗完成，耗时 {duration:.1f} 秒")
        return result

    # ------------------------------------------------------------------
    # 步骤1: 读取数据
    # ------------------------------------------------------------------

    def load_issues(
        self,
        repo_owner: str,
        repo_name: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict]:
        """从 issues_snapshot 读取历史Issue"""
        # 获取最新快照时间
        sql_latest = """
        SELECT MAX(snapshot_time) AS latest FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo
        """
        rows = self.storage.execute(sql_latest, {"owner": repo_owner, "repo": repo_name})
        if not rows or not rows[0].get("latest"):
            return []
        latest = rows[0]["latest"]

        # 构建查询
        sql = """
        SELECT issue_id, issue_number, repo_owner, repo_name,
               title, body, state, issue_type, priority, assignee,
               labels, milestone, created_at, updated_at, closed_at,
               ai_summary, ai_tags, ai_priority, status,
               progress_percentage, is_blocked, blocked_reason, snapshot_time
        FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo AND snapshot_time = :latest
        """
        params: Dict[str, Any] = {"owner": repo_owner, "repo": repo_name, "latest": latest}

        if start_date:
            sql += " AND created_at >= :start"
            params["start"] = str(start_date)
        if end_date:
            sql += " AND created_at <= :end"
            params["end"] = str(end_date)

        rows = self.storage.execute(sql, params)
        issues = [dict(r) for r in rows] if rows else []

        # 解析 labels JSON
        for issue in issues:
            raw = issue.get("labels")
            if isinstance(raw, str):
                try:
                    issue["labels"] = json.loads(raw)
                except Exception:
                    issue["labels"] = []
            elif not isinstance(raw, list):
                issue["labels"] = []
        return issues

    # ------------------------------------------------------------------
    # 步骤2: 清洗规范化
    # ------------------------------------------------------------------

    def clean_data(self, raw_issues: List[Dict]) -> Tuple[List[Dict], Dict]:
        """去重、字段规范化、缺失值处理"""
        stats = {"duplicates_removed": 0, "normalized": 0}

        # 2.1 去重
        seen: Dict[int, Dict] = {}
        for issue in raw_issues:
            iid = issue.get("issue_id")
            if iid is not None:
                seen[iid] = issue  # 后出现的覆盖前面的
        stats["duplicates_removed"] = len(raw_issues) - len(seen)
        deduped = list(seen.values())

        # 2.2 字段规范化
        rules = self.config.get("field_normalization", {})
        mapping = self.config.get("label_mapping", {})
        deprecated = set(self.config.get("deprecated_labels", []))

        cleaned = []
        for issue in deduped:
            issue = self._normalize_fields(issue, rules)
            issue = self._standardize_labels(issue, mapping, deprecated)
            issue = self._supplement_data(issue)
            cleaned.append(issue)
            stats["normalized"] += 1

        return cleaned, stats

    def _normalize_fields(self, issue: Dict, rules: Dict) -> Dict:
        c = issue.copy()
        # 标题
        title_rules = rules.get("title", {})
        if c.get("title"):
            t = c["title"].strip() if title_rules.get("trim", True) else c["title"]
            max_len = title_rules.get("max_length", 256)
            c["title"] = t[:max_len]
        # 状态
        state_rules = rules.get("state", {})
        valid = state_rules.get("valid_values", ["open", "closed"])
        if c.get("state") and c["state"].lower() not in valid:
            c["state"] = state_rules.get("default", "open")
        elif c.get("state"):
            c["state"] = c["state"].lower()
        return c

    def _standardize_labels(self, issue: Dict, mapping: Dict, deprecated: set) -> Dict:
        labels = issue.get("labels", [])
        result = []
        for label in labels:
            name = label.get("name", label) if isinstance(label, dict) else str(label)
            if name in deprecated:
                continue
            if name in mapping:
                name = mapping[name]
            result.append(name)
        issue["_label_names"] = result
        return issue

    def _supplement_data(self, issue: Dict) -> Dict:
        """补全可推断的字段"""
        if not issue.get("issue_number") and issue.get("issue_id"):
            pass  # issue_number 通常已有
        return issue

    # ------------------------------------------------------------------
    # 步骤3: AI重新打标签
    # ------------------------------------------------------------------

    def ai_relabel(self, issues: List[Dict], version: str) -> Tuple[List[Dict], Dict]:
        """AI批量重新分析Issue，规范化类型、优先级、Labels"""
        stats = {"success": 0, "failed": 0, "skipped": 0}
        if not self.llm:
            # 无LLM时使用规则回退
            for issue in issues:
                rb = self._rule_fallback(issue)
                issue["ai_issue_type"] = rb.get("issue_type", issue.get("issue_type"))
                issue["ai_priority"] = rb.get("priority", issue.get("priority"))
                issue["ai_labels"] = issue.get("_label_names", [])
                issue["ai_corrected"] = False
                stats["skipped"] += 1
            return issues, stats

        batch_size = self.config.get("ai", {}).get("batch_size", 50)
        total = len(issues)

        for idx in range(0, total, batch_size):
            batch = issues[idx : idx + batch_size]
            batch_num = idx // batch_size + 1
            total_batches = (total - 1) // batch_size + 1
            print(f"  批次 {batch_num}/{total_batches} ({len(batch)} 条)")

            for issue in batch:
                try:
                    ai_result = self._ai_analyze_single(issue)
                    issue["ai_issue_type"] = ai_result.get("issue_type", issue.get("issue_type"))
                    issue["ai_priority"] = ai_result.get("priority", issue.get("priority"))
                    issue["ai_labels"] = ai_result.get("labels", issue.get("_label_names", []))
                    issue["ai_corrected"] = True
                    self._log_change(issue.get("issue_id"), version, "ai_relabel", "ai_issue_type",
                                     issue.get("issue_type"), issue["ai_issue_type"])
                    stats["success"] += 1
                except Exception as e:
                    print(f"    ⚠️ Issue #{issue.get('issue_number')} AI失败: {e}")
                    fb = self._rule_fallback(issue)
                    issue["ai_issue_type"] = fb.get("issue_type", issue.get("issue_type"))
                    issue["ai_priority"] = fb.get("priority", issue.get("priority"))
                    issue["ai_labels"] = issue.get("_label_names", [])
                    issue["ai_corrected"] = False
                    stats["failed"] += 1

            # 批次间暂停，避免限流
            if idx + batch_size < total:
                time.sleep(1)

        return issues, stats

    def _ai_analyze_single(self, issue: Dict) -> Dict:
        """调用AI分析单个Issue"""
        title = issue.get("title", "")
        body = (issue.get("body") or "")[:500]
        labels = issue.get("_label_names", [])

        system_prompt = "你是Issue标注专家，负责规范化Issue的分类和标签。只返回JSON，不要其他说明。"
        user_prompt = f"""请分析以下Issue，返回规范化的分类和标签。

标题: {title}
正文: {body}
当前Labels: {labels}

规则：
- issue_type: bug / feature / task / question
- priority: P0 / P1 / P2 / P3
- labels: 使用标准前缀 kind/, area/, severity/, customer/

返回JSON:
{{"issue_type": "...", "priority": "...", "labels": [...]}}"""

        resp = self.llm._call_ai(system_prompt, user_prompt)
        if not resp:
            raise ValueError("AI返回为空")

        # 提取JSON
        match = re.search(r"\{[^{}]*\}", resp, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"无法解析AI响应: {resp[:200]}")

    def _rule_fallback(self, issue: Dict) -> Dict:
        """基于规则的回退分类"""
        title = (issue.get("title") or "").lower()
        labels = issue.get("_label_names", [])
        label_str = " ".join(labels).lower()

        # 类型判断
        issue_type = "task"
        if any(kw in title or kw in label_str for kw in ["bug", "fix", "crash", "error"]):
            issue_type = "bug"
        elif any(kw in title or kw in label_str for kw in ["feature", "enhancement", "新功能", "支持"]):
            issue_type = "feature"
        elif any(kw in title or kw in label_str for kw in ["question", "问题", "help"]):
            issue_type = "question"

        # 优先级判断
        priority = "P2"
        if any(kw in title for kw in ["紧急", "urgent", "critical", "p0"]):
            priority = "P0"
        elif any(kw in title for kw in ["重要", "high", "p1"]):
            priority = "P1"
        elif any(kw in title for kw in ["low", "minor", "p3"]):
            priority = "P3"

        return {"issue_type": issue_type, "priority": priority}

    def _log_change(self, issue_id, version, action, field, old_val, new_val):
        """记录变更日志"""
        if old_val == new_val:
            return
        try:
            sql = """
            INSERT INTO data_cleaning_log (issue_id, cleaning_version, action_type, field_name, old_value, new_value)
            VALUES (:iid, :ver, :action, :field, :old, :new)
            """
            self.storage.execute(sql, {
                "iid": issue_id, "ver": version, "action": action,
                "field": field, "old": str(old_val)[:1000] if old_val else None,
                "new": str(new_val)[:1000] if new_val else None,
            })
        except Exception:
            pass  # 日志写入失败不影响主流程

    # ------------------------------------------------------------------
    # 步骤4: 质量验证
    # ------------------------------------------------------------------

    def validate_quality(self, issues: List[Dict]) -> Tuple[List[Dict], List[Dict], Dict]:
        """质量验证：评分、必需字段检查，返回 (passed, failed, quality_report)"""
        qc = self.config.get("quality", self.config.get("quality_checks", {}))
        required_fields = qc.get("required_fields", ["title", "state"])
        min_score = qc.get("min_quality_score", 0.7)

        scores: List[float] = []
        passed: List[Dict] = []
        failed: List[Dict] = []

        for issue in issues:
            # 必需字段检查
            missing = [f for f in required_fields if not issue.get(f)]
            score = self._quality_score(issue)
            issue["quality_score"] = round(score, 4)
            issue["validation_passed"] = (score >= min_score and len(missing) == 0)
            scores.append(score)

            if issue["validation_passed"]:
                passed.append(issue)
            else:
                failed.append(issue)

        sorted_scores = sorted(scores) if scores else [0]
        report = {
            "total_issues": len(issues),
            "average_quality_score": round(sum(scores) / len(scores), 4) if scores else 0,
            "median_quality_score": round(sorted_scores[len(sorted_scores) // 2], 4),
            "min_quality_score": round(min(sorted_scores), 4),
            "max_quality_score": round(max(sorted_scores), 4),
            "passed_count": len(passed),
            "failed_count": len(failed),
            "pass_rate": round(len(passed) / len(issues), 4) if issues else 0,
        }
        return passed, failed, report

    def _quality_score(self, issue: Dict) -> float:
        """计算单条Issue的质量分数 (0-1)"""
        score = 0.0
        max_score = 100.0

        # 标题 (20)
        title = issue.get("title") or ""
        if 10 <= len(title) <= 200:
            score += 20
        elif len(title) > 0:
            score += 10

        # Labels (30)
        labels = issue.get("_label_names") or issue.get("ai_labels") or []
        if len(labels) >= 2:
            score += 15
        elif len(labels) >= 1:
            score += 8
        if any("kind/" in str(l) for l in labels):
            score += 10
        if any("area/" in str(l) for l in labels):
            score += 5

        # AI分析 (25)
        if issue.get("ai_corrected"):
            score += 15
        if issue.get("ai_issue_type"):
            score += 5
        if issue.get("ai_priority"):
            score += 5

        # 正文 (15)
        body = issue.get("body") or ""
        if len(body) >= 50:
            score += 15
        elif len(body) > 0:
            score += 5

        # 其他字段 (10)
        if issue.get("assignee"):
            score += 5
        if issue.get("milestone"):
            score += 5

        return score / max_score

    # ------------------------------------------------------------------
    # 步骤5: 存入实验库
    # ------------------------------------------------------------------

    def save_to_experimental(self, issues: List[Dict], version: str) -> Dict:
        """将验证通过的Issue保存到 experimental_issues 表"""
        success_count = 0
        error_count = 0

        sql = """
        INSERT INTO experimental_issues (
            issue_id, issue_number, repo_owner, repo_name,
            title, body, state, labels, assignee, milestone,
            ai_issue_type, ai_priority, ai_labels, ai_corrected,
            quality_score, validation_passed,
            cleaned_at, cleaning_version, source_snapshot_time,
            created_at, updated_at, closed_at
        ) VALUES (
            :issue_id, :issue_number, :repo_owner, :repo_name,
            :title, :body, :state, :labels, :assignee, :milestone,
            :ai_issue_type, :ai_priority, :ai_labels, :ai_corrected,
            :quality_score, :validation_passed,
            :cleaned_at, :cleaning_version, :source_snapshot_time,
            :created_at, :updated_at, :closed_at
        )
        ON DUPLICATE KEY UPDATE
            title = VALUES(title),
            body = VALUES(body),
            state = VALUES(state),
            labels = VALUES(labels),
            ai_issue_type = VALUES(ai_issue_type),
            ai_priority = VALUES(ai_priority),
            ai_labels = VALUES(ai_labels),
            quality_score = VALUES(quality_score),
            cleaned_at = VALUES(cleaned_at)
        """

        now = datetime.now()
        for issue in issues:
            try:
                self.storage.execute(sql, {
                    "issue_id": issue["issue_id"],
                    "issue_number": issue["issue_number"],
                    "repo_owner": issue["repo_owner"],
                    "repo_name": issue["repo_name"],
                    "title": issue.get("title", ""),
                    "body": issue.get("body"),
                    "state": issue.get("state", "open"),
                    "labels": json.dumps(issue.get("_label_names") or issue.get("labels") or [], ensure_ascii=False),
                    "assignee": issue.get("assignee"),
                    "milestone": issue.get("milestone"),
                    "ai_issue_type": issue.get("ai_issue_type"),
                    "ai_priority": issue.get("ai_priority"),
                    "ai_labels": json.dumps(issue.get("ai_labels") or [], ensure_ascii=False),
                    "ai_corrected": issue.get("ai_corrected", False),
                    "quality_score": issue.get("quality_score", 0.0),
                    "validation_passed": issue.get("validation_passed", True),
                    "cleaned_at": now,
                    "cleaning_version": version,
                    "source_snapshot_time": issue.get("snapshot_time"),
                    "created_at": issue.get("created_at"),
                    "updated_at": issue.get("updated_at"),
                    "closed_at": issue.get("closed_at"),
                })
                success_count += 1
            except Exception as e:
                print(f"    ⚠️ 保存Issue #{issue.get('issue_number')} 失败: {e}")
                error_count += 1

        return {"success_count": success_count, "error_count": error_count, "total": len(issues)}

    # ------------------------------------------------------------------
    # 报告生成
    # ------------------------------------------------------------------

    def _generate_report(self, stats: Dict) -> str:
        """生成 Markdown 格式的清洗报告"""
        return f"""# 数据清洗报告

## 执行信息
- 清洗版本: {stats.get('cleaning_version', 'N/A')}
- 开始时间: {stats.get('start_time', '')}
- 结束时间: {stats.get('end_time', '')}
- 总耗时: {stats.get('duration_seconds', 0)} 秒
- 仓库: {stats.get('repo_owner', '')}/{stats.get('repo_name', '')}

## 数据统计
| 指标 | 数值 |
|------|------|
| 读取Issue总数 | {stats.get('total_issues_read', 0)} |
| 去重移除 | {stats.get('duplicates_removed', 0)} |
| 清洗后记录 | {stats.get('records_cleaned', 0)} |
| AI成功 | {stats.get('ai_success', 0)} |
| AI失败 | {stats.get('ai_failed', 0)} |

## 质量验证
| 指标 | 数值 |
|------|------|
| 通过验证 | {stats.get('quality_passed', 0)} |
| 未达标 | {stats.get('quality_failed', 0)} |
| 平均质量分 | {stats.get('average_quality_score', 0):.2f} |

## 存储结果
| 指标 | 数值 |
|------|------|
| 成功写入 | {stats.get('saved_count', 0)} |
| 状态 | {stats.get('status', '')} |
"""
