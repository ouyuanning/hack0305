#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件发送模块
功能：将分析报告通过邮件发送给指定收件人
"""

import sys
import os
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))
from config.config import (
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
    EMAIL_FROM, EMAIL_FROM_NAME, REPORT_OUTPUT_DIR
)


class EmailSender:
    """邮件发送器"""
    
    def __init__(self):
        self.smtp_host = SMTP_HOST
        self.smtp_port = SMTP_PORT
        self.smtp_user = SMTP_USER
        self.smtp_password = SMTP_PASSWORD
        self.email_from = EMAIL_FROM
        self.email_from_name = EMAIL_FROM_NAME
    
    def format_comprehensive_report_html(self, report: Dict) -> str:
        """
        生成包含可扩展分析结果的HTML邮件（标签、模块、客户等）
        """
        results = report.get('analysis_results', {})
        repo = report.get('repo', 'N/A')
        generated_at = report.get('generated_at', datetime.now().isoformat())
        total_issues = report.get('total_issues', 0)

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 900px; margin: 0 auto; padding: 20px; background-color: #f5f5f5; }}
        .container {{ background-color: white; border-radius: 8px; padding: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #24292e; border-bottom: 3px solid #0366d6; padding-bottom: 10px; }}
        h2 {{ color: #0366d6; margin-top: 30px; border-bottom: 1px solid #e1e4e8; padding-bottom: 5px; }}
        h3 {{ color: #586069; margin-top: 20px; }}
        .summary-box {{ background-color: #f6f8fa; border: 1px solid #e1e4e8; border-radius: 6px; padding: 20px; margin: 20px 0; }}
        .stat-row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #e1e4e8; }}
        .stat-row:last-child {{ border-bottom: none; }}
        .stat-label {{ font-weight: 600; color: #586069; }}
        .stat-value {{ font-weight: bold; color: #24292e; font-size: 1.1em; }}
        .stat-value.high {{ color: #d73a49; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e1e4e8; }}
        th {{ background-color: #f6f8fa; font-weight: 600; color: #24292e; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #e1e4e8; color: #586069; font-size: 0.9em; text-align: center; }}
        .badge.high {{ background-color: #d73a49; color: white; padding: 2px 6px; border-radius: 3px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 GitHub Issue 综合分析报告</h1>
        <p><strong>仓库：</strong>{repo}</p>
        <p><strong>生成时间：</strong>{generated_at[:19] if isinstance(generated_at, str) and len(generated_at) > 19 else generated_at}</p>

        <h2>📈 总体概览</h2>
        <div class="summary-box">
            <div class="stat-row">
                <span class="stat-label">总Issue数</span>
                <span class="stat-value">{total_issues}</span>
            </div>
        </div>
"""

        # 标签分析
        if 'label_analysis' in results and 'error' not in results['label_analysis']:
            ld = results['label_analysis']
            html += f"""
        <h2>🏷️ 标签分析</h2>
        <div class="summary-box">
            <div class="stat-row">
                <span class="stat-label">唯一标签总数</span>
                <span class="stat-value">{ld.get('total_unique_labels', 0)}</span>
            </div>
        </div>
"""
            categories = ld.get('label_categories', {})
            if categories:
                html += "        <h3>按类别分组</h3>\n        <table>\n            <tr><th>类别</th><th>标签</th><th>数量</th></tr>\n"
                for cat_name, labels in categories.items():
                    for label, count in list(labels.items())[:5]:
                        html += f"            <tr><td>{cat_name}</td><td><code>{label}</code></td><td><strong>{count}</strong></td></tr>\n"
                html += "        </table>\n"

        # 功能模块分析
        if 'module_analysis' in results and 'error' not in results['module_analysis']:
            md = results['module_analysis']
            html += f"""
        <h2>🔧 功能模块分析</h2>
        <p>共识别 <strong>{md.get('total_modules', 0)}</strong> 个功能模块</p>
        <table>
            <tr><th>模块</th><th>总Issue</th><th>Open</th><th>Bug比例</th><th>P0数量</th></tr>
"""
            for m in md.get('top_modules', [])[:10]:
                br = m.get('bug_ratio', 0)
                p0 = m.get('p0_count', 0)
                p0_class = ' class="stat-value high"' if p0 > 0 else ''
                html += f"            <tr><td><strong>{m.get('module', 'N/A')}</strong></td><td>{m.get('total_issues', 0)}</td><td>{m.get('open_issues', 0)}</td><td>{br*100:.1f}%</td><td{p0_class}>{p0}</td></tr>\n"
            html += "        </table>\n"

        # 客户分析
        if 'customer_analysis' in results and 'error' not in results['customer_analysis']:
            cd = results['customer_analysis']
            by_customer = cd.get('by_customer', {})
            if by_customer:
                html += f"""
        <h2>👥 客户项目分析</h2>
        <p>共 <strong>{len(cd.get('customers', []))}</strong> 个客户项目</p>
        <table>
            <tr><th>客户</th><th>总Issue</th><th>完成率</th></tr>
"""
                for cname, cdata in list(by_customer.items())[:10]:
                    cr = cdata.get('completion_rate', 0)
                    html += f"            <tr><td><strong>{cname}</strong></td><td>{cdata.get('total_issues', 0)}</td><td>{cr*100:.1f}%</td></tr>\n"
                html += "        </table>\n"

        # 基础统计
        if 'basic_stats' in results and 'error' not in results['basic_stats']:
            basic = results['basic_stats']
            html += """
        <h2>📊 基础统计</h2>
        <table>
            <tr><th>维度</th><th>类别</th><th>数量</th><th>百分比</th></tr>
"""
            for state, data in basic.get('by_state', {}).items():
                if isinstance(data, dict):
                    html += f"            <tr><td>状态</td><td>{state}</td><td>{data.get('count', data)}</td><td>{data.get('percentage', '-')}%</td></tr>\n"
                else:
                    html += f"            <tr><td>状态</td><td>{state}</td><td>{data}</td><td>-</td></tr>\n"
            html += "        </table>\n"

        # LLM 洞察分析
        if 'llm_insights' in results and 'error' not in results['llm_insights']:
            li = results['llm_insights']
            insights_text = li.get('insights') or li.get('raw_response', '')
            if insights_text:
                # 将换行转为 HTML 段落
                paragraphs = [f"<p>{p.strip()}</p>" for p in insights_text.split('\n') if p.strip()]
                insights_html = '\n        '.join(paragraphs) if paragraphs else f"<p>{insights_text}</p>"
                html += f"""
        <h2>🤖 大模型洞察与建议</h2>
        <div class="summary-box" style="white-space: pre-wrap;">
        {insights_html}
        </div>
"""
        elif 'llm_insights' in results and 'error' in results['llm_insights']:
            html += f"""
        <h2>🤖 大模型洞察</h2>
        <p><em>本次未生成：{results['llm_insights'].get('error', '未知错误')}</em></p>
"""

        html += f"""
        <div class="footer">
            <p>本报告由 GitHub Issue 智能管理系统自动生成（含可扩展分析）</p>
            <p>报告时间：{generated_at[:19] if isinstance(generated_at, str) and len(generated_at) > 19 else generated_at}</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    def format_report_html(self, daily_report: Dict, progress_report: Dict, repo_owner: str, repo_name: str) -> str:
        """
        将报告格式化为HTML格式
        
        输入参数：
        - daily_report: 日报数据
        - progress_report: 进度报告数据
        - repo_owner: 仓库所有者
        - repo_name: 仓库名称
        
        输出：
        - str: HTML格式的报告内容
        """
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #24292e;
            border-bottom: 3px solid #0366d6;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #0366d6;
            margin-top: 30px;
            border-bottom: 1px solid #e1e4e8;
            padding-bottom: 5px;
        }}
        .summary-box {{
            background-color: #f6f8fa;
            border: 1px solid #e1e4e8;
            border-radius: 6px;
            padding: 20px;
            margin: 20px 0;
        }}
        .stat-row {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #e1e4e8;
        }}
        .stat-row:last-child {{
            border-bottom: none;
        }}
        .stat-label {{
            font-weight: 600;
            color: #586069;
        }}
        .stat-value {{
            font-weight: bold;
            color: #24292e;
            font-size: 1.1em;
        }}
        .stat-value.high {{
            color: #d73a49;
        }}
        .stat-value.medium {{
            color: #fb8500;
        }}
        .stat-value.low {{
            color: #28a745;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e1e4e8;
        }}
        th {{
            background-color: #f6f8fa;
            font-weight: 600;
            color: #24292e;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e1e4e8;
            color: #586069;
            font-size: 0.9em;
            text-align: center;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 0.85em;
            font-weight: 600;
        }}
        .badge.open {{
            background-color: #28a745;
            color: white;
        }}
        .badge.closed {{
            background-color: #6a737d;
            color: white;
        }}
        .badge.blocked {{
            background-color: #d73a49;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 GitHub Issue 分析报告</h1>
        <p><strong>仓库：</strong>{repo_owner}/{repo_name}</p>
        <p><strong>生成时间：</strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>📈 日报摘要</h2>
        <div class="summary-box">
"""
        
        if 'error' not in daily_report:
            summary = daily_report.get('summary', {})
            html += f"""
            <div class="stat-row">
                <span class="stat-label">总Issue数</span>
                <span class="stat-value">{summary.get('total_issues', 0)}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">开放Issue</span>
                <span class="stat-value">{summary.get('open_issues', 0)}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">已关闭Issue</span>
                <span class="stat-value">{summary.get('closed_issues', 0)}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">阻塞Issue</span>
                <span class="stat-value {'high' if summary.get('blocked_issues', 0) > 0 else 'low'}">{summary.get('blocked_issues', 0)}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">今日新增</span>
                <span class="stat-value">{summary.get('new_today', 0)}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">今日关闭</span>
                <span class="stat-value">{summary.get('closed_today', 0)}</span>
            </div>
"""
        else:
            html += f"<p>⚠️ {daily_report.get('error', '无法生成日报')}</p>"
        
        html += """
        </div>
        
        <h2>📊 进度统计</h2>
"""
        
        if 'error' not in progress_report:
            # 按状态统计
            by_status = progress_report.get('by_status', {})
            if by_status:
                html += """
        <h3>按状态分布</h3>
        <table>
            <thead>
                <tr>
                    <th>状态</th>
                    <th>数量</th>
                </tr>
            </thead>
            <tbody>
"""
                for status, count in by_status.items():
                    html += f"""
                <tr>
                    <td>{status}</td>
                    <td>{count}</td>
                </tr>
"""
                html += """
            </tbody>
        </table>
"""
            
            # 按类型统计
            by_type = progress_report.get('by_type', {})
            if by_type:
                html += """
        <h3>按类型分布</h3>
        <table>
            <thead>
                <tr>
                    <th>类型</th>
                    <th>数量</th>
                </tr>
            </thead>
            <tbody>
"""
                for issue_type, count in by_type.items():
                    html += f"""
                <tr>
                    <td>{issue_type}</td>
                    <td>{count}</td>
                </tr>
"""
                html += """
            </tbody>
        </table>
"""
            
            # 按优先级统计
            by_priority = progress_report.get('by_priority', {})
            if by_priority:
                html += """
        <h3>按优先级分布</h3>
        <table>
            <thead>
                <tr>
                    <th>优先级</th>
                    <th>数量</th>
                </tr>
            </thead>
            <tbody>
"""
                for priority, count in by_priority.items():
                    priority_class = 'high' if priority in ['high', 'urgent', 'critical'] else ('medium' if priority == 'medium' else 'low')
                    html += f"""
                <tr>
                    <td><span class="stat-value {priority_class}">{priority}</span></td>
                    <td>{count}</td>
                </tr>
"""
                html += """
            </tbody>
        </table>
"""
        else:
            html += f"<p>⚠️ {progress_report.get('error', '无法生成进度报告')}</p>"
        
        html += f"""
        <div class="footer">
            <p>本报告由 GitHub Issue 智能管理系统自动生成</p>
            <p>报告时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    def format_ai_analysis_section(self, ai_analysis_report: Dict) -> str:
        """
        生成 AI 驱动分析结果的 HTML 片段（项目推进+横向关联）
        支持多仓库，按 order 顺序展示（默认 matrixflow 优先）
        """
        if not ai_analysis_report:
            return ""
        by_repo = ai_analysis_report.get("by_repo") or {}
        order = ai_analysis_report.get("order") or list(by_repo.keys())
        html = ""
        for repo_key in order:
            if repo_key not in by_repo:
                continue
            data = by_repo[repo_key]
            proj = data.get("project_progress") or {}
            cross = data.get("cross_patterns") or {}
            html += f"""
        <h2>📦 仓库：{repo_key}</h2>
"""
            customers = proj.get("customers") or {}
            if customers:
                html += """
        <h3>🤖 项目推进分析</h3>
"""
                for cname, cdata in customers.items():
                    ai_insights = cdata.get("ai_insights") or {}
                    if "error" in ai_insights:
                        html += f"""
        <h4>客户：{cname}</h4>
        <p><em>AI 分析未完成：{ai_insights.get('error', '未知')}</em></p>
"""
                        continue
                    health_score = ai_insights.get("health_score", 0)
                    health_level = ai_insights.get("health_level", "")
                    health_color = "#28a745" if health_score >= 80 else "#ffc107" if health_score >= 60 else "#dc3545"
                    html += f"""
        <h4>客户：{cname}</h4>
        <div class="summary-box">
            <div class="stat-row">
                <span class="stat-label">健康度</span>
                <span class="stat-value" style="color:{health_color}">{health_score}/100 ({health_level})</span>
            </div>
        </div>
"""
                    findings = ai_insights.get("key_findings") or []
                    if findings:
                        html += "        <h5>关键发现</h5>\n        <ul>\n"
                        for f in findings[:5]:
                            html += f"            <li>{f}</li>\n"
                        html += "        </ul>\n"
                    recs = ai_insights.get("recommendations") or []
                    if recs:
                        html += "        <h5>建议行动</h5>\n        <ul>\n"
                        for r in recs[:5]:
                            html += f"            <li>{r}</li>\n"
                        html += "        </ul>\n"
                    urgent = ai_insights.get("urgent_actions") or []
                    if urgent:
                        html += '        <div class="summary-box" style="background-color:#fff3cd;border-left:4px solid #ffc107;padding:15px;">\n            <h5>⚠️ 需立即处理</h5>\n            <ul>\n'
                        for u in urgent[:3]:
                            html += f"                <li><strong>{u}</strong></li>\n"
                        html += "            </ul>\n        </div>\n"
            # 横向关联分析
            ai_patterns = cross.get("ai_patterns") or {}
            if ai_patterns and "error" not in ai_patterns:
                html += """
        <h3>🔗 横向关联分析</h3>
"""
                if ai_patterns.get("common_needs_pattern"):
                    html += f"""
        <h4>共性需求模式</h4>
        <p>{ai_patterns.get('common_needs_pattern')}</p>
"""
                if ai_patterns.get("strategic_recommendations"):
                    html += "        <h4>战略建议</h4>\n        <ul>\n"
                    for r in ai_patterns.get("strategic_recommendations", [])[:5]:
                        html += f"            <li>{r}</li>\n"
                    html += "        </ul>\n"
                ra = ai_patterns.get("resource_allocation") or {}
                if ra.get("should_prioritize"):
                    html += "        <h4>建议优先投入</h4>\n        <ul>\n"
                    for p in ra.get("should_prioritize", [])[:5]:
                        html += f"            <li>{p}</li>\n"
                    html += "        </ul>\n"
        return html
    
    def send_report(
        self,
        to_email: str,
        daily_report: Dict,
        progress_report: Dict,
        repo_owner: str,
        repo_name: str,
        attach_json: bool = True,
        comprehensive_report: Optional[Dict] = None,
        ai_analysis_report: Optional[Dict] = None
    ) -> bool:
        """
        发送分析报告邮件

        输入参数：
        - to_email: 收件人邮箱
        - daily_report: 日报数据
        - progress_report: 进度报告数据
        - repo_owner: 仓库所有者
        - repo_name: 仓库名称
        - attach_json: 是否附加JSON格式的报告文件
        - comprehensive_report: 可扩展分析报告（可选），若提供则邮件使用综合分析内容
        - ai_analysis_report: AI 驱动分析报告（可选），含 project_progress、cross_patterns

        输出：
        - bool: 是否发送成功
        """
        try:
            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.email_from_name} <{self.email_from}>"
            msg['To'] = to_email
            msg['Subject'] = f"GitHub Issue 分析报告 - {repo_owner}/{repo_name} - {datetime.now().strftime('%Y-%m-%d')}"

            # 生成HTML内容：优先使用可扩展分析报告
            if comprehensive_report and comprehensive_report.get('analysis_results'):
                html_content = self.format_comprehensive_report_html(comprehensive_report)
            else:
                html_content = self.format_report_html(daily_report, progress_report, repo_owner, repo_name)
            # 若有 AI 驱动分析结果，插入到页脚前
            if ai_analysis_report:
                ai_section = self.format_ai_analysis_section(ai_analysis_report)
                if ai_section:
                    html_content = html_content.replace(
                        '<div class="footer">',
                        ai_section + '\n        <div class="footer">'
                    )
            
            # 添加HTML内容
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # 附加JSON报告文件（可选）
            if attach_json:
                # 查找最新的报告文件
                report_files = list(REPORT_OUTPUT_DIR.glob(f"*{repo_owner}_{repo_name}*.json"))
                if report_files:
                    latest_file = max(report_files, key=lambda p: p.stat().st_mtime)
                    with open(latest_file, 'rb') as f:
                        attachment = MIMEBase('application', 'json')
                        attachment.set_payload(f.read())
                        encoders.encode_base64(attachment)
                        attachment.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {latest_file.name}'
                        )
                        msg.attach(attachment)
            
            # 发送邮件
            print(f"📧 正在发送邮件到 {to_email}...")
            
            if self.smtp_port == 465:
                # SSL连接
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
            else:
                # TLS连接
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
            
            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)
            
            server.send_message(msg)
            server.quit()
            
            print(f"✅ 邮件已成功发送到 {to_email}")
            return True
            
        except Exception as e:
            print(f"❌ 发送邮件失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def send_report_multi_repos(
        self,
        to_email: str,
        reports_per_repo: List[Dict],
        ai_analysis_report: Optional[Dict] = None,
        attach_json: bool = True
    ) -> bool:
        """
        多仓库合并一封邮件：先按仓库分开展示（每个仓库的日报+进度+可扩展），最后是 AI 合在一起分析。
        reports_per_repo: 列表，每项为 {
            "repo_owner": str, "repo_name": str,
            "daily_report": Dict, "progress_report": Dict,
            "comprehensive_report": Optional[Dict]
        }
        """
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.email_from_name} <{self.email_from}>"
            msg['To'] = to_email
            repo_names = [f"{r['repo_owner']}/{r['repo_name']}" for r in reports_per_repo]
            msg['Subject'] = f"GitHub Issue 分析报告 - {' + '.join(repo_names)} - {datetime.now().strftime('%Y-%m-%d')}"

            def _body_content(full_html: str) -> str:
                beg = full_html.find("<body>")
                end = full_html.find("</body>")
                if beg == -1 or end == -1:
                    return full_html
                return full_html[beg + 6 : end].strip()

            html_parts = []
            for r in reports_per_repo:
                owner, name = r.get('repo_owner', ''), r.get('repo_name', '')
                daily_report = r.get('daily_report') or {}
                progress_report = r.get('progress_report') or {}
                comprehensive_report = r.get('comprehensive_report')
                if comprehensive_report and comprehensive_report.get('analysis_results'):
                    block = _body_content(self.format_comprehensive_report_html(comprehensive_report))
                else:
                    block = _body_content(self.format_report_html(daily_report, progress_report, owner, name))
                html_parts.append(f'<div class="container" style="margin-bottom:40px;">{block}</div>')

            html_body = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 900px; margin: 0 auto; padding: 20px; background-color: #f5f5f5; }
        .container { background-color: white; border-radius: 8px; padding: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #24292e; padding-bottom: 10px; }
        h2 { color: #0366d6; margin-top: 30px; border-bottom: 1px solid #e1e4e8; padding-bottom: 5px; }
        h3 { color: #586069; margin-top: 20px; }
        .summary-box { background-color: #f6f8fa; border: 1px solid #e1e4e8; border-radius: 6px; padding: 20px; margin: 20px 0; }
        .stat-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #e1e4e8; }
        .stat-row:last-child { border-bottom: none; }
        .stat-label { font-weight: 600; color: #586069; }
        .stat-value { font-weight: bold; color: #24292e; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e1e4e8; }
        th { background-color: #f6f8fa; font-weight: 600; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #e1e4e8; color: #586069; font-size: 0.9em; text-align: center; }
    </style>
</head>
<body>
"""
            html_body += '\n'.join(html_parts)
            if ai_analysis_report:
                ai_section = self.format_ai_analysis_section(ai_analysis_report)
                if ai_section:
                    html_body += f'<div class="container" style="margin-bottom:40px;"><h1 style="border-bottom:3px solid #0366d6;">🤖 合在一起分析（AI）</h1>{ai_section}</div>'
            html_body += '\n        <div class="footer">GitHub Issue 智能管理系统 · 多仓库合并报告</div>\n</body>\n</html>'

            msg.attach(MIMEText(html_body, 'html', 'utf-8'))

            if attach_json:
                for r in reports_per_repo:
                    owner, name = r.get('repo_owner', ''), r.get('repo_name', '')
                    report_files = list(REPORT_OUTPUT_DIR.glob(f"*{owner}_{name}*.json"))
                    if report_files:
                        latest_file = max(report_files, key=lambda p: p.stat().st_mtime)
                        with open(latest_file, 'rb') as f:
                            attachment = MIMEBase('application', 'json')
                            attachment.set_payload(f.read())
                            encoders.encode_base64(attachment)
                            attachment.add_header('Content-Disposition', f'attachment; filename= {latest_file.name}')
                            msg.attach(attachment)

            print(f"📧 正在发送邮件到 {to_email}（多仓库合并）...")
            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
            server.quit()
            print(f"✅ 邮件已成功发送到 {to_email}")
            return True
        except Exception as e:
            print(f"❌ 发送邮件失败: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    # 测试代码
    sender = EmailSender()
    
    # 测试数据
    daily_report = {
        "date": "2025-02-21",
        "repo": "test/repo",
        "summary": {
            "total_issues": 100,
            "open_issues": 50,
            "closed_issues": 50,
            "blocked_issues": 5,
            "new_today": 3,
            "closed_today": 2
        }
    }
    
    progress_report = {
        "repo": "test/repo",
        "by_status": {"待处理": 20, "处理中": 30, "已关闭": 50},
        "by_type": {"bug": 30, "feature": 40, "task": 30},
        "by_priority": {"high": 10, "medium": 30, "low": 60}
    }
    
    # 测试发送（需要配置SMTP）
    # sender.send_report("test@example.com", daily_report, progress_report, "test", "repo")
