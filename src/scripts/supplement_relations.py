#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
关联关系补全脚本

用途：从已入库的 Issue 中重新提取关联关系并保存。
解决：旧流程因处理顺序导致的「无法找到 Issue #xxx 的 ID，跳过此关系」问题。

特点：
- 仅读写数据库，不调用 GitHub API、不调用 AI API，消耗极低
- 全量补充：扫描最新快照下所有 Issue 的 body 和 comments
- 可选：先清空现有关联再补充（--clear-first）

使用：
    # 全量补充（默认 matrixorigin/matrixone）
    python3 supplement_relations.py

    # 指定仓库
    python3 supplement_relations.py --repo-owner matrixorigin --repo-name matrixone

    # 先清空再补充（干净重跑）
    python3 supplement_relations.py --clear-first
"""

import sys
import os
import argparse
from datetime import datetime

# 添加项目根目录到路径（支持从 scripts/ 运行）
_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_dir)
sys.path.insert(0, _root)

from config.config import validate_config
from modules.github_collector.github_api import GitHubCollector
from modules.database_storage.mo_client import MOStorage


def get_issues_with_comments(storage, repo_owner: str, repo_name: str):
    """从数据库获取主快照（Issue 最多的快照）下的所有 Issue 及其评论"""
    sql_main = """
        SELECT snapshot_time as latest_time
        FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo
        GROUP BY snapshot_time
        ORDER BY COUNT(*) DESC
        LIMIT 1
    """
    result = storage.execute(sql_main, {"owner": repo_owner, "repo": repo_name})
    if not result or not result[0].get("latest_time"):
        return None, None

    latest_time = result[0]["latest_time"]

    # 获取所有 Issue
    sql_issues = """
        SELECT issue_id, issue_number, body
        FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo
        AND snapshot_time = :latest_time
    """
    issues = storage.execute(sql_issues, {
        "owner": repo_owner, "repo": repo_name, "latest_time": latest_time
    })

    if not issues:
        return [], latest_time

    # 获取该快照下的所有 issue_id
    issue_ids = [row["issue_id"] for row in issues]

    # 获取评论（分批查询，避免 IN 子句过长）
    comments_rows = []
    batch_size = 500
    for i in range(0, len(issue_ids), batch_size):
        batch_ids = issue_ids[i:i + batch_size]
        placeholders = ",".join([f":id{j}" for j in range(len(batch_ids))])
        sql_comments = f"""
            SELECT issue_id, body, created_at
            FROM comments
            WHERE issue_id IN ({placeholders})
        """
        params = {f"id{j}": bid for j, bid in enumerate(batch_ids)}
        batch_result = storage.execute(sql_comments, params)
        comments_rows.extend(batch_result or [])

    # 按 issue_id 分组评论
    comments_by_issue = {}
    for row in (comments_rows or []):
        issue_id = row.get("issue_id")
        if issue_id not in comments_by_issue:
            comments_by_issue[issue_id] = []
        comments_by_issue[issue_id].append({
            "body": row.get("body", ""),
            "created_at": row.get("created_at")
        })

    # 组装 (issue, comments) 列表
    issues_with_comments = []
    for issue in issues:
        issue_id = issue.get("issue_id")
        comments = comments_by_issue.get(issue_id, [])
        issues_with_comments.append((issue, comments))

    return issues_with_comments, latest_time


def run_supplement(
    repo_owner: str,
    repo_name: str,
    clear_first: bool = False,
    quiet: bool = False
) -> bool:
    """
    执行关联关系补全（可被 auto_run 等模块调用）
    
    参数:
    - repo_owner: 仓库所有者
    - repo_name: 仓库名称
    - clear_first: 是否先清空现有关联
    - quiet: 是否减少输出（被 auto_run 调用时可设为 True）
    
    返回:
    - bool: 是否成功
    """
    def log(msg: str):
        if not quiet:
            print(msg)

    try:
        storage = MOStorage()
        collector = GitHubCollector()

        if clear_first:
            log("\n⚠️  清空现有关联关系...")
            storage.execute("DELETE FROM issue_relations")
            log("✅ 已清空")

        issues_with_comments, latest_time = get_issues_with_comments(
            storage, repo_owner, repo_name
        )

        if not issues_with_comments:
            log("⚠️  未找到数据，请确认已执行过同步")
            return True

        log(f"📥 加载 {len(issues_with_comments)} 个 Issue，提取关联关系...")
        all_relations = []
        for idx, (issue, comments) in enumerate(issues_with_comments, 1):
            issue_id = issue.get("issue_id")
            issue_number = issue.get("issue_number")
            body = issue.get("body") or ""
            relations = collector.extract_relations(issue_id, issue_number, body, comments)
            if relations:
                all_relations.extend(relations)
            if not quiet and (idx % 1000 == 0 or idx == len(issues_with_comments)):
                print(f"  已扫描 {idx}/{len(issues_with_comments)} 个 Issue，发现 {len(all_relations)} 条关联")

        if not all_relations:
            log("✅ 未发现关联关系")
            return True

        storage.save_relations(all_relations, repo_owner=repo_owner, repo_name=repo_name)
        log(f"✅ 关联关系补全完成：共 {len(all_relations)} 条")
        return True

    except Exception as e:
        print(f"❌ 关联关系补全失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="关联关系补全脚本 - 从已入库数据重新提取并保存 Issue 关联关系",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 全量补充（默认 matrixorigin/matrixone）
  python3 supplement_relations.py

  # 指定仓库
  python3 supplement_relations.py --repo-owner matrixorigin --repo-name matrixflow

  # 先清空现有关联再补充
  python3 supplement_relations.py --clear-first
        """
    )
    parser.add_argument("--repo-owner", default="matrixorigin", help="仓库所有者")
    parser.add_argument("--repo-name", default="matrixone", help="仓库名称")
    parser.add_argument("--clear-first", action="store_true", help="先清空 issue_relations 再补充")

    args = parser.parse_args()

    print("=" * 60)
    print("关联关系补全脚本")
    print("=" * 60)

    if not validate_config():
        print("\n❌ 配置验证失败，请检查配置文件")
        return 1

    success = run_supplement(
        repo_owner=args.repo_owner,
        repo_name=args.repo_name,
        clear_first=args.clear_first,
        quiet=False
    )

    print("\n" + "=" * 60)
    print("✅ 关联关系补全完成" if success else "❌ 执行失败")
    print("=" * 60)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
