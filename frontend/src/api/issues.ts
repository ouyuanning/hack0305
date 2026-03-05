import apiClient from './client';
import type {
  Issue,
  PaginatedResponse,
  IssueDetailResponse,
  CreateIssueRequest,
  IssueDraft,
  GenerateIssueRequest,
  OverviewResponse,
  LabelsResponse,
  RepoInfo,
} from '@/types';

export interface IssueListParams {
  page?: number;
  page_size?: number;
  state?: string;
  labels?: string;
  assignee?: string;
  start_date?: string;
  end_date?: string;
  keyword?: string;
  sort_field?: string;
  sort_order?: string;
  repo_owner?: string;
  repo_name?: string;
}

export async function fetchIssues(params: IssueListParams): Promise<PaginatedResponse<Issue>> {
  const { data } = await apiClient.get<PaginatedResponse<Issue>>('/api/v1/issues', { params });
  return data;
}

export async function fetchIssueDetail(
  issueNumber: number,
  repoOwner?: string,
  repoName?: string,
): Promise<IssueDetailResponse> {
  const { data } = await apiClient.get<IssueDetailResponse>(`/api/v1/issues/${issueNumber}`, {
    params: { repo_owner: repoOwner, repo_name: repoName },
  });
  return data;
}

export async function createIssue(req: CreateIssueRequest): Promise<{ issue_number: number; html_url: string }> {
  const { data } = await apiClient.post<{ issue_number: number; html_url: string }>('/api/v1/issues', req);
  return data;
}

export async function generateIssue(req: GenerateIssueRequest): Promise<IssueDraft> {
  const { data } = await apiClient.post<IssueDraft>('/api/v1/ai/generate-issue', req);
  return data;
}

export async function fetchOverview(repoOwner: string, repoName: string): Promise<OverviewResponse> {
  const { data } = await apiClient.get<OverviewResponse>('/api/v1/stats/overview', {
    params: { repo_owner: repoOwner, repo_name: repoName },
  });
  return data;
}

export async function fetchLabelsStats(
  repoOwner: string,
  repoName: string,
  prefix?: string,
): Promise<LabelsResponse> {
  const { data } = await apiClient.get<LabelsResponse>('/api/v1/stats/labels', {
    params: { repo_owner: repoOwner, repo_name: repoName, prefix },
  });
  return data;
}

export async function fetchRepos(): Promise<RepoInfo[]> {
  const { data } = await apiClient.get<RepoInfo[]>('/api/v1/repos');
  return data;
}
