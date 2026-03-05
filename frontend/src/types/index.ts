// TypeScript type definitions for the Issue Dashboard frontend.
// These types mirror the backend Go API response structures.

export interface Issue {
  issue_id: number;
  issue_number: number;
  repo_owner: string;
  repo_name: string;
  title: string;
  body: string;
  state: 'open' | 'closed';
  issue_type: string;
  priority: string;
  assignee: string;
  labels: string[];
  milestone: string;
  created_at: string;
  updated_at: string;
  closed_at: string | null;
  ai_summary: string;
  ai_tags: string[];
  ai_priority: string;
  status: string;
  progress_percentage: number;
  is_blocked: boolean;
  blocked_reason: string;
}

export interface Comment {
  comment_id: number;
  issue_number: number;
  user: string;
  body: string;
  created_at: string;
  updated_at: string;
}

export interface Relation {
  from_issue_id: number;
  to_issue_id: number;
  to_issue_number: number;
  relation_type: string;
  relation_semantic: string;
  context_text: string;
}

export interface IssueDraft {
  title: string;
  body: string;
  labels: string[];
  assignees: string[];
  template_type: string;
  related_issues: string[];
}

export interface Report {
  id: string;
  type: 'daily' | 'progress' | 'extensible' | 'comprehensive' | 'shared' | 'risk' | 'customer';
  repo: string;
  generated_at: string;
  filename: string;
}

export interface ReportDetail {
  metadata: Report;
  data: Record<string, unknown>;
}

export interface WorkflowDef {
  id: string;
  name: string;
  description: string;
  implemented: boolean;
  params: WorkflowParam[];
}

export interface WorkflowParam {
  name: string;
  label: string;
  required: boolean;
  type: 'string' | 'boolean' | 'datetime';
  default_value?: string;
}

export interface WorkflowExecution {
  execution_id: string;
  workflow_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  result?: Record<string, unknown>;
  error?: string;
  started_at?: string;
  completed_at?: string;
}

export interface HealthScore {
  customer: string;
  score: number;
  total_issues: number;
  open_issues: number;
  blocked_issues: number;
}

export interface KnowledgeBase {
  content: string;
  generated_at: string;
  version: string;
}

export interface LabelGroup {
  label: string;
  count: number;
  open: number;
  closed: number;
}

export interface PaginatedResponse<T> {
  total: number;
  page: number;
  page_size: number;
  items: T[];
}

export interface RepoInfo {
  owner: string;
  name: string;
  display_name: string;
}

// --- Request types ---

export interface CreateIssueRequest {
  repo_owner: string;
  repo_name: string;
  title: string;
  body: string;
  labels: string[];
  assignees: string[];
}

export interface GenerateIssueRequest {
  user_input: string;
  images: string[];
  repo_owner: string;
  repo_name: string;
}

export interface TriggerWorkflowRequest {
  repo_owner: string;
  repo_name: string;
  full_sync?: boolean;
  since?: string;
}

// --- Composite response types ---

export interface IssueDetailResponse {
  issue: Issue;
  comments: Comment[];
  timeline: Record<string, unknown>[];
  relations: Relation[];
}

export interface OverviewResponse {
  total: number;
  open: number;
  closed: number;
  open_ratio: number;
  recent_issues: Issue[];
  health_scores: HealthScore[];
}

export interface LabelsResponse {
  groups: Record<string, LabelGroup[]>;
}

export interface ReportListResponse {
  items: Report[];
}

export interface ErrorResponse {
  code: number;
  message: string;
  detail?: string;
}
