import { useEffect, useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Badge,
  Button,
  DatePicker,
  Form,
  Input,
  Switch,
  Tag,
  Alert,
  Spin,
  Typography,
  Space,
  Row,
  Col,
  Collapse,
  Statistic,
} from 'antd';
import {
  PlayCircleOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  BookOutlined,
  EditOutlined,
  ClearOutlined,
  SyncOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { fetchWorkflows, triggerWorkflow, fetchWorkflowStatus } from '@/api/workflows';
import { useAppStore } from '@/stores/appStore';
import type { WorkflowDef, WorkflowExecution } from '@/types';

const { Title, Text } = Typography;
const { Panel } = Collapse;

const POLL_INTERVAL_MS = 2000;

// Status display config
const STATUS_TAG: Record<WorkflowExecution['status'], { color: string; label: string }> = {
  queued: { color: 'orange', label: '排队中' },
  running: { color: 'processing', label: '执行中' },
  completed: { color: 'success', label: '已完成' },
  failed: { color: 'error', label: '失败' },
};

// ---------- Workflow-specific result summaries ----------

function WorkflowResultSummary({ workflowType, result }: { workflowType?: string; result: Record<string, unknown> }) {
  const navigate = useNavigate();
  const repo = result['repo'] as string | undefined;
  const boxStyle: React.CSSProperties = {
    marginTop: 12,
    padding: '16px 20px',
    background: '#f6ffed',
    border: '1px solid #b7eb8f',
    borderRadius: 8,
  };

  switch (workflowType) {
    case 'WF-001': {
      const issueCount = Number(result['issue_count'] ?? 0);
      const commentCount = Number(result['comment_count'] ?? 0);
      const aiParsed = Number(result['ai_parsed'] ?? 0);
      const relationCount = Number(result['relation_count'] ?? 0);
      return (
        <div style={boxStyle}>
          <Space align="center" style={{ marginBottom: 12 }}>
            <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 18 }} />
            <Text strong>Issue 数据采集完成</Text>
            {repo && <Tag>{repo}</Tag>}
          </Space>
          <Row gutter={24}>
            <Col><Statistic title="采集 Issue" value={issueCount} prefix={<DatabaseOutlined />} /></Col>
            <Col><Statistic title="评论" value={commentCount} /></Col>
            <Col><Statistic title="AI 解析" value={aiParsed} /></Col>
            <Col><Statistic title="关联关系" value={relationCount} /></Col>
          </Row>
        </div>
      );
    }
    case 'WF-002': {
      const sectionCount = Number(result['section_count'] ?? 0);
      const contentLen = Number(result['content_length'] ?? 0);
      const sizeKB = (contentLen / 1024).toFixed(1);
      return (
        <div style={boxStyle}>
          <Space align="center" style={{ marginBottom: 12 }}>
            <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 18 }} />
            <Text strong>知识库生成完成</Text>
            {repo && <Tag>{repo}</Tag>}
          </Space>
          <Row gutter={24}>
            <Col><Statistic title="知识章节" value={sectionCount} prefix={<BookOutlined />} /></Col>
            <Col><Statistic title="内容大小" value={sizeKB} suffix="KB" prefix={<FileTextOutlined />} /></Col>
          </Row>
        </div>
      );
    }
    case 'WF-003': {
      const draftTitle = result['draft_title'] as string || '(无标题)';
      const labelCount = Number(result['label_count'] ?? 0);
      const templateType = result['template_type'] as string || '';
      const handleViewDraft = () => {
        navigate('/create-issue', {
          state: {
            draft: {
              title: result['draft_title'] ?? '',
              body: result['draft_body'] ?? '',
              labels: result['draft_labels'] ?? [],
              assignees: result['draft_assignees'] ?? [],
              template_type: result['template_type'] ?? '',
            },
          },
        });
      };
      return (
        <div style={boxStyle}>
          <Space align="center" style={{ marginBottom: 12 }}>
            <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 18 }} />
            <Text strong>Issue 草稿已生成</Text>
            {repo && <Tag>{repo}</Tag>}
          </Space>
          <div style={{ marginTop: 8 }}>
            <Space direction="vertical" size={4}>
              <Text><EditOutlined style={{ marginRight: 6 }} />草稿标题：<Text strong>{draftTitle}</Text></Text>
              {templateType && <Text>模板类型：<Tag color="blue">{templateType}</Tag></Text>}
              <Text>标签数量：{labelCount}</Text>
            </Space>
          </div>
          <div style={{ marginTop: 16 }}>
            <Button type="primary" icon={<EditOutlined />} onClick={handleViewDraft}>
              查看并编辑草稿
            </Button>
          </div>
        </div>
      );
    }
    case 'WF-005': {
      const totalIssues = Number(result['total_issues'] ?? 0);
      const cleanedCount = Number(result['cleaned_count'] ?? 0);
      return (
        <div style={boxStyle}>
          <Space align="center" style={{ marginBottom: 12 }}>
            <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 18 }} />
            <Text strong>历史数据清洗完成</Text>
            {repo && <Tag>{repo}</Tag>}
          </Space>
          <Row gutter={24}>
            <Col><Statistic title="Issue 总数" value={totalIssues} prefix={<DatabaseOutlined />} /></Col>
            <Col><Statistic title="本次补全" value={cleanedCount} prefix={<ClearOutlined />} /></Col>
          </Row>
        </div>
      );
    }
    case 'WF-006': {
      const trackedCount = Number(result['tracked_count'] ?? 0);
      const openCount = Number(result['open_count'] ?? 0);
      const closedCount = Number(result['closed_count'] ?? 0);
      return (
        <div style={boxStyle}>
          <Space align="center" style={{ marginBottom: 12 }}>
            <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 18 }} />
            <Text strong>状态记录完成</Text>
            {repo && <Tag>{repo}</Tag>}
          </Space>
          <Row gutter={24}>
            <Col><Statistic title="跟踪 Issue" value={trackedCount} prefix={<SyncOutlined />} /></Col>
            <Col><Statistic title="Open" value={openCount} valueStyle={{ color: '#52c41a' }} /></Col>
            <Col><Statistic title="Closed" value={closedCount} valueStyle={{ color: '#8c8c8c' }} /></Col>
          </Row>
        </div>
      );
    }
    case 'WF-007': {
      const reportCount = Number(result['report_count'] ?? 0);
      const reportTypes = (result['report_types'] as string[]) ?? [];
      return (
        <div style={boxStyle}>
          <Space align="center" style={{ marginBottom: 12 }}>
            <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 18 }} />
            <Text strong>分析报告生成完成</Text>
            {repo && <Tag>{repo}</Tag>}
          </Space>
          <Row gutter={24}>
            <Col><Statistic title="报告数量" value={reportCount} prefix={<BarChartOutlined />} /></Col>
          </Row>
          {reportTypes.length > 0 && (
            <div style={{ marginTop: 8 }}>
              {reportTypes.map((t) => <Tag key={t} color="geekblue" style={{ marginBottom: 4 }}>{t}</Tag>)}
            </div>
          )}
        </div>
      );
    }
    default:
      // Fallback for unknown workflow types
      return (
        <Alert
          type="success"
          message="工作流执行完成"
          showIcon
          style={{ marginTop: 12 }}
        />
      );
  }
}

// ---------- WorkflowCard ----------

interface WorkflowCardProps {
  workflow: WorkflowDef;
  execution: WorkflowExecution | null;
  onTrigger: (workflowId: string, values: Record<string, unknown>) => Promise<void>;
  triggering: boolean;
  defaultOwner: string;
  defaultName: string;
}

function WorkflowCard({
  workflow,
  execution,
  onTrigger,
  triggering,
  defaultOwner,
  defaultName,
}: WorkflowCardProps) {
  const [form] = Form.useForm();
  const isActive = execution?.status === 'queued' || execution?.status === 'running';

  // Pre-fill repo fields when defaults change
  useEffect(() => {
    const patch: Record<string, unknown> = {};
    if (defaultOwner) patch['repo_owner'] = defaultOwner;
    if (defaultName) patch['repo_name'] = defaultName;
    if (Object.keys(patch).length > 0) form.setFieldsValue(patch);
  }, [defaultOwner, defaultName, form]);

  const handleSubmit = async () => {
    try {
      const raw = await form.validateFields();
      // Convert dayjs datetime values to ISO strings for the API
      const values: Record<string, unknown> = {};
      for (const [key, val] of Object.entries(raw)) {
        if (val && typeof val === 'object' && typeof (val as { toISOString?: unknown }).toISOString === 'function') {
          values[key] = (val as { toISOString: () => string }).toISOString();
        } else {
          values[key] = val;
        }
      }
      await onTrigger(workflow.id, values);
    } catch {
      // validation error — antd shows inline messages
    }
  };

  const statusInfo = execution ? STATUS_TAG[execution.status] : null;

  // Build result entries for Descriptions
  const result = execution?.result ?? {};
  const workflowType = result['workflow_type'] as string | undefined;

  return (
    <Card
      style={{ marginBottom: 16 }}
      title={
        <Space>
          <Text strong>{workflow.name}</Text>
          <Badge
            status={workflow.implemented ? 'success' : 'default'}
            text={workflow.implemented ? '已实现' : '未实现'}
          />
          <Tag color="blue" style={{ fontFamily: 'monospace' }}>
            {workflow.id}
          </Tag>
        </Space>
      }
      extra={
        statusInfo && (
          <Tag color={statusInfo.color}>{statusInfo.label}</Tag>
        )
      }
    >
      <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
        {workflow.description}
      </Text>

      <Collapse ghost>
        <Panel header="展开参数 & 触发" key="params">
          <Form
            form={form}
            layout="vertical"
            initialValues={{
              repo_owner: defaultOwner,
              repo_name: defaultName,
            }}
            style={{ maxWidth: 560 }}
          >
            {/* Dynamic params from WorkflowDef */}
            {workflow.params.map((param) => (
              <Form.Item
                key={param.name}
                name={param.name}
                label={param.label}
                initialValue={param.default_value ?? (param.type === 'boolean' ? false : param.type === 'datetime' ? null : '')}
                rules={
                  param.required
                    ? [{ required: true, message: `${param.label} 不能为空` }]
                    : []
                }
                valuePropName={param.type === 'boolean' ? 'checked' : 'value'}
              >
                {param.type === 'boolean' ? (
                  <Switch />
                ) : param.type === 'datetime' ? (
                  <DatePicker
                    showTime
                    style={{ width: '100%' }}
                    placeholder={`请选择 ${param.label}`}
                  />
                ) : (
                  <Input placeholder={`请输入 ${param.label}`} />
                )}
              </Form.Item>
            ))}

            <Form.Item>
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                loading={triggering && isActive}
                disabled={isActive || !workflow.implemented}
                onClick={handleSubmit}
              >
                {isActive ? '执行中...' : '触发工作流'}
              </Button>
              {!workflow.implemented && (
                <Text type="secondary" style={{ marginLeft: 12 }}>
                  该工作流尚未实现
                </Text>
              )}
            </Form.Item>
          </Form>

          {/* Execution status area */}
          {execution && (
            <div style={{ marginTop: 8 }}>
              {/* Running spinner */}
              {isActive && (
                <Spin tip={statusInfo?.label}>
                  <div style={{ padding: '16px 0' }} />
                </Spin>
              )}

              {/* Completed: show friendly result summary */}
              {execution.status === 'completed' && (
                <WorkflowResultSummary workflowType={workflowType} result={result} />
              )}

              {/* Failed: show error */}
              {execution.status === 'failed' && (
                <Alert
                  type="error"
                  message="工作流执行失败"
                  description={execution.error ?? '未知错误'}
                  showIcon
                  style={{ marginTop: 12 }}
                />
              )}
            </div>
          )}
        </Panel>
      </Collapse>
    </Card>
  );
}

export default function WorkflowManager() {
  const { currentRepo } = useAppStore();

  const [workflows, setWorkflows] = useState<WorkflowDef[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Map: workflowId → latest execution
  const [executions, setExecutions] = useState<Record<string, WorkflowExecution>>({});
  // Map: workflowId → whether a trigger request is in-flight
  const [triggering, setTriggering] = useState<Record<string, boolean>>({});

  // Polling intervals: workflowId → intervalId
  const pollRefs = useRef<Record<string, ReturnType<typeof setInterval>>>({});

  const stopPolling = useCallback((workflowId: string) => {
    if (pollRefs.current[workflowId]) {
      clearInterval(pollRefs.current[workflowId]);
      delete pollRefs.current[workflowId];
    }
  }, []);

  const startPolling = useCallback(
    (workflowId: string, executionId: string) => {
      stopPolling(workflowId);
      const id = setInterval(async () => {
        try {
          const status = await fetchWorkflowStatus(workflowId, executionId);
          setExecutions((prev) => ({ ...prev, [workflowId]: status }));
          if (status.status === 'completed' || status.status === 'failed') {
            stopPolling(workflowId);
          }
        } catch {
          // ignore transient poll errors
        }
      }, POLL_INTERVAL_MS);
      pollRefs.current[workflowId] = id;
    },
    [stopPolling],
  );

  // Cleanup all intervals on unmount
  useEffect(() => {
    return () => {
      Object.keys(pollRefs.current).forEach(stopPolling);
    };
  }, [stopPolling]);

  const loadWorkflows = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const list = await fetchWorkflows();
      setWorkflows(list);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '加载工作流列表失败';
      setLoadError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadWorkflows();
  }, [loadWorkflows]);

  const handleTrigger = useCallback(
    async (workflowId: string, values: Record<string, unknown>) => {
      setTriggering((prev) => ({ ...prev, [workflowId]: true }));
      try {
        const execution = await triggerWorkflow(workflowId, {
          repo_owner: String(values['repo_owner'] ?? currentRepo.owner),
          repo_name: String(values['repo_name'] ?? currentRepo.name),
          full_sync: Boolean(values['full_sync']),
          since: values['since'] ? String(values['since']) : undefined,
        });
        setExecutions((prev) => ({ ...prev, [workflowId]: execution }));
        // Start polling if still in progress
        if (execution.status === 'queued' || execution.status === 'running') {
          startPolling(workflowId, execution.execution_id);
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : '触发工作流失败';
        // Store a synthetic failed execution so the UI shows the error
        setExecutions((prev) => ({
          ...prev,
          [workflowId]: {
            execution_id: '',
            workflow_id: workflowId,
            status: 'failed',
            error: msg,
          },
        }));
      } finally {
        setTriggering((prev) => ({ ...prev, [workflowId]: false }));
      }
    },
    [currentRepo, startPolling],
  );

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={4} style={{ margin: 0 }}>
            工作流管理
          </Title>
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={loadWorkflows} loading={loading}>
            刷新
          </Button>
        </Col>
      </Row>

      {loadError && (
        <Alert
          type="error"
          message={loadError}
          showIcon
          closable
          style={{ marginBottom: 16 }}
          action={
            <Button size="small" icon={<ReloadOutlined />} onClick={loadWorkflows}>
              重试
            </Button>
          }
        />
      )}

      <Spin spinning={loading}>
        {workflows.map((wf) => (
          <WorkflowCard
            key={wf.id}
            workflow={wf}
            execution={executions[wf.id] ?? null}
            onTrigger={handleTrigger}
            triggering={triggering[wf.id] ?? false}
            defaultOwner={currentRepo.owner}
            defaultName={currentRepo.name}
          />
        ))}

        {!loading && workflows.length === 0 && !loadError && (
          <Alert type="info" message="暂无工作流数据" showIcon />
        )}
      </Spin>
    </div>
  );
}
