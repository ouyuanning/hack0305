#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WF-005 历史数据清洗 CLI 入口
用法:
    python3 scripts/clean_historical_data.py \
        --repo-owner matrixorigin --repo-name matrixone \
        [--start-date 2024-01-01] [--end-date 2024-12-31] \
        [--config config/cleaning_rules.yaml]
"""

import argparse
import sys
import os
from datetime import date

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from modules.database_storage.mo_client import MOStorage
from modules.llm_parser.llm_parser import LLMParser
from modules.data_cleaning.cleaner import DataCleaner


def main():
    parser = argparse.ArgumentParser(description="WF-005 历史数据清洗")
    parser.add_argument("--repo-owner", required=True, help="仓库所有者")
    parser.add_argument("--repo-name", required=True, help="仓库名称")
    parser.add_argument("--start-date", default=None, help="开始日期 (YYYY-MM-DD)")
    parser.add_argument("--end-date", default=None, help="结束日期 (YYYY-MM-DD)")
    parser.add_argument("--config", default=None, help="清洗规则配置文件路径")
    parser.add_argument("--no-ai", action="store_true", help="跳过AI分析，仅使用规则回退")
    args = parser.parse_args()

    start_date = date.fromisoformat(args.start_date) if args.start_date else None
    end_date = date.fromisoformat(args.end_date) if args.end_date else None

    storage = MOStorage()
    llm = None if args.no_ai else LLMParser()

    cleaner = DataCleaner(storage=storage, llm=llm, config_path=args.config)
    result = cleaner.run(
        repo_owner=args.repo_owner,
        repo_name=args.repo_name,
        start_date=start_date,
        end_date=end_date,
    )

    print(f"\n{'='*60}")
    print(f"清洗结果: {result.get('status')}")
    print(f"总读取: {result.get('total_issues_read', 0)}")
    print(f"成功写入: {result.get('saved_count', 0)}")
    print(f"平均质量分: {result.get('average_quality_score', 0):.2f}")


if __name__ == "__main__":
    main()
