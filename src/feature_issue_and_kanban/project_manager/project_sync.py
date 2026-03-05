#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目 Issue 同步：从 issues_snapshot 中筛选带指定项目标签的 Issue，写入 project_issues 每日快照。
"""
import json
from datetime import date
from typing import List, Optional


class ProjectSync:
    def __init__(self, storage):
        self.storage = storage

    def sync_project_issues(
        self,
        repo_owner: str,
        repo_name: str,
        project_tag: str,
        snapshot_date: Optional[date] = None,
    ) -> int:
        """
        将指定仓库、带 project_tag 的 Issue 同步到 project_issues 表。
        :return: 写入或更新的条数
        """
        snapshot_date = snapshot_date or date.today()
        # 取该仓库最新快照时间
        sql_latest = """
        SELECT MAX(snapshot_time) AS latest FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo
        """
        rows = self.storage.execute(sql_latest, {"owner": repo_owner, "repo": repo_name})
        if not rows or not rows[0].get("latest"):
            return 0
        latest = rows[0]["latest"]
        # 查带 project_tag 的 issues（labels 为 JSON 或字符串）
        sql_issues = """
        SELECT issue_number, title, body, state, assignee, labels, milestone, created_at, updated_at, closed_at,
               progress_percentage, is_blocked, blocked_reason
        FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo AND snapshot_time = :latest
        AND (labels LIKE :tag_like)
        """
        issues = self.storage.execute(sql_issues, {
            "owner": repo_owner,
            "repo": repo_name,
            "latest": latest,
            "tag_like": f"%{project_tag}%",
        })
        if not issues:
            return 0
        count = 0
        for i in issues:
            try:
                self._upsert_project_issue(
                    repo_owner=repo_owner,
                    repo_name=repo_name,
                    issue_number=i["issue_number"],
                    issue_title=i.get("title") or "",
                    issue_state=i.get("state") or "open",
                    assignee=i.get("assignee"),
                    progress=int(i.get("progress_percentage") or 0),
                    snapshot_date=snapshot_date,
                    project_tag=project_tag,
                )
                count += 1
            except Exception as e:
                if "Duplicate" in str(e) or "1062" in str(e):
                    count += 1
                else:
                    raise
        return count

    def _upsert_project_issue(
        self,
        repo_owner: str,
        repo_name: str,
        issue_number: int,
        issue_title: str,
        issue_state: str,
        snapshot_date: date,
        project_tag: str,
        assignee: Optional[str] = None,
        progress: int = 0,
    ) -> None:
        issue_url = f"https://github.com/{repo_owner}/{repo_name}/issues/{issue_number}"
        pm_status = "completed" if issue_state == "closed" else "in_progress"
        sql = """
        INSERT INTO project_issues (
            issue_number, repo_owner, repo_name, issue_title, issue_state, issue_url,
            project_tag, pm_status, progress, assignee, snapshot_date
        ) VALUES (
            :issue_number, :repo_owner, :repo_name, :issue_title, :issue_state, :issue_url,
            :project_tag, :pm_status, :progress, :assignee, :snapshot_date
        )
        ON DUPLICATE KEY UPDATE
            issue_title = VALUES(issue_title),
            issue_state = VALUES(issue_state),
            pm_status = VALUES(pm_status),
            progress = VALUES(progress),
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
            "project_tag": project_tag,
            "pm_status": pm_status,
            "progress": progress,
            "assignee": assignee,
            "snapshot_date": snapshot_date,
        })
