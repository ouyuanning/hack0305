#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统窗口检测器（策略2）
从活动窗口标题提取Issue信息
"""
import re
import sys
from typing import Optional, Dict


def get_issue_from_window(github_token: Optional[str] = None) -> Optional[Dict]:
    """从活动窗口获取Issue"""
    if sys.platform == 'darwin':
        return _get_issue_macos(github_token)
    elif sys.platform == 'win32':
        return _get_issue_windows(github_token)
    else:
        raise Exception(f"不支持的平台: {sys.platform}")


def _get_issue_macos(github_token: Optional[str] = None) -> Optional[Dict]:
    """macOS实现"""
    try:
        from AppKit import NSWorkspace
        from Quartz.CoreGraphics import (
            CGWindowListCopyWindowInfo,
            kCGWindowListOptionOnScreenOnly,
            kCGNullWindowID,
        )
    except ImportError:
        raise Exception("需要: pip install pyobjc-framework-Quartz pyobjc-framework-Cocoa")

    # 获取活动应用
    active_app = NSWorkspace.sharedWorkspace().activeApplication()
    app_name = active_app.get('NSApplicationName', '')

    # 检查是否是浏览器
    browsers = ['Google Chrome', 'Safari', 'Firefox', 'Microsoft Edge', 'Chromium']
    if app_name not in browsers:
        return None

    # 获取窗口
    windows = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)

    for window in windows:
        if window.get('kCGWindowOwnerName') == app_name:
            title = window.get('kCGWindowName', '')
            if title:
                issue = _extract_from_title(title, github_token)
                if issue:
                    return issue

    return None


def _get_issue_windows(github_token: Optional[str] = None) -> Optional[Dict]:
    """Windows实现"""
    try:
        import win32gui
    except ImportError:
        raise Exception("需要: pip install pywin32")

    hwnd = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(hwnd)

    return _extract_from_title(title, github_token)


def _extract_from_title(title: str, github_token: Optional[str] = None) -> Optional[Dict]:
    """
    从窗口标题提取Issue

    常见格式：
    - "Issue #8450: Bug标题 · matrixorigin/matrixflow"
    - "Bug标题 · Issue #8450 · matrixorigin/matrixflow"
    """
    if not title:
        return None

    # 提取Issue编号
    m = re.search(r'#(\d+)', title)
    if not m:
        return None

    number = int(m.group(1))

    # 提取owner/repo
    m2 = re.search(r'([^/\s]+)/([^/\s·]+)', title)
    if m2:
        owner, repo = m2.group(1), m2.group(2)
    else:
        owner, repo = "matrixorigin", "matrixflow"  # 默认

    # 获取详情
    if github_token:
        from .cdp_detector import _fetch_issue_details
        return _fetch_issue_details(owner, repo, number, github_token)

    return {
        "number": number,
        "owner": owner,
        "repo": repo,
        "url": f"https://github.com/{owner}/{repo}/issues/{number}"
    }
