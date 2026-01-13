import apiClient from './client';

export interface ScheduledJob {
  id: string;
  tenant_id: string;
  job_type: string;
  schedule_cron: string;
  enabled: boolean;
  config: {
    name?: string;
    brand_ids?: string[];
    feed_ids?: string[];
    [key: string]: any;
  };
  last_run?: string;
  last_status?: string;
  last_error?: string;
  next_run?: string;
  run_count: number;
  created_at: string;
  updated_at: string;
}

export interface ScheduledJobCreate {
  job_type?: string;
  schedule_cron: string;
  enabled?: boolean;
  config: {
    name: string;
    brand_ids: string[];
    feed_ids: string[];
    [key: string]: any;
  };
}

export interface ScheduledJobUpdate {
  schedule_cron?: string;
  enabled?: boolean;
  config?: {
    name?: string;
    brand_ids?: string[];
    feed_ids?: string[];
    [key: string]: any;
  };
}

export interface JobRunResponse {
  message: string;
  job_id: string;
  status: string;
}

export interface JobExecution {
  id: string;
  job_id: string;
  tenant_id: string;
  started_at: string;
  completed_at?: string;
  status: string;
  items_processed: number;
  items_failed: number;
  error_message?: string;
  execution_log?: string;
  total_items: number;
  current_item_index: number;
  current_item_title?: string;
  celery_task_id?: string;
  created_at: string;
}

export const jobsApi = {
  getJobs: async (): Promise<ScheduledJob[]> => {
    const response = await apiClient.get<ScheduledJob[]>('/api/v1/jobs/');
    return response.data;
  },

  getJob: async (id: string): Promise<ScheduledJob> => {
    const response = await apiClient.get<ScheduledJob>(`/api/v1/jobs/${id}`);
    return response.data;
  },

  createJob: async (data: ScheduledJobCreate): Promise<ScheduledJob> => {
    const response = await apiClient.post<ScheduledJob>('/api/v1/jobs/', data);
    return response.data;
  },

  updateJob: async (id: string, data: ScheduledJobUpdate): Promise<ScheduledJob> => {
    const response = await apiClient.put<ScheduledJob>(`/api/v1/jobs/${id}`, data);
    return response.data;
  },

  deleteJob: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/v1/jobs/${id}`);
  },

  runJobNow: async (id: string): Promise<JobRunResponse> => {
    const response = await apiClient.post<JobRunResponse>(`/api/v1/jobs/${id}/run`);
    return response.data;
  },

  getAllExecutions: async (limit: number = 100): Promise<JobExecution[]> => {
    const response = await apiClient.get<JobExecution[]>(`/api/v1/jobs/executions/?limit=${limit}`);
    return response.data;
  },

  getJobExecutions: async (jobId: string, limit: number = 50): Promise<JobExecution[]> => {
    const response = await apiClient.get<JobExecution[]>(`/api/v1/jobs/${jobId}/executions?limit=${limit}`);
    return response.data;
  },
};
