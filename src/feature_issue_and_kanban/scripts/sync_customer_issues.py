#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将带指定客户标签的 Issue 从 issues_snapshot 同步到 customer_issues 表。
用法（在 src/ 目录执行）:
  python feature_issue_and_kanban/scripts/sync_customer_issues.py \
      --repo matrixorigin/matrixflow --customer-tag "customer/金盘"
"""
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.database_storage.mo_client import MOStorage

sys.path.insert(0, str(ROOT / "feature_issue_and_kanban"))
from project_manager.customer_sync import CustomerSync


def main():
    parser = argparse.ArgumentParser(description="同步客户 Issue 到 customer_issues")
    parser.add_argument("--repo", required=True, help="仓库 owner/name")
    parser.add_argument("--customer-tag", required=True, help="客户标签，如 customer/金盘")
    args = parser.parse_args()
    parts = args.repo.split("/")
    if len(parts) != 2:
        print("--repo 格式应为 owner/name")
        sys.exit(1)
    repo_owner, repo_name = parts[0], parts[1]
    storage = MOStorage()
    syncer = CustomerSync(storage)
    n = syncer.sync_customer_issues(repo_owner, repo_name, args.customer_tag)
    print(f"✓ 已同步 {n} 条 customer_issues")


if __name__ == "__main__":
    main()
