# -*- coding: utf-8 -*-
"""分析器基类"""

import json
from typing import Dict, List, Any


class BaseAnalyzer:
    """分析器基类 - 所有分析器继承此类"""

    def __init__(self, storage, config: Dict):
        self.storage = storage
        self.config = config or {}
        self.results = {}

    def analyze(self, issues: List[Dict]) -> Dict:
        """执行分析 - 子类必须实现"""
        raise NotImplementedError

    def _parse_labels(self, labels) -> List:
        """解析 labels 字段"""
        if not labels:
            return []
        if isinstance(labels, list):
            return labels
        try:
            return json.loads(labels) if isinstance(labels, str) else []
        except (json.JSONDecodeError, TypeError):
            return []

    def _parse_json_field(self, val):
        """解析 JSON 字段"""
        if val is None:
            return None
        if isinstance(val, (list, dict)):
            return val
        try:
            return json.loads(val) if isinstance(val, str) else val
        except (json.JSONDecodeError, TypeError):
            return None
