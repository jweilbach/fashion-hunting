import apiClient from './client';

export interface Feed {
  id: string;
  tenant_id: string;
  provider: string; // RSS, TikTok, Instagram
  feed_type: string; // hashtag, keyword, user, rss_url
  feed_value: string; // The actual URL, hashtag, username
  label?: string;
  enabled: boolean;
  fetch_count: number;
  config?: Record<string, any>;
  last_fetched?: string;
  last_error?: string;
  fetch_count_success: number;
  fetch_count_failed: number;
  created_at: string;
  updated_at: string;
}

export interface FeedCreate {
  provider: string;
  feed_type: string;
  feed_value: string;
  label?: string;
  enabled?: boolean;
  fetch_count?: number;
  config?: Record<string, any>;
}

export interface FeedUpdate {
  enabled?: boolean;
  label?: string;
  fetch_count?: number;
  config?: Record<string, any>;
}

export const feedsApi = {
  getFeeds: async (
    provider?: string,
    enabled_only?: boolean
  ): Promise<Feed[]> => {
    const params = new URLSearchParams();
    if (provider) params.append('provider', provider);
    if (enabled_only !== undefined) params.append('enabled_only', String(enabled_only));

    const queryString = params.toString();
    const url = `/api/v1/feeds/${queryString ? `?${queryString}` : ''}`;

    const response = await apiClient.get<Feed[]>(url);
    return response.data;
  },

  getFeed: async (id: string): Promise<Feed> => {
    const response = await apiClient.get<Feed>(`/api/v1/feeds/${id}`);
    return response.data;
  },

  createFeed: async (data: FeedCreate): Promise<Feed> => {
    const response = await apiClient.post<Feed>(`/api/v1/feeds/`, data);
    return response.data;
  },

  updateFeed: async (id: string, data: FeedUpdate): Promise<Feed> => {
    const response = await apiClient.put<Feed>(`/api/v1/feeds/${id}`, data);
    return response.data;
  },

  deleteFeed: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/v1/feeds/${id}`);
  },
};
