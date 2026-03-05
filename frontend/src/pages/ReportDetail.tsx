import { useEffect, useState, useCallback } from 'react';
import {
  Card,
  Table,
  List,
  Alert,
  Spin,
  Button,
  Typography,
  Breadcrumb,
  Tag,
  Descriptions,
  Progress,
  Row,
  Col,
} from 'antd';
import { ReloadOutlined, HomeOutlined } from '@ant-design/icons';
import { useNavigate, useParams, Link } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { fetchReportDetail } from '@/api/reports';
import { useAppStore } from '@/stores/appStore';
import type { ReportDetail as ReportDetailType, Report } from '@/types';

const { Title, Text, Paragraph } = Typography;

const REPORT_TYPE_LABELS: Record<Report['type'], string> = {
  daily: '日报',
  progress: '项目推进分析',
  comprehensive: '综合分析',
  extensible: '可扩展分析',
  shared: '横向关联分析',
  risk: '风险分析',
  customer: '客户报告',
};

// ---- Sub-renderers ----

function IssueLink({ issueNumber }: { issueNumber: number | string }) {
  const num = Number(issueNumber);
  if (!num) return <span>{issueNumber}</span>;
  return <Link to={`/issues/${num}`}>#{num}</Link>;
}

function getHealthColor(score: number) {
  if (score >= 80) return '#52c41a';
  if (score >= 60) return '#faad14';
  return '#ff4d4f';
}

// Renders progress/comprehensive report
function ProgressReport({ data }: { data: Record<string, unknown> }) {
  const healthScores = (data.health_scores ?? data.customer_health ?? []) as Array<Record<string, unknown>>;
  const hierarchyStats = (data.hierarchy_stats ?? data.level_stats ?? []) as Array<Record<string, unknown>>;
  const blockers = (data.blockers ?? data.blocked_issues ?? []) as Array<Record<string, unknown>>;
  const aiSuggestions = (data.ai_suggestions ?? data.ai_advice ?? data.suggestions ?? '') as string;

  const hierarchyColumns: ColumnsType<Record<string, unknown>> = [
    { title: '层级', dataIndex: 'level', key: 'level', width: 100 },
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: '总计', dataIndex: 'total', key: 'total', width: 80 },
    { title: 'Open', dataIndex: 'open', key: 'open', width: 80 },
    { title: 'Closed', dataIndex: 'closed', key: 'closed', width: 80 },
    {
      title: '进度',
      key: 'progress',
      width: 120,
      render: (_, record) => {
        const total = Number(record.total) || 0;
        const closed = Number(record.closed) || 0;
        const pct = total > 0 ? Math.round((closed / total) * 100) : 0;
        return <Progress percent={pct} size="small" />;
      },
    },
  ];

  return (
    <div>
      {/* Health scores */}
      {healthScores.length > 0 && (
        <Card title="客户健康度评分" style={{ marginBottom: 16 }}>
          <Row gutter={[12, 12]}>
            {healthScores.map((hs, idx) => {
              const score = Number(hs.score ?? 0);
              const customer = String(hs.customer ?? hs.name ?? `客户 ${idx + 1}`);
              return (
                <Col xs={24} sm={12} md={8} lg={6} key={customer}>
                  <Card size="small" hoverable>
                    <Text strong>{customer}</Text>
                    <div style={{ marginTop: 8 }}>
                      <Progress
                        type="circle"
                        percent={Math.round(score)}
                        size={72}
                        strokeColor={getHealthColor(score)}
                      />
                    </div>
                    <div style={{ marginTop: 8 }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        总计: {String(hs.total_issues ?? '-')} | Open: {String(hs.open_issues ?? '-')} | 阻塞: {String(hs.blocked_issues ?? '-')}
                      </Text>
                    </div>
                  </Card>
                </Col>
              );
            })}
          </Row>
        </Card>
      )}

      {/* Hierarchy stats */}
      {hierarchyStats.length > 0 && (
        <Card title="层级统计" style={{ marginBottom: 16 }}>
          <Table
            columns={hierarchyColumns}
            dataSource={hierarchyStats}
            rowKey={(_, idx) => String(idx)}
            pagination={false}
            size="small"
            scroll={{ x: 500 }}
          />
        </Card>
      )}

      {/* Blockers */}
      {blockers.length > 0 && (
        <Card title="堵塞点" style={{ marginBottom: 16 }}>
          <List
            dataSource={blockers}
            renderItem={(item, idx) => (
              <List.Item key={idx}>
                <List.Item.Meta
                  title={
                    <span>
                      {item.issue_number != null && (
                        <>
                          <IssueLink issueNumber={item.issue_number as number} />
                          {' '}
                        </>
                      )}
                      {String(item.title ?? item.reason ?? '')}
                    </span>
                  }
                  description={item.blocked_reason ? String(item.blocked_reason) : undefined}
                />
              </List.Item>
            )}
          />
        </Card>
      )}

      {/* AI suggestions */}
      {aiSuggestions && (
        <Alert
          type="info"
          message="AI 建议"
          description={<Paragraph style={{ marginBottom: 0, whiteSpace: 'pre-wrap' }}>{aiSuggestions}</Paragraph>}
          showIcon
        />
      )}
    </div>
  );
}

// Renders shared/risk report
function SharedReport({ data }: { data: Record<string, unknown> }) {
  const sharedFeatures = (data.shared_features ?? data.common_features ?? []) as Array<Record<string, unknown>>;
  const highBugFeatures = (data.high_bug_features ?? data.bug_features ?? []) as Array<Record<string, unknown>>;
  const aiStrategic = (data.ai_strategic_suggestions ?? data.ai_suggestions ?? data.strategic_advice ?? '') as string;

  const featureColumns: ColumnsType<Record<string, unknown>> = [
    { title: 'Feature', dataIndex: 'feature', key: 'feature', ellipsis: true },
    { title: '客户数', dataIndex: 'customer_count', key: 'customer_count', width: 90 },
    {
      title: '关联 Issues',
      dataIndex: 'issue_numbers',
      key: 'issue_numbers',
      render: (nums: unknown) => {
        const arr = Array.isArray(nums) ? nums : [];
        return arr.map((n) => (
          <span key={String(n)} style={{ marginRight: 4 }}>
            <IssueLink issueNumber={n as number} />
          </span>
        ));
      },
    },
  ];

  const bugColumns: ColumnsType<Record<string, unknown>> = [
    { title: 'Feature', dataIndex: 'feature', key: 'feature', ellipsis: true },
    { title: 'Bug 数量', dataIndex: 'bug_count', key: 'bug_count', width: 100 },
    {
      title: '关联 Issues',
      dataIndex: 'issue_numbers',
      key: 'issue_numbers',
      render: (nums: unknown) => {
        const arr = Array.isArray(nums) ? nums : [];
        return arr.map((n) => (
          <span key={String(n)} style={{ marginRight: 4 }}>
            <IssueLink issueNumber={n as number} />
          </span>
        ));
      },
    },
  ];

  return (
    <div>
      {sharedFeatures.length > 0 && (
        <Card title="共用 Feature" style={{ marginBottom: 16 }}>
          <Table
            columns={featureColumns}
            dataSource={sharedFeatures}
            rowKey={(_, idx) => String(idx)}
            pagination={false}
            size="small"
            scroll={{ x: 500 }}
          />
        </Card>
      )}

      {highBugFeatures.length > 0 && (
        <Card title="高 Bug Feature" style={{ marginBottom: 16 }}>
          <Table
            columns={bugColumns}
            dataSource={highBugFeatures}
            rowKey={(_, idx) => String(idx)}
            pagination={false}
            size="small"
            scroll={{ x: 500 }}
          />
        </Card>
      )}

      {aiStrategic && (
        <Alert
          type="warning"
          message="AI 战略建议"
          description={<Paragraph style={{ marginBottom: 0, whiteSpace: 'pre-wrap' }}>{aiStrategic}</Paragraph>}
          showIcon
        />
      )}
    </div>
  );
}

// Generic JSON fallback renderer
function GenericReport({ data }: { data: Record<string, unknown> }) {
  return (
    <Card title="报告内容">
      <pre
        style={{
          background: '#f5f5f5',
          padding: 16,
          borderRadius: 6,
          overflow: 'auto',
          fontSize: 13,
          maxHeight: 600,
        }}
      >
        {JSON.stringify(data, null, 2)}
      </pre>
    </Card>
  );
}

// ---- Main component ----

export default function ReportDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentRepo } = useAppStore();

  const [detail, setDetail] = useState<ReportDetailType | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDetail = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetchReportDetail(id, currentRepo.owner, currentRepo.name);
      setDetail(res);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '加载报告详情失败';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [id, currentRepo.owner, currentRepo.name]);

  useEffect(() => {
    loadDetail();
  }, [loadDetail]);

  const meta = detail?.metadata;
  const reportType = meta?.type;
  const typeLabel = reportType ? (REPORT_TYPE_LABELS[reportType] ?? reportType) : '报告';

  const renderContent = () => {
    if (!detail) return null;
    const { data } = detail;

    if (reportType === 'progress' || reportType === 'comprehensive') {
      return <ProgressReport data={data} />;
    }
    if (reportType === 'shared' || reportType === 'risk') {
      return <SharedReport data={data} />;
    }
    // daily / extensible / customer → generic JSON view
    return <GenericReport data={data} />;
  };

  if (loading && !detail) {
    return (
      <div style={{ textAlign: 'center', padding: 80 }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  if (error && !detail) {
    return (
      <Alert
        type="error"
        message="加载失败"
        description={error}
        showIcon
        action={
          <Button icon={<ReloadOutlined />} onClick={loadDetail}>
            重试
          </Button>
        }
      />
    );
  }

  return (
    <div>
      <Breadcrumb
        style={{ marginBottom: 16 }}
        items={[
          { title: <HomeOutlined />, onClick: () => navigate('/'), href: '/' },
          { title: '分析报告', onClick: () => navigate('/reports'), href: '/reports' },
          { title: typeLabel },
        ]}
      />

      <Title level={4} style={{ marginBottom: 16 }}>
        {typeLabel}
      </Title>

      {meta && (
        <Card style={{ marginBottom: 16 }}>
          <Descriptions size="small" column={{ xs: 1, sm: 2, md: 3 }}>
            <Descriptions.Item label="报告类型">
              <Tag color="blue">{typeLabel}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="仓库">{meta.repo}</Descriptions.Item>
            <Descriptions.Item label="生成时间">
              {meta.generated_at ? dayjs(meta.generated_at).format('YYYY-MM-DD HH:mm') : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="文件名">{meta.filename}</Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      {error && (
        <Alert
          type="error"
          message={error}
          showIcon
          closable
          style={{ marginBottom: 16 }}
          action={
            <Button size="small" icon={<ReloadOutlined />} onClick={loadDetail}>
              重试
            </Button>
          }
        />
      )}

      <Spin spinning={loading}>{renderContent()}</Spin>
    </div>
  );
}
