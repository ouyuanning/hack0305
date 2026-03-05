#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库存储模块
功能：将Issue数据存储到数据库，支持多种数据库类型
修复了Issue Number到Issue ID的转换问题
"""

import sys
import os
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, BigInteger, String, Text, DateTime, Boolean, Float, JSON, UniqueConstraint
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))
from config.config import (
    get_database_url, DATABASE_TYPE, DB_POOL_SIZE, DB_MAX_OVERFLOW, DB_POOL_PRE_PING,
    ENABLE_FULL_RESYNC, BACKUP_SNAPSHOT_RETENTION_DAYS
)


class MOStorage:
    """数据库存储类，支持多种数据库类型"""
    
    def __init__(self):
        self.database_url = get_database_url()
        
        # 为 MatrixOne 配置连接参数
        connect_args = {}
        if DATABASE_TYPE == "matrixone":
            # MatrixOne 使用 MySQL 协议，需要设置连接参数
            connect_args = {
                "connect_timeout": 10,  # 连接超时时间（秒）
                "charset": "utf8mb4",  # 字符集
                "read_timeout": 30,  # 读取超时时间（秒）
                "write_timeout": 30,  # 写入超时时间（秒）
            }
        
        self.engine = create_engine(
            self.database_url,
            pool_pre_ping=DB_POOL_PRE_PING,
            pool_size=DB_POOL_SIZE,
            max_overflow=DB_MAX_OVERFLOW,
            echo=False,
            connect_args=connect_args if connect_args else {}
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.metadata = MetaData()
        self._init_tables()
        self._create_tables()
    
    def _init_tables(self):
        """初始化表结构"""
        # Issues快照表
        self.issues_snapshot = Table(
            'issues_snapshot',
            self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('issue_id', BigInteger, nullable=False, index=True),  # GitHub Issue ID (使用BIGINT支持大ID)
            Column('issue_number', Integer, nullable=False, index=True),  # Issue编号
            Column('repo_owner', String(100), nullable=False),
            Column('repo_name', String(100), nullable=False),
            Column('title', String(500), nullable=False),
            Column('body', Text),
            Column('state', String(20), nullable=False),  # open, closed
            Column('issue_type', String(50)),  # bug, feature, task
            Column('priority', String(10)),  # P0, P1, P2, P3
            Column('assignee', String(100)),
            Column('labels', JSON),
            Column('milestone', String(100)),
            Column('created_at', DateTime),
            Column('updated_at', DateTime),
            Column('closed_at', DateTime),
            Column('ai_summary', Text),
            Column('ai_tags', JSON),
            Column('ai_priority', String(10)),
            Column('status', String(50)),  # 待处理, 处理中, 待评审, 已完成, 已关闭
            Column('progress_percentage', Float, default=0.0),
            Column('is_blocked', Boolean, default=False),
            Column('blocked_reason', Text),
            Column('snapshot_time', DateTime, nullable=False, index=True),  # 快照时间
            Column('created_at_db', DateTime, server_default=text('CURRENT_TIMESTAMP')),
            # 添加唯一约束，用于 ON CONFLICT
            UniqueConstraint('issue_id', 'snapshot_time', name='uq_issue_snapshot')
        )
        
        # Issue关联关系表
        self.issue_relations = Table(
            'issue_relations',
            self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('from_issue_id', BigInteger, nullable=False, index=True),  # 源Issue的GitHub ID (使用BIGINT支持大ID)
            Column('to_issue_id', BigInteger, nullable=False, index=True),  # 目标Issue的GitHub ID (使用BIGINT支持大ID)
            Column('relation_type', String(50), nullable=False),  # mention, reference, duplicate, related, fixes, blocks, depends_on
            Column('relation_semantic', String(100)),  # 关系语义描述
            Column('created_at', DateTime),
            Column('source', String(50)),  # body, comment
            Column('context_text', Text),
            Column('created_at_db', DateTime, server_default=text('CURRENT_TIMESTAMP')),
            # 添加唯一约束，用于 ON CONFLICT
            UniqueConstraint('from_issue_id', 'to_issue_id', 'relation_type', name='uq_issue_relations')
        )
        
        # 评论表
        self.comments = Table(
            'comments',
            self.metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('comment_id', BigInteger, nullable=False, unique=True, index=True),  # GitHub Comment ID (使用BIGINT支持大ID)
            Column('issue_id', BigInteger, nullable=False, index=True),  # Issue的GitHub ID (使用BIGINT支持大ID)
            Column('issue_number', Integer, nullable=False, index=True),  # Issue编号
            Column('author', String(100), nullable=False),
            Column('body', Text, nullable=False),
            Column('created_at', DateTime),
            Column('created_at_db', DateTime, server_default=text('CURRENT_TIMESTAMP'))
        )
    
    def _create_tables(self):
        """创建数据库表"""
        try:
            self.metadata.create_all(self.engine)
            print("✅ 数据库表创建/检查完成")
        except Exception as e:
            print(f"⚠️  创建表时出错: {e}")
            # 如果表已存在，继续执行
    
    def get_session(self):
        """获取数据库会话"""
        return self.SessionLocal()
    
    def execute(self, sql: str, params: Optional[Dict] = None) -> any:
        """
        执行SQL语句
        
        输入参数：
        - sql: SQL语句
        - params: 参数字典
        
        输出：
        - SELECT查询：返回字典列表
        - INSERT/UPDATE/DELETE：返回影响的行数
        """
        with self.engine.connect() as conn:
            try:
                result = conn.execute(text(sql), params or {})
                conn.commit()
                
                if sql.strip().upper().startswith('SELECT') or sql.strip().upper().startswith('SHOW'):
                    rows = result.fetchall()
                    # 统一转换为字典列表
                    return [dict(row._mapping) for row in rows]
                elif sql.strip().upper().startswith('INSERT'):
                    return result.lastrowid
                else:
                    return result.rowcount
            except SQLAlchemyError as e:
                conn.rollback()
                raise Exception(f"SQL执行错误: {e}")
    
    def save_issue_snapshot(self, issue_data: Dict, snapshot_time: datetime):
        """
        保存Issue快照
        
        输入参数：
        - issue_data: Issue数据字典，必须包含：
          - issue_id: GitHub Issue ID
          - issue_number: Issue编号
          - repo_owner: 仓库所有者
          - repo_name: 仓库名称
          - title, body, state等字段
        - snapshot_time: 快照时间
        """
        sql = """
        INSERT INTO issues_snapshot (
            issue_id, issue_number, repo_owner, repo_name, title, body,
            state, issue_type, priority, assignee, labels, milestone,
            created_at, updated_at, closed_at,
            ai_summary, ai_tags, ai_priority,
            status, progress_percentage, is_blocked, blocked_reason,
            snapshot_time
        ) VALUES (
            :issue_id, :issue_number, :repo_owner, :repo_name, :title, :body,
            :state, :issue_type, :priority, :assignee, :labels, :milestone,
            :created_at, :updated_at, :closed_at,
            :ai_summary, :ai_tags, :ai_priority,
            :status, :progress_percentage, :is_blocked, :blocked_reason,
            :snapshot_time
        )
        """
        
        # 将 snapshot_time 添加到参数字典中
        params = issue_data.copy()
        params['snapshot_time'] = snapshot_time
        
        # SQLite 和 MatrixOne 需要将 JSON 字段序列化为字符串
        # MatrixOne 对 JSON 类型的处理与标准 MySQL 不同，需要手动序列化
        if DATABASE_TYPE in ["sqlite", "matrixone"]:
            if 'labels' in params and params['labels'] is not None:
                if isinstance(params['labels'], (list, dict)):
                    params['labels'] = json.dumps(params['labels'], ensure_ascii=False)
            if 'ai_tags' in params and params['ai_tags'] is not None:
                if isinstance(params['ai_tags'], (list, dict)):
                    params['ai_tags'] = json.dumps(params['ai_tags'], ensure_ascii=False)
        
        # 处理ON DUPLICATE KEY UPDATE（MySQL/MatrixOne）
        if DATABASE_TYPE in ["mysql", "matrixone"]:
            # MatrixOne 不支持更新唯一键，所以不更新 snapshot_time
            # 如果记录已存在（相同的 issue_id 和 snapshot_time），只更新其他字段
            sql += """
            ON DUPLICATE KEY UPDATE
                title = VALUES(title),
                body = VALUES(body),
                state = VALUES(state),
                issue_type = VALUES(issue_type),
                priority = VALUES(priority),
                assignee = VALUES(assignee),
                labels = VALUES(labels),
                milestone = VALUES(milestone),
                updated_at = VALUES(updated_at),
                closed_at = VALUES(closed_at),
                ai_summary = VALUES(ai_summary),
                ai_tags = VALUES(ai_tags),
                ai_priority = VALUES(ai_priority),
                status = VALUES(status),
                progress_percentage = VALUES(progress_percentage),
                is_blocked = VALUES(is_blocked),
                blocked_reason = VALUES(blocked_reason)
            """
        else:
            # PostgreSQL/SQLite 使用 ON CONFLICT
            sql = sql.replace("INSERT INTO", "INSERT INTO") + """
            ON CONFLICT (issue_id, snapshot_time) DO UPDATE SET
                title = EXCLUDED.title,
                body = EXCLUDED.body,
                state = EXCLUDED.state,
                issue_type = EXCLUDED.issue_type,
                priority = EXCLUDED.priority,
                assignee = EXCLUDED.assignee,
                labels = EXCLUDED.labels,
                milestone = EXCLUDED.milestone,
                updated_at = EXCLUDED.updated_at,
                closed_at = EXCLUDED.closed_at,
                ai_summary = EXCLUDED.ai_summary,
                ai_tags = EXCLUDED.ai_tags,
                ai_priority = EXCLUDED.ai_priority,
                status = EXCLUDED.status,
                progress_percentage = EXCLUDED.progress_percentage,
                is_blocked = EXCLUDED.is_blocked,
                blocked_reason = EXCLUDED.blocked_reason,
                snapshot_time = EXCLUDED.snapshot_time
            """
        
        try:
            self.execute(sql, params)
        except IntegrityError as e:
            # MatrixOne 在 ON DUPLICATE KEY UPDATE 时有时仍抛出 1062，视为已存在
            err_code = getattr(e.orig, 'args', [None])[0] if getattr(e, 'orig', None) else None
            if err_code == 1062 or 'Duplicate entry' in str(e):
                pass  # 已存在，视为成功
            else:
                print(f"⚠️  保存Issue快照失败: {e}")
                raise
        except Exception as e:
            print(f"⚠️  保存Issue快照失败: {e}")
            raise
    
    def save_relations(self, relations: List[Dict], repo_owner: Optional[str] = None, repo_name: Optional[str] = None):
        """
        保存Issue关联关系
        修复了Issue Number到Issue ID的转换问题
        
        输入参数：
        - relations: 关联关系列表
        - repo_owner, repo_name: 可选，指定时使用该仓库的最新快照做 number->id 查找
        """
        if not relations:
            return
        
        # 收集所有需要转换的 issue_number
        issue_numbers_to_convert = set()
        for rel in relations:
            if 'to_issue_number' in rel and 'to_issue_id' not in rel:
                issue_numbers_to_convert.add(rel['to_issue_number'])
        
        # 批量查询 number -> id 映射
        number_to_id = {}
        if issue_numbers_to_convert:
            # 获取快照时间（指定 repo 时用该 repo 的最新，否则用全局最新）
            if repo_owner and repo_name:
                sql_latest = """
                    SELECT MAX(snapshot_time) as latest_time FROM issues_snapshot
                    WHERE repo_owner = :owner AND repo_name = :repo
                """
                latest_result = self.execute(sql_latest, {"owner": repo_owner, "repo": repo_name})
            else:
                sql_latest = "SELECT MAX(snapshot_time) as latest_time FROM issues_snapshot"
                latest_result = self.execute(sql_latest)

            if latest_result and latest_result[0].get('latest_time'):
                latest_time = latest_result[0]['latest_time']

                # 构建查询（指定 repo 时只查该 repo 的快照）
                placeholders = ','.join([f':num{i}' for i in range(len(issue_numbers_to_convert))])
                sql_map = f"""
                    SELECT issue_id, issue_number
                    FROM issues_snapshot
                    WHERE issue_number IN ({placeholders})
                    AND snapshot_time = :latest_time
                """
                params = {f'num{i}': num for i, num in enumerate(issue_numbers_to_convert)}
                params['latest_time'] = latest_time
                if repo_owner and repo_name:
                    sql_map += " AND repo_owner = :owner AND repo_name = :repo"
                    params['owner'] = repo_owner
                    params['repo'] = repo_name

                rows = self.execute(sql_map, params)
                number_to_id = {row['issue_number']: row['issue_id'] for row in rows}
        
        # 转换并保存（修复：先查后插/更新，避免 MatrixOne ON DUPLICATE KEY UPDATE 行为不一致导致 1062）
        check_sql = """
        SELECT id FROM issue_relations
        WHERE from_issue_id = :from_id AND to_issue_id = :to_id AND relation_type = :rel_type
        LIMIT 1
        """
        update_sql = """
        UPDATE issue_relations
        SET relation_semantic = :relation_semantic, context_text = :context_text
        WHERE from_issue_id = :from_issue_id AND to_issue_id = :to_issue_id AND relation_type = :relation_type
        """
        insert_sql = """
        INSERT INTO issue_relations (
            from_issue_id, to_issue_id, relation_type, relation_semantic,
            created_at, source, context_text
        ) VALUES (
            :from_issue_id, :to_issue_id, :relation_type, :relation_semantic,
            :created_at, :source, :context_text
        )
        """
        saved_count = 0
        duplicate_count = 0
        error_count = 0
        for rel in relations:
            try:
                # 转换 to_issue_number 到 to_issue_id
                if 'to_issue_id' not in rel:
                    if 'to_issue_number' in rel:
                        issue_number = rel['to_issue_number']
                        if issue_number in number_to_id:
                            rel['to_issue_id'] = number_to_id[issue_number]
                        else:
                            print(f"⚠️  无法找到 Issue #{issue_number} 的 ID，跳过此关系")
                            continue
                    else:
                        print(f"⚠️  关系数据缺少 to_issue_id 或 to_issue_number，跳过")
                        continue
                from_id = rel['from_issue_id']
                to_id = rel['to_issue_id']
                rel_type = rel['relation_type']
                existing = self.execute(check_sql, {
                    'from_id': from_id, 'to_id': to_id, 'rel_type': rel_type
                })
                if existing:
                    self.execute(update_sql, {
                        'from_issue_id': from_id, 'to_issue_id': to_id, 'relation_type': rel_type,
                        'relation_semantic': rel.get('relation_semantic'),
                        'context_text': rel.get('context_text')
                    })
                    duplicate_count += 1
                else:
                    self.execute(insert_sql, {
                        'from_issue_id': from_id, 'to_issue_id': to_id, 'relation_type': rel_type,
                        'relation_semantic': rel.get('relation_semantic'),
                        'created_at': rel.get('created_at', datetime.now()),
                        'source': rel.get('source', 'unknown'),
                        'context_text': rel.get('context_text')
                    })
                    saved_count += 1
            except Exception as e:
                error_str = str(e)
                if '1062' in error_str or 'Duplicate entry' in error_str:
                    duplicate_count += 1
                else:
                    print(f"⚠️  保存关联关系失败: {e}")
                    error_count += 1
        
        if saved_count > 0:
            print(f"✅ 保存了 {saved_count} 条关联关系")
        if duplicate_count > 0:
            print(f"ℹ️  跳过/更新 {duplicate_count} 条已存在的重复关系")
        if error_count > 0:
            print(f"⚠️  {error_count} 条保存失败")
    
    def save_comments(self, comments: List[Dict], issue_id: int, issue_number: int):
        """
        保存评论
        
        输入参数：
        - comments: 评论列表
        - issue_id: Issue的GitHub ID
        - issue_number: Issue编号
        """
        if not comments:
            return
        
        sql = """
        INSERT INTO comments (
            comment_id, issue_id, issue_number, author, body, created_at
        ) VALUES (
            :comment_id, :issue_id, :issue_number, :author, :body, :created_at
        )
        """
        
        # 处理ON DUPLICATE KEY UPDATE
        if DATABASE_TYPE in ["mysql", "matrixone"]:
            sql += """
            ON DUPLICATE KEY UPDATE
                body = VALUES(body)
            """
        else:
            # PostgreSQL
            sql += """
            ON CONFLICT (comment_id) DO UPDATE SET
                body = EXCLUDED.body
            """
        
        saved_count = 0
        for comment in comments:
            try:
                comment_data = {
                    'comment_id': comment.get('id'),
                    'issue_id': issue_id,
                    'issue_number': issue_number,
                    'author': comment.get('user', {}).get('login', 'unknown'),
                    'body': comment.get('body', ''),
                    'created_at': self._parse_datetime(comment.get('created_at'))
                }
                self.execute(sql, comment_data)
                saved_count += 1
            except Exception as e:
                print(f"⚠️  保存评论失败: {e}")
                continue
        
        if saved_count > 0:
            print(f"✅ 保存了 {saved_count} 条评论")
    
    def get_latest_snapshot_time(self) -> Optional[datetime]:
        """获取最新快照时间（用于增量同步）"""
        sql = "SELECT MAX(snapshot_time) as latest_time FROM issues_snapshot"
        result = self.execute(sql)
        if result and result[0].get('latest_time'):
            return result[0]['latest_time']
        return None

    def create_mo_snapshot(self, suffix: str = "") -> Optional[str]:
        """
        为当前账户创建 MatrixOne 快照（仅当 DATABASE_TYPE=matrixone 时有效）。
        用于同步前防误删：每次跑同步前先打快照，出问题可 RESTORE DATABASE github_issues FROM SNAPSHOT xxx。
        参数 suffix: 快照名后缀，如 "_before_sync"。
        返回快照名，失败返回 None。
        """
        if DATABASE_TYPE != "matrixone":
            return None
        name = f"snap_{datetime.now().strftime('%Y%m%d_%H%M')}{suffix}"
        try:
            self.execute(f"CREATE SNAPSHOT {name} FOR ACCOUNT")
            return name
        except Exception as e:
            print(f"⚠️  创建快照失败: {e}")
            return None

    def trim_old_mo_snapshots(self, retention_days: int) -> int:
        """
        删除超过 retention_days 天的 MatrixOne 快照（通过 SHOW SNAPSHOTS 获取列表并 DROP）。
        仅当 DATABASE_TYPE=matrixone 时有效。返回删除的快照数量。
        """
        if DATABASE_TYPE != "matrixone" or retention_days <= 0:
            return 0
        try:
            rows = self.execute("SHOW SNAPSHOTS")
            if not rows or not isinstance(rows, list):
                return 0
            cutoff = datetime.now() - timedelta(days=retention_days)
            dropped = 0
            for row in rows:
                name = (row.get("SNAPSHOT_NAME") or row.get("snapshot_name") or "").strip()
                ts = row.get("TIMESTAMP") or row.get("timestamp")
                if not name:
                    continue
                if ts is None:
                    continue
                if isinstance(ts, str):
                    try:
                        # MatrixOne 可能返回微秒位数较多，fromisoformat 只接受最多 6 位
                        s = ts.replace("Z", "+00:00").strip()
                        if "." in s and len(s.split(".")[-1]) > 6:
                            s = s[: s.index(".") + 7]
                        ts = datetime.fromisoformat(s)
                    except Exception:
                        continue
                if ts < cutoff:
                    try:
                        self.execute(f"DROP SNAPSHOT {name}")
                        dropped += 1
                        print(f"  已删除过期快照: {name}")
                    except Exception as e:
                        print(f"  ⚠️  删除快照 {name} 失败: {e}")
            return dropped
        except Exception as e:
            print(f"⚠️  清理旧快照失败: {e}")
            return 0

    def trim_old_snapshots_for_repo(
        self, repo_owner: str, repo_name: str, keep_snapshot_time: datetime
    ) -> int:
        """
        删除指定仓库中早于 keep_snapshot_time 的快照行（仅 issues_snapshot），
        用于全量同步不清空时只保留本次快照，避免历史快照堆积。
        不删 comments / issue_relations（仍被保留的快照引用）。
        返回删除的行数。
        """
        try:
            n = self.execute(
                """DELETE FROM issues_snapshot
                   WHERE repo_owner = :ro AND repo_name = :rn AND snapshot_time < :t""",
                {"ro": repo_owner, "rn": repo_name, "t": keep_snapshot_time}
            )
            n = int(n) if n is not None else 0
            if n > 0:
                print(f"✅ 已清理该仓库早于 {keep_snapshot_time} 的旧快照，删除 {n} 行")
            return n
        except Exception as e:
            print(f"⚠️  清理旧快照失败: {e}")
            return 0

    def clear_all_data(self, force: bool = False, repo_owner: Optional[str] = None, repo_name: Optional[str] = None):
        """清空数据（用于全量重新运行）
        - force: 为True时跳过配置检查（如命令行传入--full-sync时）
        - repo_owner, repo_name: 若同时传入，则只清空该仓库数据，不影响其他仓库；不传则清空整库（兼容旧行为）
        """
        if not force and not ENABLE_FULL_RESYNC:
            print("⚠️  全量重新运行未启用，请在config/config.py中设置ENABLE_FULL_RESYNC=true")
            return False

        only_repo = repo_owner and repo_name
        if only_repo:
            print(f"⚠️  正在清空仓库 {repo_owner}/{repo_name} 的数据（不影响其他仓库）...")
        else:
            print("⚠️  正在清空所有数据...")
        try:
            if only_repo:
                # 只删当前仓库：先删评论、关联（依赖 issue_id），再删快照
                self.execute(
                    "DELETE FROM comments WHERE issue_id IN (SELECT issue_id FROM issues_snapshot WHERE repo_owner = :ro AND repo_name = :rn)",
                    {"ro": repo_owner, "rn": repo_name}
                )
                self.execute(
                    """DELETE FROM issue_relations WHERE from_issue_id IN (SELECT issue_id FROM issues_snapshot WHERE repo_owner = :ro AND repo_name = :rn)
                       OR to_issue_id IN (SELECT issue_id FROM issues_snapshot WHERE repo_owner = :ro AND repo_name = :rn)""",
                    {"ro": repo_owner, "rn": repo_name}
                )
                self.execute(
                    "DELETE FROM issues_snapshot WHERE repo_owner = :ro AND repo_name = :rn",
                    {"ro": repo_owner, "rn": repo_name}
                )
            else:
                self.execute("DELETE FROM issue_relations")
                self.execute("DELETE FROM comments")
                self.execute("DELETE FROM issues_snapshot")
            print("✅ 数据已清空")
            return True
        except Exception as e:
            print(f"❌ 清空数据失败: {e}")
            return False
    
    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """解析时间字符串"""
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except:
            return None


if __name__ == "__main__":
    # 测试代码
    storage = MOStorage()
    
    print("测试：数据库连接...")
    try:
        result = storage.execute("SELECT 1 as test")
        print(f"✅ 数据库连接成功: {result}")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
