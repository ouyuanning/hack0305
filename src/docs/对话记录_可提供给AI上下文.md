# 对话记录 - 提供给 AI 的上下文

**用途**：下次开启新对话时，可将此文件内容发给 AI，以便延续上下文。

---

## 近期对话概要（2026-02-25 / 2026-03-01）

1. **浏览器监听模块 - 混合方案（4 层智能检测）**
   - **问题**：原方案依赖 Chrome CDP 调试模式，用户需以 `--remote-debugging-port=9222` 启动 Chrome，对普通用户不可行。
   - **方案**：4 层智能检测，自动降级：① Chrome CDP（9222）→ ② 系统窗口标题（macOS/Windows）→ ③ 剪贴板（Issue URL）→ ④ 手动输入。
   - **实现**：新增 `utils/browser_context_smart.py`、`cdp_detector.py`、`window_detector.py`、`clipboard_detector.py`、`manual_input.py`；`browser_context.py` 改为调用智能检测；`ai_issue_generator._get_browser_issue_context` 不再检查 environment 配置。
   - **测试结果**：剪贴板策略（复制 Issue URL）通过；CDP 需 Chrome 调试模式；窗口需 pyobjc（macOS）或 pywin32（Windows）；手动输入需交互式 TTY。
   - **监控原理**：CDP 是「被动查询」，可后触发（提 Issue 时再调用），会返回当时所有 tabs；但 Chrome 必须在启动时带调试端口，不能在运行中再开启。
   - **内容获取**：Issue 详情（标题、标签、正文）来自 **GitHub API**，不是解析网页 HTML；先识别 Issue URL/编号，再调 API 拉取。
   - **范围限制**：**仅识别 GitHub Issue**；非 GitHub 网页（URL、标题、内容）不会被获取或处理，设计上不收集用户其他浏览信息。

2. **自动写 Issue 与 AI 看板（独立功能模块）**
   - **位置**：在 `feature_issue_and_kanban/` 下独立开发，不直接改主项目；测试通过后再合并。
   - **云端友好架构升级**（2026-02-28）：`core/environment.py` 环境检测、`core/config_manager.py` 配置管理、分层依赖 `requirements/`、重复检测 `duplicate_detector.py`、统一接口 `services/unified_interface.py`（Cursor/企微共用），Dockerfile、setup_dependencies.py。
   - **功能 1 - 自动写 Issue**：聊天窗口收集信息（标题、正文、类型、层级、标签、负责人）→ 按类型带出正文模板（Doc Request、User Bug、MOI Feature 等）→ 生成本地预览页（GitHub 风格，含 Labels/Type/层级/里程碑）→ 用户确认后调用 GitHub API 创建；支持单条与批量（批量输出 Excel 链接表）。
   - **功能 2 - 项目看板**：按项目标签（如 `project/问数深化`）从 `project_issues` 或回退从 `issues_snapshot` 聚合；生成与「项目计划-甘特图 v3」同风格的看板 HTML（顶栏渐变、任务表、状态徽章、风险评估卡片）；支持 `--demo` 假数据演示。
   - **脚本与入口**：`generate_preview_only.py`（纯预览，不依赖 DB/AI）、`create_issue_interactive.py`（单轮/交互/直接 --title --body --type）、`batch_create_issues.py`（批量创建 + Excel）、`generate_daily_dashboard.py`（看板，支持 --demo、--output-html）。
   - **模板**：`feature_issue_and_kanban/templates/*.md` 各类型正文模板（Doc_Request、User_Bug、MOI_Feature 等），选类型时自动带出。
   - **聊天流程**：在 Cursor 聊天中说「我要建一个 Issue：…」→ AI 询问标题/正文/类型/负责人等 → 信息齐后执行生成预览 → 打开浏览器 → 用户说修改或「确认无误」→ AI 执行创建并返回链接。详见 `feature_issue_and_kanban/docs/聊天流程-创建Issue与预览.md`。

2. **AI 驱动分析多仓库邮件**：用户要求 AI 驱动分析同时覆盖 matrixone 和 matrixflow，且邮件中**优先展示 matrixflow**（用户更关注 matrixflow）。
2. **实施**：`auto_run.py` 步骤 2.7 使用 `--ai-report` 时，依次分析 matrixflow、matrixone，将结果写入 `ai_analysis_report`（结构：`by_repo` + `order`）；`email_sender.format_ai_analysis_section()` 改为支持多仓库，按 `order` 遍历，每个仓库单独展示项目推进与横向关联，matrixflow 排在前。
3. **文档更新**：将上述变更同步到自动运行脚本说明、AI分析拓展升级优化方案、完整分析报告说明、对话记录。
4. **产品需求文档 PRD**：根据治理指南与可行性评价报告，在 Download 输出产品方案 PRD（非开发方案）；用户要求做成 Word 并追加「项目代码功能对应说明」→ 新增 `scripts/generate_prd_docx.py`，生成 `GitHub_Issue智能管理系统_产品需求文档PRD-V1-260224.docx`；用户反馈文档太复杂 → 简化为五章：产品是什么、解决什么问题、主要功能、怎么用、功能与代码对应，脚本已改为输出简化版。
5. **单独做分析命令行**：用户需测试分析和发邮件，已给出一条命令（`--skip-sync --extensible-report --ai-report --email`）。

---

## 一、项目背景

- **项目路径**：`/Users/wupeng/Desktop/GitHub_Issue_智能管理系统`
- **产品方案**：`/Users/wupeng/Downloads/GitHub_Issue智能管理系统_完整产品方案_Final.md`
- **功能**：从 GitHub 采集 Issue、AI 解析、存库、生成日报/进度报告、邮件推送；**独立模块**：自动写 Issue（聊天流程 + 预览 + API 创建）、项目看板（甘特图风格 HTML，支持 demo）。
- **数据库**：优先使用 MatrixOne；MatrixOne 需将本机公网 IP 加入白名单。看板/知识库用表：`project_issues`、`issue_knowledge_base`、`conversation_sessions`（见 `feature_issue_and_kanban/scripts/create_new_tables.sql`）。

### 支持的仓库说明

| 仓库 | 定位 | 说明 |
|------|------|------|
| **matrixorigin/matrixone** | 数据库内核 | MatrixOne 云原生数据库，Issue 偏底层：storage、sql、optimizer、performance 等 |
| **matrixorigin/matrixflow** | 应用/产品 | 基于 MatrixOne 的上层应用，Issue 偏业务：ChatBI、问数、数据总览、账户管理；含 `customer/金盘` 等客户标签 |

- 两个仓库**分别同步**，一次 `auto_run` 只同步一个仓库
- 客户标签（`customer/xxx`）主要在 matrixflow 使用

---

## 二、已完成的优化与修复

### 1. 分页问题（只拉 62 条 Issue）
- **原因**：GitHub API 每页混有 Issue 和 PR，过滤 PR 后数量变小，误判为最后一页
- **修改**：`modules/github_collector/github_api.py` 中 `fetch_issues` 返回 `(issues, raw_count)`，`main.py` 用 `raw_count` 判断是否继续分页

### 2. 全量同步清空逻辑
- **原因**：`clear_all_data()` 依赖 `ENABLE_FULL_RESYNC`，传入 `--full-sync` 也不清空
- **修改**：增加 `force` 参数，命令行 `--full-sync` 时调用 `clear_all_data(force=True)`

### 3. 关联关系顺序导致丢失
- **原因**：处理 Issue A 引用 B 时，B 尚未入库，导致「无法找到 Issue #xxx 的 ID」
- **修改**：拆成 Phase 1（采集、解析、存储）+ Phase 2（统一提取并保存关联）

### 4. 关联关系补全脚本
- **新增**：`supplement_relations.py`，从已入库数据重新提取并保存关联
- **接入**：`auto_run.py` 支持 `--supplement-relations`，同步完成后可选执行补全

### 5. Labels 使用说明
- **文档**：`docs/Labels标签使用说明.md`
- **示例**：`query_labels_sample.py`（MatrixOne 用 `CAST(labels AS CHAR)` 避免 JSON 解析问题）

### 6. 代码优化方案 1-0222 集成
- **来源**：`/Users/wupeng/Downloads/代码优化方案1-0222.zip`
- **内容**：多维度分析引擎、改进的报告生成器
- **问题**：`issue_relations` 表无 `repo_owner`、`repo_name` 列，原 SQL 会报错
- **修复**：在 `multi_dimensional_analyzer.py` 中新增 `_get_repo_relations()`，通过 JOIN `issues_snapshot` 按仓库过滤
- **集成**：
  - `modules/analysis_engine/`：多维度分析引擎
  - `modules/report_generator/improved_report_gen.py`：改进报告生成，输出到 `data/reports/`
  - `auto_run.py` 增加 `--multi-report` 参数

### 7. 可扩展分析模块升级 - 260223
- **来源**：`Download/分析模块升级逻辑-260223.zip`
- **内容**：配置驱动的可扩展分析框架，支持 7 类分析器与多格式输出
- **新增**：
  - `modules/analysis_extensible/`：可扩展分析框架
  - `config/analysis_config.yaml`：分析配置（启用分析器、输出格式）
  - `run_extensible_analysis.py`：独立运行入口
- **分析器**：基础统计、标签分析、模块分析、层级分析、客户分析、关联分析、趋势分析
- **输出格式**：JSON、Markdown、HTML（由 config 控制）
- **集成**：`auto_run.py` 增加 `--extensible-report` 参数，支持配置文件 `extensible_report: true`

### 8. 邮件未发送问题修复 - 260223
- **来源**：`/Users/wupeng/Downloads/邮件未发送问题修复-260223.zip`（内含 `完整修复指南.md`、修复版代码片段）
- **问题**：多维度报告 SQL 子查询（MatrixOne 20102）、关联保存 Duplicate 1062、流程中断导致邮件未发送
- **修复**（已全部应用至项目）：
  1. **SQL 兼容**：`multi_dimensional_analyzer.py` 新增 `_get_latest_snapshot_time()`，所有子查询改为先查 latest_time 再传入，避免 JOIN/WHERE 中的子查询
  2. **Duplicate 处理**：`mo_client.py` 的 `save_relations` 改为先查后插/更新，避免 ON DUPLICATE KEY UPDATE 在 MatrixOne 中行为不一致
  3. **流程健壮性**：`auto_run.py` 步骤 2.5 多维度报告用 try-except 包裹，失败时继续执行步骤 3 发邮件

### 9. 可扩展分析邮件集成 - 260224
- **来源**：`/Users/wupeng/Downloads/files.zip`（内含《可扩展分析集成诊断与修复.md》、`test_analysis.py`）
- **问题**：可扩展分析生成报告保存到 `data/reports/`，但邮件正文仍只显示日报/进度基础统计
- **修复**（已全部应用至项目）：
  1. **test_analysis.py**：新增可扩展分析诊断脚本（5 步：模块导入、配置文件、数据库连接、分析器模块、完整分析），运行 `python3 test_analysis.py` 可验证可扩展分析是否正常
  2. **auto_run.py**：`ext_engine.run()` 返回值赋给 `comprehensive_report`，调用 `send_report()` 时传入
  3. **email_sender.py**：新增 `format_comprehensive_report_html()`，`send_report()` 支持 `comprehensive_report` 参数；当存在可扩展分析结果时，邮件正文展示标签分析、模块分析、客户分析、基础统计等
- **效果**：使用 `--extensible-report` 运行并发送邮件时，邮件正文包含综合分析内容（不再仅有基础统计）

### 10. 大模型洞察分析 - 260224
- **需求**：在规则分析完成后，调用大模型对当前数据做自然语言解读与建议
- **实施**：
  1. **llm_insights.py**：基于规则分析结果（basic_stats、label、module、customer 等）构建摘要，调用现有 LLM（千问/Claude 等）生成洞察与建议
  2. **analysis_engine.py**：在 7 个规则分析器之后增加 LLM 洞察步骤（由 `llm_insights.enabled` 控制）
  3. **analysis_config.yaml**：`llm_insights.enabled: true`，`max_summary_chars: 4000`
  4. **输出**：邮件正文、Markdown、JSON 均包含「大模型洞察与建议」；失败时不影响其他输出
- **脚本与邮件**：`run_extensible_analysis.py` 只生成报告不发邮件；发邮件用 `auto_run.py --extensible-report`，不写 `--email` 时用默认收件人

### 11. AI 驱动分析多仓库邮件集成 - 260224

- **需求**：AI 驱动分析同时覆盖 matrixone 和 matrixflow，邮件中**优先展示 matrixflow**
- **实施**：
  1. **auto_run.py**：`--ai-report` 时，步骤 2.7 依次分析 `matrixorigin/matrixflow`、`matrixorigin/matrixone`，结果写入 `ai_analysis_report`，结构为 `{"by_repo": {repo_key: {project_progress, cross_patterns}}, "order": ["matrixorigin/matrixflow", "matrixorigin/matrixone"]}`
  2. **email_sender.py**：`format_ai_analysis_section()` 支持多仓库，按 `order` 遍历，每个仓库用 `<h2>📦 仓库：{repo_key}</h2>` 作为标题，展示项目推进与横向关联
- **效果**：使用 `--ai-report` 发送邮件时，正文会先展示 matrixflow 的 AI 分析，再展示 matrixone

### 12. 产品需求文档 PRD 与 Word 输出 - 260224

- **需求**：在 Download 输出产品方案 PRD（给他人看项目代码），参考治理指南、可行性评价报告；要求为产品 PRD 非开发方案。
- **实施**：
  1. 先输出 Markdown 版 PRD（`Downloads/GitHub_Issue智能管理系统_产品需求文档PRD-V1-260224.md`），后用户要求 Word 且追加「项目代码功能对应说明」。
  2. 新增 `scripts/generate_prd_docx.py`（依赖 python-docx），生成 `Downloads/GitHub_Issue智能管理系统_产品需求文档PRD-V1-260224.docx`，内含功能与代码对应表、主要入口与命令、目录与配置说明。
  3. 用户反馈文档太复杂 → 脚本改为输出**简化版**：五章（产品是什么、解决什么问题、主要功能、怎么用、功能与代码对应），去掉长治理规范、多角色场景、非功能需求、验收表、成本等。
- **单独做分析发邮件**：测试用命令 `python3 auto_run.py --repo-owner matrixorigin --repo-name matrixflow --skip-sync --extensible-report --ai-report --email 收件人`。

---

## 三、关键文件路径

| 文件 | 说明 |
|------|------|
| `main.py` | 主流程，含 Phase 1 + Phase 2 |
| `auto_run.py` | 自动运行，支持 `--full-sync`、`--supplement-relations`、`--multi-report`、`--extensible-report`、`--ai-report` |
| `supplement_relations.py` | 关联关系补全 |
| `sync_missing_issues.py` | 临时脚本：从运行反馈 docx 提取缺失 Issue 编号并同步入库（用完可删） |
| `modules/github_collector/github_api.py` | 采集逻辑，含分页修复 |
| `modules/database_storage/mo_client.py` | 存储 |
| `modules/analysis_engine/multi_dimensional_analyzer.py` | 多维度分析 |
| `modules/report_generator/improved_report_gen.py` | 多维度报告生成 |
| `modules/analysis_extensible/analysis_engine.py` | 可扩展分析引擎 |
| `modules/analysis_extensible/llm_insights.py` | 大模型洞察分析（基于规则分析结果调用 LLM） |
| `config/analysis_config.yaml` | 可扩展分析配置（含 llm_insights.enabled） |
| `run_extensible_analysis.py` | 可扩展分析独立运行入口 |
| `test_analysis.py` | 可扩展分析诊断脚本（5 步测试，验证分析是否正常） |
| `config/config.py` | 配置（含 163 邮箱、REPORT_OUTPUT_DIR 等） |
| `docs/后续优化计划.md` | 优化计划 |
| `docs/Labels标签使用说明.md` | Labels 使用说明 |
| `docs/代码优化方案1-0222_检查报告.md` | 优化方案检查与集成说明 |
| `docs/完整分析报告_说明与执行指引.md` | 报告执行指引与输出路径 |
| `docs/自动运行脚本说明.md` | auto_run 参数与示例 |
| `feature_issue_and_kanban/README.md` | 自动写 Issue + 看板 独立模块说明 |
| `feature_issue_and_kanban/scripts/generate_preview_only.py` | 纯预览（按类型带模板，不依赖 DB/AI） |
| `feature_issue_and_kanban/scripts/create_issue_interactive.py` | 单轮/交互/直接创建 Issue |
| `feature_issue_and_kanban/scripts/generate_daily_dashboard.py` | 每日看板（支持 --demo、--output-html 甘特图风格） |
| `feature_issue_and_kanban/utils/browser_context_smart.py` | 监听模块混合方案（4 层智能检测入口） |
| `feature_issue_and_kanban/utils/browser_context.py` | 监听模块接口（向后兼容） |
| `feature_issue_and_kanban/docs/聊天流程-创建Issue与预览.md` | 聊天窗口流程说明 |
| `feature_issue_and_kanban/docs/监听模块使用说明.md` | 监听模块（混合方案、4 层检测、测试结果、范围限制） |

---

## 四、常用命令

```bash
# 完整流程
python3 auto_run.py --repo-owner matrixorigin --repo-name matrixflow --email xxx@example.com

# 全量同步
python3 auto_run.py --repo-owner matrixorigin --repo-name matrixflow --full-sync

# 同步后补全关联
python3 auto_run.py --repo-owner matrixorigin --repo-name matrixflow --supplement-relations

# 生成多维度报告
python3 auto_run.py --repo-owner matrixorigin --repo-name matrixflow --multi-report

# 生成可扩展分析报告并发送邮件（含大模型洞察；不写 --email 时用默认收件人）
python3 auto_run.py --repo-owner matrixorigin --repo-name matrixflow --skip-sync --extensible-report

# AI 驱动分析（分析 matrixone + matrixflow，邮件中 matrixflow 优先）
python3 auto_run.py --repo-owner matrixorigin --repo-name matrixflow --skip-sync --ai-report

# 可扩展分析诊断测试
python3 test_analysis.py

# 单独运行可扩展分析
python3 run_extensible_analysis.py --repo-owner matrixorigin --repo-name matrixone

# 单独运行多维度报告
python3 -m modules.report_generator.improved_report_gen

# 单独运行现有分析并发邮件（不同步，用配置里默认收件人，可从任意目录执行）
cd /Users/wupeng/Desktop/GitHub_Issue_智能管理系统 && python3 auto_run.py --repo-owner matrixorigin --repo-name matrixone --skip-sync --email wupeng@matrixorigin.cn

# --- 自动写 Issue 与看板（需在项目根目录执行）---
# 生成 Issue 预览页（按类型带正文模板）
python3 feature_issue_and_kanban/scripts/generate_preview_only.py --repo matrixorigin/matrixflow --title "标题" --type "Doc Request" --assignees "wupeng" --output-html feature_issue_and_kanban/preview.html --success-msg
# 直接创建 Issue（不预览）
python3 feature_issue_and_kanban/scripts/create_issue_interactive.py --repo matrixorigin/matrixflow --title "标题" --body "正文" --assignees "wupeng"
# 看板演示（假数据，甘特图风格 HTML）
python3 feature_issue_and_kanban/scripts/generate_daily_dashboard.py --project-tag "project/问数深化" --demo --output-html feature_issue_and_kanban/dashboard_demo.html
```

---

## 五、客户标签

- 格式：`customer/金盘`、`customer/软通` 等
- 主要在 `matrixorigin/matrixflow` 仓库使用

## 六、邮件与默认收件人

- **默认收件人**：`config/config.py` 中 `DEFAULT_EMAIL_TO`（如 `wupeng@matrixorigin.cn`），未传 `--email` 时使用
- **邮件发送**：步骤 2.5 多维度报告失败不会阻断步骤 3，基础报告（daily/progress）仍会随邮件发送
- **可扩展分析邮件**：使用 `--extensible-report` 时，若可扩展分析成功，邮件正文会包含综合分析（标签、模块、客户、基础统计、大模型洞察）；否则使用基础报告格式
- **run_extensible_analysis 与 auto_run**：`run_extensible_analysis.py` 只生成报告（JSON/Markdown），不发邮件；发邮件需用 `auto_run.py --extensible-report`
- **AI 驱动分析邮件**：使用 `--ai-report` 时，会同时分析 matrixone 和 matrixflow，项目推进+横向关联写入邮件正文，**matrixflow 排在 matrixone 前面**

---

## 七、2026-02-23 运行记录与补全

### 运行记录问题与补全
- **来源**：Download/20260223脚本运行记录.docx、Download/运行反馈.docx（matrixorigin/matrixone，约 8849 Issue）
- **问题**：① 关联因顺序跳过（无法找到 Issue #xxx 的 ID）② 保存关联时 Duplicate 1062 ③ 多维度报告 SQL 子查询 20102 ④ 流程中断导致邮件未发送
- **脚本**：
  - `supplement_relations.py`：关联补全（已优化为先查后插/更新，减少 1062）
  - `repair_ai_parse.py`：AI 解析补全
  - `run_full_repair_and_analysis.py`：一键补全 + 报告
- **文档**：`docs/20260223运行记录_问题分析与补全方案.md`

---

## 八、常用任务与命令

### 任务 1：检查并补全关联失败的 Issue
- **脚本**：`supplement_relations.py`、`sync_missing_issues.py`（临时）
- **说明**：`supplement_relations.py` 从已入库数据重新提取关联并保存。若运行反馈中有大量「无法找到 Issue #xxx 的 ID」，说明这些 Issue 未入库，可先用 **临时脚本** `sync_missing_issues.py` 从运行反馈 docx 提取缺失编号，从 GitHub 拉取并入库，再运行 `supplement_relations.py` 补全关联。信息同步好后可删除 `sync_missing_issues.py`。
- **执行**（需本地网络可达 MatrixOne）：
  ```bash
  # 若运行反馈有大量「无法找到 Issue #xxx 的 ID」，先同步缺失 Issue（临时脚本）
  python3 sync_missing_issues.py
  # 再补全关联
  python3 supplement_relations.py --repo-owner matrixorigin --repo-name matrixone
  ```

### 任务 2：整体分析并发送报告邮件
- **只跑现有分析并发邮件**（不同步、不补全，用配置默认收件人，可从任意目录执行）：
  ```bash
  cd /Users/wupeng/Desktop/GitHub_Issue_智能管理系统 && python3 auto_run.py --repo-owner matrixorigin --repo-name matrixone --skip-sync --email wupeng@matrixorigin.cn
  ```
  不写 `--email` 时使用 `config/config.py` 中 `DEFAULT_EMAIL_TO`。
- **可扩展分析发邮件**（邮件正文含标签、模块、客户、大模型洞察；不写 --email 用默认收件人）：
  ```bash
  python3 auto_run.py --repo-owner matrixorigin --repo-name matrixone --skip-sync --extensible-report
  ```
  可先运行 `python3 test_analysis.py` 验证可扩展分析是否正常。
- **AI 驱动分析发邮件**（分析 matrixone + matrixflow，邮件中 matrixflow 优先）：
  ```bash
  python3 auto_run.py --repo-owner matrixorigin --repo-name matrixflow --skip-sync --ai-report
  ```
- **一键执行**（关联补全 + 多维度报告 + 邮件）：
  ```bash
  ./一键补全并发送报告.sh wupeng@matrixorigin.cn
  # 或（不指定 --email 时使用 config 中 DEFAULT_EMAIL_TO）
  cd /Users/wupeng/Desktop/GitHub_Issue_智能管理系统 && python3 auto_run.py --repo-owner matrixorigin --repo-name matrixone \
    --skip-sync --supplement-relations --multi-report
  ```
- **分步执行**：
  ```bash
  python3 supplement_relations.py --repo-owner matrixorigin --repo-name matrixone
  python3 run_full_repair_and_analysis.py --repo-owner matrixorigin --repo-name matrixone --skip-ai-repair --email 收件人@example.com
  ```

---

## 九、文档更新记录

| 日期       | 更新内容 |
|------------|----------|
| 2026-02-23 | 新增「近期对话概要」；补充邮件未发送修复与运行反馈来源（§7）；合并运行记录与任务为 §7、§8；新增 §6 邮件与默认收件人、§9 文档更新记录；同步更新《自动运行脚本说明》《完整分析报告_说明与执行指引》 |
| 2026-02-23 | 近期对话：可扩展分析写入多份项目文档；补充「单独运行分析并发邮件」带 cd 的完整命令。文档同步：README（可扩展分析、run_extensible_analysis、架构与报告说明）、docs/自动运行脚本说明（--extensible-report、示例 7b、配置项）、docs/完整分析报告_说明与执行指引（可扩展分析命令与输出）、docs/快速开始（下一步链接）、docs/使用教程（主要功能、模块5 可扩展分析、Q8 报告路径）、项目清理和自动运行脚本说明（运行选项与保留脚本）、文件说明（主程序与 analysis_extensible）。§四 常用命令、§八 任务2 增加「单独运行分析发邮件」一行命令。 |
| 2026-02-24 | 近期对话：files.zip 修改意见实施（可扩展分析集成到邮件正文）。新增 §9 可扩展分析邮件集成 - 260224；§三 关键文件路径增加 test_analysis.py；§四 常用命令增加可扩展分析邮件命令、test_analysis.py；§六 邮件与默认收件人补充可扩展分析邮件说明。文档同步：自动运行脚本说明、完整分析报告说明、文件说明、README、使用教程、项目清理说明。 |
| 2026-02-24 | 近期对话：run_extensible_analysis 只生成报告不发邮件、需用 auto_run --extensible-report；可扩展分析为规则分析非 AI；新增大模型洞察环节（llm_insights.py）；默认收件人可不写 --email。新增 §10 大模型洞察分析 - 260224；§三 增加 llm_insights.py；§四 §六 §八 补充大模型洞察、默认收件人、run_extensible vs auto_run 说明。 |
| 2026-02-24 | IP白名单 CIDR：IP白名单配置指南 新增「CIDR 表示法说明」；MatrixOne配置指南 §3 补充 CIDR；对话记录 §一 补充白名单 CIDR 提示。 |
| 2026-02-24 | 仓库说明：对话记录 §一 新增「支持的仓库说明」表格；Labels标签使用说明 新增「仓库说明」章节；README 主要功能下补充 matrixone/matrixflow 两仓库定位。 |
| 2026-02-24 | AI 驱动分析多仓库邮件：format_ai_analysis_section 支持 by_repo+order；matrixflow 优先展示。新增 §11；§三 §四 §六 补充 --ai-report、AI 驱动分析邮件说明。文档同步：自动运行脚本说明（--ai-report、示例8）、AI分析拓展升级优化方案（邮件集成）、完整分析报告说明（AI 驱动分析命令与输出）。 |
| 2026-02-24 | 产品需求文档 PRD：Download 输出 Word 版 PRD（参考治理指南、可行性报告）；新增 scripts/generate_prd_docx.py；用户要求简化后改为五章简化版。新增 §12；近期对话概要补充 PRD 与单独分析命令行。优化项文档新增「文档与交付物」PRD 说明。 |
| 2026-02-26 | 项目内容总结：新增「近期对话概要（2026-02-25/26）」— 自动写 Issue 与 AI 看板（feature_issue_and_kanban）、聊天流程、预览与模板、看板甘特图风格；§一 功能与数据库补充看板/知识库表；§三 关键文件路径与 §四 常用命令补充 feature_issue_and_kanban 脚本与看板命令。 |
| 2026-03-01 | 浏览器监听混合方案：4 层智能检测（CDP→窗口→剪贴板→手动）；监控原理（被动查询、可后触发）；内容来源（GitHub API 非网页解析）；范围限制（仅 GitHub Issue）。近期对话概要新增 §1 混合方案与测试结果。 |

---

*最后更新：2026-03-01*
