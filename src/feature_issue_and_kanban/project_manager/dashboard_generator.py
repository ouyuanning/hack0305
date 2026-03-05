#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日看板生成：按项目标签从 project_issues 聚合，生成进度、风险、阻塞与 AI 总结，输出 Markdown。
"""
from datetime import date, timedelta
from typing import Dict, List, Optional


class DashboardGenerator:
    def __init__(self, storage, llm=None):
        self.storage = storage
        self.llm = llm

    def generate_dashboard(
        self,
        project_tag: str,
        snapshot_date: Optional[date] = None,
        repo_owner: Optional[str] = None,
        repo_name: Optional[str] = None,
    ) -> str:
        """
        生成指定项目、指定日期的看板 Markdown。
        优先从 project_issues 读；若表不存在或无数据则从 issues_snapshot 按标签回退。
        """
        snapshot_date = snapshot_date or date.today()
        rows = self._fetch_project_issues(project_tag, snapshot_date, repo_owner, repo_name)
        if not rows:
            return self._empty_dashboard(project_tag, snapshot_date)
        return self._build_dashboard_md(project_tag, snapshot_date, rows)

    def generate_dashboard_from_rows(
        self,
        project_tag: str,
        snapshot_date: Optional[date] = None,
        rows: Optional[List[Dict]] = None,
    ) -> str:
        """用给定的 rows 直接生成看板 Markdown（用于 --demo 假数据）。"""
        snapshot_date = snapshot_date or date.today()
        if not rows:
            return self._empty_dashboard(project_tag, snapshot_date)
        return self._build_dashboard_md(project_tag, snapshot_date, rows)

    def _build_dashboard_md(self, project_tag: str, snapshot_date: date, rows: List[Dict]) -> str:
        total = len(rows)
        completed = sum(1 for r in rows if r.get("issue_state") == "closed")
        progress_avg = sum(int(r.get("progress") or 0) for r in rows) // total if total else 0
        overdue = [r for r in rows if r.get("is_overdue")]
        blocked = [r for r in rows if r.get("pm_status") == "blocked"]
        in_progress = [r for r in rows if r.get("pm_status") == "in_progress"]
        md = f"""# 项目看板 · {project_tag}
**日期**: {snapshot_date} | **统计**: 共 {total} 项，已完成 {completed} 项，平均进度 {progress_avg}%

---
## 总体进度
- 完成率: {completed}/{total} ({100 * completed // total if total else 0}%)
- 平均进度: {progress_avg}%

---
## 逾期项
"""
        if not overdue:
            md += "- 无\n"
        else:
            for r in overdue:
                md += f"- #{r['issue_number']} [{r.get('issue_title', '')[:40]}]({r.get('issue_url', '')}) 逾期{r.get('days_overdue', 0)}天\n"
        md += "\n## 阻塞项\n"
        if not blocked:
            md += "- 无\n"
        else:
            for r in blocked:
                md += f"- #{r['issue_number']} {r.get('issue_title', '')[:50]}\n"
        md += "\n## 进行中\n"
        for r in in_progress[:15]:
            md += f"- #{r['issue_number']} {r.get('issue_title', '')[:50]} ({r.get('progress', 0)}%) assignee: {r.get('assignee') or '-'}\n"
        if len(in_progress) > 15:
            md += f"- ... 共 {len(in_progress)} 项\n"
        ai_summary = self._get_ai_summary(rows, overdue, blocked, progress_avg)
        if ai_summary:
            md += f"\n---\n## AI 总结与建议\n{ai_summary}\n"
        return md

    def generate_dashboard_html(
        self,
        project_tag: str,
        snapshot_date: Optional[date] = None,
        repo_owner: Optional[str] = None,
        repo_name: Optional[str] = None,
        rows: Optional[List[Dict]] = None,
    ) -> str:
        """生成与甘特图 v3 风格一致的看板 HTML（表头、表格、风险评估卡片）。"""
        snapshot_date = snapshot_date or date.today()
        if rows is None:
            rows = self._fetch_project_issues(project_tag, snapshot_date, repo_owner, repo_name)
        repo_owner = repo_owner or (rows[0].get("repo_owner") if rows else "matrixorigin")
        repo_name = repo_name or (rows[0].get("repo_name") if rows else "matrixflow")
        total = len(rows)
        completed = sum(1 for r in rows if r.get("issue_state") == "closed")
        progress_avg = sum(int(r.get("progress") or 0) for r in rows) // total if total else 0
        overdue = [r for r in rows if r.get("is_overdue")]
        blocked = [r for r in rows if r.get("pm_status") == "blocked"]
        in_progress = [r for r in rows if r.get("pm_status") == "in_progress"]

        def _st_badge(r: Dict) -> str:
            if r.get("pm_status") == "blocked":
                return '<span class="sb sb-b">🔴 卡点</span>'
            if r.get("issue_state") == "closed":
                return '<span class="sb sb-d">✅ 完成</span>'
            return '<span class="sb sb-p">🟡 进行</span>'

        def _note(r: Dict) -> str:
            if r.get("is_overdue") and r.get("days_overdue"):
                return f'⚠️ 逾期 {r["days_overdue"]} 天'
            if r.get("pm_status") == "blocked":
                return "阻塞中"
            return "—"

        def _esc(s: str) -> str:
            return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

        rows_html = []
        for i, r in enumerate(rows, 1):
            url = r.get("issue_url") or f"https://github.com/{repo_owner}/{repo_name}/issues/{r.get('issue_number')}"
            title = _esc(r.get("issue_title") or "")
            rows_html.append(
                f'<tr><td class="c-idx">{i}</td>'
                f'<td class="c-task"><a class="link" href="{_esc(url)}">#{r.get("issue_number")}</a> {title}</td>'
                f'<td class="c-owner">{_esc(r.get("assignee") or "—")}</td>'
                f'<td class="c-st">{_st_badge(r)}</td>'
                f'<td class="c-progress">{r.get("progress", 0)}%</td>'
                f'<td class="c-note">{_esc(_note(r))}</td></tr>'
            )
        table_body = "\n      ".join(rows_html)

        risk_cards = []
        for r in blocked:
            risk_cards.append(f'<div class="sc hi"><b>#{r.get("issue_number")} {_esc((r.get("issue_title") or "")[:30])} 🔴</b>当前阻塞，需优先推动</div>')
        for r in overdue[:3]:
            risk_cards.append(f'<div class="sc hi"><b>#{r.get("issue_number")} {_esc((r.get("issue_title") or "")[:30])} ⚠️</b>逾期 {r.get("days_overdue", 0)} 天</div>')
        for r in in_progress[:2]:
            if r not in overdue:
                risk_cards.append(f'<div class="sc mi"><b>#{r.get("issue_number")} {_esc((r.get("issue_title") or "")[:30])}</b>进行中 {r.get("progress", 0)}%</div>')
        for r in rows:
            if r.get("issue_state") == "closed":
                risk_cards.append(f'<div class="sc lo"><b>#{r.get("issue_number")} {_esc((r.get("issue_title") or "")[:30])} ✅</b>已完成</div>')
        risk_html = "\n    ".join(risk_cards[:8])

        title_show = project_tag.replace("project/", "") if project_tag.startswith("project/") else project_tag
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title_show} — 项目看板</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #f0f2f5; color: #1a1a2e; font-size: 12px; }}
    .header {{ background: linear-gradient(135deg, #1a365d 0%, #2d5a87 100%); color: white; padding: 16px 24px; position: sticky; top: 0; z-index: 200; }}
    .header h1 {{ font-size: 17px; font-weight: 600; }}
    .header .subtitle {{ font-size: 11px; opacity: 0.8; margin-top: 3px; }}
    .legend {{ display: flex; gap: 14px; margin-top: 8px; flex-wrap: wrap; }}
    .legend-item {{ display: flex; align-items: center; gap: 4px; font-size: 10px; opacity: 0.9; }}
    .legend-dot {{ width: 14px; height: 10px; border-radius: 2px; }}
    .container {{ padding: 16px; overflow: auto; max-height: calc(100vh - 220px); }}
    table.board {{ border-collapse: collapse; width: 100%; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden; }}
    table.board th, table.board td {{ border: 1px solid #e0e0e0; padding: 8px 10px; text-align: left; }}
    table.board thead th {{ background: #2F5496; color: white; font-size: 11px; font-weight: 500; }}
    table.board tbody tr:hover {{ background: #f5f8ff; }}
    table.board .c-idx {{ width: 36px; text-align: center; color: #666; }}
    table.board .c-task {{ min-width: 200px; }}
    table.board .c-owner {{ width: 90px; color: #555; }}
    table.board .c-st {{ width: 80px; text-align: center; }}
    table.board .c-progress {{ width: 70px; text-align: center; }}
    table.board .c-note {{ min-width: 160px; color: #666; font-size: 11px; }}
    .sb {{ display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 10px; font-weight: 500; }}
    .sb-b {{ background: #fce4e4; color: #c0392b; }}
    .sb-p {{ background: #fff3cd; color: #856404; }}
    .sb-d {{ background: #d4edda; color: #155724; }}
    .summary {{ margin: 16px; padding: 14px; background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
    .summary h3 {{ font-size: 13px; color: #1a365d; margin-bottom: 8px; }}
    .sg {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 8px; }}
    .sc {{ padding: 8px 10px; border-radius: 6px; border-left: 3px solid; font-size: 11px; }}
    .sc.hi {{ border-color: #e74c3c; background: #fef5f5; }}
    .sc.mi {{ border-color: #f39c12; background: #fffbf0; }}
    .sc.lo {{ border-color: #27ae60; background: #f0faf4; }}
    .sc b {{ display: block; margin-bottom: 2px; }}
    .link {{ color: #0969da; text-decoration: none; }}
    .link:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
<div class="header">
  <h1>{title_show} 项目计划 — 看板</h1>
  <div class="subtitle">更新: {snapshot_date} | 共 {total} 项，已完成 {completed} 项，平均进度 {progress_avg}%</div>
  <div class="legend">
    <div class="legend-item"><div class="legend-dot" style="background:#fce4e4"></div>🔴 卡点/阻塞</div>
    <div class="legend-item"><div class="legend-dot" style="background:#fff3cd"></div>🟡 进行中</div>
    <div class="legend-item"><div class="legend-dot" style="background:#d4edda"></div>✅ 完成</div>
  </div>
</div>
<div class="container">
  <table class="board">
    <thead><tr><th class="c-idx">#</th><th class="c-task">任务</th><th class="c-owner">负责人</th><th class="c-st">状态</th><th class="c-progress">进度</th><th class="c-note">备注</th></tr></thead>
    <tbody>
      {table_body}
    </tbody>
  </table>
</div>
<div class="summary">
  <h3>📊 风险评估</h3>
  <div class="sg">
    {risk_html}
  </div>
</div>
</body>
</html>"""

    @staticmethod
    def get_demo_rows(repo_owner: str = "matrixorigin", repo_name: str = "matrixflow") -> List[Dict]:
        """返回用于演示的假数据。"""
        base_url = f"https://github.com/{repo_owner}/{repo_name}/issues"
        return [
            {"issue_number": 9001, "repo_owner": repo_owner, "repo_name": repo_name, "issue_title": "[L1] 问数深化项目", "issue_state": "open", "pm_status": "in_progress", "progress": 80, "assignee": "wupeng", "risk_level": "low", "is_overdue": False, "days_overdue": 0, "issue_url": f"{base_url}/9001"},
            {"issue_number": 9002, "repo_owner": repo_owner, "repo_name": repo_name, "issue_title": "[L3] 单据检索 PRD 设计", "issue_state": "open", "pm_status": "in_progress", "progress": 30, "assignee": "wupeng", "risk_level": "medium", "is_overdue": True, "days_overdue": 3, "issue_url": f"{base_url}/9002"},
            {"issue_number": 9003, "repo_owner": repo_owner, "repo_name": repo_name, "issue_title": "[L3] CRM 接口对接", "issue_state": "open", "pm_status": "blocked", "progress": 10, "assignee": "zhangsan", "risk_level": "high", "is_overdue": False, "days_overdue": 0, "issue_url": f"{base_url}/9003"},
            {"issue_number": 9004, "repo_owner": repo_owner, "repo_name": repo_name, "issue_title": "[L3] SAP 接口对接", "issue_state": "closed", "pm_status": "completed", "progress": 100, "assignee": "lisi", "risk_level": "low", "is_overdue": False, "days_overdue": 0, "issue_url": f"{base_url}/9004"},
            {"issue_number": 9005, "repo_owner": repo_owner, "repo_name": repo_name, "issue_title": "[L4] 合同智能体调用报错 500", "issue_state": "open", "pm_status": "in_progress", "progress": 60, "assignee": "wupeng", "risk_level": "medium", "is_overdue": True, "days_overdue": 1, "issue_url": f"{base_url}/9005"},
        ]

    def _fetch_project_issues(
        self,
        project_tag: str,
        snapshot_date: date,
        repo_owner: Optional[str],
        repo_name: Optional[str],
    ) -> List[Dict]:
        """优先从 project_issues 查；失败或为空则从 issues_snapshot 按标签查。"""
        sql = """
        SELECT issue_number, repo_owner, repo_name, issue_title, issue_state, pm_status,
               progress, assignee, risk_level, is_overdue, days_overdue, issue_url
        FROM project_issues
        WHERE project_tag = :tag AND snapshot_date = :snap
        """
        params = {"tag": project_tag, "snap": snapshot_date}
        if repo_owner:
            sql += " AND repo_owner = :owner"
            params["owner"] = repo_owner
        if repo_name:
            sql += " AND repo_name = :repo"
            params["repo"] = repo_name
        sql += " ORDER BY progress ASC, issue_number ASC"
        try:
            rows = self.storage.execute(sql, params) or []
            if rows:
                return rows
        except Exception:
            pass
        return self._fallback_from_issues_snapshot(project_tag, repo_owner, repo_name)

    def _fallback_from_issues_snapshot(
        self, project_tag: str, repo_owner: Optional[str], repo_name: Optional[str]
    ) -> List[Dict]:
        """从 issues_snapshot 取最新快照中带 project_tag 的 Issue，用于 project_issues 未就绪时。"""
        sub_where = "1=1"
        params = {"tag1": f"%{project_tag}%", "tag2": f'%"{project_tag}"%'}
        if repo_owner:
            sub_where += " AND repo_owner = :owner"
            params["owner"] = repo_owner
        if repo_name:
            sub_where += " AND repo_name = :repo"
            params["repo"] = repo_name
        sql = f"""
        SELECT i.issue_number, i.repo_owner, i.repo_name, i.title AS issue_title, i.state AS issue_state,
               COALESCE(i.progress_percentage, 0) AS progress, i.assignee,
               'low' AS risk_level, 0 AS days_overdue,
               CONCAT('https://github.com/', i.repo_owner, '/', i.repo_name, '/issues/', i.issue_number) AS issue_url
        FROM issues_snapshot i
        INNER JOIN (
            SELECT repo_owner, repo_name, MAX(snapshot_time) AS mt
            FROM issues_snapshot
            WHERE {sub_where}
        ) t ON i.repo_owner = t.repo_owner AND i.repo_name = t.repo_name AND i.snapshot_time = t.mt
        WHERE (i.labels LIKE :tag1 OR i.labels LIKE :tag2)
        ORDER BY i.progress_percentage ASC, i.issue_number ASC
        """
        try:
            rows = self.storage.execute(sql, params) or []
            for r in rows:
                r["pm_status"] = "completed" if (r.get("issue_state") == "closed") else "in_progress"
                r["is_overdue"] = False
            return rows
        except Exception:
            return []

    def _empty_dashboard(self, project_tag: str, snapshot_date: date) -> str:
        return f"# 项目看板 · {project_tag}\n**日期**: {snapshot_date}\n\n暂无带该项目标签的 Issue 数据。请先执行项目同步（sync_project_issues），或确保 issues_snapshot 中有带该标签的 Issue。\n"

    def _get_ai_summary(
        self,
        rows: List[Dict],
        overdue: List[Dict],
        blocked: List[Dict],
        progress_avg: int,
    ) -> Optional[str]:
        if not self.llm:
            return None
        prompt = f"""
当前项目共 {len(rows)} 项，平均进度 {progress_avg}%，逾期 {len(overdue)} 项，阻塞 {len(blocked)} 项。
请用 2～4 句话给出简要风险与建议（如：需关注逾期项、建议优先解决阻塞等）。不要输出 markdown 标题，只输出段落。
"""
        try:
            return self.llm._call_ai("你是项目看板助手，输出简短中文总结。", prompt)
        except Exception:
            return None
