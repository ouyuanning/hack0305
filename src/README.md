# GitHub Issue 智能管理系统

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

一个智能化的GitHub Issue管理系统，能够自动采集、分析和报告GitHub项目的Issue数据。

**本项目的两个主要仓库**：
- **matrixorigin/matrixone**：数据库内核，Issue 偏底层（storage、sql、performance 等）
- **matrixorigin/matrixflow**：应用/产品，Issue 含客户标签（`customer/金盘` 等）、ChatBI、问数等业务标签

## ✨ 主要功能

- 🔄 **自动采集**：从GitHub API自动获取所有Issue数据（包括评论和时间线）
- 🤖 **智能分析**：使用AI（OpenAI/Claude/通义千问）自动分类Issue类型、提取优先级和标签
- 💾 **数据存储**：支持多种数据库（SQLite/PostgreSQL/MySQL/MatrixOne）
- 📊 **报告生成**：自动生成日报、进度报告、多维度分析报告、可扩展分析报告
- 🔗 **关联分析**：自动识别Issue之间的关联关系（依赖、阻塞、相关等）

## 📁 项目结构概览与文档

新手可按下面结构快速找到入口和文档：

```
├── main.py / run.py / auto_run.py   # 入口（推荐用 auto_run.py 做定时）
├── config/config.py                  # 所有主要配置都在这一个文件
├── config/analysis_config.yaml       # 可扩展分析配置
├── modules/                          # 功能模块
│   ├── github_collector/             # GitHub 采集
│   ├── llm_parser/                   # AI 解析
│   ├── database_storage/             # 存库（含 MatrixOne）
│   ├── report_generator/              # 日报、进度报告
│   ├── analysis_extensible/         # 可扩展分析
│   ├── ai_analysis/                  # AI 驱动分析
│   └── email_sender/                 # 发邮件
├── scripts/                          # 补全、备份、检查等脚本 → 见 scripts/README.md
├── docs/                             # 文档
│   ├── 文件说明.md                    # 目录与文件一一说明
│   ├── 自动运行脚本说明.md            # auto_run 用法、定时、两仓
│   ├── 快速开始.md / 使用教程.md      # 上手与完整教程
│   └── matrixone/                    # MatrixOne 配置、备份、白名单
├── data/reports/                     # 报告输出
└── 临时/                             # 临时文件
```

**主要配置在哪里**：全部在 **`config/config.py`**。必改项：数据库（MatrixOne/MySQL/PostgreSQL/SQLite 选一）、`GITHUB_TOKEN`、AI 的 Key（如千问 `DASHSCOPE_API_KEY`）、发邮件（SMTP 地址/端口/账号、发件人、默认收件人 `DEFAULT_EMAIL_TO`）。端口等见该文件内注释。

更细的目录与文档对应见 [docs/文件说明.md](docs/文件说明.md)。

## 🚀 快速开始

### 1. 安装依赖

```bash
pip3 install -r requirements.txt
```

### 2. 配置环境变量

所有密钥和数据库连接信息通过 `.env` 文件管理，不要硬编码到代码中。

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入实际值：

| 变量 | 说明 | 必填 |
|------|------|------|
| `GITHUB_TOKEN` | GitHub Personal Access Token | ✅ |
| `DASHSCOPE_API_KEY` | 通义千问 API Key（推荐） | ✅（AI 功能） |
| `CLAUDE_API_KEY` | Claude API Key（可选替代） | 否 |
| `MATRIXONE_HOST` | MatrixOne 主机地址 | ✅（使用 MO 时） |
| `MATRIXONE_PORT` | MatrixOne 端口（默认 6001） | ✅（使用 MO 时） |
| `MATRIXONE_USER` | MatrixOne 用户名 | ✅（使用 MO 时） |
| `MATRIXONE_PASSWORD` | MatrixOne 密码 | ✅（使用 MO 时） |
| `SMTP_PASSWORD` | SMTP 邮箱授权码 | 否（发邮件时需要） |

> `.env` 文件已在 `.gitignore` 中，不会被提交到 Git。模板文件 `.env.example` 不含真实密钥，可安全提交。

`config/config.py` 会自动加载 `.env` 文件中的变量，也可以通过系统环境变量覆盖。

### 3. 配置系统

如需调整 AI 提供商、数据库类型等非密钥配置，编辑 `config/config.py`：

- **AI_PROVIDER**：`qwen`（默认）、`claude`、`openai`、`local`
- **DATABASE_TYPE**：`matrixone`（默认）、`sqlite`、`mysql`、`postgresql`
- **SMTP 发件人**等其他配置

### 3. 运行系统

**方式1：交互式运行（推荐新手）**

```bash
python3 run.py
```

或者：

```bash
python3 main.py
```

**方式2：自动运行脚本（推荐定时任务）**

使用可配置的自动运行脚本，支持配置文件、环境变量和命令行参数：

```bash
# 使用命令行参数
python3 auto_run.py --repo-owner matrixorigin --repo-name matrixone --email user@example.com

# 使用配置文件
python3 auto_run.py --config config.example.json

# 同步完成后自动补全关联关系
python3 auto_run.py --repo-owner matrixorigin --repo-name matrixone --supplement-relations

# 生成多维度分析报告 / 可扩展分析报告 / AI 驱动分析报告
python3 auto_run.py --repo-owner matrixorigin --repo-name matrixone --multi-report
python3 auto_run.py --repo-owner matrixorigin --repo-name matrixone --extensible-report --email user@example.com
# AI 驱动分析（项目推进+横向关联，适用 matrixflow 等含 customer 标签的仓库，结果写入邮件）
python3 auto_run.py --repo-owner matrixorigin --repo-name matrixflow --ai-report --email user@example.com
```

详细说明请参考：[自动运行脚本说明](docs/自动运行脚本说明.md)

**方式3：辅助脚本**（均在 `scripts/` 目录，需在项目根目录执行）

```bash
# 关联关系补全
python3 scripts/supplement_relations.py
python3 scripts/supplement_relations.py --repo-owner matrixorigin --repo-name matrixone --clear-first

# AI 解析补全
python3 scripts/repair_ai_parse.py --dry-run   # 先查看数量
python3 scripts/repair_ai_parse.py             # 执行补全

# 补全数据并生成完整分析报告
python3 scripts/run_full_repair_and_analysis.py

# 查询 labels 存储样例 / 可扩展分析
python3 scripts/query_labels_sample.py
python3 scripts/run_extensible_analysis.py --repo-owner matrixorigin --repo-name matrixone

# 一键补全并发送报告
./scripts/一键补全并发送报告.sh user@example.com
```

更多脚本说明见 [scripts/README.md](scripts/README.md)

## 📖 详细文档

- **[完整使用教程](docs/使用教程.md)** - 包含详细的安装、配置和使用说明
- **[Labels 标签使用说明](docs/Labels标签使用说明.md)** - 标签存储、按客户筛选、SQL/Python 查询示例
- **[完整分析报告说明](docs/完整分析报告_说明与执行指引.md)** - 多维度报告、可扩展分析报告的执行指引
- **[AI 分析拓展升级方案](docs/AI分析拓展升级优化方案-260224.md)** - AI 驱动分析、可扩展分析设计
- **[后续优化计划](docs/后续优化计划.md)** - 原计划与实际调整情况、关联关系补全脚本说明
- **[配置说明](docs/使用教程.md#配置说明)** - 所有配置项的详细说明
- **[常见问题](docs/使用教程.md#常见问题)** - 常见问题解答

## 🏗️ 系统架构

```
GitHub_Issue_智能管理系统/
├── config/                  # 配置文件
│   ├── config.py            # 主配置文件
│   └── analysis_config.yaml # 可扩展分析配置
├── modules/                 # 功能模块
│   ├── llm_parser/          # AI 智能分析
│   ├── database_storage/    # 数据库存储
│   ├── report_generator/    # 报告生成
│   ├── analysis_engine/     # 多维度分析
│   ├── analysis_extensible/ # 可扩展分析引擎（标签/模块/趋势等）
│   └── email_sender/        # 邮件发送
├── scripts/                 # 辅助脚本（补全、检查、诊断等）
├── docs/                    # 文档
│   └── matrixone/           # MatrixOne 配置与连接文档
├── data/                    # 数据目录
├── logs/                    # 日志目录
├── 临时/                    # 临时文件归档
├── main.py                  # 主程序入口
├── run.py                   # 快速运行
├── auto_run.py              # 自动运行（定时任务，推荐）
├── config.example.json      # 配置示例
├── create_tables.sql        # 建表 SQL
└── requirements.txt         # 依赖包
```

## 🔧 配置说明

### GitHub配置

```python
GITHUB_TOKEN = "ghp_xxxxxxxxxxxx"  # 你的GitHub Token
```

### AI配置

支持多种AI服务提供商：

- **OpenAI**：`AI_PROVIDER = "openai"`
- **Claude**：`AI_PROVIDER = "claude"`
- **通义千问（推荐）**：`AI_PROVIDER = "qwen"`
- **本地模型**：`AI_PROVIDER = "local"`（需要OpenAI兼容接口）

#### 通义千问配置（阿里云百炼）

**推荐使用环境变量配置**（更安全）：

```bash
# macOS/Linux (Zsh)
export DASHSCOPE_API_KEY="your_api_key_here"
echo "export DASHSCOPE_API_KEY='your_api_key_here'" >> ~/.zshrc
source ~/.zshrc

# macOS/Linux (Bash)
export DASHSCOPE_API_KEY="your_api_key_here"
echo "export DASHSCOPE_API_KEY='your_api_key_here'" >> ~/.bash_profile
source ~/.bash_profile
```

**获取API Key**：
1. 访问 [阿里云百炼控制台](https://bailian.console.aliyun.com/)
2. 前往密钥管理页面，创建API Key
3. 详细步骤请参考：[首次调用千问API](https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen#f0577378e8sz4)

**配置说明**：
- 系统优先使用 `DASHSCOPE_API_KEY` 环境变量（官方推荐）
- 也支持 `QWEN_API_KEY` 环境变量（向后兼容）
- API地址默认使用兼容模式：`https://dashscope.aliyuncs.com/compatible-mode/v1`
- 推荐模型：`qwen-plus` 或 `qwen-max-latest`

### 数据库配置

支持多种数据库：

- **SQLite**（推荐新手）：无需额外配置
- **PostgreSQL**：需要配置连接信息
- **MySQL**：需要配置连接信息
- **MatrixOne**：需要配置连接信息（已配置，可直接使用）

**MatrixOne 配置说明**：
- 主机地址：`freetier-01.cn-hangzhou.cluster.matrixonecloud.cn`
- 端口：`6001`
- 用户名格式：`实例ID:admin:accountadmin`
- 数据库：`github_issues`

详细配置请参考 [使用教程](docs/使用教程.md#配置说明) 和 [MatrixOne配置指南](docs/matrixone/MatrixOne配置指南.md)

## 📊 功能特性

### 1. 智能分类

系统使用AI自动分析每个Issue，识别：
- **类型**：bug、feature、task、question等
- **优先级**：P0（紧急）、P1（高）、P2（中）、P3（低）
- **标签**：自动提取相关标签
- **摘要**：生成简洁的摘要描述

### 2. 关联关系识别

自动识别Issue之间的关联关系：
- **依赖关系**：Issue A依赖Issue B
- **阻塞关系**：Issue A阻塞Issue B
- **相关关系**：Issue A与Issue B相关
- **重复关系**：Issue A与Issue B重复

### 3. 数据同步

- **增量同步**：只采集新增或更新的Issue（默认）
- **全量同步**：清空旧数据，重新采集所有Issue

### 4. 报告生成

自动生成多种报告：
- **日报**：每日Issue统计和分析
- **进度报告**：项目整体进度和趋势
- **多维度报告**：按客户、层级、共用 Feature 等维度分析（`--multi-report`）
- **可扩展分析报告**：标签、模块、趋势等，配置驱动，输出 JSON/Markdown/HTML；使用 `--extensible-report` 时邮件正文会包含综合分析（`--extensible-report` 或 `run_extensible_analysis.py`）

## 🛠️ 系统要求

- Python 3.8+
- GitHub Token（必须）
- AI API Key（OpenAI/Claude/通义千问，必须）
- 数据库（SQLite/PostgreSQL/MySQL/MatrixOne，可选，默认SQLite）

## 📝 使用示例

```bash
# 1. 运行系统
python3 run.py

# 2. 输入仓库信息
请输入仓库所有者（例如：octocat）: microsoft
请输入仓库名称（例如：Hello-World）: vscode

# 3. 选择同步模式
是否执行全量同步（清空旧数据）？(y/N): n

# 4. 等待处理完成
# 系统会自动：
# - 从GitHub获取Issues
# - 使用AI分析每个Issue
# - 保存到数据库
# - 提取关联关系

# 5. 生成报告
是否生成报告？(Y/n): y
```

## 🔍 模块说明

### GitHub采集模块

- 从GitHub API获取Issue数据
- 获取评论和时间线信息
- 提取Issue之间的关联关系

### LLM解析模块

- 使用AI分类Issue类型
- 提取优先级和标签
- 生成摘要和分析阻塞原因

### 数据库存储模块

- 保存Issue快照
- 保存评论和关联关系
- 支持全量重新运行

### 报告生成模块

- 生成日报和进度报告
- 统计各种指标
- 导出JSON格式报告

详细说明请参考 [使用教程 - 各模块说明](docs/使用教程.md#各模块说明)

## ❓ 常见问题

### Q: 配置验证失败怎么办？

A: 检查 `config/config.py` 中的GitHub Token和AI API Key是否正确设置。

### Q: 数据库连接失败怎么办？

A: 
- **SQLite**：检查 `data` 文件夹是否存在
- **PostgreSQL/MySQL**：确认数据库服务已启动，检查连接配置
- **MatrixOne**：
  - 运行 `python3 scripts/test_db_connection.py` 诊断连接问题
  - 检查 IP 白名单配置（参考 [IP白名单配置指南](docs/matrixone/IP白名单配置指南.md)）
  - 确认用户名格式正确（实例ID:admin:accountadmin）
  - 参考 [MatrixOne配置指南](docs/matrixone/MatrixOne配置指南.md)

### Q: AI调用错误怎么办？

A: 
- **通义千问**：
  - 检查 `DASHSCOPE_API_KEY` 环境变量是否正确设置
  - 获取API Key：访问 [阿里云百炼控制台](https://bailian.console.aliyun.com/) → 密钥管理
  - 参考文档：[首次调用千问API](https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen#f0577378e8sz4)
  - 确认账户有足够余额（免费额度用完后需要充值）
- **其他AI服务**：检查API Key是否正确、余额是否充足、网络是否正常
- 系统有回退机制，即使AI调用失败也能继续工作（使用基于规则的方法）

### Q: 如何重新采集所有数据？

A: 在配置文件中设置 `ENABLE_FULL_RESYNC = True`，或在运行时选择全量同步。

更多问题请参考 [常见问题](docs/使用教程.md#常见问题)

## 🧪 集成测试

集成测试脚本 `tests/test_integration.py` 会连接本地 MatrixOne，插入模拟数据后验证 WF-005（历史数据清洗）和 WF-006（客户标签同步）的完整流程。

### 前置条件

1. 本地 MatrixOne 已启动（通过 moi-core 或独立部署），可通过以下命令验证连接：

```bash
mysql -h 127.0.0.1 -P 6001 -udump -p111 --ssl-mode=DISABLED -e "SELECT 1"
```

2. 创建数据库并建表：

```bash
mysql -h 127.0.0.1 -P 6001 -udump -p111 --ssl-mode=DISABLED -e "CREATE DATABASE IF NOT EXISTS github_issues;"
mysql -h 127.0.0.1 -P 6001 -udump -p111 --ssl-mode=DISABLED github_issues < create_tables.sql
```

3. `.env` 中已配置本地 MO 连接信息（参考 `.env.example`）。

### 运行测试

```bash
# 在 src/ 目录下执行
python3 tests/test_integration.py
```

### 测试覆盖内容

- **WF-005 历史数据清洗**：load_issues → clean_data → ai_relabel（规则回退）→ validate_quality → save_to_experimental → run() 完整流程 → 幂等性 → 变更日志
- **WF-006 客户标签同步**：表创建 → sync_customer_issues → 数据验证（字段、severity 提取、URL）→ 幂等性 → 不存在标签返回 0

测试数据使用隔离的 `repo_owner=_test_integ`，测试结束后自动清理，不影响正式数据。

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📞 支持

如有问题，请查看：
1. [完整使用教程](docs/使用教程.md)
2. [常见问题](docs/使用教程.md#常见问题)
3. 检查配置和日志文件

---

**祝你使用愉快！** 🚀
