#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置检查和邮件发送脚本
功能：检查配置是否正确，运行完整流程并发送邮件报告
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径（支持从 scripts/ 运行）
_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_dir)
sys.path.insert(0, _root)

from config.config import (
    AI_PROVIDER, DASHSCOPE_API_KEY, QWEN_MODEL,
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM, EMAIL_FROM_NAME,
    validate_config
)
from main import IssueManagerScheduler
from modules.email_sender.email_sender import EmailSender


def check_configuration():
    """检查配置状态"""
    print("=" * 60)
    print("📋 配置检查")
    print("=" * 60)
    
    # AI配置检查
    print(f"\n🤖 AI配置:")
    print(f"  - AI Provider: {AI_PROVIDER}")
    if AI_PROVIDER == "qwen":
        if DASHSCOPE_API_KEY and DASHSCOPE_API_KEY not in ["your_qwen_api_key_here", "your_dashscope_api_key_here"]:
            print(f"  - ✅ 千问API Key: 已配置")
            print(f"  - ✅ 千问模型: {QWEN_MODEL}")
        else:
            print(f"  - ❌ 千问API Key: 未配置")
            print(f"    提示: 请设置 DASHSCOPE_API_KEY 环境变量")
    
    # 邮件配置检查
    print(f"\n📧 邮件配置:")
    print(f"  - SMTP Host: {SMTP_HOST}")
    print(f"  - SMTP Port: {SMTP_PORT}")
    if SMTP_USER:
        print(f"  - ✅ SMTP User: 已配置")
    else:
        print(f"  - ⚠️  SMTP User: 未配置（需要配置才能发送邮件）")
    
    if SMTP_PASSWORD:
        print(f"  - ✅ SMTP Password: 已配置")
    else:
        print(f"  - ⚠️  SMTP Password: 未配置（需要配置才能发送邮件）")
    
    if EMAIL_FROM:
        print(f"  - ✅ 发件人邮箱: {EMAIL_FROM}")
    else:
        print(f"  - ⚠️  发件人邮箱: 未配置（将使用SMTP_USER）")
    
    print(f"  - 发件人名称: {EMAIL_FROM_NAME}")
    
    # 验证配置
    print(f"\n🔍 配置验证:")
    if validate_config():
        print("  ✅ 基本配置验证通过")
    else:
        print("  ⚠️  配置验证有警告，请检查")
    
    return True


def run_full_analysis_and_send_email(repo_owner: str, repo_name: str, to_email: str, full_sync: bool = False):
    """
    运行完整分析流程并发送邮件
    
    参数:
    - repo_owner: 仓库所有者
    - repo_name: 仓库名称
    - to_email: 收件人邮箱
    - full_sync: 是否全量同步
    """
    print("=" * 60)
    print(f"🚀 开始运行完整分析流程")
    print(f"仓库: {repo_owner}/{repo_name}")
    print(f"收件人: {to_email}")
    print("=" * 60)
    
    try:
        # 创建调度器
        scheduler = IssueManagerScheduler()
        
        # 1. 同步仓库
        print("\n📥 步骤1: 同步GitHub Issue数据...")
        stats = scheduler.sync_repo(repo_owner, repo_name, full_sync=full_sync)
        print(f"✅ 同步完成: 新增 {stats.get('new', 0)} 个，更新 {stats.get('updated', 0)} 个")
        
        # 2. 生成报告
        print("\n📊 步骤2: 生成分析报告...")
        daily_report = scheduler.analyzer.generate_daily_report(repo_owner, repo_name)
        progress_report = scheduler.analyzer.generate_progress_report(repo_owner, repo_name)
        print("✅ 报告生成完成")
        
        # 3. 发送邮件
        print("\n📧 步骤3: 发送邮件报告...")
        if not SMTP_USER or not SMTP_PASSWORD:
            print("⚠️  邮件配置不完整，无法发送邮件")
            print("   请配置 SMTP_USER 和 SMTP_PASSWORD")
            print("   报告已保存在 data/reports/ 目录")
            return False
        
        sender = EmailSender()
        success = sender.send_report(
            to_email=to_email,
            daily_report=daily_report,
            progress_report=progress_report,
            repo_owner=repo_owner,
            repo_name=repo_name,
            attach_json=True
        )
        
        if success:
            print(f"\n✅ 所有任务完成！邮件已发送到 {to_email}")
            return True
        else:
            print(f"\n❌ 邮件发送失败，但报告已保存在 data/reports/ 目录")
            return False
            
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("GitHub Issue 智能管理系统 - 配置检查和邮件发送")
    print("=" * 60)
    
    # 检查配置
    check_configuration()
    
    # 询问是否继续
    print("\n" + "=" * 60)
    continue_choice = input("\n是否继续运行完整流程并发送邮件？(Y/n): ").strip().lower()
    if continue_choice == 'n':
        print("已取消")
        return
    
    # 获取仓库信息
    print("\n" + "=" * 60)
    repo_owner = input("请输入仓库所有者（例如：octocat）: ").strip()
    repo_name = input("请输入仓库名称（例如：Hello-World）: ").strip()
    
    if not repo_owner or not repo_name:
        print("❌ 仓库信息不能为空")
        return
    
    # 获取收件人邮箱
    to_email = input("请输入收件人邮箱（默认: wupeng@matrixorigin.cn）: ").strip()
    if not to_email:
        to_email = "wupeng@matrixorigin.cn"
    
    # 询问是否全量同步
    full_sync_input = input("\n是否执行全量同步（清空旧数据）？(y/N): ").strip().lower()
    full_sync = full_sync_input == 'y'
    
    # 运行完整流程
    run_full_analysis_and_send_email(repo_owner, repo_name, to_email, full_sync)


if __name__ == "__main__":
    main()
