# 需求文档

## 简介

为 GitHub Issue 智能管理系统设计一个前端 Dashboard 页面，使用户能够通过 Web 界面与系统的各项功能进行交互。该系统当前通过 CLI 工具（issuectl）和 Python 脚本运行，包含 Issue 数据采集（WF-001）、知识库生成（WF-002）、智能提 Issue（WF-003/WF-004）、历史数据清洗（WF-005）、特殊 Issue 状态记录（WF-006）和分析报告生成（WF-007）等工作流。前端 Dashboard 将提供数据可视化、Issue 管理、分析报告查看和工作流触发等核心能力。

## 术语表

- **Dashboard**: 前端 Web 仪表盘页面，系统的主要用户界面
- **Issue_List**: Issue 列表视图组件，展示 Issue 数据并支持筛选排序
- **Issue_Detail**: Issue 详情视图组件，展示单个 Issue 的完整信息
- **Report_Viewer**: 分析报告查看组件，展示 WF-007 生成的各类分析报告
- **Kanban_Board**: 看板视图组件，按项目或客户维度展示 Issue 状态
- **Issue_Creator**: Issue 创建组件，对应 WF-003/WF-004 的前端交互界面
- **Workflow_Trigger**: 工作流触发组件，允许用户通过界面触发后端工作流
- **Knowledge_Base_Viewer**: 知识库查看组件，展示 WF-002 生成的知识库内容
- **Backend_API**: Go 后端提供的 REST API 接口层
- **Filter_Panel**: 筛选面板组件，提供多维度数据筛选能力

## 需求

### 需求 1：Dashboard 总览页

**用户故事：** 作为项目管理人员，我希望打开 Dashboard 后能看到系统的整体概况，以便快速了解当前 Issue 的整体状态。

#### 验收标准

1. WHEN 用户访问 Dashboard 首页，THE Dashboard SHALL 展示 Issue 总数、Open 数量、Closed 数量和 Open 占比的统计卡片
2. WHEN 用户访问 Dashboard 首页，THE Dashboard SHALL 展示按 Labels 前缀（kind/、area/、customer/）分组的 Issue 分布图表
3. WHEN 用户访问 Dashboard 首页，THE Dashboard SHALL 展示最近 7 天内更新的 Issue 列表（按更新时间降序，最多 20 条）
4. WHEN 用户访问 Dashboard 首页，THE Dashboard SHALL 展示各客户项目的健康度评分摘要（来自 WF-007 的分析结果）
5. IF Dashboard 首页数据加载失败，THEN THE Dashboard SHALL 展示错误提示信息并提供重试按钮

### 需求 2：Issue 列表与筛选

**用户故事：** 作为开发人员，我希望能够按多种维度筛选和搜索 Issue，以便快速找到需要关注的 Issue。

#### 验收标准

1. THE Issue_List SHALL 以分页表格形式展示 Issue 数据，每页默认 20 条，包含编号、标题、状态、Labels、负责人和更新时间列
2. WHEN 用户在 Filter_Panel 中选择筛选条件（状态、Labels、负责人、时间范围），THE Issue_List SHALL 根据所选条件过滤展示的 Issue 数据
3. WHEN 用户在搜索框中输入关键词，THE Issue_List SHALL 按标题和正文内容匹配并展示搜索结果
4. WHEN 用户点击表格列标题，THE Issue_List SHALL 按该列进行升序或降序排序
5. WHEN 用户点击某条 Issue 行，THE Issue_Detail SHALL 展示该 Issue 的完整信息，包含标题、正文（Markdown 渲染）、Labels、负责人、时间线和评论
6. IF 查询结果为空，THEN THE Issue_List SHALL 展示"无匹配结果"的提示信息

### 需求 3：看板视图

**用户故事：** 作为项目管理人员，我希望以看板形式查看项目 Issue 的状态分布，以便直观了解项目进度。

#### 验收标准

1. WHEN 用户切换到看板视图，THE Kanban_Board SHALL 按 Issue 状态（待处理、进行中、已完成、已关闭）分列展示 Issue 卡片
2. WHEN 用户在看板视图中选择一个 project/ 标签，THE Kanban_Board SHALL 仅展示带有该 project/ 标签的 Issue
3. WHEN 用户在看板视图中选择一个 customer/ 标签，THE Kanban_Board SHALL 仅展示带有该 customer/ 标签的 Issue
4. THE Kanban_Board SHALL 在每个 Issue 卡片上展示标题、负责人、优先级标识和进度百分比
5. WHEN 用户点击看板中的 Issue 卡片，THE Issue_Detail SHALL 展示该 Issue 的完整信息
6. THE Kanban_Board SHALL 在看板顶部展示当前筛选维度下的完成率和平均进度统计

### 需求 4：智能创建 Issue

**用户故事：** 作为开发人员，我希望通过前端界面输入问题描述后，系统能 AI 智能生成 Issue 预览，以便降低提 Issue 的门槛。

#### 验收标准

1. WHEN 用户在 Issue_Creator 中输入文字描述并提交，THE Issue_Creator SHALL 调用后端 AI 接口生成 Issue 预览，包含标题、正文、推荐 Labels 和推荐负责人
2. WHEN 用户在 Issue_Creator 中上传图片，THE Issue_Creator SHALL 将图片作为附加上下文发送给后端 AI 接口
3. WHEN AI 生成 Issue 预览完成，THE Issue_Creator SHALL 以可编辑表单形式展示预览内容，允许用户修改标题、正文、Labels 和负责人
4. WHEN 用户确认 Issue 预览内容并点击"创建"按钮，THE Issue_Creator SHALL 调用后端 API 将 Issue 创建到 GitHub，并展示创建成功的 Issue 链接
5. WHILE AI 正在生成 Issue 预览，THE Issue_Creator SHALL 展示加载状态指示器
6. IF AI 生成 Issue 预览失败，THEN THE Issue_Creator SHALL 展示错误信息并允许用户手动填写 Issue 内容

### 需求 5：分析报告查看

**用户故事：** 作为项目管理人员，我希望在前端查看系统生成的各类分析报告，以便获取项目洞察和决策支持。

#### 验收标准

1. THE Report_Viewer SHALL 展示可用报告列表，按生成时间降序排列，包含报告类型（项目推进分析、横向关联分析、可扩展分析）、生成时间和仓库名称
2. WHEN 用户选择一份报告，THE Report_Viewer SHALL 以结构化方式渲染报告内容，包含统计数据、图表和 AI 洞察
3. WHEN 用户查看项目推进分析报告，THE Report_Viewer SHALL 展示各客户的健康度评分、层级统计表格、堵塞点列表和 AI 建议
4. WHEN 用户查看横向关联分析报告，THE Report_Viewer SHALL 展示共用 Feature 列表、高 Bug Feature 列表和 AI 战略建议
5. WHEN 用户点击报告中的 Issue 编号链接，THE Dashboard SHALL 导航到该 Issue 的详情页面
6. IF 报告列表为空，THEN THE Report_Viewer SHALL 展示"暂无报告"的提示信息并引导用户触发报告生成

### 需求 6：工作流触发与状态监控

**用户故事：** 作为系统管理员，我希望通过前端界面触发后端工作流并查看执行状态，以便替代命令行操作。

#### 验收标准

1. THE Workflow_Trigger SHALL 展示所有可用工作流列表（WF-001 至 WF-007），包含工作流名称、描述和实现状态
2. WHEN 用户选择一个工作流并填写必要参数（如 repo_owner、repo_name），THE Workflow_Trigger SHALL 调用后端 API 触发该工作流执行
3. WHEN 工作流开始执行，THE Workflow_Trigger SHALL 展示执行状态（排队中、执行中、已完成、失败）
4. WHEN 工作流执行完成，THE Workflow_Trigger SHALL 展示执行结果摘要（如同步的 Issue 数量、生成的报告路径）
5. IF 工作流执行失败，THEN THE Workflow_Trigger SHALL 展示错误信息和失败原因
6. WHILE 工作流正在执行，THE Workflow_Trigger SHALL 禁用该工作流的重复触发按钮

### 需求 7：知识库查看

**用户故事：** 作为开发人员，我希望在前端查看系统生成的知识库内容，以便了解产品结构、标签体系和常见 Issue 类型。

#### 验收标准

1. WHEN 用户访问知识库页面，THE Knowledge_Base_Viewer SHALL 展示最新版本的知识库内容，包含产品结构、标签体系和常见 Issue 类型三个板块
2. WHEN 用户在产品结构板块中点击某个产品或模块，THE Knowledge_Base_Viewer SHALL 展示该产品或模块关联的 Issue 列表
3. WHEN 用户在标签体系板块中点击某个标签，THE Issue_List SHALL 按该标签筛选展示 Issue
4. THE Knowledge_Base_Viewer SHALL 展示知识库的生成时间和版本信息
5. IF 知识库数据不存在，THEN THE Knowledge_Base_Viewer SHALL 展示"知识库尚未生成"的提示信息并引导用户触发 WF-002

### 需求 8：后端 API 层

**用户故事：** 作为前端开发人员，我希望后端提供 RESTful API 接口，以便前端页面能够获取数据和触发操作。

#### 验收标准

1. THE Backend_API SHALL 提供 Issue 查询接口，支持分页、筛选（状态、Labels、负责人、时间范围）和关键词搜索参数
2. THE Backend_API SHALL 提供 Issue 详情接口，返回单个 Issue 的完整信息（含评论和时间线）
3. THE Backend_API SHALL 提供分析报告列表和详情接口，返回 JSON 格式的报告数据
4. THE Backend_API SHALL 提供工作流触发接口，接受工作流 ID 和参数，返回执行状态
5. THE Backend_API SHALL 提供知识库查询接口，返回最新版本的知识库数据
6. THE Backend_API SHALL 提供 AI Issue 生成接口，接受用户描述和图片，返回 Issue 预览数据
7. THE Backend_API SHALL 提供 Issue 创建接口，接受 Issue 内容并调用 GitHub API 创建 Issue
8. IF 请求参数不合法，THEN THE Backend_API SHALL 返回 HTTP 400 状态码和错误描述
9. IF 后端服务内部错误，THEN THE Backend_API SHALL 返回 HTTP 500 状态码和错误描述

### 需求 9：响应式布局与导航

**用户故事：** 作为用户，我希望 Dashboard 页面在不同屏幕尺寸下都能正常使用，并且导航结构清晰。

#### 验收标准

1. THE Dashboard SHALL 提供侧边栏导航，包含总览、Issue 列表、看板、创建 Issue、分析报告、工作流管理和知识库等导航项
2. WHEN 用户点击侧边栏导航项，THE Dashboard SHALL 切换到对应的页面视图
3. WHILE 屏幕宽度小于 768px，THE Dashboard SHALL 将侧边栏折叠为汉堡菜单
4. THE Dashboard SHALL 在页面顶部展示当前仓库名称和用户信息
5. THE Dashboard SHALL 支持在多个仓库之间切换（如 matrixone 和 matrixflow）
