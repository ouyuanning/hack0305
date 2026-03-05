#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按项目标签生成每日看板 Markdown（可选 AI 总结）。
用法（在项目根目录执行）:
  python feature_issue_and_kanban/scripts/generate_daily_dashboard.py --project-tag "project/问数深化"
  python feature_issue_and_kanban/scripts/generate_daily_dashboard.py --project-tag "project/问数深化" --repo matrixorigin/matrixflow --output ./dashboard.md
"""
import sys
import argparse
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.database_storage.mo_client import MOStorage
from modules.llm_parser.llm_parser import LLMParser

sys.path.insert(0, str(ROOT / "feature_issue_and_kanban"))
from project_manager.dashboard_generator import DashboardGenerator


def main():
    parser = argparse.ArgumentParser(description="生成每日项目看板")
    parser.add_argument("--project-tag", required=True, help="项目标签，如 project/问数深化")
    parser.add_argument("--repo", help="可选，限制仓库 owner/name")
    parser.add_argument("--date", help="快照日期 YYYY-MM-DD，默认今天")
    parser.add_argument("--output", help="输出文件路径，不指定则打印到 stdout")
    parser.add_argument("--no-ai", action="store_true", help="不调用 AI 总结")
    parser.add_argument("--demo", action="store_true", help="使用假数据生成看板，不查库")
    parser.add_argument("--output-html", help="同时输出甘特图风格 HTML 看板（与甘特图v3 效果一致）")
    args = parser.parse_args()
    snapshot_date = date.today()
    if args.date:
        try:
            snapshot_date = date.fromisoformat(args.date)
        except ValueError:
            print("--date 格式应为 YYYY-MM-DD")
            sys.exit(1)
    repo_owner = repo_name = None
    if args.repo:
        parts = args.repo.split("/")
        if len(parts) != 2:
            print("--repo 格式应为 owner/name")
            sys.exit(1)
        repo_owner, repo_name = parts[0], parts[1]
    if args.demo:
        gen = DashboardGenerator(storage=None, llm=None)
        demo_rows = DashboardGenerator.get_demo_rows(
            repo_owner or "matrixorigin",
            repo_name or "matrixflow",
        )
        md = gen.generate_dashboard_from_rows(
            project_tag=args.project_tag,
            snapshot_date=snapshot_date,
            rows=demo_rows,
        )
        if args.output:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            Path(args.output).write_text(md, encoding="utf-8")
            print("✓ 已写入（演示数据）", args.output)
        else:
            print(md)
        if getattr(args, "output_html", None):
            html_path = Path(args.output_html)
            html_path.parent.mkdir(parents=True, exist_ok=True)
            html_path.write_text(
                gen.generate_dashboard_html(project_tag=args.project_tag, snapshot_date=snapshot_date, rows=demo_rows),
                encoding="utf-8",
            )
            print("✓ 已写入 HTML 看板", args.output_html)
        return
    storage = MOStorage()
    llm = None if args.no_ai else LLMParser()
    gen = DashboardGenerator(storage, llm)
    md = gen.generate_dashboard(
        project_tag=args.project_tag,
        snapshot_date=snapshot_date,
        repo_owner=repo_owner,
        repo_name=repo_name,
    )
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(md, encoding="utf-8")
        print("✓ 已写入", args.output)
    else:
        print(md)
    if getattr(args, "output_html", None):
        html_path = Path(args.output_html)
        html_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.write_text(
            gen.generate_dashboard_html(
                project_tag=args.project_tag,
                snapshot_date=snapshot_date,
                repo_owner=repo_owner,
                repo_name=repo_name,
            ),
            encoding="utf-8",
        )
        print("✓ 已写入 HTML 看板", args.output_html)


if __name__ == "__main__":
    main()
