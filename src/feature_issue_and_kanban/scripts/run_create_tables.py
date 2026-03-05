#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行 create_new_tables.sql，在现有库中创建 project_issues / issue_knowledge_base / conversation_sessions。
需在项目根目录运行，或确保可导入 config 与 database_storage。
"""
import sys
from pathlib import Path

# 项目根目录（GitHub_Issue_智能管理系统）
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.config import get_database_url, DATABASE_TYPE
from sqlalchemy import create_engine, text

def main():
    sql_file = Path(__file__).parent / "create_new_tables.sql"
    sql_content = sql_file.read_text(encoding="utf-8")
    # 按分号拆分，去掉注释块和空语句
    statements = []
    for part in sql_content.split(";"):
        part = part.strip()
        if not part or part.startswith("--"):
            continue
        statements.append(part)
    engine = create_engine(get_database_url())
    with engine.connect() as conn:
        for stmt in statements:
            stmt = stmt.strip()
            if not stmt:
                continue
            try:
                conn.execute(text(stmt))
                conn.commit()
                print("✓", stmt[:60].replace("\n", " ") + "...")
            except Exception as e:
                if "already exists" in str(e).lower() or "Duplicate" in str(e):
                    print("⊙ 表已存在，跳过:", stmt[:50])
                    conn.rollback()
                else:
                    raise
    print("Done. 新表已创建或已存在。")

if __name__ == "__main__":
    main()
