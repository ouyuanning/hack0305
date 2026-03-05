import apiClient from './client';
import type { KnowledgeBase } from '@/types';

export async function fetchKnowledge(
  repoOwner: string,
  repoName: string,
): Promise<KnowledgeBase> {
  const { data } = await apiClient.get<KnowledgeBase>('/api/v1/knowledge', {
    params: { repo_owner: repoOwner, repo_name: repoName },
  });
  return data;
}
