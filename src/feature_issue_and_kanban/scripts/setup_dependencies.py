#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动检测环境并安装依赖
本地和云端都能使用
"""
import os
import sys
import subprocess
import platform
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIK_ROOT = ROOT / "feature_issue_and_kanban"
REQ_DIR = FIK_ROOT / "requirements"


def detect_environment():
    if os.path.exists("/.dockerenv"):
        return "docker"
    if os.getenv("CLOUD_DEPLOYMENT", "").lower() in ("true", "1", "yes"):
        return "cloud"
    if any(os.getenv(k) for k in ("AWS_EXECUTION_ENV", "KUBERNETES_SERVICE_HOST", "ALIYUN_ECS")):
        return "cloud"
    return "local"


def install_from_file(filename: str) -> bool:
    path = REQ_DIR / filename
    if not path.exists():
        print(f"⚠️  文件不存在: {path}")
        return False
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", str(path), "-q"
        ])
        print(f"✅ {filename} 安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {filename} 安装失败: {e}")
        return False


def get_recommended_command() -> str:
    """根据系统给出推荐运行命令"""
    plat = platform.system().lower()
    if plat == "darwin":
        return "python3"  # macOS 通常只有 python3
    if plat == "linux":
        return "python3"  # 常见 Linux 发行版
    return "python"  # Windows 常用 python


def main():
    env = detect_environment()
    plat = platform.system().lower()
    cmd = get_recommended_command()
    print(f"🔍 检测到环境: {env}")
    print(f"🔍 平台: {plat}")
    print(f"💡 推荐命令: {cmd} 或使用 ./scripts/setup_dependencies.sh")

    print("\n📦 安装核心依赖...")
    install_from_file("requirements-core.txt")

    if env == "local":
        print("\n📦 安装本地监控依赖...")
        install_from_file("requirements-local.txt")
    elif env in ("cloud", "docker"):
        print("\n📦 安装云端依赖...")
        install_from_file("requirements-cloud.txt")

    print("\n✅ 依赖安装完成")


if __name__ == "__main__":
    main()
