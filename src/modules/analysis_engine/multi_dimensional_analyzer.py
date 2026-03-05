#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多维度分析引擎 - MatrixOne兼容版本
功能：按客户、层级、关联关系等多维度分析Issue
修复：移除JOIN/WHERE中的子查询，改为先查询latest_time再使用（MatrixOne不支持）
"""

import sys
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))
from modules.database_storage.mo_client import MOStorage


class MultiDimensionalAnalyzer:
    """多维度Issue分析器 - MatrixOne兼容版"""
    
    def __init__(self, storage: MOStorage):
        self.storage = storage
        self._latest_snapshot_cache = {}
    
    def _get_latest_snapshot_time(self, repo_owner: str, repo_name: str) -> Optional[datetime]:
        """
        获取最新快照时间（独立查询，避免子查询）
        """
        cache_key = f"{repo_owner}/{repo_name}"
        if cache_key in self._latest_snapshot_cache:
            return self._latest_snapshot_cache[cache_key]
        try:
            sql = """
            SELECT MAX(snapshot_time) as latest_time
            FROM issues_snapshot
            WHERE repo_owner = :owner AND repo_name = :repo
            """
            result = self.storage.execute(sql, {'owner': repo_owner, 'repo': repo_name})
            if result and result[0].get('latest_time'):
                latest_time = result[0]['latest_time']
                self._latest_snapshot_cache[cache_key] = latest_time
                return latest_time
        except Exception as e:
            print(f"⚠️  获取最新快照时间失败: {e}")
        return None
    
    def _get_repo_relations(self, repo_owner: str, repo_name: str, relation_types: List[str]) -> List[Dict]:
        """
        获取指定仓库内的关联关系
        修复：先查询latest_time，JOIN中直接使用，避免子查询（MatrixOne不支持）
        """
        latest_time = self._get_latest_snapshot_time(repo_owner, repo_name)
        if not latest_time:
            return []
        placeholders = ','.join([f"'{t}'" for t in relation_types])
        sql = f"""
        SELECT r.from_issue_id, r.to_issue_id, r.relation_type
        FROM issue_relations r
        INNER JOIN issues_snapshot i1 ON r.from_issue_id = i1.issue_id
            AND i1.repo_owner = :owner AND i1.repo_name = :repo
            AND i1.snapshot_time = :latest_time
        INNER JOIN issues_snapshot i2 ON r.to_issue_id = i2.issue_id
            AND i2.repo_owner = :owner2 AND i2.repo_name = :repo2
            AND i2.snapshot_time = :latest_time
        WHERE r.relation_type IN ({placeholders})
        """
        params = {
            'owner': repo_owner, 'repo': repo_name,
            'owner2': repo_owner, 'repo2': repo_name,
            'latest_time': latest_time,
        }
        return self.storage.execute(sql, params)
    
    # =========================================================================
    # 核心功能1: 客户/项目维度分析
    # =========================================================================
    
    def get_all_customers(self, repo_owner: str, repo_name: str) -> List[str]:
        """
        获取所有客户列表（从labels中提取customer/xxx）
        修复：先查询latest_time，避免子查询
        """
        latest_time = self._get_latest_snapshot_time(repo_owner, repo_name)
        if not latest_time:
            print(f"⚠️  未找到 {repo_owner}/{repo_name} 的快照数据")
            return []
        sql = """
        SELECT DISTINCT CAST(labels AS CHAR) as labels_str
        FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo
        AND snapshot_time = :latest_time
        AND CAST(labels AS CHAR) LIKE '%customer/%'
        """
        results = self.storage.execute(sql, {
            'owner': repo_owner,
            'repo': repo_name,
            'latest_time': latest_time
        })
        
        customers = set()
        for row in results:
            labels_str = row.get('labels_str', '[]')
            try:
                labels = json.loads(labels_str) if isinstance(labels_str, str) else labels_str
                if isinstance(labels, list):
                    for label in labels:
                        if label.startswith('customer/'):
                            customer_name = label.replace('customer/', '').strip()
                            customers.add(customer_name)
            except (json.JSONDecodeError, TypeError):
                continue
        
        return sorted(list(customers))
    
    def get_customer_issues(self, repo_owner: str, repo_name: str, customer: str) -> List[Dict]:
        """
        获取某个客户的所有Issue
        修复：先查询latest_time，避免子查询
        """
        latest_time = self._get_latest_snapshot_time(repo_owner, repo_name)
        if not latest_time:
            return []
        sql = """
        SELECT 
            id, issue_id, issue_number, title, body, state,
            issue_type, priority, assignee, labels, milestone,
            created_at, updated_at, closed_at,
            ai_summary, ai_tags, status, progress_percentage,
            is_blocked, blocked_reason
        FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo
        AND snapshot_time = :latest_time
        AND CAST(labels AS CHAR) LIKE :customer_pattern
        """
        results = self.storage.execute(sql, {
            'owner': repo_owner,
            'repo': repo_name,
            'latest_time': latest_time,
            'customer_pattern': f'%customer/{customer}%'
        })
        
        return [dict(row) for row in results]
    
    def analyze_customer_project(self, repo_owner: str, repo_name: str, customer: str) -> Dict:
        """
        分析单个客户项目的详细情况
        
        返回:
        {
            "customer": "金盘",
            "total_issues": 25,
            "by_state": {"open": 15, "closed": 10},
            "by_type": {"bug": 8, "feature": 12, "task": 5},
            "by_priority": {"P0": 2, "P1": 8, "P2": 10, "P3": 5},
            "by_status": {"待处理": 3, "处理中": 7, "已完成": 10, "已关闭": 5},
            "completion_rate": 0.6,
            "blocked_issues": [...],
            "risks": {...}
        }
        """
        issues = self.get_customer_issues(repo_owner, repo_name, customer)
        
        if not issues:
            return {
                "customer": customer,
                "error": "没有找到该客户的Issue"
            }
        
        # 基础统计
        total = len(issues)
        by_state = defaultdict(int)
        by_type = defaultdict(int)
        by_priority = defaultdict(int)
        by_status = defaultdict(int)
        blocked = []
        
        for issue in issues:
            # 状态统计
            state = issue.get('state', 'unknown')
            by_state[state] += 1
            
            # 类型统计
            issue_type = issue.get('issue_type') or issue.get('ai_tags', [])
            if isinstance(issue_type, list) and issue_type:
                issue_type = issue_type[0]
            by_type[issue_type or 'unknown'] += 1
            
            # 优先级统计
            priority = issue.get('priority') or issue.get('ai_priority', 'P3')
            by_priority[priority] += 1
            
            # 状态统计
            status = issue.get('status', '未知')
            by_status[status] += 1
            
            # 收集被阻塞的Issue
            if issue.get('is_blocked'):
                blocked.append({
                    'issue_number': issue['issue_number'],
                    'title': issue['title'],
                    'reason': issue.get('blocked_reason', '未知原因')
                })
        
        # 完成率计算
        closed_count = by_state.get('closed', 0)
        completion_rate = closed_count / total if total > 0 else 0
        
        # 风险识别
        risks = self._identify_customer_risks(issues)
        
        return {
            "customer": customer,
            "total_issues": total,
            "by_state": dict(by_state),
            "by_type": dict(by_type),
            "by_priority": dict(by_priority),
            "by_status": dict(by_status),
            "completion_rate": round(completion_rate, 2),
            "blocked_issues": blocked,
            "risks": risks,
            "analyzed_at": datetime.now().isoformat()
        }
    
    def _identify_customer_risks(self, issues: List[Dict]) -> Dict:
        """识别客户项目风险"""
        risks = {
            "high_priority_open": [],    # 高优先级未关闭
            "long_time_open": [],         # 长时间未关闭
            "blocked_chain": [],          # 被阻塞的Issue
            "low_progress": []            # 进度低于预期
        }
        
        now = datetime.now()
        
        for issue in issues:
            issue_number = issue['issue_number']
            title = issue['title']
            state = issue.get('state')
            priority = issue.get('priority') or issue.get('ai_priority')
            created_at = issue.get('created_at')
            
            # 高优先级未关闭
            if state == 'open' and priority in ['P0', 'P1']:
                risks['high_priority_open'].append({
                    'issue_number': issue_number,
                    'title': title,
                    'priority': priority,
                    'days_open': (now - created_at).days if created_at else 0
                })
            
            # 长时间未关闭（超过30天）
            if state == 'open' and created_at:
                days_open = (now - created_at).days
                if days_open > 30:
                    risks['long_time_open'].append({
                        'issue_number': issue_number,
                        'title': title,
                        'days_open': days_open
                    })
            
            # 被阻塞
            if issue.get('is_blocked'):
                risks['blocked_chain'].append({
                    'issue_number': issue_number,
                    'title': title,
                    'reason': issue.get('blocked_reason', '未知')
                })
            
            # 进度低（处理中但进度<30%）
            if issue.get('status') == '处理中':
                progress = issue.get('progress_percentage', 0)
                if progress < 30:
                    risks['low_progress'].append({
                        'issue_number': issue_number,
                        'title': title,
                        'progress': progress
                    })
        
        return risks
    
    # =========================================================================
    # 核心功能2: Issue层级分析（L1/L2/L3/L4）
    # =========================================================================
    
    def identify_issue_level(self, issue: Dict) -> str:
        """
        识别Issue层级
        
        策略：
        1. 通过labels识别（如有level/L1等标签）
        2. 通过title关键词识别
        3. 通过关联关系识别（有父Issue则为子级）
        
        返回: 'L1', 'L2', 'L3', 或 'L4'
        """
        title = issue.get('title', '').lower()
        labels = issue.get('labels', [])
        
        if isinstance(labels, str):
            try:
                labels = json.loads(labels)
            except:
                labels = []
        
        # 策略1: 通过labels
        for label in labels:
            label_lower = label.lower()
            if 'level/l1' in label_lower or 'project' in label_lower:
                return 'L1'
            if 'level/l2' in label_lower or 'test' in label_lower:
                return 'L2'
            if 'level/l3' in label_lower or 'feature' in label_lower:
                return 'L3'
            if 'level/l4' in label_lower or 'task' in label_lower or 'subtask' in label_lower:
                return 'L4'
        
        # 策略2: 通过标题关键词
        l1_keywords = ['客户项目', 'customer project', '项目需求', '总项目']
        l2_keywords = ['测试需求', 'test request', 'qa', '测试任务']
        l3_keywords = ['feature', '功能', '需求', 'epic']
        l4_keywords = ['bug', 'task', '任务', '缺陷', 'subtask', '子任务']
        
        if any(kw in title for kw in l1_keywords):
            return 'L1'
        if any(kw in title for kw in l2_keywords):
            return 'L2'
        if any(kw in title for kw in l3_keywords):
            return 'L3'
        if any(kw in title for kw in l4_keywords):
            return 'L4'
        
        # 默认为L3（Feature级别）
        return 'L3'
    
    def analyze_hierarchy_progress(self, repo_owner: str, repo_name: str, customer: str) -> Dict:
        """
        分析客户项目的层级进度
        
        返回:
        {
            "customer": "金盘",
            "L1": {"total": 1, "closed": 0, "rate": 0.0},
            "L2": {"total": 5, "closed": 3, "rate": 0.6},
            "L3": {"total": 10, "closed": 6, "rate": 0.6},
            "L4": {"total": 9, "closed": 7, "rate": 0.78}
        }
        """
        issues = self.get_customer_issues(repo_owner, repo_name, customer)
        
        # 按层级分组
        by_level = {
            'L1': {'issues': [], 'total': 0, 'closed': 0},
            'L2': {'issues': [], 'total': 0, 'closed': 0},
            'L3': {'issues': [], 'total': 0, 'closed': 0},
            'L4': {'issues': [], 'total': 0, 'closed': 0}
        }
        
        for issue in issues:
            level = self.identify_issue_level(issue)
            by_level[level]['issues'].append(issue)
            by_level[level]['total'] += 1
            if issue.get('state') == 'closed':
                by_level[level]['closed'] += 1
        
        # 计算完成率
        result = {"customer": customer}
        for level, data in by_level.items():
            total = data['total']
            closed = data['closed']
            result[level] = {
                'total': total,
                'closed': closed,
                'rate': round(closed / total, 2) if total > 0 else 0
            }
        
        return result
    
    # =========================================================================
    # 核心功能3: 跨项目共用Feature识别
    # =========================================================================
    
    def find_shared_features(self, repo_owner: str, repo_name: str) -> List[Dict]:
        """
        识别被多个客户项目共用的Feature
        
        返回:
        [
            {
                "feature_number": 1234,
                "feature_title": "CSV批量导入功能",
                "customers": ["金盘", "软通", "XX银行"],
                "customer_count": 3,
                "risk_level": "high"
            }
        ]
        """
        latest_time = self._get_latest_snapshot_time(repo_owner, repo_name)
        if not latest_time:
            return []
        relations = self._get_repo_relations(
            repo_owner, repo_name,
            ['depends_on', 'reference', 'related']
        )
        feature_customers = defaultdict(set)
        for rel in relations:
            from_id = rel['from_issue_id']
            to_id = rel['to_issue_id']
            from_issue = self._get_issue_by_id(repo_owner, repo_name, from_id, latest_time)
            if not from_issue:
                continue
            customer = self._extract_customer_from_labels(from_issue.get('labels'))
            if not customer:
                continue
            feature_customers[to_id].add(customer)
        shared = []
        for feature_id, customers in feature_customers.items():
            if len(customers) > 1:
                feature = self._get_issue_by_id(repo_owner, repo_name, feature_id, latest_time)
                if feature:
                    shared.append({
                        'feature_number': feature['issue_number'],
                        'feature_title': feature['title'],
                        'customers': sorted(list(customers)),
                        'customer_count': len(customers),
                        'risk_level': 'high' if len(customers) >= 3 else 'medium'
                    })
        
        # 按客户数量排序
        shared.sort(key=lambda x: x['customer_count'], reverse=True)
        
        return shared
    
    def _get_issue_by_id(self, repo_owner: str, repo_name: str, issue_id: int,
                         latest_time: Optional[datetime] = None) -> Optional[Dict]:
        """根据issue_id获取Issue，修复：直接传入latest_time避免子查询"""
        if not latest_time:
            latest_time = self._get_latest_snapshot_time(repo_owner, repo_name)
        if not latest_time:
            return None
        sql = """
        SELECT *
        FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo
        AND issue_id = :issue_id
        AND snapshot_time = :latest_time
        LIMIT 1
        """
        results = self.storage.execute(sql, {
            'owner': repo_owner,
            'repo': repo_name,
            'issue_id': issue_id,
            'latest_time': latest_time
        })
        return dict(results[0]) if results else None
    
    def _extract_customer_from_labels(self, labels) -> Optional[str]:
        """从labels中提取客户名称"""
        if isinstance(labels, str):
            try:
                labels = json.loads(labels)
            except:
                return None
        
        if not isinstance(labels, list):
            return None
        
        for label in labels:
            if label.startswith('customer/'):
                return label.replace('customer/', '').strip()
        
        return None
    
    # =========================================================================
    # 核心功能4: 阻塞链分析
    # =========================================================================
    
    def analyze_blocking_chains(self, repo_owner: str, repo_name: str) -> List[Dict]:
        """
        分析阻塞链
        
        返回:
        [
            {
                "chain": [100, 200, 300],  # Issue #100 被 #200 阻塞，#200 被 #300 阻塞
                "length": 3,
                "description": "#100 ← #200 ← #300"
            }
        ]
        """
        blocks = self._get_repo_relations(repo_owner, repo_name, ['blocks'])
        
        # 构建依赖图: blocked -> [blockers]
        graph = defaultdict(list)
        for rel in blocks:
            blocker = rel['from_issue_id']
            blocked = rel['to_issue_id']
            graph[blocked].append(blocker)
        
        # 找出阻塞链
        chains = []
        visited = set()
        
        for start_id in graph.keys():
            if start_id in visited:
                continue
            
            chain = [start_id]
            current = start_id
            
            # 追溯阻塞链
            while current in graph and len(chain) < 10:  # 防止环
                blockers = graph[current]
                if not blockers:
                    break
                
                blocker = blockers[0]  # 取第一个阻塞者
                if blocker in chain:  # 检测到环
                    break
                
                chain.append(blocker)
                visited.add(blocker)
                current = blocker
            
            if len(chain) > 1:
                latest_time = self._get_latest_snapshot_time(repo_owner, repo_name)
                issue_numbers = []
                for issue_id in chain:
                    issue = self._get_issue_by_id(repo_owner, repo_name, issue_id, latest_time)
                    if issue:
                        issue_numbers.append(issue['issue_number'])
                
                chains.append({
                    'chain': issue_numbers,
                    'length': len(issue_numbers),
                    'description': ' ← '.join([f'#{n}' for n in issue_numbers])
                })
        
        # 按链长度排序
        chains.sort(key=lambda x: x['length'], reverse=True)
        
        return chains
    
    # =========================================================================
    # 核心功能5: 综合报告生成
    # =========================================================================
    
    def generate_comprehensive_report(self, repo_owner: str, repo_name: str) -> Dict:
        """
        生成综合分析报告
        
        包含:
        1. 总体概览
        2. 各客户项目独立分析
        3. 跨项目共用Feature
        4. 阻塞链分析
        """
        # 总体概览（先查latest_time避免子查询）
        latest_time = self._get_latest_snapshot_time(repo_owner, repo_name)
        if not latest_time:
            return {
                "repo": f"{repo_owner}/{repo_name}",
                "generated_at": datetime.now().isoformat(),
                "summary": {"error": "未找到快照数据"},
                "customers": [],
                "customer_reports": {},
                "shared_features": [],
                "blocking_chains": []
            }
        sql_summary = """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN state = 'open' THEN 1 ELSE 0 END) as open_count,
            SUM(CASE WHEN state = 'closed' THEN 1 ELSE 0 END) as closed_count,
            SUM(CASE WHEN is_blocked = 1 THEN 1 ELSE 0 END) as blocked_count
        FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo
        AND snapshot_time = :latest_time
        """
        summary_result = self.storage.execute(sql_summary, {
            'owner': repo_owner,
            'repo': repo_name,
            'latest_time': latest_time
        })
        summary = dict(summary_result[0]) if summary_result else {}
        
        # 获取所有客户
        customers = self.get_all_customers(repo_owner, repo_name)
        
        # 各客户分析
        customer_reports = {}
        for customer in customers:
            customer_reports[customer] = self.analyze_customer_project(
                repo_owner, repo_name, customer
            )
        
        # 共用Feature分析
        shared_features = self.find_shared_features(repo_owner, repo_name)
        
        # 阻塞链分析
        blocking_chains = self.analyze_blocking_chains(repo_owner, repo_name)
        
        return {
            "repo": f"{repo_owner}/{repo_name}",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_issues": summary.get('total', 0),
                "open_issues": summary.get('open_count', 0),
                "closed_issues": summary.get('closed_count', 0),
                "blocked_issues": summary.get('blocked_count', 0),
                "customer_count": len(customers)
            },
            "customers": customers,
            "customer_reports": customer_reports,
            "shared_features": shared_features,
            "blocking_chains": blocking_chains
        }


# ============================================================================
# 使用示例
# ============================================================================

if __name__ == "__main__":
    from modules.database_storage.mo_client import MOStorage
    
    storage = MOStorage()
    analyzer = MultiDimensionalAnalyzer(storage)
    
    repo_owner = "matrixorigin"
    repo_name = "matrixflow"
    
    # 1. 获取所有客户
    print("=" * 60)
    print("所有客户列表:")
    customers = analyzer.get_all_customers(repo_owner, repo_name)
    for customer in customers:
        print(f"  - {customer}")
    
    # 2. 分析单个客户项目
    if customers:
        customer = customers[0]
        print(f"\n{customer} 客户项目分析:")
        print("=" * 60)
        report = analyzer.analyze_customer_project(repo_owner, repo_name, customer)
        print(json.dumps(report, indent=2, ensure_ascii=False))
    
    # 3. 生成综合报告
    print("\n综合报告:")
    print("=" * 60)
    comprehensive = analyzer.generate_comprehensive_report(repo_owner, repo_name)
    
    # 保存到文件
    output_file = "comprehensive_analysis_report.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(comprehensive, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 综合报告已保存到: {output_file}")
