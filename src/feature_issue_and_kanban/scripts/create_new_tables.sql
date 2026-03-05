-- 自动写 Issue 与 AI 看板功能 - 新增表结构
-- 执行方式：使用 scripts/run_create_tables.py 或数据库客户端执行
-- 兼容 MatrixOne / MySQL

-- 1. 项目管理 Issue 每日快照表
CREATE TABLE IF NOT EXISTS project_issues (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    issue_number INT NOT NULL COMMENT 'GitHub Issue编号',
    repo_owner VARCHAR(100) NOT NULL COMMENT '仓库所有者',
    repo_name VARCHAR(100) NOT NULL COMMENT '仓库名称',
    issue_title TEXT COMMENT 'Issue标题',
    issue_state VARCHAR(20) COMMENT 'Issue状态: open/closed',
    issue_url VARCHAR(500) COMMENT 'GitHub Issue URL',
    project_tag VARCHAR(100) COMMENT '项目标签: project/问数深化',
    issue_type VARCHAR(50) COMMENT 'PM类型: milestone/epic/task',
    pm_status VARCHAR(50) DEFAULT 'not_started' COMMENT 'PM状态: not_started/in_progress/completed/blocked',
    planned_start_date DATE COMMENT '计划开始日期',
    planned_end_date DATE COMMENT '计划结束日期',
    actual_start_date DATE COMMENT '实际开始日期',
    actual_end_date DATE COMMENT '实际结束日期',
    progress INT DEFAULT 0 COMMENT '进度: 0-100',
    risk_level VARCHAR(20) DEFAULT 'low' COMMENT '风险等级: low/medium/high/critical',
    is_overdue BOOLEAN DEFAULT FALSE COMMENT '是否逾期',
    days_overdue INT DEFAULT 0 COMMENT '逾期天数',
    assignee VARCHAR(100) COMMENT '负责人',
    team VARCHAR(100) COMMENT '所属团队',
    parent_issue_number INT COMMENT '父Issue编号',
    dependencies JSON COMMENT '依赖的Issue列表',
    blocks JSON COMMENT '阻塞的Issue列表',
    related_issues JSON COMMENT '相关Issue列表',
    snapshot_date DATE NOT NULL COMMENT '快照日期',
    progress_change INT DEFAULT 0 COMMENT '进度变化(与昨日对比)',
    status_changed BOOLEAN DEFAULT FALSE COMMENT '状态是否变化',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_project (project_tag, snapshot_date),
    INDEX idx_issue (repo_owner, repo_name, issue_number, snapshot_date),
    INDEX idx_snapshot (snapshot_date),
    INDEX idx_status (pm_status, snapshot_date),
    INDEX idx_assignee (assignee, snapshot_date),
    UNIQUE KEY uk_issue_snapshot (repo_owner, repo_name, issue_number, snapshot_date)
) COMMENT='项目管理Issue每日快照表';

-- 2. Issue 知识库表
CREATE TABLE IF NOT EXISTS issue_knowledge_base (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    knowledge_type VARCHAR(50) NOT NULL COMMENT '知识类型: product/feature/label/common_issue',
    category VARCHAR(100) COMMENT '一级分类: MOI/MO/问数',
    subcategory VARCHAR(100) COMMENT '二级分类',
    title VARCHAR(500) NOT NULL COMMENT '知识标题',
    description TEXT COMMENT '详细描述',
    keywords JSON COMMENT '关键词列表',
    examples JSON COMMENT '示例Issue编号',
    issue_count INT DEFAULT 0 COMMENT '相关Issue数量',
    confidence FLOAT DEFAULT 1.0 COMMENT '置信度: 0-1',
    version INT DEFAULT 1 COMMENT '版本号',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '生成时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_type (knowledge_type, category),
    INDEX idx_active (is_active, knowledge_type),
    INDEX idx_version (version, generated_at)
) COMMENT='Issue知识库';

-- 3. 对话会话表（多轮创建 Issue）
CREATE TABLE IF NOT EXISTS conversation_sessions (
    session_id VARCHAR(64) PRIMARY KEY COMMENT 'Session UUID',
    user_id VARCHAR(100) NOT NULL COMMENT '用户ID',
    status VARCHAR(20) DEFAULT 'active' COMMENT '状态: active/expired/completed',
    conversation_history JSON COMMENT '对话历史记录',
    current_draft JSON COMMENT '当前Issue草稿',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL COMMENT 'Session过期时间',
    INDEX idx_user (user_id, status),
    INDEX idx_expires (expires_at)
) COMMENT='对话Session表';
