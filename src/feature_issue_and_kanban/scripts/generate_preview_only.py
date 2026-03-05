#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
纯预览脚本：只根据标题/正文写 HTML，不依赖数据库和 AI。
完整展示：Labels（多种 tag）、Type、层级、项目、里程碑、负责人等，贴近 GitHub Issue 字段。
"""
import argparse
import html
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = ROOT / "feature_issue_and_kanban" / "templates"

# Issue 类型 -> 正文模板文件名（与 templates/*.md 对应）
TYPE_TO_TEMPLATE = {
    "Doc Request": "Doc_Request.md",
    "Customer Project": "Customer_Project.md",
    "MO Feature": "MO_Feature.md",
    "MO Bug": "MO_Bug.md",
    "MOI Feature": "MOI_Feature.md",
    "MOI Bug": "MOI_Bug.md",
    "MOI SubTask": "MOI_SubTask.md",
    "Test Request": "Test_Request.md",
    "EE Feature": "EE_Feature.md",
    "User Bug": "User_Bug.md",
}


def _load_body_template(issue_type: str) -> str:
    """根据类型加载正文模板，找不到则返回空字符串。"""
    fname = TYPE_TO_TEMPLATE.get((issue_type or "").strip())
    if not fname:
        return ""
    path = TEMPLATES_DIR / fname
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


def _body_to_html(md: str) -> str:
    if not md:
        return ""
    s = html.escape(md)
    return "<p>" + s.replace("\n\n", "</p><p>").replace("\n", "<br>\n") + "</p>"


def _group_labels(labels):
    """按前缀分组：kind/, area/, project/, severity/, 其他"""
    groups = defaultdict(list)
    for l in labels:
        if "/" in l:
            prefix = l.split("/", 1)[0] + "/"
            groups[prefix].append(l)
        else:
            groups["其他"].append(l)
    order = ["kind/", "area/", "project/", "severity/", "priority/", "其他"]
    return [(k, groups[k]) for k in order if groups[k]] + [(k, groups[k]) for k in sorted(groups) if k not in order]


def _pill(lab, css_class=""):
    c = f' class="label-pill {css_class}"' if css_class else ' class="label-pill"'
    return f'<span{c}>{html.escape(lab)}</span>'


def main():
    parser = argparse.ArgumentParser(description="仅生成预览 HTML，不调用 AI/DB")
    parser.add_argument("--repo", required=True, help="owner/name，如 matrixorigin/matrixflow")
    parser.add_argument("--title", required=True, help="Issue 标题")
    parser.add_argument("--body", default="", help="Issue 正文（支持多行）")
    parser.add_argument("--level", default="", help="层级：L1/L2/L3/L4")
    parser.add_argument("--type", "--issue-type", dest="issue_type", default="", help="Issue 类型（模版），如 Doc Request, MOI Feature")
    parser.add_argument("--labels", default="", help="逗号分隔的 Labels/tags，如 kind/docs,area/问数,project/问数深化")
    parser.add_argument("--assignees", default="", help="逗号分隔负责人")
    parser.add_argument("--milestone", default="", help="里程碑")
    parser.add_argument("--project", default="", help="项目（若未在 labels 里写 project/xxx 可单独填）")
    parser.add_argument("--priority", default="", help="优先级，如 P0/P1")
    parser.add_argument("--output-html", required=True, help="输出 HTML 路径")
    parser.add_argument("--success-msg", action="store_true", help="在 HTML 顶部显示「生成成功」")
    args = parser.parse_args()
    parts = args.repo.strip().split("/")
    if len(parts) != 2:
        print("--repo 格式应为 owner/name", file=sys.stderr)
        sys.exit(1)
    repo_owner, repo_name = parts[0], parts[1]
    labels = [x.strip() for x in args.labels.split(",") if x.strip()]
    if args.project and not any(l.startswith("project/") for l in labels):
        labels.append("project/" + args.project.strip())
    assignees = [x.strip() for x in args.assignees.split(",") if x.strip()]
    level = (args.level or "").strip()
    issue_type = (args.issue_type or "").strip()
    milestone = (args.milestone or "").strip()
    priority = (args.priority or "").strip()
    body = (args.body or "").strip()
    body_from_template = False
    if issue_type and (not body or body == (args.title or "").strip()):
        template = _load_body_template(issue_type)
        if template:
            body = template
            body_from_template = True
    body_html = _body_to_html(body)
    success_banner = ""
    if args.success_msg:
        success_banner = '''<div class="success-banner">✓ 生成成功，请确认下方所有标签与信息。确认无误后在聊天窗口说「确认无误」由 AI 提交到 GitHub。</div>'''
    repo_url = f"https://github.com/{repo_owner}/{repo_name}"
    assignee_line = ", ".join(html.escape(a) for a in assignees) if assignees else '<span class="meta-muted">未指定</span>'

    # 右侧栏：1) Labels（按分组） 2) Type  3) 其他信息表
    label_groups = _group_labels(labels)
    labels_html = ""
    for prefix, grp in label_groups:
        name = "Labels · " + prefix.rstrip("/") if prefix != "其他" else "Labels · 其他"
        labels_html += f'<div class="label-group"><span class="label-group-name">{html.escape(name)}</span><div class="label-pills">{" ".join(_pill(l) for l in grp)}</div></div>'
    if not labels_html:
        labels_html = '<div class="meta-muted">暂无标签，可在聊天中补充 --labels "kind/xxx,area/xxx,project/xxx"</div>'

    type_html = html.escape(issue_type) if issue_type else '<span class="meta-muted">未选</span>'
    extra_rows = [
        ("层级", html.escape(level) if level else "—", "L1/L2/L3/L4"),
        ("Type（Issue 类型）", type_html, "Doc Request, MOI Feature, MOI SubTask 等"),
        ("负责人", assignee_line, ""),
        ("里程碑", html.escape(milestone) if milestone else "—", ""),
        ("优先级", html.escape(priority) if priority else "—", "P0/P1/P2"),
    ]
    template_hint = ""
    if body_from_template and issue_type:
        template_hint = f'<p class="meta-muted" style="font-size:12px;margin-top:8px;">当前正文已按「{html.escape(issue_type)}」类型模板生成，可在聊天中说明要修改的段落。</p>'
    extra_table = "".join(
        f'<tr><td class="extra-name">{html.escape(name)}</td><td>{val}</td><td class="meta-muted">{html.escape(hint)}</td></tr>'
        for name, val, hint in extra_rows
    )
    # 标题下方整行展示所有 label pills
    all_pills = " ".join(_pill(l) for l in labels) if labels else '<span class="meta-muted">无</span>'
    if issue_type:
        all_pills = _pill(issue_type, "type") + " " + all_pills
    if level:
        all_pills = _pill("层级:" + level, "level") + " " + all_pills

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Issue 预览 · {html.escape(args.title[:50])}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif; font-size: 14px; line-height: 1.5; color: #1f2328; background: #f6f8fa; margin: 0; padding: 24px; }}
    .container {{ max-width: 1280px; margin: 0 auto; display: flex; gap: 24px; flex-wrap: wrap; }}
    .main {{ flex: 1; min-width: 0; background: #fff; border: 1px solid #d0d7de; border-radius: 6px; }}
    .sidebar {{ width: 300px; flex-shrink: 0; }}
    .box {{ background: #fff; border: 1px solid #d0d7de; border-radius: 6px; padding: 16px; margin-bottom: 16px; }}
    .box-title {{ font-weight: 600; margin-bottom: 12px; color: #1f2328; font-size: 14px; }}
    .success-banner {{ background: #dafbe1; color: #1a7f37; border: 1px solid #2da44e; padding: 12px 16px; border-radius: 6px; margin-bottom: 16px; }}
    .issue-header {{ padding: 16px 24px; border-bottom: 1px solid #d0d7de; }}
    .issue-title {{ font-size: 24px; font-weight: 600; margin: 0 0 8px 0; }}
    .issue-meta {{ display: flex; flex-wrap: wrap; gap: 16px; align-items: center; color: #57606a; font-size: 14px; margin-top: 8px; }}
    .label-pill {{ display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 12px; margin-right: 6px; margin-bottom: 4px; background: #ddf4ff; color: #0969da; }}
    .label-pill.type {{ background: #dafbe1; color: #1a7f37; }}
    .label-pill.level {{ background: #fff8e5; color: #9a6700; }}
    .label-pills {{ margin-top: 4px; }}
    .label-group {{ margin-bottom: 12px; }}
    .label-group-name {{ font-size: 12px; color: #57606a; display: block; margin-bottom: 4px; }}
    .meta-muted {{ color: #8c959f; }}
    .issue-body {{ padding: 24px; }}
    .issue-body p {{ margin: 0 0 12px 0; }}
    .repo-link {{ color: #0969da; text-decoration: none; }}
    .repo-link:hover {{ text-decoration: underline; }}
    .extra-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    .extra-table td {{ padding: 6px 8px; border-bottom: 1px solid #d0d7de; vertical-align: top; }}
    .extra-name {{ color: #57606a; width: 100px; }}
  </style>
</head>
<body>
  {success_banner}
  <div class="container">
    <div class="main">
      <div class="issue-header">
        <h1 class="issue-title">{html.escape(args.title)}</h1>
        <div class="issue-meta">
          <span>仓库 <a class="repo-link" href="{html.escape(repo_url)}">{html.escape(repo_owner + "/" + repo_name)}</a></span>
          <span>·</span>
          <span>负责人 {assignee_line}</span>
        </div>
        <div class="issue-meta" style="margin-top: 12px;">{all_pills}</div>
      </div>
      <div class="issue-body">
        {body_html}
      </div>
    </div>
    <div class="sidebar">
      <div class="box">
        <div class="box-title">Labels（标签 / Tags）</div>
        {labels_html}
      </div>
      <div class="box">
        <div class="box-title">Type · 层级 · 其他信息</div>
        <table class="extra-table">
          <tbody>{extra_table}</tbody>
        </table>
        {template_hint}
      </div>
    </div>
  </div>
</body>
</html>
"""
    out = Path(args.output_html)
    if not out.is_absolute():
        out = ROOT / out
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_content, encoding="utf-8")
    print("PREVIEW_OK", str(out))
    return str(out)


if __name__ == "__main__":
    main()
