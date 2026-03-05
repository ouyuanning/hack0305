#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可扩展分析引擎 - 独立运行入口

基于《分析模块升级逻辑-260223.zip》设计的配置驱动分析框架。
支持：基础统计、标签分析、模块分析、层级分析、客户分析、关联分析、趋势分析。
输出：JSON、Markdown、HTML。

使用：
    python3 run_extensible_analysis.py
    python3 run_extensible_analysis.py --repo-owner matrixorigin --repo-name matrixone
    python3 run_extensible_analysis.py --config config/analysis_config.yaml
"""

import sys
import os

# 添加项目根目录到路径（支持从 scripts/ 运行）
_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_dir)
sys.path.insert(0, _root)

from modules.analysis_extensible.analysis_engine import ExtensibleAnalysisEngine


def main():
    import argparse
    p = argparse.ArgumentParser(description="可扩展分析引擎")
    p.add_argument("--config", help="配置文件路径（默认 config/analysis_config.yaml）")
    p.add_argument("--repo-owner", default="matrixorigin", help="仓库所有者")
    p.add_argument("--repo-name", default="matrixone", help="仓库名称")
    args = p.parse_args()
    engine = ExtensibleAnalysisEngine(config_path=args.config)
    engine.run(repo_owner=args.repo_owner, repo_name=args.repo_name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
