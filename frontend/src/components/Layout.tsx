import { useEffect, useState, type ReactNode } from 'react';
import { Layout as AntLayout, Menu, Select, theme } from 'antd';
import {
  DashboardOutlined,
  UnorderedListOutlined,
  ProjectOutlined,
  PlusCircleOutlined,
  BarChartOutlined,
  ThunderboltOutlined,
  BookOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAppStore } from '@/stores/appStore';

const { Header, Sider, Content } = AntLayout;

interface LayoutProps {
  children: ReactNode;
}

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '总览' },
  { key: '/issues', icon: <UnorderedListOutlined />, label: 'Issue 列表' },
  { key: '/kanban', icon: <ProjectOutlined />, label: '看板' },
  { key: '/create-issue', icon: <PlusCircleOutlined />, label: '创建 Issue' },
  { key: '/reports', icon: <BarChartOutlined />, label: '分析报告' },
  { key: '/workflows', icon: <ThunderboltOutlined />, label: '工作流管理' },
  { key: '/knowledge', icon: <BookOutlined />, label: '知识库' },
];

export default function Layout({ children }: LayoutProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { currentRepo, repos, setCurrentRepo, loadRepos } = useAppStore();
  const [collapsed, setCollapsed] = useState(false);
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();

  useEffect(() => {
    loadRepos();
  }, [loadRepos]);

  const selectedKey = menuItems.find((item) => {
    if (item.key === '/') return location.pathname === '/';
    return location.pathname.startsWith(item.key);
  })?.key ?? '/';

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        breakpoint="md"
        collapsedWidth={80}
        style={{ background: colorBgContainer }}
      >
        <div
          style={{
            height: 32,
            margin: 16,
            textAlign: 'center',
            fontWeight: 'bold',
            fontSize: collapsed ? 14 : 18,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
          }}
        >
          {collapsed ? 'IS' : 'Issue 管理'}
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <AntLayout>
        <Header
          style={{
            padding: '0 24px',
            background: colorBgContainer,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span style={{ fontWeight: 600, fontSize: 16 }}>
            {currentRepo.owner}/{currentRepo.name}
          </span>
          <Select
            value={`${currentRepo.owner}/${currentRepo.name}`}
            onChange={(value) => {
              const [owner, name] = value.split('/');
              setCurrentRepo(owner, name);
            }}
            style={{ width: 240 }}
            options={repos.map((r) => ({
              value: `${r.owner}/${r.name}`,
              label: r.display_name || `${r.owner}/${r.name}`,
            }))}
            placeholder="选择仓库"
          />
        </Header>
        <Content
          style={{
            margin: 24,
            padding: 24,
            background: colorBgContainer,
            borderRadius: borderRadiusLG,
            minHeight: 280,
          }}
        >
          {children}
        </Content>
      </AntLayout>
    </AntLayout>
  );
}
