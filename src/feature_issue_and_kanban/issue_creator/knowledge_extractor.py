#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Issue 知识库提炼器：从历史 Issue 中提炼产品结构、标签体系、常见类型，供 AI 创建 Issue 时参考。
"""
import json
import re
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict


class KnowledgeExtractor:
    def __init__(self, storage, llm):
        self.storage = storage
        self.llm = llm
        self.min_issue_count = 3

    def extract_full_knowledge_base(self, repo_owner: str, repo_name: str) -> Dict:
        """提炼完整知识库并落库、写 Markdown。"""
        print(f"\n{'='*70}\n开始提炼Issue知识库: {repo_owner}/{repo_name}\n{'='*70}\n")
        print("步骤1: 加载Issue数据...")
        issues = self._load_all_issues(repo_owner, repo_name)
        print(f"✓ 加载了 {len(issues)} 个Issue\n")
        print("步骤2: AI分析产品结构...")
        products = self._extract_products(issues)
        print(f"✓ 识别出 {len(products)} 个产品/模块\n")
        print("步骤3: 分析标签体系...")
        label_system = self._extract_label_system(issues)
        print(f"✓ 提取了 {sum(len(v) for v in label_system.values())} 个标签\n")
        print("步骤4: AI识别常见Issue类型...")
        common_issues = self._extract_common_issue_types(issues)
        print(f"✓ 识别出 {len(common_issues)} 种常见Issue\n")
        print("步骤5: 生成知识库索引...")
        markdown = self._generate_markdown_index({
            "products": products,
            "label_system": label_system,
            "common_issues": common_issues,
        })
        print(f"✓ Markdown 大小: {len(markdown)} 字节\n")
        print("步骤6: 保存到数据库...")
        self._save_to_database(products, label_system, common_issues)
        print("✓ 数据库保存完成\n")
        print("步骤7: 保存Markdown文件...")
        self._save_markdown_file(markdown, repo_owner, repo_name)
        print("✓ 文件保存完成\n")
        print(f"{'='*70}\n✅ 知识库提炼完成\n{'='*70}\n")
        return {
            "products": products,
            "label_system": label_system,
            "common_issues": common_issues,
            "markdown": markdown,
            "generated_at": datetime.now().isoformat(),
        }

    def _load_all_issues(self, repo_owner: str, repo_name: str) -> List[Dict]:
        sql = """
        SELECT issue_number, title, labels, state, created_at
        FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo
        AND snapshot_time = (
            SELECT MAX(snapshot_time) FROM issues_snapshot
            WHERE repo_owner = :owner AND repo_name = :repo
        )
        """
        rows = self.storage.execute(sql, {"owner": repo_owner, "repo": repo_name})
        return [
            {
                "number": r["issue_number"],
                "title": r["title"],
                "labels": self._parse_labels(r.get("labels")),
                "state": r.get("state", "unknown"),
                "created_at": str(r.get("created_at", "")),
            }
            for r in (rows or [])
        ]

    def _extract_products(self, issues: List[Dict]) -> Dict:
        sample_size = min(200, len(issues))
        sampled = self._sample_issues(issues, sample_size)
        prompt = f"""
你是产品分析专家。请根据以下 {len(sampled)} 个 Issue 样本，提取产品结构。

Issue样本：
{json.dumps(sampled, ensure_ascii=False, indent=2)}

请识别：1) 主产品（如 MOI、MO）；2) 子产品/模块；3) 主要功能。
返回纯 JSON，格式示例：
{{"MOI": {{"type": "platform", "sub_products": {{"问数": {{"features": ["NL2SQL"], "issue_count": 100}}}}}}, "MO": {{"type": "database", "modules": {{"storage": {{"issue_count": 50}}}}}}}}
只返回 JSON，不要其他说明。
"""
        try:
            resp = self.llm._call_ai("你只输出合法 JSON，不要 markdown 代码块。", prompt)
            if resp:
                text = self._extract_json(resp)
                return json.loads(text)
        except Exception:
            pass
        return self._fallback_extract_products(issues)

    def _extract_label_system(self, issues: List[Dict]) -> Dict:
        label_stats = defaultdict(lambda: defaultdict(int))
        for issue in issues:
            for label in issue.get("labels", []):
                if isinstance(label, dict):
                    name = label.get("name") or label.get("label", "")
                else:
                    name = str(label)
                if "/" in name:
                    prefix = name.split("/", 1)[0] + "/"
                    label_stats[prefix][name] += 1
                else:
                    label_stats["other"][name] += 1
        result = {}
        for prefix, labels in label_stats.items():
            filtered = {
                k: v for k, v in sorted(labels.items(), key=lambda x: -x[1])
                if v >= self.min_issue_count
            }
            if filtered:
                result[prefix] = filtered
        return result

    def _extract_common_issue_types(self, issues: List[Dict]) -> List[Dict]:
        grouped = defaultdict(list)
        for issue in issues:
            labels = issue.get("labels", [])
            names = []
            for lb in labels:
                n = lb.get("name", lb.get("label", lb)) if isinstance(lb, dict) else lb
                names.append(str(n))
            key = tuple(sorted([n for n in names if "kind/" in n or "area/" in n]))
            if key:
                grouped[key].append(issue)
        common = []
        for labels_tuple, issue_list in grouped.items():
            if len(issue_list) < 10:
                continue
            common.append({
                "labels": list(labels_tuple),
                "count": len(issue_list),
                "examples": [{"number": i["number"], "title": i["title"]} for i in issue_list[:5]],
            })
        common.sort(key=lambda x: -x["count"])
        return common[:50]

    def _generate_markdown_index(self, knowledge: Dict) -> str:
        md = f"# Issue知识库索引\n\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n\n## 一、产品结构\n\n"
        for product_name, product_info in knowledge.get("products", {}).items():
            md += f"### {product_name}\n\n"
            if "sub_products" in product_info:
                for sub_name, sub_info in product_info["sub_products"].items():
                    md += f"- {sub_name} ({sub_info.get('issue_count', 0)} Issues)\n"
                    if sub_info.get("features"):
                        md += f"  - 功能: {', '.join(sub_info['features'])}\n"
            if "modules" in product_info:
                for mod_name, mod_info in product_info["modules"].items():
                    md += f"- {mod_name} ({mod_info.get('issue_count', 0)} Issues)\n"
            md += "\n"
        md += "## 二、标签体系\n\n"
        for prefix, labels in knowledge.get("label_system", {}).items():
            md += f"### {prefix}\n\n"
            for label, count in list(labels.items())[:20]:
                md += f"- `{label}` ({count})\n"
            md += "\n"
        md += "## 三、常见Issue类型\n\n"
        for idx, it in enumerate(knowledge.get("common_issues", [])[:20], 1):
            md += f"### {idx}. {', '.join(it.get('labels', []))} ({it.get('count', 0)} Issues)\n\n"
            for ex in it.get("examples", [])[:3]:
                md += f"- #{ex['number']}: {ex['title']}\n"
            md += "\n"
        return md

    def _save_to_database(self, products: Dict, label_system: Dict, common_issues: List) -> None:
        version = int(datetime.now().timestamp())
        for product_name, product_info in products.items():
            self._insert_knowledge(
                knowledge_type="product",
                category=product_name,
                title=product_name,
                description=json.dumps(product_info, ensure_ascii=False),
                version=version,
            )
        for prefix, labels in label_system.items():
            for label, count in labels.items():
                self._insert_knowledge(
                    knowledge_type="label",
                    category=prefix,
                    title=label,
                    description=f"出现{count}次",
                    issue_count=count,
                    version=version,
                )
        for issue_type in common_issues:
            self._insert_knowledge(
                knowledge_type="common_issue",
                category=",".join(issue_type["labels"]),
                title=f"常见类型: {','.join(issue_type['labels'])}",
                description=json.dumps(issue_type, ensure_ascii=False),
                issue_count=issue_type["count"],
                version=version,
            )

    def _insert_knowledge(
        self,
        knowledge_type: str,
        category: str,
        title: str,
        description: str,
        issue_count: int = 0,
        version: int = 1,
    ) -> None:
        sql = """
        INSERT INTO issue_knowledge_base (knowledge_type, category, title, description, issue_count, version)
        VALUES (:ktype, :category, :title, :description, :cnt, :version)
        """
        self.storage.execute(
            sql,
            {
                "ktype": knowledge_type,
                "category": category,
                "title": title,
                "description": description,
                "cnt": issue_count,
                "version": version,
            },
        )

    def _save_markdown_file(self, markdown: str, repo_owner: str, repo_name: str) -> None:
        # 优先在项目根下的 data/knowledge_base
        root = Path(__file__).resolve().parents[2]
        for base in [root, Path.cwd()]:
            output_dir = base / "data" / "knowledge_base"
            output_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d")
            (output_dir / f"{repo_owner}_{repo_name}_knowledge_{ts}.md").write_text(markdown, encoding="utf-8")
            (output_dir / f"{repo_owner}_{repo_name}_knowledge_latest.md").write_text(markdown, encoding="utf-8")
            print(f"   文件路径: {output_dir}")
            return

    def _parse_labels(self, labels) -> List:
        if labels is None:
            return []
        if isinstance(labels, str):
            try:
                labels = json.loads(labels)
            except Exception:
                return []
        return list(labels) if isinstance(labels, list) else []

    def _sample_issues(self, issues: List[Dict], size: int) -> List[Dict]:
        return random.sample(issues, size) if len(issues) > size else issues

    def _extract_json(self, text: str) -> str:
        text = (text or "").strip()
        for pattern in [r"```json\s*(.*?)\s*```", r"```\s*(.*?)\s*```"]:
            m = re.search(pattern, text, re.DOTALL)
            if m:
                return m.group(1).strip()
        m = re.search(r"\{.*\}", text, re.DOTALL)
        return m.group(0) if m else text

    def _fallback_extract_products(self, issues: List[Dict]) -> Dict:
        products = {}
        for issue in issues:
            for label in issue.get("labels", []):
                name = label.get("name", label) if isinstance(label, dict) else str(label)
                if name.startswith("area/"):
                    area = name.replace("area/", "")
                    if "MOI" not in products:
                        products["MOI"] = {"type": "platform", "sub_products": {}}
                    if area not in products["MOI"]["sub_products"]:
                        products["MOI"]["sub_products"][area] = {"issue_count": 0}
                    products["MOI"]["sub_products"][area]["issue_count"] += 1
        return products
