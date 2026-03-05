#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置检查脚本
快速检查所有配置项是否正确设置
"""

import sys
import socket
from pathlib import Path

# 添加项目根目录到路径（支持从 scripts/ 运行）
_script = Path(__file__).resolve()
_root = _script.parent.parent
sys.path.insert(0, str(_root))

try:
    from config.config import *
except ImportError as e:
    print(f"❌ 导入配置失败: {e}")
    sys.exit(1)

def check_python_packages():
    """检查Python依赖包"""
    print("\n" + "="*60)
    print("📦 检查Python依赖包")
    print("="*60)
    
    packages = {
        "httpx": "HTTP请求库",
        "sqlalchemy": "数据库ORM",
        "psycopg2": "PostgreSQL驱动（可选）",
        "pymysql": "MySQL/MatrixOne驱动",
        "anthropic": "Claude SDK",
        "openai": "OpenAI SDK（可选）",
        "dashscope": "通义千问SDK（可选）",
        "python-dotenv": "环境变量管理",
    }
    
    missing = []
    installed = []
    
    for package, desc in packages.items():
        try:
            if package == "psycopg2":
                __import__("psycopg2")
            elif package == "pymysql":
                __import__("pymysql")
            elif package == "anthropic":
                __import__("anthropic")
            elif package == "openai":
                __import__("openai")
            elif package == "dashscope":
                __import__("dashscope")
            elif package == "python-dotenv":
                __import__("dotenv")
            else:
                __import__(package)
            
            installed.append(f"✅ {package:20s} - {desc}")
        except ImportError:
            if package in ["anthropic"] and AI_PROVIDER == "claude":
                missing.append(f"❌ {package:20s} - {desc} (必须安装)")
            elif package in ["sqlalchemy"]:
                missing.append(f"❌ {package:20s} - {desc} (必须安装)")
            elif package in ["pymysql"] and DATABASE_TYPE in ["mysql", "matrixone"]:
                missing.append(f"❌ {package:20s} - {desc} (必须安装，用于{DATABASE_TYPE})")
            elif package in ["psycopg2"] and DATABASE_TYPE == "postgresql":
                missing.append(f"❌ {package:20s} - {desc} (必须安装，用于PostgreSQL)")
            else:
                print(f"⚠️  {package:20s} - {desc} (未安装，可选)")
    
    for item in installed:
        print(item)
    
    for item in missing:
        print(item)
    
    return len(missing) == 0

def check_github_config():
    """检查GitHub配置"""
    print("\n" + "="*60)
    print("🔗 检查GitHub配置")
    print("="*60)
    
    if GITHUB_TOKEN and GITHUB_TOKEN != "your_github_token_here":
        print(f"✅ GitHub Token: 已设置 ({GITHUB_TOKEN[:10]}...)")
        return True
    else:
        print("❌ GitHub Token: 未设置")
        return False

def check_ai_config():
    """检查AI配置"""
    print("\n" + "="*60)
    print(f"🤖 检查AI配置 ({AI_PROVIDER})")
    print("="*60)
    
    if AI_PROVIDER == "claude":
        if CLAUDE_API_KEY and CLAUDE_API_KEY != "your_claude_api_key_here":
            print(f"✅ Claude API Key: 已设置 ({CLAUDE_API_KEY[:20]}...)")
            print(f"✅ Claude Model: {CLAUDE_MODEL}")
            return True
        else:
            print("❌ Claude API Key: 未设置")
            return False
    elif AI_PROVIDER == "openai":
        if OPENAI_API_KEY and OPENAI_API_KEY != "your_openai_api_key_here":
            print(f"✅ OpenAI API Key: 已设置")
            print(f"✅ OpenAI Model: {OPENAI_MODEL}")
            return True
        else:
            print("❌ OpenAI API Key: 未设置")
            return False
    elif AI_PROVIDER == "qwen":
        if QWEN_API_KEY and QWEN_API_KEY != "your_qwen_api_key_here":
            print(f"✅ 通义千问 API Key: 已设置")
            print(f"✅ 通义千问 Model: {QWEN_MODEL}")
            return True
        else:
            print("❌ 通义千问 API Key: 未设置")
            return False
    else:
        print(f"⚠️  未知的AI Provider: {AI_PROVIDER}")
        return False

def check_database_config():
    """检查数据库配置"""
    print("\n" + "="*60)
    print(f"💾 检查数据库配置 ({DATABASE_TYPE})")
    print("="*60)
    
    print(f"数据库类型: {DATABASE_TYPE}")
    
    if DATABASE_TYPE == "postgresql":
        print(f"主机: {POSTGRESQL_HOST}")
        print(f"端口: {POSTGRESQL_PORT}")
        print(f"用户: {POSTGRESQL_USER}")
        print(f"数据库: {POSTGRESQL_DATABASE}")
        print(f"密码: {'已设置' if POSTGRESQL_PASSWORD else '未设置'}")
        
        # 尝试连接
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=POSTGRESQL_HOST,
                port=POSTGRESQL_PORT,
                user=POSTGRESQL_USER,
                password=POSTGRESQL_PASSWORD,
                database=POSTGRESQL_DATABASE,
                connect_timeout=3
            )
            conn.close()
            print("✅ PostgreSQL连接: 成功")
            return True
        except psycopg2.OperationalError as e:
            print(f"❌ PostgreSQL连接: 失败")
            print(f"   错误: {str(e)[:100]}")
            print(f"   提示: 请检查PostgreSQL服务是否启动，数据库是否存在")
            return False
        except Exception as e:
            print(f"⚠️  PostgreSQL连接: 无法测试 ({type(e).__name__})")
            return False
    
    elif DATABASE_TYPE == "sqlite":
        sqlite_path = Path(SQLITE_PATH)
        sqlite_dir = sqlite_path.parent
        print(f"数据库路径: {SQLITE_PATH}")
        
        if sqlite_dir.exists() or sqlite_dir == BASE_DIR / "data":
            print("✅ SQLite目录: 存在或可创建")
            return True
        else:
            print(f"⚠️  SQLite目录: {sqlite_dir} 不存在（系统会自动创建）")
            return True
    
    elif DATABASE_TYPE == "mysql":
        print(f"主机: {MYSQL_HOST}")
        print(f"端口: {MYSQL_PORT}")
        print(f"用户: {MYSQL_USER}")
        print(f"数据库: {MYSQL_DATABASE}")
        print("⚠️  MySQL连接: 未测试（请手动验证）")
        return True
    
    elif DATABASE_TYPE == "matrixone":
        print(f"主机: {MATRIXONE_HOST}")
        print(f"端口: {MATRIXONE_PORT}")
        print(f"用户: {MATRIXONE_USER}")
        print(f"数据库: {MATRIXONE_DATABASE}")
        print(f"密码: {'已设置' if MATRIXONE_PASSWORD else '未设置'}")
        
        # 先进行网络诊断
        print("\n🔍 网络诊断:")
        network_ok = True
        
        # 1. DNS 解析测试
        try:
            ip_address = socket.gethostbyname(MATRIXONE_HOST)
            print(f"   ✅ DNS解析: {MATRIXONE_HOST} -> {ip_address}")
        except socket.gaierror as e:
            print(f"   ❌ DNS解析失败: 无法解析主机名 '{MATRIXONE_HOST}'")
            print(f"      错误: {str(e)}")
            print(f"      提示: 请检查主机地址是否正确，或检查网络连接")
            network_ok = False
        
        # 2. 端口连通性测试
        if network_ok:
            try:
                port = int(MATRIXONE_PORT)
                print(f"   🔄 测试端口连通性: {MATRIXONE_HOST}:{MATRIXONE_PORT}...")
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((ip_address, port))
                sock.close()
                
                if result == 0:
                    print(f"   ✅ 端口连通: {MATRIXONE_HOST}:{MATRIXONE_PORT} 可访问")
                else:
                    print(f"   ❌ 端口不通: {MATRIXONE_HOST}:{MATRIXONE_PORT} 无法连接")
                    print(f"      IP地址: {ip_address}")
                    print(f"      错误代码: {result}")
                    network_ok = False
            except socket.timeout:
                print(f"   ❌ 端口连接超时: {MATRIXONE_HOST}:{MATRIXONE_PORT}")
                network_ok = False
            except Exception as e:
                print(f"   ⚠️  端口测试失败: {str(e)}")
                network_ok = False
        
        # 如果网络诊断失败，提供详细的解决方案
        if not network_ok:
            print(f"\n❌ MatrixOne连接: 网络诊断失败，跳过数据库连接测试")
            print(f"\n📋 问题分析:")
            print(f"   • DNS解析成功，说明主机地址正确")
            print(f"   • 端口 {MATRIXONE_PORT} 无法连接，可能原因：")
            print(f"     1. MatrixOne 实例可能已暂停或未启动")
            print(f"     2. 防火墙或安全组阻止了端口 {MATRIXONE_PORT}")
            print(f"     3. 网络环境限制（公司网络、VPN等）")
            print(f"     4. MatrixOne 服务暂时不可用")
            print(f"\n🔧 解决方案:")
            print(f"   1. 登录 MatrixOne 控制台检查实例状态")
            print(f"      - 确认实例是否正常运行")
            print(f"      - 检查实例是否被暂停")
            print(f"      - 查看连接信息是否正确")
            print(f"   2. 检查网络环境")
            print(f"      - 尝试从其他网络环境连接")
            print(f"      - 检查是否需要配置 VPN")
            print(f"      - 检查防火墙/安全组设置")
            print(f"   3. 验证连接信息")
            print(f"      - 主机: {MATRIXONE_HOST}")
            print(f"      - 端口: {MATRIXONE_PORT}")
            print(f"      - 确认这些信息与 MatrixOne 控制台一致")
            print(f"   4. 联系 MatrixOne 支持")
            print(f"      - 如果实例状态正常但仍无法连接，请联系技术支持")
            return False
        
        # 尝试数据库连接
        print("\n🔗 数据库连接测试:")
        try:
            from sqlalchemy import create_engine, text
            from sqlalchemy.exc import OperationalError
            
            # 使用 get_database_url() 获取连接串
            db_url = get_database_url()
            engine = create_engine(db_url, connect_args={"connect_timeout": 10})
            
            # 测试连接
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            print("   ✅ MatrixOne连接: 成功")
            return True
        except ImportError as e:
            print(f"   ❌ MatrixOne连接: 无法测试（缺少依赖: {e}）")
            print(f"      提示: 请安装 pymysql 和 sqlalchemy: pip3 install pymysql sqlalchemy")
            return False
        except OperationalError as e:
            print(f"   ❌ MatrixOne连接: 失败")
            error_msg = str(e)
            if "Unknown database" in error_msg or "doesn't exist" in error_msg:
                print(f"      错误: 数据库 '{MATRIXONE_DATABASE}' 不存在")
                print(f"      提示: 请在 MatrixOne 控制台的 SQL 编辑器中执行:")
                print(f"             CREATE DATABASE {MATRIXONE_DATABASE};")
            elif "Access denied" in error_msg or "password" in error_msg.lower() or "1045" in error_msg:
                print(f"      错误: 用户名或密码错误")
                print(f"      提示: 请检查 config/config.py 中的 MATRIXONE_USER 和 MATRIXONE_PASSWORD")
                print(f"            或检查 MatrixOne 控制台中的用户凭证")
            elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                print(f"      错误: 连接超时")
                print(f"      提示: 虽然网络可达，但数据库连接超时")
                print(f"            可能原因:")
                print(f"            - MatrixOne 服务负载过高")
                print(f"            - 网络延迟过高")
                print(f"            - 数据库实例可能已暂停或不可用")
            elif "Connection refused" in error_msg or "2003" in error_msg:
                print(f"      错误: 连接被拒绝")
                print(f"      提示: 端口可能未开放或服务未启动")
            else:
                print(f"      错误: {error_msg[:150]}")
                print(f"      提示: 请检查 MatrixOne 配置，参考 MatrixOne配置指南.md")
            return False
        except Exception as e:
            print(f"   ⚠️  MatrixOne连接: 无法测试 ({type(e).__name__}: {str(e)[:100]})")
            return False
    
    else:
        print(f"❌ 不支持的数据库类型: {DATABASE_TYPE}")
        return False

def main():
    """主函数"""
    print("="*60)
    print("GitHub Issue 智能管理系统 - 配置检查")
    print("="*60)
    
    results = {
        "Python包": check_python_packages(),
        "GitHub配置": check_github_config(),
        "AI配置": check_ai_config(),
        "数据库配置": check_database_config(),
    }
    
    print("\n" + "="*60)
    print("📊 检查结果汇总")
    print("="*60)
    
    all_ok = True
    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name:15s}: {status}")
        if not result:
            all_ok = False
    
    print("\n" + "="*60)
    if all_ok:
        print("🎉 所有配置检查通过！可以运行系统了。")
        print("\n运行命令: python3 run.py")
    else:
        print("⚠️  部分配置需要修复，请查看上面的详细信息。")
        print("\n💡 提示:")
        print("   1. 安装缺失的依赖: pip3 install -r requirements.txt")
        print("   2. 检查配置文件: config/config.py")
        print("   3. 查看详细报告: 配置检查报告.md")
    print("="*60)

if __name__ == "__main__":
    main()
