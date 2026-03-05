#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量创建 Issue，并输出 Excel 表（编号、标题、链接、状态）。

用法（在项目根目录执行）:
  # CSV 格式：标题,正文,标签,负责人（逗号分隔多值用 | 分隔）
  python3 feature_issue_and_kanban/scripts/batch_create_issues.py --repo matrixorigin/matrixflow --csv issues.csv --output result.xlsx
  # 或 JSON： [{"title":"...","body":"...","labels":["a","b"],"assignees":["wupeng"]}]
  python3 feature_issue_and_kanban/scripts/batch_create_issues.py --repo matrixorigin/matrixflow --json issues.json --output result.xlsx
"""
import sys
import csv
import json
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "feature_issue_and_kanban"))

from config.config import GITHUB_TOKEN, GITHUB_API_BASE_URL
from issue_creator.github_issue_creator import create_issue_on_github


def load_from_csv(path: Path) -> list:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            title = (row.get("title") or row.get("标题") or "").strip()
            body = (row.get("body") or row.get("正文") or "").strip()
            labels = (row.get("labels") or row.get("标签") or "").strip().replace("|", ",").split(",")
            labels = [x.strip() for x in labels if x.strip()]
            assignees = (row.get("assignees") or row.get("负责人") or "").strip().replace("|", ",").split(",")
            assignees = [x.strip() for x in assignees if x.strip()]
            if title:
                rows.append({"title": title, "body": body, "labels": labels, "assignees": assignees})
    return rows


def load_from_json(path: Path) -> list:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else [data]


def main():
    parser = argparse.ArgumentParser(description="批量创建 Issue 并输出 Excel")
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument("--csv", help="CSV 文件路径（列：title, body, labels, assignees 或 标题,正文,标签,负责人）")
    parser.add_argument("--json", help="JSON 文件路径（数组，每项含 title, body, labels, assignees）")
    parser.add_argument("--output", required=True, help="输出 Excel 路径，如 result.xlsx")
    parser.add_argument("--dry-run", action="store_true", help="只打印不创建")
    args = parser.parse_args()
    if args.csv:
        items = load_from_csv(Path(args.csv))
    elif args.json:
        items = load_from_json(Path(args.json))
    else:
        print("请指定 --csv 或 --json", file=sys.stderr)
        sys.exit(1)
    if not items:
        print("没有可创建的条目", file=sys.stderr)
        sys.exit(1)
    parts = args.repo.split("/")
    if len(parts) != 2:
        print("--repo 格式应为 owner/name", file=sys.stderr)
        sys.exit(1)
    owner, repo = parts[0], parts[1]
    results = []
    for i, item in enumerate(items):
        title = item.get("title", "")
        body = item.get("body", "")
        labels = item.get("labels", [])
        assignees = item.get("assignees", [])
        if args.dry_run:
            results.append({"number": "-", "title": title, "url": "(dry-run)", "status": "跳过"})
            print(f"[{i+1}] (dry-run) {title}")
            continue
        try:
            created = create_issue_on_github(owner=owner, repo=repo, title=title, body=body, token=GITHUB_TOKEN, labels=labels or None, assignees=assignees or None, base_url=GITHUB_API_BASE_URL)
            url = created.get("html_url", "")
            num = created.get("number", "")
            results.append({"number": num, "title": title, "url": url, "status": "已创建"})
            print(f"[{i+1}] #{num} {url}")
        except Exception as e:
            results.append({"number": "-", "title": title, "url": str(e), "status": "失败"})
            print(f"[{i+1}] 失败: {e}")
    out_path = Path(args.output)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["序号", "Issue 编号", "标题", "链接", "状态"])
        for i, r in enumerate(results, 1):
            ws.append([i, r["number"], r["title"], r["url"], r["status"]])
        wb.save(out_path)
        print("已写入 Excel:", out_path)
    except ImportError:
        csv_path = out_path.with_suffix(".csv")
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["序号", "Issue 编号", "标题", "链接", "状态"])
            for i, r in enumerate(results, 1):
                w.writerow([i, r["number"], r["title"], r["url"], r["status"]])
        print("未安装 openpyxl，已写入 CSV:", csv_path)


if __name__ == "__main__":
    main()
