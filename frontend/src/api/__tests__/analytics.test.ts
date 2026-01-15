/**
 * Tests for the Analytics API client
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { analyticsApi } from '../analytics'
import apiClient from '../client'

// Mock the axios client
vi.mock('../client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

describe('analyticsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getOverview', () => {
    it('should fetch analytics overview from public endpoint', async () => {
      const mockResponse = {
        data: {
          total_reports: 1500,
          total_brands: 250,
          reports_by_sentiment: {
            positive: 600,
            neutral: 500,
            negative: 400,
          },
          reports_by_provider: {
            Instagram: 500,
            TikTok: 400,
            YouTube: 350,
            RSS: 250,
          },
          recent_activity: [],
        },
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await analyticsApi.getOverview()

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/public/overview')
      expect(result.total_reports).toBe(1500)
      expect(result.total_brands).toBe(250)
      expect(result.reports_by_sentiment.positive).toBe(600)
    })

    it('should propagate API errors', async () => {
      const error = new Error('Service unavailable')
      vi.mocked(apiClient.get).mockRejectedValue(error)

      await expect(analyticsApi.getOverview()).rejects.toThrow('Service unavailable')
    })
  })

  describe('getBrandTrends', () => {
    it('should fetch brand trends without filters', async () => {
      const mockResponse = {
        data: [
          { date: '2024-01-01', brand_name: 'Nike', mention_count: 50 },
          { date: '2024-01-02', brand_name: 'Nike', mention_count: 75 },
          { date: '2024-01-03', brand_name: 'Nike', mention_count: 60 },
        ],
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await analyticsApi.getBrandTrends()

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/analytics/brand-trends?')
      expect(result).toHaveLength(3)
      expect(result[1].mention_count).toBe(75)
    })

    it('should apply brand name filter', async () => {
      const mockResponse = {
        data: [{ date: '2024-01-01', brand_name: 'Adidas', mention_count: 30 }],
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      await analyticsApi.getBrandTrends('Adidas')

      const callUrl = vi.mocked(apiClient.get).mock.calls[0][0]
      expect(callUrl).toContain('brand_name=Adidas')
    })

    it('should apply date range filters', async () => {
      const mockResponse = { data: [] }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      await analyticsApi.getBrandTrends(undefined, '2024-01-01', '2024-01-31')

      const callUrl = vi.mocked(apiClient.get).mock.calls[0][0]
      expect(callUrl).toContain('start_date=2024-01-01')
      expect(callUrl).toContain('end_date=2024-01-31')
    })

    it('should apply all filters together', async () => {
      const mockResponse = { data: [] }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      await analyticsApi.getBrandTrends('Nike', '2024-06-01', '2024-06-30')

      const callUrl = vi.mocked(apiClient.get).mock.calls[0][0]
      expect(callUrl).toContain('brand_name=Nike')
      expect(callUrl).toContain('start_date=2024-06-01')
      expect(callUrl).toContain('end_date=2024-06-30')
    })

    it('should return empty array when no data', async () => {
      const mockResponse = { data: [] }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await analyticsApi.getBrandTrends('NonExistent')

      expect(result).toEqual([])
    })
  })
})
