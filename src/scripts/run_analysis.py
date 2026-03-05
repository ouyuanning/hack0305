#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Issue 智能管理系统 - 非交互式运行脚本
支持命令行参数，可以直接运行完整流程
"""

import sys
import os
import argparse
from pathlib import Path

# 添加项目根目录到路径（支持从 scripts/ 运行）
_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_dir)
sys.path.insert(0, _root)

from config.config import (
    AI_PROVIDER, DASHSCOPE_API_KEY, QWEN_MODEL,
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM, EMAIL_FROM_NAME,
    validate_config, DEFAULT_EMAIL_TO
)
from main import IssueManagerScheduler
from modules.email_sender.email_sender import EmailSender


def run_full_analysis(
    repo_owner: str,
    repo_name: str,
    to_email: str = None,
    full_sync: bool = False,
    skip_email: bool = False
):
    """
    运行完整分析流程并发送邮件
    
    参数:
    - repo_owner: 仓库所有者
    - repo_name: 仓库名称
    - to_email: 收件人邮箱（可选，默认使用配置中的DEFAULT_EMAIL_TO）
    - full_sync: 是否全量同步
    - skip_email: 是否跳过邮件发送
    """
    print("=" * 60)
    print(f"🚀 开始运行完整分析流程")
    print(f"仓库: {repo_owner}/{repo_name}")
    if to_email and not skip_email:
        print(f"收件人: {to_email}")
    print("=" * 60)
    
    try:
        # 创建调度器
        scheduler = IssueManagerScheduler()
        
        # 1. 同步仓库
        print("\n📥 步骤1: 同步GitHub Issue数据...")
        stats = scheduler.sync_repo(repo_owner, repo_name, full_sync=full_sync)
        print(f"✅ 同步完成: 总计 {stats.get('total', 0)} 个，成功 {stats.get('processed', 0)} 个，失败 {stats.get('errors', 0)} 个")
        
        # 2. 生成报告
        print("\n📊 步骤2: 生成分析报告...")
        daily_report = scheduler.analyzer.generate_daily_report(repo_owner, repo_name)
        progress_report = scheduler.analyzer.generate_progress_report(repo_owner, repo_name)
        print("✅ 报告生成完成")
        
        # 3. 发送邮件（如果配置了邮件且未跳过）
        if not skip_email:
            print("\n📧 步骤3: 发送邮件报告...")
            if not SMTP_USER or not SMTP_PASSWORD:
                print("⚠️  邮件配置不完整，无法发送邮件")
                print("   请配置 SMTP_USER 和 SMTP_PASSWORD 环境变量")
                print("   报告已保存在 data/reports/ 目录")
            else:
                # 使用提供的邮箱或默认邮箱
                email_to = to_email or DEFAULT_EMAIL_TO or "wupeng@matrixorigin.cn"
                
                sender = EmailSender()
                success = sender.send_report(
                    to_email=email_to,
                    daily_report=daily_report,
                    progress_report=progress_report,
                    repo_owner=repo_owner,
                    repo_name=repo_name,
                    attach_json=True
                )
                
                if success:
                    print(f"\n✅ 所有任务完成！邮件已发送到 {email_to}")
                else:
                    print(f"\n❌ 邮件发送失败，但报告已保存在 data/reports/ 目录")
        else:
            print("\n⏭️  跳过邮件发送（报告已保存在 data/reports/ 目录）")
        
        print("\n" + "=" * 60)
        print("✅ 所有任务完成！")
        print("=" * 60)
        return True
            
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="GitHub Issue 智能管理系统 - 运行完整分析流程",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本运行（需要交互式输入）
  python3 run_analysis.py
  
  # 指定仓库
  python3 run_analysis.py --repo-owner matrixorigin --repo-name matrixone
  
  # 指定仓库和邮箱
  python3 run_analysis.py --repo-owner matrixorigin --repo-name matrixone --email wupeng@matrixorigin.cn
  
  # 全量同步
  python3 run_analysis.py --repo-owner matrixorigin --repo-name matrixone --full-sync
  
  # 只生成报告，不发送邮件
  python3 run_analysis.py --repo-owner matrixorigin --repo-name matrixone --skip-email
        """
    )
    
    parser.add_argument(
        "--repo-owner",
        type=str,
        help="仓库所有者（例如：matrixorigin）"
    )
    parser.add_argument(
        "--repo-name",
        type=str,
        help="仓库名称（例如：matrixone）"
    )
    parser.add_argument(
        "--email",
        type=str,
        help="收件人邮箱（默认：wupeng@matrixorigin.cn）"
    )
    parser.add_argument(
        "--full-sync",
        action="store_true",
        help="执行全量同步（清空旧数据）"
    )
    parser.add_argument(
        "--skip-email",
        action="store_true",
        help="跳过邮件发送（只生成报告）"
    )
    
    args = parser.parse_args()
    
    # 显示配置检查
    print("=" * 60)
    print("GitHub Issue 智能管理系统")
    print("=" * 60)
    
    print(f"\n🤖 AI配置:")
    print(f"  - AI Provider: {AI_PROVIDER}")
    if AI_PROVIDER == "qwen":
        if DASHSCOPE_API_KEY and DASHSCOPE_API_KEY not in ["your_qwen_api_key_here", "your_dashscope_api_key_here"]:
            print(f"  - ✅ 千问API Key: 已配置")
            print(f"  - ✅ 千问模型: {QWEN_MODEL}")
        else:
            print(f"  - ❌ 千问API Key: 未配置")
    
    # 验证配置
    if not validate_config():
        print("\n❌ 配置验证失败，请检查配置文件")
        return 1
    
    # 获取仓库信息
    repo_owner = args.repo_owner
    repo_name = args.repo_name
    
    if not repo_owner:
        repo_owner = input("\n请输入仓库所有者（例如：matrixorigin）: ").strip()
    
    if not repo_name:
        repo_name = input("请输入仓库名称（例如：matrixone）: ").strip()
    
    if not repo_owner or not repo_name:
        print("❌ 仓库信息不能为空")
        return 1
    
    # 运行完整流程
    success = run_full_analysis(
        repo_owner=repo_owner,
        repo_name=repo_name,
        to_email=args.email,
        full_sync=args.full_sync,
        skip_email=args.skip_email
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
