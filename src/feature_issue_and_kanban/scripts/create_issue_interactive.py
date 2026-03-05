#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交互式 / 单轮 AI 创建 Issue。
用法（在项目根目录执行）:
  python3 feature_issue_and_kanban/scripts/create_issue_interactive.py --input "描述" --repo matrixorigin/matrixflow --preview --output-html feature_issue_and_kanban/preview.html
"""
import sys
import traceback
from pathlib import Path

# 项目根目录（脚本在 feature_issue_and_kanban/scripts/ 下）
ROOT = Path(__file__).resolve().parents[2]
ERROR_FILE = ROOT / "feature_issue_and_kanban" / "last_error.txt"
PREVIEW_DIR = ROOT / "feature_issue_and_kanban"

def _write_preview_html(content: str, output_path: Path) -> None:
    out = output_path if output_path.is_absolute() else ROOT / output_path
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")

# 在任何可能失败的 import 之前，先根据命令行写出预览占位页
if "--output-html" in sys.argv:
    try:
        i = sys.argv.index("--output-html")
        if i + 1 < len(sys.argv):
            _write_preview_html(
                """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><title>Issue 预览</title></head><body><p>正在生成草稿…请查看终端。若长时间无更新，请打开同目录下 last_error.txt 查看报错。</p></body></html>""",
                Path(sys.argv[i + 1]),
            )
    except Exception:
        pass

import json
import argparse
import html
from typing import Optional

# 若下面 import 项目模块失败，会把报错写入 last_error.txt 并更新预览页

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def _ensure_preview_path(output_html: Optional[Path]) -> Optional[Path]:
    if not output_html:
        return None
    out = Path(output_html)
    if not out.is_absolute():
        out = ROOT / out
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    placeholder = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><title>Issue 预览 - 生成中</title></head><body><p>正在生成草稿，请稍候…若长时间无更新，请查看终端报错。</p></body></html>"""
    out.write_text(placeholder, encoding="utf-8")
    return out

try:
    from config.config import GITHUB_TOKEN, GITHUB_API_BASE_URL
    from modules.database_storage.mo_client import MOStorage
    from modules.llm_parser.llm_parser import LLMParser
    sys.path.insert(0, str(ROOT / "feature_issue_and_kanban"))
    from issue_creator.ai_issue_generator import AIIssueGenerator
    from issue_creator.github_issue_creator import create_issue_on_github
except Exception as e:
    err_msg = traceback.format_exc()
    try:
        ERROR_FILE.parent.mkdir(parents=True, exist_ok=True)
        ERROR_FILE.write_text(err_msg, encoding="utf-8")
    except Exception:
        pass
    if "--output-html" in sys.argv and sys.argv.index("--output-html") + 1 < len(sys.argv):
        try:
            out = Path(sys.argv[sys.argv.index("--output-html") + 1])
            if not out.is_absolute():
                out = ROOT / out
            out = out.resolve()
            err_html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><title>Issue 预览 - 报错</title><style>pre {{ white-space: pre-wrap; background: #f6f8fa; padding: 12px; }}</style></head><body><h2>脚本在加载或运行时报错</h2><p>请根据下方报错排查（如：数据库连接、AI 配置、网络）。</p><pre>{html.escape(err_msg)}</pre></body></html>"""
            out.write_text(err_html, encoding="utf-8")
        except Exception:
            pass
    raise


def _body_to_html(md: str) -> str:
    """Markdown 转 HTML（标题、粗体、列表、链接）"""
    if not md:
        return ""
    import re
    # [text](url) 先替换为占位符，escape 后再还原为 <a> 标签
    def _link_repl(m):
        return f"__LINK__{m.group(1)}__URL__{m.group(2)}__END__"
    s = re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', _link_repl, md)
    s = html.escape(s)
    s = re.sub(r'__LINK__(.+?)__URL__(.+?)__END__',
               lambda m: f'<a href="{m.group(2)}" style="color:#0969da;text-decoration:none;">{m.group(1)}</a>', s)
    # **bold**
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    # ## Heading（在段落之前）
    s = re.sub(r'^### (.+)$', r'<h3>\1</h3>', s, flags=re.MULTILINE)
    s = re.sub(r'^## (.+)$', r'<h2>\1</h2>', s, flags=re.MULTILINE)
    # 有序列表 \n1. xxx\n2. xxx
    def _ol(m):
        items = [x.strip() for x in m.group(0).strip().split('\n') if re.match(r'\d+\.', x)]
        lis = ''.join(f'<li>{re.sub(r"^\d+\.\s*", "", i)}</li>' for i in items)
        return f'<ol>{lis}</ol>'
    s = re.sub(r'\n(?:\d+\. .+\n?)+', _ol, s)
    # 无序列表 \n- xxx
    def _ul(m):
        items = [x.strip().lstrip('- ').strip() for x in m.group(0).strip().split('\n') if x.strip().startswith('-')]
        return '<ul>' + ''.join(f'<li>{i}</li>' for i in items) + '</ul>'
    s = re.sub(r'\n(?:- .+\n?)+', _ul, s)
    # 段落与换行
    s = s.replace("\n\n", "</p><p>").replace("\n", "<br>\n")
    return f"<p>{s}</p>"


def _label_color(label: str) -> str:
    """GitHub 风格标签颜色"""
    l = (label or "").lower()
    if "kind/bug" in l or "bug" in l:
        return "#d73a4a"  # red
    if "kind/feature" in l or "feature" in l:
        return "#a2eeef"  # cyan
    if "customer/" in l:
        return "#d4c5f9"  # purple
    if "area/" in l:
        return "#c2e0c6"  # green
    return "#ddf4ff"  # blue default


def write_preview_html(
    draft: dict,
    repo_owner: str,
    repo_name: str,
    output_path: Path,
    screenshot_path: Optional[Path] = None,
) -> str:
    """把草稿写成 GitHub 风格的本地 HTML 预览页（两栏布局）。screenshot_path 可选，添加到底部。"""
    title = draft.get("title") or "Issue 草稿"
    body = draft.get("body") or ""
    labels = draft.get("labels") or []
    assignees = draft.get("assignees") or []
    issue_type = draft.get("template_type") or ""
    related = draft.get("related_issues") or []
    body_html = _body_to_html(body)

    labels_html = "".join(
        f'<span class="label" style="background:{_label_color(l)};color:#1f2328;">{html.escape(l)}</span>'
        for l in labels
    ) or '<span class="muted">None yet</span>'

    assignees_html = "".join(
        f'<div class="sidebar-item"><span class="avatar">👤</span>{html.escape(a)}</div>'
        for a in assignees
    ) or '<span class="muted">No one assigned</span>'

    related_html = "".join(
        f'<a href="https://github.com/{repo_owner}/{repo_name}/issues/{str(r).lstrip("#")}" class="related-link">{html.escape(str(r))}</a> '
        for r in related
    ) if related else '<span class="muted">None yet</span>'

    # 截图区域：置于正文最下方（相对 preview.html 的路径）
    screenshot_html = ""
    out_dir = (ROOT / output_path).parent if not Path(output_path).is_absolute() else Path(output_path).resolve().parent
    default_screenshot = out_dir / "screenshots" / "issue_screenshot.png"
    use_screenshot = (screenshot_path and Path(screenshot_path).exists()) or default_screenshot.exists()
    if use_screenshot:
        rel = "screenshots/issue_screenshot.png"  # 截图放在 screenshots/ 下
        screenshot_html = f'''
      <div class="card" style="margin-top: 16px;">
        <h2 class="body-content" style="margin-top: 0;">Screenshots</h2>
        <img src="{rel}" alt="截图" style="max-width: 100%; border: 1px solid #d0d7de; border-radius: 6px;" />
      </div>'''

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} · {repo_owner}/{repo_name}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif; background: #f6f8fa; margin: 0; padding: 24px; color: #1f2328; line-height: 1.5; }}
    .container {{ max-width: 1280px; margin: 0 auto; display: flex; gap: 24px; flex-wrap: wrap; }}
    .main {{ flex: 1; min-width: 0; }}
    .sidebar {{ width: 296px; flex-shrink: 0; }}
    .header {{ margin-bottom: 16px; }}
    .title {{ font-size: 24px; font-weight: 600; margin: 0 0 8px 0; }}
    .badges {{ margin-bottom: 16px; }}
    .badge {{ display: inline-block; padding: 4px 12px; border-radius: 24px; font-size: 12px; font-weight: 500; margin-right: 8px; }}
    .badge-open {{ background: #dafbe1; color: #1a7f37; }}
    .badge-type {{ background: #ddf4ff; color: #0969da; }}
    .author {{ font-size: 14px; color: #57606a; margin-bottom: 16px; }}
    .card {{ background: #fff; border: 1px solid #d0d7de; border-radius: 6px; padding: 16px; margin-bottom: 16px; }}
    .body-content {{ font-size: 14px; }}
    .body-content p {{ margin: 0 0 12px 0; }}
    .body-content h2 {{ font-size: 16px; margin: 24px 0 8px 0; border-bottom: 1px solid #d0d7de; padding-bottom: 4px; }}
    .body-content h3 {{ font-size: 14px; margin: 16px 0 8px 0; }}
    .body-content ul, .body-content ol {{ margin: 8px 0; padding-left: 24px; }}
    .body-content a {{ color: #0969da; text-decoration: none; }}
    .body-content a:hover {{ text-decoration: underline; }}
    .sidebar-section {{ margin-bottom: 16px; }}
    .sidebar-title {{ font-size: 12px; font-weight: 600; color: #57606a; margin-bottom: 8px; }}
    .label {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px; margin: 2px 4px 2px 0; }}
    .muted {{ color: #57606a; font-size: 14px; }}
    .related-link {{ color: #0969da; margin-right: 8px; }}
    .footer {{ margin-top: 24px; font-size: 12px; color: #57606a; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="main">
      <div class="header">
        <h1 class="title">{html.escape(title)}</h1>
        <div class="badges">
          <span class="badge badge-open">Open</span>
          <span class="badge badge-type">{html.escape(issue_type or "Issue")}</span>
        </div>
        <div class="author">Preview · 本地预览</div>
      </div>
      <div class="card">
        <div class="body-content">
          {body_html}
        </div>
      </div>
      {screenshot_html}
      <p class="footer">此为本地预览，确认后请使用 create_issue_interactive.py 创建 Issue。</p>
    </div>
    <div class="sidebar">
      <div class="card sidebar-section">
        <div class="sidebar-title">Assignees</div>
        {assignees_html}
      </div>
      <div class="card sidebar-section">
        <div class="sidebar-title">Labels</div>
        <div>{labels_html}</div>
      </div>
      <div class="card sidebar-section">
        <div class="sidebar-title">Type</div>
        <div class="muted">{html.escape(issue_type or "—")}</div>
      </div>
      <div class="card sidebar-section">
        <div class="sidebar-title">Relationships</div>
        <div>{related_html}</div>
      </div>
      <div class="card sidebar-section">
        <div class="sidebar-title">Repository</div>
        <div class="muted">{html.escape(repo_owner + "/" + repo_name)}</div>
      </div>
    </div>
  </div>
</body>
</html>
"""
    out = Path(output_path)
    if not out.is_absolute():
        out = ROOT / out
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_content, encoding="utf-8")
    return str(out)


def run_single(repo_owner: str, repo_name: str, user_input: str, preview_only: bool, output_html: Optional[Path] = None) -> dict:
    print("正在初始化（数据库、AI）...", flush=True)
    try:
        storage = MOStorage()
        llm = LLMParser()
        gen = AIIssueGenerator(storage, llm, GITHUB_TOKEN, GITHUB_API_BASE_URL)
        print("正在生成草稿（调用 AI）...", flush=True)
        draft = gen.generate_issue_draft(user_input, repo_owner, repo_name)
    except Exception as e:
        print(f"生成草稿时出错: {e}", flush=True)
        draft = {
            "title": (user_input[:80] + "…") if len(user_input) > 80 else user_input,
            "body": user_input,
            "labels": [],
            "assignees": [],
        }
    print("\n--- 草稿预览 ---", flush=True)
    print("标题:", draft.get("title"), flush=True)
    print("正文:", (draft.get("body") or "")[:500], "..." if len(draft.get("body") or "") > 500 else "", flush=True)
    print("标签:", draft.get("labels"), flush=True)
    print("负责人:", draft.get("assignees"), flush=True)
    if output_html:
        path = write_preview_html(draft, repo_owner, repo_name, output_html, screenshot_path=None)
        print("本地网页已生成:", path, flush=True)
        _open_preview_in_browser(path)
    if preview_only:
        return {"draft": draft, "created": False}
    print("\n正在创建 Issue...")
    created = create_issue_on_github(
        owner=repo_owner,
        repo=repo_name,
        title=draft.get("title", "新Issue"),
        body=draft.get("body", ""),
        token=GITHUB_TOKEN,
        labels=draft.get("labels"),
        assignees=draft.get("assignees"),
        base_url=GITHUB_API_BASE_URL,
    )
    print("✓ 已创建:", created.get("html_url"), "编号 #" + str(created.get("number", "")))
    return {"draft": draft, "created": created}


def run_interactive(repo_owner: str, repo_name: str) -> None:
    storage = MOStorage()
    llm = LLMParser()
    gen = AIIssueGenerator(storage, llm, GITHUB_TOKEN, GITHUB_API_BASE_URL)
    print(f"交互模式 · 仓库 {repo_owner}/{repo_name} · 输入描述后生成草稿，输入 'q' 退出")
    while True:
        user_input = input("\n描述> ").strip()
        if user_input.lower() == "q":
            break
        if not user_input:
            continue
        draft = gen.generate_issue_draft(user_input, repo_owner, repo_name)
        print("标题:", draft.get("title"))
        print("正文摘要:", (draft.get("body") or "")[:300])
        print("标签:", draft.get("labels"))
        confirm = input("确认创建? (y/n)> ").strip().lower()
        if confirm == "y":
            created = create_issue_on_github(
                owner=repo_owner,
                repo=repo_name,
                title=draft.get("title", "新Issue"),
                body=draft.get("body", ""),
                token=GITHUB_TOKEN,
                labels=draft.get("labels"),
                assignees=draft.get("assignees"),
                base_url=GITHUB_API_BASE_URL,
            )
            print("✓ 已创建:", created.get("html_url"))


def _open_preview_in_browser(path: str) -> None:
    """生成预览后自动打开浏览器（macOS/Windows/Linux）"""
    try:
        import subprocess
        if sys.platform == "darwin":
            subprocess.run(["open", path], capture_output=True, timeout=2, check=False)
        elif sys.platform == "win32":
            subprocess.run(["start", "", path], shell=True, capture_output=True, timeout=2, check=False)
        else:
            subprocess.run(["xdg-open", path], capture_output=True, timeout=2, check=False)
    except Exception:
        pass


def _load_body_template(issue_type: str) -> str:
    """按类型加载正文模板（与 generate_preview_only 一致）。"""
    tpl_dir = ROOT / "feature_issue_and_kanban" / "templates"
    mapping = {"Doc Request": "Doc_Request.md", "Customer Project": "Customer_Project.md", "MO Feature": "MO_Feature.md", "MO Bug": "MO_Bug.md", "MOI Feature": "MOI_Feature.md", "MOI Bug": "MOI_Bug.md", "MOI SubTask": "MOI_SubTask.md", "Test Request": "Test_Request.md", "EE Feature": "EE_Feature.md", "User Bug": "User_Bug.md"}
    fname = mapping.get((issue_type or "").strip())
    if fname and (tpl_dir / fname).exists():
        return (tpl_dir / fname).read_text(encoding="utf-8").strip()
    return ""


def run_direct(repo_owner: str, repo_name: str, title: str, body: str, labels: list, assignees: list, preview_only: bool, output_html: Optional[Path] = None) -> dict:
    """直接使用标题/正文，不调用 AI/DB。用于聊天流程中「确认后提交」或「仅生成预览」。"""
    draft = {"title": title, "body": body, "labels": labels, "assignees": assignees}
    print("标题:", title, flush=True)
    print("正文:", (body or "")[:300] + ("..." if len(body or "") > 300 else ""), flush=True)
    if output_html:
        path = write_preview_html(draft, repo_owner, repo_name, output_html)
        print("本地网页已生成:", path, flush=True)
        _open_preview_in_browser(path)
    if preview_only:
        return {"draft": draft, "created": False}
    from issue_creator.github_issue_creator import create_issue_on_github
    from config.config import GITHUB_TOKEN, GITHUB_API_BASE_URL
    created = create_issue_on_github(owner=repo_owner, repo=repo_name, title=title, body=body or "", token=GITHUB_TOKEN, labels=labels or None, assignees=assignees or None, base_url=GITHUB_API_BASE_URL)
    print("✓ 已创建:", created.get("html_url"), "编号 #" + str(created.get("number", "")))
    return {"draft": draft, "created": created}


def main():
    print("Issue 创建脚本已启动", flush=True)
    parser = argparse.ArgumentParser(description="AI 驱动 Issue 创建")
    parser.add_argument("--input", help="Issue 描述（单轮模式，会调 AI）")
    parser.add_argument("--title", help="直接指定标题（与 --body 或 --type 同时使用时跳过 AI）")
    parser.add_argument("--body", help="直接指定正文；不填且指定 --type 时使用该类型正文模板")
    parser.add_argument("--type", "--issue-type", dest="issue_type", default="", help="Issue 类型，如 Doc Request；未传 --body 时用该类型模板作为正文")
    parser.add_argument("--labels", default="", help="逗号分隔标签，如 kind/docs,area/问数")
    parser.add_argument("--assignees", default="", help="逗号分隔负责人，如 wupeng")
    parser.add_argument("--repo", required=True, help="仓库 owner/name，如 matrixorigin/matrixflow")
    parser.add_argument("--interactive", action="store_true", help="交互模式")
    parser.add_argument("--preview", action="store_true", help="仅预览不创建")
    parser.add_argument("--output-html", help="生成本地预览网页路径")
    args = parser.parse_args()
    parts = args.repo.split("/")
    if len(parts) != 2:
        print("--repo 格式应为 owner/name")
        sys.exit(1)
    repo_owner, repo_name = parts[0], parts[1]
    out_html = Path(args.output_html) if args.output_html else None
    if out_html:
        _ensure_preview_path(out_html)

    if args.title is not None:
        if str(ROOT / "feature_issue_and_kanban") not in sys.path:
            sys.path.insert(0, str(ROOT / "feature_issue_and_kanban"))
        labels = [x.strip() for x in (args.labels or "").split(",") if x.strip()]
        assignees = [x.strip() for x in (args.assignees or "").split(",") if x.strip()]
        body = (args.body or "").strip()
        if not body and (args.issue_type or "").strip():
            body = _load_body_template((args.issue_type or "").strip())
        run_direct(repo_owner, repo_name, args.title, body, labels, assignees, args.preview, out_html)
        return
    if args.interactive:
        run_interactive(repo_owner, repo_name)
        return
    if not args.input:
        print("单轮模式需提供 --input；或同时提供 --title 与 --body 跳过 AI")
        sys.exit(1)
    try:
        run_single(repo_owner, repo_name, args.input, args.preview, out_html)
    except Exception as e:
        print(f"错误: {e}", flush=True)
        raise


if __name__ == "__main__":
    main()

