import { useEffect, useState, useCallback } from 'react';
import {
  Row,
  Col,
  Card,
  Statistic,
  List,
  Alert,
  Button,
  Spin,
  Progress,
  Typography,
  Tag,
  Modal,
  Space,
  message,
} from 'antd';
import {
  ReloadOutlined,
  BugOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  PercentageOutlined,
  DeleteOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { useNavigate } from 'react-router-dom';
import { fetchOverview, fetchLabelsStats } from '@/api/issues';
import { resetSystem } from '@/api/system';
import { useAppStore } from '@/stores/appStore';
import type { OverviewResponse, LabelsResponse } from '@/types';

const { Title, Text } = Typography;

export default function Dashboard() {
  const navigate = useNavigate();
  const { currentRepo } = useAppStore();

  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [labelsData, setLabelsData] = useState<LabelsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resetting, setResetting] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [overviewRes, labelsRes] = await Promise.all([
        fetchOverview(currentRepo.owner, currentRepo.name),
        fetchLabelsStats(currentRepo.owner, currentRepo.name),
      ]);
      setOverview(overviewRes);
      setLabelsData(labelsRes);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '数据加载失败，请重试';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [currentRepo.owner, currentRepo.name]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleReset = () => {
    Modal.confirm({
      title: '确认重置系统',
      icon: <WarningOutlined style={{ color: '#ff4d4f' }} />,
      content: (
        <div>
          <p>此操作将清除所有数据，包括：</p>
          <ul>
            <li>本地报告文件</li>
            <li>MOI Volume 中的所有快照和分析数据</li>
            <li>工作流执行历史</li>
          </ul>
          <p style={{ color: '#ff4d4f', fontWeight: 'bold' }}>
            此操作不可恢复，请谨慎操作！
          </p>
        </div>
      ),
      okText: '确认重置',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        setResetting(true);
        try {
          const result = await resetSystem({ confirm: true });
          message.success(result.message || '系统重置成功');
          // Reload data after reset
          setTimeout(() => {
            loadData();
          }, 1000);
        } catch (err: unknown) {
          const msg = err instanceof Error ? err.message : '重置失败';
          message.error(msg);
        } finally {
          setResetting(false);
        }
      },
    });
  };

  const getLabelChartOption = () => {
    if (!labelsData?.groups) return {};

    const prefixes = Object.keys(labelsData.groups);
    const seriesData = prefixes.flatMap((prefix) =>
      labelsData.groups[prefix].map((item) => ({
        name: item.label,
        value: item.count,
      })),
    );

    return {
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: {
        type: 'scroll' as const,
        orient: 'vertical' as const,
        right: 10,
        top: 20,
        bottom: 20,
      },
      series: [
        {
          type: 'pie',
          radius: ['40%', '70%'],
          avoidLabelOverlap: false,
          itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
          label: { show: false },
          emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
          data: seriesData,
        },
      ],
    };
  };

  const getBarChartOption = () => {
    if (!labelsData?.groups) return {};

    const prefixes = Object.keys(labelsData.groups);
    const categories: string[] = [];
    const values: number[] = [];

    prefixes.forEach((prefix) => {
      labelsData.groups[prefix].forEach((item) => {
        categories.push(item.label);
        values.push(item.count);
      });
    });

    return {
      tooltip: { trigger: 'axis' as const },
      xAxis: {
        type: 'category' as const,
        data: categories,
        axisLabel: { rotate: 45, fontSize: 10 },
      },
      yAxis: { type: 'value' as const },
      series: [
        {
          type: 'bar',
          data: values,
          itemStyle: { borderRadius: [4, 4, 0, 0] },
        },
      ],
      grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    };
  };

  const getHealthColor = (score: number) => {
    if (score >= 80) return '#52c41a';
    if (score >= 60) return '#faad14';
    return '#ff4d4f';
  };

  if (loading && !overview) {
    return (
      <div style={{ textAlign: 'center', padding: 80 }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  if (error && !overview) {
    return (
      <Alert
        type="error"
        message="加载失败"
        description={error}
        showIcon
        action={
          <Button icon={<ReloadOutlined />} onClick={loadData}>
            重试
          </Button>
        }
      />
    );
  }

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={4} style={{ margin: 0 }}>
            Dashboard 总览
          </Title>
        </Col>
        <Col>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={loadData} loading={loading}>
              刷新
            </Button>
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={handleReset}
              loading={resetting}
            >
              重置系统
            </Button>
          </Space>
        </Col>
      </Row>

      {error && (
        <Alert
          type="error"
          message={error}
          showIcon
          closable
          style={{ marginBottom: 16 }}
          action={
            <Button size="small" icon={<ReloadOutlined />} onClick={loadData}>
              重试
            </Button>
          }
        />
      )}

      {/* 统计卡片区 */}
      <Spin spinning={loading}>
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={12} sm={12} md={6}>
            <Card hoverable>
              <Statistic
                title="Issue 总数"
                value={overview?.total ?? 0}
                prefix={<BugOutlined />}
              />
            </Card>
          </Col>
          <Col xs={12} sm={12} md={6}>
            <Card hoverable>
              <Statistic
                title="Open"
                value={overview?.open ?? 0}
                valueStyle={{ color: '#cf1322' }}
                prefix={<ExclamationCircleOutlined />}
              />
            </Card>
          </Col>
          <Col xs={12} sm={12} md={6}>
            <Card hoverable>
              <Statistic
                title="Closed"
                value={overview?.closed ?? 0}
                valueStyle={{ color: '#3f8600' }}
                prefix={<CheckCircleOutlined />}
              />
            </Card>
          </Col>
          <Col xs={12} sm={12} md={6}>
            <Card hoverable>
              <Statistic
                title="Open 占比"
                value={overview?.open_ratio ?? 0}
                precision={2}
                suffix="%"
                prefix={<PercentageOutlined />}
              />
            </Card>
          </Col>
        </Row>

        {/* 图表区 */}
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} md={12}>
            <Card title="Labels 分布（饼图）">
              {labelsData && Object.keys(labelsData.groups).length > 0 ? (
                <ReactECharts option={getLabelChartOption()} style={{ height: 350 }} />
              ) : (
                <Text type="secondary">暂无标签数据</Text>
              )}
            </Card>
          </Col>
          <Col xs={24} md={12}>
            <Card title="Labels 分布（柱状图）">
              {labelsData && Object.keys(labelsData.groups).length > 0 ? (
                <ReactECharts option={getBarChartOption()} style={{ height: 350 }} />
              ) : (
                <Text type="secondary">暂无标签数据</Text>
              )}
            </Card>
          </Col>
        </Row>

        {/* 最近更新列表 + 健康度摘要 */}
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={14}>
            <Card title="最近 7 天更新的 Issue">
              <List
                dataSource={overview?.recent_issues ?? []}
                locale={{ emptyText: '暂无最近更新的 Issue' }}
                renderItem={(issue) => (
                  <List.Item
                    key={issue.issue_number}
                    style={{ cursor: 'pointer' }}
                    onClick={() => navigate(`/issues/${issue.issue_number}`)}
                  >
                    <List.Item.Meta
                      title={
                        <span>
                          <Tag color={issue.state === 'open' ? 'red' : 'green'}>
                            {issue.state}
                          </Tag>
                          #{issue.issue_number} {issue.title}
                        </span>
                      }
                      description={
                        <span>
                          {issue.assignee && (
                            <Text type="secondary" style={{ marginRight: 12 }}>
                              负责人: {issue.assignee}
                            </Text>
                          )}
                          <Text type="secondary">
                            更新于: {new Date(issue.updated_at).toLocaleDateString()}
                          </Text>
                        </span>
                      }
                    />
                  </List.Item>
                )}
              />
            </Card>
          </Col>
          <Col xs={24} lg={10}>
            <Card title="客户项目健康度">
              {overview?.health_scores && overview.health_scores.length > 0 ? (
                <Row gutter={[12, 12]}>
                  {overview.health_scores.map((hs) => (
                    <Col xs={24} sm={12} key={hs.customer}>
                      <Card size="small" hoverable>
                        <div style={{ marginBottom: 8 }}>
                          <Text strong>{hs.customer}</Text>
                        </div>
                        <Progress
                          type="circle"
                          percent={Math.round(hs.score)}
                          size={80}
                          strokeColor={getHealthColor(hs.score)}
                        />
                        <div style={{ marginTop: 8 }}>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            总计: {hs.total_issues} | Open: {hs.open_issues} | 阻塞: {hs.blocked_issues}
                          </Text>
                        </div>
                      </Card>
                    </Col>
                  ))}
                </Row>
              ) : (
                <Text type="secondary">暂无健康度数据</Text>
              )}
            </Card>
          </Col>
        </Row>
      </Spin>
    </div>
  );
}
