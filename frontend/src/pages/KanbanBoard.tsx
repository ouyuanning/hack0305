import { useEffect, useState, useMemo, useCallback } from 'react';
import {
  Row,
  Col,
  Card,
  Avatar,
  Badge,
  Progress,
  Select,
  Statistic,
  Spin,
  Alert,
  Button,
  Typography,
  Empty,
  Tag,
} from 'antd';
import { ReloadOutlined, UserOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { fetchIssues } from '@/api/issues';
import { useAppStore } from '@/stores/appStore';
import type { Issue } from '@/types';

const { Title, Text } = Typography;

const COLUMNS: { key: string; label: string; color: string }[] = [
  { key: '待处理', label: '待处理', color: '#faad14' },
  { key: '处理中', label: '处理中', color: '#1677ff' },
  { key: '已完成', label: '已完成', color: '#52c41a' },
  { key: '已关闭', label: '已关闭', color: '#8c8c8c' },
];

const PRIORITY_COLORS: Record<string, string> = {
  critical: 'red',
  high: 'orange',
  medium: 'blue',
  low: 'green',
  P0: 'red',
  P1: 'orange',
  P2: 'blue',
  P3: 'green',
};

function getPriorityColor(priority: string): string {
  if (!priority) return 'default';
  const lower = priority.toLowerCase();
  for (const [key, color] of Object.entries(PRIORITY_COLORS)) {
    if (lower === key.toLowerCase()) return color;
  }
  return 'default';
}

function IssueCard({ issue, onClick }: { issue: Issue; onClick: () => void }) {
  const priorityColor = getPriorityColor(issue.priority);
  const initials = issue.assignee
    ? issue.assignee.slice(0, 2).toUpperCase()
    : '';

  return (
    <Card
      size="small"
      hoverable
      onClick={onClick}
      style={{ marginBottom: 8, cursor: 'pointer' }}
      styles={{ body: { padding: '10px 12px' } }}
    >
      <div style={{ marginBottom: 6 }}>
        <Text strong style={{ fontSize: 13, lineHeight: '1.4' }}>
          #{issue.issue_number} {issue.title}
        </Text>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {issue.assignee ? (
            <Avatar size={20} style={{ backgroundColor: '#1677ff', fontSize: 10 }}>
              {initials}
            </Avatar>
          ) : (
            <Avatar size={20} icon={<UserOutlined />} style={{ backgroundColor: '#d9d9d9' }} />
          )}
          <Text type="secondary" style={{ fontSize: 12 }}>
            {issue.assignee || '未分配'}
          </Text>
        </div>
        {issue.priority && (
          <Badge
            color={priorityColor}
            text={
              <Text style={{ fontSize: 11, color: '#666' }}>{issue.priority}</Text>
            }
          />
        )}
      </div>

      <Progress
        percent={issue.progress_percentage ?? 0}
        size="small"
        strokeColor={issue.progress_percentage >= 100 ? '#52c41a' : '#1677ff'}
        format={(p) => `${p}%`}
        style={{ marginBottom: 0 }}
      />
    </Card>
  );
}

export default function KanbanBoard() {
  const navigate = useNavigate();
  const { currentRepo } = useAppStore();

  const [issues, setIssues] = useState<Issue[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [projectFilter, setProjectFilter] = useState<string | undefined>(undefined);
  const [customerFilter, setCustomerFilter] = useState<string | undefined>(undefined);

  const loadIssues = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchIssues({
        page: 1,
        page_size: 500,
        repo_owner: currentRepo.owner,
        repo_name: currentRepo.name,
      });
      setIssues(res.items ?? []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '加载看板数据失败';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [currentRepo.owner, currentRepo.name]);

  useEffect(() => {
    loadIssues();
  }, [loadIssues]);

  // Extract unique project/ and customer/ labels
  const projectLabels = useMemo(() => {
    const set = new Set<string>();
    issues.forEach((issue) =>
      issue.labels?.forEach((l) => {
        if (l.startsWith('project/')) set.add(l);
      }),
    );
    return Array.from(set).sort().map((l) => ({ label: l, value: l }));
  }, [issues]);

  const customerLabels = useMemo(() => {
    const set = new Set<string>();
    issues.forEach((issue) =>
      issue.labels?.forEach((l) => {
        if (l.startsWith('customer/')) set.add(l);
      }),
    );
    return Array.from(set).sort().map((l) => ({ label: l, value: l }));
  }, [issues]);

  // Apply filters
  const filteredIssues = useMemo(() => {
    return issues.filter((issue) => {
      if (projectFilter && !issue.labels?.includes(projectFilter)) return false;
      if (customerFilter && !issue.labels?.includes(customerFilter)) return false;
      return true;
    });
  }, [issues, projectFilter, customerFilter]);

  // Stats
  const stats = useMemo(() => {
    const total = filteredIssues.length;
    if (total === 0) return { completionRate: 0, avgProgress: 0, total };
    const closed = filteredIssues.filter((i) => i.status === '已关闭').length;
    const completionRate = Math.round((closed / total) * 100);
    const avgProgress = Math.round(
      filteredIssues.reduce((sum, i) => sum + (i.progress_percentage ?? 0), 0) / total,
    );
    return { completionRate, avgProgress, total };
  }, [filteredIssues]);

  // Group by status
  const columnIssues = useMemo(() => {
    const map: Record<string, Issue[]> = {};
    COLUMNS.forEach((col) => {
      map[col.key] = filteredIssues.filter((i) => i.status === col.key);
    });
    return map;
  }, [filteredIssues]);

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>
        看板视图
      </Title>

      {error && (
        <Alert
          type="error"
          description={error}
          showIcon
          closable
          style={{ marginBottom: 16 }}
          action={
            <Button size="small" icon={<ReloadOutlined />} onClick={loadIssues}>
              重试
            </Button>
          }
        />
      )}

      {/* Filters */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} md={6}>
          <Select
            style={{ width: '100%' }}
            placeholder="project/ 标签筛选"
            value={projectFilter}
            onChange={(v) => setProjectFilter(v)}
            options={projectLabels}
            allowClear
            showSearch
          />
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Select
            style={{ width: '100%' }}
            placeholder="customer/ 标签筛选"
            value={customerFilter}
            onChange={(v) => setCustomerFilter(v)}
            options={customerLabels}
            allowClear
            showSearch
          />
        </Col>
        <Col xs={24} sm={24} md={12} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {projectFilter && (
            <Tag color="cyan" closable onClose={() => setProjectFilter(undefined)}>
              {projectFilter}
            </Tag>
          )}
          {customerFilter && (
            <Tag color="orange" closable onClose={() => setCustomerFilter(undefined)}>
              {customerFilter}
            </Tag>
          )}
        </Col>
      </Row>

      {/* Stats bar */}
      <Row gutter={16} style={{ marginBottom: 20 }}>
        <Col xs={8} sm={6} md={4}>
          <Statistic title="总 Issue" value={stats.total} />
        </Col>
        <Col xs={8} sm={6} md={4}>
          <Statistic title="完成率" value={stats.completionRate} suffix="%" />
        </Col>
        <Col xs={8} sm={6} md={4}>
          <Statistic title="平均进度" value={stats.avgProgress} suffix="%" />
        </Col>
      </Row>

      {/* Kanban columns */}
      <Spin spinning={loading}>
        <Row gutter={12} align="top">
          {COLUMNS.map((col) => {
            const colIssues = columnIssues[col.key] ?? [];
            return (
              <Col key={col.key} xs={24} sm={12} md={6} style={{ marginBottom: 16 }}>
                <Card
                  title={
                    <span>
                      <span
                        style={{
                          display: 'inline-block',
                          width: 10,
                          height: 10,
                          borderRadius: '50%',
                          backgroundColor: col.color,
                          marginRight: 8,
                        }}
                      />
                      {col.label}
                      <Badge
                        count={colIssues.length}
                        style={{ backgroundColor: col.color, marginLeft: 8 }}
                        overflowCount={999}
                      />
                    </span>
                  }
                  size="small"
                  styles={{
                    header: { backgroundColor: '#fafafa', borderBottom: `2px solid ${col.color}` },
                    body: { padding: '8px', minHeight: 200, backgroundColor: '#f5f5f5' },
                  }}
                >
                  {colIssues.length === 0 ? (
                    <Empty
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                      description="暂无 Issue"
                      style={{ margin: '20px 0' }}
                    />
                  ) : (
                    colIssues.map((issue) => (
                      <IssueCard
                        key={issue.issue_number}
                        issue={issue}
                        onClick={() => navigate(`/issues/${issue.issue_number}`)}
                      />
                    ))
                  )}
                </Card>
              </Col>
            );
          })}
        </Row>
      </Spin>
    </div>
  );
}
