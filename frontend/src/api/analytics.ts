import apiClient from './client';
import type { AnalyticsOverview, BrandMentionTrend } from '../types';

export const analyticsApi = {
  // Get analytics overview
  getOverview: async (): Promise<AnalyticsOverview> => {
    const response = await apiClient.get<AnalyticsOverview>('/api/v1/public/overview');
    return response.data;
  },

  // Get brand mention trends over time
  getBrandTrends: async (
    brandName?: string,
    startDate?: string,
    endDate?: string
  ): Promise<BrandMentionTrend[]> => {
    const params = new URLSearchParams();
    if (brandName) params.append('brand_name', brandName);
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);

    const response = await apiClient.get<BrandMentionTrend[]>(
      `/api/v1/analytics/brand-trends?${params.toString()}`
    );
    return response.data;
  },
};
