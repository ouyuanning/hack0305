# Labels 标签使用说明

本文档说明 GitHub Issue 上的 Labels（标签/tag）在系统中的存储方式及使用示例。

---

## 仓库说明

| 仓库 | 定位 | 标签特点 |
|------|------|----------|
| **matrixorigin/matrixone** | 数据库内核 | kind/、area/、severity/、priority/ 等，无 customer 标签 |
| **matrixorigin/matrixflow** | 应用/产品 | 含 `customer/金盘`、`customer/安利` 等客户标签；ChatBI、问数、数据总览等业务标签 |

两仓库**分别同步**，需分别指定 `--repo-name matrixone` 或 `matrixflow`。

---

## 一、标签存储说明

### 1.1 两套标签体系

| 字段 | 来源 | 说明 |
|------|------|------|
| **labels** | GitHub API | Issue 上手动添加的标签，**完整保留** |
| **ai_tags** | AI 解析 | 从标题和正文中提取的关键词，作为补充 |

### 1.2 存储格式

- **labels**：来自 `issue_data.get('labels')`，保存每个 label 的 `name`
- **存储**：JSON 数组格式，例如 `["kind/bug", "customer/金盘", "ChatBI"]`
- **位置**：`issues_snapshot` 表的 `labels` 列

### 1.3 标签分类示例

不同仓库的标签体系可能不同，常见分类包括：

| 类别 | 示例 | 说明 |
|------|------|------|
| **kind/** | kind/bug, kind/feature | 类型 |
| **priority/** | priority/p0, priority/p1 | 优先级 |
| **severity/** | severity/s0, severity/s1 | 严重程度 |
| **area/** | area/ai, area/storage | 领域/模块 |
| **customer/** | customer/金盘 | **客户标签**，用于按客户筛选 |
| **其他** | ChatBI, bug, needs-triage | 自定义标签 |

---

## 二、按客户标签筛选

### 2.1 场景说明

当 Issue 标记了 `customer/金盘` 等客户标签时，可将该客户相关的 Issue 单独筛选出来分析。

**示例 Issue**：[matrixorigin/matrixflow#8059](https://github.com/matrixorigin/matrixflow/issues/8059)  
- Labels: `ChatBI`, `bug`, `customer/金盘`

### 2.2 SQL 查询示例

**注意**：MatrixOne 对 JSON 列直接比较可能报错，建议用 `CAST` 转成文本后再查询。

```sql
-- 方法1：使用 CAST 转文本后 LIKE 匹配（适用于 MatrixOne）
SELECT issue_number, title, CAST(labels AS CHAR) as labels, state, issue_type
FROM issues_snapshot
WHERE repo_owner = 'matrixorigin' AND repo_name = 'matrixflow'
AND snapshot_time = (SELECT MAX(snapshot_time) FROM issues_snapshot 
                     WHERE repo_owner = 'matrixorigin' AND repo_name = 'matrixflow')
AND CAST(labels AS CHAR) LIKE '%customer/金盘%';
```

```sql
-- 方法2：MySQL 5.7+ 可使用 JSON_CONTAINS
SELECT issue_number, title, labels, state, issue_type
FROM issues_snapshot
WHERE repo_owner = 'matrixorigin' AND repo_name = 'matrixflow'
AND snapshot_time = (SELECT MAX(snapshot_time) FROM issues_snapshot 
                     WHERE repo_owner = 'matrixorigin' AND repo_name = 'matrixflow')
AND JSON_CONTAINS(labels, '"customer/金盘"', '$');
```

### 2.3 Python 查询示例

```python
from config.config import get_database_url
from sqlalchemy import create_engine, text
import json

engine = create_engine(get_database_url())

# 获取最新快照中有某客户标签的 Issue
sql = text("""
    SELECT issue_number, title, CAST(labels AS CHAR) as labels, state
    FROM issues_snapshot
    WHERE repo_owner = :owner AND repo_name = :repo
    AND snapshot_time = :latest
    AND labels IS NOT NULL
""")

with engine.connect() as conn:
    latest = conn.execute(text(
        "SELECT MAX(snapshot_time) FROM issues_snapshot "
        "WHERE repo_owner = :owner AND repo_name = :repo"
    ), {"owner": "matrixorigin", "repo": "matrixflow"}).scalar()
    
    result = conn.execute(sql, {
        "owner": "matrixorigin", "repo": "matrixflow", "latest": latest
    })
    
    customer_label = "customer/金盘"
    for row in result:
        labels_str = row[2]
        if labels_str and customer_label in labels_str:
            labels = json.loads(labels_str) if isinstance(labels_str, str) else labels_str
            if customer_label in labels:
                print(f"Issue #{row[0]}: {row[1]} | {row[3]} | {labels}")
```

---

## 三、按任意标签筛选

### 3.1 查询包含某标签的所有 Issue

```python
def get_issues_by_label(repo_owner: str, repo_name: str, label: str) -> list:
    """按标签筛选 Issue"""
    engine = create_engine(get_database_url())
    sql = text("""
        SELECT issue_number, title, CAST(labels AS CHAR) as labels, state, issue_type
        FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo
        AND snapshot_time = :latest
        AND labels IS NOT NULL
        AND CAST(labels AS CHAR) LIKE :label_pattern
    """)
    
    with engine.connect() as conn:
        latest = conn.execute(text(
            "SELECT MAX(snapshot_time) FROM issues_snapshot "
            "WHERE repo_owner = :owner AND repo_name = :repo"
        ), {"owner": repo_owner, "repo": repo_name}).scalar()
        
        result = conn.execute(sql, {
            "owner": repo_owner, "repo": repo_name,
            "latest": latest,
            "label_pattern": f'%"{label}"%'  # JSON 数组中的格式
        })
        return list(result)
```

### 3.2 统计各标签的 Issue 数量

```python
def count_issues_by_labels(repo_owner: str, repo_name: str) -> dict:
    """统计每个 label 出现的 Issue 数量"""
    engine = create_engine(get_database_url())
    sql = text("""
        SELECT CAST(labels AS CHAR) as labels
        FROM issues_snapshot
        WHERE repo_owner = :owner AND repo_name = :repo
        AND snapshot_time = :latest
        AND labels IS NOT NULL
    """)
    
    label_counts = {}
    with engine.connect() as conn:
        latest = conn.execute(text(
            "SELECT MAX(snapshot_time) FROM issues_snapshot "
            "WHERE repo_owner = :owner AND repo_name = :repo"
        ), {"owner": repo_owner, "repo": repo_name}).scalar()
        
        result = conn.execute(sql, {"owner": repo_owner, "repo": repo_name, "latest": latest})
        for row in result:
            labels = json.loads(row[0]) if row[0] else []
            for label in labels:
                label_counts[label] = label_counts.get(label, 0) + 1
    
    return label_counts
```

---

## 四、实用脚本

项目根目录下的 `query_labels_sample.py` 可用于：

1. 查看有 labels 的 Issue 样例
2. 输出当前快照中所有不重复的 labels 列表

```bash
cd /Users/wupeng/Desktop/GitHub_Issue_智能管理系统
python3 query_labels_sample.py
```

如需查询 **matrixflow** 仓库，可修改脚本中的 `repo_name` 为 `matrixflow`。

---

## 五、注意事项

1. **MatrixOne**：对 JSON 列直接做 `!= ''` 等比较可能报错 `invalid input: json text`，建议用 `CAST(labels AS CHAR)` 转为文本后再操作。

2. **仓库差异**：matrixorigin/matrixone 与 matrixorigin/matrixflow 的标签体系不同，matrixflow 包含 `customer/xxx` 等客户标签。

3. **同步顺序**：需先同步对应仓库的数据，labels 才会入库。运行 `auto_run.py` 时指定 `--repo-name matrixflow` 可同步 matrixflow。

---

## 六、相关文档

- [后续优化计划](后续优化计划.md) - Tag 能力建设规划
- [使用教程](使用教程.md) - 系统完整使用说明
