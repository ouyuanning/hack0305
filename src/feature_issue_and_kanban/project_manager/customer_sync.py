#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WF-006 补充: 客户 Issue 同步
从 issues_snapshot 中筛选带 customer/ 标签的 Issue，写入 customer_issues 每日快照。
"""
import json
from datetime import date
from typing import Optional


class CustomerSync:
    def __init__(self, storage):
        self.storage = storage
        self._ensure_table()

    def _ensure_table(self):
        """创建 customer_issues 表（如不存在）"""
        ddl = """
        CREATE TABLE IF NOT EXISTS customer_issues (
            id INT AUTO_INCREMENT PRIMARY KEY,
            issue_number INT NOT NULL,
            repo_owner VARCHAR(100) NOT NULL,
            repo_name VARCHAR(100) NOT NULL,
            issue_title VARCHAR(500),
            issue_state VARCHAR(20),
            issue_url VARCHAR(255),
            customer_tag VARCHAR(100) NOT NULL,
            priority VARCHAR(10),
            severity VARCHAR(20),
            assignee VARCHAR(100),
            snapshot_date DATE NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_cust_repo (repo_owner, repo_name),
            INDEX idx_cust_tag (customer_tag),
            INDEX idx_cust_date (snapshot_date),
            UNIQUE KEY uk_customer_issue (issue_number, repo_owner, repo_name, customer_tag, snapshot_date)
        )
        """
        try:
            self.storage.execute(ddl)
        except Exception as e:
            print(f"⚠️  customer_issues 建表跳过（可能已存在）: {e}")

    def sync_customer_issues(
        self,
        repo_owner: str,
        repo_name: str,
        customer_tag: str,
        snapshot_date: Optional[date] = None,
    ) -> int:
        """
        将指定仓库、带 customer_tag 的 Issue 同步到 customer_issues 表。
        :return: 写入或更新的条数
        """
        snapshot_date = snapshot_date or date.today()

        # 取最新快照时间
        sql_latest = """
        SELECT MAX(snapshot_time) AS latest FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo
        """
        rows = self.storage.execute(sql_latest, {"owner": repo_owner, "repo": repo_name})
        if not rows or not rows[0].get("latest"):
            return 0
        latest = rows[0]["latest"]

        # 查带 customer_tag 的 issues
        sql_issues = """
        SELECT issue_number, title, state, assignee, labels, priority
        FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo AND snapshot_time = :latest
        AND (labels LIKE :tag_like)
        """
        issues = self.storage.execute(sql_issues, {
            "owner": repo_owner,
            "repo": repo_name,
            "latest": latest,
            "tag_like": f"%{customer_tag}%",
        })
        if not issues:
            return 0

        count = 0
        for i in issues:
            try:
                severity = self._extract_severity(i.get("labels"))
                self._upsert_customer_issue(
                    repo_owner=repo_owner,
                    repo_name=repo_name,
                    issue_number=i["issue_number"],
                    issue_title=i.get("title") or "",
                    issue_state=i.get("state") or "open",
                    assignee=i.get("assignee"),
                    priority=i.get("priority"),
                    severity=severity,
                    customer_tag=customer_tag,
                    snapshot_date=snapshot_date,
                )
                count += 1
            except Exception as e:
                if "Duplicate" in str(e) or "1062" in str(e):
                    count += 1
                else:
                    raise
        return count

    def _extract_severity(self, labels) -> Optional[str]:
        """从 labels 中提取 severity/ 前缀的标签值"""
        if not labels:
            return None
        if isinstance(labels, str):
            try:
                labels = json.loads(labels)
            except Exception:
                return None
        for label in labels:
            name = label.get("name", label) if isinstance(label, dict) else str(label)
            if name.startswith("severity/"):
                return name.split("/", 1)[1]
        return None

    def _upsert_customer_issue(
        self,
        repo_owner: str,
        repo_name: str,
        issue_number: int,
        issue_title: str,
        issue_state: str,
        customer_tag: str,
        snapshot_date: date,
        assignee: Optional[str] = None,
        priority: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> None:
        issue_url = f"https://github.com/{repo_owner}/{repo_name}/issues/{issue_number}"
        sql = """
        INSERT INTO customer_issues (
            issue_number, repo_owner, repo_name, issue_title, issue_state, issue_url,
            customer_tag, priority, severity, assignee, snapshot_date
        ) VALUES (
            :issue_number, :repo_owner, :repo_name, :issue_title, :issue_state, :issue_url,
            :customer_tag, :priority, :severity, :assignee, :snapshot_date
        )
        ON DUPLICATE KEY UPDATE
            issue_title = VALUES(issue_title),
            issue_state = VALUES(issue_state),
            priority = VALUES(priority),
            severity = VALUES(severity),
            assignee = VALUES(assignee),
            updated_at = CURRENT_TIMESTAMP
        """
        self.storage.execute(sql, {
            "issue_number": issue_number,
            "repo_owner": repo_owner,
            "repo_name": repo_name,
            "issue_title": issue_title,
            "issue_state": issue_state,
            "issue_url": issue_url,
            "customer_tag": customer_tag,
            "priority": priority,
            "severity": severity,
            "assignee": assignee,
            "snapshot_date": snapshot_date,
        })
