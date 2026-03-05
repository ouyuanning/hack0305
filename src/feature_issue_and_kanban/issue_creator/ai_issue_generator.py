#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Issue 生成器：根据用户自然语言描述生成 Issue 草稿（标题、正文、标签、负责人等），并可调用 GitHub API 创建。
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any


class AIIssueGenerator:
    def __init__(self, storage, llm, github_token: str, base_url: str = "https://api.github.com"):
        self.storage = storage
        self.llm = llm
        self.github_token = github_token
        self.base_url = base_url
        self.knowledge_base = None  # 可加载为 dict 或 str

    def load_knowledge_base(self, repo_owner: str, repo_name: str) -> None:
        """从数据库或 data/knowledge_base/*.md 加载知识库摘要，供生成时参考。"""
        root = Path(__file__).resolve().parents[2]
        for base in [root, Path.cwd()]:
            p = base / "data" / "knowledge_base" / f"{repo_owner}_{repo_name}_knowledge_latest.md"
            if p.exists():
                self.knowledge_base = p.read_text(encoding="utf-8")[:8000]
                return
        sql = """
        SELECT knowledge_type, category, title, description FROM issue_knowledge_base
        WHERE is_active = 1 ORDER BY id DESC LIMIT 200
        """
        try:
            rows = self.storage.execute(sql, {})
            if rows:
                self.knowledge_base = json.dumps(
                    [{"type": r.get("knowledge_type"), "category": r.get("category"), "title": r.get("title")} for r in rows],
                    ensure_ascii=False,
                )
        except Exception:
            self.knowledge_base = None

    def generate_issue_draft(
        self,
        user_input: str,
        repo_owner: str,
        repo_name: str,
        explicit_requirements: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        根据用户描述生成 Issue 草稿。

        修复版本 - 新流程：
        1. 提前获取浏览器Issue上下文（在AI生成之前）
        2. 智能推断Bug类型（3层策略：标签>AI+知识库>关键词）
        3. 将浏览器Issue信息告诉AI
        4. AI生成草稿
        5. 追加浏览器Issue详情

        返回: { "title", "body", "labels", "assignees", "related_issues", "template_type" }
        """
        print(f"\n{'='*60}")
        print(f"开始生成Issue草稿")
        print(f"用户输入: {user_input}")
        print(f"{'='*60}\n")

        # 1. 加载知识库
        self.load_knowledge_base(repo_owner, repo_name)
        kb = (self.knowledge_base or "")[:6000]

        # 2. 【修复】提前获取浏览器Issue上下文（在生成之前）
        browser_issue = self._get_browser_issue_context()

        if browser_issue:
            print(f"浏览器上下文:")
            print(f"  Issue: #{browser_issue.get('number')}")
            print(f"  标题: {browser_issue.get('title', 'N/A')}")
            print(f"  标签: {browser_issue.get('labels', [])}")
            print()
        else:
            print(f"浏览器上下文: 无\n")

        # 3. 【修复】智能推断Bug类型（结合浏览器Issue标签）
        bug_type = self._infer_bug_type_intelligent(
            user_input=user_input,
            knowledge_base=kb,
            browser_issue=browser_issue
        )

        print(f"推断的模板类型: {bug_type}\n")

        # 4. 获取模板结构
        template_hint = self._get_template_structure_hint(bug_type)

        # 5. 【修复】构建增强的prompt（包含浏览器Issue信息）
        prompt = self._build_enhanced_prompt(
            user_input=user_input,
            knowledge_base=kb,
            bug_type=bug_type,
            template_hint=template_hint,
            browser_issue=browser_issue,
            explicit_requirements=explicit_requirements
        )

        # 6. 调用AI生成
        resp = self.llm._call_ai("你只输出合法的一行 JSON，不要 markdown 与解释。", prompt)

        # 7. 解析响应
        draft = self._parse_draft_response(resp, user_input)
        draft.setdefault("repo_owner", repo_owner)
        draft.setdefault("repo_name", repo_name)
        draft["template_type"] = bug_type

        # 8. 【修复】处理关联Issue（已经从浏览器获取了）
        if browser_issue:
            # 确保related_issues包含浏览器Issue
            if "related_issues" not in draft or not draft["related_issues"]:
                draft["related_issues"] = [f"#{browser_issue['number']}"]
            elif f"#{browser_issue['number']}" not in draft["related_issues"]:
                draft["related_issues"].append(f"#{browser_issue['number']}")

            # 追加关联Issue详情到body
            draft["body"] = self._append_browser_issue_section(
                draft.get("body", ""),
                browser_issue
            )
        else:
            # 降级：从描述/URL 提取关联 Issue
            refs = self._extract_related_issue_refs(user_input, repo_owner, repo_name)
            if refs and ("related_issues" not in draft or not draft["related_issues"]):
                draft["related_issues"] = [f"#{r[2]}" for r in refs]
            if refs:
                draft["body"] = self._append_related_issues_section(
                    draft.get("body", ""), refs
                )

        print(f"\n生成结果:")
        print(f"  标题: {draft.get('title')}")
        print(f"  模板: {draft.get('template_type')}")
        print(f"  关联: {draft.get('related_issues', [])}")
        print(f"{'='*60}\n")

        return draft

    def _infer_bug_template_hint(self, user_input: str) -> str:
        """根据描述推断 Bug 模板类型：MO Bug / MOI Bug / User Bug"""
        t = (user_input or "").lower()
        mo_keywords = ("mo", "matrixone", "数据备份", "内核", "同步工具", "存储", "sql", "ddl")
        moi_keywords = ("moi", "问数", "chatbi", "智能体", "产品", "前端", "api 接口")
        if any(k in t for k in mo_keywords) and not any(k in t for k in moi_keywords):
            return "MO Bug"
        if any(k in t for k in moi_keywords):
            return "MOI Bug"
        return "User Bug"

    def _get_template_structure_hint(self, template_type: str) -> str:
        """返回该类型的正文模板结构，供 AI 按结构生成"""
        root = Path(__file__).resolve().parents[2]
        templates_dir = root / "feature_issue_and_kanban" / "templates"
        mapping = {"MO Bug": "MO_Bug.md", "MOI Bug": "MOI_Bug.md", "User Bug": "User_Bug.md"}
        fname = mapping.get(template_type)
        if fname and (templates_dir / fname).exists():
            content = (templates_dir / fname).read_text(encoding="utf-8").strip()
            return f"请严格按以下「{template_type}」模板结构生成 body：\n```\n{content}\n```"
        return ""

    def _extract_related_issue_refs(
        self, user_input: str, default_owner: str, default_repo: str
    ) -> list:
        """从描述中提取关联 Issue：支持 #123 或 https://github.com/owner/repo/issues/123"""
        refs = []
        import re
        # 匹配 github.com/owner/repo/issues/123
        for m in re.finditer(
            r"github\.com/([^/]+)/([^/]+)/issues/(\d+)", user_input, re.I
        ):
            refs.append((m.group(1), m.group(2), int(m.group(3))))
        # 匹配 #123（仅当未匹配到完整 URL 时）
        if not refs:
            for m in re.finditer(r"#(\d+)", user_input):
                refs.append((default_owner, default_repo, int(m.group(1))))
        return refs[:5]

    def _append_related_issues_section(self, body: str, refs: list) -> str:
        """拉取关联 Issue 信息并追加到 body"""
        try:
            from modules.github_collector.github_api import GitHubCollector
            collector = GitHubCollector()
        except Exception:
            return body
        lines = []
        for owner, repo, num in refs:
            try:
                issue = collector.fetch_issue(owner, repo, num)
                title = issue.get("title", "")
                url = issue.get("html_url", f"https://github.com/{owner}/{repo}/issues/{num}")
                body_text = (issue.get("body") or "")[:300].replace("\n", " ")
                labels = [l.get("name", "") for l in (issue.get("labels") or [])[:5]]
                lines.append(f"- #{num} [{title}]({url})\n  - 标签: {', '.join(labels) or '—'}\n  - 摘要: {body_text}...")
            except Exception:
                lines.append(f"- #{num} https://github.com/{owner}/{repo}/issues/{num}")
        if lines:
            body = body.rstrip() + "\n\n## 关联 Issue\n" + "\n".join(lines)
        return body

    def _get_browser_issue_context(self) -> Optional[Dict]:
        """
        【修改】获取浏览器Issue上下文
        新实现：智能混合方案（CDP→窗口→剪贴板→手动），不依赖Chrome调试模式
        """
        try:
            from utils.browser_context import get_issue_details_from_browser

            # 直接调用，不检查配置（智能检测总是可用）
            issue = get_issue_details_from_browser(
                github_token=self.github_token
            )

            if issue:
                print(f"ℹ️ Issue检测方式: {issue.get('source', 'unknown')}")

            return issue

        except Exception as e:
            print(f"⚠️ 获取浏览器Issue失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _infer_bug_type_intelligent(
        self,
        user_input: str,
        knowledge_base: str,
        browser_issue: Optional[Dict]
    ) -> str:
        """
        【改进】智能推断Bug类型

        3层策略（优先级从高到低）：
        1. 从浏览器Issue标签推断（最准确）
        2. AI结合知识库判断
        3. 降级到关键词匹配

        Returns:
            "MO Bug" / "MOI Bug" / "User Bug"
        """
        # 策略1：从浏览器Issue标签推断（最准确）
        if browser_issue and browser_issue.get("labels"):
            labels = browser_issue["labels"]

            for label in labels:
                label_lower = label.lower()

                # MO产品标签
                if any(keyword in label_lower for keyword in [
                    "product/mo", "area/内核", "area/存储", "area/sql",
                    "component/数据备份", "component/同步", "area/database"
                ]):
                    print(f"✅ 从浏览器Issue标签推断: MO Bug (标签: {label})")
                    return "MO Bug"

                # MOI产品标签
                if any(keyword in label_lower for keyword in [
                    "product/moi", "area/问数", "area/chatbi",
                    "component/前端", "component/api", "area/bi"
                ]):
                    print(f"✅ 从浏览器Issue标签推断: MOI Bug (标签: {label})")
                    return "MOI Bug"

        # 策略2：使用AI结合知识库智能判断
        if knowledge_base:
            try:
                browser_ctx = ""
                if browser_issue:
                    t = browser_issue.get("title", "")
                    lbl = browser_issue.get("labels", [])
                    browser_ctx = f"\n浏览器当前Issue: {t} (标签: {lbl})"

                prompt = f"""
用户描述：{user_input}

参考知识库（产品分类）：
{knowledge_base[:2000]}
{browser_ctx}

判断这个Bug应该归属哪个产品：

- **MO Bug**: MatrixOne数据库内核相关（数据备份、同步工具、SQL引擎、存储、DDL等）
- **MOI Bug**: 问数/ChatBI产品相关（前端、API接口、智能体、BI功能、可视化等）
- **User Bug**: 用户反馈的一般性Bug

只返回以下之一：MO Bug / MOI Bug / User Bug
不要其他文字。
"""
                response = self.llm._call_ai("", prompt).strip()

                if "MO Bug" in response or "MO bug" in response:
                    print(f"✅ AI智能推断: MO Bug")
                    return "MO Bug"
                elif "MOI Bug" in response or "MOI bug" in response:
                    print(f"✅ AI智能推断: MOI Bug")
                    return "MOI Bug"
                elif "User Bug" in response:
                    print(f"✅ AI智能推断: User Bug")
                    return "User Bug"

            except Exception as e:
                print(f"⚠️ AI推断失败: {e}")

        # 策略3：降级到关键词匹配
        result = self._infer_bug_template_hint_fallback(user_input)
        print(f"ℹ️ 关键词匹配推断: {result}")
        return result

    def _infer_bug_template_hint_fallback(self, user_input: str) -> str:
        """
        降级方案：关键词匹配

        当浏览器标签和AI判断都不可用时使用
        """
        t = (user_input or "").lower()

        mo_keywords = (
            "mo ", "mo数", "matrixone", "数据备份", "内核", "同步工具",
            "存储", "sql", "ddl", "数据库", "引擎", "备份", "database"
        )

        moi_keywords = (
            "moi", "问数", "chatbi", "智能体", "产品",
            "前端", "api", "接口", "bi", "可视化", "dashboard"
        )

        mo_count = sum(1 for k in mo_keywords if k in t)
        moi_count = sum(1 for k in moi_keywords if k in t)

        if mo_count > moi_count:
            return "MO Bug"
        elif moi_count > 0:
            return "MOI Bug"

        return "User Bug"

    def _build_enhanced_prompt(
        self,
        user_input: str,
        knowledge_base: str,
        bug_type: str,
        template_hint: str,
        browser_issue: Optional[Dict],
        explicit_requirements: Optional[Dict[str, Any]]
    ) -> str:
        """
        【新增】构建增强的prompt
        将浏览器Issue信息告诉AI
        """
        prompt = f"""
用户描述：
{user_input}

{f'额外要求：{json.dumps(explicit_requirements, ensure_ascii=False)}' if explicit_requirements else ''}
"""

        # 【关键】添加浏览器Issue上下文
        if browser_issue:
            prompt += f"""

【重要】用户当前正在浏览：
- Issue #{browser_issue.get('number')}: {browser_issue.get('title', '')}
- 标签: {', '.join(browser_issue.get('labels', []))}
- 描述摘要: {browser_issue.get('body', '')[:300]}

**这个Issue应该被添加到related_issues中**，并从中提取相关信息。
"""

        related_issues_json = (
            f'["#{browser_issue["number"]}"]' if browser_issue else '[]'
        )

        prompt += f"""

参考知识库（可选）：
{knowledge_base}

{template_hint}

请根据描述生成一条 GitHub Issue 草稿，严格按以下 JSON 输出（不要 markdown 代码块）：
{{
  "title": "简短标题，建议带 [{bug_type.split()[0]}] 前缀",
  "body": "正文 Markdown，必须严格按上述模板结构填写",
  "labels": ["kind/bug", "area/xxx"],
  "assignees": ["GitHub 登录名"],
  "related_issues": {related_issues_json},
  "template_type": "{bug_type}"
}}

只返回一行 JSON，不要其他文字。
"""

        return prompt

    def _append_browser_issue_section(self, body: str, browser_issue: Dict) -> str:
        """
        【新增】追加浏览器Issue详情到body
        """
        if not browser_issue:
            return body

        number = browser_issue.get("number")
        title = browser_issue.get("title", "")
        labels = browser_issue.get("labels", [])
        body_text = browser_issue.get("body", "")[:300]
        url = browser_issue.get("url", "")

        section = f"""

## 关联 Issue

- #{number} [{title}]({url})
  - 标签: {', '.join(labels) or '无'}
  - 摘要: {body_text}...
"""

        return body.rstrip() + section

    def _parse_draft_response(self, response: Optional[str], fallback_title: str) -> Dict[str, Any]:
        if not response:
            return {
                "title": fallback_title[:200] or "新Issue",
                "body": "",
                "labels": [],
                "assignees": [],
                "related_issues": [],
                "template_type": "unknown",
            }
        text = response.strip()
        m = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        return {
            "title": text[:200] or fallback_title[:200],
            "body": text,
            "labels": [],
            "assignees": [],
            "related_issues": [],
            "template_type": "unknown",
        }

    def generate_from_enhanced_context(
        self,
        enhanced_prompt: str,
        context: Optional[Dict[str, Any]] = None,
        screenshots: Optional[List[Dict]] = None,
        repo_owner: str = "",
        repo_name: str = "",
    ) -> Dict[str, Any]:
        """
        从增强上下文（代码、报错、截图）生成 Issue 草稿。
        Cursor 扩展或上下文服务调用。
        """
        system_prompt = """你是 GitHub Issue 创建助手。基于用户提供的代码上下文、报错、截图，生成结构化的 Issue。
请返回 JSON（不要 markdown 代码块）：{"title","body","labels","issue_type","assignees","product"}
只返回一行 JSON。"""
        resp = self.llm._call_ai(system_prompt, enhanced_prompt)
        draft = self._parse_draft_response(resp, "新Issue")
        draft.setdefault("repo_owner", repo_owner)
        draft.setdefault("repo_name", repo_name)

        if context:
            draft["body"] = self._enhance_body_with_context(
                draft.get("body", ""), context, screenshots or []
            )
        return draft

    def _enhance_body_with_context(
        self, body: str, context: Dict[str, Any], screenshots: List[Dict]
    ) -> str:
        """在正文中添加上下文信息（代码位置、报错、截图描述）"""
        if not context:
            return body
        extra = ""
        if context.get("file_path"):
            extra += f"""
## 代码位置
- **文件**: `{context.get("file_path")}`
- **行号**: Line {context.get("line_number", "?")}
- **分支**: {context.get("git_branch", "unknown")}
"""
            if context.get("selected_code"):
                lang = context.get("language", "")
                extra += f"\n## 相关代码\n```{lang}\n{context.get('selected_code')}\n```\n"
        errors = context.get("errors") or []
        if errors:
            extra += "\n## 报错信息\n"
            for e in errors[:3]:
                extra += f"- {e.get('message', 'Unknown')}\n"
        if screenshots:
            extra += "\n## 截图\n"
            for i, ss in enumerate(screenshots, 1):
                extra += f"{i}. {ss.get('description', '截图')}\n"
        return body.rstrip() + "\n" + extra

    def generate_with_duplicate_check(
        self,
        user_input: str,
        repo_owner: str,
        repo_name: str,
        context: Optional[Dict[str, Any]] = None,
        explicit_requirements: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        生成 Issue 并检查重复。
        若检测到高度重复，在 draft 中加入 warning 字段。
        """
        if context:
            prompt = f"""用户描述：{user_input}

## 代码上下文
- 文件：{context.get("file_path", "unknown")}
- 行号：{context.get("line_number", 0)}
- 语言：{context.get("language", "text")}
- 分支：{context.get("git_branch", "unknown")}
- 选中代码：{context.get("selected_code", "(无)")[:300]}
- 报错：{context.get("errors", [])[:3]}
请根据上下文生成 Issue 草稿 JSON。"""
            draft = self.generate_from_enhanced_context(
                prompt, context, [], repo_owner, repo_name
            )
        else:
            draft = self.generate_issue_draft(
                user_input, repo_owner, repo_name, explicit_requirements
            )

        from .duplicate_detector import DuplicateDetector
        detector = DuplicateDetector(self.storage)
        dup_result = detector.check_duplicate(draft, repo_owner, repo_name)

        draft["duplicate_check"] = dup_result
        if dup_result.get("is_duplicate") and dup_result.get("confidence", 0) > 0.8:
            warn = f"""
⚠️ **重复检测警告**

{dup_result.get("suggested_action", "检测到可能重复的 Issue")}

相似 Issue：
"""
            for obj in dup_result.get("similar_issue_objects", [])[:3]:
                warn += f"- #{obj.get('issue_number')}: {obj.get('title')}\n"
            warn += "\n建议：若确实重复，不创建新 Issue；若相关但不重复，创建后添加关联。"
            draft["warning"] = warn
        return draft

    def create_issue_on_github(self, draft: Dict[str, Any]) -> Dict[str, Any]:
        """根据草稿调用 GitHub API 创建 Issue。"""
        from .github_issue_creator import create_issue_on_github as do_create
        owner = draft.get("repo_owner") or draft.get("owner")
        repo = draft.get("repo_name") or draft.get("repo")
        if not owner or not repo:
            raise ValueError("草稿中缺少 repo_owner/repo_name 或 owner/repo")
        return do_create(
            owner=owner,
            repo=repo,
            title=draft.get("title", "新Issue"),
            body=draft.get("body", ""),
            token=self.github_token,
            labels=draft.get("labels") or None,
            assignees=draft.get("assignees") or None,
            base_url=self.base_url,
        )
