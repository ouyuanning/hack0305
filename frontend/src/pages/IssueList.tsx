import { useEffect, useState, useCallback, useMemo } from 'react';
import {
  Table,
  Tag,
  Input,
  Select,
  DatePicker,
  Row,
  Col,
  Empty,
  Spin,
  Alert,
  Button,
  Typography,
} from 'antd';
import { ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import { useNavigate, useSearchParams } from 'react-router-dom';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import type { SorterResult } from 'antd/es/table/interface';
import dayjs from 'dayjs';
import { fetchIssues } from '@/api/issues';
import type { IssueListParams } from '@/api/issues';
import { useAppStore } from '@/stores/appStore';
import type { Issue } from '@/types';

const { RangePicker } = DatePicker;
const { Title } = Typography;

const STATE_OPTIONS = [
  { label: '全部', value: 'all' },
  { label: 'Open', value: 'open' },
  { label: 'Closed', value: 'closed' },
];

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

export default function IssueList() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { currentRepo } = useAppStore();

  // Data state
  const [issues, setIssues] = useState<Issue[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filter state — pre-fill labels from URL query param (e.g. /issues?labels=area/foo)
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [state, setState] = useState<string>('all');
  const [selectedLabels, setSelectedLabels] = useState<string[]>(() => {
    const labelsParam = searchParams.get('labels');
    return labelsParam ? labelsParam.split(',').filter(Boolean) : [];
  });
  const [assignee, setAssignee] = useState<string | undefined>(undefined);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);
  const [keyword, setKeyword] = useState('');
  const [sortField, setSortField] = useState<string | undefined>(undefined);
  const [sortOrder, setSortOrder] = useState<string | undefined>(undefined);

  // Derived unique values for filter dropdowns
  const labelOptions = useMemo(() => {
    const allLabels = new Set<string>();
    issues.forEach((issue) => issue.labels?.forEach((l) => allLabels.add(l)));
    return Array.from(allLabels).sort().map((l) => ({ label: l, value: l }));
  }, [issues]);

  const assigneeOptions = useMemo(() => {
    const allAssignees = new Set<string>();
    issues.forEach((issue) => {
      if (issue.assignee) allAssignees.add(issue.assignee);
    });
    return Array.from(allAssignees).sort().map((a) => ({ label: a, value: a }));
  }, [issues]);

  const loadIssues = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: IssueListParams = {
        page,
        page_size: pageSize,
        repo_owner: currentRepo.owner,
        repo_name: currentRepo.name,
      };
      if (state && state !== 'all') params.state = state;
      if (selectedLabels.length > 0) params.labels = selectedLabels.join(',');
      if (assignee) params.assignee = assignee;
      if (dateRange) {
        params.start_date = dateRange[0].startOf('day').toISOString();
        params.end_date = dateRange[1].endOf('day').toISOString();
      }
      if (keyword.trim()) params.keyword = keyword.trim();
      if (sortField) params.sort_field = sortField;
      if (sortOrder) params.sort_order = sortOrder;

      const res = await fetchIssues(params);
      setIssues(res.items ?? []);
      setTotal(res.total);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '加载 Issue 列表失败';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, state, selectedLabels, assignee, dateRange, keyword, sortField, sortOrder, currentRepo.owner, currentRepo.name]);

  useEffect(() => {
    loadIssues();
  }, [loadIssues]);

  // Reset to page 1 when filters change
  useEffect(() => {
    setPage(1);
  }, [state, selectedLabels, assignee, dateRange, keyword, currentRepo.owner, currentRepo.name]);

  const handleTableChange = (
    pagination: TablePaginationConfig,
    _filters: Record<string, unknown>,
    sorter: SorterResult<Issue> | SorterResult<Issue>[],
  ) => {
    if (pagination.current) setPage(pagination.current);
    if (pagination.pageSize) setPageSize(pagination.pageSize);

    const singleSorter = Array.isArray(sorter) ? sorter[0] : sorter;
    if (singleSorter?.field && singleSorter.order) {
      setSortField(singleSorter.field as string);
      setSortOrder(singleSorter.order === 'ascend' ? 'asc' : 'desc');
    } else {
      setSortField(undefined);
      setSortOrder(undefined);
    }
  };

  const columns: ColumnsType<Issue> = [
    {
      title: '编号',
      dataIndex: 'issue_number',
      key: 'issue_number',
      width: 100,
      sorter: true,
      sortOrder: sortField === 'issue_number' ? (sortOrder === 'asc' ? 'ascend' : 'descend') : undefined,
      render: (num: number) => `#${num}`,
    },
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'state',
      key: 'state',
      width: 90,
      render: (s: string) => (
        <Tag color={s === 'open' ? 'red' : 'green'}>{s === 'open' ? 'Open' : 'Closed'}</Tag>
      ),
    },
    {
      title: 'Labels',
      dataIndex: 'labels',
      key: 'labels',
      width: 250,
      render: (labels: string[]) =>
        labels?.length > 0 ? (
          <>
            {labels.map((label) => (
              <Tag key={label} color={getLabelColor(label)} style={{ marginBottom: 2 }}>
                {label}
              </Tag>
            ))}
          </>
        ) : (
          '-'
        ),
    },
    {
      title: '负责人',
      dataIndex: 'assignee',
      key: 'assignee',
      width: 120,
      render: (a: string) => a || '-',
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 170,
      sorter: true,
      sortOrder: sortField === 'updated_at' ? (sortOrder === 'asc' ? 'ascend' : 'descend') : undefined,
      render: (t: string) => (t ? dayjs(t).format('YYYY-MM-DD HH:mm') : '-'),
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 24 }}>
        Issue 列表
      </Title>

      {error && (
        <Alert
          type="error"
          message={error}
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

      {/* Filter Panel */}
      <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} md={6} lg={4}>
          <Select
            style={{ width: '100%' }}
            placeholder="状态"
            value={state}
            onChange={(v) => setState(v)}
            options={STATE_OPTIONS}
            allowClear={false}
          />
        </Col>
        <Col xs={24} sm={12} md={6} lg={5}>
          <Select
            mode="multiple"
            style={{ width: '100%' }}
            placeholder="Labels"
            value={selectedLabels}
            onChange={(v) => setSelectedLabels(v)}
            options={labelOptions}
            allowClear
            maxTagCount="responsive"
          />
        </Col>
        <Col xs={24} sm={12} md={6} lg={4}>
          <Select
            style={{ width: '100%' }}
            placeholder="负责人"
            value={assignee}
            onChange={(v) => setAssignee(v)}
            options={assigneeOptions}
            allowClear
            showSearch
          />
        </Col>
        <Col xs={24} sm={12} md={6} lg={5}>
          <RangePicker
            style={{ width: '100%' }}
            value={dateRange}
            onChange={(dates) => setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null)}
          />
        </Col>
        <Col xs={24} sm={24} md={12} lg={6}>
          <Input.Search
            placeholder="搜索标题或正文..."
            allowClear
            enterButton={<SearchOutlined />}
            onSearch={(v) => setKeyword(v)}
          />
        </Col>
      </Row>

      {/* Table */}
      <Spin spinning={loading}>
        <Table<Issue>
          columns={columns}
          dataSource={issues}
          rowKey="issue_number"
          onChange={handleTableChange}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
            pageSizeOptions: ['10', '20', '50', '100'],
          }}
          onRow={(record) => ({
            onClick: () => navigate(`/issues/${record.issue_number}`),
            style: { cursor: 'pointer' },
          })}
          locale={{
            emptyText: <Empty description="无匹配结果" />,
          }}
          scroll={{ x: 800 }}
        />
      </Spin>
    </div>
  );
}
