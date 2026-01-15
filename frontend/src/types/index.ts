// TypeScript types matching the FastAPI backend models

export interface Report {
  id: string;
  tenant_id: string;
  dedupe_key?: string;
  timestamp: string;
  source: string;
  provider: string;
  source_type?: 'digital' | 'social' | 'broadcast';
  brands: string[];
  title: string;
  link: string;
  summary: string;
  full_text?: string;
  sentiment: 'positive' | 'neutral' | 'negative';
  topic: string;
  est_reach: number;
  raw_data?: Record<string, any>;
  processing_status: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
  is_new?: boolean; // Computed by backend: true if created in last 24 hours
}

export interface Brand {
  id: string;
  tenant_id: string;
  brand_name: string;
  is_known_brand: boolean;
  category?: string;
  mention_count: number;
  last_mentioned?: string;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface Feed {
  id: string;
  tenant_id: string;
  provider: string;
  feed_url?: string;
  search_query?: string;
  is_enabled: boolean;
  fetch_frequency?: string;
  last_fetched?: string;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: string;
  tenant_id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  full_name?: string;
  role: 'admin' | 'editor' | 'viewer';
  is_active: boolean;
  is_superuser?: boolean;
  last_login?: string;
  created_at: string;
  updated_at: string;
}

export interface Tenant {
  id: string;
  name: string;
  is_active: boolean;
  settings?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

// API Request/Response types
export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface ReportsFilters {
  provider?: string;
  sentiment?: string;
  topic?: string;
  brand?: string;
  start_date?: string;
  end_date?: string;
  skip?: number;
  limit?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

// Analytics types
export interface BrandMentionTrend {
  brand_name: string;
  date: string;
  mention_count: number;
}

export interface SentimentDistribution {
  sentiment: 'positive' | 'neutral' | 'negative';
  count: number;
  percentage: number;
}

export interface TopSource {
  source: string;
  count: number;
}

export interface TopicDistribution {
  topic: string;
  count: number;
  percentage: number;
}

export interface AnalyticsOverview {
  total_reports: number;
  total_brands: number;
  active_feeds: number;
  sentiment_distribution: SentimentDistribution[];
  top_sources: TopSource[];
  topic_distribution: TopicDistribution[];
  recent_reports: Report[];
}

// Chart data types
export interface TimeSeriesData {
  date: string;
  value: number;
  label?: string;
}

export interface PieChartData {
  name: string;
  value: number;
  percentage?: number;
}

export interface BarChartData {
  name: string;
  value: number;
}

// List types
export interface List {
  id: string;
  tenant_id: string;
  name: string;
  list_type: 'report' | 'contact' | 'editor';
  description?: string;
  created_by?: string;
  creator_name?: string;
  item_count: number;
  created_at: string;
  updated_at: string;
}

export interface ListItem {
  id: string;
  list_id: string;
  item_id: string;
  added_by?: string;
  adder_name?: string;
  added_at: string;
  updated_at: string;
}

export interface ListWithReports extends List {
  reports: Report[];
}

export interface ListCreate {
  name: string;
  list_type?: 'report' | 'contact' | 'editor';
  description?: string;
}

export interface ListUpdate {
  name?: string;
  description?: string;
}
