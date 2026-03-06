import { useEffect, useState } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
  Tag,
  Card,
  Descriptions,
  Avatar,
  Spin,
  Alert,
  Button,
  Timeline,
  List,
  Typography,
  Space,
  Divider,
  Badge,
} from 'antd';
import {
  ArrowLeftOutlined,
  UserOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import dayjs from 'dayjs';
import { fetchIssueDetail } from '@/api/issues';
import { useAppStore } from '@/stores/appStore';
import type { Issue, Comment, Relation } from '@/types';

const { Title, Text } = Typography;

const LABEL_COLORS: Record<string, string> = {
  'kind/': 'blue',
  'area/': 'purple',
  'customer/': 'orange',
  'priority/': 'red',
  'project/': 'cyan',
};

function getLabelColor(label: string): string {
  for (const [prefix, color] of Object.entries(LABEL_COLORS)) {
    if (label.startsWith(prefix)) return color;
  }
  return 'default';
}

function formatTime(t: string | null | undefined): string {
  if (!t) return '-';
  return dayjs(t).format('YYYY-MM-DD HH:mm');
}

// Timeline event from backend is a free-form map
type TimelineEvent = Record<string, unknown>;

function getTimelineLabel(event: TimelineEvent): string {
  const type = (event.event as string) || (event.type as string) || '事件';
  const actor = (event.actor as string) || '';
  if (actor) return `${actor} ${type}`;
  return type;
}

function getTimelineTime(event: TimelineEvent): string {
  const t = (event.created_at as string) || (event.timestamp as string) || '';
  return t ? formatTime(t) : '';
}

export default function IssueDetail() {
  const { number } = useParams<{ number: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { currentRepo } = useAppStore();

  // Pin repo to URL params so switching repos in header doesn't break this page
  const repoOwner = searchParams.get('repo_owner') || currentRepo.owner;
  const repoName = searchParams.get('repo_name') || currentRepo.name;

  const [issue, setIssue] = useState<Issue | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [relations, setRelations] = useState<Relation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const issueNumber = number ? parseInt(number, 10) : NaN;

  const loadDetail = async () => {
    if (isNaN(issueNumber)) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetchIssueDetail(issueNumber, repoOwner, repoName);
      setIssue(res.issue);
      setComments(res.comments ?? []);
      setTimeline(res.timeline ?? []);
      setRelations(res.relations ?? []);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '加载 Issue 详情失败';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDetail();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [issueNumber, repoOwner, repoName]);

  return (
    <div style={{ maxWidth: 960, margin: '0 auto' }}>
      <Button
        icon={<ArrowLeftOutlined />}
        type="text"
        onClick={() => navigate(-1)}
        style={{ marginBottom: 16 }}
      >
        返回列表
      </Button>

      {error && (
        <Alert
          type="error"
          message={error}
          showIcon
          style={{ marginBottom: 16 }}
          action={
            <Button size="small" icon={<ReloadOutlined />} onClick={loadDetail}>
              重试
            </Button>
          }
        />
      )}

      <Spin spinning={loading}>
        {issue && (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            {/* Header */}
            <Card>
              <Space align="start" style={{ width: '100%', justifyContent: 'space-between' }}>
                <div style={{ flex: 1 }}>
                  <Title level={4} style={{ marginBottom: 8 }}>
                    <Text type="secondary" style={{ fontWeight: 'normal', marginRight: 8 }}>
                      #{issue.issue_number}
                    </Text>
                    {issue.title}
                  </Title>
                  <Space wrap>
                    <Tag color={issue.state === 'open' ? 'red' : 'green'}>
                      {issue.state === 'open' ? 'Open' : 'Closed'}
                    </Tag>
                    {issue.is_blocked && <Badge status="error" text="Blocked" />}
                    {issue.labels?.map((label) => (
                      <Tag key={label} color={getLabelColor(label)}>
                        {label}
                      </Tag>
                    ))}
                  </Space>
                </div>
              </Space>

              <Divider style={{ margin: '12px 0' }} />

              <Descriptions size="small" column={{ xs: 1, sm: 2, md: 3 }}>
                <Descriptions.Item label="负责人">
                  {issue.assignee ? (
                    <Space>
                      <Avatar size="small" icon={<UserOutlined />} />
                      {issue.assignee}
                    </Space>
                  ) : (
                    '-'
                  )}
                </Descriptions.Item>
                <Descriptions.Item label="状态">{issue.status || '-'}</Descriptions.Item>
                <Descriptions.Item label="进度">{issue.progress_percentage ?? 0}%</Descriptions.Item>
                <Descriptions.Item label="创建时间">
                  <Space>
                    <ClockCircleOutlined />
                    {formatTime(issue.created_at)}
                  </Space>
                </Descriptions.Item>
                <Descriptions.Item label="更新时间">{formatTime(issue.updated_at)}</Descriptions.Item>
                {issue.closed_at && (
                  <Descriptions.Item label="关闭时间">{formatTime(issue.closed_at)}</Descriptions.Item>
                )}
                {issue.blocked_reason && (
                  <Descriptions.Item label="阻塞原因" span={3}>
                    <Text type="danger">{issue.blocked_reason}</Text>
                  </Descriptions.Item>
                )}
              </Descriptions>
            </Card>

            {/* Body */}
            <Card title="正文">
              {issue.body ? (
                <div className="markdown-body">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{issue.body}</ReactMarkdown>
                </div>
              ) : (
                <Text type="secondary">暂无正文</Text>
              )}
            </Card>

            {/* AI Summary */}
            {issue.ai_summary && (
              <Card title="AI 摘要">
                <Text>{issue.ai_summary}</Text>
              </Card>
            )}

            {/* Relations */}
            {relations.length > 0 && (
              <Card title={`关联 Issue (${relations.length})`}>
                <List
                  size="small"
                  dataSource={relations}
                  renderItem={(rel) => (
                    <List.Item>
                      <Space>
                        <Tag>{rel.relation_type}</Tag>
                        <Button
                          type="link"
                          size="small"
                          style={{ padding: 0 }}
                          onClick={() => navigate(`/issues/${rel.to_issue_number}?repo_owner=${repoOwner}&repo_name=${repoName}`)}
                        >
                          #{rel.to_issue_number}
                        </Button>
                        {rel.relation_semantic && (
                          <Text type="secondary">{rel.relation_semantic}</Text>
                        )}
                        {rel.context_text && (
                          <Text type="secondary" ellipsis style={{ maxWidth: 300 }}>
                            {rel.context_text}
                          </Text>
                        )}
                      </Space>
                    </List.Item>
                  )}
                />
              </Card>
            )}

            {/* Timeline */}
            {timeline.length > 0 && (
              <Card title={`时间线 (${timeline.length})`}>
                <Timeline
                  items={timeline.map((event, idx) => ({
                    key: idx,
                    label: getTimelineTime(event),
                    children: getTimelineLabel(event),
                  }))}
                  mode="left"
                />
              </Card>
            )}

            {/* Comments */}
            <Card title={`评论 (${comments.length})`}>
              {comments.length === 0 ? (
                <Text type="secondary">暂无评论</Text>
              ) : (
                <List
                  dataSource={comments}
                  itemLayout="vertical"
                  renderItem={(comment) => (
                    <List.Item key={comment.comment_id}>
                      <List.Item.Meta
                        avatar={<Avatar icon={<UserOutlined />} />}
                        title={
                          <Space>
                            <Text strong>{comment.user}</Text>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {formatTime(comment.created_at)}
                            </Text>
                            {comment.updated_at !== comment.created_at && (
                              <Text type="secondary" style={{ fontSize: 12 }}>
                                (已编辑 {formatTime(comment.updated_at)})
                              </Text>
                            )}
                          </Space>
                        }
                      />
                      <div className="markdown-body" style={{ marginTop: 8 }}>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{comment.body}</ReactMarkdown>
                      </div>
                    </List.Item>
                  )}
                />
              )}
            </Card>
          </Space>
        )}

        {!loading && !error && !issue && (
          <Alert type="warning" message={`Issue #${issueNumber} 不存在`} showIcon />
        )}
      </Spin>
    </div>
  );
}
