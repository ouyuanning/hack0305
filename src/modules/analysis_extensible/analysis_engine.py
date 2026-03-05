# -*- coding: utf-8 -*-
"""
可扩展分析引擎
功能：配置驱动的多维度 Issue 分析
架构：配置驱动 + 插件式分析器 + 多格式输出
"""

import sys
import os
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))
from modules.database_storage.mo_client import MOStorage


class ExtensibleAnalysisEngine:
    """可扩展分析引擎"""

    def __init__(self, config_path: Optional[str] = None):
        base = Path(__file__).resolve().parent.parent.parent
        cfg = config_path or str(base / "config" / "analysis_config.yaml")
        self.config_path = cfg
        self.config = self._load_config()
        self.storage = MOStorage()
        self.analyzers = {}
        self.results = {}
        self._load_analyzers()
        print(f"✅ 可扩展分析引擎初始化完成，加载 {len(self.analyzers)} 个分析器")

    def _load_config(self) -> Dict:
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _load_analyzers(self):
        from .analyzers.basic_stats_analyzer import BasicStatsAnalyzer
        from .analyzers.label_analyzer import LabelAnalyzer
        from .analyzers.module_analyzer import ModuleAnalyzer
        from .analyzers.hierarchy_analyzer import HierarchyAnalyzer
        from .analyzers.customer_analyzer import CustomerAnalyzer
        from .analyzers.relation_analyzer import RelationAnalyzer
        from .analyzers.trend_analyzer import TrendAnalyzer

        classes = {
            "basic_stats": BasicStatsAnalyzer,
            "label_analysis": LabelAnalyzer,
            "module_analysis": ModuleAnalyzer,
            "hierarchy_analysis": HierarchyAnalyzer,
            "customer_analysis": CustomerAnalyzer,
            "relation_analysis": RelationAnalyzer,
            "trend_analysis": TrendAnalyzer,
        }
        global_cfg = self.config.get("global", {})
        for ac in self.config.get("analyzers", []):
            name = ac.get("name")
            if not ac.get("enabled", True) or name not in classes:
                continue
            cfg = ac.get("config", {}).copy()
            cfg["_repo_owner"] = global_cfg.get("repo_owner", "matrixorigin")
            cfg["_repo_name"] = global_cfg.get("repo_name", "matrixone")
            try:
                self.analyzers[name] = classes[name](self.storage, cfg)
            except Exception as e:
                print(f"⚠️  加载分析器 {name} 失败: {e}")

    def _load_issues(self, repo_owner: str, repo_name: str) -> List[Dict]:
        """使用主快照（Issue 最多的）加载数据，兼容 MatrixOne"""
        sql_main = """
        SELECT snapshot_time
        FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo
        GROUP BY snapshot_time
        ORDER BY COUNT(*) DESC
        LIMIT 1
        """
        r = self.storage.execute(sql_main, {"owner": repo_owner, "repo": repo_name})
        if not r or not r[0].get("snapshot_time"):
            return []
        latest = r[0]["snapshot_time"]
        sql = """
        SELECT *
        FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo AND snapshot_time = :lt
        """
        rows = self.storage.execute(sql, {"owner": repo_owner, "repo": repo_name, "lt": latest})
        return [dict(row) for row in rows] if rows else []

    def run(self, repo_owner: str = None, repo_name: str = None) -> Dict:
        repo_owner = repo_owner or self.config.get("global", {}).get("repo_owner", "matrixorigin")
        repo_name = repo_name or self.config.get("global", {}).get("repo_name", "matrixone")

        print(f"\n{'='*60}")
        print(f"📊 可扩展分析: {repo_owner}/{repo_name}")
        print("=" * 60)

        print("\n📁 加载 Issue 数据...")
        issues = self._load_issues(repo_owner, repo_name)
        print(f"   加载 {len(issues)} 个 Issue")

        self.results = {
            "repo": f"{repo_owner}/{repo_name}",
            "generated_at": datetime.now().isoformat(),
            "total_issues": len(issues),
            "analysis_results": {},
        }

        print("\n🔍 执行分析...")
        for i, (name, analyzer) in enumerate(self.analyzers.items(), 1):
            try:
                result = analyzer.analyze(issues)
                self.results["analysis_results"][name] = result
                print(f"   [{i}/{len(self.analyzers)}] {name} ✓")
            except Exception as e:
                print(f"   [{i}/{len(self.analyzers)}] {name} ✗ ({e})")
                self.results["analysis_results"][name] = {"error": str(e)}

        print("\n📄 生成输出...")
        self._generate_outputs()

        print("\n✅ 可扩展分析完成")
        return self.results

    def _generate_outputs(self):
        from .formatters.json_formatter import JSONFormatter
        from .formatters.markdown_formatter import MarkdownFormatter
        from .formatters.html_formatter import HTMLFormatter

        formatters = {"json": JSONFormatter, "markdown": MarkdownFormatter, "html": HTMLFormatter}
        base_dir = Path(self.config.get("output", {}).get("base_dir", "data/reports"))
        base_dir = Path(__file__).resolve().parent.parent.parent / base_dir
        base_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d")

        for fc in self.config.get("output", {}).get("formats", []):
            if not fc.get("enabled", True):
                continue
            t = fc.get("type")
            if t not in formatters:
                continue
            fn = fc.get("filename", f"{t}_output").replace("{date}", date_str)
            out_path = base_dir / fn
            try:
                f = formatters[t](self.results, fc, self.config.get("output", {}).get("sections", []))
                f.save(out_path)
                print(f"   ✓ {t.upper()}: {out_path}")
            except Exception as e:
                print(f"   ✗ {t.upper()}: {e}")


def main():
    import argparse
    p = argparse.ArgumentParser(description="可扩展分析引擎")
    p.add_argument("--config", help="配置文件路径")
    p.add_argument("--repo-owner", default="matrixorigin")
    p.add_argument("--repo-name", default="matrixone")
    args = p.parse_args()
    engine = ExtensibleAnalysisEngine(config_path=args.config)
    engine.run(repo_owner=args.repo_owner, repo_name=args.repo_name)


if __name__ == "__main__":
    main()
