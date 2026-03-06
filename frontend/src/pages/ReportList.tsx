import { useEffect, useState, useCallback } from 'react';
import { Table, Tag, Empty, Spin, Alert, Button, Typography } from 'antd';
import { ReloadOutlined, FileTextOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { fetchReports } from '@/api/reports';
import { useAppStore } from '@/stores/appStore';
import type { Report } from '@/types';

const { Title } = Typography;

const REPORT_TYPE_LABELS: Record<Report['type'], string> = {
  daily: '日报',
  progress: '项目推进分析',
  comprehensive: '综合分析',
  extensible: '可扩展分析',
  shared: '横向关联分析',
  risk: '风险分析',
  customer: '客户报告',
};

const REPORT_TYPE_COLORS: Record<Report['type'], string> = {
  daily: 'default',
  progress: 'blue',
  comprehensive: 'purple',
  extensible: 'cyan',
  shared: 'orange',
  risk: 'red',
  customer: 'green',
};

export default function ReportList() {
  const navigate = useNavigate();
  const { currentRepo } = useAppStore();

  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadReports = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchReports(currentRepo.owner, currentRepo.name);
      // Sort by generated_at descending
      const sorted = [...(res.items ?? [])].sort(
        (a, b) => new Date(b.generated_at).getTime() - new Date(a.generated_at).getTime(),
      );
      setReports(sorted);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '加载报告列表失败';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [currentRepo.owner, currentRepo.name]);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  const columns: ColumnsType<Report> = [
    {
      title: '报告类型',
      dataIndex: 'type',
      key: 'type',
      width: 160,
      render: (type: Report['type']) => (
        <Tag color={REPORT_TYPE_COLORS[type] ?? 'default'}>
          {REPORT_TYPE_LABELS[type] ?? type}
        </Tag>
      ),
    },
    {
      title: '仓库',
      dataIndex: 'repo',
      key: 'repo',
      width: 220,
    },
    {
      title: '生成时间',
      dataIndex: 'generated_at',
      key: 'generated_at',
      width: 180,
      render: (t: string) => (t ? dayjs(t).format('YYYY-MM-DD HH:mm') : '-'),
    },
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      ellipsis: true,
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 24 }}>
        分析报告
      </Title>

      {error && (
        <Alert
          type="error"
          message={error}
          showIcon
          closable
          style={{ marginBottom: 16 }}
          action={
            <Button size="small" icon={<ReloadOutlined />} onClick={loadReports}>
              重试
            </Button>
          }
        />
      )}

      <Spin spinning={loading}>
        <Table<Report>
          columns={columns}
          dataSource={reports}
          rowKey="id"
          onRow={(record) => ({
            onClick: () => navigate(`/reports/${record.id}?repo_owner=${currentRepo.owner}&repo_name=${currentRepo.name}`),
            style: { cursor: 'pointer' },
          })}
          locale={{
            emptyText: (
              <Empty
                image={<FileTextOutlined style={{ fontSize: 48, color: '#bfbfbf' }} />}
                description={
                  <span>
                    暂无报告
                    <br />
                    <span style={{ color: '#8c8c8c', fontSize: 13 }}>
                      请前往「工作流管理」触发 WF-007 生成分析报告
                    </span>
                  </span>
                }
              />
            ),
          }}
          pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 份报告` }}
          scroll={{ x: 700 }}
        />
      </Spin>
    </div>
  );
}
