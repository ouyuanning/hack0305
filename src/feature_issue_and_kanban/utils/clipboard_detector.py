#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剪贴板检测器（策略3）
从剪贴板检测GitHub Issue URL
"""
import re
import sys
import subprocess
from typing import Optional, Dict


def get_issue_from_clipboard(github_token: Optional[str] = None) -> Optional[Dict]:
    """从剪贴板获取Issue"""
    text = _get_clipboard()
    if not text:
        return None

    # 查找Issue URL
    m = re.search(r'https?://github\.com/([^/]+)/([^/]+)/issues/(\d+)', text, re.I)
    if not m:
        return None

    owner, repo, number = m.group(1), m.group(2), int(m.group(3))

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


def _get_clipboard() -> Optional[str]:
    """获取剪贴板（跨平台）"""
    if sys.platform == 'darwin':
        return _get_clipboard_macos()
    elif sys.platform == 'win32':
        return _get_clipboard_windows()
    else:
        return _get_clipboard_linux()


def _get_clipboard_macos() -> Optional[str]:
    """macOS: pbpaste"""
    try:
        result = subprocess.run(
            ['pbpaste'],
            capture_output=True,
            text=True,
            timeout=1,
            check=False
        )
        return result.stdout if result.returncode == 0 and result.stdout else None
    except Exception:
        return None


def _get_clipboard_windows() -> Optional[str]:
    """Windows: win32clipboard"""
    try:
        import win32clipboard
        win32clipboard.OpenClipboard()
        try:
            text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            if text is None:
                text = win32clipboard.GetClipboardData(win32clipboard.CF_TEXT)
                if isinstance(text, bytes):
                    text = text.decode('utf-8', errors='ignore')
            return text
        finally:
            win32clipboard.CloseClipboard()
    except Exception:
        return None


def _get_clipboard_linux() -> Optional[str]:
    """Linux: xclip 或 xsel"""
    for cmd in [
        ['xclip', '-selection', 'clipboard', '-o'],
        ['xsel', '--clipboard', '--output'],
    ]:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1,
                check=False
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None
