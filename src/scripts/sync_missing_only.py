#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
只同步「GitHub 有、DB 里没有」的 Issue
用途：上次同步时部分 Issue 因报错未入库，用本脚本只对这些漏掉的做拉取 + AI 解析 + 入库，不重跑全量，省 token。
用法（在项目根目录执行）：
  python3 scripts/sync_missing_only.py --repo-owner matrixorigin --repo-name matrixone
  python3 scripts/sync_missing_only.py --repo-owner matrixorigin --repo-name matrixone --dry-run  # 仅列出将补全的数量
"""
import sys
import os
import argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from modules.github_collector.github_api import GitHubCollector
from modules.llm_parser.llm_parser import LLMParser
from modules.database_storage.mo_client import MOStorage


def get_github_issue_numbers(collector: GitHubCollector, repo_owner: str, repo_name: str) -> set:
    """从 GitHub 拉取当前仓库所有 Issue 的 number（分页，只收集编号）"""
    numbers = set()
    page = 1
    per_page = 100
    while True:
        issues, raw_count = collector.fetch_issues(
            repo_owner, repo_name, state="all", since=None, page=page, per_page=per_page
        )
        for i in issues:
            if i.get("pull_request") is None:  # 只要 Issue，不要 PR
                num = i.get("number")
                if num is not None:
                    numbers.add(num)
        print(f"  已获取 {len(numbers)} 个 Issue 编号（第 {page} 页）...")
        if raw_count < per_page:
            break
        page += 1
    return numbers


def get_db_issue_numbers(storage: MOStorage, repo_owner: str, repo_name: str) -> set:
    """获取 DB 最新快照中该仓库已有的 issue_number"""
    latest = storage.execute(
        "SELECT MAX(snapshot_time) as t FROM issues_snapshot WHERE repo_owner = :ro AND repo_name = :rn",
        {"ro": repo_owner, "rn": repo_name}
    )
    if not latest or not latest[0].get("t"):
        return set()
    t = latest[0]["t"]
    result = storage.execute(
        "SELECT DISTINCT issue_number FROM issues_snapshot WHERE repo_owner = :ro AND repo_name = :rn AND snapshot_time = :t",
        {"ro": repo_owner, "rn": repo_name, "t": t}
    )
    if not result:
        return set()
    return {row["issue_number"] for row in result}


def main():
    parser = argparse.ArgumentParser(description="只同步 GitHub 有但 DB 没有的 Issue，省 token")
    parser.add_argument("--repo-owner", required=True, help="仓库 owner")
    parser.add_argument("--repo-name", required=True, help="仓库 name")
    parser.add_argument("--dry-run", action="store_true", help="仅统计将补全数量，不实际拉取与解析")
    args = parser.parse_args()
    repo_owner = args.repo_owner
    repo_name = args.repo_name
    dry_run = args.dry_run

    print("=" * 60)
    print("只同步「漏网」Issue（GitHub 有、DB 无）")
    print(f"仓库: {repo_owner}/{repo_name}")
    print("=" * 60)

    collector = GitHubCollector()
    storage = MOStorage()

    print("\n📥 获取 GitHub 上所有 Issue 编号...")
    gh_numbers = get_github_issue_numbers(collector, repo_owner, repo_name)
    print(f"   GitHub 共 {len(gh_numbers)} 个 Issue")

    print("\n📂 获取 DB 最新快照中已有编号...")
    db_numbers = get_db_issue_numbers(storage, repo_owner, repo_name)
    print(f"   DB 已有 {len(db_numbers)} 个 Issue")

    missing = sorted(gh_numbers - db_numbers)
    print(f"\n📋 漏掉未入库: {len(missing)} 个 Issue")
    if not missing:
        print("✅ 无需补全，已退出")
        return

    if dry_run:
        print("  (dry-run，不执行拉取与解析)")
        return

    parser_llm = LLMParser()
    snapshot_time = datetime.now()
    pending_relations = []
    ok, err = 0, 0

    for idx, issue_number in enumerate(missing, 1):
        try:
            issue_data = collector.fetch_issue(repo_owner, repo_name, issue_number)
            if not issue_data:
                err += 1
                continue
            comments = collector.fetch_comments(repo_owner, repo_name, issue_number)

            title = (issue_data.get("title") or "") or ""
            body = (issue_data.get("body") or "") or ""
            comment_bodies = [(c.get("body") or "") for c in comments]

            print(f"\n[{idx}/{len(missing)}] 补全 Issue #{issue_number}: {title[:50]}...")
            print("  🤖 AI解析中...")

            classification = parser_llm.classify_issue(title, body)
            issue_type = classification.get("type", "task")
            priority = parser_llm.extract_priority(title, body, issue_type)
            tags = parser_llm.extract_tags(title, body)
            summary = parser_llm.generate_summary(title, body, comment_bodies)
            blocking_reason = parser_llm.analyze_blocking_reasons(issue_data, comments)

            issue_snapshot = {
                "issue_id": issue_data.get("id"),
                "issue_number": issue_data.get("number"),
                "repo_owner": repo_owner,
                "repo_name": repo_name,
                "title": title,
                "body": body,
                "state": issue_data.get("state", "open"),
                "issue_type": issue_type,
                "priority": priority,
                "assignee": issue_data.get("assignee", {}).get("login") if issue_data.get("assignee") else None,
                "labels": [lb.get("name") for lb in issue_data.get("labels", [])],
                "milestone": issue_data.get("milestone", {}).get("title") if issue_data.get("milestone") else None,
                "created_at": collector.parse_datetime(issue_data.get("created_at")),
                "updated_at": collector.parse_datetime(issue_data.get("updated_at")),
                "closed_at": collector.parse_datetime(issue_data.get("closed_at")),
                "ai_summary": summary,
                "ai_tags": tags,
                "ai_priority": priority,
                "status": "已关闭" if issue_data.get("state") == "closed" else ("处理中" if issue_data.get("assignee") else "待处理"),
                "progress_percentage": 100.0 if issue_data.get("state") == "closed" else 0.0,
                "is_blocked": blocking_reason is not None,
                "blocked_reason": blocking_reason,
                "snapshot_time": snapshot_time,
            }
            storage.save_issue_snapshot(issue_snapshot, snapshot_time)
            if comments:
                storage.save_comments(comments, issue_data.get("id"), issue_data.get("number"))
            pending_relations.append({
                "issue_id": issue_data.get("id"),
                "issue_number": issue_data.get("number"),
                "body": body,
                "comments": comments or [],
            })
            ok += 1
            print(f"  ✅ 类型: {issue_type}, 优先级: {priority}")
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            err += 1

    if pending_relations:
        print("\n🔗 补全关联关系...")
        all_relations = []
        for item in pending_relations:
            rels = collector.extract_relations(
                item["issue_id"], item["issue_number"], item["body"], item["comments"]
            )
            if rels:
                all_relations.extend(rels)
        if all_relations:
            storage.save_relations(all_relations, repo_owner=repo_owner, repo_name=repo_name)
            print(f"✅ 关联已保存: {len(all_relations)} 条")

    print("\n" + "=" * 60)
    print(f"补全完成: 成功 {ok}, 失败 {err}")
    print("=" * 60)


if __name__ == "__main__":
    main()
