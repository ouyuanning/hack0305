# WF-003: 自动提Issue并生成样板

## 📌 工作流基本信息

| 属性 | 内容 |
|------|------|
| **工作流ID** | WF-003 |
| **工作流名称** | 自动提Issue并生成样板 |
| **功能描述** | 基于用户输入（文字+图片+浏览器上下文），AI智能生成Issue预览，**不创建到GitHub** |
| **实现状态** | ✅ 已实现 |
| **云端可用** | ⚠️ 部分可用（浏览器检测本地可用，云端需手动输入或浏览器扩展） |
| **核心价值** | 降低提Issue门槛，AI智能填充，多模态输入支持 |

---

## 🔄 流程步骤总览

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│  步骤1   │──▶│  步骤2   │──▶│  步骤3   │──▶│  步骤4   │──▶│  步骤5   │──▶│  步骤6   │──▶│  步骤7   │
│用户输入  │   │浏览器检测│   │AI判断类型│   │匹配模板  │   │检索相关  │   │AI生成    │   │生成预览  │
└──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
  文字+图片       4层回退策略     Issue类型      知识库查询     Issue搜索      完整内容      HTML/文字
  微信/Cursor     CDP/Window     MOI/MO Bug     模板结构       关联Issue      标题+正文      预览展示
                  Clipboard       Feature等      标签推荐                      Labels
                  Manual
```

**快速理解**：
1. **步骤1** - 获取用户输入：文字描述 + 截图（支持微信、Cursor等多渠道）
2. **步骤2** - 浏览器检测：4层回退（CDP→Window→Clipboard→Manual）获取正在浏览的Issue上下文
3. **步骤3** - AI判断类型：根据输入+浏览器Issue+知识库，判断Issue类型（MOI Bug、MO Feature等）
4. **步骤4** - 匹配知识库：查询产品、模块、Labels，获取模板结构
5. **步骤5** - 检索相关Issue：从MO库搜索相似Issue（关键词搜索）
6. **步骤6** - AI生成内容：调用通义千问生成标题、正文、Labels、负责人
7. **步骤7** - 生成预览：本地生成HTML，云端生成文字说明（**不创建到GitHub**）

**核心特点**：✅ 多模态输入 | ⚠️ 浏览器检测云端受限 | ✅ AI智能生成 | ✅ 只到预览不创建

---

## 📥 整体输入

### 1. 用户输入内容

| 输入项 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| **user_input** | String | 用户文字描述（自然语言） | `"查询超时，需要优化性能"` |
| **images** | File[] | 截图、错误截图、示意图（可选） | `.png`, `.jpg` 文件 |
| **input_channel** | String | 输入渠道 | `wechat` / `cursor` / `cli` |

### 2. 浏览器上下文（可选，自动检测）

| 输入项 | 类型 | 说明 | 检测方式 |
|--------|------|------|---------|
| **browser_issue_url** | String | 正在浏览的GitHub Issue链接 | 自动检测或手动输入 |
| **browser_issue_number** | Integer | Issue编号 | 从URL提取 |
| **browser_issue_labels** | Array | 浏览Issue的Labels | GitHub API获取 |

### 3. 数据库和知识库

| 输入项 | 类型 | 说明 | 来源 |
|--------|------|------|------|
| **知识库** | Markdown | 产品结构、标签体系、常见Issue | WF-002输出 |
| **历史Issue数据** | 数据库 | 用于相关Issue检索 | WF-001输出 |
| **Issue模板** | Markdown | 各类型Issue的标准模板 | `templates/*.md` |

### 4. AI服务配置

| 输入项 | 类型 | 说明 |
|--------|------|------|
| **AI_PROVIDER** | String | `qwen`（推荐） |
| **DASHSCOPE_API_KEY** | String | 通义千问API密钥 |
| **QWEN_MODEL** | String | `qwen-plus` |

### 5. GitHub配置

| 输入项 | 类型 | 说明 | 用途 |
|--------|------|------|------|
| **GITHUB_TOKEN** | String | GitHub访问令牌 | 用于获取浏览器Issue详情 |
| **repo_owner** | String | 目标仓库所有者 | `matrixorigin` |
| **repo_name** | String | 目标仓库名称 | `matrixone` / `matrixflow` |

---

## 📤 整体输出

### 1. Issue预览内容

| 输出项 | 类型 | 说明 |
|--------|------|------|
| **title** | String | AI生成的Issue标题 |
| **body** | String | Issue正文（按模板结构生成） |
| **labels** | Array | 推荐的Labels列表 |
| **assignees** | Array | 推荐的负责人 |
| **template_type** | String | 使用的模板类型 |
| **related_issues** | Array | 相关Issue列表 |

### 2. 预览展示

| 输出项 | 类型 | 说明 | 环境 |
|--------|------|------|------|
| **preview.html** | HTML文件 | 可视化预览页面 | 本地环境 |
| **preview_text** | String | 文字格式预览 | 云端环境 |

### 3. 元数据

| 输出项 | 类型 | 说明 |
|--------|------|------|
| **detection_source** | String | 浏览器检测方式 |
| **generation_time** | Float | AI生成耗时（秒） |
| **confidence** | String | AI生成置信度 |

---

## 🔄 详细步骤拆分

### 步骤1: 获取用户输入

**步骤ID**: WF-003-S01  
**功能**: 从不同渠道获取用户的文字描述和图片  
**实现状态**: ✅ 已实现

#### 输入
- **input_channel**: 输入渠道（`wechat` / `cursor` / `cli`）
- **user_message**: 用户消息对象（含文字和图片）

#### 处理逻辑

**支持的输入渠道**：

1. **微信输入** (`wechat`):
   ```python
   # 接收微信消息
   {
       "text": "查询超时问题",
       "images": [
           {"url": "http://...", "data": base64_data}
       ]
   }
   ```

2. **Cursor输入** (`cursor`):
   ```python
   # Cursor窗口信息提取
   {
       "text": "需要修复这个bug",
       "window_info": {
           "title": "Issue #8450",
           "url": "https://github.com/..."
       }
   }
   ```

3. **命令行输入** (`cli`):
   ```bash
   python3 create_issue_interactive.py \
       --title "查询超时" \
       --description "详细描述..." \
       --image screenshot.png
   ```

**文字提取**：
```python
user_input = message.get('text', '').strip()
```

**图片处理**：
```python
images = []
for img in message.get('images', []):
    # OCR提取图片中的文字
    text_in_image = extract_text_from_image(img)
    # 合并到user_input
    user_input += f"\n[图片内容: {text_in_image}]"
    images.append(img)
```

#### 输出
- **user_input** (String): 完整的用户描述（含图片OCR文字）
- **images** (Array): 图片数据数组

#### 代码模块
- **文件**: `feature_issue_and_kanban/services/unified_interface.py`
- **方法**: 各渠道的消息接收和解析

---

### 步骤2: 浏览器上下文检测（4层回退）

**步骤ID**: WF-003-S02  
**功能**: 智能检测用户正在浏览的GitHub Issue，作为上下文参考  
**实现状态**: ✅ 已实现（云端部分受限）

#### 输入
- **GITHUB_TOKEN**: GitHub访问令牌（用于获取Issue详情）

#### 处理逻辑

**4层回退策略**（按优先级依次尝试）：

**策略1: Chrome CDP（Chrome DevTools Protocol）**
```python
# 需要Chrome以debug模式启动
# chrome.exe --remote-debugging-port=9222

import websocket
ws = websocket.create_connection("ws://localhost:9222/...")
# 获取当前激活Tab的URL
result = ws.send('{"method":"Target.getTargets"}')
# 解析GitHub Issue URL
url = parse_github_issue_url(active_tab_url)
```

**优点**: 最准确，实时获取  
**限制**: ⚠️ 需要本地Chrome，云端不可用

---

**策略2: 系统窗口标题检测**
```python
import pygetwindow as gw

# 获取所有窗口
windows = gw.getAllTitles()

# 查找包含GitHub Issue的窗口
for title in windows:
    if 'github.com' in title.lower():
        # 从窗口标题提取Issue号
        match = re.search(r'#(\d+)', title)
        if match:
            issue_number = int(match.group(1))
```

**优点**: 不依赖浏览器  
**限制**: ⚠️ 需要本地系统API，云端不可用

---

**策略3: 剪贴板检测**
```python
import pyperclip

# 读取剪贴板内容
clipboard_text = pyperclip.paste()

# 匹配GitHub Issue URL
match = re.search(
    r'https://github\.com/([^/]+)/([^/]+)/issues/(\d+)',
    clipboard_text
)
if match:
    owner, repo, number = match.groups()
```

**优点**: 简单易用  
**限制**: ⚠️ 需要本地剪贴板访问，云端不可用

---

**策略4: 手动输入（云端可用）**
```python
print("请输入Issue URL或编号：")
user_input = input().strip()

# 支持多种格式
formats = [
    r'https://github\.com/([^/]+)/([^/]+)/issues/(\d+)',  # 完整URL
    r'#(\d+)',                                              # #8450
    r'(\d+)',                                               # 8450
]

for pattern in formats:
    match = re.search(pattern, user_input)
    if match:
        # 解析并获取Issue信息
        ...
```

**优点**: ✅ 云端可用，通用性强  
**限制**: 需要用户手动操作

---

**GitHub API获取Issue详情**：
```python
# 无论通过哪种方式获得Issue号，都调用API获取详情
url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}"
response = requests.get(url, headers={
    "Authorization": f"token {GITHUB_TOKEN}"
})

issue_data = response.json()
# 提取有用信息
browser_issue = {
    "number": issue_data['number'],
    "owner": owner,
    "repo": repo,
    "title": issue_data['title'],
    "labels": [label['name'] for label in issue_data['labels']],
    "url": issue_data['html_url'],
    "source": detection_method  # cdp/window/clipboard/manual
}
```

#### 输出
- **browser_issue** (Dict | None): 浏览器Issue上下文
  ```json
  {
      "number": 8450,
      "owner": "matrixorigin",
      "repo": "matrixflow",
      "title": "NL2SQL翻译错误",
      "labels": ["area/问数", "kind/bug", "customer/金盘"],
      "url": "https://github.com/matrixorigin/matrixflow/issues/8450",
      "source": "cdp"
  }
  ```
- 如果所有策略失败，返回 `None`

#### 代码模块
- **文件**: `feature_issue_and_kanban/utils/browser_context_smart.py`
- **函数**: `get_issue_context_smart(github_token)`
- **子模块**:
  - `cdp_detector.py` - CDP检测
  - `window_detector.py` - 窗口检测
  - `clipboard_detector.py` - 剪贴板检测
  - `manual_input.py` - 手动输入

---

### 步骤3: AI判断Issue类型

**步骤ID**: WF-003-S03  
**功能**: 根据用户输入、浏览器Issue、知识库，智能判断Issue类型  
**实现状态**: ✅ 已实现

#### 输入
- **user_input** (步骤1输出): 用户描述
- **browser_issue** (步骤2输出): 浏览器Issue上下文（可选）
- **knowledge_base**: 知识库内容（WF-002输出）

#### 处理逻辑

**3层判断策略**（按优先级）：

**层1: 基于浏览器Issue的Labels**
```python
if browser_issue and browser_issue.get('labels'):
    labels = browser_issue['labels']
    
    # 规则映射
    if 'product/mo' in labels:
        if 'kind/bug' in labels:
            return 'MO_Bug'
        elif 'kind/feature' in labels:
            return 'MO_Feature'
    
    elif 'area/问数' in labels or 'area/chatbi' in labels:
        if 'kind/bug' in labels:
            return 'MOI_Bug'
        elif 'kind/feature' in labels:
            return 'MOI_Feature'
```

**层2: AI + 知识库推断**
```python
prompt = f"""
你是Issue分类专家。根据以下信息判断Issue类型。

用户描述：{user_input}

浏览器Issue：{browser_issue}

知识库（产品结构）：
{knowledge_base}

可选类型：
- MOI_Bug: MOI产品的Bug
- MOI_Feature: MOI产品的功能需求
- MO_Bug: MO数据库的Bug
- MO_Feature: MO数据库的功能
- Customer_Project: 客户项目
- Doc_Request: 文档需求
- Test_Request: 测试需求

请返回最合适的类型（只返回类型名称）。
"""

ai_response = llm.call(prompt)
return ai_response.strip()
```

**层3: 基于关键词的回退**
```python
# AI失败时的规则判断
keywords_map = {
    'MOI_Bug': ['问数', 'chatbi', 'nl2sql', '翻译', '查询'],
    'MO_Bug': ['数据库', 'storage', 'sql', '性能', '超时'],
    'MOI_Feature': ['新功能', '支持', '增加'],
    'Doc_Request': ['文档', 'readme', '说明'],
}

for issue_type, keywords in keywords_map.items():
    if any(kw in user_input.lower() for kw in keywords):
        return issue_type

return 'MOI_Bug'  # 默认类型
```

#### 输出
- **template_type** (String): Issue类型
  - 可能值: `MOI_Bug`, `MOI_Feature`, `MO_Bug`, `MO_Feature`, `Customer_Project`, `Doc_Request`, `Test_Request`, `MOI_SubTask`, `EE_Feature`, `User_Bug`

#### 代码模块
- **文件**: `feature_issue_and_kanban/issue_creator/ai_issue_generator.py`
- **方法**: `_infer_bug_type_intelligent(user_input, knowledge_base, browser_issue)`

---

### 步骤4: 匹配知识库和模板

**步骤ID**: WF-003-S04  
**功能**: 根据Issue类型，加载模板结构，查询相关产品/标签信息  
**实现状态**: ✅ 已实现

#### 输入
- **template_type** (步骤3输出): Issue类型
- **knowledge_base**: 知识库（WF-002输出）

#### 处理逻辑

**1. 加载Issue模板文件**：
```python
template_file = f"feature_issue_and_kanban/templates/{template_type}.md"
template_content = Path(template_file).read_text(encoding='utf-8')

# 模板示例（MOI_Bug.md）：
"""
## 问题描述
[请详细描述问题]

## 复现步骤
1. 
2. 
3. 

## 期望行为
[描述期望的正确行为]

## 实际行为
[描述实际发生的错误行为]

## 环境信息
- 产品: 问数/ChatBI
- 版本: 
- 浏览器: 

## 相关Issue
[如有相关Issue请链接]
"""
```

**2. 提取模板结构提示**：
```python
# 从模板中提取章节标题，给AI参考
template_hint = extract_sections(template_content)
# 结果: ["问题描述", "复现步骤", "期望行为", "实际行为", "环境信息", "相关Issue"]
```

**3. 查询知识库推荐Labels**：
```python
# 从知识库中查询该类型常用的Labels
if template_type == 'MOI_Bug':
    recommended_labels = [
        'kind/bug',
        'area/问数',  # 或 'area/chatbi'，根据user_input推断
        'severity/medium'  # 根据严重程度
    ]
```

**4. 推荐负责人**：
```python
# 从历史Issue中统计该类型的常见负责人
sql = """
    SELECT assignee, COUNT(*) as count
    FROM issues_snapshot
    WHERE labels LIKE '%area/问数%' AND labels LIKE '%kind/bug%'
    GROUP BY assignee
    ORDER BY count DESC
    LIMIT 3
"""
assignees = execute_query(sql)
```

#### 输出
- **template_structure** (Dict): 模板结构信息
  ```json
  {
      "type": "MOI_Bug",
      "sections": ["问题描述", "复现步骤", "期望行为", ...],
      "recommended_labels": ["kind/bug", "area/问数"],
      "recommended_assignees": ["zhangsan", "lisi"]
  }
  ```

#### 代码模块
- **方法**: `_get_template_structure_hint(template_type)`

---

### 步骤5: 检索相关Issue

**步骤ID**: WF-003-S05  
**功能**: 从历史Issue中搜索相似Issue，避免重复  
**实现状态**: ⚠️ 部分实现（关键词搜索，未实现向量搜索）

#### 输入
- **user_input** (步骤1输出): 用户描述
- **template_type** (步骤3输出): Issue类型
- **repo_owner**, **repo_name**: 仓库标识

#### 处理逻辑

**关键词提取**：
```python
# 从user_input中提取关键词
keywords = extract_keywords(user_input)
# 例如: ["查询", "超时", "性能"]
```

**数据库搜索**（关键词匹配）：
```sql
SELECT 
    issue_number,
    title,
    body,
    labels,
    state
FROM issues_snapshot
WHERE repo_owner = :owner 
  AND repo_name = :repo
  AND (
      title LIKE '%查询%' OR title LIKE '%超时%'
      OR body LIKE '%查询%' OR body LIKE '%超时%'
  )
  AND labels LIKE '%kind/bug%'  -- 根据类型过滤
ORDER BY updated_at DESC
LIMIT 10
```

**相似度排序**（简单版）：
```python
# 计算标题相似度
for issue in search_results:
    similarity = calculate_similarity(user_input, issue['title'])
    issue['similarity_score'] = similarity

# 排序并取前5个
related_issues = sorted(search_results, key=lambda x: -x['similarity_score'])[:5]
```

**未实现：向量搜索**（优化方向）：
```python
# TODO: 使用向量数据库进行语义搜索
# 1. 将user_input转换为向量
# 2. 查询最相似的Issue向量
# 3. 返回最相关的Issue
```

#### 输出
- **related_issues** (Array): 相关Issue列表
  ```json
  [
      {
          "number": 8450,
          "title": "查询超时问题",
          "url": "https://github.com/matrixorigin/matrixflow/issues/8450",
          "similarity_score": 0.85
      },
      ...
  ]
  ```

#### 代码模块
- **文件**: `feature_issue_and_kanban/issue_creator/duplicate_detector.py`
- **方法**: `search_related_issues(user_input, repo_owner, repo_name)`

---

### 步骤6: AI生成Issue内容

**步骤ID**: WF-003-S06  
**功能**: 调用AI API，生成完整的Issue标题、正文、Labels  
**实现状态**: ✅ 已实现

#### 输入
- **user_input** (步骤1输出): 用户描述
- **browser_issue** (步骤2输出): 浏览器上下文
- **template_type** (步骤3输出): Issue类型
- **template_structure** (步骤4输出): 模板结构
- **related_issues** (步骤5输出): 相关Issue
- **knowledge_base**: 知识库

#### 处理逻辑

**构建AI Prompt**：
```python
prompt = f"""
你是GitHub Issue撰写专家。请根据以下信息生成一个完整的Issue。

【用户描述】
{user_input}

【浏览器上下文】
正在浏览的Issue: #{browser_issue['number']} - {browser_issue['title']}
Labels: {browser_issue['labels']}

【Issue类型】
{template_type}

【模板结构】
{template_structure['sections']}

【知识库（产品信息）】
{knowledge_base[:3000]}

【相关Issue】
{related_issues}

【要求】
1. 标题：简洁明确，包含关键信息（20-50字）
2. 正文：按模板结构组织，详细描述
3. Labels：从知识库中选择合适的标签
4. 负责人：根据历史数据推荐

请返回JSON格式：
{{
    "title": "Issue标题",
    "body": "Issue正文（Markdown格式）",
    "labels": ["kind/bug", "area/问数", "severity/high"],
    "assignees": ["zhangsan"]
}}
"""
```

**调用AI API**：
```python
client = OpenAI(api_key=DASHSCOPE_API_KEY, base_url=QWEN_BASE_URL)
response = client.chat.completions.create(
    model=QWEN_MODEL,
    messages=[
        {"role": "system", "content": "你是Issue撰写专家，只输出JSON格式。"},
        {"role": "user", "content": prompt}
    ],
    temperature=0.7
)

ai_output = response.choices[0].message.content
```

**解析AI响应**：
```python
# 提取JSON（去除Markdown代码块）
json_text = extract_json(ai_output)
issue_draft = json.loads(json_text)

# 验证和修正
issue_draft['title'] = issue_draft.get('title', '').strip()
issue_draft['body'] = issue_draft.get('body', '').strip()
issue_draft['labels'] = issue_draft.get('labels', [])
issue_draft['assignees'] = issue_draft.get('assignees', [])
```

**追加浏览器Issue信息**（如果有）：
```python
if browser_issue:
    issue_draft['body'] += f"\n\n## 相关Issue\n\n#{browser_issue['number']}: {browser_issue['title']}\n{browser_issue['url']}"
```

#### 输出
- **issue_draft** (Dict): 完整的Issue草稿
  ```json
  {
      "title": "【问数】NL2SQL查询超时问题",
      "body": "## 问题描述\n\n在使用问数进行复杂查询时...\n\n## 复现步骤\n...",
      "labels": ["kind/bug", "area/问数", "severity/high", "customer/金盘"],
      "assignees": ["zhangsan"],
      "template_type": "MOI_Bug",
      "related_issues": [...]
  }
  ```

#### 代码模块
- **文件**: `feature_issue_and_kanban/issue_creator/ai_issue_generator.py`
- **方法**: `generate_issue_draft(user_input, repo_owner, repo_name)`

---

### 步骤7: 生成预览

**步骤ID**: WF-003-S07  
**功能**: 生成可视化预览（HTML或文字），**不创建到GitHub**  
**实现状态**: ✅ 已实现（云端可能生成文字预览）

#### 输入
- **issue_draft** (步骤6输出): Issue草稿
- **repo_owner**, **repo_name**: 仓库标识

#### 处理逻辑

**本地环境：生成HTML预览**
```python
# 调用预览生成脚本
html_path = generate_html_preview(
    repo=f"{repo_owner}/{repo_name}",
    title=issue_draft['title'],
    body=issue_draft['body'],
    labels=','.join(issue_draft['labels']),
    assignees=','.join(issue_draft['assignees']),
    issue_type=issue_draft['template_type'],
    output_html='preview.html'
)

# HTML预览包含：
# - GitHub风格的Issue展示
# - Labels按分组显示（kind/, area/, project/等）
# - 负责人、里程碑等元信息
# - 正文Markdown渲染
```

**云端环境：生成文字预览**
```python
# 如果无法生成HTML，返回文字格式
preview_text = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 Issue预览
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【标题】
{issue_draft['title']}

【仓库】
{repo_owner}/{repo_name}

【类型】
{issue_draft['template_type']}

【Labels】
{', '.join(issue_draft['labels'])}

【负责人】
{', '.join(issue_draft['assignees'])}

【正文】
{issue_draft['body']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 预览生成完成
请确认无误后，回复"确认创建"即可提交到GitHub
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
```

**HTML预览示例**（本地）：
- GitHub风格界面
- 左侧：标题、正文
- 右侧：Labels、Type、负责人、里程碑等信息
- 顶部：成功提示banner

#### 输出
- **preview_html** (String): HTML文件路径（本地）
- **preview_text** (String): 文字预览内容（云端）
- **issue_draft** (Dict): Issue草稿数据（供WF-004使用）

#### 代码模块
- **文件**: `feature_issue_and_kanban/scripts/generate_preview_only.py`
- **主函数**: `main()`（命令行调用）
- **返回**: HTML文件路径或文字内容

---

## 🗄️ 数据库表结构

### 本工作流不直接操作数据库

本工作流主要是**读取**操作：
- 读取 `issues_snapshot` 表（步骤5：检索相关Issue）
- 读取 `issue_knowledge_base` 表（步骤4：查询知识库）

**不写入任何表**，所有数据保存在内存中，等待用户确认后交给WF-004创建。

---

## ⚙️ 配置文件说明

**主配置**: `config/config.py`

```python
# GitHub配置
GITHUB_TOKEN = "ghp_xxxxxxxxxxxx"

# AI配置
AI_PROVIDER = "qwen"
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
QWEN_MODEL = "qwen-plus"

# 浏览器检测配置（代码内部）
CHROME_DEBUG_PORT = 9222  # CDP端口
ENABLE_BROWSER_DETECTION = True  # 是否启用浏览器检测
```

**模板路径**: `feature_issue_and_kanban/templates/`

---

## 🔧 运行方式

### 方式1：交互式命令行

```bash
python3 feature_issue_and_kanban/scripts/create_issue_interactive.py \
    --repo-owner matrixorigin \
    --repo-name matrixflow

# 然后按提示输入Issue描述
```

### 方式2：直接生成预览（跳过浏览器检测）

```bash
python3 feature_issue_and_kanban/scripts/generate_preview_only.py \
    --repo matrixorigin/matrixflow \
    --title "【问数】查询超时问题" \
    --body "详细描述..." \
    --labels "kind/bug,area/问数,severity/high" \
    --assignees "zhangsan" \
    --type "MOI Bug" \
    --output-html preview.html
```

### 方式3：Python代码调用

```python
from feature_issue_and_kanban.issue_creator.ai_issue_generator import AIIssueGenerator
from modules.database_storage.mo_client import MOStorage
from modules.llm_parser.llm_parser import LLMParser

# 初始化
storage = MOStorage()
llm = LLMParser()
generator = AIIssueGenerator(storage, llm, GITHUB_TOKEN)

# 生成Issue草稿
issue_draft = generator.generate_issue_draft(
    user_input="查询超时，需要优化性能",
    repo_owner="matrixorigin",
    repo_name="matrixflow"
)

print(f"标题: {issue_draft['title']}")
print(f"Labels: {issue_draft['labels']}")
print(f"正文:\n{issue_draft['body']}")
```

---

## ✅ 实现验证

### 验证步骤

1. **测试浏览器检测**（本地环境）：
   ```bash
   # 启动Chrome调试模式
   chrome.exe --remote-debugging-port=9222
   
   # 打开一个Issue页面
   # 运行检测
   python3 -c "from feature_issue_and_kanban.utils.browser_context_smart import *; print(get_issue_context_smart('ghp_xxx'))"
   ```

2. **测试AI生成**：
   ```bash
   python3 feature_issue_and_kanban/scripts/create_issue_interactive.py
   # 输入描述，查看生成结果
   ```

3. **测试预览生成**：
   ```bash
   # 生成HTML预览
   python3 feature_issue_and_kanban/scripts/generate_preview_only.py \
       --repo matrixorigin/matrixflow \
       --title "测试Issue" \
       --body "测试内容" \
       --labels "kind/bug" \
       --output-html test_preview.html
   
   # 在浏览器中打开
   open test_preview.html
   ```

---

## 🚨 关键确认点（根据用户要求）

### ✅ 1. 只到预览，不创建
**确认**：步骤7生成预览后**工作流结束**，不调用GitHub API创建Issue

### ⚠️ 2. 云端预览方式
**确认**：
- **本地环境**：生成HTML文件（`preview.html`），可在浏览器打开
- **云端环境**：生成文字说明（格式化的文本预览），无法生成完整HTML

### ✅ 3. 浏览器检测
**确认**：4层回退策略，本地环境全部可用，云端只有**策略4（手动输入）**可用

---

## 🔄 云端部署注意事项

### ⚠️ 部分可用

**云端限制**：
- ❌ CDP检测：需要本地Chrome
- ❌ 窗口检测：需要本地系统API
- ❌ 剪贴板检测：需要本地剪贴板访问
- ✅ 手动输入：完全可用
- ⚠️ HTML预览：可能无法生成完整HTML

### 云端部署方案

**方案1：浏览器扩展**（推荐）
```javascript
// Chrome扩展获取当前Issue
chrome.tabs.query({active: true}, function(tabs) {
    let url = tabs[0].url;
    // 发送到云端API
    fetch('https://api.example.com/create-issue', {
        method: 'POST',
        body: JSON.stringify({
            browser_issue_url: url,
            user_input: "..."
        })
    });
});
```

**方案2：手动输入模式**
```python
# 云端运行时，提示用户输入Issue URL
print("请输入正在浏览的Issue URL（可选）：")
browser_url = input().strip()

if browser_url:
    # 解析并获取Issue信息
    browser_issue = fetch_issue_from_url(browser_url)
else:
    browser_issue = None
```

**方案3：文字预览**
```python
# 云端无法生成HTML时，返回格式化文本
if not can_generate_html():
    return generate_text_preview(issue_draft)
```

---

## 📊 性能指标

| 指标 | 数值 | 说明 |
|------|------|------|
| **总耗时** | 5-15秒 | 取决于AI响应时间 |
| **浏览器检测** | 0.5-2秒 | CDP最快，手动输入最慢 |
| **AI生成** | 3-10秒 | 通义千问API响应时间 |
| **预览生成** | <1秒 | 本地HTML生成 |
| **成功率** | ~90% | AI生成成功率 |

---

## 📈 优化方向

### 1. 向量搜索（步骤5）
- 当前：关键词匹配（准确率有限）
- 优化：使用向量数据库进行语义搜索

### 2. 浏览器扩展（步骤2）
- 开发Chrome/Edge扩展
- 实现云端环境的浏览器检测

### 3. 多轮对话优化
- 支持用户追问和修改
- AI根据反馈迭代生成

---

**文档版本**: v1.0  
**最后更新**: 2026-03-04
