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
  Statistic,
  Space,
} from 'antd';
import {
  ReloadOutlined,
  HomeOutlined,
  BugOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { useNavigate, useParams, useSearchParams, Link } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import ReactECharts from 'echarts-for-react';
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

// ---- Daily Report ----
function DailyReport({ data }: { data: Record<string, unknown> }) {
  const summary = (data.summary ?? {}) as Record<string, number>;
  const date = data.date as string;

  return (
    <div>
      {date && (
        <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
          报告日期：{date}
        </Text>
      )}
      <Row gutter={[16, 16]}>
        <Col xs={12} sm={8} md={4}>
          <Card>
            <Statistic title="Issue 总数" value={summary.total_issues ?? 0} prefix={<BugOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card>
            <Statistic title="Open" value={summary.open_issues ?? 0} valueStyle={{ color: '#cf1322' }} prefix={<ExclamationCircleOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card>
            <Statistic title="Closed" value={summary.closed_issues ?? 0} valueStyle={{ color: '#3f8600' }} prefix={<CheckCircleOutlined />} />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card>
            <Statistic title="今日新增" value={summary.new_today ?? 0} valueStyle={{ color: '#1677ff' }} />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card>
            <Statistic title="今日关闭" value={summary.closed_today ?? 0} valueStyle={{ color: '#3f8600' }} />
          </Card>
        </Col>
        <Col xs={12} sm={8} md={4}>
          <Card>
            <Statistic title="阻塞中" value={summary.blocked_issues ?? 0} valueStyle={{ color: '#faad14' }} prefix={<WarningOutlined />} />
          </Card>
        </Col>
      </Row>
      <Card style={{ marginTop: 16 }}>
        <Progress
          percent={
            (summary.total_issues ?? 0) > 0
              ? Math.round(((summary.closed_issues ?? 0) / (summary.total_issues ?? 1)) * 100)
              : 0
          }
          strokeColor="#3f8600"
          format={(p) => `已关闭 ${p}%`}
        />
      </Card>
    </div>
  );
}

// ---- Extensible Analysis Report ----
function ExtensibleReport({ data }: { data: Record<string, unknown> }) {
  const results = (data.analysis_results ?? {}) as Record<string, unknown>;
  const basicStats = (results.basic_stats ?? {}) as Record<string, unknown>;
  const byType = (basicStats.by_type ?? {}) as Record<string, { count: number; percentage: number }>;
  const byPriority = (basicStats.by_priority ?? {}) as Record<string, { count: number; percentage: number }>;
  const byState = (basicStats.by_state ?? {}) as Record<string, { count: number; percentage: number }>;
  const labelAnalysis = (results.label_analysis ?? {}) as Record<string, unknown>;
  const labelDist = (labelAnalysis.label_distribution ?? {}) as Record<string, { count: number; open: number; closed: number; percentage: number }>;
  const moduleAnalysis = (results.module_analysis ?? {}) as Record<string, unknown>;
  const topModules = (moduleAnalysis.top_modules ?? []) as Array<Record<string, unknown>>;
  const trendAnalysis = (results.trend_analysis ?? {}) as Record<string, unknown>;
  const byWindow = (trendAnalysis.by_window ?? {}) as Record<string, Record<string, number>>;
  const relationAnalysis = (results.relation_analysis ?? {}) as Record<string, unknown>;
  const mostReferenced = (relationAnalysis.most_referenced ?? []) as Array<Record<string, unknown>>;
  const topCombos = (labelAnalysis.top_label_combinations ?? []) as Array<{ count: number; labels: string[] }>;

  const typeChartOption = {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical' as const, right: 10, top: 'center' },
    series: [{
      type: 'pie', radius: ['40%', '70%'],
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 13, fontWeight: 'bold' } },
      data: Object.entries(byType).map(([name, v]) => ({ name, value: v.count })),
    }],
  };

  const priorityChartOption = {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    color: ['#ff4d4f', '#faad14', '#52c41a', '#1677ff'],
    series: [{
      type: 'pie', radius: ['40%', '70%'],
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 13, fontWeight: 'bold' } },
      data: Object.entries(byPriority).map(([name, v]) => ({ name, value: v.count })),
    }],
  };

  const topLabels = Object.entries(labelDist)
    .sort((a, b) => b[1].count - a[1].count)
    .slice(0, 15);

  const labelBarOption = {
    tooltip: { trigger: 'axis' as const },
    xAxis: { type: 'category' as const, data: topLabels.map(([l]) => l), axisLabel: { rotate: 40, fontSize: 10 } },
    yAxis: { type: 'value' as const },
    series: [
      { name: 'Open', type: 'bar', stack: 'total', data: topLabels.map(([, v]) => v.open), itemStyle: { color: '#ff4d4f' } },
      { name: 'Closed', type: 'bar', stack: 'total', data: topLabels.map(([, v]) => v.closed), itemStyle: { color: '#52c41a' } },
    ],
    legend: { data: ['Open', 'Closed'] },
    grid: { left: '3%', right: '4%', bottom: '20%', containLabel: true },
  };

  const moduleColumns: ColumnsType<Record<string, unknown>> = [
    { title: '模块', dataIndex: 'module', key: 'module' },
    { title: '总计', dataIndex: 'total_issues', key: 'total_issues', width: 70 },
    { title: 'Open', dataIndex: 'open_issues', key: 'open_issues', width: 70, render: (v) => <Text style={{ color: '#cf1322' }}>{v}</Text> },
    { title: 'Bug 数', dataIndex: 'bug_count', key: 'bug_count', width: 80 },
    { title: '平均解决天数', dataIndex: 'avg_resolution_days', key: 'avg_resolution_days', width: 120, render: (v) => Number(v) > 0 ? `${Number(v).toFixed(0)} 天` : '-' },
    {
      title: '热度', dataIndex: 'hot_level', key: 'hot_level', width: 80,
      render: (v) => <Tag color={v === 'high' ? 'red' : v === 'medium' ? 'orange' : 'default'}>{v}</Tag>,
    },
  ];

  const windows = Object.entries(byWindow);

  return (
    <div>
      {/* Summary stats */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        {Object.entries(byState).map(([state, v]) => (
          <Col xs={12} sm={6} key={state}>
            <Card>
              <Statistic
                title={state === 'open' ? 'Open' : 'Closed'}
                value={v.count}
                suffix={`(${v.percentage.toFixed(1)}%)`}
                valueStyle={{ color: state === 'open' ? '#cf1322' : '#3f8600' }}
              />
            </Card>
          </Col>
        ))}
        <Col xs={12} sm={6}>
          <Card><Statistic title="Issue 总数" value={basicStats.total_issues as number ?? 0} /></Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card><Statistic title="标签种类" value={(labelAnalysis.total_unique_labels as number) ?? 0} /></Card>
        </Col>
      </Row>

      {/* Type + Priority pie charts */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} md={12}>
          <Card title="Issue 类型分布">
            <ReactECharts option={typeChartOption} style={{ height: 280 }} />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="优先级分布">
            <ReactECharts option={priorityChartOption} style={{ height: 280 }} />
          </Card>
        </Col>
      </Row>

      {/* Label bar chart */}
      {topLabels.length > 0 && (
        <Card title="Top 15 标签分布（Open / Closed）" style={{ marginBottom: 16 }}>
          <ReactECharts option={labelBarOption} style={{ height: 300 }} />
        </Card>
      )}

      {/* Trend windows */}
      {windows.length > 0 && (
        <Card title="趋势分析" style={{ marginBottom: 16 }}>
          <Row gutter={[16, 16]}>
            {windows.map(([window, stats]) => (
              <Col xs={24} sm={8} key={window}>
                <Card size="small" title={window === 'last_7d' ? '近 7 天' : window === 'last_30d' ? '近 30 天' : '近 90 天'}>
                  <Space direction="vertical" size={2} style={{ width: '100%' }}>
                    <Text>新增：<Text strong style={{ color: '#1677ff' }}>{stats.new_issues}</Text></Text>
                    <Text>关闭：<Text strong style={{ color: '#3f8600' }}>{stats.closed_issues}</Text></Text>
                    <Text>净变化：<Text strong style={{ color: (stats.net_change ?? 0) < 0 ? '#3f8600' : '#cf1322' }}>{stats.net_change > 0 ? '+' : ''}{stats.net_change}</Text></Text>
                    <Text>平均解决：<Text strong>{stats.avg_resolution_days?.toFixed(0)} 天</Text></Text>
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>
        </Card>
      )}

      {/* Top modules */}
      {topModules.length > 0 && (
        <Card title="模块分析" style={{ marginBottom: 16 }}>
          <Table
            columns={moduleColumns}
            dataSource={topModules.slice(0, 10)}
            rowKey={(_, i) => String(i)}
            pagination={false}
            size="small"
            scroll={{ x: 600 }}
          />
        </Card>
      )}

      {/* Most referenced issues */}
      {mostReferenced.length > 0 && (
        <Card title="被引用最多的 Issue" style={{ marginBottom: 16 }}>
          <List
            dataSource={mostReferenced}
            size="small"
            renderItem={(item) => (
              <List.Item>
                <Space>
                  <Tag color="blue">引用 {String(item.count)} 次</Tag>
                  <IssueLink issueNumber={item.issue_number as number} />
                  <Text ellipsis style={{ maxWidth: 400 }}>{String(item.title ?? '')}</Text>
                </Space>
              </List.Item>
            )}
          />
        </Card>
      )}

      {/* Top label combos */}
      {topCombos.length > 0 && (
        <Card title="常见标签组合">
          <List
            dataSource={topCombos.slice(0, 8)}
            size="small"
            renderItem={(item) => (
              <List.Item>
                <Space wrap>
                  <Tag color="geekblue">{item.count} 个 Issue</Tag>
                  {item.labels.map((l) => <Tag key={l}>{l}</Tag>)}
                </Space>
              </List.Item>
            )}
          />
        </Card>
      )}
    </div>
  );
}

// ---- Comprehensive Report ----
function ComprehensiveReport({ data }: { data: Record<string, unknown> }) {
  const summary = (data.summary ?? {}) as Record<string, number>;
  const healthScores = (data.health_scores ?? []) as Array<Record<string, unknown>>;
  const blockers = (data.blockers ?? data.blocking_chains ?? []) as Array<Record<string, unknown>>;
  const aiSuggestions = (data.ai_suggestions ?? data.ai_advice ?? '') as string;

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        {[
          { title: 'Issue 总数', key: 'total_issues', color: undefined },
          { title: 'Open', key: 'open_issues', color: '#cf1322' },
          { title: 'Closed', key: 'closed_issues', color: '#3f8600' },
          { title: '阻塞中', key: 'blocked_issues', color: '#faad14' },
          { title: '客户数', key: 'customer_count', color: undefined },
        ].map(({ title, key, color }) => (
          <Col xs={12} sm={8} md={4} key={key}>
            <Card>
              <Statistic title={title} value={summary[key] ?? 0} valueStyle={color ? { color } : undefined} />
            </Card>
          </Col>
        ))}
      </Row>

      {healthScores.length > 0 && (
        <Card title="客户健康度" style={{ marginBottom: 16 }}>
          <Row gutter={[12, 12]}>
            {healthScores.map((hs, idx) => {
              const score = Number(hs.score ?? 0);
              const customer = String(hs.customer ?? hs.name ?? `客户 ${idx + 1}`);
              return (
                <Col xs={24} sm={12} md={8} lg={6} key={customer}>
                  <Card size="small" hoverable>
                    <Text strong>{customer}</Text>
                    <div style={{ marginTop: 8 }}>
                      <Progress type="circle" percent={Math.round(score)} size={72} strokeColor={getHealthColor(score)} />
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

      {blockers.length > 0 && (
        <Card title="阻塞链" style={{ marginBottom: 16 }}>
          <List
            dataSource={blockers}
            size="small"
            renderItem={(item, idx) => (
              <List.Item key={idx}>
                <List.Item.Meta
                  title={<span>{item.issue_number != null && <><IssueLink issueNumber={item.issue_number as number} />{' '}</>}{String(item.title ?? item.reason ?? '')}</span>}
                  description={item.blocked_reason ? String(item.blocked_reason) : undefined}
                />
              </List.Item>
            )}
          />
        </Card>
      )}

      {aiSuggestions && (
        <Alert type="info" message="AI 建议" description={<Paragraph style={{ marginBottom: 0, whiteSpace: 'pre-wrap' }}>{aiSuggestions}</Paragraph>} showIcon />
      )}

      {healthScores.length === 0 && blockers.length === 0 && !aiSuggestions && (
        <Alert type="info" message="暂无详细数据" description="综合报告数据为空，请确认已运行 WF-001 采集数据后再生成报告。" showIcon />
      )}
    </div>
  );
}

// ---- Risk Report ----
function RiskReport({ data }: { data: Record<string, unknown> }) {
  const summary = (data.summary ?? {}) as Record<string, number>;
  const risks = (data.risks ?? {}) as Record<string, unknown>;
  const highPriorityOpen = (risks.high_priority_open ?? []) as Array<Record<string, unknown>>;
  const longTimeOpen = (risks.long_time_open ?? []) as Array<Record<string, unknown>>;
  const blockedChain = (risks.blocked_chain ?? []) as Array<Record<string, unknown>>;

  const summaryItems = [
    { title: '高优先级未关闭', value: summary.total_high_priority_open ?? 0, color: '#cf1322', icon: <ExclamationCircleOutlined /> },
    { title: '长期未关闭', value: summary.total_long_time_open ?? 0, color: '#faad14', icon: <ClockCircleOutlined /> },
    { title: '阻塞链', value: summary.total_blocked ?? 0, color: '#ff4d4f', icon: <WarningOutlined /> },
    { title: '共用 Feature 风险', value: summary.total_shared_features ?? 0, color: '#722ed1', icon: <BugOutlined /> },
  ];

  const issueColumns: ColumnsType<Record<string, unknown>> = [
    { title: 'Issue', key: 'issue', width: 90, render: (_, r) => <IssueLink issueNumber={r.issue_number as number} /> },
    { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true },
    { title: '优先级', dataIndex: 'priority', key: 'priority', width: 90, render: (v) => v ? <Tag color="red">{String(v)}</Tag> : '-' },
    { title: '天数', dataIndex: 'days_open', key: 'days_open', width: 80, render: (v) => v != null ? `${v} 天` : '-' },
  ];

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        {summaryItems.map(({ title, value, color, icon }) => (
          <Col xs={12} sm={6} key={title}>
            <Card>
              <Statistic title={title} value={value} valueStyle={{ color }} prefix={icon} />
            </Card>
          </Col>
        ))}
      </Row>

      {highPriorityOpen.length > 0 && (
        <Card title="高优先级未关闭 Issue" style={{ marginBottom: 16 }}>
          <Table columns={issueColumns} dataSource={highPriorityOpen} rowKey={(_, i) => String(i)} pagination={false} size="small" scroll={{ x: 500 }} />
        </Card>
      )}

      {longTimeOpen.length > 0 && (
        <Card title="长期未关闭 Issue" style={{ marginBottom: 16 }}>
          <Table columns={issueColumns} dataSource={longTimeOpen} rowKey={(_, i) => String(i)} pagination={false} size="small" scroll={{ x: 500 }} />
        </Card>
      )}

      {blockedChain.length > 0 && (
        <Card title="阻塞链" style={{ marginBottom: 16 }}>
          <List
            dataSource={blockedChain}
            size="small"
            renderItem={(item, idx) => (
              <List.Item key={idx}>
                <Space>
                  <IssueLink issueNumber={item.issue_number as number} />
                  <Text>{String(item.title ?? '')}</Text>
                  {item.blocked_reason && <Tag color="red">{String(item.blocked_reason)}</Tag>}
                </Space>
              </List.Item>
            )}
          />
        </Card>
      )}

      {highPriorityOpen.length === 0 && longTimeOpen.length === 0 && blockedChain.length === 0 && (
        <Alert type="success" message="暂无风险项" description="当前没有检测到高优先级未关闭、长期未关闭或阻塞链问题。" showIcon />
      )}
    </div>
  );
}

// ---- Shared Features Report ----
function SharedFeaturesReport({ data }: { data: Record<string, unknown> }) {
  const sharedFeatures = (data.shared_features ?? data.features ?? []) as Array<Record<string, unknown>>;
  const highBugFeatures = (data.high_bug_features ?? data.bug_features ?? []) as Array<Record<string, unknown>>;
  const aiStrategic = (data.ai_strategic_suggestions ?? data.ai_suggestions ?? '') as string;

  const featureColumns: ColumnsType<Record<string, unknown>> = [
    { title: 'Feature', dataIndex: 'feature', key: 'feature', ellipsis: true },
    { title: '客户数', dataIndex: 'customer_count', key: 'customer_count', width: 90 },
    {
      title: '关联 Issues', dataIndex: 'issue_numbers', key: 'issue_numbers',
      render: (nums: unknown) => (Array.isArray(nums) ? nums : []).map((n) => (
        <span key={String(n)} style={{ marginRight: 4 }}><IssueLink issueNumber={n as number} /></span>
      )),
    },
  ];

  const bugColumns: ColumnsType<Record<string, unknown>> = [
    { title: 'Feature', dataIndex: 'feature', key: 'feature', ellipsis: true },
    { title: 'Bug 数量', dataIndex: 'bug_count', key: 'bug_count', width: 100 },
    {
      title: '关联 Issues', dataIndex: 'issue_numbers', key: 'issue_numbers',
      render: (nums: unknown) => (Array.isArray(nums) ? nums : []).map((n) => (
        <span key={String(n)} style={{ marginRight: 4 }}><IssueLink issueNumber={n as number} /></span>
      )),
    },
  ];

  return (
    <div>
      {sharedFeatures.length > 0 ? (
        <Card title="共用 Feature" style={{ marginBottom: 16 }}>
          <Table columns={featureColumns} dataSource={sharedFeatures} rowKey={(_, i) => String(i)} pagination={false} size="small" scroll={{ x: 500 }} />
        </Card>
      ) : (
        <Alert type="info" message="暂无共用 Feature 数据" showIcon style={{ marginBottom: 16 }} />
      )}

      {highBugFeatures.length > 0 && (
        <Card title="高 Bug Feature" style={{ marginBottom: 16 }}>
          <Table columns={bugColumns} dataSource={highBugFeatures} rowKey={(_, i) => String(i)} pagination={false} size="small" scroll={{ x: 500 }} />
        </Card>
      )}

      {aiStrategic && (
        <Alert type="warning" message="AI 战略建议" description={<Paragraph style={{ marginBottom: 0, whiteSpace: 'pre-wrap' }}>{aiStrategic}</Paragraph>} showIcon />
      )}
    </div>
  );
}

// ---- Main component ----
export default function ReportDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { currentRepo, setCurrentRepo } = useAppStore();

  // Pin repo to URL params so navigating back doesn't lose context
  const repoOwner = searchParams.get('repo_owner') || currentRepo.owner;
  const repoName = searchParams.get('repo_name') || currentRepo.name;

  const [detail, setDetail] = useState<ReportDetailType | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDetail = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetchReportDetail(id, repoOwner, repoName);
      setDetail(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '加载报告详情失败');
    } finally {
      setLoading(false);
    }
  }, [id, repoOwner, repoName]);

  useEffect(() => { loadDetail(); }, [loadDetail]);

  const meta = detail?.metadata;
  const reportType = meta?.type;
  const typeLabel = reportType ? (REPORT_TYPE_LABELS[reportType] ?? reportType) : '报告';

  const renderContent = () => {
    if (!detail) return null;
    const { data } = detail;
    switch (reportType) {
      case 'daily':       return <DailyReport data={data} />;
      case 'extensible':  return <ExtensibleReport data={data} />;
      case 'comprehensive': return <ComprehensiveReport data={data} />;
      case 'risk':        return <RiskReport data={data} />;
      case 'shared':      return <SharedFeaturesReport data={data} />;
      default:
        // progress / customer — try comprehensive renderer as fallback
        return <ComprehensiveReport data={data} />;
    }
  };

  if (loading && !detail) {
    return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" tip="加载中..." /></div>;
  }

  if (error && !detail) {
    return (
      <Alert type="error" message="加载失败" description={error} showIcon
        action={<Button icon={<ReloadOutlined />} onClick={loadDetail}>重试</Button>} />
    );
  }

  return (
    <div>
      <Breadcrumb
        style={{ marginBottom: 16 }}
        items={[
          { title: <span style={{ cursor: 'pointer' }}><HomeOutlined /></span>, onClick: () => navigate('/') },
          {
            title: <span style={{ cursor: 'pointer' }}>分析报告</span>,
            onClick: () => {
              setCurrentRepo(repoOwner, repoName);
              navigate('/reports');
            },
          },
          { title: typeLabel },
        ]}
      />

      <Title level={4} style={{ marginBottom: 16 }}>{typeLabel}</Title>

      {meta && (
        <Card style={{ marginBottom: 16 }}>
          <Descriptions size="small" column={{ xs: 1, sm: 2, md: 3 }}>
            <Descriptions.Item label="报告类型"><Tag color="blue">{typeLabel}</Tag></Descriptions.Item>
            <Descriptions.Item label="仓库">{meta.repo}</Descriptions.Item>
            <Descriptions.Item label="生成时间">
              {meta.generated_at ? dayjs(meta.generated_at).format('YYYY-MM-DD HH:mm') : '-'}
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      {error && (
        <Alert type="error" message={error} showIcon closable style={{ marginBottom: 16 }}
          action={<Button size="small" icon={<ReloadOutlined />} onClick={loadDetail}>重试</Button>} />
      )}

      <Spin spinning={loading}>{renderContent()}</Spin>
    </div>
  );
}
