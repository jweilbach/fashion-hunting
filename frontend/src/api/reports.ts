import apiClient from './client';
import type { Report, ReportsFilters, PaginatedResponse } from '../types';

export const reportsApi = {
  // Get all reports with optional filters
  getReports: async (filters?: ReportsFilters): Promise<PaginatedResponse<Report>> => {
    const params = new URLSearchParams();

    if (filters) {
      if (filters.provider) params.append('provider', filters.provider);
      if (filters.sentiment) params.append('sentiment', filters.sentiment);
      if (filters.topic) params.append('topic', filters.topic);
      if (filters.brand) params.append('brand', filters.brand);
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);
      if (filters.skip !== undefined) params.append('skip', filters.skip.toString());
      if (filters.limit !== undefined) params.append('limit', filters.limit.toString());
    }

    const response = await apiClient.get<PaginatedResponse<Report>>(
      `/api/v1/reports?${params.toString()}`
    );
    return response.data;
  },

  // Get single report by ID
  getReport: async (id: string): Promise<Report> => {
    const response = await apiClient.get<Report>(`/api/v1/reports/${id}`);
    return response.data;
  },

  // Get recent reports
  getRecentReports: async (limit: number = 10): Promise<Report[]> => {
    const response = await apiClient.get<Report[]>(`/api/v1/public/reports/recent?limit=${limit}`);
    return response.data;
  },

  // Delete a report
  deleteReport: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/v1/reports/${id}`);
  },
};
