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

// ============================================================================
// Brand 360 Types
// ============================================================================

/**
 * Individual search entry for a provider
 */
export interface SearchEntry {
  type: string; // Provider-specific: 'profile' | 'hashtag' | 'mentions' | 'user' | 'keyword' | 'channel' | 'search' | 'video' | 'rss_keyword'
  value: string; // The search term/handle/hashtag (without # or @)
  count: number; // Number of results to fetch (1-100, default from tenant settings)
}

/**
 * Per-provider configuration for Brand 360
 */
export interface ProviderConfig {
  enabled: boolean;
  handle?: string; // Instagram/TikTok username
  channel_id?: string; // YouTube channel ID (UCxxx)
  channel_handle?: string; // YouTube @handle
  searches: SearchEntry[];
}

/**
 * Social profiles structure for brand configuration
 */
export interface SocialProfiles {
  instagram?: ProviderConfig;
  tiktok?: ProviderConfig;
  youtube?: ProviderConfig;
  google_news?: ProviderConfig;
  google_search?: ProviderConfig;
}

/**
 * Search type option (from backend providers)
 */
export interface SearchTypeOption {
  value: string;
  label: string;
}

/**
 * Provider metadata (from backend registry)
 */
export interface ProviderMetadata {
  name: string;
  display_name: string;
  search_types: SearchTypeOption[];
  requires_handle: boolean;
  handle_placeholder: string;
  handle_label: string;
  icon: string;
  is_social_media: boolean;
}

export interface Brand {
  id: string;
  tenant_id: string;
  brand_name: string;
  aliases?: string[];
  is_known_brand: boolean;
  should_ignore?: boolean;
  category?: string;
  notes?: string;
  social_profiles?: SocialProfiles; // Brand 360
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
  feed_type?: string;
  feed_value: string;
  feed_url?: string;
  search_query?: string;
  label?: string;
  enabled: boolean;
  is_enabled?: boolean; // Alias for backwards compatibility
  fetch_count?: number;
  config?: Record<string, any>;
  brand_id?: string; // Brand 360 - FK to brand
  is_auto_generated?: boolean; // Brand 360 - true if created from brand social_profiles
  fetch_frequency?: string;
  last_fetched?: string;
  last_error?: string;
  fetch_count_success?: number;
  fetch_count_failed?: number;
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

// ============================================================================
// Summary Types (Brand 360)
// ============================================================================

/**
 * AI-generated PDF summary document
 */
export interface Summary {
  id: string;
  tenant_id: string;
  job_id?: string;
  execution_id?: string;
  brand_ids: string[];
  title: string;
  executive_summary?: string;
  period_start?: string;
  period_end?: string;
  file_path?: string;
  file_size_bytes?: number;
  report_count: number;
  generation_status: 'pending' | 'generating' | 'completed' | 'failed';
  generation_error?: string;
  created_at: string;
  updated_at: string;
}

export interface SummaryListResponse {
  items: Summary[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

// ============================================================================
// Job Types (updated for Brand 360)
// ============================================================================

export interface Job {
  id: string;
  tenant_id: string;
  job_type: string;
  schedule_cron: string;
  enabled: boolean;
  config: Record<string, any>;
  generate_summary?: boolean; // Brand 360 - whether to create AI summary after execution
  last_run?: string;
  last_status?: string;
  last_error?: string;
  next_run?: string;
  run_count?: number;
  created_at: string;
  updated_at: string;
}

export interface JobExecution {
  id: string;
  job_id: string;
  tenant_id: string;
  started_at: string;
  completed_at?: string;
  status: 'running' | 'success' | 'failed' | 'partial';
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
