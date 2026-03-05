#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
临时脚本：针对「关系缺失」的 Issue 进行同步

用途：从运行反馈 docx 中提取「无法找到 Issue #xxx 的 ID」的编号，从 GitHub 拉取这些 Issue 的
      信息并入库；信息同步好后可再运行 supplement_relations 补全关联。用完可删除。

来源：Download/运行后关系缺失issue-260223.docx

使用：
    # 从默认 docx 路径提取缺失编号并同步（matrixorigin/matrixone）
    python3 sync_missing_issues.py

    # 指定 docx 路径
    python3 sync_missing_issues.py --input "/Users/wupeng/Downloads/运行后关系缺失issue-260223.docx"

    # 指定仓库
    python3 sync_missing_issues.py --repo-owner matrixorigin --repo-name matrixone

    # 只提取编号，不真正同步（预览）
    python3 sync_missing_issues.py --dry-run
"""

import sys
import os
import re
import argparse
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from config.config import validate_config
from modules.github_collector.github_api import GitHubCollector
from modules.llm_parser.llm_parser import LLMParser
from modules.database_storage.mo_client import MOStorage


DEFAULT_DOCX = "/Users/wupeng/Downloads/运行后关系缺失issue-260223.docx"


def extract_missing_issue_numbers_from_docx(docx_path: str) -> list:
    """
    从 docx 中提取「无法找到 Issue #xxx 的 ID」的编号
    返回去重后的 int 列表
    """
    with zipfile.ZipFile(docx_path, "r") as zf:
        with zf.open("word/document.xml") as f:
            tree = ET.parse(f)
    root = tree.getroot()
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

    def get_text(elem):
        parts = []
        if elem.text:
            parts.append(elem.text)
        for c in elem:
            parts.extend(get_text(c))
            if c.tail:
                parts.append(c.tail)
        return parts

    raw = "".join(get_text(root))
    nums = re.findall(r"无法找到 Issue #(\d+) 的 ID", raw)
    nums = list(dict.fromkeys(nums))
    nums = [int(n) for n in nums if int(n) > 0]
    nums.sort()
    return nums


def sync_single_issue(
    collector: GitHubCollector,
    parser: LLMParser,
    storage: MOStorage,
    repo_owner: str,
    repo_name: str,
    issue_number: int,
    snapshot_time: datetime,
) -> bool:
    """
    同步单个 Issue：拉取、AI 解析、入库
    返回 True 表示成功，False 表示跳过或失败
    """
    try:
        issue_data = collector.fetch_issue(repo_owner, repo_name, issue_number)
    except Exception as e:
        if "404" in str(e):
            print(f"  ⏭️  #{issue_number} 不存在（404），跳过")
        else:
            print(f"  ❌ #{issue_number} 拉取失败: {e}")
        return False

    if "pull_request" in issue_data:
        print(f"  ⏭️  #{issue_number} 是 PR，跳过")
        return False

    try:
        comments = collector.fetch_comments(repo_owner, repo_name, issue_number)
    except Exception as e:
        print(f"  ⚠️  #{issue_number} 评论拉取失败，使用空: {e}")
        comments = []

    title = issue_data.get("title", "")
    body = issue_data.get("body", "") or ""

    try:
        classification = parser.classify_issue(title, body)
        issue_type = classification.get("type", "task")
        priority = parser.extract_priority(title, body, issue_type)
        tags = parser.extract_tags(title, body)
        summary = parser.generate_summary(
            title, body, [c.get("body", "") for c in comments]
        )
        blocking_reason = parser.analyze_blocking_reasons(issue_data, comments)
    except Exception as e:
        print(f"  ⚠️  #{issue_number} AI 解析失败，使用默认: {e}")
        issue_type = "task"
        priority = "P3"
        tags = []
        summary = title[:200] if title else ""
        blocking_reason = None

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
        "assignee": (
            issue_data.get("assignee", {}).get("login")
            if issue_data.get("assignee")
            else None
        ),
        "labels": [lb.get("name") for lb in issue_data.get("labels", [])],
        "milestone": (
            issue_data.get("milestone", {}).get("title")
            if issue_data.get("milestone")
            else None
        ),
        "created_at": collector.parse_datetime(issue_data.get("created_at")),
        "updated_at": collector.parse_datetime(issue_data.get("updated_at")),
        "closed_at": collector.parse_datetime(issue_data.get("closed_at")),
        "ai_summary": summary,
        "ai_tags": tags,
        "ai_priority": priority,
        "status": (
            "已关闭"
            if issue_data.get("state") == "closed"
            else ("处理中" if issue_data.get("assignee") else "待处理")
        ),
        "progress_percentage": 100.0 if issue_data.get("state") == "closed" else 0.0,
        "is_blocked": blocking_reason is not None,
        "blocked_reason": blocking_reason,
        "snapshot_time": snapshot_time,
    }

    try:
        storage.save_issue_snapshot(issue_snapshot, snapshot_time)
    except Exception as e:
        if "1062" in str(e) or "Duplicate entry" in str(e):
            print(f"  ℹ️  已存在，跳过")
            return True  # 视为成功，已入库
        raise

    if comments:
        storage.save_comments(
            comments,
            issue_data.get("id"),
            issue_data.get("number"),
        )

    return True


def main():
    parser = argparse.ArgumentParser(
        description="针对关系缺失的 Issue 进行同步（临时脚本）"
    )
    parser.add_argument(
        "--input",
        type=str,
        nargs="+",
        default=None,
        help="运行反馈 docx 路径，可指定多个，如 --input a.docx b.docx",
    )
    parser.add_argument(
        "--repo-owner",
        type=str,
        default="matrixorigin",
        help="仓库所有者",
    )
    parser.add_argument(
        "--repo-name",
        type=str,
        default="matrixone",
        help="仓库名称",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅提取编号并打印，不实际同步",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="限制同步数量（0=不限制），可用于分批",
    )
    args = parser.parse_args()

    inputs = args.input or [
        "/Users/wupeng/Downloads/再次运行反馈-260223.docx",
        "/Users/wupeng/Downloads/再次运行反馈-260223-2.docx",
    ]
    inputs = [Path(p).expanduser() for p in inputs]
    for p in inputs:
        if not p.exists():
            print(f"❌ 文件不存在: {p}")
            return 1

    print("=" * 60)
    print("临时脚本：关系缺失 Issue 同步")
    print("=" * 60)

    print(f"\n📄 从 {len(inputs)} 个文件提取缺失编号...")
    all_numbers = set()
    for p in inputs:
        nums = extract_missing_issue_numbers_from_docx(str(p))
        all_numbers.update(nums)
        print(f"   {p.name}: {len(nums)} 个")
    numbers = sorted(all_numbers)
    # 过滤明显异常：0 和超大编号
    numbers = [n for n in numbers if 0 < n < 200000]
    print(f"   合并去重后: {len(numbers)} 个")

    if args.limit:
        numbers = numbers[: args.limit]
        print(f"   限制为前 {args.limit} 个")

    if args.dry_run:
        print("\n[--dry-run] 编号列表（前 50 个）:")
        for n in numbers[:50]:
            print(f"  #{n}")
        if len(numbers) > 50:
            print(f"  ... 等共 {len(numbers)} 个")
        return 0

    if not validate_config():
        print("\n❌ 配置验证失败")
        return 1

    collector = GitHubCollector()
    parser_obj = LLMParser()
    storage = MOStorage()

    # 使用「包含最多 Issue 的快照时间」，使新同步的 Issue 归入主快照，supplement_relations 才能看到完整数据
    sql_main = """
        SELECT snapshot_time
        FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo
        GROUP BY snapshot_time
        ORDER BY COUNT(*) DESC
        LIMIT 1
    """
    res = storage.execute(sql_main, {"owner": args.repo_owner, "repo": args.repo_name})
    if res and res[0].get("snapshot_time"):
        snapshot_time = res[0]["snapshot_time"]
        print(f"\n📅 使用主快照时间（Issue 最多的）: {snapshot_time}")
    else:
        snapshot_time = datetime.now()
        print(f"\n📅 无已有快照，使用当前时间: {snapshot_time}")

    print(f"\n📥 开始同步 {args.repo_owner}/{args.repo_name}...")
    ok = 0
    skip = 0

    for i, num in enumerate(numbers, 1):
        print(f"\n[{i}/{len(numbers)}] #{num} ...", end=" ")
        if sync_single_issue(
            collector, parser_obj, storage,
            args.repo_owner, args.repo_name,
            num, snapshot_time,
        ):
            print("✅")
            ok += 1
        else:
            skip += 1

    print("\n" + "=" * 60)
    print(f"✅ 成功: {ok}   ⏭️ 跳过: {skip}")
    print("=" * 60)
    print("\n建议：同步完成后运行关联补全：")
    print(
        f"  python3 supplement_relations.py --repo-owner {args.repo_owner} "
        f"--repo-name {args.repo_name}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
