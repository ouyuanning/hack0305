#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查询数据库中 labels/tag 的存储样例
用于确认 GitHub Issue 上的 tag 是否完整保留
"""

import sys
import os
import json

# 添加项目根目录到路径（支持从 scripts/ 运行）
_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_dir)
sys.path.insert(0, _root)

from config.config import get_database_url, DATABASE_TYPE
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


def main():
    print("=" * 60)
    print("Labels/Tag 存储样例查询")
    print("=" * 60)
    
    try:
        engine = create_engine(
            get_database_url(),
            connect_args={"charset": "utf8mb4"} if DATABASE_TYPE == "matrixone" else {}
        )
        
        # 先获取最新快照时间
        sql_latest = """
        SELECT MAX(snapshot_time) as t FROM issues_snapshot
        WHERE repo_owner = 'matrixorigin' AND repo_name = 'matrixone'
        """
        with engine.connect() as conn:
            latest = conn.execute(text(sql_latest)).scalar()
        
        if not latest:
            print("\n⚠️ 未找到数据，请确认已执行过同步")
            return
        
        # 查询 Issue 样例（取最新快照）
        # 使用 CAST 将 JSON 转为文本，规避 MatrixOne 的 "invalid input: json text" 问题
        sql = text("""
        SELECT issue_number, title,
               CAST(labels AS CHAR) as labels,
               CAST(ai_tags AS CHAR) as ai_tags,
               issue_type, priority, state
        FROM issues_snapshot
        WHERE repo_owner = 'matrixorigin' AND repo_name = 'matrixone'
        AND snapshot_time = :latest
        AND labels IS NOT NULL
        ORDER BY issue_number DESC
        LIMIT 30
        """)
        
        with engine.connect() as conn:
            result = conn.execute(sql, {"latest": latest})
            rows = result.fetchall()
        
        if not rows:
            print("\n⚠️ 未找到数据，请确认已执行过同步")
            return
        
        # 过滤掉 labels 为空的（在 Python 中处理，避免 MatrixOne JSON 比较问题）
        rows_with_labels = []
        for row in rows:
            labels_val = row[2]
            if labels_val:
                try:
                    parsed = json.loads(labels_val) if isinstance(labels_val, str) else labels_val
                    if parsed and (isinstance(parsed, list) and len(parsed) > 0):
                        rows_with_labels.append(row)
                except:
                    rows_with_labels.append(row)
            if len(rows_with_labels) >= 15:
                break
        rows = rows_with_labels or rows[:15]
        
        print(f"\n共查询到 {len(rows)} 条有 labels 的样例（最新快照）\n")
        print("-" * 80)
        
        for row in rows:
            issue_number, title, labels, ai_tags, issue_type, priority, state = row
            title_short = (title or "")[:45] + "..." if len(title or "") > 45 else (title or "")
            
            # 解析 JSON（可能是字符串）
            if isinstance(labels, str):
                try:
                    labels = json.loads(labels) if labels else []
                except:
                    labels = [labels]
            labels = labels or []
            
            if isinstance(ai_tags, str):
                try:
                    ai_tags = json.loads(ai_tags) if ai_tags else []
                except:
                    ai_tags = [ai_tags]
            ai_tags = ai_tags or []
            
            print(f"Issue #{issue_number} | {state} | {issue_type} | {priority}")
            print(f"  标题: {title_short}")
            print(f"  📌 labels (GitHub tag): {labels}")
            print(f"  🤖 ai_tags (AI 提取):   {ai_tags}")
            print("-" * 80)
        
        # 统计所有不重复的 labels（CAST 规避 MatrixOne JSON 解析问题）
        sql_all_labels = text("""
        SELECT CAST(labels AS CHAR) as labels FROM issues_snapshot
        WHERE repo_owner = 'matrixorigin' AND repo_name = 'matrixone'
        AND snapshot_time = :latest
        AND labels IS NOT NULL
        """)
        with engine.connect() as conn:
            result = conn.execute(sql_all_labels, {"latest": latest})
            all_rows = result.fetchall()
        
        all_labels = set()
        for row in all_rows:
            labels = row[0]
            if isinstance(labels, str):
                try:
                    labels = json.loads(labels) if labels else []
                except:
                    continue
            if labels:
                all_labels.update(labels if isinstance(labels, list) else [labels])
        
        print(f"\n📊 当前快照中所有不重复的 labels (共 {len(all_labels)} 个):")
        print(sorted(all_labels))
        
    except SQLAlchemyError as e:
        print(f"\n❌ 数据库连接失败: {e}")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
