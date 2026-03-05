#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将带指定项目标签的 Issue 从 issues_snapshot 同步到 project_issues 表。
用法（在项目根目录执行）:
  python feature_issue_and_kanban/scripts/sync_project_issues.py --repo matrixorigin/matrixflow --project-tag "project/问数深化"
"""
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.database_storage.mo_client import MOStorage

sys.path.insert(0, str(ROOT / "feature_issue_and_kanban"))
from project_manager.project_sync import ProjectSync


def main():
    parser = argparse.ArgumentParser(description="同步项目 Issue 到 project_issues")
    parser.add_argument("--repo", required=True, help="仓库 owner/name")
    parser.add_argument("--project-tag", required=True, help="项目标签，如 project/问数深化")
    args = parser.parse_args()
    parts = args.repo.split("/")
    if len(parts) != 2:
        print("--repo 格式应为 owner/name")
        sys.exit(1)
    repo_owner, repo_name = parts[0], parts[1]
    storage = MOStorage()
    syncer = ProjectSync(storage)
    n = syncer.sync_project_issues(repo_owner, repo_name, args.project_tag)
    print(f"✓ 已同步 {n} 条 project_issues")


if __name__ == "__main__":
    main()
