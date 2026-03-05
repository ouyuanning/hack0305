#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动输入模块（策略4）
当所有自动检测失败时，让用户输入
"""
import re
import sys
from typing import Optional, Dict


def get_issue_from_user_input(github_token: Optional[str] = None) -> Optional[Dict]:
    """
    用户手动输入

    支持格式：
    1. URL: https://github.com/matrixorigin/matrixflow/issues/8450
    2. 编号: #8450 或 8450
    3. 跳过: 直接回车
    """
    # 非交互模式（如 API、后台脚本）时跳过
    if not sys.stdin.isatty():
        return None

    print("\n" + "=" * 60)
    print("⚠️ 无法自动检测Issue")
    print("=" * 60)
    print("\n请提供Issue信息（可选）：")
    print("  1. 粘贴Issue URL")
    print("  2. 输入编号（如：8450）")
    print("  3. 回车跳过")
    print()

    try:
        user_input = input("请输入: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nℹ️ 跳过Issue关联")
        return None

    # 跳过
    if not user_input:
        print("ℹ️ 跳过Issue关联")
        return None

    # 解析URL
    m = re.search(r'github\.com/([^/]+)/([^/]+)/issues/(\d+)', user_input, re.I)
    if m:
        owner, repo, number = m.group(1), m.group(2), int(m.group(3))
        print(f"✅ 识别: {owner}/{repo}#{number}")

        if github_token:
            from .cdp_detector import _fetch_issue_details
            return _fetch_issue_details(owner, repo, number, github_token)

        return {
            "number": number,
            "owner": owner,
            "repo": repo,
            "url": f"https://github.com/{owner}/{repo}/issues/{number}"
        }

    # 解析编号
    m = re.search(r'#?(\d+)', user_input)
    if m:
        number = int(m.group(1))
        print(f"✅ 识别编号: #{number}")
        print("仓库（默认matrixorigin/matrixflow）:")

        try:
            repo_input = input("owner/repo: ").strip()
        except (EOFError, KeyboardInterrupt):
            repo_input = ""

        if repo_input and '/' in repo_input:
            owner, repo = repo_input.split('/', 1)
        else:
            owner, repo = "matrixorigin", "matrixflow"

        if github_token:
            from .cdp_detector import _fetch_issue_details
            return _fetch_issue_details(owner, repo, number, github_token)

        return {
            "number": number,
            "owner": owner,
            "repo": repo,
            "url": f"https://github.com/{owner}/{repo}/issues/{number}"
        }

    print("⚠️ 无法识别，跳过")
    return None
