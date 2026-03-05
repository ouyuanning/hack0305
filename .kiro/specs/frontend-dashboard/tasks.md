# 实施计划：Frontend Dashboard

## 概述

基于前后端分离架构，先搭建后端 Go API 层（复用现有 internal 包），再构建前端 React SPA 应用。后端优先确保数据接口可用，前端逐步实现各页面组件。采用增量开发方式，每个阶段都可独立验证。

## 任务

- [x] 1. 搭建后端 API 基础框架
  - [x] 1.1 创建 API 服务入口和路由框架
    - 创建 `go/cmd/api-server/main.go`，初始化 Gin 引擎、加载配置、注册路由、启动 HTTP 服务
    - 创建 `go/internal/api/router.go`，定义路由组 `/api/v1/`，注册所有 API 路由
    - 创建 `go/internal/api/types.go`，定义 `PaginatedResponse`、`ErrorResponse`、`OverviewResponse`、`HealthScore` 等请求/响应结构体
    - _需求: 8.1-8.9_

  - [x] 1.2 实现 CORS 和错误处理中间件
    - 创建 `go/internal/api/middleware.go`，实现 CORS 中间件（允许前端跨域请求）和统一错误处理中间件（panic 恢复、错误响应格式化）
    - _需求: 8.8, 8.9_

  - [ ]* 1.3 编写中间件属性测试
    - **Property 15: API 非法参数拒绝**
    - **验证: 需求 8.8**

- [x] 2. 实现后端 Issue 相关 API
  - [x] 2.1 实现 Issue 列表查询接口
    - 创建 `go/internal/api/issues.go`，实现 `GET /api/v1/issues` handler
    - 从 VolumeStore 加载 Issue 快照，实现内存筛选（状态、标签、负责人、时间范围）、关键词搜索（标题+正文）、排序和分页逻辑
    - _需求: 8.1, 2.1, 2.2, 2.3, 2.4_

  - [ ]* 2.2 编写分页逻辑属性测试
    - **Property 5: 分页正确性**
    - **验证: 需求 2.1, 8.1**

  - [ ]* 2.3 编写筛选逻辑属性测试
    - **Property 6: 多维度筛选正确性**
    - **验证: 需求 2.2, 3.2, 3.3**

  - [ ]* 2.4 编写关键词搜索属性测试
    - **Property 7: 关键词搜索正确性**
    - **验证: 需求 2.3**

  - [ ]* 2.5 编写排序逻辑属性测试
    - **Property 8: 排序正确性**
    - **验证: 需求 2.4**

  - [x] 2.6 实现 Issue 详情接口和创建接口
    - 实现 `GET /api/v1/issues/:number` handler，返回 Issue 快照、评论、时间线和关联关系
    - 实现 `POST /api/v1/issues` handler，调用 GitHub Client 创建 Issue，返回 issue_number 和 html_url
    - _需求: 8.2, 8.7_

- [x] 3. 实现后端统计、报告和知识库 API
  - [x] 3.1 实现 Dashboard 统计接口
    - 创建 `go/internal/api/stats.go`（或在 issues.go 中），实现 `GET /api/v1/stats/overview` 和 `GET /api/v1/stats/labels`
    - 计算 Issue 总数/Open/Closed/Open 占比、最近 7 天更新 Issue、各客户健康度评分、Labels 分组统计
    - _需求: 1.1, 1.2, 1.3, 1.4_

  - [x] 3.2 实现报告列表和详情接口
    - 创建 `go/internal/api/reports.go`，实现 `GET /api/v1/reports` 和 `GET /api/v1/reports/:id`
    - 从存储层读取报告文件列表和内容，返回 JSON 格式数据
    - _需求: 8.3, 5.1_

  - [x] 3.3 实现知识库查询接口
    - 创建 `go/internal/api/knowledge.go`，实现 `GET /api/v1/knowledge`
    - 从存储层读取最新知识库文件，返回 content、generated_at、version
    - _需求: 8.5, 7.1, 7.4_

  - [x] 3.4 实现仓库列表接口
    - 实现 `GET /api/v1/repos`，返回配置中的可用仓库列表
    - _需求: 9.5_

- [x] 4. 实现后端工作流和 AI 接口
  - [x] 4.1 实现工作流管理接口
    - 创建 `go/internal/api/workflows.go`，实现 `GET /api/v1/workflows`（工作流列表）、`POST /api/v1/workflows/:id/trigger`（触发执行）、`GET /api/v1/workflows/:id/status`（查询状态）
    - 工作流执行状态使用内存 map 管理，触发时启动 goroutine 异步执行
    - 执行中的工作流拒绝重复触发（返回 409）
    - _需求: 8.4, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [ ]* 4.2 编写工作流状态管理属性测试
    - **Property 14: 工作流状态有效性与防重复触发**
    - **验证: 需求 6.3, 6.6**

  - [x] 4.3 实现 AI Issue 生成接口
    - 创建 `go/internal/api/ai.go`，实现 `POST /api/v1/ai/generate-issue`
    - 调用 LLM Client 生成 Issue 预览（标题、正文、推荐 Labels、推荐负责人）
    - _需求: 8.6, 4.1_

- [x] 5. 检查点 - 后端 API 验证
  - 确保所有后端测试通过，使用 httptest 验证各 API 端点的基本功能，如有问题请询问用户。

- [x] 6. 搭建前端项目基础框架
  - [x] 6.1 初始化前端项目
    - 使用 Vite 创建 React + TypeScript 项目到 `frontend/` 目录
    - 安装依赖：antd、echarts、echarts-for-react、zustand、react-router-dom、axios、react-markdown、remark-gfm
    - 配置 `vite.config.ts`（API 代理到后端）、`tsconfig.json`
    - _需求: 9.1-9.5_

  - [x] 6.2 定义 TypeScript 类型和 API Client
    - 创建 `frontend/src/types/index.ts`，定义 Issue、Comment、Relation、IssueDraft、Report、WorkflowDef、WorkflowExecution、HealthScore、KnowledgeBase、LabelGroup、PaginatedResponse、RepoInfo 等类型
    - 创建 `frontend/src/api/client.ts`，配置 Axios 实例（baseURL、请求/响应拦截器、错误处理）
    - 创建 `frontend/src/api/issues.ts`、`reports.ts`、`workflows.ts`、`knowledge.ts`，封装各模块 API 调用函数
    - _需求: 8.1-8.7_

  - [x] 6.3 实现全局状态管理和路由
    - 创建 `frontend/src/stores/appStore.ts`，使用 Zustand 管理全局状态（当前仓库 repo_owner/repo_name、仓库列表）
    - 创建 `frontend/src/App.tsx`，配置 React Router v6 路由（/、/issues、/issues/:number、/kanban、/create-issue、/reports、/reports/:id、/workflows、/knowledge）
    - _需求: 9.2, 9.5_

  - [x] 6.4 实现 Layout 布局组件
    - 创建 `frontend/src/components/Layout.tsx`，使用 Ant Design Layout + Sider + Menu 实现侧边栏导航
    - 顶部栏展示当前仓库名称和仓库切换下拉框（Select 组件）
    - 响应式处理：屏幕宽度 < 768px 时侧边栏折叠为汉堡菜单（使用 Sider 的 collapsible + breakpoint）
    - 创建 `frontend/src/components/ErrorBoundary.tsx`，实现 React 错误边界组件
    - _需求: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [ ]* 6.5 编写路由映射属性测试
    - **Property 16: 导航路由映射**
    - **验证: 需求 9.2**

  - [ ]* 6.6 编写仓库切换状态属性测试
    - **Property 17: 仓库切换状态更新**
    - **验证: 需求 9.5**

- [x] 7. 实现 Dashboard 总览页
  - [x] 7.1 实现 Dashboard 页面组件
    - 创建 `frontend/src/pages/Dashboard.tsx`
    - 统计卡片区：使用 Ant Design Card + Statistic 展示 Issue 总数、Open 数量、Closed 数量、Open 占比
    - 图表区：使用 ECharts 饼图/柱状图展示按 Labels 前缀分组的 Issue 分布
    - 最近更新列表：使用 Ant Design List 展示最近 7 天更新的 Issue（点击跳转详情）
    - 健康度摘要：使用 Card 展示各客户项目健康度评分
    - 错误处理：加载失败时展示 Alert + 重试按钮
    - _需求: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [ ]* 7.2 编写统计计算属性测试
    - **Property 1: Issue 统计不变量**
    - **验证: 需求 1.1**

  - [ ]* 7.3 编写 Labels 分组属性测试
    - **Property 2: Labels 分组正确性**
    - **验证: 需求 1.2**

  - [ ]* 7.4 编写最近更新过滤属性测试
    - **Property 3: 最近更新 Issue 过滤与排序**
    - **验证: 需求 1.3**

  - [ ]* 7.5 编写健康度评分属性测试
    - **Property 4: 健康度评分计算**
    - **验证: 需求 1.4**

- [x] 8. 实现 Issue 列表和详情页
  - [x] 8.1 实现 Issue 列表页面组件
    - 创建 `frontend/src/pages/IssueList.tsx`
    - 使用 Ant Design Table 实现分页表格（列：编号、标题、状态 Tag、Labels Tag 组、负责人、更新时间），每页默认 20 条
    - 实现 Filter_Panel：状态 Select、Labels 多选 Select、负责人 Select、时间范围 RangePicker
    - 实现搜索框：Input.Search 组件，关键词搜索
    - 点击列标题排序，点击行跳转 IssueDetail
    - 空结果展示 Empty 组件提示"无匹配结果"
    - _需求: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [x] 8.2 实现 Issue 详情页面组件
    - 创建 `frontend/src/pages/IssueDetail.tsx`
    - 使用 react-markdown + remark-gfm 渲染 Issue 正文
    - 展示 Labels（Tag 组件）、负责人、创建/更新时间
    - 使用 Timeline 组件展示时间线事件
    - 使用 Comment 组件展示评论列表
    - _需求: 2.5_

  - [ ]* 8.3 编写前端分页逻辑属性测试
    - **Property 5: 分页正确性（前端验证）**
    - **验证: 需求 2.1**

- [x] 9. 实现看板视图页
  - [x] 9.1 实现 KanbanBoard 页面组件
    - 创建 `frontend/src/pages/KanbanBoard.tsx`
    - 四列看板布局（待处理、进行中、已完成、已关闭），使用 Ant Design Card + Row/Col 实现
    - 每个 Issue 卡片展示标题、负责人 Avatar、优先级 Badge、进度 Progress 组件
    - 顶部筛选：project/ 标签下拉、customer/ 标签下拉
    - 顶部统计栏：完成率和平均进度 Statistic 组件
    - 点击卡片跳转 IssueDetail
    - _需求: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [ ]* 9.2 编写看板分列属性测试
    - **Property 9: 看板状态分列正确性**
    - **验证: 需求 3.1**

  - [ ]* 9.3 编写看板卡片信息属性测试
    - **Property 10: 看板卡片信息完整性**
    - **验证: 需求 3.4**

  - [ ]* 9.4 编写看板统计属性测试
    - **Property 11: 看板统计计算**
    - **验证: 需求 3.6**

- [x] 10. 实现智能创建 Issue 页
  - [x] 10.1 实现 IssueCreator 页面组件
    - 创建 `frontend/src/pages/IssueCreator.tsx`
    - 输入区：TextArea 输入问题描述 + Upload 组件支持图片上传（拖拽）
    - 提交按钮调用 AI 生成接口，展示 Spin 加载状态
    - 预览表单：可编辑的 Input（标题）、Markdown 编辑器（正文）、Select 多选（Labels）、Select（负责人）
    - 确认创建按钮调用创建接口，成功后展示 Issue 链接（Result 组件）
    - AI 生成失败时展示 Alert 错误信息，允许手动填写
    - _需求: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [ ]* 10.2 编写 AI Draft 响应属性测试
    - **Property 12: AI Draft 响应完整性**
    - **验证: 需求 4.1**

- [x] 11. 检查点 - 前端核心页面验证
  - 确保所有前端测试通过，验证 Dashboard、Issue 列表/详情、看板、创建 Issue 页面的基本渲染和交互，如有问题请询问用户。

- [x] 12. 实现报告查看页
  - [x] 12.1 实现 ReportList 和 ReportDetail 页面组件
    - 创建 `frontend/src/pages/ReportList.tsx`，使用 Table 展示报告列表（报告类型、生成时间、仓库名称），按生成时间降序
    - 空列表展示 Empty 提示"暂无报告"并引导触发报告生成
    - 创建 `frontend/src/pages/ReportDetail.tsx`，根据报告类型渲染不同结构：
      - 项目推进分析：健康度评分 Card、层级统计 Table、堵塞点 List、AI 建议 Alert
      - 横向关联分析：共用 Feature Table、高 Bug Feature Table、AI 战略建议
    - Issue 编号渲染为 Link，点击跳转 IssueDetail
    - _需求: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

  - [ ]* 12.2 编写报告列表排序属性测试
    - **Property 13: 报告列表排序**
    - **验证: 需求 5.1**

- [x] 13. 实现工作流管理页
  - [x] 13.1 实现 WorkflowManager 页面组件
    - 创建 `frontend/src/pages/WorkflowManager.tsx`
    - 使用 Card 列表展示所有工作流（WF-001 ~ WF-007），包含名称、描述、实现状态 Badge
    - 点击展开参数表单（Form 组件：repo_owner、repo_name 等动态参数）
    - 触发按钮调用触发接口，展示执行状态（Steps 或 Tag 组件：排队中/执行中/已完成/失败）
    - 执行中时禁用触发按钮（Button disabled）
    - 完成后展示结果摘要（Descriptions 组件），失败时展示错误信息（Alert）
    - _需求: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [x] 14. 实现知识库页
  - [x] 14.1 实现 KnowledgeBase 页面组件
    - 创建 `frontend/src/pages/KnowledgeBase.tsx`
    - 使用 Tabs 组件展示三个板块：产品结构、标签体系、常见 Issue 类型
    - 使用 react-markdown 渲染知识库内容
    - 产品/模块和标签渲染为可点击链接，跳转到 IssueList 并携带筛选参数
    - 展示生成时间和版本信息（Descriptions 组件）
    - 知识库不存在时展示 Empty 提示"知识库尚未生成"并引导触发 WF-002
    - _需求: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ]* 14.2 编写知识库元数据属性测试
    - **Property 18: 知识库元数据完整性**
    - **验证: 需求 7.4**

- [x] 15. 前后端集成与联调
  - [x] 15.1 配置前端 API 代理和联调
    - 配置 `vite.config.ts` 的 proxy 将 `/api` 请求代理到后端 Go 服务
    - 验证前端各页面与后端 API 的数据交互正确性
    - 处理 API 错误响应在前端的展示（400/404/500 状态码对应的用户提示）
    - _需求: 8.8, 8.9, 1.5, 4.6, 6.5_

- [x] 16. 最终检查点 - 全部测试通过
  - 确保所有前端和后端测试通过，验证各页面功能完整性和 API 接口正确性，如有问题请询问用户。

## 备注

- 标记 `*` 的任务为可选任务，可跳过以加速 MVP 开发
- 每个任务引用了具体的需求编号，确保需求可追溯
- 检查点任务用于阶段性验证，确保增量开发的正确性
- 属性测试验证通用正确性属性，单元测试验证具体示例和边界情况
- 前端属性测试使用 fast-check + Vitest，后端属性测试使用 gopter
