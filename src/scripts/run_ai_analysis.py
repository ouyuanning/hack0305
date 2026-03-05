#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 驱动分析 - 独立运行脚本

功能：
1. 项目推进分析（每日）：按客户、层级分析进度，AI 输出健康度与建议
2. 横向关联分析（每周一）：共性 Feature、高 Bug Feature、AI 模式识别

依赖：使用 config 中配置的 AI（默认千问），与主系统一致
适用于：matrixflow 等含 customer/xxx 标签的仓库

使用：
    python3 scripts/run_ai_analysis.py --repo-owner matrixorigin --repo-name matrixflow
    python3 scripts/run_ai_analysis.py  # 默认 matrixorigin/matrixflow
"""

import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_dir)
sys.path.insert(0, _root)


def main():
    parser = argparse.ArgumentParser(description="AI 驱动分析：项目推进 + 横向关联")
    parser.add_argument("--repo-owner", default="matrixorigin", help="仓库所有者")
    parser.add_argument("--repo-name", default="matrixflow", help="仓库名称")
    parser.add_argument("--skip-cross", action="store_true", help="跳过横向关联分析")
    parser.add_argument("--output-dir", default="data/reports/ai_analysis", help="输出目录")
    args = parser.parse_args()

    try:
        from modules.database_storage.mo_client import MOStorage
        from modules.ai_analysis.ai_driven_analysis_engine import AIAnalysisEngine
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")

    print("=" * 70)
    print("AI 驱动分析")
    print(f"仓库: {args.repo_owner}/{args.repo_name}")
    print("=" * 70)

    storage = MOStorage()
    engine = AIAnalysisEngine(storage)

    # 1. 项目推进分析
    project_progress = engine.analyze_project_progress(args.repo_owner, args.repo_name)
    out_project = output_dir / f"project_progress_{date_str}.json"
    with open(out_project, "w", encoding="utf-8") as f:
        json.dump(project_progress, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n✅ 项目推进分析已保存: {out_project}")

    # 2. 横向关联分析（可选，建议每周一跑）
    if not args.skip_cross:
        cross_patterns = engine.analyze_cross_customer_patterns(args.repo_owner, args.repo_name)
        out_cross = output_dir / f"cross_patterns_{date_str}.json"
        with open(out_cross, "w", encoding="utf-8") as f:
            json.dump(cross_patterns, f, indent=2, ensure_ascii=False, default=str)
        print(f"✅ 横向关联分析已保存: {out_cross}")
    else:
        print("\n⏭️  跳过横向关联分析 (--skip-cross)")

    print("\n" + "=" * 70)
    print("✅ AI 分析完成")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
