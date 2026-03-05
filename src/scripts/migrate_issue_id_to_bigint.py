#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：将 issue_id 相关字段从 INT 改为 BIGINT

用于修复 GitHub Issue ID 超过 INT32 范围的问题
"""

import sys
import os
# 添加项目根目录到路径（支持从 scripts/ 运行）
_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_dir)
sys.path.insert(0, _root)

from config.config import DATABASE_TYPE, get_database_url
from sqlalchemy import create_engine, text

def migrate_issue_id_to_bigint():
    """将 issue_id 相关字段从 INT 改为 BIGINT"""
    
    print("=" * 60)
    print("数据库迁移：issue_id 字段类型升级")
    print("=" * 60)
    print(f"数据库类型: {DATABASE_TYPE}")
    print()
    
    if DATABASE_TYPE not in ["mysql", "matrixone"]:
        print("⚠️  此迁移脚本仅适用于 MySQL/MatrixOne 数据库")
        print(f"   当前数据库类型: {DATABASE_TYPE}")
        return False
    
    database_url = get_database_url()
    print(f"连接数据库...")
    
    try:
        engine = create_engine(database_url, echo=False)
        
        with engine.connect() as conn:
            # 开始事务
            trans = conn.begin()
            
            try:
                print("\n1. 修改 issues_snapshot 表...")
                conn.execute(text("""
                    ALTER TABLE issues_snapshot 
                    MODIFY COLUMN issue_id BIGINT NOT NULL
                """))
                print("   ✅ issue_id 字段已修改为 BIGINT")
                
                print("\n2. 修改 issue_relations 表...")
                conn.execute(text("""
                    ALTER TABLE issue_relations 
                    MODIFY COLUMN from_issue_id BIGINT NOT NULL
                """))
                print("   ✅ from_issue_id 字段已修改为 BIGINT")
                
                conn.execute(text("""
                    ALTER TABLE issue_relations 
                    MODIFY COLUMN to_issue_id BIGINT NOT NULL
                """))
                print("   ✅ to_issue_id 字段已修改为 BIGINT")
                
                print("\n3. 修改 comments 表...")
                # 检查表是否存在
                result = conn.execute(text("""
                    SELECT COUNT(*) as cnt 
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE() 
                    AND table_name = 'comments'
                """))
                table_exists = result.fetchone()[0] > 0
                
                if table_exists:
                    conn.execute(text("""
                        ALTER TABLE comments 
                        MODIFY COLUMN issue_id BIGINT NOT NULL
                    """))
                    print("   ✅ issue_id 字段已修改为 BIGINT")
                    
                    conn.execute(text("""
                        ALTER TABLE comments 
                        MODIFY COLUMN comment_id BIGINT NOT NULL
                    """))
                    print("   ✅ comment_id 字段已修改为 BIGINT")
                else:
                    print("   ⚠️  comments 表不存在，跳过")
                
                # 提交事务
                trans.commit()
                print("\n" + "=" * 60)
                print("✅ 迁移完成！所有字段已成功修改为 BIGINT")
                print("=" * 60)
                return True
                
            except Exception as e:
                trans.rollback()
                print(f"\n❌ 迁移失败: {e}")
                print("   已回滚所有更改")
                return False
                
    except Exception as e:
        print(f"\n❌ 数据库连接失败: {e}")
        return False

if __name__ == "__main__":
    success = migrate_issue_id_to_bigint()
    sys.exit(0 if success else 1)
