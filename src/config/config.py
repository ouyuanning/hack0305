#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一配置文件
所有API和数据库配置都在这里，方便修改和替换
"""

import os
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

# 获取项目根目录
BASE_DIR = Path(__file__).parent.parent

# 加载 .env 文件（如果存在）
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    with open(_env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

# ==================== GitHub API 配置 ====================
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
# 如果上面的环境变量没有设置，可以在这里直接填写
# GITHUB_TOKEN = "ghp_xxxxxxxxxxxxxxxxxxxx"

GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_RATE_LIMIT_RETRY = 3  # API限流重试次数

# ==================== AI API 配置 ====================
# 支持的AI服务提供商：openai, claude, qwen, local
# 如果设置为 "qwen" 或 "claude"，将优先使用千问，失败时自动回退到Claude
AI_PROVIDER = os.getenv("AI_PROVIDER", "qwen")  # 可选: openai, claude, qwen, local

# OpenAI 配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

# Claude 配置
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
CLAUDE_BASE_URL = os.getenv("CLAUDE_BASE_URL", "https://api.anthropic.com/v1")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-sonnet-20240229")

# 通义千问配置（阿里云百炼）
# 优先使用 DASHSCOPE_API_KEY（官方推荐），向后兼容 QWEN_API_KEY
# 获取API Key：https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen#f0577378e8sz4
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", os.getenv("QWEN_API_KEY", ""))
QWEN_API_KEY = DASHSCOPE_API_KEY  # 保持向后兼容
# 使用兼容模式API地址（推荐），支持OpenAI兼容接口
# 也可以使用标准API：https://dashscope.aliyuncs.com/api/v1
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-plus")  # 推荐使用 qwen-plus 或 qwen-max-latest

# 本地模型配置（如果使用本地部署的模型）
LOCAL_MODEL_URL = os.getenv("LOCAL_MODEL_URL", "http://localhost:8000/v1")
LOCAL_MODEL_NAME = os.getenv("LOCAL_MODEL_NAME", "local-model")

# ==================== 数据库配置 ====================
# 数据库类型：postgresql, mysql, sqlite, matrixone
DATABASE_TYPE = os.getenv("DATABASE_TYPE", "matrixone")

# PostgreSQL 配置
POSTGRESQL_HOST = os.getenv("POSTGRESQL_HOST", "localhost")
POSTGRESQL_PORT = os.getenv("POSTGRESQL_PORT", "5432")
POSTGRESQL_USER = os.getenv("POSTGRESQL_USER", "postgres")
POSTGRESQL_PASSWORD = os.getenv("POSTGRESQL_PASSWORD", "password")
POSTGRESQL_DATABASE = os.getenv("POSTGRESQL_DATABASE", "github_issues")

# MySQL 配置
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "password")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "github_issues")

# SQLite 配置（用于测试）
SQLITE_PATH = os.getenv("SQLITE_PATH", str(BASE_DIR / "data" / "github_issues.db"))

# MatrixOne 配置
# 使用控制台提供的连接地址：freetier-01.cn-hangzhou.cluster.matrixonecloud.cn
MATRIXONE_HOST = os.getenv("MATRIXONE_HOST", "freetier-01.cn-hangzhou.cluster.matrixonecloud.cn")
MATRIXONE_PORT = os.getenv("MATRIXONE_PORT", "6001")
# 用户名格式：实例ID:admin:accountadmin
MATRIXONE_USER = os.getenv("MATRIXONE_USER", "019c3caf-ae5a-7ced-ac5b-37d070f153f5:admin:accountadmin")
MATRIXONE_PASSWORD = os.getenv("MATRIXONE_PASSWORD", "")
MATRIXONE_DATABASE = os.getenv("MATRIXONE_DATABASE", "github_issues")

# 数据库连接池配置
DB_POOL_SIZE = 10
DB_MAX_OVERFLOW = 20
DB_POOL_PRE_PING = True

# ==================== 获取数据库连接URL ====================
def get_database_url() -> str:
    """根据配置的数据库类型返回连接URL"""
    if DATABASE_TYPE == "postgresql":
        return f"postgresql://{POSTGRESQL_USER}:{POSTGRESQL_PASSWORD}@{POSTGRESQL_HOST}:{POSTGRESQL_PORT}/{POSTGRESQL_DATABASE}"
    elif DATABASE_TYPE == "mysql":
        return f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
    elif DATABASE_TYPE == "sqlite":
        return f"sqlite:///{SQLITE_PATH}"
    elif DATABASE_TYPE == "matrixone":
        # MatrixOne 使用 MySQL 协议
        # 用户名可能包含冒号，需要进行 URL 编码
        encoded_user = quote_plus(MATRIXONE_USER)
        encoded_password = quote_plus(MATRIXONE_PASSWORD)
        return f"mysql+pymysql://{encoded_user}:{encoded_password}@{MATRIXONE_HOST}:{MATRIXONE_PORT}/{MATRIXONE_DATABASE}"
    else:
        raise ValueError(f"不支持的数据库类型: {DATABASE_TYPE}")

# ==================== 其他配置 ====================
# 日志配置
LOG_DIR = BASE_DIR / "logs"
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR

# 数据目录
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# 是否启用全量重新运行（清空旧数据）
ENABLE_FULL_RESYNC = os.getenv("ENABLE_FULL_RESYNC", "false").lower() == "true"

# 全量同步时是否跳过清空：True=全量拉取后直接写入（比对/覆盖），False=先清空再全量写入（默认，保持原行为）
FULL_SYNC_SKIP_CLEAR = os.getenv("FULL_SYNC_SKIP_CLEAR", "false").lower() == "true"

# MatrixOne 快照备份保留天数：超过 N 天的快照在创建新快照后自动 DROP；0 表示不自动删除
BACKUP_SNAPSHOT_RETENTION_DAYS = int(os.getenv("BACKUP_SNAPSHOT_RETENTION_DAYS", "7"))

# Issue 关联关系提取配置
EXTRACT_RELATIONS = True  # 是否提取Issue之间的关联关系

# 报告生成配置
REPORT_OUTPUT_DIR = BASE_DIR / "data" / "reports"
REPORT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ==================== 邮件配置 ====================
# SMTP服务器配置
# 常用邮箱SMTP设置：
# Gmail: smtp.gmail.com:587 (TLS) 或 465 (SSL)
# Outlook: smtp-mail.outlook.com:587
# QQ邮箱: smtp.qq.com:587 或 465
# 163邮箱: smtp.163.com:465 (SSL) 或 587 (TLS)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.163.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))  # 163 推荐 465 (SSL)
SMTP_USER = os.getenv("SMTP_USER", "AaronTest20260222@163.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")  # 163 授权码

# 发件人信息
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER)  # 发件人邮箱
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "GitHub Issue 智能管理系统")  # 发件人名称

# 默认收件人（可选）
DEFAULT_EMAIL_TO = os.getenv("DEFAULT_EMAIL_TO", "wupeng@matrixorigin.cn")

# ==================== 验证配置 ====================
def validate_config():
    """验证配置是否完整"""
    errors = []
    
    if GITHUB_TOKEN == "your_github_token_here":
        errors.append("⚠️  请设置 GITHUB_TOKEN")
    
    if AI_PROVIDER == "openai" and OPENAI_API_KEY == "your_openai_api_key_here":
        errors.append("⚠️  请设置 OPENAI_API_KEY")
    elif AI_PROVIDER == "claude" and CLAUDE_API_KEY == "your_claude_api_key_here":
        errors.append("⚠️  请设置 CLAUDE_API_KEY")
    elif AI_PROVIDER == "qwen":
        # 检查 DASHSCOPE_API_KEY 或 QWEN_API_KEY
        if not DASHSCOPE_API_KEY or DASHSCOPE_API_KEY in ["your_qwen_api_key_here", "your_dashscope_api_key_here"]:
            errors.append("⚠️  请设置 DASHSCOPE_API_KEY 或 QWEN_API_KEY（推荐使用 DASHSCOPE_API_KEY）")
            errors.append("   获取方式：https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen#f0577378e8sz4")
    
    if errors:
        print("\n".join(errors))
        print("\n💡 提示：可以在 config/config.py 文件中直接修改配置，或者设置环境变量")
        return False
    
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("GitHub Issue 智能管理系统 - 配置检查")
    print("=" * 50)
    print(f"GitHub Token: {'已设置' if GITHUB_TOKEN != 'your_github_token_here' else '❌ 未设置'}")
    print(f"AI Provider: {AI_PROVIDER}")
    print(f"Database Type: {DATABASE_TYPE}")
    print(f"Database URL: {get_database_url()}")
    print("=" * 50)
    validate_config()
