#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Issue 智能管理系统 - 主程序
功能：协调各个模块，完成Issue采集、解析、存储、报告生成的全流程
"""

import sys
import os
from datetime import datetime
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from config.config import validate_config, ENABLE_FULL_RESYNC, FULL_SYNC_SKIP_CLEAR, DATABASE_TYPE
from modules.github_collector.github_api import GitHubCollector
from modules.llm_parser.llm_parser import LLMParser
from modules.database_storage.mo_client import MOStorage
from modules.report_generator.report_gen import Analyzer


class IssueManagerScheduler:
    """Issue管理调度器"""
    
    def __init__(self):
        self.collector = GitHubCollector()
        self.parser = LLMParser()
        self.storage = MOStorage()
        self.analyzer = Analyzer(self.storage)
    
    def sync_repo(
        self,
        repo_owner: str,
        repo_name: str,
        full_sync: bool = False
    ):
        """
        同步仓库的所有Issues
        
        输入参数：
        - repo_owner: 仓库所有者（例如：octocat）
        - repo_name: 仓库名称（例如：Hello-World）
        - full_sync: 是否全量同步（清空旧数据重新采集）
        
        输出：
        - Dict: 同步结果统计
        """
        print("=" * 60)
        print(f"开始同步仓库: {repo_owner}/{repo_name}")
        print("=" * 60)
        
        # 防误删：同步前先为当前账户打快照（仅 MatrixOne），便于出问题后 RESTORE DATABASE/TABLE FROM SNAPSHOT
        if DATABASE_TYPE == "matrixone":
            snap_name = self.storage.create_mo_snapshot("_before_sync")
            if snap_name:
                print(f"💾 已创建同步前快照: {snap_name}（若同步出问题可 RESTORE DATABASE github_issues FROM SNAPSHOT {snap_name};）")
            else:
                print("⚠️  同步前快照创建失败或未启用，继续同步")
        
        # 全量同步：可选先清空，或跳过清空、全量拉取后比对写入（由 FULL_SYNC_SKIP_CLEAR 控制）
        if full_sync or ENABLE_FULL_RESYNC:
            if FULL_SYNC_SKIP_CLEAR:
                print("📋 全量同步（不清空）：将拉取全部 Issue 并写入/更新，完成后仅保留本次快照")
            else:
                print("⚠️  执行全量同步，将清空本仓库旧数据...")
                self.storage.clear_all_data(force=full_sync, repo_owner=repo_owner, repo_name=repo_name)
        
        # 获取增量同步的起始时间（全量时 since=None；增量时用最新快照时间）
        since = None
        if not full_sync and not ENABLE_FULL_RESYNC:
            latest_time = self.storage.get_latest_snapshot_time()
            if latest_time:
                since = latest_time
                print(f"📅 增量同步：从 {since} 开始")
        
        # 获取所有Issues
        print("📥 正在获取Issues...")
        all_issues = []
        page = 1
        
        while True:
            issues, raw_count = self.collector.fetch_issues(
                repo_owner, repo_name,
                state="all",
                since=since,
                page=page,
                per_page=100
            )
            
            if not issues and raw_count == 0:
                break
            
            all_issues.extend(issues)
            print(f"  已获取 {len(all_issues)} 个Issues...")
            
            # 按原始API返回条数判断：若 < 100 说明已是最后一页
            # （不能用过滤后的数量，因为API混合返回Issue和PR，过滤后可能只有几十条）
            if raw_count < 100:
                break
            
            page += 1
        
        print(f"✅ 共获取 {len(all_issues)} 个Issues")
        
        # 处理每个Issue（Phase 1: 采集、AI解析、存储）
        # 关联关系延后到 Phase 2 处理，避免因先后顺序导致"无法找到 Issue ID"
        stats = {
            "total": len(all_issues),
            "processed": 0,
            "errors": 0
        }
        
        # 用于 Phase 2 关联关系提取：[(issue_id, issue_number, body, comments), ...]
        pending_relations = []
        
        snapshot_time = datetime.now()
        
        for idx, issue_data in enumerate(all_issues, 1):
            try:
                print(f"\n[{idx}/{len(all_issues)}] 处理 Issue #{issue_data.get('number')}: {issue_data.get('title', '')[:50]}")
                
                # 获取评论
                comments = self.collector.fetch_comments(
                    repo_owner, repo_name, issue_data.get('number')
                )
                
                # AI解析（确保 title/body 不为 None，避免 NoneType + str）
                title = (issue_data.get('title') or '') or ''
                body = (issue_data.get('body') or '') or ''
                comment_bodies = [(c.get('body') or '') for c in comments]

                print("  🤖 AI解析中...")
                classification = self.parser.classify_issue(title, body)
                issue_type = classification.get('type', 'task')
                priority = self.parser.extract_priority(title, body, issue_type)
                tags = self.parser.extract_tags(title, body)
                summary = self.parser.generate_summary(title, body, comment_bodies)
                blocking_reason = self.parser.analyze_blocking_reasons(issue_data, comments)
                
                print(f"  ✅ 类型: {issue_type}, 优先级: {priority}")
                
                # 准备存储数据
                issue_snapshot = {
                    'issue_id': issue_data.get('id'),
                    'issue_number': issue_data.get('number'),
                    'repo_owner': repo_owner,
                    'repo_name': repo_name,
                    'title': title,
                    'body': body,
                    'state': issue_data.get('state', 'open'),
                    'issue_type': issue_type,
                    'priority': priority,
                    'assignee': issue_data.get('assignee', {}).get('login') if issue_data.get('assignee') else None,
                    'labels': [label.get('name') for label in issue_data.get('labels', [])],
                    'milestone': issue_data.get('milestone', {}).get('title') if issue_data.get('milestone') else None,
                    'created_at': self.collector.parse_datetime(issue_data.get('created_at')),
                    'updated_at': self.collector.parse_datetime(issue_data.get('updated_at')),
                    'closed_at': self.collector.parse_datetime(issue_data.get('closed_at')),
                    'ai_summary': summary,
                    'ai_tags': tags,
                    'ai_priority': priority,
                    'status': '已关闭' if issue_data.get('state') == 'closed' else ('处理中' if issue_data.get('assignee') else '待处理'),
                    'progress_percentage': 100.0 if issue_data.get('state') == 'closed' else 0.0,
                    'is_blocked': blocking_reason is not None,
                    'blocked_reason': blocking_reason,
                    'snapshot_time': snapshot_time
                }
                
                # 保存Issue快照
                self.storage.save_issue_snapshot(issue_snapshot, snapshot_time)
                
                # 保存评论
                if comments:
                    self.storage.save_comments(
                        comments,
                        issue_data.get('id'),
                        issue_data.get('number')
                    )
                
                # 暂不提取关联关系，收集待处理项（Phase 2 统一处理）
                pending_relations.append({
                    'issue_id': issue_data.get('id'),
                    'issue_number': issue_data.get('number'),
                    'body': body,
                    'comments': comments or []
                })
                
                stats['processed'] += 1
                
            except Exception as e:
                print(f"  ❌ 处理失败: {e}")
                stats['errors'] += 1
                continue
        
        # Phase 2: 所有 Issue 入库后，统一提取并保存关联关系
        # 此时被引用的 Issue 均已存在，可正确建立关联
        if pending_relations:
            print("\n" + "=" * 60)
            print("🔗 Phase 2: 提取并保存关联关系（所有 Issue 已入库，可正确解析引用）...")
            print("=" * 60)
            all_relations = []
            for idx, item in enumerate(pending_relations, 1):
                relations = self.collector.extract_relations(
                    item['issue_id'],
                    item['issue_number'],
                    item['body'],
                    item['comments']
                )
                if relations:
                    all_relations.extend(relations)
                if idx % 500 == 0 or idx == len(pending_relations):
                    print(f"  已扫描 {idx}/{len(pending_relations)} 个 Issue，发现 {len(all_relations)} 条关联")
            if all_relations:
                self.storage.save_relations(all_relations, repo_owner=repo_owner, repo_name=repo_name)
                print(f"✅ 关联关系处理完成：共发现 {len(all_relations)} 条")
        
        # 全量同步且未清空时：清理该仓库早于本次的旧快照，只保留本次 snapshot_time
        if (full_sync or ENABLE_FULL_RESYNC) and FULL_SYNC_SKIP_CLEAR:
            self.storage.trim_old_snapshots_for_repo(repo_owner, repo_name, snapshot_time)
        
        print("\n" + "=" * 60)
        print("同步完成！")
        print(f"总计: {stats['total']}, 成功: {stats['processed']}, 失败: {stats['errors']}")
        print("=" * 60)
        
        return stats
    
    def generate_reports(self, repo_owner: str, repo_name: str):
        """
        生成报告
        
        输入参数：
        - repo_owner: 仓库所有者
        - repo_name: 仓库名称
        
        输出：
        - tuple: (daily_report, progress_report) 报告数据字典
        - 报告文件保存在 data/reports/ 目录
        """
        print("=" * 60)
        print(f"生成报告: {repo_owner}/{repo_name}")
        print("=" * 60)
        
        # 生成日报
        print("\n📊 生成日报...")
        daily_report = self.analyzer.generate_daily_report(repo_owner, repo_name)
        
        # 生成进度报告
        print("\n📈 生成进度报告...")
        progress_report = self.analyzer.generate_progress_report(repo_owner, repo_name)
        
        print("\n✅ 所有报告已生成")
        
        return daily_report, progress_report


def main():
    """主函数"""
    print("=" * 60)
    print("GitHub Issue 智能管理系统")
    print("=" * 60)
    
    # 验证配置
    if not validate_config():
        print("\n❌ 配置验证失败，请检查配置文件")
        return
    
    # 创建调度器
    scheduler = IssueManagerScheduler()
    
    # 示例：同步仓库
    # 请修改为你要同步的仓库
    repo_owner = input("\n请输入仓库所有者（例如：octocat）: ").strip()
    repo_name = input("请输入仓库名称（例如：Hello-World）: ").strip()
    
    if not repo_owner or not repo_name:
        print("❌ 仓库信息不能为空")
        return
    
    # 询问是否全量同步
    full_sync_input = input("\n是否执行全量同步（清空旧数据）？(y/N): ").strip().lower()
    full_sync = full_sync_input == 'y'
    
    # 执行同步
    try:
        stats = scheduler.sync_repo(repo_owner, repo_name, full_sync=full_sync)
        
        # 生成报告
        generate_reports = input("\n是否生成报告？(Y/n): ").strip().lower()
        if generate_reports != 'n':
            scheduler.generate_reports(repo_owner, repo_name)
        
        print("\n✅ 所有任务完成！")
        
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
