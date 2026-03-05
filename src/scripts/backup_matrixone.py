#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MatrixOne 数据库定时备份脚本（SQL 快照，FOR ACCOUNT）

存储方式：只为当前账户创建快照，与官方推荐一致：
  CREATE SNAPSHOT snap_xxx FOR ACCOUNT;
恢复：RESTORE DATABASE github_issues FROM SNAPSHOT snap_xxx;
     或 RESTORE TABLE github_issues.issues_snapshot FROM SNAPSHOT snap_xxx;

用途：
- 作为单独定时事项创建快照；
- 同步前防误删：main 会在跑同步前自动打 snap_xxx_before_sync，便于出问题后恢复。

仅当 config 中 DATABASE_TYPE=matrixone 时有效。

使用示例：
  # 创建当前时刻的账户快照并列出所有快照（会按 BACKUP_SNAPSHOT_RETENTION_DAYS 清理过期快照）
  python3 scripts/backup_matrixone.py

  # 同步前打快照（名称带 _before_sync，便于识别）
  python3 scripts/backup_matrixone.py --before-sync

  # 仅列出已有快照，不创建
  python3 scripts/backup_matrixone.py --list-only

  # 仅打印将要执行的 SQL，不连接数据库
  python3 scripts/backup_matrixone.py --dry-run

定时建议（cron）：每日执行一次，例如每天 2:00
  0 2 * * * cd /path/to/GitHub_Issue_智能管理系统 && python3 scripts/backup_matrixone.py >> logs/backup_matrixone.log 2>&1
"""

import sys
import os
import argparse
from datetime import datetime

# 项目根目录
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from config.config import DATABASE_TYPE, BACKUP_SNAPSHOT_RETENTION_DAYS


def main():
    parser = argparse.ArgumentParser(description="MatrixOne 数据库快照备份（FOR ACCOUNT，定时事项）")
    parser.add_argument("--list-only", action="store_true", help="仅列出已有快照，不创建")
    parser.add_argument("--before-sync", action="store_true", help="同步前快照，名称带 _before_sync")
    parser.add_argument("--dry-run", action="store_true", help="仅打印 SQL，不执行")
    args = parser.parse_args()

    if DATABASE_TYPE != "matrixone":
        print("⚠️  当前 DATABASE_TYPE 不是 matrixone，本脚本仅用于 MatrixOne 快照备份，退出。")
        return 1

    suffix = "_before_sync" if args.before_sync else ""
    snapshot_name = f"snap_{datetime.now().strftime('%Y%m%d_%H%M')}{suffix}"

    if args.dry_run:
        print("-- 将执行的 SQL（dry-run）：")
        if not args.list_only:
            print(f"CREATE SNAPSHOT {snapshot_name} FOR ACCOUNT;")
        print("SHOW SNAPSHOTS;")
        if not args.list_only and BACKUP_SNAPSHOT_RETENTION_DAYS > 0:
            print(f"-- 保留最近 {BACKUP_SNAPSHOT_RETENTION_DAYS} 天快照，其余 DROP SNAPSHOT ...")
        return 0

    # 连接并执行
    from modules.database_storage.mo_client import MOStorage

    storage = MOStorage()

    if not args.list_only:
        create_sql = f"CREATE SNAPSHOT {snapshot_name} FOR ACCOUNT"
        try:
            storage.execute(create_sql)
            print(f"✅ 快照已创建: {snapshot_name} (FOR ACCOUNT)")
        except Exception as e:
            print(f"❌ 创建快照失败: {e}")
            print("   若为 Serverless 实例，请确认控制台是否支持 CREATE SNAPSHOT；参见 docs/matrixone/MatrixOne备份与恢复.md")
            return 1

        # 按配置保留天数清理过期快照
        if BACKUP_SNAPSHOT_RETENTION_DAYS > 0:
            n = storage.trim_old_mo_snapshots(BACKUP_SNAPSHOT_RETENTION_DAYS)
            if n > 0:
                print(f"✅ 已清理 {n} 个超过 {BACKUP_SNAPSHOT_RETENTION_DAYS} 天的快照")

    # 列出快照
    try:
        result = storage.execute("SHOW SNAPSHOTS")
        if result and isinstance(result, list) and len(result) > 0:
            print("\n当前快照列表：")
            for row in result:
                print("  ", row)
        elif result is not None and not isinstance(result, list):
            print("\nSHOW SNAPSHOTS 返回:", result)
        else:
            print("\n当前无快照或 SHOW SNAPSHOTS 返回为空。")
    except Exception as e:
        print(f"⚠️  列出快照失败: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
