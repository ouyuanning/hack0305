#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据库连接脚本
用于诊断 MatrixOne 数据库连接问题
"""

import sys
import os
# 添加项目根目录到路径（支持从 scripts/ 运行）
_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_dir)
sys.path.insert(0, _root)

from config.config import (
    MATRIXONE_HOST, MATRIXONE_PORT, MATRIXONE_USER, 
    MATRIXONE_PASSWORD, MATRIXONE_DATABASE, DATABASE_TYPE
)
import pymysql
from sqlalchemy import create_engine, text

def test_pymysql_connection():
    """测试直接使用 pymysql 连接"""
    print("=" * 60)
    print("测试1: 直接使用 pymysql 连接")
    print("=" * 60)
    print(f"主机: {MATRIXONE_HOST}")
    print(f"端口: {MATRIXONE_PORT}")
    print(f"用户: {MATRIXONE_USER}")
    print(f"数据库: {MATRIXONE_DATABASE}")
    print("-" * 60)
    
    try:
        connection = pymysql.connect(
            host=MATRIXONE_HOST,
            port=int(MATRIXONE_PORT),
            user=MATRIXONE_USER,
            password=MATRIXONE_PASSWORD,
            database=MATRIXONE_DATABASE,
            connect_timeout=10,
            charset='utf8mb4',
            read_timeout=30,
            write_timeout=30
        )
        print("✅ pymysql 连接成功！")
        
        # 测试查询
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"✅ 数据库版本: {version[0]}")
            
            cursor.execute("SELECT DATABASE()")
            db = cursor.fetchone()
            print(f"✅ 当前数据库: {db[0]}")
        
        connection.close()
        return True
    except Exception as e:
        print(f"❌ pymysql 连接失败: {type(e).__name__}: {e}")
        return False

def test_sqlalchemy_connection():
    """测试使用 SQLAlchemy 连接"""
    print("\n" + "=" * 60)
    print("测试2: 使用 SQLAlchemy 连接")
    print("=" * 60)
    
    from config.config import get_database_url
    
    database_url = get_database_url()
    print(f"连接URL: {database_url.replace(MATRIXONE_PASSWORD, '****')}")
    print("-" * 60)
    
    try:
        connect_args = {
            "connect_timeout": 10,
            "charset": "utf8mb4",
            "read_timeout": 30,
            "write_timeout": 30,
        }
        
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            connect_args=connect_args
        )
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT VERSION()"))
            version = result.fetchone()
            print(f"✅ SQLAlchemy 连接成功！")
            print(f"✅ 数据库版本: {version[0]}")
        
        return True
    except Exception as e:
        print(f"❌ SQLAlchemy 连接失败: {type(e).__name__}: {e}")
        import traceback
        print("\n详细错误信息:")
        traceback.print_exc()
        return False

def test_dns_resolution():
    """测试 DNS 解析"""
    print("\n" + "=" * 60)
    print("测试3: DNS 解析测试")
    print("=" * 60)
    
    import socket
    try:
        ip = socket.gethostbyname(MATRIXONE_HOST)
        print(f"✅ DNS 解析成功: {MATRIXONE_HOST} -> {ip}")
        return True
    except socket.gaierror as e:
        print(f"❌ DNS 解析失败: {e}")
        print(f"   错误代码: {e.errno}")
        print(f"   错误信息: {e.strerror}")
        return False
    except Exception as e:
        print(f"❌ DNS 解析异常: {type(e).__name__}: {e}")
        return False

def test_port_connection():
    """测试端口连接"""
    print("\n" + "=" * 60)
    print("测试4: 端口连接测试")
    print("=" * 60)
    
    import socket
    try:
        ip = socket.gethostbyname(MATRIXONE_HOST)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((ip, int(MATRIXONE_PORT)))
        sock.close()
        
        if result == 0:
            print(f"✅ 端口 {MATRIXONE_PORT} 连接成功")
            return True
        else:
            print(f"❌ 端口 {MATRIXONE_PORT} 连接失败 (错误代码: {result})")
            return False
    except Exception as e:
        print(f"❌ 端口连接测试异常: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("MatrixOne 数据库连接诊断工具")
    print("=" * 60)
    print(f"数据库类型: {DATABASE_TYPE}")
    print()
    
    results = []
    
    # 测试 DNS 解析
    results.append(("DNS解析", test_dns_resolution()))
    
    # 如果 DNS 解析成功，测试端口连接
    if results[0][1]:
        results.append(("端口连接", test_port_connection()))
    
    # 测试数据库连接
    results.append(("pymysql连接", test_pymysql_connection()))
    results.append(("SQLAlchemy连接", test_sqlalchemy_connection()))
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    print("\n" + "=" * 60)
    if all(r[1] for r in results):
        print("🎉 所有测试通过！数据库连接正常。")
    else:
        print("⚠️  部分测试失败，请检查网络连接和配置。")
    print("=" * 60)
