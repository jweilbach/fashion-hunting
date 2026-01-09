import apiClient from './client';
import type { Report, ReportsFilters, PaginatedResponse } from '../types';

export interface ReportsQueryParams extends ReportsFilters {
  source_type?: string;
  search?: string;
}

// Map frontend provider IDs to backend provider names
const PROVIDER_NAME_MAP: Record<string, string> = {
  'INSTAGRAM': 'INSTAGRAM',
  'TIKTOK': 'TikTok',
  'YOUTUBE': 'YouTube',
  'GOOGLE_SEARCH': 'GOOGLE_SEARCH',
  'RSS': 'RSS',
};

export const reportsApi = {
  // Get all reports with optional filters
  getReports: async (filters?: ReportsQueryParams): Promise<PaginatedResponse<Report>> => {
    const params = new URLSearchParams();

    if (filters) {
      // Map provider ID to backend provider name
      if (filters.provider) {
        const backendProvider = PROVIDER_NAME_MAP[filters.provider] || filters.provider;
        params.append('provider', backendProvider);
      }
      if (filters.sentiment) params.append('sentiment', filters.sentiment);
      if (filters.topic) params.append('topic', filters.topic);
      if (filters.brand) params.append('brand', filters.brand);
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);
      if (filters.source_type) params.append('source_type', filters.source_type);
      if (filters.search) params.append('search', filters.search);

      // Convert skip/limit to page/page_size for backend
      const limit = filters.limit ?? 50;
      const skip = filters.skip ?? 0;
      const page = Math.floor(skip / limit) + 1;
      params.append('page', page.toString());
      params.append('page_size', limit.toString());
    }

    // Backend returns { items, total, page, page_size, pages }
    // Frontend expects { items, total, skip, limit }
    const response = await apiClient.get<{
      items: Report[];
      total: number;
      page: number;
      page_size: number;
      pages: number;
    }>(`/api/v1/reports?${params.toString()}`);

    // Transform response to frontend format
    const { items, total, page: respPage, page_size } = response.data;
    return {
      items,
      total,
      skip: (respPage - 1) * page_size,
      limit: page_size,
    };
  },

  // Get single report by ID
  getReport: async (id: string): Promise<Report> => {
    const response = await apiClient.get<Report>(`/api/v1/reports/${id}`);
    return response.data;
  },

  // Get recent reports
  getRecentReports: async (limit: number = 10, skip: number = 0, sourceType?: string): Promise<PaginatedResponse<Report>> => {
    const params = new URLSearchParams();
    params.append('limit', limit.toString());
    params.append('skip', skip.toString());
    if (sourceType) {
      params.append('source_type', sourceType);
    }
    const response = await apiClient.get<PaginatedResponse<Report>>(`/api/v1/public/reports/recent?${params.toString()}`);
    return response.data;
  },

  // Delete a report
  deleteReport: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/v1/reports/${id}`);
  },
};
