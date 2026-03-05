# -*- coding: utf-8 -*-
"""JSON 输出"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict


class JSONFormatter:
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
        with open(out, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        return out
