#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从指定仓库的历史 Issue 提炼知识库并写入数据库与 data/knowledge_base/*.md。
用法（在项目根目录执行）:
  python feature_issue_and_kanban/scripts/update_knowledge_base.py --repo matrixorigin/matrixflow
  python feature_issue_and_kanban/scripts/update_knowledge_base.py --repo matrixorigin/matrixone
"""
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.database_storage.mo_client import MOStorage
from modules.llm_parser.llm_parser import LLMParser

sys.path.insert(0, str(ROOT / "feature_issue_and_kanban"))
from issue_creator.knowledge_extractor import KnowledgeExtractor


def main():
    parser = argparse.ArgumentParser(description="更新 Issue 知识库")
    parser.add_argument("--repo", required=True, help="仓库 owner/name")
    args = parser.parse_args()
    parts = args.repo.split("/")
    if len(parts) != 2:
        print("--repo 格式应为 owner/name")
        sys.exit(1)
    repo_owner, repo_name = parts[0], parts[1]
    storage = MOStorage()
    llm = LLMParser()
    extractor = KnowledgeExtractor(storage, llm)
    extractor.extract_full_knowledge_base(repo_owner, repo_name)


if __name__ == "__main__":
    main()
