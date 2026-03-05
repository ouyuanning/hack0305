import { useEffect, useState, useRef, useCallback } from 'react';
import {
  Card,
  Badge,
  Button,
  Form,
  Input,
  Switch,
  Tag,
  Alert,
  Descriptions,
  Spin,
  Typography,
  Space,
  Row,
  Col,
  Collapse,
} from 'antd';
import { PlayCircleOutlined, ReloadOutlined } from '@ant-design/icons';
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
      const values = await form.validateFields();
      await onTrigger(workflow.id, values);
    } catch {
      // validation error — antd shows inline messages
    }
  };

  const statusInfo = execution ? STATUS_TAG[execution.status] : null;

  // Build result entries for Descriptions
  const resultEntries = execution?.result
    ? Object.entries(execution.result)
    : [];

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
                initialValue={param.default_value ?? (param.type === 'boolean' ? false : '')}
                rules={
                  param.required
                    ? [{ required: true, message: `${param.label} 不能为空` }]
                    : []
                }
                valuePropName={param.type === 'boolean' ? 'checked' : 'value'}
              >
                {param.type === 'boolean' ? (
                  <Switch />
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

              {/* Completed: show result summary */}
              {execution.status === 'completed' && resultEntries.length > 0 && (
                <Descriptions
                  title="执行结果"
                  bordered
                  size="small"
                  column={1}
                  style={{ marginTop: 12 }}
                >
                  {resultEntries.map(([key, value]) => (
                    <Descriptions.Item key={key} label={key}>
                      {String(value)}
                    </Descriptions.Item>
                  ))}
                </Descriptions>
              )}

              {execution.status === 'completed' && resultEntries.length === 0 && (
                <Alert
                  type="success"
                  message="工作流执行完成"
                  showIcon
                  style={{ marginTop: 12 }}
                />
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
