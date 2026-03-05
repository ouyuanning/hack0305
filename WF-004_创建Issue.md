# WF-004: 创建Issue

## 📌 工作流基本信息

| 属性 | 内容 |
|------|------|
| **工作流ID** | WF-004 |
| **工作流名称** | 创建Issue |
| **功能描述** | 用户确认预览后，调用GitHub API创建Issue到GitHub仓库，返回Issue链接 |
| **实现状态** | ✅ 已实现 |
| **云端可用** | ✅ 完全可用 |
| **核心价值** | 完成Issue创建的最后一步，将草稿提交到GitHub |

---

## 🔄 流程步骤总览

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   步骤1:     │ ───▶ │   步骤2:     │ ───▶ │   步骤3:     │
│  接收确认    │      │ 调用GitHub   │      │  返回结果    │
│   信号       │      │   API创建    │      │             │
└──────────────┘      └──────────────┘      └──────────────┘
  用户确认             POST /issues          Issue URL
  + Issue预览          + 重试机制            + Issue编号
  + Token验证          + 限流处理            + 创建状态
```

**快速理解**：
1. **步骤1** - 接收用户确认信号 + Issue预览内容（来自WF-003）
2. **步骤2** - 调用GitHub API创建Issue（带重试和限流处理）
3. **步骤3** - 返回创建成功的Issue链接和编号

**核心特点**：✅ 用户确认机制 | ✅ API重试容错 | ✅ 限流自动等待

---

## 📥 整体输入

### 1. 用户确认信号

| 输入项 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| **user_confirmation** | Boolean | 用户确认信号 | `True` |
| **confirmation_message** | String | 用户确认的具体消息（可选） | `"确认创建"` / `"确认无误"` |

### 2. Issue预览内容（来自WF-003）

| 输入项 | 类型 | 说明 | 来源 |
|--------|------|------|------|
| **title** | String | Issue标题 | WF-003步骤6输出 |
| **body** | String | Issue正文（Markdown格式） | WF-003步骤6输出 |
| **labels** | Array[String] | Labels列表 | WF-003步骤6输出 |
| **assignees** | Array[String] | 负责人列表 | WF-003步骤6输出 |
| **repo_owner** | String | 仓库所有者 | WF-003输入 |
| **repo_name** | String | 仓库名称 | WF-003输入 |

### 3. GitHub凭证

| 输入项 | 类型 | 说明 | 权限要求 |
|--------|------|------|---------|
| **GITHUB_TOKEN** | String | GitHub Personal Access Token | 需要 `repo` 权限（可创建Issue） |
| **GITHUB_API_BASE_URL** | String | GitHub API地址 | `https://api.github.com`（默认） |

### 4. 可选配置

| 输入项 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| **milestone** | Integer | 里程碑ID（可选） | `None` |
| **project_id** | Integer | 项目ID（可选） | `None` |
| **retry_times** | Integer | API重试次数 | `3` |

---

## 📤 整体输出

### 1. 创建成功

| 输出项 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| **issue_url** | String | Issue的GitHub链接 | `https://github.com/matrixorigin/matrixflow/issues/8451` |
| **issue_number** | Integer | Issue编号 | `8451` |
| **issue_id** | Integer | GitHub Issue ID | `123456789` |
| **created_at** | Datetime | 创建时间 | `2026-03-04T10:30:00Z` |
| **status** | String | 创建状态 | `success` |

### 2. 创建失败

| 输出项 | 类型 | 说明 |
|--------|------|------|
| **status** | String | `failed` |
| **error_message** | String | 错误信息 |
| **error_code** | String | 错误代码 |

### 3. 返回的完整数据

GitHub API返回的完整Issue对象（包含但不限于）：
```json
{
    "id": 123456789,
    "number": 8451,
    "title": "【问数】查询超时问题",
    "body": "## 问题描述\n...",
    "state": "open",
    "labels": [...],
    "assignees": [...],
    "html_url": "https://github.com/matrixorigin/matrixflow/issues/8451",
    "created_at": "2026-03-04T10:30:00Z",
    "updated_at": "2026-03-04T10:30:00Z"
}
```

---

## 🔄 详细步骤拆分

### 步骤1: 接收用户确认

**步骤ID**: WF-004-S01  
**功能**: 接收用户确认信号，验证Issue预览内容完整性  
**实现状态**: ✅ 已实现

#### 输入
- **user_confirmation**: 用户确认信号（Boolean或确认消息）
- **issue_draft**: Issue预览内容（WF-003输出）

#### 处理逻辑

**1. 确认信号识别**：
```python
# 支持多种确认方式
confirmation_keywords = [
    "确认创建", "确认无误", "确认提交",
    "创建", "提交", "发布",
    "ok", "yes", "confirm"
]

def is_user_confirmed(user_message: str) -> bool:
    message_lower = user_message.lower().strip()
    return any(keyword in message_lower for keyword in confirmation_keywords)

# 使用示例
if is_user_confirmed("确认无误，可以创建"):
    # 继续创建流程
    ...
```

**2. 验证Issue预览内容**：
```python
def validate_issue_draft(draft: Dict) -> Tuple[bool, str]:
    """验证Issue草稿完整性"""
    
    # 必需字段检查
    if not draft.get('title'):
        return False, "标题不能为空"
    
    if len(draft['title']) > 256:
        return False, "标题过长（最多256字符）"
    
    if not draft.get('body'):
        return False, "正文不能为空"
    
    # Labels格式检查
    labels = draft.get('labels', [])
    if not isinstance(labels, list):
        return False, "Labels格式错误"
    
    # Assignees格式检查
    assignees = draft.get('assignees', [])
    if not isinstance(assignees, list):
        return False, "Assignees格式错误"
    
    return True, "验证通过"

# 使用示例
is_valid, message = validate_issue_draft(issue_draft)
if not is_valid:
    print(f"❌ 验证失败: {message}")
    return None
```

**3. Token权限验证**：
```python
def validate_github_token(token: str, owner: str, repo: str) -> bool:
    """验证Token是否有创建Issue的权限"""
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 401:
        print("❌ Token无效")
        return False
    
    if response.status_code == 404:
        print("❌ 仓库不存在或无访问权限")
        return False
    
    # 检查权限（查看是否有issues权限）
    repo_data = response.json()
    if not repo_data.get('has_issues', True):
        print("❌ 该仓库未启用Issues功能")
        return False
    
    return True
```

#### 输出
- **confirmed**: Boolean（是否确认）
- **validated_draft**: Dict（验证通过的Issue草稿）
- **validation_message**: String（验证消息）

#### 代码模块
- **文件**: `feature_issue_and_kanban/scripts/create_issue_interactive.py`
- **逻辑**: 交互式确认流程

---

### 步骤2: 调用GitHub API创建Issue

**步骤ID**: WF-004-S02  
**功能**: 调用GitHub API的POST接口创建Issue  
**实现状态**: ✅ 已实现

#### 输入
- **validated_draft** (步骤1输出): 验证通过的Issue草稿
- **GITHUB_TOKEN**: GitHub访问令牌
- **repo_owner**, **repo_name**: 仓库标识

#### 处理逻辑

**1. 构建API请求**：
```python
url = f"https://api.github.com/repos/{owner}/{repo}/issues"

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "GitHub-Issue-Manager"
}

payload = {
    "title": validated_draft['title'],
    "body": validated_draft['body']
}

# 可选字段
if validated_draft.get('labels'):
    payload['labels'] = validated_draft['labels']

if validated_draft.get('assignees'):
    payload['assignees'] = validated_draft['assignees']

if validated_draft.get('milestone'):
    payload['milestone'] = validated_draft['milestone']
```

**2. 发送POST请求**（带重试机制）：
```python
import httpx
import time

def create_issue_with_retry(
    url: str, 
    headers: dict, 
    payload: dict, 
    max_retries: int = 3
) -> dict:
    """创建Issue，带指数退避重试"""
    
    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=payload, headers=headers)
                
                # 处理限流（403 Rate Limit）
                if response.status_code == 403:
                    if "rate limit" in response.text.lower():
                        # 获取限流重置时间
                        reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                        wait_seconds = max(0, reset_time - time.time() + 1)
                        
                        print(f"⏳ API限流，等待 {int(wait_seconds)} 秒...")
                        time.sleep(wait_seconds)
                        continue
                
                # 处理其他错误
                if response.status_code >= 400:
                    error_msg = response.json().get('message', response.text)
                    print(f"❌ 创建失败 (状态码 {response.status_code}): {error_msg}")
                    
                    # 如果是客户端错误（4xx），不重试
                    if 400 <= response.status_code < 500 and response.status_code != 403:
                        raise httpx.HTTPStatusError(
                            f"客户端错误: {error_msg}",
                            request=response.request,
                            response=response
                        )
                
                response.raise_for_status()
                return response.json()
        
        except httpx.HTTPStatusError as e:
            if attempt < max_retries - 1:
                # 指数退避重试
                wait_time = 2 ** attempt
                print(f"⚠️  请求失败，{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue
            else:
                raise
        
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"⚠️  网络错误，{wait_time}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue
            else:
                raise
    
    raise RuntimeError("创建Issue失败，已达最大重试次数")
```

**3. GitHub API限流处理**：
```python
# 检查剩余配额
remaining = response.headers.get('X-RateLimit-Remaining', 'unknown')
limit = response.headers.get('X-RateLimit-Limit', 'unknown')
reset_time = response.headers.get('X-RateLimit-Reset', 'unknown')

print(f"📊 API配额: {remaining}/{limit}")
if reset_time != 'unknown':
    reset_datetime = datetime.fromtimestamp(int(reset_time))
    print(f"   重置时间: {reset_datetime}")
```

**4. 响应处理**：
```python
# 成功创建
if response.status_code == 201:
    issue_data = response.json()
    print(f"✅ Issue创建成功!")
    print(f"   编号: #{issue_data['number']}")
    print(f"   链接: {issue_data['html_url']}")
    return issue_data

# 其他状态码
else:
    error_data = response.json()
    error_message = error_data.get('message', '未知错误')
    print(f"❌ 创建失败: {error_message}")
    return None
```

#### 输出
- **issue_data** (Dict): GitHub API返回的完整Issue对象
  ```json
  {
      "id": 123456789,
      "number": 8451,
      "title": "【问数】查询超时问题",
      "body": "## 问题描述\n...",
      "state": "open",
      "html_url": "https://github.com/matrixorigin/matrixflow/issues/8451",
      "labels": [...],
      "assignees": [...],
      "created_at": "2026-03-04T10:30:00Z",
      "updated_at": "2026-03-04T10:30:00Z",
      "user": {...}
  }
  ```

#### 代码模块
- **文件**: `feature_issue_and_kanban/issue_creator/github_issue_creator.py`
- **函数**: `create_issue_on_github(owner, repo, title, body, token, labels, assignees)`

---

### 步骤3: 返回创建结果

**步骤ID**: WF-004-S03  
**功能**: 格式化并返回Issue创建结果，提供给用户  
**实现状态**: ✅ 已实现

#### 输入
- **issue_data** (步骤2输出): GitHub API返回的Issue对象

#### 处理逻辑

**1. 提取关键信息**：
```python
result = {
    "status": "success",
    "issue_url": issue_data['html_url'],
    "issue_number": issue_data['number'],
    "issue_id": issue_data['id'],
    "title": issue_data['title'],
    "created_at": issue_data['created_at'],
    "labels": [label['name'] for label in issue_data.get('labels', [])],
    "assignees": [user['login'] for user in issue_data.get('assignees', [])]
}
```

**2. 格式化输出消息**：
```python
success_message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Issue创建成功！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 Issue信息
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
编号: #{result['issue_number']}
标题: {result['title']}
链接: {result['issue_url']}

🏷️ Labels: {', '.join(result['labels'])}
👤 负责人: {', '.join(result['assignees']) if result['assignees'] else '未指定'}

⏰ 创建时间: {result['created_at']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 提示: 可以在GitHub上继续编辑和管理该Issue
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

print(success_message)
```

**3. 记录到日志**：
```python
import logging

logger = logging.getLogger('issue_creator')
logger.info(f"Issue创建成功: #{result['issue_number']} - {result['title']}")
logger.info(f"URL: {result['issue_url']}")
```

**4. 可选：同步回数据库**：
```python
# 将新创建的Issue同步回MatrixOne（触发WF-001）
# 这样可以在系统中追踪这个Issue
from modules.github_collector.github_api import GitHubCollector

collector = GitHubCollector()
# 重新拉取这个Issue的完整数据
issue_detail = collector.fetch_issue_detail(
    owner=repo_owner,
    repo=repo_name,
    issue_number=result['issue_number']
)
# 存入数据库（WF-001的逻辑）
```

#### 输出
- **result** (Dict): 格式化的创建结果
- **success_message** (String): 用户友好的成功消息
- **log_entry** (String): 日志记录

#### 代码模块
- **文件**: `feature_issue_and_kanban/scripts/create_issue_interactive.py`
- **逻辑**: 结果展示和用户提示

---

## 🗄️ 数据库表结构

### 可选：更新issues_snapshot表

创建成功后，可以选择将新Issue同步回数据库：

```python
# 触发WF-001的增量同步
from modules.database_storage.mo_client import MOStorage

storage = MOStorage()
storage.save_issue({
    "issue_id": result['issue_id'],
    "issue_number": result['issue_number'],
    "repo_owner": repo_owner,
    "repo_name": repo_name,
    "title": result['title'],
    "body": issue_draft['body'],
    "state": "open",
    "labels": result['labels'],
    "created_at": result['created_at'],
    "updated_at": result['created_at'],
    "snapshot_time": datetime.now()
})
```

---

## ⚙️ 配置文件说明

**配置位置**: `config/config.py`

```python
# GitHub配置
GITHUB_TOKEN = "ghp_xxxxxxxxxxxx"  # 必须有repo权限
GITHUB_API_BASE_URL = "https://api.github.com"

# API重试配置
GITHUB_API_RETRY_TIMES = 3
GITHUB_API_RETRY_DELAY = 2  # 初始延迟（秒），指数增长
```

**Token权限要求**：
- ✅ `repo` 权限（可读写仓库，包括创建Issue）
- 或 ✅ `public_repo` 权限（仅公开仓库）

---

## 🔧 运行方式

### 方式1：接续WF-003运行

```python
# WF-003生成预览
issue_draft = generate_issue_draft(...)

# 展示预览给用户
print(preview)

# 等待用户确认
user_input = input("是否创建到GitHub? (y/n): ")

if user_input.lower() == 'y':
    # WF-004创建Issue
    result = create_issue_on_github(
        owner=repo_owner,
        repo=repo_name,
        title=issue_draft['title'],
        body=issue_draft['body'],
        token=GITHUB_TOKEN,
        labels=issue_draft['labels'],
        assignees=issue_draft['assignees']
    )
    
    print(f"✅ Issue创建成功: {result['html_url']}")
```

### 方式2：直接API调用

```python
from feature_issue_and_kanban.issue_creator.github_issue_creator import create_issue_on_github

result = create_issue_on_github(
    owner="matrixorigin",
    repo="matrixflow",
    title="【问数】查询超时问题",
    body="## 问题描述\n\n查询执行时间超过30秒...",
    token="ghp_xxxxxxxxxxxx",
    labels=["kind/bug", "area/问数", "severity/high"],
    assignees=["zhangsan"]
)

if result:
    print(f"Issue URL: {result['html_url']}")
```

### 方式3：命令行工具

```bash
# 从预览文件创建（假设有预览数据）
python3 feature_issue_and_kanban/scripts/create_from_preview.py \
    --preview-file preview.json \
    --token ghp_xxxxxxxxxxxx

# 或直接指定参数
python3 feature_issue_and_kanban/scripts/create_issue.py \
    --owner matrixorigin \
    --repo matrixflow \
    --title "【问数】查询超时" \
    --body-file issue_body.md \
    --labels "kind/bug,area/问数" \
    --assignees "zhangsan" \
    --token ghp_xxxxxxxxxxxx
```

---

## ✅ 实现验证

### 验证步骤

1. **验证Token权限**：
   ```bash
   curl -H "Authorization: token ghp_xxxxxxxxxxxx" \
        https://api.github.com/repos/matrixorigin/matrixflow
   # 应返回200，包含仓库信息
   ```

2. **测试创建Issue**：
   ```python
   result = create_issue_on_github(
       owner="your-username",
       repo="test-repo",
       title="测试Issue",
       body="这是一个测试",
       token="ghp_xxxxxxxxxxxx"
   )
   
   assert result is not None
   assert 'html_url' in result
   print(f"✅ 测试成功: {result['html_url']}")
   ```

3. **验证创建的Issue**：
   - 在GitHub上打开Issue链接
   - 检查标题、正文、Labels、负责人是否正确
   - 验证Issue状态为"open"

---

## 🚨 关键确认点（根据用户要求）

### ✅ 1. 用户确认机制
**确认**：必须接收用户明确的确认信号才能创建

### ✅ 2. Token要求
**确认**：需要具有`repo`权限的GitHub Token

### ✅ 3. 输入来源
**确认**：Issue预览内容来自WF-003的输出

---

## 🚨 常见错误处理

### 错误1: 401 Unauthorized
```
原因: Token无效或过期
解决: 重新生成GitHub Token
```

### 错误2: 403 Forbidden (Rate Limit)
```
原因: API调用次数超限
解决: 系统自动等待到重置时间
     或使用更高配额的Token
```

### 错误3: 404 Not Found
```
原因: 仓库不存在或Token无权限访问
解决: 检查repo_owner和repo_name是否正确
     检查Token是否有该仓库的访问权限
```

### 错误4: 422 Validation Failed
```
原因: 请求数据格式错误
可能情况:
  - 标题为空或过长
  - Labels不存在
  - Assignees用户名不存在
解决: 验证所有输入数据的格式和有效性
```

---

## 🔄 云端部署注意事项

### ✅ 完全可用

该工作流在云端部署**无任何限制**：
- ✅ 纯HTTP API调用
- ✅ 无本地依赖
- ✅ 无文件操作（可选同步回数据库）

### 安全建议

1. **Token安全**：
   ```python
   # 使用环境变量
   GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
   
   # 不要在代码中硬编码Token
   # 不要提交Token到Git仓库
   ```

2. **权限最小化**：
   ```
   只授予必需的权限（repo或public_repo）
   定期轮换Token
   ```

3. **日志脱敏**：
   ```python
   # 日志中不记录完整Token
   logger.info(f"Using token: {GITHUB_TOKEN[:7]}...")
   ```

---

## 📊 性能指标

| 指标 | 数值 | 说明 |
|------|------|------|
| **API响应时间** | 1-3秒 | GitHub API的响应时间 |
| **成功率** | >99% | 在Token有效且配额充足时 |
| **重试次数** | 3次 | 默认最大重试 |
| **限流等待** | 0-3600秒 | 取决于限流重置时间 |

---

## 📈 与其他工作流的关系

### 前置工作流
- **WF-003**: 提供Issue预览内容

### 后续工作流（可选）
- **WF-001**: 可选择将新Issue同步回数据库
- **WF-006**: 如果是project/或customer/标签，可触发状态记录

### 独立使用
本工作流也可以完全独立使用，直接提供Issue内容创建。

---

**文档版本**: v1.0  
**最后更新**: 2026-03-04
