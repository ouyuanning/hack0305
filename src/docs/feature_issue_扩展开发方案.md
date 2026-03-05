# 自动提 Issue 模块 - 扩展开发方案

> 基于云端友好架构、3大需求实施方案、扩展方案文档整合  
> 更新日期：2026-02-28

---

## 一、总体架构（云端友好）

```
┌─────────────────────────────────────────────────────┐
│  应用层（统一接口）                                  │
│  • Cursor 扩展 / 企微 Bot / Web API                  │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│  环境检测层（自动适配）                              │
│  core/environment.py + core/config_manager.py        │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│  核心服务层（始终可用）                              │
│  • AI Issue 生成器 • 重复检测 • GitHub API           │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│  可选功能层（动态加载）                              │
│  • 上下文监控（本地） • 图片上传（云端/本地）         │
└─────────────────────────────────────────────────────┘
```

---

## 二、实施计划与优先级

| 序号 | 模块 | 优先级 | 说明 | 预估时间 |
|------|------|--------|------|----------|
| 1 | 云端友好架构 | P0 | 分层依赖、环境检测、配置管理 | 1 周 |
| 2 | 重复 Issue 检测 | P0 | 规则+AI，不依赖向量库 | 1 周 |
| 3 | 上下文服务 + AIIssueGenerator 增强 | P1 | Flask 服务，增强 prompt | 2 周 |
| 4 | 企微集成 + 统一接口 | P2 | Webhook、Session 管理 | 1-2 周 |
| 5 | Cursor 扩展 | P3 | 上下文采集、快捷键 | 2-3 周 |

---

## 三、模块与文件清单

### 3.1 云端友好架构

| 文件 | 说明 |
|------|------|
| `feature_issue_and_kanban/requirements/requirements-core.txt` | 核心依赖（requests、psutil 等） |
| `feature_issue_and_kanban/requirements/requirements-local.txt` | 本地监控（pyobjc、pywinauto 等） |
| `feature_issue_and_kanban/requirements/requirements-cloud.txt` | 云端部署（gunicorn、redis、boto3） |
| `feature_issue_and_kanban/core/environment.py` | 环境检测、配置加载 |
| `feature_issue_and_kanban/core/config_manager.py` | 统一配置接口 |
| `feature_issue_and_kanban/core/feature_loader.py` | 功能动态加载 |
| `feature_issue_and_kanban/scripts/setup_dependencies.py` | 自动安装依赖 |
| `feature_issue_and_kanban/scripts/deploy.py` | 一键部署（local/docker/cloud） |
| `feature_issue_and_kanban/Dockerfile` | Docker 镜像 |
| `feature_issue_and_kanban/docker-compose.yml` | 本地测试云端环境 |
| `feature_issue_and_kanban/.env.example` | 环境变量模板 |

### 3.2 重复检测

| 文件 | 说明 |
|------|------|
| `feature_issue_and_kanban/issue_creator/duplicate_detector.py` | 规则过滤 + AI 判断，不依赖向量 |

### 3.3 上下文与企微

| 文件 | 说明 |
|------|------|
| `feature_issue_and_kanban/services/context_service.py` | Cursor 上下文捕获服务（Flask） |
| `feature_issue_and_kanban/services/wechat_service.py` | 企微 Bot Webhook |
| `feature_issue_and_kanban/services/unified_interface.py` | Cursor/企微 统一 API |
| `feature_issue_and_kanban/utils/imgur_uploader.py` | 本地图床（Imgur） |
| `feature_issue_and_kanban/utils/s3_uploader.py` | 云端 S3 上传 |

### 3.4 AIIssueGenerator 增强

在 `issue_creator/ai_issue_generator.py` 中新增方法：
- `generate_from_enhanced_context(enhanced_prompt, context, screenshots)`：从代码上下文生成
- `generate_with_duplicate_check(user_input, context)`：生成并检查重复

---

## 四、关键设计

### 4.1 重复检测（不依赖向量）

- **第一轮**：规则过滤（标签、关键词、标题相似）
- **第二轮**：AI 理解判断（merge/link/create）
- **数据源**：`issues_snapshot` 表

### 4.2 统一接口

- Cursor 与企微通过同一 API：`POST /api/create-issue`
- `source` 参数区分：`cursor` / `wechat`
- Cursor 可传 `context`（文件、代码、报错），企微仅文字

### 4.3 环境检测

- `CLOUD_DEPLOYMENT` / `/.dockerenv` / AWS/阿里云/K8s 环境变量 → 云端
- 云端：禁用监控，使用 S3/Redis
- 本地：可选监控，使用 Imgur/内存缓存

---

## 五、参考文档

- `Downloads/云端友好架构-完整方案.md` - 环境检测、分层依赖、Docker
- `Downloads/基于现有代码的3大需求实施方案.md` - 上下文服务、重复检测、企微
- `Downloads/Issue智能管理系统_扩展方案.md` - Cursor 扩展、相似检测、企微适配

---

*文档版本：v1.0 | 2026-02-28*
