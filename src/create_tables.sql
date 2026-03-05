-- ============================================
-- GitHub Issue 智能管理系统 - 数据库表结构
-- 适用于 MatrixOne 数据库
-- ============================================

USE github_issues;

-- 1. Issues快照表
CREATE TABLE IF NOT EXISTS issues_snapshot (
    id INT AUTO_INCREMENT PRIMARY KEY,
    issue_id INT NOT NULL COMMENT 'GitHub Issue ID',
    issue_number INT NOT NULL COMMENT 'Issue编号',
    repo_owner VARCHAR(100) NOT NULL COMMENT '仓库所有者',
    repo_name VARCHAR(100) NOT NULL COMMENT '仓库名称',
    title VARCHAR(500) NOT NULL COMMENT '标题',
    body TEXT COMMENT '内容',
    state VARCHAR(20) NOT NULL COMMENT '状态: open, closed',
    issue_type VARCHAR(50) COMMENT '类型: bug, feature, task',
    priority VARCHAR(10) COMMENT '优先级: P0, P1, P2, P3',
    assignee VARCHAR(100) COMMENT '负责人',
    labels JSON COMMENT '标签',
    milestone VARCHAR(100) COMMENT '里程碑',
    created_at DATETIME COMMENT '创建时间',
    updated_at DATETIME COMMENT '更新时间',
    closed_at DATETIME COMMENT '关闭时间',
    ai_summary TEXT COMMENT 'AI摘要',
    ai_tags JSON COMMENT 'AI标签',
    ai_priority VARCHAR(10) COMMENT 'AI优先级',
    status VARCHAR(50) COMMENT '状态: 待处理, 处理中, 待评审, 已完成, 已关闭',
    progress_percentage FLOAT DEFAULT 0.0 COMMENT '进度百分比',
    is_blocked BOOLEAN DEFAULT FALSE COMMENT '是否被阻塞',
    blocked_reason TEXT COMMENT '阻塞原因',
    snapshot_time DATETIME NOT NULL COMMENT '快照时间',
    created_at_db DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '数据库创建时间',
    INDEX idx_issue_id (issue_id),
    INDEX idx_issue_number (issue_number),
    INDEX idx_snapshot_time (snapshot_time),
    UNIQUE KEY uk_issue_snapshot (issue_id, snapshot_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Issue快照表';

-- 2. Issue关联关系表
CREATE TABLE IF NOT EXISTS issue_relations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    from_issue_id INT NOT NULL COMMENT '源Issue的GitHub ID',
    to_issue_id INT NOT NULL COMMENT '目标Issue的GitHub ID',
    relation_type VARCHAR(50) NOT NULL COMMENT '关系类型: mention, reference, duplicate, related, fixes, blocks, depends_on',
    relation_semantic VARCHAR(100) COMMENT '关系语义描述',
    created_at DATETIME COMMENT '创建时间',
    source VARCHAR(50) COMMENT '来源: body, comment',
    context_text TEXT COMMENT '上下文文本',
    created_at_db DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '数据库创建时间',
    INDEX idx_from_issue_id (from_issue_id),
    INDEX idx_to_issue_id (to_issue_id),
    UNIQUE KEY uk_relation (from_issue_id, to_issue_id, relation_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Issue关联关系表';

-- 3. 评论表
CREATE TABLE IF NOT EXISTS comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    comment_id INT NOT NULL UNIQUE COMMENT 'GitHub Comment ID',
    issue_id INT NOT NULL COMMENT 'Issue的GitHub ID',
    issue_number INT NOT NULL COMMENT 'Issue编号',
    author VARCHAR(100) NOT NULL COMMENT '作者',
    body TEXT NOT NULL COMMENT '评论内容',
    created_at DATETIME COMMENT '创建时间',
    created_at_db DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '数据库创建时间',
    INDEX idx_comment_id (comment_id),
    INDEX idx_issue_id (issue_id),
    INDEX idx_issue_number (issue_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='评论表';

-- ============================================
-- 表创建完成
-- ============================================
