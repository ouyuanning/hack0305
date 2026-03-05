import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Button,
  Descriptions,
  Empty,
  Spin,
  Tabs,
  Typography,
} from 'antd';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Components } from 'react-markdown';
import { fetchKnowledge } from '@/api/knowledge';
import { useAppStore } from '@/stores/appStore';
import type { KnowledgeBase as KnowledgeBaseType } from '@/types';

const { Text } = Typography;

// Split markdown content into sections by heading patterns
interface Section {
  key: string;
  label: string;
  content: string;
}

function parseSections(content: string): Section[] {
  // Split on level-1 or level-2 headings
  const lines = content.split('\n');
  const headingIndices: { index: number; line: string }[] = [];

  lines.forEach((line, i) => {
    if (/^#{1,2}\s/.test(line)) {
      headingIndices.push({ index: i, line });
    }
  });

  if (headingIndices.length === 0) {
    return [{ key: 'all', label: '全部内容', content }];
  }

  const sections: Section[] = [];

  const productPattern = /产品|结构|product/i;
  const labelPattern = /标签|label/i;
  const issuePattern = /issue|类型|type/i;

  const sectionDefs = [
    { key: 'product', label: '产品结构', pattern: productPattern },
    { key: 'labels', label: '标签体系', pattern: labelPattern },
    { key: 'issues', label: '常见 Issue 类型', pattern: issuePattern },
  ];

  // Find which heading matches which section
  const matched: Record<string, { startLine: number; endLine: number }> = {};

  headingIndices.forEach(({ index, line }, pos) => {
    const nextHeadingIndex =
      pos + 1 < headingIndices.length ? headingIndices[pos + 1].index : lines.length;

    for (const def of sectionDefs) {
      if (def.pattern.test(line) && !(def.key in matched)) {
        matched[def.key] = { startLine: index, endLine: nextHeadingIndex };
        break;
      }
    }
  });

  for (const def of sectionDefs) {
    if (def.key in matched) {
      const { startLine, endLine } = matched[def.key];
      sections.push({
        key: def.key,
        label: def.label,
        content: lines.slice(startLine, endLine).join('\n').trim(),
      });
    }
  }

  if (sections.length === 0) {
    return [{ key: 'all', label: '全部内容', content }];
  }

  return sections;
}

// Custom markdown components to make label/product links navigable
function useMarkdownComponents(navigate: ReturnType<typeof useNavigate>): Components {
  return {
    a({ href, children, ...props }) {
      if (href?.startsWith('#label:')) {
        const label = decodeURIComponent(href.slice('#label:'.length));
        return (
          <a
            href="#"
            onClick={(e) => {
              e.preventDefault();
              navigate(`/issues?labels=${encodeURIComponent(label)}`);
            }}
            style={{ color: '#1677ff' }}
            {...props}
          >
            {children}
          </a>
        );
      }
      if (href?.startsWith('#product:')) {
        const product = decodeURIComponent(href.slice('#product:'.length));
        return (
          <a
            href="#"
            onClick={(e) => {
              e.preventDefault();
              navigate(`/issues?labels=${encodeURIComponent(product)}`);
            }}
            style={{ color: '#1677ff' }}
            {...props}
          >
            {children}
          </a>
        );
      }
      // For regular links, render as-is
      return (
        <a href={href} target="_blank" rel="noopener noreferrer" {...props}>
          {children}
        </a>
      );
    },
    // Render inline code that looks like a label (area/xxx, kind/xxx, customer/xxx) as clickable
    code({ children, ...props }) {
      const text = String(children);
      const labelPattern = /^(area|kind|customer|project|priority)\/\S+$/;
      if (labelPattern.test(text)) {
        return (
          <a
            href="#"
            onClick={(e) => {
              e.preventDefault();
              navigate(`/issues?labels=${encodeURIComponent(text)}`);
            }}
            style={{
              color: '#1677ff',
              background: '#f0f5ff',
              padding: '1px 6px',
              borderRadius: 4,
              fontFamily: 'monospace',
              fontSize: '0.9em',
            }}
          >
            {text}
          </a>
        );
      }
      return <code {...props}>{children}</code>;
    },
  };
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

export default function KnowledgeBase() {
  const navigate = useNavigate();
  const { currentRepo } = useAppStore();

  const [knowledge, setKnowledge] = useState<KnowledgeBaseType | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  const markdownComponents = useMarkdownComponents(navigate);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setNotFound(false);
    try {
      const data = await fetchKnowledge(currentRepo.owner, currentRepo.name);
      if (!data.content) {
        setNotFound(true);
      } else {
        setKnowledge(data);
      }
    } catch (err: unknown) {
      // Treat 404 as "not found" rather than an error
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 404) {
        setNotFound(true);
      } else {
        setError(err instanceof Error ? err.message : '加载知识库失败');
      }
    } finally {
      setLoading(false);
    }
  }, [currentRepo.owner, currentRepo.name]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 80 }}>
        <Spin size="large" tip="加载知识库中..." />
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 24 }}>
        <Alert
          type="error"
          message="加载失败"
          description={error}
          action={
            <Button size="small" onClick={load}>
              重试
            </Button>
          }
          showIcon
        />
      </div>
    );
  }

  if (notFound || !knowledge) {
    return (
      <div style={{ padding: 48, textAlign: 'center' }}>
        <Empty
          description={
            <span>
              知识库尚未生成
              <br />
              <Text type="secondary">请前往工作流管理页面触发 WF-002 生成知识库</Text>
            </span>
          }
        >
          <Button type="primary" onClick={() => navigate('/workflows')}>
            前往工作流管理触发 WF-002
          </Button>
        </Empty>
      </div>
    );
  }

  const sections = parseSections(knowledge.content);

  const tabItems = sections.map((section) => ({
    key: section.key,
    label: section.label,
    children: (
      <div style={{ padding: '8px 0' }}>
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
          {section.content}
        </ReactMarkdown>
      </div>
    ),
  }));

  return (
    <div style={{ padding: 24 }}>
      <Descriptions
        title="知识库信息"
        bordered
        size="small"
        style={{ marginBottom: 24 }}
        column={2}
      >
        <Descriptions.Item label="生成时间">{formatDate(knowledge.generated_at)}</Descriptions.Item>
        <Descriptions.Item label="版本">{knowledge.version}</Descriptions.Item>
        <Descriptions.Item label="仓库" span={2}>
          {currentRepo.owner}/{currentRepo.name}
        </Descriptions.Item>
      </Descriptions>

      <Tabs defaultActiveKey={sections[0]?.key} items={tabItems} />
    </div>
  );
}
