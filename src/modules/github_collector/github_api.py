#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub API 采集模块
功能：从GitHub API获取Issue数据、评论、时间线等
"""

import time
import httpx
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))
from config.config import GITHUB_TOKEN, GITHUB_API_BASE_URL, GITHUB_RATE_LIMIT_RETRY


class GitHubCollector:
    """GitHub API 采集器"""
    
    def __init__(self):
        self.base_url = GITHUB_API_BASE_URL
        self.headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-Issue-Manager"
        }
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = 0
    
    def _check_rate_limit(self):
        """检查并等待API限流"""
        if self.rate_limit_remaining < 10:
            wait_time = max(0, self.rate_limit_reset - time.time() + 1)
            if wait_time > 0:
                print(f"⏳ API限流，等待 {int(wait_time)} 秒...")
                time.sleep(wait_time)
    
    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """发送HTTP请求，带重试和限流检查"""
        self._check_rate_limit()
        
        for attempt in range(GITHUB_RATE_LIMIT_RETRY):
            try:
                with httpx.Client(timeout=30.0) as client:
                    response = client.request(method, url, headers=self.headers, **kwargs)
                    
                    # 更新限流信息
                    if 'X-RateLimit-Remaining' in response.headers:
                        self.rate_limit_remaining = int(response.headers['X-RateLimit-Remaining'])
                    if 'X-RateLimit-Reset' in response.headers:
                        self.rate_limit_reset = int(response.headers['X-RateLimit-Reset'])
                    
                    # 处理限流
                    if response.status_code == 403:
                        if 'X-RateLimit-Remaining' in response.headers and int(response.headers['X-RateLimit-Remaining']) == 0:
                            reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                            wait_time = max(0, reset_time - time.time() + 1)
                            print(f"⏳ API限流，等待 {int(wait_time)} 秒...")
                            time.sleep(wait_time)
                            continue
                    
                    response.raise_for_status()
                    return response
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise
                if attempt < GITHUB_RATE_LIMIT_RETRY - 1:
                    wait_time = 2 ** attempt
                    print(f"⚠️  请求失败，{wait_time}秒后重试... (尝试 {attempt + 1}/{GITHUB_RATE_LIMIT_RETRY})")
                    time.sleep(wait_time)
                else:
                    raise
            except Exception as e:
                if attempt < GITHUB_RATE_LIMIT_RETRY - 1:
                    wait_time = 2 ** attempt
                    print(f"⚠️  请求错误，{wait_time}秒后重试... (尝试 {attempt + 1}/{GITHUB_RATE_LIMIT_RETRY})")
                    time.sleep(wait_time)
                else:
                    raise
        
        raise Exception("请求失败，已达到最大重试次数")
    
    def fetch_issues(
        self,
        owner: str,
        repo: str,
        state: str = "all",
        since: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 100
    ) -> Tuple[List[Dict], int]:
        """
        获取Issues列表
        
        输入参数：
        - owner: GitHub仓库所有者
        - repo: 仓库名称
        - state: Issue状态 (all/open/closed)
        - since: 只获取此时间之后的Issues（用于增量同步）
        - page: 页码
        - per_page: 每页数量
        
        输出：
        - tuple: (Issue列表, 原始API返回条数)
          - 原始条数用于分页判断：若 < per_page 表示最后一页
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        params = {
            "state": state,
            "page": page,
            "per_page": per_page,
            "sort": "updated",
            "direction": "desc"
        }
        
        if since:
            params["since"] = since.isoformat()
        
        response = self._request("GET", url, params=params)
        raw_issues = response.json()
        raw_count = len(raw_issues)
        
        # 过滤掉Pull Requests（GitHub API会把PR也当作Issue返回）
        issues = [issue for issue in raw_issues if "pull_request" not in issue]
        
        return issues, raw_count
    
    def fetch_issue(self, owner: str, repo: str, issue_number: int) -> Dict:
        """
        获取单个Issue详情
        
        输入参数：
        - owner: GitHub仓库所有者
        - repo: 仓库名称
        - issue_number: Issue编号
        
        输出：
        - Dict: Issue数据
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}"
        response = self._request("GET", url)
        return response.json()
    
    def fetch_comments(self, owner: str, repo: str, issue_number: int) -> List[Dict]:
        """
        获取Issue评论
        
        输入参数：
        - owner: GitHub仓库所有者
        - repo: 仓库名称
        - issue_number: Issue编号
        
        输出：
        - List[Dict]: 评论数据列表
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments"
        response = self._request("GET", url)
        return response.json()
    
    def fetch_timeline(self, owner: str, repo: str, issue_number: int) -> List[Dict]:
        """
        获取Issue时间线（事件历史）
        
        输入参数：
        - owner: GitHub仓库所有者
        - repo: 仓库名称
        - issue_number: Issue编号
        
        输出：
        - List[Dict]: 时间线事件列表
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/timeline"
        response = self._request("GET", url)
        return response.json()
    
    def extract_relations(self, issue_id: int, issue_number: int, body: str, comments: List[Dict]) -> List[Dict]:
        """
        提取Issue之间的关联关系
        
        输入参数：
        - issue_id: Issue的GitHub ID（不是number）
        - issue_number: Issue编号
        - body: Issue正文内容
        - comments: 评论列表
        
        输出：
        - List[Dict]: 关联关系列表，格式：
          [{
              "from_issue_id": int,  # 源Issue的GitHub ID
              "to_issue_number": int,  # 目标Issue的编号（注意：这里返回number，需要在存储时转换为ID）
              "relation_type": str,  # 关系类型：mention, reference, duplicate, related
              "relation_semantic": str,  # 关系语义描述
              "created_at": datetime,  # 关系创建时间
              "source": str,  # 来源：body, comment
              "context_text": str  # 上下文文本
          }]
        """
        import re
        
        relations = []
        text_sources = [
            ("body", body),
        ]
        
        # 添加评论
        for comment in comments:
            text_sources.append(("comment", comment.get("body", "")))
        
        # 匹配Issue引用模式：#123, #456, issue #789, fixes #111
        issue_pattern = r'#(\d+)'
        
        for source_type, text in text_sources:
            if not text:
                continue
            
            # 查找所有Issue引用
            matches = re.finditer(issue_pattern, text)
            for match in matches:
                mentioned_number = int(match.group(1))
                
                # 跳过自己
                if mentioned_number == issue_number:
                    continue
                
                # 判断关系类型
                context_start = max(0, match.start() - 50)
                context_end = min(len(text), match.end() + 50)
                context = text[context_start:context_end]
                
                relation_type = "mention"
                relation_semantic = "提及"
                
                # 根据上下文判断关系类型
                context_lower = context.lower()
                if any(kw in context_lower for kw in ["fixes", "fix", "解决", "修复"]):
                    relation_type = "fixes"
                    relation_semantic = "修复"
                elif any(kw in context_lower for kw in ["duplicate", "重复", "相同"]):
                    relation_type = "duplicate"
                    relation_semantic = "重复"
                elif any(kw in context_lower for kw in ["related", "相关", "关联"]):
                    relation_type = "related"
                    relation_semantic = "相关"
                elif any(kw in context_lower for kw in ["blocks", "阻塞", "阻止"]):
                    relation_type = "blocks"
                    relation_semantic = "阻塞"
                elif any(kw in context_lower for kw in ["depends on", "依赖", "需要"]):
                    relation_type = "depends_on"
                    relation_semantic = "依赖"
                
                # 解析时间
                created_at = datetime.now()
                if source_type == "comment":
                    # 从评论中获取时间
                    for comment in comments:
                        if comment.get("body", "") == text:
                            created_at_str = comment.get("created_at")
                            if created_at_str:
                                try:
                                    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                                except:
                                    pass
                            break
                
                relations.append({
                    "from_issue_id": issue_id,  # 使用GitHub ID
                    "to_issue_number": mentioned_number,  # 注意：这里返回number，需要在存储时转换为ID
                    "relation_type": relation_type,
                    "relation_semantic": relation_semantic,
                    "created_at": created_at,
                    "source": source_type,
                    "context_text": context.strip()
                })
        
        return relations
    
    def parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """解析GitHub时间字符串"""
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except:
            return None


if __name__ == "__main__":
    # 测试代码
    collector = GitHubCollector()
    
    # 测试获取Issues
    print("测试：获取Issues...")
    try:
        issues, raw_count = collector.fetch_issues("octocat", "Hello-World", state="all", per_page=5)
        print(f"✅ 成功获取 {len(issues)} 个Issues (原始返回 {raw_count} 条)")
        if issues:
            print(f"示例Issue: #{issues[0].get('number')} - {issues[0].get('title')}")
    except Exception as e:
        print(f"❌ 错误: {e}")
