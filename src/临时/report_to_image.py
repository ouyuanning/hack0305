#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
临时脚本：把「分析结果」渲染成一张固定宽、高度随内容的长图，供后续传给线上平台集成。

用法：
  # 用内置 demo 内容出一张图（先测通）
  python3 临时/report_to_image.py

  # 指定 HTML 文件出图
  python3 临时/report_to_image.py --html path/to/page.html

  # 指定输出路径
  python3 临时/report_to_image.py --output 临时/output_images/客户A_20260225.png

依赖（本脚本单独用，主项目未带）：
  pip install playwright
  playwright install chromium
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

# 固定宽度（与之前说的「邮件宽度固定」一致，便于平台展示）
OUTPUT_WIDTH = 800
OUTPUT_DIR = Path(__file__).resolve().parent / "output_images"


def _demo_html() -> str:
    """内置一段 demo HTML，固定宽度 800px，内容可改着测。"""
    return """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    * { box-sizing: border-box; }
    body { margin: 0; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; background: #f5f5f5; }
    .page { max-width: """ + str(OUTPUT_WIDTH - 40) + """px; margin: 0 auto; background: #fff; padding: 24px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    h1 { color: #24292e; border-bottom: 3px solid #0366d6; padding-bottom: 10px; font-size: 1.5em; }
    h2 { color: #0366d6; margin-top: 24px; font-size: 1.2em; }
    .stat-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }
    .stat-label { color: #586069; font-weight: 600; }
    .stat-value { font-weight: bold; }
    ul { margin: 8px 0; padding-left: 20px; }
    .footer { margin-top: 32px; padding-top: 16px; border-top: 1px solid #eee; color: #586069; font-size: 0.9em; }
  </style>
</head>
<body>
  <div class="page">
    <h1>📊 分析结果（demo）</h1>
    <p><strong>生成时间：</strong>""" + datetime.now().strftime("%Y-%m-%d %H:%M") + """</p>
    <h2>总体概览</h2>
    <div class="stat-row"><span class="stat-label">总 Issue 数</span><span class="stat-value">9011</span></div>
    <div class="stat-row"><span class="stat-label">Open</span><span class="stat-value">1200</span></div>
    <div class="stat-row"><span class="stat-label">Closed 今日</span><span class="stat-value">5</span></div>
    <h2>某客户简要</h2>
    <ul>
      <li>健康度：85/100</li>
      <li>关键发现：需求按期推进，无阻塞</li>
      <li>建议：保持当前节奏</li>
    </ul>
    <div class="footer">GitHub Issue 智能管理系统 · 出图测试</div>
  </div>
</body>
</html>
"""


def html_to_image(html_content: str, output_path: Path, width: int = OUTPUT_WIDTH) -> bool:
    """
    把一段 HTML 渲染成一张长图（固定宽 width px，高度随内容）。
    需要安装：pip install playwright && playwright install chromium
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ 未安装 playwright，请执行：")
        print("   pip install playwright")
        print("   playwright install chromium")
        return False

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        # 固定视口宽度，高度给大一点，后面按内容截
        page.set_viewport_size({"width": width, "height": 2000})
        page.set_content(html_content, wait_until="networkidle")
        # 用 JS 取 body 实际高度，再设一次 viewport 或直接截整页
        body_height = page.evaluate("""() => {
            document.body.style.overflow = 'hidden';
            return Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);
        }""")
        page.set_viewport_size({"width": width, "height": body_height + 40})
        page.screenshot(path=str(output_path), full_page=True)
        browser.close()

    print(f"✅ 已出图: {output_path}")
    return True


def main():
    parser = argparse.ArgumentParser(description="分析结果 → 固定宽长图")
    parser.add_argument("--html", type=str, help="输入 HTML 文件路径；不传则用内置 demo")
    parser.add_argument("--output", "-o", type=str, help="输出图片路径，默认 临时/output_images/report_日期时间.png")
    parser.add_argument("--width", type=int, default=OUTPUT_WIDTH, help=f"图片宽度，默认 {OUTPUT_WIDTH}")
    args = parser.parse_args()

    if args.html:
        html_path = Path(args.html)
        if not html_path.exists():
            print(f"❌ 文件不存在: {html_path}")
            return 1
        html_content = html_path.read_text(encoding="utf-8")
    else:
        html_content = _demo_html()

    if args.output:
        out_path = Path(args.output)
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUTPUT_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

    ok = html_to_image(html_content, out_path, width=args.width)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
