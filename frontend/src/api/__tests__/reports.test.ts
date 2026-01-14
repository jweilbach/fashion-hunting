/**
 * Tests for the Reports API client
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { reportsApi } from '../reports'
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

// Mock window for exportReports tests
const mockCreateObjectURL = vi.fn(() => 'blob:mock-url')
const mockRevokeObjectURL = vi.fn()
Object.defineProperty(window, 'URL', {
  value: {
    createObjectURL: mockCreateObjectURL,
    revokeObjectURL: mockRevokeObjectURL,
  },
})

describe('reportsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getReports', () => {
    it('should fetch reports with default pagination', async () => {
      const mockResponse = {
        data: {
          items: [
            { id: 'report-1', title: 'Report 1', sentiment: 'positive' },
            { id: 'report-2', title: 'Report 2', sentiment: 'negative' },
          ],
          total: 100,
          page: 1,
          page_size: 50,
          pages: 2,
        },
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await reportsApi.getReports()

      expect(apiClient.get).toHaveBeenCalled()
      expect(result.items).toHaveLength(2)
      expect(result.total).toBe(100)
      expect(result.skip).toBe(0)
      expect(result.limit).toBe(50)
    })

    it('should apply provider filter with backend name mapping', async () => {
      const mockResponse = {
        data: {
          items: [],
          total: 0,
          page: 1,
          page_size: 50,
          pages: 0,
        },
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      await reportsApi.getReports({ provider: 'TIKTOK' })

      const callUrl = vi.mocked(apiClient.get).mock.calls[0][0]
      expect(callUrl).toContain('provider=TikTok')
    })

    it('should apply sentiment filter', async () => {
      const mockResponse = {
        data: { items: [], total: 0, page: 1, page_size: 50, pages: 0 },
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      await reportsApi.getReports({ sentiment: 'positive' })

      const callUrl = vi.mocked(apiClient.get).mock.calls[0][0]
      expect(callUrl).toContain('sentiment=positive')
    })

    it('should apply search filter', async () => {
      const mockResponse = {
        data: { items: [], total: 0, page: 1, page_size: 50, pages: 0 },
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      await reportsApi.getReports({ search: 'nike shoes' })

      const callUrl = vi.mocked(apiClient.get).mock.calls[0][0]
      expect(callUrl).toContain('search=nike+shoes')
    })

    it('should convert skip/limit to page/page_size', async () => {
      const mockResponse = {
        data: { items: [], total: 200, page: 3, page_size: 25, pages: 8 },
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await reportsApi.getReports({ skip: 50, limit: 25 })

      const callUrl = vi.mocked(apiClient.get).mock.calls[0][0]
      expect(callUrl).toContain('page=3')
      expect(callUrl).toContain('page_size=25')
      // Response should convert back to skip/limit format
      expect(result.skip).toBe(50)
      expect(result.limit).toBe(25)
    })

    it('should apply date range filters', async () => {
      const mockResponse = {
        data: { items: [], total: 0, page: 1, page_size: 50, pages: 0 },
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      await reportsApi.getReports({
        start_date: '2024-01-01',
        end_date: '2024-12-31',
      })

      const callUrl = vi.mocked(apiClient.get).mock.calls[0][0]
      expect(callUrl).toContain('start_date=2024-01-01')
      expect(callUrl).toContain('end_date=2024-12-31')
    })
  })

  describe('getReport', () => {
    it('should fetch single report by ID', async () => {
      const mockResponse = {
        data: {
          id: 'report-123',
          title: 'Test Report',
          content: 'Full content here',
          sentiment: 'neutral',
          provider: 'Instagram',
        },
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await reportsApi.getReport('report-123')

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/reports/report-123')
      expect(result.title).toBe('Test Report')
      expect(result.sentiment).toBe('neutral')
    })

    it('should propagate errors for non-existent reports', async () => {
      const error = new Error('Report not found')
      vi.mocked(apiClient.get).mockRejectedValue(error)

      await expect(reportsApi.getReport('non-existent')).rejects.toThrow('Report not found')
    })
  })

  describe('getRecentReports', () => {
    it('should fetch recent reports with default parameters', async () => {
      const mockResponse = {
        data: {
          items: [{ id: 'report-1', title: 'Recent Report' }],
          total: 50,
          skip: 0,
          limit: 10,
        },
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await reportsApi.getRecentReports()

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/public/reports/recent?limit=10&skip=0')
      expect(result.items).toHaveLength(1)
    })

    it('should support custom limit and skip', async () => {
      const mockResponse = {
        data: { items: [], total: 0, skip: 20, limit: 5 },
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      await reportsApi.getRecentReports(5, 20)

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/public/reports/recent?limit=5&skip=20')
    })

    it('should apply source type filter', async () => {
      const mockResponse = {
        data: { items: [], total: 0, skip: 0, limit: 10 },
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      await reportsApi.getRecentReports(10, 0, 'social')

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/public/reports/recent?limit=10&skip=0&source_type=social')
    })
  })

  describe('deleteReport', () => {
    it('should delete report by ID', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({})

      await reportsApi.deleteReport('report-123')

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/reports/report-123')
    })

    it('should propagate deletion errors', async () => {
      const error = new Error('Permission denied')
      vi.mocked(apiClient.delete).mockRejectedValue(error)

      await expect(reportsApi.deleteReport('report-123')).rejects.toThrow('Permission denied')
    })
  })

  describe('exportReports', () => {
    // Mock anchor click to prevent JSDOM navigation warnings
    const mockClick = vi.fn()

    beforeEach(() => {
      // Mock DOM manipulation and prevent actual navigation
      vi.spyOn(document.body, 'appendChild').mockImplementation((node) => {
        // Mock the click method on the anchor element to prevent navigation
        if (node instanceof HTMLAnchorElement) {
          node.click = mockClick
        }
        return node
      })
      vi.spyOn(document.body, 'removeChild').mockImplementation(() => document.createElement('a'))
      mockClick.mockClear()
    })

    it('should export reports as CSV', async () => {
      const mockBlob = new Blob(['csv,data'])
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockBlob })

      await reportsApi.exportReports({ format: 'csv' })

      const callUrl = vi.mocked(apiClient.post).mock.calls[0][0]
      expect(callUrl).toContain('format=csv')
      expect(mockCreateObjectURL).toHaveBeenCalled()
      expect(mockRevokeObjectURL).toHaveBeenCalled()
    })

    it('should export reports as Excel', async () => {
      const mockBlob = new Blob(['excel data'])
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockBlob })

      await reportsApi.exportReports({ format: 'excel' })

      const callUrl = vi.mocked(apiClient.post).mock.calls[0][0]
      expect(callUrl).toContain('format=excel')
    })

    it('should include filters in export request', async () => {
      const mockBlob = new Blob(['data'])
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockBlob })

      await reportsApi.exportReports({
        format: 'csv',
        provider: 'INSTAGRAM',
        sentiment: 'positive',
        brand: 'Nike',
      })

      const callUrl = vi.mocked(apiClient.post).mock.calls[0][0]
      expect(callUrl).toContain('provider=INSTAGRAM')
      expect(callUrl).toContain('sentiment=positive')
      expect(callUrl).toContain('brand=Nike')
    })

    it('should include report IDs when provided', async () => {
      const mockBlob = new Blob(['data'])
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockBlob })

      await reportsApi.exportReports({
        format: 'csv',
        report_ids: ['id-1', 'id-2', 'id-3'],
      })

      const callUrl = vi.mocked(apiClient.post).mock.calls[0][0]
      expect(callUrl).toContain('report_ids=id-1')
      expect(callUrl).toContain('report_ids=id-2')
      expect(callUrl).toContain('report_ids=id-3')
    })
  })
})
