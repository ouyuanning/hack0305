# 聊天窗口流程：创建 Issue 与预览

在 Cursor 聊天窗口（或其它对话界面）中，由 AI 与你配合完成「你发起 → AI 启动服务 → 收集信息 → 生成预览 → 确认 → 提交 Issue」的流程。

---

## 〇、你发起请求

- **你**：在聊天里说「我要提一个 Bug」「帮我建一个 Feature 的 Issue」「建一个 Doc Request」等。
- **AI**：收到后先启动本机统一接口服务（若未启动），然后向你询问或确认信息。

**AI 需先启动的服务**（端口 8767）：
```bash
cd /Users/wupeng/Desktop/GitHub_Issue_智能管理系统
python3 feature_issue_and_kanban/services/unified_interface.py
# 后台运行：nohup python3 ... &  或  python3 ... &
# 健康检查：curl http://127.0.0.1:8767/health
```

若你只想**测试预览**（不创建 GitHub Issue），AI 全程使用 `create_issue_interactive.py --preview` 或 `test_preview.sh`，不调用创建接口。

---

## 一、单条 Issue 流程

### 1. 聊天窗口询问信息

- **你**：说明要建什么 Issue（例如「建一个 Bug：workers 模块报错 500」或「建一个单据检索的 PRD 的 Issue」）。
- **AI**：在聊天里向你询问或确认：
  - **仓库**：如 `matrixorigin/matrixflow`
  - **标题**：Issue 标题
  - **正文**：PRD 要点或完整内容
  - **负责人**：如 `wupeng`
  - **标签**（可选）：如 `kind/docs`、`area/问数`

### 2. AI 确认信息完整并生成预览

- 当你提供完上述信息后，AI 在聊天中确认：「信息已齐，正在生成预览页。」
- AI 执行**纯预览脚本**（不依赖数据库和 AI 接口，保证能生成文件）：
  ```bash
  cd /Users/wupeng/Desktop/GitHub_Issue_智能管理系统
  python3 feature_issue_and_kanban/scripts/generate_preview_only.py \
    --repo matrixorigin/matrixflow \
    --title "你确认的标题" \
    --body "你确认的正文内容" \
    --assignees "wupeng" \
    --output-html feature_issue_and_kanban/preview.html \
    --success-msg
  ```
- 脚本输出 `PREVIEW_OK <绝对路径>` 表示成功。
- AI 在聊天中回复：「生成成功，已生成本地预览页。」并执行打开浏览器：
  ```bash
  open feature_issue_and_kanban/preview.html
  ```
- 页面中会显示「生成成功」提示和完整标题/正文/负责人/标签，供你核对。

### 3. 在聊天中提出修改

- 你在聊天中说需要改什么，例如：「标题改成 xxx」「正文里加一段 yyy」。
- AI 根据你的修改更新标题/正文，再次执行 `generate_preview_only.py`（同上），并再次 `open .../preview.html`。
- 重复直到你在聊天中说「确认无误」或「没问题」。

### 4. 提交到 GitHub

- 你确认无误后，AI 执行创建 Issue（不再加 `--preview`）：
  ```bash
  python3 feature_issue_and_kanban/scripts/create_issue_interactive.py \
    --repo matrixorigin/matrixflow \
    --title "最终标题" \
    --body "最终正文" \
    --assignees "wupeng" \
    --labels "kind/docs,area/问数"
  ```
- 脚本会调用 GitHub API 创建 Issue，并在终端输出链接。
- AI 在聊天中把 **Issue 链接** 和 **编号** 发给你。

---

## 二、批量 Issue 流程

### 1. 在聊天中提供多条 Issue

- 你提供多条的：标题、正文、负责人、标签（可表格或列表）。
- AI 整理成一份 **CSV** 或 **JSON**，列：`title`（或 标题）、`body`（或 正文）、`labels`、`assignees`。

### 2. 批量创建并得到 Excel

- AI 执行批量脚本，例如：
  ```bash
  python3 feature_issue_and_kanban/scripts/batch_create_issues.py \
    --repo matrixorigin/matrixflow \
    --csv feature_issue_and_kanban/issues_batch.csv \
    --output feature_issue_and_kanban/result.xlsx
  ```
- 脚本会逐条创建 Issue，并生成 **Excel**（或未装 openpyxl 时生成 CSV），列：序号、Issue 编号、标题、链接、状态。
- AI 在聊天中把 **result.xlsx 的路径** 和「每条对应的链接」反馈给你。

---

## 三、脚本与路径约定

| 用途           | 脚本 | 说明 |
|----------------|------|------|
| **启动统一接口** | `unified_interface.py` | 端口 8767，Cursor/企微共用，你发起「我要提 Bug」时由 AI 启动 |
| 仅生成预览页   | `generate_preview_only.py` | 不依赖 DB/AI，保证能生成 preview.html |
| **测试预览**（不创建） | `test_preview.sh --demo` 或 `create_issue_interactive.py --preview` | 只到预览，不调 GitHub API |
| 直接创建单条   | `create_issue_interactive.py --title ... --body ...` | 跳过 AI，按给定标题/正文创建 |
| 批量创建+Excel | `batch_create_issues.py --csv/--json --output result.xlsx` | 批量创建并输出 Excel/CSV |

**使用顺序**：你先说「我要提 Bug」→ AI 启动 `unified_interface.py`（或直接用脚本）→ AI 按你的描述生成预览 → 你在网页上调整 → 确认后 AI 再创建（测试时可跳过创建）。

所有命令均在**项目根目录**下执行；预览页默认路径：`feature_issue_and_kanban/preview.html`。
