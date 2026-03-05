import apiClient from './client';
import type { ReportListResponse, ReportDetail } from '@/types';

export async function fetchReports(
  repoOwner: string,
  repoName: string,
  type?: string,
): Promise<ReportListResponse> {
  const { data } = await apiClient.get<ReportListResponse>('/api/v1/reports', {
    params: { repo_owner: repoOwner, repo_name: repoName, type },
  });
  return data;
}

export async function fetchReportDetail(
  reportId: string,
  repoOwner: string,
  repoName: string,
): Promise<ReportDetail> {
  const { data } = await apiClient.get<ReportDetail>(`/api/v1/reports/${reportId}`, {
    params: { repo_owner: repoOwner, repo_name: repoName },
  });
  return data;
}
