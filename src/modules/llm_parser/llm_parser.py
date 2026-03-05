#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM 解析模块
功能：使用AI API解析Issue内容，进行分类、优先级判定、标签提取等
支持多种AI服务提供商：OpenAI, Claude, 通义千问等
"""

import json
import sys
import os
from typing import Dict, List, Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))
from config.config import (
    AI_PROVIDER, OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL,
    CLAUDE_API_KEY, CLAUDE_BASE_URL, CLAUDE_MODEL,
    QWEN_API_KEY, QWEN_BASE_URL, QWEN_MODEL,
    DASHSCOPE_API_KEY,
    LOCAL_MODEL_URL, LOCAL_MODEL_NAME
)


class LLMParser:
    """LLM解析器，支持多种AI服务提供商，支持多AI提供商配置和自动回退"""
    
    def __init__(self):
        self.provider = AI_PROVIDER
        # 支持多个AI客户端（用于回退）
        self.clients = {}  # {provider: client}
        self.models = {}   # {provider: model}
        self.provider_order = []  # 优先级顺序
        self._init_clients()
    
    def _init_clients(self):
        """初始化AI客户端（支持多个提供商）"""
        # 根据配置确定优先级顺序
        # 如果配置为"qwen"或"claude"，优先使用千问，然后回退到Claude
        if self.provider in ["qwen", "claude"]:
            self.provider_order = ["qwen", "claude"]
        elif self.provider == "openai":
            self.provider_order = ["openai"]
        elif self.provider == "local":
            self.provider_order = ["local"]
        else:
            self.provider_order = ["qwen", "claude"]  # 默认优先级
        
        # 初始化千问客户端（优先）
        # 支持两种方式：OpenAI兼容接口（推荐）和DashScope SDK
        if "qwen" in self.provider_order:
            api_key = DASHSCOPE_API_KEY or QWEN_API_KEY
            if api_key and api_key not in ["your_qwen_api_key_here", "your_dashscope_api_key_here"]:
                # 优先使用OpenAI兼容接口（兼容模式）
                if "/compatible-mode/" in QWEN_BASE_URL:
                    try:
                        from openai import OpenAI
                        self.clients["qwen"] = OpenAI(
                            api_key=api_key,
                            base_url=QWEN_BASE_URL
                        )
                        self.models["qwen"] = QWEN_MODEL
                        print("✅ 通义千问客户端初始化成功（OpenAI兼容接口，优先使用）")
                    except ImportError:
                        print("⚠️  未安装 openai 库，请运行: pip install openai")
                        # 回退到DashScope SDK
                        self._init_qwen_dashscope(api_key)
                    except Exception as e:
                        print(f"⚠️  通义千问OpenAI兼容接口初始化失败: {e}，尝试DashScope SDK...")
                        # 回退到DashScope SDK
                        self._init_qwen_dashscope(api_key)
                else:
                    # 使用DashScope SDK（标准API）
                    self._init_qwen_dashscope(api_key)
            else:
                print("⚠️  通义千问API密钥未配置，跳过")
                print("   提示：请设置 DASHSCOPE_API_KEY 环境变量")
                print("   获取方式：https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen#f0577378e8sz4")
    
    def _init_qwen_dashscope(self, api_key: str):
        """初始化DashScope SDK客户端（备用方式）"""
        try:
            import dashscope
            dashscope.api_key = api_key
            self.clients["qwen"] = dashscope
            self.models["qwen"] = QWEN_MODEL
            print("✅ 通义千问客户端初始化成功（DashScope SDK）")
        except ImportError:
            print("⚠️  未安装 dashscope 库，请运行: pip install dashscope")
        except Exception as e:
            print(f"⚠️  通义千问DashScope SDK初始化失败: {e}")
        
        # 初始化Claude客户端（备用）
        if "claude" in self.provider_order:
            try:
                from anthropic import Anthropic
                if CLAUDE_API_KEY and CLAUDE_API_KEY != "your_claude_api_key_here":
                    self.clients["claude"] = Anthropic(api_key=CLAUDE_API_KEY)
                    self.models["claude"] = CLAUDE_MODEL
                    print("✅ Claude客户端初始化成功（备用）")
                else:
                    print("⚠️  Claude API密钥未配置，跳过")
            except ImportError:
                print("⚠️  未安装 anthropic 库，请运行: pip install anthropic")
            except Exception as e:
                print(f"⚠️  Claude初始化失败: {e}")
        
        # 初始化OpenAI客户端（如果配置）
        if "openai" in self.provider_order:
            try:
                from openai import OpenAI
                if OPENAI_API_KEY and OPENAI_API_KEY != "your_openai_api_key_here":
                    self.clients["openai"] = OpenAI(
                        api_key=OPENAI_API_KEY,
                        base_url=OPENAI_BASE_URL
                    )
                    self.models["openai"] = OPENAI_MODEL
                    print("✅ OpenAI客户端初始化成功")
                else:
                    print("⚠️  OpenAI API密钥未配置，跳过")
            except ImportError:
                print("⚠️  未安装 openai 库，请运行: pip install openai")
            except Exception as e:
                print(f"⚠️  OpenAI初始化失败: {e}")
        
        # 初始化本地模型（如果配置）
        if "local" in self.provider_order:
            try:
                from openai import OpenAI
                self.clients["local"] = OpenAI(
                    api_key="not-needed",
                    base_url=LOCAL_MODEL_URL
                )
                self.models["local"] = LOCAL_MODEL_NAME
                print("✅ 本地模型客户端初始化成功")
            except ImportError:
                print("⚠️  未安装 openai 库，请运行: pip install openai")
            except Exception as e:
                print(f"⚠️  本地模型初始化失败: {e}")
        
        if not self.clients:
            print(f"⚠️  所有AI服务都未初始化，将使用基于规则的回退方法")
        else:
            print(f"✅ 已初始化 {len(self.clients)} 个AI服务提供商: {list(self.clients.keys())}")
    
    def _call_ai(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """
        调用AI API，支持多提供商自动回退
        按优先级顺序尝试：优先千问，失败时回退到Claude
        """
        if not self.clients:
            return None
        
        # 按优先级顺序尝试每个提供商
        last_error = None
        for provider in self.provider_order:
            if provider not in self.clients:
                continue
            
            try:
                client = self.clients[provider]
                model = self.models[provider]
                
                if provider == "qwen":
                    # 通义千问API调用
                    # 判断使用OpenAI兼容接口还是DashScope SDK
                    if hasattr(client, 'chat') and hasattr(client.chat, 'completions'):
                        # OpenAI兼容接口
                        response = client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            temperature=0.3
                        )
                        return response.choices[0].message.content
                    else:
                        # DashScope SDK
                        response = client.Generation.call(
                            model=model,
                            prompt=f"{system_prompt}\n\n{user_prompt}",
                            temperature=0.3
                        )
                        if response.status_code == 200:
                            return response.output.text
                        else:
                            error_msg = getattr(response, 'message', f'状态码: {response.status_code}')
                            print(f"⚠️  千问API错误: {error_msg}，尝试下一个提供商...")
                            last_error = error_msg
                            continue
                
                elif provider == "claude":
                    # Claude API调用
                    message = client.messages.create(
                        model=model,
                        max_tokens=1024,
                        system=system_prompt,
                        messages=[
                            {"role": "user", "content": user_prompt}
                        ]
                    )
                    return message.content[0].text
                
                elif provider == "openai" or provider == "local":
                    # OpenAI兼容API调用
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.3
                    )
                    return response.choices[0].message.content
            
            except Exception as e:
                print(f"⚠️  {provider}调用错误: {e}，尝试下一个提供商...")
                last_error = str(e)
                continue
        
        # 所有提供商都失败了
        print(f"❌ 所有AI提供商都调用失败，最后错误: {last_error}")
        return None
    
    def classify_issue(self, title: str, body: str) -> Dict:
        """
        分类Issue类型（Bug/Feature/任务）
        
        输入参数：
        - title: Issue标题
        - body: Issue正文
        
        输出：
        - Dict: {"type": "bug|feature|task", "confidence": 0.0-1.0}
        """
        title, body = title or "", body or ""
        content = f"标题: {title}\n内容: {(body or '')[:500]}"
        
        system_prompt = """你是一个Issue分类助手。根据Issue的标题和内容，判断它是Bug、Feature还是任务。
只返回JSON格式：{"type": "bug|feature|task", "confidence": 0.0-1.0}"""
        
        result_text = self._call_ai(system_prompt, content)
        
        if result_text:
            try:
                # 尝试提取JSON
                result_text = result_text.strip()
                if result_text.startswith("```"):
                    # 移除代码块标记
                    result_text = result_text.split("```")[1]
                    if result_text.startswith("json"):
                        result_text = result_text[4:]
                result = json.loads(result_text)
                if "type" in result and result["type"] in ["bug", "feature", "task"]:
                    return result
            except:
                pass
        
        # 回退到基于规则的方法
        return self._rule_based_classify(title, body)
    
    def _rule_based_classify(self, title: str, body: str) -> Dict:
        """基于规则的回退分类方法"""
        title = title or ""
        body = body or ""
        text = (title + " " + body).lower()
        
        bug_keywords = ["bug", "错误", "缺陷", "问题", "崩溃", "异常", "报错", "fix", "修复"]
        feature_keywords = ["feature", "功能", "需求", "新增", "添加", "实现"]
        
        bug_score = sum(1 for keyword in bug_keywords if keyword in text)
        feature_score = sum(1 for keyword in feature_keywords if keyword in text)
        
        if bug_score > feature_score and bug_score > 0:
            return {"type": "bug", "confidence": min(bug_score / 3, 1.0)}
        elif feature_score > 0:
            return {"type": "feature", "confidence": min(feature_score / 3, 1.0)}
        else:
            return {"type": "task", "confidence": 0.7}
    
    def extract_priority(self, title: str, body: str, issue_type: str) -> str:
        """
        提取优先级（P0/P1/P2/P3）
        
        输入参数：
        - title: Issue标题
        - body: Issue正文
        - issue_type: Issue类型
        
        输出：
        - str: 优先级 (P0/P1/P2/P3)
        """
        title, body = title or "", body or ""
        content = f"类型: {issue_type}\n标题: {title}\n内容: {(body or '')[:500]}"
        
        system_prompt = """你是一个优先级判定助手。根据Issue的类型和内容，判断优先级。
P0: 紧急/崩溃性问题；P1: 高优先级；P2: 中优先级；P3: 低优先级。
只返回优先级：P0/P1/P2/P3"""
        
        priority = self._call_ai(system_prompt, content)
        
        if priority:
            priority = priority.strip().upper()
            if priority in ["P0", "P1", "P2", "P3"]:
                return priority
        
        # 回退到基于规则的方法
        return self._rule_based_priority(title, body, issue_type)
    
    def _rule_based_priority(self, title: str, body: str, issue_type: str) -> str:
        """基于规则的优先级判定"""
        title, body = title or "", body or ""
        text = (title + " " + body).lower()
        
        p0_keywords = ["崩溃", "crash", "无法使用", "阻塞", "紧急", "urgent", "critical"]
        p1_keywords = ["重要", "重要功能", "核心", "高优先级", "high priority"]
        p2_keywords = ["优化", "改进", "enhancement"]
        
        if any(kw in text for kw in p0_keywords):
            return "P0"
        elif any(kw in text for kw in p1_keywords):
            return "P1"
        elif any(kw in text for kw in p2_keywords):
            return "P2"
        else:
            return "P3"
    
    def extract_tags(self, title: str, body: str) -> List[str]:
        """
        提取标签
        
        输入参数：
        - title: Issue标题
        - body: Issue正文
        
        输出：
        - List[str]: 标签列表
        """
        title, body = title or "", body or ""
        content = f"标题: {title}\n内容: {(body or '')[:500]}"
        
        system_prompt = """你是一个标签提取助手。从Issue内容中提取3-5个关键词作为标签。
只返回JSON数组：["标签1", "标签2", ...]"""
        
        tags_text = self._call_ai(system_prompt, content)
        
        if tags_text:
            try:
                tags_text = tags_text.strip()
                if tags_text.startswith("```"):
                    tags_text = tags_text.split("```")[1]
                    if tags_text.startswith("json"):
                        tags_text = tags_text[4:]
                tags = json.loads(tags_text)
                if isinstance(tags, list):
                    return tags[:5]  # 最多5个标签
            except:
                pass
        
        # 回退到基于关键词的方法
        return self._rule_based_tags(title, body)
    
    def _rule_based_tags(self, title: str, body: str) -> List[str]:
        """基于规则的标签提取"""
        title, body = title or "", body or ""
        text = title + " " + body
        tags = []
        
        # 提取模块相关关键词
        module_keywords = ["前端", "后端", "API", "数据库", "UI", "mobile", "web", "测试", "文档"]
        for keyword in module_keywords:
            if keyword.lower() in text.lower():
                tags.append(keyword)
        
        return tags[:5]
    
    def generate_summary(self, title: str, body: str, comments: List[str]) -> str:
        """
        生成Issue摘要
        
        输入参数：
        - title: Issue标题
        - body: Issue正文
        - comments: 评论列表
        
        输出：
        - str: 摘要文本
        """
        title, body = title or "", body or ""
        comments_safe = [(c if isinstance(c, str) else (c or "")) for c in (comments or [])]
        comments_text = "\n".join(comments_safe[:10])  # 最多10条评论
        content = f"标题: {title}\n内容: {body}\n评论:\n{comments_text}"
        
        system_prompt = """你是一个摘要生成助手。总结Issue的核心内容、当前状态和关键信息。
生成100字以内的摘要。"""
        
        summary = self._call_ai(system_prompt, content[:2000])  # 限制长度
        
        if summary:
            return summary.strip()
        
        # 回退方法
        return f"{title}: {(body or '')[:100]}..."
    
    def analyze_blocking_reasons(self, issue_data: Dict, comments: List[Dict]) -> Optional[str]:
        """
        分析阻塞原因
        
        输入参数：
        - issue_data: Issue数据
        - comments: 评论列表
        
        输出：
        - Optional[str]: 阻塞原因，如果没有则返回None
        """
        import re
        
        blocking_keywords = ["阻塞", "blocked", "等待", "依赖", "无法进行", "需要"]
        body = issue_data.get("body") or ""
        parts = [body] + [((c or {}).get("body") or "") for c in (comments or [])]
        text = " ".join(parts)
        
        for keyword in blocking_keywords:
            if keyword in text:
                # 尝试提取阻塞原因
                pattern = rf"{keyword}[：:]\s*([^。\n]+)"
                match = re.search(pattern, text)
                if match:
                    return match.group(1).strip()
        
        return None


if __name__ == "__main__":
    # 测试代码
    parser = LLMParser()
    
    print("测试：Issue分类...")
    result = parser.classify_issue("修复登录页面崩溃问题", "用户登录时页面崩溃，需要紧急修复")
    print(f"✅ 分类结果: {result}")
    
    print("\n测试：优先级提取...")
    priority = parser.extract_priority("修复登录页面崩溃问题", "用户登录时页面崩溃", "bug")
    print(f"✅ 优先级: {priority}")
    
    print("\n测试：标签提取...")
    tags = parser.extract_tags("前端UI优化", "优化登录页面的用户体验")
    print(f"✅ 标签: {tags}")
