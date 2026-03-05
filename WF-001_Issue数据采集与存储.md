# WF-001: Issue数据采集与存储

## 📌 工作流基本信息

| 属性 | 内容 |
|------|------|
| **工作流ID** | WF-001 |
| **工作流名称** | Issue数据采集与存储 |
| **功能描述** | 从GitHub API拉取Issue数据（含comments、labels、timeline等），经AI清洗分析后存入MatrixOne数据库 |
| **实现状态** | ✅ 已实现 |
| **云端可用** | ✅ 完全可用 |
| **核心价值** | 自动化数据采集，AI智能分类，为后续分析提供数据基础 |

---

## 🔄 流程步骤总览

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  步骤1: GitHub  │ ───▶ │  步骤2: AI分析  │ ───▶ │  步骤3: 存储MO  │
│   API获取数据   │      │   清洗分类      │      │   数据库        │
└─────────────────┘      └─────────────────┘      └─────────────────┘
   获取Issue列表            AI智能分类               存储快照+AI结果
   + Comments              + 优先级判断              + 关联关系
   + Timeline              + 标签提取                + 评论数据
   + Labels                + 摘要生成
```

**快速理解**：
1. **步骤1** - 从GitHub拉取Issue原始数据（含comments、labels、timeline）
2. **步骤2** - 通义千问AI分析：类型、优先级、标签、摘要（有回退机制）
3. **步骤3** - 存入MatrixOne：原始快照+AI结果同时存储

**核心特点**：✅ Labels完整存储 | ✅ 原始+清洗都存 | ✅ AI多提供商回退

---

## 📥 整体输入

### 1. 必需配置输入

| 输入项 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| **repo_owner** | String | GitHub仓库所有者（用户名或组织名） | `matrixorigin` |
| **repo_name** | String | GitHub仓库名称 | `matrixone` |
| **GITHUB_TOKEN** | String | GitHub Personal Access Token，需要`repo`权限 | `ghp_xxxxxxxxxxxx` |
| **GITHUB_API_BASE_URL** | String | GitHub API基础URL | `https://api.github.com` |

### 2. 数据库连接配置

| 输入项 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| **DATABASE_TYPE** | String | 数据库类型 | `matrixone` / `mysql` / `postgresql` / `sqlite` |
| **MO_HOST** | String | MatrixOne主机地址 | `freetier-01.cn-hangzhou.cluster.matrixonecloud.cn` |
| **MO_PORT** | Integer | MatrixOne端口 | `6001` |
| **MO_USER** | String | MatrixOne用户名（格式：实例ID:admin:accountadmin） | `instance_abc:admin:accountadmin` |
| **MO_PASSWORD** | String | MatrixOne密码 | `your_password` |
| **MO_DATABASE** | String | MatrixOne数据库名 | `github_issues` |

### 3. AI服务配置

| 输入项 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| **AI_PROVIDER** | String | AI服务提供商 | `qwen` / `openai` / `claude` |
| **DASHSCOPE_API_KEY** | String | 通义千问API密钥（环境变量或配置） | `sk-xxxxxxxxxxxx` |
| **QWEN_BASE_URL** | String | 千问API地址 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| **QWEN_MODEL** | String | 千问模型名称 | `qwen-plus` / `qwen-max-latest` |

### 4. Issue规范文件（可选但推荐）

| 输入项 | 类型 | 说明 | 位置 |
|--------|------|------|------|
| **Issue模板文件** | Markdown | Issue标准模板，AI分析时作为参考 | `feature_issue_and_kanban/templates/*.md` |

**模板文件列表**：
- `MO_Bug.md` - MO产品Bug模板
- `MO_Feature.md` - MO产品Feature模板  
- `MOI_Bug.md` - MOI产品Bug模板
- `MOI_Feature.md` - MOI产品Feature模板
- `Customer_Project.md` - 客户项目模板
- `Test_Request.md` - 测试请求模板
- 等...

### 5. 运行参数（可选）

| 输入项 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| **state** | String | Issue状态过滤 | `all` (可选：`open`, `closed`) |
| **since** | DateTime | 增量同步起始时间 | `None`（全量） |
| **per_page** | Integer | 每页获取数量 | `100` |
| **ENABLE_FULL_RESYNC** | Boolean | 是否全量重新同步 | `False` |

---

## 📤 整体输出

### 1. 数据库存储结果

| 输出项 | 表名 | 说明 |
|--------|------|------|
| **Issue快照数据** | `issues_snapshot` | 存储Issue原始数据快照 + AI分析结果 |
| **AI解析结果** | `ai_parse` | 存储AI分类、优先级、标签等解析结果 |
| **Issue关联关系** | `issue_relations` | 存储Issue间的依赖、阻塞、相关等关系 |
| **评论数据** | `issue_comments` | 存储Issue的所有评论 |

### 2. 日志输出

| 输出项 | 类型 | 说明 |
|--------|------|------|
| **执行日志** | Console / File | 采集进度、AI调用状态、错误信息 |
| **统计信息** | JSON | 新增/更新/跳过的Issue数量 |

---

## 🔄 详细步骤拆分

### 步骤1: 调用GitHub API获取Issue数据

**步骤ID**: WF-001-S01  
**功能**: 从GitHub API分页获取Issue列表及详细信息  
**实现状态**: ✅ 已实现

#### 输入
- `repo_owner`: 仓库所有者（如 `matrixorigin`）
- `repo_name`: 仓库名称（如 `matrixone`）
- `GITHUB_TOKEN`: GitHub访问令牌
- `state`: Issue状态（`all` / `open` / `closed`）
- `since`: 增量同步起始时间（可选）
- `page`, `per_page`: 分页参数

#### 处理逻辑
1. 构建API请求URL: `GET /repos/{owner}/{repo}/issues`
2. 添加请求头:
   ```python
   {
       "Authorization": f"token {GITHUB_TOKEN}",
       "Accept": "application/vnd.github.v3+json",
       "User-Agent": "GitHub-Issue-Manager"
   }
   ```
3. 分页获取所有Issue（每页100条）
4. 对每个Issue，进一步获取：
   - **Comments**: `GET /repos/{owner}/{repo}/issues/{issue_number}/comments`
   - **Timeline**: `GET /repos/{owner}/{repo}/issues/{issue_number}/timeline`
   - **Labels**: 已包含在Issue数据中
5. 处理API限流（Rate Limit）：
   - 检查 `X-RateLimit-Remaining` 响应头
   - 如果剩余次数<10，等待到 `X-RateLimit-Reset` 时间
6. 错误重试机制：指数退避重试（2^n秒）

#### 输出
- **Issue原始数据**（JSON格式）包含：
  ```json
  {
    "id": 123456789,               // GitHub Issue ID (BIGINT)
    "number": 8450,                // Issue编号
    "title": "Bug: 查询超时",
    "body": "详细描述...",
    "state": "open",
    "labels": [                     // Labels完整信息
      {"name": "bug", "color": "d73a4a"},
      {"name": "customer/金盘", "color": "fbca04"}
    ],
    "assignee": "username",
    "milestone": "v1.0",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-02T00:00:00Z",
    "closed_at": null,
    "comments": [...],              // 所有评论
    "timeline": [...]               // 时间线事件
  }
  ```

#### 代码模块
- **文件**: `modules/github_collector/github_api.py`
- **类**: `GitHubCollector`
- **方法**:
  - `fetch_issues()` - 获取Issue列表
  - `fetch_issue_detail()` - 获取Issue详情
  - `fetch_issue_comments()` - 获取评论
  - `fetch_issue_timeline()` - 获取时间线
  - `extract_relations()` - 提取关联关系

---

### 步骤2: AI数据清洗与分析

**步骤ID**: WF-001-S02  
**功能**: 使用AI API分析Issue内容，进行智能分类和标签提取  
**实现状态**: ✅ 已实现

#### 输入
- **Issue原始数据**（步骤1输出）
- **AI配置**:
  - `AI_PROVIDER`: 使用的AI服务（`qwen`推荐）
  - `DASHSCOPE_API_KEY`: API密钥
  - `QWEN_MODEL`: 模型名称
- **Issue规范模板**（可选）: `feature_issue_and_kanban/templates/*.md`

#### 处理逻辑

**AI调用流程**：
1. 构建AI提示词（Prompt）：
   ```
   System Prompt: 你是GitHub Issue分析专家，负责分类和提取关键信息
   
   User Prompt:
   标题：{issue_title}
   内容：{issue_body}
   Labels：{labels}
   
   请分析并返回JSON格式：
   {
     "issue_type": "bug|feature|task|question",
     "priority": "P0|P1|P2|P3",
     "ai_tags": ["标签1", "标签2"],
     "ai_summary": "简洁摘要",
     "blocked_reason": "阻塞原因（如有）"
   }
   ```

2. **AI服务调用**（支持多提供商回退）：
   - **优先**：通义千问（OpenAI兼容接口）
     ```python
     client = OpenAI(api_key=DASHSCOPE_API_KEY, base_url=QWEN_BASE_URL)
     response = client.chat.completions.create(
         model=QWEN_MODEL,
         messages=[
             {"role": "system", "content": system_prompt},
             {"role": "user", "content": user_prompt}
         ]
     )
     ```
   - **回退**：Claude API（如果千问失败）
   - **回退**：基于规则的分类（如果所有AI失败）

3. **解析AI响应**：
   - 提取JSON结构
   - 验证字段有效性
   - 处理解析失败情况

4. **基于规则的回退方法**（AI失败时）：
   - 根据标题关键词判断类型（"Bug", "Feature", "Fix"等）
   - 根据标签推断优先级
   - 生成简单摘要（标题前50字）

#### 输出
- **AI分析结果**（JSON格式）：
  ```json
  {
    "issue_id": 123456789,
    "issue_type": "bug",           // bug/feature/task/question
    "priority": "P1",              // P0/P1/P2/P3
    "ai_summary": "查询超时问题，影响生产环境",
    "ai_tags": ["性能", "数据库", "紧急"],
    "blocked_reason": null,
    "is_blocked": false,
    "status": "待处理",            // 待处理/处理中/待评审/已完成/已关闭
    "progress_percentage": 0.0
  }
  ```

#### 代码模块
- **文件**: `modules/llm_parser/llm_parser.py`
- **类**: `LLMParser`
- **方法**:
  - `parse_issue()` - 解析单个Issue
  - `parse_issues_batch()` - 批量解析
  - `_call_ai()` - AI API调用（支持多提供商）
  - `_fallback_parse()` - 基于规则的回退方法

---

### 步骤3: 存储到MatrixOne数据库

**步骤ID**: WF-001-S03  
**功能**: 将Issue原始数据和AI分析结果存入数据库  
**实现状态**: ✅ 已实现

#### 输入
- **Issue原始数据**（步骤1输出）
- **AI分析结果**（步骤2输出）
- **数据库连接配置**（整体输入中的MO配置）

#### 处理逻辑

**数据库连接**：
```python
# 构建连接字符串
database_url = f"mysql+pymysql://{MO_USER}:{MO_PASSWORD}@{MO_HOST}:{MO_PORT}/{MO_DATABASE}?charset=utf8mb4"

# 创建引擎（带连接池）
engine = create_engine(
    database_url,
    pool_pre_ping=True,        # 连接前ping测试
    pool_size=5,               # 连接池大小
    max_overflow=10,           # 最大溢出连接数
    connect_args={
        "connect_timeout": 10,
        "charset": "utf8mb4",
        "read_timeout": 30,
        "write_timeout": 30
    }
)
```

**存储逻辑**：

1. **存储Issue快照** → `issues_snapshot`表：
   - **原始快照**：GitHub返回的完整数据
   - **AI分析结果**：ai_summary, ai_tags, ai_priority等字段
   - **两者合并存储**在同一条记录中

2. **存储AI解析结果** → `ai_parse`表（独立表）

3. **存储Issue关联关系** → `issue_relations`表

4. **存储评论** → `issue_comments`表

#### 输出
- **数据库记录**：Issue数据成功存入4个表
- **统计信息**：新增/更新/跳过数量

#### 代码模块
- **文件**: `modules/database_storage/mo_client.py`
- **类**: `MOStorage`
- **方法**: `save_issue()`, `save_issues_batch()`等

---

## 🗄️ 数据库表结构

### issues_snapshot（Issue快照表）

**说明**: 存储Issue的**原始数据快照 + AI分析结果**

主要字段：
- `issue_id` (BIGINT): GitHub Issue ID  
- `issue_number` (INT): Issue编号（#8450）
- `labels` (JSON): Labels完整信息（name, color, description）
- `ai_summary` (TEXT): AI生成摘要
- `ai_tags` (JSON): AI标签数组
- `ai_priority` (VARCHAR): AI优先级
- `snapshot_time` (DATETIME): 快照时间点

---

## ⚙️ 配置文件说明

**文件位置**: `config/config.py`

关键配置项已在"整体输入"部分详细说明。

---

## ✅ 实现验证

```bash
# 1. 检查数据库连接
python3 scripts/test_db_connection.py

# 2. 验证GitHub Token
python3 scripts/check_config.py

# 3. 运行采集测试
python3 auto_run.py --repo-owner matrixorigin --repo-name matrixone
```

---

## 🚨 关键确认点（根据用户要求）

### ✅ 1. Issue规范文件
**确认**：`feature_issue_and_kanban/templates/*.md` 作为AI分析的参考输入

### ✅ 2. Labels信息
**确认**：完整存储在 `labels` (JSON)字段中，包含name、color、description

### ✅ 3. 存储内容
**确认**：`issues_snapshot`表同时存储**原始快照 + AI清洗结果**

### ✅ 4. AI调用
**确认**：通义千问API用于分类和标签提取，有完整的回退机制

### ✅ 5. 连接配置
**确认**：需要完整的MO连接串（host/port/user/password/database）

### ✅ 6. Issue规范作用
**确认**：模板文件是AI分析的参考，也用于WF-002知识库生成

---

**文档版本**: v1.0  
**最后更新**: 2026-03-04
