#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 解析补全脚本

用途：对 ai_summary、ai_tags 等 AI 解析字段为空或异常的 Issue 重新调用 AI 解析并更新。
适用：因网络中断、AI 欠费、解析异常等导致部分 Issue 未完成 AI 解析的场景。

特点：
- 仅处理需要补全的 Issue，不重复解析已成功的
- 消耗 AI API 调用额度，建议在网络稳定、AI 配额充足时运行

使用：
    # 默认 matrixorigin/matrixone
    python3 repair_ai_parse.py

    # 指定仓库
    python3 repair_ai_parse.py --repo-owner matrixorigin --repo-name matrixone

    # 干跑（仅统计，不实际调用 AI）
    python3 repair_ai_parse.py --dry-run
"""

import sys
import os
import json
import argparse
from datetime import datetime

# 添加项目根目录到路径（支持从 scripts/ 运行）
_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_dir)
sys.path.insert(0, _root)

from config.config import validate_config
from modules.database_storage.mo_client import MOStorage
from modules.llm_parser.llm_parser import LLMParser


def get_issues_needing_repair(storage, repo_owner: str, repo_name: str):
    """获取需要补全 AI 解析的 Issue（ai_summary 或 ai_tags 为空）"""
    sql = """
    SELECT issue_id, issue_number, title, body, state, snapshot_time,
           assignee, issue_type, priority, ai_summary, ai_tags,
           labels, milestone, created_at, updated_at, closed_at
    FROM issues_snapshot
    WHERE repo_owner = :owner AND repo_name = :repo
    AND snapshot_time = (
        SELECT MAX(snapshot_time) FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo
    )
    AND (ai_summary IS NULL OR ai_summary = '')
    """
    return storage.execute(sql, {"owner": repo_owner, "repo": repo_name})


def get_comments_for_issue(storage, issue_id: int):
    """从数据库获取某 Issue 的评论"""
    sql = """
    SELECT body, created_at FROM comments WHERE issue_id = :issue_id
    ORDER BY created_at
    """
    rows = storage.execute(sql, {"issue_id": issue_id})
    return [{"body": r.get("body", ""), "created_at": r.get("created_at")} for r in (rows or [])]


def run_repair(
    repo_owner: str = "matrixorigin",
    repo_name: str = "matrixone",
    dry_run: bool = False,
    limit: int = None,
) -> bool:
    """
    执行 AI 解析补全

    参数:
    - repo_owner, repo_name: 仓库
    - dry_run: 仅统计需补全数量，不实际调用 AI
    - limit: 最多补全条数（用于分批，None 表示不限制）

    返回:
    - bool: 是否成功
    """
    try:
        storage = MOStorage()
        parser = LLMParser()

        issues = get_issues_needing_repair(storage, repo_owner, repo_name)
        if not issues:
            print("✅ 无需补全：所有 Issue 均已有 AI 解析结果")
            return True

        total = len(issues)
        print(f"📋 发现 {total} 个 Issue 需补全 AI 解析")
        if dry_run:
            for i, row in enumerate(issues[:10], 1):
                print(f"   {i}. #{row['issue_number']}: {row.get('title', '')[:50]}...")
            if total > 10:
                print(f"   ... 共 {total} 个")
            return True

        if limit:
            issues = issues[:limit]
            print(f"⚠️  限制处理前 {limit} 个")
        success_count = 0
        error_count = 0

        for idx, row in enumerate(issues, 1):
            issue_id = row["issue_id"]
            issue_number = row["issue_number"]
            title = row.get("title", "")
            body = row.get("body", "") or ""
            snapshot_time = row["snapshot_time"]
            state = row.get("state", "open")

            print(f"\n[{idx}/{len(issues)}] 补全 Issue #{issue_number}: {title[:50]}...")

            try:
                comments = get_comments_for_issue(storage, issue_id)
                comment_bodies = [c["body"] for c in comments if c.get("body")]

                classification = parser.classify_issue(title, body)
                issue_type = classification.get("type", "task")
                priority = parser.extract_priority(title, body, issue_type)
                tags = parser.extract_tags(title, body)
                summary = parser.generate_summary(title, body, comment_bodies)

                # 构造完整快照数据用于 UPSERT
                labels = row.get("labels")
                if isinstance(labels, str):
                    try:
                        labels = json.loads(labels) if labels else []
                    except Exception:
                        labels = []
                elif labels is None:
                    labels = []

                issue_snapshot = {
                    "issue_id": issue_id,
                    "issue_number": issue_number,
                    "repo_owner": repo_owner,
                    "repo_name": repo_name,
                    "title": title,
                    "body": body,
                    "state": state,
                    "issue_type": issue_type,
                    "priority": priority,
                    "assignee": row.get("assignee"),
                    "labels": labels,
                    "milestone": row.get("milestone"),
                    "created_at": row.get("created_at"),
                    "updated_at": row.get("updated_at"),
                    "closed_at": row.get("closed_at"),
                    "ai_summary": summary,
                    "ai_tags": tags,
                    "ai_priority": priority,
                    "status": "已关闭" if state == "closed" else "待处理",
                    "progress_percentage": 100.0 if state == "closed" else 0.0,
                    "is_blocked": False,
                    "blocked_reason": None,
                }

                storage.save_issue_snapshot(issue_snapshot, snapshot_time)
                print(f"  ✅ 补全成功")
                success_count += 1
            except Exception as e:
                print(f"  ❌ 补全失败: {e}")
                error_count += 1

        print(f"\n✅ AI 解析补全完成：成功 {success_count}，失败 {error_count}")
        return True
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="AI 解析补全脚本 - 对未完成 AI 解析的 Issue 重新解析",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--repo-owner", default="matrixorigin", help="仓库所有者")
    parser.add_argument("--repo-name", default="matrixone", help="仓库名称")
    parser.add_argument("--dry-run", action="store_true", help="仅统计，不实际调用 AI")
    parser.add_argument("--limit", type=int, default=None, help="最多补全条数（分批用）")

    args = parser.parse_args()

    print("=" * 60)
    print("AI 解析补全脚本")
    print("=" * 60)

    if not validate_config():
        print("\n❌ 配置验证失败，请检查配置文件")
        return 1

    success = run_repair(
        repo_owner=args.repo_owner,
        repo_name=args.repo_name,
        dry_run=args.dry_run,
        limit=args.limit,
    )
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
