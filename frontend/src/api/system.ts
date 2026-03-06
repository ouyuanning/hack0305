import apiClient from './client';

export interface SystemResetRequest {
  confirm: boolean;
}

export interface SystemResetResponse {
  success: boolean;
  message: string;
  deleted_paths?: string[];
  deleted_volume: boolean;
}

export async function resetSystem(req: SystemResetRequest): Promise<SystemResetResponse> {
  const { data } = await apiClient.post<SystemResetResponse>('/api/v1/system/reset', req);
  return data;
}
