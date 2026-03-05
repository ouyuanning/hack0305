#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Issue 智能管理系统 - 可配置自动运行脚本

功能：
1. 支持配置文件（JSON/YAML）
2. 支持环境变量
3. 支持命令行参数
4. 自动运行完整流程（同步、分析、报告、邮件）

使用方法：
    # 使用配置文件
    python3 auto_run.py --config config.json
    
    # 使用命令行参数
    python3 auto_run.py --repo-owner matrixorigin --repo-name matrixone --email user@example.com
    
    # 使用环境变量
    export REPO_OWNER=matrixorigin
    export REPO_NAME=matrixone
    export REPORT_EMAIL=user@example.com
    python3 auto_run.py
"""

import sys
import os
import json
import argparse
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(__file__))

# 支持从 scripts/ 导入 supplement_relations
_scripts_dir = os.path.join(os.path.dirname(__file__), "scripts")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from config.config import (
    AI_PROVIDER, DASHSCOPE_API_KEY, QWEN_MODEL,
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM, EMAIL_FROM_NAME,
    validate_config, DEFAULT_EMAIL_TO
)
from main import IssueManagerScheduler
from modules.email_sender.email_sender import EmailSender
from supplement_relations import run_supplement


class AutoRunner:
    """自动运行器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化自动运行器
        
        参数:
        - config: 配置字典，包含仓库信息、邮件配置等
        """
        self.config = config or {}
        self.scheduler = None
        
    def load_config_file(self, config_path: str) -> Dict[str, Any]:
        """从文件加载配置"""
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            if config_path.endswith('.json'):
                return json.load(f)
            elif config_path.endswith('.yaml') or config_path.endswith('.yml'):
                try:
                    import yaml
                    return yaml.safe_load(f)
                except ImportError:
                    raise ImportError("需要安装 PyYAML: pip install pyyaml")
            else:
                raise ValueError(f"不支持的配置文件格式: {config_path}")
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        获取配置值，优先级：命令行参数 > 配置文件 > 环境变量 > 默认值
        
        参数:
        - key: 配置键名
        - default: 默认值
        
        返回:
        - 配置值
        """
        # 1. 从配置文件获取
        if key in self.config:
            return self.config[key]
        
        # 2. 从环境变量获取
        env_key = key.upper().replace('-', '_')
        env_value = os.getenv(env_key)
        if env_value:
            return env_value
        
        # 3. 返回默认值
        return default
    
    def check_configuration(self) -> bool:
        """检查系统配置"""
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
        
        # 验证配置
        print(f"\n🔍 配置验证:")
        if validate_config():
            print("  ✅ 基本配置验证通过")
            return True
        else:
            print("  ⚠️  配置验证有警告，请检查")
            return False
    
    def run(
        self,
        repo_owner: Optional[str] = None,
        repo_name: Optional[str] = None,
        email: Optional[str] = None,
        full_sync: bool = False,
        skip_email: bool = False,
        skip_sync: bool = False,
        skip_report: bool = False,
        supplement_relations: bool = False,
        multi_report: bool = False,
        extensible_report: bool = False,
        ai_report: bool = False,
        run_backup: bool = False
    ) -> bool:
        """
        运行完整流程
        
        参数:
        - repo_owner: 仓库所有者
        - repo_name: 仓库名称
        - email: 收件人邮箱
        - full_sync: 是否全量同步
        - skip_email: 是否跳过邮件发送
        - skip_sync: 是否跳过同步
        - skip_report: 是否跳过报告生成
        - supplement_relations: 同步完成后是否执行关联关系补全
        - multi_report: 是否额外生成多维度分析报告（按客户、层级、关联等）
        - ai_report: 是否生成 AI 驱动分析报告（项目推进+横向关联，需含 customer 标签的仓库如 matrixflow）
        - run_backup: 是否在流程结束后执行 MatrixOne 数据库快照备份（定时事项，建议单独或配合 cron 使用）
        
        返回:
        - 是否成功
        """
        # 获取配置值
        repo_owner = repo_owner or self.get_config_value('repo_owner') or self.get_config_value('repo-owner')
        repo_name = repo_name or self.get_config_value('repo_name') or self.get_config_value('repo-name')
        email = email or self.get_config_value('email') or self.get_config_value('report_email') or DEFAULT_EMAIL_TO
        
        if not repo_owner or not repo_name:
            print("❌ 错误: 需要提供仓库信息")
            print("   请使用 --repo-owner 和 --repo-name 参数，或设置配置文件")
            return False
        
        print("=" * 60)
        print(f"🚀 开始运行完整分析流程")
        print(f"仓库: {repo_owner}/{repo_name}")
        if email and not skip_email:
            print(f"收件人: {email}")
        print("=" * 60)
        
        try:
            # 创建调度器
            self.scheduler = IssueManagerScheduler()
            
            # 1. 同步仓库
            if not skip_sync:
                print("\n📥 步骤1: 同步GitHub Issue数据...")
                stats = self.scheduler.sync_repo(repo_owner, repo_name, full_sync=full_sync)
                print(f"✅ 同步完成: 总计 {stats.get('total', 0)} 个，成功 {stats.get('processed', 0)} 个，失败 {stats.get('errors', 0)} 个")

                # 1.5 关联关系补全（可选，用于补充旧流程中因顺序跳过的关联）
                if supplement_relations:
                    print("\n🔗 步骤1.5: 关联关系补全...")
                    run_supplement(repo_owner, repo_name, clear_first=False, quiet=False)
            else:
                print("\n⏭️  跳过同步步骤")

            # 1.5 关联关系补全（跳过同步时也可单独执行，用于修复历史遗漏）
            if skip_sync and supplement_relations:
                print("\n🔗 步骤1.5: 关联关系补全...")
                run_supplement(repo_owner, repo_name, clear_first=False, quiet=False)
            
            # 2. 生成报告
            if not skip_report:
                print("\n📊 步骤2: 生成分析报告...")
                daily_report = self.scheduler.analyzer.generate_daily_report(repo_owner, repo_name)
                progress_report = self.scheduler.analyzer.generate_progress_report(repo_owner, repo_name)
                print("✅ 报告生成完成")
            else:
                print("\n⏭️  跳过报告生成步骤")
                daily_report = None
                progress_report = None

            # 2.5 多维度分析报告（可选，失败不影响邮件发送）
            # 2.6 可扩展分析报告（可选，配置驱动：标签/模块/趋势等）
            # 2.7 AI 驱动分析（可选，项目推进+横向关联；分析 matrixone 和 matrixflow 两个仓库，邮件中 matrixflow 优先展示）
            comprehensive_report = None
            ai_analysis_report = None
            if ai_report:
                try:
                    print("\n📊 步骤2.7: 生成 AI 驱动分析报告（matrixone + matrixflow）...")
                    from modules.database_storage.mo_client import MOStorage
                    from modules.ai_analysis.ai_driven_analysis_engine import AIAnalysisEngine
                    _storage = MOStorage()
                    _ai_engine = AIAnalysisEngine(_storage)
                    # 分析两个仓库，邮件中 matrixflow 优先（用户更关注 matrixflow）
                    _repos = [
                        ("matrixorigin", "matrixflow"),  # 优先
                        ("matrixorigin", "matrixone"),
                    ]
                    _by_repo = {}
                    for _o, _n in _repos:
                        try:
                            _proj = _ai_engine.analyze_project_progress(_o, _n)
                            _cross = _ai_engine.analyze_cross_customer_patterns(_o, _n)
                            _by_repo[f"{_o}/{_n}"] = {"project_progress": _proj, "cross_patterns": _cross}
                        except Exception as _e:
                            print(f"⚠️  {_o}/{_n} AI 分析失败: {_e}")
                    ai_analysis_report = {"by_repo": _by_repo, "order": [f"{_o}/{_n}" for _o, _n in _repos]}
                    print("✅ AI 驱动分析报告完成")
                except Exception as e:
                    print(f"⚠️  AI 驱动分析失败: {e}")
                    import traceback
                    traceback.print_exc()
            if extensible_report:
                try:
                    print("\n📊 步骤2.6: 生成可扩展分析报告...")
                    from modules.analysis_extensible.analysis_engine import ExtensibleAnalysisEngine
                    ext_engine = ExtensibleAnalysisEngine()
                    comprehensive_report = ext_engine.run(repo_owner=repo_owner, repo_name=repo_name)
                    print("✅ 可扩展分析报告完成")
                except Exception as e:
                    print(f"⚠️  可扩展分析失败: {e}")
                    import traceback
                    traceback.print_exc()
            if multi_report:
                try:
                    print("\n📊 步骤2.5: 生成多维度分析报告...")
                    from modules.database_storage.mo_client import MOStorage
                    from modules.report_generator.improved_report_gen import ImprovedReportGenerator
                    storage = MOStorage()
                    multi_gen = ImprovedReportGenerator(storage)
                    multi_gen.generate_all_reports(repo_owner, repo_name)
                    print("✅ 多维度报告生成完成")
                except Exception as e:
                    print(f"⚠️  多维度报告生成失败: {e}")
                    print("⚠️  多维度报告失败不影响邮件发送，继续执行...")
                    import traceback
                    traceback.print_exc()
            
            # 3. 发送邮件（即使多维度报告失败也会执行）
            if not skip_email:
                print("\n📧 步骤3: 发送邮件报告...")
                if not SMTP_USER or not SMTP_PASSWORD:
                    print("⚠️  邮件配置不完整，无法发送邮件")
                    print("   请配置 SMTP_USER 和 SMTP_PASSWORD 环境变量")
                    print("   报告已保存在 data/reports/ 目录")
                else:
                    if not email:
                        print("⚠️  未指定收件人邮箱，跳过邮件发送")
                    else:
                        print(f"   收件人: {email}")
                        sender = EmailSender()
                        success = sender.send_report(
                            to_email=email,
                            daily_report=daily_report,
                            progress_report=progress_report,
                            repo_owner=repo_owner,
                            repo_name=repo_name,
                            attach_json=True,
                            comprehensive_report=comprehensive_report,
                            ai_analysis_report=ai_analysis_report
                        )
                        
                        if success:
                            print(f"\n✅ 所有任务完成！邮件已发送到 {email}")
                        else:
                            print(f"\n❌ 邮件发送失败，但报告已保存在 data/reports/ 目录")
            else:
                print("\n⏭️  跳过邮件发送（报告已保存在 data/reports/ 目录）")
            
            # 4. 数据库备份（单独定时事项，可选在本流程中执行）
            if run_backup:
                print("\n💾 步骤4: MatrixOne 数据库快照备份...")
                try:
                    import subprocess
                    backup_script = os.path.join(os.path.dirname(__file__), "scripts", "backup_matrixone.py")
                    rc = subprocess.run(
                        [sys.executable, backup_script],
                        cwd=os.path.dirname(__file__),
                        timeout=120
                    )
                    if rc.returncode == 0:
                        print("✅ 数据库快照备份完成")
                    else:
                        print("⚠️  数据库备份脚本返回非零，请查看上方输出或 docs/matrixone/MatrixOne备份与恢复.md")
                except subprocess.TimeoutExpired:
                    print("⚠️  数据库备份超时")
                except Exception as e:
                    print(f"⚠️  执行数据库备份失败: {e}")
            
            print("\n" + "=" * 60)
            print("✅ 所有任务完成！")
            print("=" * 60)
            return True
                
        except Exception as e:
            print(f"\n❌ 执行失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def run_both_repos(
        self,
        email: Optional[str] = None,
        skip_email: bool = False,
        extensible_report: bool = True,
        ai_report: bool = True
    ) -> bool:
        """
        两仓分开分析（matrixflow、matrixone 各一份日报+进度+可扩展），再 AI 合在一起分析，一封邮件发出。
        不跑同步，仅用已有数据生成报告。
        """
        BOTH_REPOS = [
            ("matrixorigin", "matrixflow"),
            ("matrixorigin", "matrixone"),
        ]
        email = email or self.get_config_value('email') or self.get_config_value('report_email') or DEFAULT_EMAIL_TO
        print("=" * 60)
        print("🚀 两仓分开分析 + 合在一起分析，一封邮件")
        print("   仓库: matrixorigin/matrixflow, matrixorigin/matrixone")
        if email and not skip_email:
            print(f"   收件人: {email}")
        print("=" * 60)
        try:
            self.scheduler = IssueManagerScheduler()
            reports_per_repo = []
            for repo_owner, repo_name in BOTH_REPOS:
                print(f"\n📊 生成报告: {repo_owner}/{repo_name}")
                daily_report = self.scheduler.analyzer.generate_daily_report(repo_owner, repo_name)
                progress_report = self.scheduler.analyzer.generate_progress_report(repo_owner, repo_name)
                comprehensive_report = None
                if extensible_report:
                    try:
                        from modules.analysis_extensible.analysis_engine import ExtensibleAnalysisEngine
                        ext_engine = ExtensibleAnalysisEngine()
                        comprehensive_report = ext_engine.run(repo_owner=repo_owner, repo_name=repo_name)
                    except Exception as e:
                        print(f"⚠️  {repo_owner}/{repo_name} 可扩展分析失败: {e}")
                reports_per_repo.append({
                    "repo_owner": repo_owner,
                    "repo_name": repo_name,
                    "daily_report": daily_report,
                    "progress_report": progress_report,
                    "comprehensive_report": comprehensive_report,
                })
            ai_analysis_report = None
            if ai_report:
                try:
                    print("\n📊 生成 AI 驱动分析（两仓合在一起）...")
                    from modules.database_storage.mo_client import MOStorage
                    from modules.ai_analysis.ai_driven_analysis_engine import AIAnalysisEngine
                    _storage = MOStorage()
                    _ai_engine = AIAnalysisEngine(_storage)
                    _by_repo = {}
                    for _o, _n in BOTH_REPOS:
                        try:
                            _proj = _ai_engine.analyze_project_progress(_o, _n)
                            _cross = _ai_engine.analyze_cross_customer_patterns(_o, _n)
                            _by_repo[f"{_o}/{_n}"] = {"project_progress": _proj, "cross_patterns": _cross}
                        except Exception as _e:
                            print(f"⚠️  {_o}/{_n} AI 分析失败: {_e}")
                    ai_analysis_report = {"by_repo": _by_repo, "order": [f"{_o}/{_n}" for _o, _n in BOTH_REPOS]}
                    print("✅ AI 驱动分析完成")
                except Exception as e:
                    print(f"⚠️  AI 驱动分析失败: {e}")
            if not skip_email and email:
                print("\n📧 发送邮件（多仓库合并）...")
                if not SMTP_USER or not SMTP_PASSWORD:
                    print("⚠️  邮件配置不完整，无法发送")
                else:
                    sender = EmailSender()
                    success = sender.send_report_multi_repos(
                        to_email=email,
                        reports_per_repo=reports_per_repo,
                        ai_analysis_report=ai_analysis_report,
                        attach_json=True
                    )
                    if success:
                        print(f"\n✅ 邮件已发送到 {email}")
                    else:
                        print("\n❌ 邮件发送失败")
            else:
                print("\n⏭️  跳过邮件发送")
            print("\n" + "=" * 60)
            print("✅ 两仓分析完成")
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
        description="GitHub Issue 智能管理系统 - 可配置自动运行脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用配置文件
  python3 auto_run.py --config config.json
  
  # 使用命令行参数
  python3 auto_run.py --repo-owner matrixorigin --repo-name matrixone --email user@example.com
  
  # 使用环境变量
  export REPO_OWNER=matrixorigin
  export REPO_NAME=matrixone
  export REPORT_EMAIL=user@example.com
  python3 auto_run.py
  
  # 只同步，不生成报告和发送邮件
  python3 auto_run.py --repo-owner matrixorigin --repo-name matrixone --skip-report --skip-email
  
  # 只生成报告，不同步和发送邮件
  python3 auto_run.py --repo-owner matrixorigin --repo-name matrixone --skip-sync --skip-email

  # 同步完成后自动执行关联关系补全
  python3 auto_run.py --repo-owner matrixorigin --repo-name matrixone --supplement-relations

  # 额外生成多维度分析报告
  python3 auto_run.py --repo-owner matrixorigin --repo-name matrixflow --multi-report
        """
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="配置文件路径（JSON或YAML格式）"
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
        help="收件人邮箱"
    )
    parser.add_argument(
        "--full-sync",
        action="store_true",
        help="执行全量同步（清空旧数据）"
    )
    parser.add_argument(
        "--skip-email",
        action="store_true",
        help="跳过邮件发送"
    )
    parser.add_argument(
        "--skip-sync",
        action="store_true",
        help="跳过数据同步"
    )
    parser.add_argument(
        "--skip-report",
        action="store_true",
        help="跳过报告生成"
    )
    parser.add_argument(
        "--supplement-relations",
        action="store_true",
        help="同步完成后自动执行关联关系补全（补充因顺序跳过的关联）"
    )
    parser.add_argument(
        "--multi-report",
        action="store_true",
        help="额外生成多维度分析报告（按客户、层级、关联等）"
    )
    parser.add_argument(
        "--extensible-report",
        action="store_true",
        help="额外生成可扩展分析报告（标签、模块、趋势等，配置驱动）"
    )
    parser.add_argument(
        "--ai-report",
        action="store_true",
        help="额外生成 AI 驱动分析报告（项目推进+横向关联，适用 matrixflow 等含 customer 标签的仓库）"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="仅检查配置，不运行分析"
    )
    parser.add_argument(
        "--run-backup",
        action="store_true",
        help="流程结束后执行 MatrixOne 数据库快照备份（建议作为单独定时事项或配合 cron 使用）"
    )
    parser.add_argument(
        "--both-repos",
        action="store_true",
        help="两仓分开分析 + AI 合在一起分析，一封邮件发出（matrixflow + matrixone，不跑同步）"
    )
    
    args = parser.parse_args()
    
    # 加载配置
    config = {}
    if args.config:
        try:
            runner = AutoRunner()
            config = runner.load_config_file(args.config)
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            return 1
    
    # 创建运行器
    runner = AutoRunner(config)
    
    # 显示标题
    print("=" * 60)
    print("GitHub Issue 智能管理系统 - 自动运行脚本")
    print("=" * 60)
    
    # 检查配置
    if not runner.check_configuration():
        print("\n⚠️  配置检查有警告，但将继续运行...")
    
    # 如果只是检查配置，则退出
    if args.check_only:
        return 0
    
    # 运行（supplement_relations 支持配置文件）
    supplement_relations = args.supplement_relations or (
        runner.get_config_value('supplement_relations') in (True, 'true', '1')
    )
    multi_report = args.multi_report or (
        runner.get_config_value('multi_report') in (True, 'true', '1')
    )
    extensible_report = args.extensible_report or (
        runner.get_config_value('extensible_report') in (True, 'true', '1')
    )
    ai_report = args.ai_report or (
        runner.get_config_value('ai_report') in (True, 'true', '1')
    )
    # 默认开启丰富版邮件（可扩展分析 + AI 分析）；仅当配置显式设为 false 时关闭
    if not extensible_report and runner.get_config_value('extensible_report') not in (False, 'false', '0'):
        extensible_report = True
    if not ai_report and runner.get_config_value('ai_report') not in (False, 'false', '0'):
        ai_report = True
    # 未指定邮箱时使用默认收件人
    email = args.email or DEFAULT_EMAIL_TO
    run_backup = args.run_backup or (
        runner.get_config_value('run_backup') in (True, 'true', '1')
    )
    if args.both_repos:
        success = runner.run_both_repos(
            email=email,
            skip_email=args.skip_email,
            extensible_report=extensible_report,
            ai_report=True
        )
    else:
        success = runner.run(
            repo_owner=args.repo_owner,
            repo_name=args.repo_name,
            email=email,
            full_sync=args.full_sync,
            skip_email=args.skip_email,
            skip_sync=args.skip_sync,
            skip_report=args.skip_report,
            supplement_relations=supplement_relations,
            multi_report=multi_report,
            extensible_report=extensible_report,
            ai_report=ai_report,
            run_backup=run_backup
        )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
