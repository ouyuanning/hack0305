#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
浏览器上下文获取（混合方案入口）
4层智能检测：CDP → 窗口 → 剪贴板 → 手动输入
"""
from typing import Optional, Dict, List, Tuple

from .browser_context_smart import get_issue_context_smart


def get_issue_details_from_browser(
    cdp_url: str = "http://localhost:9222",
    github_token: Optional[str] = None
) -> Optional[Dict]:
    """
    获取浏览器Issue详情
    新实现：智能混合方案，自动尝试4种策略
    """
    return get_issue_context_smart(github_token)


def get_related_issues_from_browser(
    cdp_url: str = "http://localhost:9222",
) -> List[Tuple[str, str, int]]:
    """
    获取关联Issue（兼容接口）
    """
    issue = get_issue_context_smart()

    if issue:
        return [(
            issue.get('owner', 'matrixorigin'),
            issue.get('repo', 'matrixflow'),
            issue['number']
        )]

    return []


def get_active_tab_url(cdp_url: str = "http://localhost:9222") -> Optional[str]:
    """获取活动tab URL（兼容接口）"""
    issue = get_issue_context_smart()
    return issue.get('url') if issue else None
