# WF-006: 特殊Issue状态记录

## 📌 工作流基本信息

| 属性 | 内容 |
|------|------|
| **工作流ID** | WF-006 |
| **工作流名称** | 特殊Issue状态记录 |
| **功能描述** | 从MatrixOne的issues_snapshot表中，按Tag维度（customer/、project/等）筛选特殊Issue，提取状态和时间戳，存入专用表 |
| **实现状态** | ⚠️ 部分实现（project标签已实现，customer标签未实现） |
| **云端可用** | ✅ 完全可用 |
| **核心价值** | 为客户项目、专项任务提供独立的状态追踪，支持WF-008（项目看板生成） |

---

## 🔄 流程步骤总览

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   步骤1: 筛选   │ ───▶ │  步骤2: 提取    │ ───▶ │  步骤3: 存储    │
│   按Tag过滤     │      │  状态和时间点   │      │  到专用表       │
└─────────────────┘      └─────────────────┘      └─────────────────┘
  从issues_snapshot       提取关键信息              写入project_issues
  筛选project/标签        + pm_status              + snapshot_date
  获取最新快照            + progress               + 每日快照
                          + assignee
```

**快速理解**：
1. **步骤1** - 从`issues_snapshot`表按Tag筛选（如`project/问数深化`）
2. **步骤2** - 提取状态信息（state→pm_status、progress、assignee、时间戳）
3. **步骤3** - 存入`project_issues`专用表（带snapshot_date，支持历史追踪）

**核心特点**：✅ Tag维度筛选 | ✅ 时间戳记录 | ✅ 支持历史状态追踪

**实现状态**：✅ project/标签已实现 | ❌ customer/标签待实现

---

## 📥 整体输入

### 1. 数据源输入

| 输入项 | 类型 | 说明 | 来源 |
|--------|------|------|------|
| **repo_owner** | String | 仓库所有者 | `matrixorigin` |
| **repo_name** | String | 仓库名称 | `matrixflow`（通常） |
| **issues_snapshot表** | 数据库表 | 主Issue快照表 | WF-001的输出 |

### 2. 筛选条件配置

| 输入项 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| **project_tag** | String | Project标签（用于筛选） | `project/问数深化` / `project/Q1目标` |
| **customer_tag** | String | Customer标签（用于筛选） | `customer/金盘` / `customer/XX公司` |
| **snapshot_date** | Date | 快照记录日期 | `2026-03-04`（默认今天） |

### 3. 数据库连接配置

| 输入项 | 类型 | 说明 |
|--------|------|------|
| **DATABASE_URL** | String | MatrixOne连接串（同WF-001） |

---

## 📤 整体输出

### 1. 数据库存储

| 输出项 | 表名 | 说明 |
|--------|------|------|
| **Project Issue记录** | `project_issues` | 存储project/标签的Issue状态快照 |
| **Customer Issue记录** | `customer_issues` | 存储customer/标签的Issue状态快照（待实现） |

### 2. 记录内容

**每条记录包含**：
- Issue基本信息（number, title, state）
- 状态信息（pm_status, progress, assignee）
- **时间戳**（snapshot_date）- 关键字段
- 项目/客户标识

### 3. 统计输出

| 输出项 | 类型 | 说明 |
|--------|------|------|
| **处理数量** | Integer | 本次同步的Issue数量 |
| **更新数量** | Integer | 更新的已有记录数量 |

---

## 🔄 详细步骤拆分

### 步骤1: 按Tag筛选Issue

**步骤ID**: WF-006-S01  
**功能**: 从issues_snapshot表中筛选带特定Tag的Issue  
**实现状态**: ✅ 已实现（project标签）

#### 输入
- `repo_owner`, `repo_name`: 仓库标识
- `project_tag`: 项目标签（如 `project/问数深化`）
- **issues_snapshot表**: 主Issue快照表

#### 处理逻辑

**第1步：获取最新快照时间**：
```sql
SELECT MAX(snapshot_time) AS latest 
FROM issues_snapshot
WHERE repo_owner = :owner 
  AND repo_name = :repo
```

**第2步：筛选带指定Tag的Issue**：
```sql
SELECT 
    issue_number,
    title,
    body,
    state,               -- open/closed
    assignee,
    labels,              -- JSON字段，包含所有Labels
    milestone,
    created_at,
    updated_at,
    closed_at,
    progress_percentage, -- 进度百分比
    is_blocked,          -- 是否阻塞
    blocked_reason       -- 阻塞原因
FROM issues_snapshot
WHERE repo_owner = :owner 
  AND repo_name = :repo 
  AND snapshot_time = :latest
  AND labels LIKE :tag_like      -- 如 '%project/问数深化%'
```

**Labels字段处理**：
- `labels` 是JSON字符串：`'[{"name": "project/问数深化", "color": "..."}]'`
- 使用 `LIKE` 模糊匹配：`labels LIKE '%project/问数深化%'`

#### 输出
- **Issue列表**（Python字典数组）：
  ```python
  [
      {
          "issue_number": 1234,
          "title": "完成NL2SQL功能优化",
          "state": "open",
          "assignee": "zhangsan",
          "labels": '[{"name": "project/问数深化"}, ...]',
          "progress_percentage": 60,
          "is_blocked": False,
          "blocked_reason": None,
          ...
      },
      ...
  ]
  ```

#### 代码模块
- **文件**: `feature_issue_and_kanban/project_manager/project_sync.py`
- **类**: `ProjectSync`
- **方法**: `sync_project_issues(repo_owner, repo_name, project_tag)`

---

### 步骤2: 提取状态和时间点

**步骤ID**: WF-006-S02  
**功能**: 从Issue数据中提取关键状态信息和时间戳  
**实现状态**: ✅ 已实现

#### 输入
- **Issue列表**（步骤1输出）
- `snapshot_date`: 快照记录日期（默认今天）

#### 处理逻辑

**状态映射**：
```python
# GitHub state → PM status映射
if issue['state'] == 'closed':
    pm_status = 'completed'
else:
    pm_status = 'in_progress'  # 或根据progress_percentage细分
```

**进度处理**：
```python
progress = int(issue.get('progress_percentage', 0))
# 0-100的整数值
```

**时间点提取**：
```python
# 记录快照时间（用于追踪历史状态变化）
snapshot_date = date.today()  # 或指定日期

# 其他时间字段
created_at = issue['created_at']
updated_at = issue['updated_at']
closed_at = issue['closed_at']    # 可能为None
```

**生成Issue URL**：
```python
issue_url = f"https://github.com/{repo_owner}/{repo_name}/issues/{issue_number}"
```

#### 输出
- **结构化状态数据**：
  ```python
  {
      "issue_number": 1234,
      "issue_title": "完成NL2SQL功能优化",
      "issue_state": "open",
      "issue_url": "https://github.com/matrixorigin/matrixflow/issues/1234",
      "project_tag": "project/问数深化",
      "pm_status": "in_progress",
      "progress": 60,
      "assignee": "zhangsan",
      "snapshot_date": "2026-03-04"
  }
  ```

#### 代码模块
- **方法**: `_upsert_project_issue(...)`内的数据处理逻辑

---

### 步骤3: 存入专用表

**步骤ID**: WF-006-S03  
**功能**: 将状态数据写入 `project_issues` 表  
**实现状态**: ✅ 已实现

#### 输入
- **结构化状态数据**（步骤2输出）

#### 处理逻辑

**UPSERT逻辑**（插入或更新）：
```sql
INSERT INTO project_issues (
    issue_number,
    repo_owner,
    repo_name,
    issue_title,
    issue_state,
    issue_url,
    project_tag,
    pm_status,
    progress,
    assignee,
    snapshot_date
) VALUES (
    :issue_number,
    :repo_owner,
    :repo_name,
    :issue_title,
    :issue_state,
    :issue_url,
    :project_tag,
    :pm_status,
    :progress,
    :assignee,
    :snapshot_date
)
ON DUPLICATE KEY UPDATE
    issue_title = VALUES(issue_title),
    issue_state = VALUES(issue_state),
    pm_status = VALUES(pm_status),
    progress = VALUES(progress),
    assignee = VALUES(assignee),
    updated_at = CURRENT_TIMESTAMP
```

**唯一键约束**：
- `(issue_number, repo_owner, repo_name, project_tag, snapshot_date)`
- 同一天同一Issue只记录一次，更新时只更新状态字段

**事务处理**：
- 批量插入时使用事务
- 遇到重复键错误（Duplicate Key）时忽略或更新

#### 输出
- **数据库记录**: 成功写入 `project_issues` 表
- **处理统计**: 
  ```python
  {
      "total": 50,        # 处理的Issue总数
      "inserted": 10,     # 新插入记录数
      "updated": 40       # 更新已有记录数
  }
  ```

#### 代码模块
- **方法**: `_upsert_project_issue(...)`

---

## 🗄️ 数据库表结构

### project_issues（Project Issue状态表）

**说明**: 记录带 `project/` 标签的Issue每日状态快照

| 字段名 | 类型 | 说明 | 索引 |
|--------|------|------|------|
| id | INTEGER | 主键 | PK |
| issue_number | INTEGER | Issue编号 | YES |
| repo_owner | VARCHAR(100) | 仓库所有者 | YES |
| repo_name | VARCHAR(100) | 仓库名称 | YES |
| issue_title | VARCHAR(500) | Issue标题 | - |
| issue_state | VARCHAR(20) | GitHub状态（open/closed） | - |
| issue_url | VARCHAR(255) | Issue链接 | - |
| **project_tag** | VARCHAR(100) | 项目标签（如project/问数深化） | YES |
| **pm_status** | VARCHAR(50) | 项目管理状态 | - |
| **progress** | INTEGER | 进度（0-100） | - |
| **assignee** | VARCHAR(100) | 负责人 | - |
| **snapshot_date** | DATE | 快照日期（关键字段） | YES |
| created_at | DATETIME | 入库时间 | - |
| updated_at | DATETIME | 更新时间 | - |

**pm_status取值**：
- `in_progress`: 进行中
- `completed`: 已完成
- `blocked`: 阻塞中

**唯一约束**: `(issue_number, repo_owner, repo_name, project_tag, snapshot_date)`

---

### customer_issues（Customer Issue状态表）- 待实现

**说明**: 记录带 `customer/` 标签的Issue状态快照

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INTEGER | 主键 |
| issue_number | INTEGER | Issue编号 |
| repo_owner | VARCHAR(100) | 仓库所有者 |
| repo_name | VARCHAR(100) | 仓库名称 |
| issue_title | VARCHAR(500) | Issue标题 |
| issue_state | VARCHAR(20) | GitHub状态 |
| **customer_tag** | VARCHAR(100) | 客户标签（如customer/金盘） |
| **priority** | VARCHAR(10) | 优先级（P0/P1/P2/P3） |
| **severity** | VARCHAR(20) | 严重程度 |
| **snapshot_date** | DATE | 快照日期 |
| created_at | DATETIME | 入库时间 |
| updated_at | DATETIME | 更新时间 |

---

## ⚙️ 配置文件说明

**配置位置**: 代码调用时传参，无独立配置文件

**运行参数**：
```python
sync_project_issues(
    repo_owner="matrixorigin",
    repo_name="matrixflow",
    project_tag="project/问数深化",    # 可配置
    snapshot_date=date.today()         # 可指定日期
)
```

---

## 🔧 运行方式

### 方式1：使用同步脚本

```bash
python3 feature_issue_and_kanban/scripts/sync_project_issues.py \
    --repo-owner matrixorigin \
    --repo-name matrixflow \
    --project-tag "project/问数深化"
```

### 方式2：Python代码调用

```python
from feature_issue_and_kanban/project_manager.project_sync import ProjectSync
from modules.database_storage.mo_client import MOStorage
from datetime import date

# 初始化
storage = MOStorage()
syncer = ProjectSync(storage)

# 同步project标签的Issue
count = syncer.sync_project_issues(
    repo_owner="matrixorigin",
    repo_name="matrixflow",
    project_tag="project/问数深化",
    snapshot_date=date.today()
)

print(f"✅ 同步完成，处理了 {count} 个Issue")
```

### 方式3：定时任务（推荐）

```python
# 每日自动同步
import schedule
import time

def daily_sync():
    # 同步所有project标签
    for tag in ["project/问数深化", "project/Q1目标", "project/性能优化"]:
        count = syncer.sync_project_issues(
            repo_owner="matrixorigin",
            repo_name="matrixflow",
            project_tag=tag
        )
        print(f"{tag}: {count} issues")

# 每天早上9点执行
schedule.every().day.at("09:00").do(daily_sync)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## ✅ 实现验证

### 验证步骤

1. **检查数据库记录**：
   ```sql
   -- 查看project_issues表
   SELECT * FROM project_issues 
   WHERE project_tag = 'project/问数深化' 
   ORDER BY snapshot_date DESC 
   LIMIT 10;
   
   -- 统计每个项目的Issue数量
   SELECT project_tag, COUNT(*) as count 
   FROM project_issues 
   GROUP BY project_tag;
   
   -- 查看特定日期的快照
   SELECT * FROM project_issues 
   WHERE snapshot_date = '2026-03-04';
   ```

2. **验证时间序列**：
   ```sql
   -- 查看某个Issue的历史状态变化
   SELECT 
       snapshot_date,
       issue_state,
       pm_status,
       progress,
       assignee
   FROM project_issues 
   WHERE issue_number = 1234
   ORDER BY snapshot_date DESC;
   ```

3. **验证进度追踪**：
   ```sql
   -- 统计项目整体进度
   SELECT 
       AVG(progress) as avg_progress,
       SUM(CASE WHEN issue_state = 'closed' THEN 1 ELSE 0 END) as closed_count,
       COUNT(*) as total_count
   FROM project_issues 
   WHERE project_tag = 'project/问数深化' 
     AND snapshot_date = (SELECT MAX(snapshot_date) FROM project_issues);
   ```

---

## 🚨 实现状态说明

### ✅ 已实现

**Project标签同步**：
- Tag筛选：`project/*`
- 状态提取：state, progress, assignee
- 时间戳记录：snapshot_date
- 数据表：`project_issues`

**代码位置**：
- `feature_issue_and_kanban/project_manager/project_sync.py`
- `feature_issue_and_kanban/scripts/sync_project_issues.py`

### ❌ 未实现

**Customer标签同步**：
- Tag筛选：`customer/*`
- 专属字段：priority, severity
- 数据表：`customer_issues`（表结构待创建）

**实现建议**：
```python
# 参考project_sync.py实现customer_sync.py
class CustomerSync:
    def sync_customer_issues(
        self, 
        repo_owner: str, 
        repo_name: str, 
        customer_tag: str
    ):
        # 类似逻辑，筛选customer/标签
        # 存入customer_issues表
        pass
```

---

## 📊 使用场景

### 场景1：项目进度追踪

**需求**：追踪"问数深化"项目的每日进度

**实现**：
```python
# 每天执行一次
syncer.sync_project_issues(
    repo_owner="matrixorigin",
    repo_name="matrixflow",
    project_tag="project/问数深化"
)

# 查询30天进度趋势
SELECT 
    snapshot_date,
    AVG(progress) as avg_progress,
    COUNT(*) as total_issues
FROM project_issues
WHERE project_tag = 'project/问数深化'
  AND snapshot_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
GROUP BY snapshot_date
ORDER BY snapshot_date
```

### 场景2：客户Issue监控（待实现）

**需求**：监控"金盘客户"的Issue状态

**实现**：
```python
# 需要先实现customer_sync
customer_syncer.sync_customer_issues(
    repo_owner="matrixorigin",
    repo_name="matrixflow",
    customer_tag="customer/金盘"
)
```

---

## 🔄 云端部署注意事项

### ✅ 完全可用

该工作流在云端部署**无任何限制**：
- 纯数据库操作（SELECT + INSERT）
- 无本地文件依赖
- 无复杂计算

### 部署建议

1. **定时执行**：
   - 推荐每日执行（凌晨或早上）
   - 使用cron或云调度服务

2. **多Tag支持**：
   ```python
   # 配置需要监控的Tag列表
   project_tags = [
       "project/问数深化",
       "project/Q1目标",
       "project/性能优化"
   ]
   
   for tag in project_tags:
       syncer.sync_project_issues(..., project_tag=tag)
   ```

3. **容错处理**：
   - 使用try-except捕获异常
   - 记录失败日志
   - 继续处理其他Tag

---

## 📈 扩展方向

### 1. Customer标签支持

- 创建 `customer_issues` 表
- 实现 `CustomerSync` 类
- 添加客户专属字段（priority, severity）

### 2. 更多维度

- `milestone/` 标签：里程碑追踪
- `area/` 标签：功能模块追踪
- 自定义Tag：用户自定义分组

### 3. 关联关系记录

- 记录Issue之间的依赖关系
- 支持WF-008的甘特图生成

---

**文档版本**: v1.0  
**最后更新**: 2026-03-04
