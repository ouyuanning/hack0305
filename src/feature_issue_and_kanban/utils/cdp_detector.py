#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chrome CDP检测器（策略1）
需要Chrome调试模式，失败时抛出异常
"""
import re
from typing import Optional, Dict

try:
    import requests
except ImportError:
    requests = None


def get_issue_from_cdp(github_token: Optional[str] = None) -> Optional[Dict]:
    """通过CDP获取Issue"""
    if not requests:
        raise Exception("需要安装 requests")

    # 检查CDP是否可用
    try:
        response = requests.get('http://localhost:9222/json', timeout=2)
        if response.status_code != 200:
            raise Exception("CDP不可访问")
    except Exception as e:
        raise Exception(f"无法连接CDP: {e}")

    # 获取tabs
    tabs = response.json()
    page_tabs = [t for t in tabs if t.get("type") == "page" and t.get("url")]

    # 查找GitHub Issue页面（3层策略）
    github_issue_tabs = [
        t for t in page_tabs
        if "github.com" in t.get("url", "") and "/issues/" in t.get("url", "")
    ]

    if github_issue_tabs:
        url = github_issue_tabs[-1].get("url")
    else:
        github_tabs = [t for t in page_tabs if "github.com" in t.get("url", "")]
        if github_tabs:
            url = github_tabs[-1].get("url")
        elif page_tabs:
            url = page_tabs[-1].get("url")
        else:
            return None

    if not url:
        return None

    m = re.search(r"github\.com/([^/]+)/([^/]+)/issues/(\d+)", url, re.I)

    if not m:
        return None

    owner, repo, number = m.group(1), m.group(2), int(m.group(3))

    # 获取详情
    if github_token:
        return _fetch_issue_details(owner, repo, number, github_token)

    return {
        "number": number,
        "owner": owner,
        "repo": repo,
        "url": f"https://github.com/{owner}/{repo}/issues/{number}"
    }


def _fetch_issue_details(owner: str, repo: str, number: int, token: str) -> Dict:
    """获取Issue详情（供其他检测器调用）"""
    if not requests:
        return {
            "number": number,
            "owner": owner,
            "repo": repo,
            "url": f"https://github.com/{owner}/{repo}/issues/{number}"
        }

    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            issue = r.json()
            return {
                "number": number,
                "owner": owner,
                "repo": repo,
                "title": issue.get("title", ""),
                "labels": [l.get("name", "") for l in issue.get("labels", [])],
                "body": (issue.get("body") or "")[:500],
                "url": issue.get("html_url", ""),
                "state": issue.get("state", "")
            }
    except Exception:
        pass

    return {
        "number": number,
        "owner": owner,
        "repo": repo,
        "url": f"https://github.com/{owner}/{repo}/issues/{number}"
    }
