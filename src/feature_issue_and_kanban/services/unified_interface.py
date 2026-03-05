#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一接口：Cursor 和企微都通过此 API 连接
POST /api/create-issue
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


def _get_generator():
    from config.config import GITHUB_TOKEN, GITHUB_API_BASE_URL
    from modules.database_storage.mo_client import MOStorage
    from modules.llm_parser.llm_parser import LLMParser
    sys.path.insert(0, str(ROOT / "feature_issue_and_kanban"))
    from issue_creator.ai_issue_generator import AIIssueGenerator

    storage = MOStorage()
    llm = LLMParser()
    return AIIssueGenerator(storage, llm, GITHUB_TOKEN, GITHUB_API_BASE_URL)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "issue-assistant-unified"})


@app.route("/api/create-issue", methods=["POST"])
def create_issue():
    """
    统一 Issue 创建接口

    请求 JSON：
    {
        "source": "cursor" | "wechat",
        "user_input": "用户描述",
        "context": { "file_path", "selected_code", "errors", ... },  # Cursor 提供
        "images": [],  # base64 截图等
        "repo_owner": "matrixorigin",
        "repo_name": "matrixflow"
    }
    """
    data = request.json or {}
    source = data.get("source", "unknown")
    user_input = data.get("user_input", "").strip()
    context = data.get("context") or {}
    images = data.get("images") or []
    repo_owner = data.get("repo_owner", "matrixorigin")
    repo_name = data.get("repo_name", "matrixflow")

    if not user_input:
        return jsonify({"success": False, "error": "user_input 不能为空"}), 400

    try:
        gen = _get_generator()

        if source == "cursor" and context:
            prompt = f"""用户描述：{user_input}

## 代码上下文
- 文件：{context.get("file_path", "unknown")}
- 行号：{context.get("line_number", 0)}
- 语言：{context.get("language", "text")}
- 分支：{context.get("git_branch", "unknown")}
- 选中代码：{(context.get("selected_code") or "")[:500]}
- 报错：{context.get("errors", [])[:3]}

请根据上下文生成 Issue 草稿 JSON。"""
            draft = gen.generate_from_enhanced_context(
                prompt, context, images, repo_owner, repo_name
            )
        else:
            draft = gen.generate_with_duplicate_check(
                user_input, repo_owner, repo_name, context=None
            )

        return jsonify({
            "success": True,
            "draft": draft,
            "source": source,
        })
    except Exception as e:
        import traceback
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


if __name__ == "__main__":
    print("统一接口服务启动：POST /api/create-issue")
    print("Cursor: source=cursor, 企微: source=wechat")
    app.run(host="127.0.0.1", port=8767, debug=True)
