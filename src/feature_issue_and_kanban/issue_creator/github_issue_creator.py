#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub 创建 Issue 封装
不修改主项目 github_collector，在此模块内用 Token 调用 POST /repos/{owner}/{repo}/issues
"""
import time
import httpx
from typing import Dict, List, Optional, Any


def create_issue_on_github(
    owner: str,
    repo: str,
    title: str,
    body: str,
    token: str,
    labels: Optional[List[str]] = None,
    assignees: Optional[List[str]] = None,
    base_url: str = "https://api.github.com",
) -> Dict[str, Any]:
    """
    调用 GitHub API 创建 Issue。
    :param owner: 仓库 owner
    :param repo: 仓库名
    :param title: 标题
    :param body: 正文
    :param token: GitHub Token
    :param labels: 标签列表
    :param assignees: 负责人登录名列表
    :param base_url: API 根地址
    :return: API 返回的 Issue 信息（含 number, html_url 等）
    """
    url = f"{base_url.rstrip('/')}/repos/{owner}/{repo}/issues"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-Issue-Manager",
    }
    payload = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels
    if assignees:
        payload["assignees"] = assignees

    for attempt in range(3):
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, json=payload, headers=headers)
                if resp.status_code == 403 and "rate limit" in resp.text.lower():
                    reset = int(resp.headers.get("X-RateLimit-Reset", 0))
                    wait = max(0, reset - time.time() + 1)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            raise
    raise RuntimeError("创建 Issue 失败，已达最大重试次数")
