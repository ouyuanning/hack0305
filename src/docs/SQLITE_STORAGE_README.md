# SQLite 存储使用说明

## 概述

由于 MatrixOne 数据库连接可能存在网络问题，系统已支持使用 **SQLite** 作为临时存储方案。SQLite 是 Python 内置的轻量级数据库，无需额外安装数据库服务器，非常适合本地开发和测试。

## 快速开始

### 1. 切换到 SQLite

在运行脚本前，设置环境变量：

```bash
export DATABASE_TYPE=sqlite
```

或者在 Python 代码中：

```python
import os
os.environ["DATABASE_TYPE"] = "sqlite"
```

### 2. 运行测试

#### 测试存储功能
```bash
python3 test_storage_sqlite.py
```

#### 测试 GitHub 数据拉取 + 存储
```bash
python3 test_github_to_storage.py [用户名] [仓库名]
# 示例
python3 test_github_to_storage.py microsoft vscode
```

#### 测试 GitHub API
```bash
python3 test_github_simple.py [用户名] [仓库名]
```

## 数据库文件位置

SQLite 数据库文件默认保存在：
```
data/github_issues.db
```

## 查看数据

### 使用 SQLite 命令行工具
```bash
sqlite3 data/github_issues.db

# 在 SQLite 命令行中：
.tables                    # 查看所有表
SELECT * FROM issues_snapshot LIMIT 5;  # 查看 Issues
SELECT * FROM comments LIMIT 5;         # 查看评论
SELECT * FROM issue_relations LIMIT 5; # 查看关联关系
.quit                     # 退出
```

### 使用 SQLite 浏览器工具

推荐使用以下工具查看数据：
- **DB Browser for SQLite** (免费，跨平台)
- **TablePlus** (macOS/Windows)
- **DBeaver** (免费，跨平台)

## 数据库表结构

### issues_snapshot (Issues 快照表)
- `id`: 主键
- `issue_id`: GitHub Issue ID
- `issue_number`: Issue 编号
- `repo_owner`: 仓库所有者
- `repo_name`: 仓库名称
- `title`: 标题
- `body`: 内容
- `state`: 状态 (open/closed)
- `labels`: 标签 (JSON 格式)
- `snapshot_time`: 快照时间
- ... 更多字段

### comments (评论表)
- `id`: 主键
- `comment_id`: GitHub Comment ID
- `issue_id`: 关联的 Issue ID
- `author`: 作者
- `body`: 评论内容
- `created_at`: 创建时间

### issue_relations (关联关系表)
- `id`: 主键
- `from_issue_id`: 源 Issue ID
- `to_issue_id`: 目标 Issue ID
- `relation_type`: 关系类型
- `relation_semantic`: 关系语义描述

## 注意事项

1. **JSON 字段序列化**: SQLite 不支持原生 JSON 类型，系统会自动将列表和字典序列化为 JSON 字符串存储。

2. **唯一约束**: 表已添加唯一约束，支持 `ON CONFLICT` 语法，可以自动更新重复数据。

3. **数据持久化**: SQLite 数据库文件保存在本地，删除文件会丢失所有数据。

4. **性能**: SQLite 适合中小规模数据，如果数据量很大（> 10万条），建议使用 PostgreSQL 或 MySQL。

## 切换回 MatrixOne

如果需要切换回 MatrixOne 或其他数据库：

```bash
export DATABASE_TYPE=matrixone  # 或其他: mysql, postgresql
```

或在 `config/config.py` 中修改 `DATABASE_TYPE` 变量。

## 测试结果

✅ 所有存储功能测试通过：
- ✅ 数据库连接
- ✅ Issue 数据保存
- ✅ 评论保存
- ✅ 关联关系保存
- ✅ 数据查询
- ✅ GitHub 数据拉取 + 存储完整流程

## 故障排除

如果遇到问题：

1. **数据库文件被锁定**: 确保没有其他程序正在使用数据库文件
2. **权限问题**: 确保 `data/` 目录有写入权限
3. **表不存在**: 删除 `data/github_issues.db` 文件，重新运行测试脚本会自动创建表

