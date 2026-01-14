/**
 * MSW Request Handlers
 *
 * Define mock API responses for testing. These handlers intercept
 * network requests during tests and return mock data.
 */
import { http, HttpResponse } from 'msw'

// Base URL for API requests
const API_BASE = '/api/v1'

export const handlers = [
  // ==================== Auth Endpoints ====================

  http.post(`${API_BASE}/auth/login`, () => {
    return HttpResponse.json({
      access_token: 'mock-jwt-token',
      token_type: 'bearer',
      user: {
        id: 'user-123',
        email: 'test@example.com',
        full_name: 'Test User',
        role: 'editor',
        tenant_id: 'tenant-123',
      },
    })
  }),

  http.get(`${API_BASE}/auth/me`, () => {
    return HttpResponse.json({
      id: 'user-123',
      email: 'test@example.com',
      full_name: 'Test User',
      role: 'editor',
      tenant_id: 'tenant-123',
    })
  }),

  // ==================== Lists Endpoints ====================

  http.get(`${API_BASE}/lists/types/`, () => {
    return HttpResponse.json({
      types: [
        { id: 'report', label: 'Reports', description: 'Collection of media reports' },
      ],
    })
  }),

  http.get(`${API_BASE}/lists/`, () => {
    return HttpResponse.json({
      items: [
        {
          id: 'list-1',
          name: 'Test List 1',
          list_type: 'report',
          description: 'First test list',
          item_count: 5,
          created_at: '2024-01-15T10:00:00Z',
          updated_at: '2024-01-15T10:00:00Z',
        },
        {
          id: 'list-2',
          name: 'Test List 2',
          list_type: 'report',
          description: 'Second test list',
          item_count: 10,
          created_at: '2024-01-14T10:00:00Z',
          updated_at: '2024-01-14T10:00:00Z',
        },
      ],
      total: 2,
      page: 1,
      page_size: 50,
      pages: 1,
    })
  }),

  http.post(`${API_BASE}/lists/`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json(
      {
        id: 'new-list-id',
        name: body.name,
        list_type: body.list_type,
        description: body.description,
        item_count: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      { status: 201 }
    )
  }),

  // ==================== Reports Endpoints ====================

  http.get(`${API_BASE}/reports/`, () => {
    return HttpResponse.json({
      items: [
        {
          id: 'report-1',
          title: 'Test Report 1',
          source: 'Example News',
          provider: 'google_search',
          link: 'https://example.com/article-1',
          timestamp: '2024-01-15T10:00:00Z',
          summary: 'This is a test report summary.',
          sentiment: 'positive',
          brands: ['Brand A', 'Brand B'],
          est_reach: 50000,
        },
        {
          id: 'report-2',
          title: 'Test Report 2',
          source: 'Another Source',
          provider: 'instagram',
          link: 'https://instagram.com/p/123',
          timestamp: '2024-01-14T10:00:00Z',
          summary: 'Another test report.',
          sentiment: 'neutral',
          brands: ['Brand C'],
          est_reach: 25000,
        },
      ],
      total: 2,
      page: 1,
      page_size: 10,
      pages: 1,
    })
  }),

  // ==================== Brands Endpoints ====================

  http.get(`${API_BASE}/brands/`, () => {
    return HttpResponse.json({
      items: [
        {
          id: 'brand-1',
          name: 'Brand A',
          aliases: ['BrandA', 'BA'],
          is_active: true,
        },
        {
          id: 'brand-2',
          name: 'Brand B',
          aliases: [],
          is_active: true,
        },
      ],
      total: 2,
      page: 1,
      page_size: 50,
      pages: 1,
    })
  }),

  // ==================== Analytics Endpoints ====================

  http.get(`${API_BASE}/analytics/summary`, () => {
    return HttpResponse.json({
      period_days: 30,
      total_reports: 150,
      avg_daily_reports: 5.0,
      total_estimated_reach: 2500000,
      sentiment: {
        counts: { positive: 80, neutral: 50, negative: 20 },
        percentages: { positive: 53.33, neutral: 33.33, negative: 13.33 },
      },
      top_brands: [
        { brand: 'Brand A', mentions: 45 },
        { brand: 'Brand B', mentions: 30 },
      ],
      providers: {
        google_search: { report_count: 100, total_reach: 2000000 },
        instagram: { report_count: 50, total_reach: 500000 },
      },
    })
  }),

  // ==================== Jobs Endpoints ====================

  http.get(`${API_BASE}/jobs/`, () => {
    return HttpResponse.json({
      items: [
        {
          id: 'job-1',
          name: 'Daily News Fetch',
          feed_id: 'feed-1',
          schedule: '0 8 * * *',
          is_active: true,
          last_run: '2024-01-15T08:00:00Z',
          next_run: '2024-01-16T08:00:00Z',
          status: 'completed',
        },
      ],
      total: 1,
      page: 1,
      page_size: 50,
      pages: 1,
    })
  }),

  // ==================== Feeds Endpoints ====================

  http.get(`${API_BASE}/feeds/`, () => {
    return HttpResponse.json({
      items: [
        {
          id: 'feed-1',
          name: 'Google News Feed',
          feed_type: 'google_search',
          is_active: true,
          config: { query: 'fashion news' },
        },
      ],
      total: 1,
      page: 1,
      page_size: 50,
      pages: 1,
    })
  }),

  // ==================== Health Check ====================

  http.get('/health', () => {
    return HttpResponse.json({
      status: 'healthy',
      version: '1.0.0',
      database: 'healthy',
      redis: 'healthy',
      timestamp: new Date().toISOString(),
    })
  }),
]
