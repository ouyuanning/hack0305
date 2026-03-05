import { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from '@/components/Layout';
import ErrorBoundary from '@/components/ErrorBoundary';

const Dashboard = lazy(() => import('@/pages/Dashboard'));
const IssueList = lazy(() => import('@/pages/IssueList'));
const IssueDetail = lazy(() => import('@/pages/IssueDetail'));
const KanbanBoard = lazy(() => import('@/pages/KanbanBoard'));
const IssueCreator = lazy(() => import('@/pages/IssueCreator'));
const ReportList = lazy(() => import('@/pages/ReportList'));
const ReportDetail = lazy(() => import('@/pages/ReportDetail'));
const WorkflowManager = lazy(() => import('@/pages/WorkflowManager'));
const KnowledgeBase = lazy(() => import('@/pages/KnowledgeBase'));

export default function App() {
  return (
    <ErrorBoundary>
      <Layout>
        <Suspense fallback={<div>Loading...</div>}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/issues" element={<IssueList />} />
            <Route path="/issues/:number" element={<IssueDetail />} />
            <Route path="/kanban" element={<KanbanBoard />} />
            <Route path="/create-issue" element={<IssueCreator />} />
            <Route path="/reports" element={<ReportList />} />
            <Route path="/reports/:id" element={<ReportDetail />} />
            <Route path="/workflows" element={<WorkflowManager />} />
            <Route path="/knowledge" element={<KnowledgeBase />} />
          </Routes>
        </Suspense>
      </Layout>
    </ErrorBoundary>
  );
}
