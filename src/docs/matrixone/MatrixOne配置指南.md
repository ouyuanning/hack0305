# MatrixOne 配置指南

## ✅ 当前配置状态

**所有配置已完成，可以直接使用！**

当前配置信息：
- **主机地址**：`freetier-01.cn-hangzhou.cluster.matrixonecloud.cn`
- **端口**：`6001`
- **用户名**：`019c3caf-ae5a-7ced-ac5b-37d070f153f5:admin:accountadmin`（格式：实例ID:admin:accountadmin）
- **密码**：`Adminadmin1`
- **数据库**：`github_issues`

---

## 🔗 连接串格式

MatrixOne 使用 MySQL 协议，连接串格式如下：

```
mysql+pymysql://用户名:密码@主机地址:端口/数据库名
```

**重要**：用户名和密码中的特殊字符（如 `:`、`@`）会自动进行 URL 编码处理。

**当前连接串**（已自动生成）：
```
mysql+pymysql://019c3caf-ae5a-7ced-ac5b-37d070f153f5%3Aadmin%3Aaccountadmin:Adminadmin1@freetier-01.cn-hangzhou.cluster.matrixonecloud.cn:6001/github_issues
```

---

## 📋 配置文件位置

配置文件位于：`config/config.py`

**当前配置（第 69-76 行）**：

```python
# MatrixOne 配置
# 使用控制台提供的连接地址：freetier-01.cn-hangzhou.cluster.matrixonecloud.cn
MATRIXONE_HOST = os.getenv("MATRIXONE_HOST", "freetier-01.cn-hangzhou.cluster.matrixonecloud.cn")
MATRIXONE_PORT = os.getenv("MATRIXONE_PORT", "6001")
# 用户名格式：实例ID:admin:accountadmin
MATRIXONE_USER = os.getenv("MATRIXONE_USER", "019c3caf-ae5a-7ced-ac5b-37d070f153f5:admin:accountadmin")
MATRIXONE_PASSWORD = os.getenv("MATRIXONE_PASSWORD", "Adminadmin1")
MATRIXONE_DATABASE = os.getenv("MATRIXONE_DATABASE", "github_issues")
```

---

## 🔧 配置说明

### 1. MATRIXONE_HOST - 主机地址

- **含义**：MatrixOne 数据库服务器的主机名
- **当前值**：`freetier-01.cn-hangzhou.cluster.matrixonecloud.cn`
- **获取方式**：从 MatrixOne 控制台的连接信息中获取

### 2. MATRIXONE_PORT - 端口号

- **含义**：数据库服务端口
- **当前值**：`6001`（MatrixOne 默认端口）
- **说明**：通常不需要修改

### 3. MATRIXONE_USER - 用户名

- **含义**：连接数据库的用户名
- **格式**：`实例ID:admin:accountadmin`
- **当前值**：`019c3caf-ae5a-7ced-ac5b-37d070f153f5:admin:accountadmin`
- **说明**：
  - 第一部分是实例ID（从控制台获取）
  - 第二部分是 `admin`（固定）
  - 第三部分是 `accountadmin`（固定）

### 4. MATRIXONE_PASSWORD - 密码

- **含义**：连接数据库的密码
- **当前值**：`Adminadmin1`
- **说明**：创建实例时设置的密码

### 5. MATRIXONE_DATABASE - 数据库名

- **含义**：要连接的数据库名称
- **当前值**：`github_issues`
- **说明**：如果数据库不存在，系统会自动创建

---

## 🧪 测试连接

### 方法 1：运行简单连接测试（推荐）✅

```bash
cd ~/Desktop/GitHub_Issue_智能管理系统
python3 test_mo_connection_simple.py
```

这会执行 4 项测试：
1. DNS 解析
2. 端口连接
3. 数据库连接
4. SQLAlchemy 连接

**预期结果**：所有测试通过 ✅

### 方法 2：运行配置检查

```bash
cd ~/Desktop/GitHub_Issue_智能管理系统
python3 scripts/check_config.py
```

这会检查所有配置项，包括数据库连接。

### 方法 3：运行完整连接测试

```bash
cd ~/Desktop/GitHub_Issue_智能管理系统
python3 test_matrixone_connection.py
```

这会执行 10 项全面测试，包括 CRUD 操作、事务等。

---

## ⚠️ 重要提示

### 1. 用户名格式

MatrixOne 的用户名格式为：`实例ID:admin:accountadmin`

- 实例ID 可以从控制台获取
- 用户名中的冒号（`:`）会自动进行 URL 编码（`%3A`）
- 配置文件中已经正确处理了 URL 编码

### 2. URL 编码

系统会自动处理用户名和密码中的特殊字符：
- `:` → `%3A`
- `@` → `%40`
- `/` → `%2F`

这些都在 `config/config.py` 的 `get_database_url()` 函数中自动处理。

### 3. IP 白名单

如果连接失败，可能需要：
1. 登录 MatrixOne 控制台
2. 将你的 IP 地址添加到白名单
3. 参考 [IP白名单配置指南.md](IP白名单配置指南.md)

### 4. 数据库创建

如果数据库 `github_issues` 不存在：
- 系统会在首次运行时自动创建
- 或者手动在 SQL 编辑器中执行：`CREATE DATABASE github_issues;`

---

## 📝 配置检查清单

修改配置后，请确认：

- [x] `MATRIXONE_HOST` - 已设置为正确的主机地址
- [x] `MATRIXONE_PORT` - 已设置为 `6001`
- [x] `MATRIXONE_USER` - 已设置为正确的用户名格式（实例ID:admin:accountadmin）
- [x] `MATRIXONE_PASSWORD` - 已设置为正确的密码
- [x] `MATRIXONE_DATABASE` - 已设置为 `github_issues`
- [x] 连接测试通过

---

## 🚀 快速开始

### 第一步：确认配置

打开 `config/config.py`，确认 MatrixOne 配置部分（第 69-76 行）已正确设置。

### 第二步：测试连接

```bash
cd ~/Desktop/GitHub_Issue_智能管理系统
python3 test_mo_connection_simple.py
```

如果所有测试通过，就可以开始使用了！

### 第三步：运行系统

```bash
python3 run.py
```

---

## 🔍 常见问题

### Q1: 连接失败，提示 "nodename nor servname provided, or not known"

**原因**：DNS 解析失败或网络问题

**解决方案**：
1. 检查网络连接
2. 确认主机地址正确
3. 检查 IP 白名单配置

### Q2: 连接失败，提示 "Access denied"

**原因**：用户名或密码错误

**解决方案**：
1. 检查用户名格式是否正确（实例ID:admin:accountadmin）
2. 检查密码是否正确
3. 确认实例ID是否正确

### Q3: 连接失败，提示 "Unknown database"

**原因**：数据库不存在

**解决方案**：
1. 在 MatrixOne SQL 编辑器中创建数据库：`CREATE DATABASE github_issues;`
2. 或让系统自动创建（首次运行时会自动创建）

### Q4: 如何获取实例ID？

**方法**：
1. 登录 MatrixOne 控制台
2. 查看实例列表，实例ID通常显示在实例名称旁边
3. 或者在连接信息中查看

---

## 📚 相关文档

- [MatrixOne连接测试使用说明.md](MatrixOne连接测试使用说明.md) - 详细测试说明
- [IP白名单配置指南.md](IP白名单配置指南.md) - IP白名单配置
- [MatrixOne备份与恢复.md](MatrixOne备份与恢复.md) - **备份与恢复要点**（SQL 快照、定时备份、误删恢复）
- [README.md](README.md) - 项目总览

---

**最后更新**：2025-02-21

**配置状态**：✅ 已完成，可直接使用
