# -*- coding: utf-8 -*-
"""HTML 报告（简化版）"""

from pathlib import Path
from datetime import datetime
from typing import Dict


class HTMLFormatter:
    def __init__(self, results: Dict, format_config: Dict, sections: list = None):
        self.results = results
        self.config = format_config or {}
        self.sections = sections or []

    def save(self, output_path: Path):
        path = str(output_path)
        if "{date}" in path:
            path = path.replace("{date}", datetime.now().strftime("%Y%m%d"))
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Issue分析报告</title>
<style>body{{font-family:sans-serif;margin:20px}} table{{border-collapse:collapse}}
th,td{{border:1px solid #ccc;padding:6px}} th{{background:#f0f0f0}}</style>
</head>
<body>
<h1>GitHub Issue 可扩展分析报告</h1>
<p><b>仓库</b>: {self.results.get('repo','')} | 
<b>生成时间</b>: {datetime.now().isoformat()} | 
<b>总Issue数</b>: {self.results.get('total_issues',0)}</p>
<pre>{self._escape(str(self.results))}</pre>
</body>
</html>"""
        with open(out, "w", encoding="utf-8") as f:
            f.write(html)
        return out

    def _escape(self, s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
