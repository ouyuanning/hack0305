import { useState, useCallback, useEffect } from 'react';
import {
  Steps,
  Card,
  Input,
  Button,
  Upload,
  Spin,
  Alert,
  Select,
  Form,
  Result,
  Typography,
  Space,
  Tag,
} from 'antd';
import {
  InboxOutlined,
  RobotOutlined,
  SendOutlined,
  EditOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import type { UploadFile, UploadProps } from 'antd';
import { useLocation } from 'react-router-dom';
import { generateIssue, createIssue } from '@/api/issues';
import { useAppStore } from '@/stores/appStore';
import type { IssueDraft } from '@/types';

const { TextArea } = Input;
const { Title, Text, Link } = Typography;
const { Dragger } = Upload;

// Convert a File to base64 string
function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      // Strip the data URL prefix (e.g. "data:image/png;base64,")
      const base64 = result.split(',')[1] ?? result;
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

const COMMON_LABELS = [
  'kind/bug',
  'kind/feature',
  'kind/enhancement',
  'kind/question',
  'kind/documentation',
  'priority/P0',
  'priority/P1',
  'priority/P2',
  'priority/P3',
];

const COMMON_ASSIGNEES = [
  'aunjgr',
  'daviszhen',
  'reusee',
  'nnsgmsone',
  'ouyuanning',
];

export default function IssueCreator() {
  const { currentRepo } = useAppStore();
  const location = useLocation();

  // Step 0: input
  const [currentStep, setCurrentStep] = useState(0);
  const [description, setDescription] = useState('');
  const [fileList, setFileList] = useState<UploadFile[]>([]);

  // Step 1: AI generating
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  // Step 1: draft form
  const [draft, setDraft] = useState<IssueDraft | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editBody, setEditBody] = useState('');
  const [editLabels, setEditLabels] = useState<string[]>([]);
  const [editAssignees, setEditAssignees] = useState<string[]>([]);

  // Step 2: creating
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createdIssue, setCreatedIssue] = useState<{ issue_number: number; html_url: string } | null>(null);

  // Accept draft from navigation state (e.g. from WF-003 result)
  useEffect(() => {
    const state = location.state as { draft?: Partial<IssueDraft> } | null;
    if (state?.draft) {
      const d = state.draft;
      setDraft(d as IssueDraft);
      setEditTitle(d.title ?? '');
      setEditBody(d.body ?? '');
      setEditLabels(d.labels ?? []);
      setEditAssignees(d.assignees ?? []);
      setCurrentStep(1);
      // Clear the state so refreshing doesn't re-apply
      window.history.replaceState({}, '');
    }
  }, [location.state]);

  // Upload config: prevent auto-upload, only accept images
  const uploadProps: UploadProps = {
    name: 'file',
    multiple: true,
    accept: 'image/*',
    fileList,
    beforeUpload: (file) => {
      setFileList((prev) => [...prev, { uid: file.uid, name: file.name, status: 'done', originFileObj: file } as UploadFile]);
      return false; // prevent auto-upload
    },
    onRemove: (file) => {
      setFileList((prev) => prev.filter((f) => f.uid !== file.uid));
    },
    showUploadList: {
      showRemoveIcon: true,
    },
  };

  const handleGenerate = useCallback(async () => {
    if (!description.trim()) return;

    setAiLoading(true);
    setAiError(null);

    try {
      // Convert images to base64
      const images: string[] = [];
      for (const f of fileList) {
        if (f.originFileObj) {
          const b64 = await fileToBase64(f.originFileObj as File);
          images.push(b64);
        }
      }

      const result = await generateIssue({
        user_input: description,
        images,
        repo_owner: currentRepo.owner,
        repo_name: currentRepo.name,
      });

      setDraft(result);
      setEditTitle(result.title ?? '');
      setEditBody(result.body ?? '');
      setEditLabels(result.labels ?? []);
      setEditAssignees(result.assignees ?? []);
      setCurrentStep(1);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'AI 生成失败，请稍后重试';
      setAiError(msg);
      // Still allow manual editing: advance to step 1 with empty form
      setDraft(null);
      setEditTitle('');
      setEditBody('');
      setEditLabels([]);
      setEditAssignees([]);
      setCurrentStep(1);
    } finally {
      setAiLoading(false);
    }
  }, [description, fileList, currentRepo]);

  const handleCreate = useCallback(async () => {
    if (!editTitle.trim()) return;

    setCreateLoading(true);
    setCreateError(null);

    try {
      const result = await createIssue({
        repo_owner: currentRepo.owner,
        repo_name: currentRepo.name,
        title: editTitle,
        body: editBody,
        labels: editLabels,
        assignees: editAssignees,
      });
      setCreatedIssue(result);
      setCurrentStep(2);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '创建 Issue 失败，请稍后重试';
      setCreateError(msg);
    } finally {
      setCreateLoading(false);
    }
  }, [editTitle, editBody, editLabels, editAssignees, currentRepo]);

  const handleReset = () => {
    setCurrentStep(0);
    setDescription('');
    setFileList([]);
    setAiError(null);
    setDraft(null);
    setEditTitle('');
    setEditBody('');
    setEditLabels([]);
    setEditAssignees([]);
    setCreateError(null);
    setCreatedIssue(null);
  };

  const steps = [
    { title: '描述问题', icon: <EditOutlined /> },
    { title: '预览 & 编辑', icon: <RobotOutlined /> },
    { title: '创建成功', icon: <SendOutlined /> },
  ];

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <Title level={4} style={{ marginBottom: 24 }}>
        智能创建 Issue
      </Title>

      <Steps
        current={currentStep}
        items={steps}
        style={{ marginBottom: 32 }}
      />

      {/* Step 0: Input description + images */}
      {currentStep === 0 && (
        <Card title="描述你的问题">
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <div>
              <Text strong>问题描述</Text>
              <TextArea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="请详细描述你遇到的问题或需求，AI 将根据描述自动生成 Issue 内容..."
                rows={6}
                style={{ marginTop: 8 }}
                maxLength={5000}
                showCount
              />
            </div>

            <div>
              <Text strong>上传截图（可选）</Text>
              <Dragger {...uploadProps} style={{ marginTop: 8 }}>
                <p className="ant-upload-drag-icon">
                  <InboxOutlined />
                </p>
                <p className="ant-upload-text">点击或拖拽图片到此区域上传</p>
                <p className="ant-upload-hint">支持 PNG、JPG、GIF 等图片格式，图片将作为上下文发送给 AI</p>
              </Dragger>
            </div>

            {aiError && currentStep === 0 && (
              <Alert type="error" message={aiError} showIcon closable onClose={() => setAiError(null)} />
            )}

            <div style={{ textAlign: 'right' }}>
              <Button
                type="primary"
                icon={<RobotOutlined />}
                size="large"
                loading={aiLoading}
                disabled={!description.trim()}
                onClick={handleGenerate}
              >
                AI 生成预览
              </Button>
            </div>
          </Space>
        </Card>
      )}

      {/* Step 1: Preview & edit form */}
      {currentStep === 1 && (
        <Spin spinning={aiLoading} tip="AI 正在生成 Issue 预览...">
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            {aiError && (
              <Alert
                type="warning"
                message="AI 生成失败"
                description={`${aiError}。你可以手动填写 Issue 内容。`}
                showIcon
                closable
                onClose={() => setAiError(null)}
              />
            )}

            {!aiError && draft && (
              <Alert
                type="success"
                message="AI 已生成 Issue 预览，你可以在下方编辑内容后创建"
                showIcon
                closable
              />
            )}

            <Card
              title="Issue 预览（可编辑）"
              extra={
                <Button size="small" icon={<DeleteOutlined />} onClick={handleReset}>
                  重新开始
                </Button>
              }
            >
              <Form layout="vertical">
                <Form.Item
                  label="标题"
                  required
                  validateStatus={!editTitle.trim() ? 'error' : ''}
                  help={!editTitle.trim() ? '标题不能为空' : ''}
                >
                  <Input
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    placeholder="Issue 标题"
                    maxLength={256}
                    showCount
                  />
                </Form.Item>

                <Form.Item label="正文（Markdown）">
                  <TextArea
                    value={editBody}
                    onChange={(e) => setEditBody(e.target.value)}
                    placeholder="Issue 正文，支持 Markdown 格式..."
                    rows={10}
                    style={{ fontFamily: 'monospace' }}
                  />
                </Form.Item>

                <Form.Item label="Labels">
                  <Select
                    mode="tags"
                    value={editLabels}
                    onChange={setEditLabels}
                    placeholder="选择或输入 Labels"
                    style={{ width: '100%' }}
                    options={COMMON_LABELS.map((l) => ({ label: l, value: l }))}
                    tagRender={({ label, value, closable, onClose }) => (
                      <Tag
                        color="blue"
                        closable={closable}
                        onClose={onClose}
                        style={{ marginRight: 4 }}
                      >
                        {label ?? value}
                      </Tag>
                    )}
                  />
                </Form.Item>

                <Form.Item label="负责人">
                  <Select
                    mode="tags"
                    value={editAssignees}
                    onChange={setEditAssignees}
                    placeholder="选择或输入负责人 GitHub 用户名"
                    style={{ width: '100%' }}
                    options={COMMON_ASSIGNEES.map((a) => ({ label: a, value: a }))}
                  />
                </Form.Item>
              </Form>
            </Card>

            {createError && (
              <Alert
                type="error"
                message="创建失败"
                description={createError}
                showIcon
                closable
                onClose={() => setCreateError(null)}
              />
            )}

            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <Button onClick={() => setCurrentStep(0)}>返回修改描述</Button>
              <Button
                type="primary"
                icon={<SendOutlined />}
                size="large"
                loading={createLoading}
                disabled={!editTitle.trim()}
                onClick={handleCreate}
              >
                创建 Issue
              </Button>
            </div>
          </Space>
        </Spin>
      )}

      {/* Step 2: Success */}
      {currentStep === 2 && createdIssue && (
        <Card>
          <Result
            status="success"
            title={`Issue #${createdIssue.issue_number} 创建成功！`}
            subTitle={
              <Space direction="vertical" align="center">
                <Text>Issue 已成功创建到 GitHub 仓库</Text>
                <Link href={createdIssue.html_url} target="_blank" rel="noopener noreferrer">
                  {createdIssue.html_url}
                </Link>
              </Space>
            }
            extra={[
              <Button
                key="view"
                type="primary"
                href={createdIssue.html_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                在 GitHub 查看
              </Button>,
              <Button key="new" onClick={handleReset}>
                创建新 Issue
              </Button>,
            ]}
          />
        </Card>
      )}
    </div>
  );
}
