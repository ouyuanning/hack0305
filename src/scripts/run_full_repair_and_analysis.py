#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补全数据并生成完整分析报告

用途：对 20260223 等运行中出现的关联缺失、AI 解析失败进行补全，并输出完整分析。
流程：1. 关联关系补全  2. AI 解析补全（可选）  3. 日报+进度+多维度报告  4. 邮件发送（可选）

使用：
    python3 run_full_repair_and_analysis.py
    python3 run_full_repair_and_analysis.py --repo-owner matrixorigin --repo-name matrixone
    python3 run_full_repair_and_analysis.py --skip-ai-repair  # 跳过 AI 补全
    python3 run_full_repair_and_analysis.py --email user@example.com  # 发送报告邮件
"""

import sys
import os
import argparse

# 添加项目根目录到路径（支持从 scripts/ 运行）
_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_dir)
sys.path.insert(0, _root)

from config.config import validate_config, SMTP_USER, SMTP_PASSWORD, DEFAULT_EMAIL_TO


def main():
    parser = argparse.ArgumentParser(description="补全数据并生成完整分析报告")
    parser.add_argument("--repo-owner", default="matrixorigin", help="仓库所有者")
    parser.add_argument("--repo-name", default="matrixone", help="仓库名称")
    parser.add_argument("--skip-ai-repair", action="store_true", help="跳过 AI 解析补全（仅做关联补全+报告）")
    parser.add_argument("--ai-repair-dry-run", action="store_true", help="AI 补全仅统计不执行")
    parser.add_argument("--email", type=str, default="", help="收件人邮箱，指定后发送报告邮件")

    args = parser.parse_args()

    if not validate_config():
        print("❌ 配置验证失败")
        return 1

    repo_owner = args.repo_owner
    repo_name = args.repo_name

    print("=" * 60)
    print("补全数据并生成完整分析报告")
    print(f"仓库: {repo_owner}/{repo_name}")
    print("=" * 60)

    # 1. 关联关系补全
    print("\n📌 步骤 1/3: 关联关系补全")
    from supplement_relations import run_supplement
    if not run_supplement(repo_owner, repo_name, clear_first=False, quiet=False):
        print("⚠️  关联补全失败，继续执行后续步骤...")

    # 2. AI 解析补全
    if not args.skip_ai_repair:
        print("\n📌 步骤 2/3: AI 解析补全")
        from repair_ai_parse import run_repair
        run_repair(repo_owner, repo_name, dry_run=args.ai_repair_dry_run)
    else:
        print("\n⏭️  步骤 2/3: 跳过 AI 解析补全")

    # 3. 生成报告
    print("\n📌 步骤 3/3: 生成分析报告")
    from modules.database_storage.mo_client import MOStorage
    from modules.report_generator.report_gen import Analyzer
    from modules.report_generator.improved_report_gen import ImprovedReportGenerator

    storage = MOStorage()
    analyzer = Analyzer(storage)
    print("  - 日报...")
    daily = analyzer.generate_daily_report(repo_owner, repo_name)
    print("  - 进度报告...")
    progress = analyzer.generate_progress_report(repo_owner, repo_name)
    print("  - 多维度分析报告...")
    multi_gen = ImprovedReportGenerator(storage)
    multi_gen.generate_all_reports(repo_owner, repo_name)

    # 4. 发送邮件（可选）
    to_email = args.email or DEFAULT_EMAIL_TO
    if to_email:
        if SMTP_USER and SMTP_PASSWORD:
            print("\n📧 发送报告邮件...")
            from modules.email_sender.email_sender import EmailSender
            sender = EmailSender()
            success = sender.send_report(
                to_email=to_email,
                daily_report=daily,
                progress_report=progress,
                repo_owner=repo_owner,
                repo_name=repo_name,
                attach_json=True
            )
            if success:
                print(f"✅ 邮件已发送到 {to_email}")
            else:
                print(f"⚠️ 邮件发送失败，报告已保存在 data/reports/")
        else:
            print("\n⚠️ 未配置 SMTP，跳过邮件发送")
    else:
        print("\n💡 提示：添加 --email your@example.com 可发送报告邮件")

    print("\n" + "=" * 60)
    print("✅ 全部完成！报告已保存到 data/reports/")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
