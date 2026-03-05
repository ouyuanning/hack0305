#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一配置管理
自动适配本地和云端
"""
from .environment import get_env


class ConfigManager:
    """配置管理器"""

    def __init__(self):
        self.env = get_env()

    def get_ai_config(self) -> dict:
        return {
            "api_key": self.env.config.get("qwen_api_key", ""),
            "model": "qwen-plus",
            "timeout": 30,
        }

    def get_github_config(self) -> dict:
        return {
            "token": self.env.config.get("github_token", ""),
            "api_base": "https://api.github.com",
        }

    def get_monitoring_config(self) -> dict:
        return self.env.get_feature_config("monitoring")

    def get_image_upload_config(self) -> dict:
        return self.env.get_feature_config("image_upload")

    def get_cache_config(self) -> dict:
        return self.env.get_feature_config("cache")

    def is_feature_available(self, feature: str) -> bool:
        return self.env.capabilities.get(feature, False)


# 全局实例
_config: "ConfigManager | None" = None


def get_config() -> ConfigManager:
    global _config
    if _config is None:
        _config = ConfigManager()
    return _config
