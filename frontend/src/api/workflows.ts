import apiClient from './client';
import type { WorkflowDef, WorkflowExecution, TriggerWorkflowRequest } from '@/types';

export async function fetchWorkflows(): Promise<WorkflowDef[]> {
  const { data } = await apiClient.get<WorkflowDef[]>('/api/v1/workflows');
  return data;
}

export async function triggerWorkflow(
  workflowId: string,
  req: TriggerWorkflowRequest,
): Promise<WorkflowExecution> {
  const { data } = await apiClient.post<WorkflowExecution>(
    `/api/v1/workflows/${workflowId}/trigger`,
    req,
  );
  return data;
}

export async function fetchWorkflowStatus(
  workflowId: string,
  executionId: string,
): Promise<WorkflowExecution> {
  const { data } = await apiClient.get<WorkflowExecution>(
    `/api/v1/workflows/${workflowId}/status`,
    { params: { execution_id: executionId } },
  );
  return data;
}
