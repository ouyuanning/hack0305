#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告生成模块
功能：生成各种分析报告（进度报告、Bug分析、团队工作量等）
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))
from config.config import REPORT_OUTPUT_DIR
from modules.database_storage.mo_client import MOStorage


class Analyzer:
    """分析器，用于生成各种报告"""
    
    def __init__(self, storage: MOStorage):
        self.storage = storage
    
    def generate_daily_report(self, repo_owner: str, repo_name: str, target_date: Optional[datetime] = None) -> Dict:
        """
        生成日报
        
        输入参数：
        - repo_owner: 仓库所有者
        - repo_name: 仓库名称
        - target_date: 目标日期（默认为今天）
        
        输出：
        - Dict: 报告数据
        """
        if not target_date:
            target_date = datetime.now()
        
        # 获取最新快照
        sql_latest = """
        SELECT MAX(snapshot_time) as latest_time
        FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo
        """
        latest_result = self.storage.execute(sql_latest, {
            'owner': repo_owner,
            'repo': repo_name
        })
        
        if not latest_result or not latest_result[0].get('latest_time'):
            return {"error": "没有找到数据"}
        
        latest_time = latest_result[0]['latest_time']
        
        # 统计新Issue数量
        sql_new = """
        SELECT COUNT(*) as count
        FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo
        AND DATE(created_at) = DATE(:date)
        AND snapshot_time = :latest_time
        """
        new_result = self.storage.execute(sql_new, {
            'owner': repo_owner,
            'repo': repo_name,
            'date': target_date,
            'latest_time': latest_time
        })
        new_count = new_result[0]['count'] if new_result else 0
        
        # 统计关闭的Issue数量
        sql_closed = """
        SELECT COUNT(*) as count
        FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo
        AND state = 'closed'
        AND DATE(closed_at) = DATE(:date)
        AND snapshot_time = :latest_time
        """
        closed_result = self.storage.execute(sql_closed, {
            'owner': repo_owner,
            'repo': repo_name,
            'date': target_date,
            'latest_time': latest_time
        })
        closed_count = closed_result[0]['count'] if closed_result else 0
        
        # 统计总数
        sql_total = """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN state = 'open' THEN 1 ELSE 0 END) as open_count,
            SUM(CASE WHEN state = 'closed' THEN 1 ELSE 0 END) as closed_count,
            SUM(CASE WHEN is_blocked = 1 THEN 1 ELSE 0 END) as blocked_count
        FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo
        AND snapshot_time = :latest_time
        """
        total_result = self.storage.execute(sql_total, {
            'owner': repo_owner,
            'repo': repo_name,
            'latest_time': latest_time
        })
        
        total_stats = total_result[0] if total_result else {}
        
        report = {
            "date": target_date.strftime("%Y-%m-%d"),
            "repo": f"{repo_owner}/{repo_name}",
            "summary": {
                "total_issues": total_stats.get('total', 0),
                "open_issues": total_stats.get('open_count', 0),
                "closed_issues": total_stats.get('closed_count', 0),
                "blocked_issues": total_stats.get('blocked_count', 0),
                "new_today": new_count,
                "closed_today": closed_count
            },
            "generated_at": datetime.now().isoformat()
        }
        
        # 保存报告
        report_file = REPORT_OUTPUT_DIR / f"daily_report_{repo_owner}_{repo_name}_{target_date.strftime('%Y%m%d')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 日报已生成: {report_file}")
        return report
    
    def generate_progress_report(self, repo_owner: str, repo_name: str) -> Dict:
        """
        生成进度报告
        
        输入参数：
        - repo_owner: 仓库所有者
        - repo_name: 仓库名称
        
        输出：
        - Dict: 报告数据
        """
        # 获取最新快照
        sql_latest = """
        SELECT MAX(snapshot_time) as latest_time
        FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo
        """
        latest_result = self.storage.execute(sql_latest, {
            'owner': repo_owner,
            'repo': repo_name
        })
        
        if not latest_result or not latest_result[0].get('latest_time'):
            return {"error": "没有找到数据"}
        
        latest_time = latest_result[0]['latest_time']
        
        # 按状态统计
        sql_by_status = """
        SELECT status, COUNT(*) as count
        FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo
        AND snapshot_time = :latest_time
        GROUP BY status
        """
        status_result = self.storage.execute(sql_by_status, {
            'owner': repo_owner,
            'repo': repo_name,
            'latest_time': latest_time
        })
        by_status = {row['status']: row['count'] for row in status_result}
        
        # 按类型统计
        sql_by_type = """
        SELECT issue_type, COUNT(*) as count
        FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo
        AND snapshot_time = :latest_time
        GROUP BY issue_type
        """
        type_result = self.storage.execute(sql_by_type, {
            'owner': repo_owner,
            'repo': repo_name,
            'latest_time': latest_time
        })
        by_type = {row['issue_type']: row['count'] for row in type_result}
        
        # 按优先级统计
        sql_by_priority = """
        SELECT priority, COUNT(*) as count
        FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo
        AND snapshot_time = :latest_time
        GROUP BY priority
        """
        priority_result = self.storage.execute(sql_by_priority, {
            'owner': repo_owner,
            'repo': repo_name,
            'latest_time': latest_time
        })
        by_priority = {row['priority']: row['count'] for row in priority_result}
        
        report = {
            "repo": f"{repo_owner}/{repo_name}",
            "generated_at": datetime.now().isoformat(),
            "by_status": by_status,
            "by_type": by_type,
            "by_priority": by_priority
        }
        
        # 保存报告
        report_file = REPORT_OUTPUT_DIR / f"progress_report_{repo_owner}_{repo_name}_{datetime.now().strftime('%Y%m%d')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 进度报告已生成: {report_file}")
        return report


if __name__ == "__main__":
    # 测试代码
    from modules.database_storage.mo_client import MOStorage
    
    storage = MOStorage()
    analyzer = Analyzer(storage)
    
    print("测试：生成报告...")
    # report = analyzer.generate_daily_report("octocat", "Hello-World")
    # print(f"报告: {json.dumps(report, ensure_ascii=False, indent=2)}")
