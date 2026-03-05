#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境检测与自动配置
自动识别本地/云端环境，加载对应配置
"""
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# 项目根目录
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class Environment:
    """环境管理器"""

    def __init__(self):
        self.env_type = self._detect_environment()
        self.platform = sys.platform

        # 自动加载配置
        self.config = self._load_config()

        # 检测可用功能
        self.capabilities = self._detect_capabilities()

    def _detect_environment(self) -> str:
        """检测环境类型"""
        if os.path.exists("/.dockerenv"):
            return "docker"

        if os.getenv("CLOUD_DEPLOYMENT", "").lower() in ("true", "1", "yes"):
            return "cloud"

        if os.getenv("AWS_EXECUTION_ENV"):
            return "aws"

        if os.getenv("ALIYUN_ECS"):
            return "aliyun"

        if os.getenv("KUBERNETES_SERVICE_HOST"):
            return "k8s"

        return "local"

    def _load_config(self) -> Dict[str, Any]:
        """
        加载配置
        优先级：环境变量 > 主项目 config.config > 默认值
        """
        config: Dict[str, Any] = {}

        # 1. 从主项目 config 或环境变量
        try:
            from config.config import GITHUB_TOKEN, DASHSCOPE_API_KEY, QWEN_API_KEY
            config["github_token"] = os.getenv("GITHUB_TOKEN") or GITHUB_TOKEN
            config["qwen_api_key"] = os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY") or DASHSCOPE_API_KEY or QWEN_API_KEY
        except ImportError:
            config["github_token"] = os.getenv("GITHUB_TOKEN", "")
            config["qwen_api_key"] = os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY", "")

        # 2. 监控配置（云端默认禁用；本地默认开启，用于监听浏览器等）
        if self.env_type in ("cloud", "aws", "aliyun", "k8s", "docker"):
            config["monitor_enabled"] = False
        else:
            config["monitor_enabled"] = os.getenv("MONITOR_ENABLED", "true").lower() in ("true", "1", "yes")

        # 3. 存储配置
        if self.env_type in ("cloud", "aws", "aliyun", "k8s", "docker"):
            config["storage_type"] = "cloud"
            config["s3_bucket"] = os.getenv("S3_BUCKET", "issue-assistant-images")
            config["s3_region"] = os.getenv("AWS_REGION", "us-west-2")
        else:
            config["storage_type"] = "imgur"
            config["imgur_client_id"] = os.getenv("IMGUR_CLIENT_ID", "")

        # 4. 缓存配置
        if self.env_type in ("cloud", "k8s", "docker"):
            config["cache_type"] = "redis"
            config["redis_url"] = os.getenv("REDIS_URL", "redis://localhost:6379")
        else:
            config["cache_type"] = "memory"

        return config

    def _detect_capabilities(self) -> Dict[str, bool]:
        """检测可用功能"""
        caps = {
            "core": True,
            "monitoring": False,
            "browser_debug": False,
            "image_upload": bool(self.config.get("imgur_client_id") or self.config.get("s3_bucket")),
            "cache": True,
        }

        # 监控（仅本地）
        if self.env_type == "local" and self.config.get("monitor_enabled"):
            try:
                if self.platform == "darwin":
                    import Quartz  # noqa: F401
                    caps["monitoring"] = True
                elif self.platform == "win32":
                    import pywinauto  # noqa: F401
                    caps["monitoring"] = True
            except ImportError:
                pass

        # Chrome 调试（仅本地）
        if self.env_type == "local":
            try:
                import requests
                r = requests.get("http://localhost:9222/json", timeout=1)
                if r.status_code == 200:
                    caps["browser_debug"] = True
            except Exception:
                pass

        return caps

    def get_feature_config(self, feature: str) -> Dict[str, Any]:
        """获取特定功能配置"""
        if feature == "monitoring":
            return {
                "enabled": self.capabilities["monitoring"],
                "browser": self.capabilities["browser_debug"],
                "terminal": self.env_type == "local",
            }
        if feature == "image_upload":
            if self.config.get("storage_type") == "cloud":
                return {
                    "enabled": True,
                    "type": "s3",
                    "bucket": self.config.get("s3_bucket"),
                    "region": self.config.get("s3_region"),
                }
            return {
                "enabled": self.capabilities["image_upload"],
                "type": "imgur",
                "client_id": self.config.get("imgur_client_id"),
            }
        if feature == "cache":
            if self.config.get("cache_type") == "redis":
                return {"enabled": True, "type": "redis", "url": self.config.get("redis_url")}
            return {"enabled": True, "type": "memory"}
        return {"enabled": False}

    def print_environment_info(self) -> None:
        """打印环境信息（调试用）"""
        print("=" * 60)
        print("🌍 环境信息")
        print("=" * 60)
        print(f"环境类型: {self.env_type}")
        print(f"平台: {self.platform}")
        print("可用功能:")
        for k, v in self.capabilities.items():
            print(f"  {'✅' if v else '❌'} {k}")
        print("=" * 60)


# 全局实例
_env: Optional[Environment] = None


def get_env() -> Environment:
    global _env
    if _env is None:
        _env = Environment()
    return _env
