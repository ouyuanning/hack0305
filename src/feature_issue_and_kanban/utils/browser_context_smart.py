#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能浏览器上下文检测（混合方案核心）
自动尝试4种策略，优雅降级
"""
from typing import Optional, Dict


def get_issue_context_smart(github_token: Optional[str] = None) -> Optional[Dict]:
    """
    智能获取浏览器Issue上下文

    Returns:
        {
            "number": 8450,
            "owner": "matrixorigin",
            "repo": "matrixflow",
            "title": "Issue标题",
            "labels": ["product/mo"],
            "url": "https://...",
            "source": "cdp/window/clipboard/manual"
        }
    """
    print("\n" + "=" * 60)
    print("🔍 智能检测浏览器Issue")
    print("=" * 60)

    # 策略1：Chrome CDP
    print("\n【策略1】Chrome CDP...")
    try:
        from .cdp_detector import get_issue_from_cdp
        issue = get_issue_from_cdp(github_token)
        if issue:
            issue['source'] = 'cdp'
            print(f"✅ 从CDP获取 #{issue['number']}")
            return issue
        print("ℹ️ CDP可用但未找到Issue")
    except Exception as e:
        print(f"ℹ️ CDP不可用: {str(e)[:50]}")

    # 策略2：系统窗口
    print("\n【策略2】系统窗口...")
    try:
        from .window_detector import get_issue_from_window
        issue = get_issue_from_window(github_token)
        if issue:
            issue['source'] = 'window'
            print(f"✅ 从窗口推断 #{issue['number']}")
            return issue
        print("ℹ️ 窗口未找到Issue")
    except Exception as e:
        print(f"ℹ️ 窗口检测失败: {str(e)[:50]}")

    # 策略3：剪贴板
    print("\n【策略3】剪贴板...")
    try:
        from .clipboard_detector import get_issue_from_clipboard
        issue = get_issue_from_clipboard(github_token)
        if issue:
            issue['source'] = 'clipboard'
            print(f"✅ 从剪贴板 #{issue['number']}")
            return issue
        print("ℹ️ 剪贴板无Issue")
    except Exception as e:
        print(f"ℹ️ 剪贴板失败: {str(e)[:50]}")

    # 策略4：手动输入
    print("\n【策略4】手动输入...")
    try:
        from .manual_input import get_issue_from_user_input
        issue = get_issue_from_user_input(github_token)
        if issue:
            issue['source'] = 'manual'
            print(f"✅ 用户输入 #{issue['number']}")
            return issue
    except Exception as e:
        print(f"⚠️ 手动输入失败: {e}")

    print("\n⚠️ 未能获取Issue")
    return None
