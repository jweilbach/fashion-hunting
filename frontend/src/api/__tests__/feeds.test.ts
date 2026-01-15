/**
 * Tests for the Feeds API client
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { feedsApi } from '../feeds'
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

describe('feedsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getFeeds', () => {
    it('should fetch all feeds without filters', async () => {
      const mockResponse = {
        data: [
          {
            id: 'feed-1',
            provider: 'RSS',
            feed_type: 'rss_url',
            feed_value: 'https://example.com/feed.xml',
            enabled: true,
            fetch_count: 100,
          },
          {
            id: 'feed-2',
            provider: 'TikTok',
            feed_type: 'hashtag',
            feed_value: '#fashion',
            enabled: true,
            fetch_count: 50,
          },
        ],
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await feedsApi.getFeeds()

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/feeds/')
      expect(result).toHaveLength(2)
      expect(result[0].provider).toBe('RSS')
      expect(result[1].feed_type).toBe('hashtag')
    })

    it('should filter by provider', async () => {
      const mockResponse = {
        data: [
          {
            id: 'feed-1',
            provider: 'Instagram',
            feed_type: 'user',
            feed_value: '@fashionista',
            enabled: true,
          },
        ],
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await feedsApi.getFeeds('Instagram')

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/feeds/?provider=Instagram')
      expect(result[0].provider).toBe('Instagram')
    })

    it('should filter by enabled status', async () => {
      const mockResponse = { data: [] }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      await feedsApi.getFeeds(undefined, true)

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/feeds/?enabled_only=true')
    })

    it('should apply both provider and enabled filters', async () => {
      const mockResponse = { data: [] }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      await feedsApi.getFeeds('TikTok', true)

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/feeds/?provider=TikTok&enabled_only=true')
    })

    it('should handle enabled_only=false', async () => {
      const mockResponse = { data: [] }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      await feedsApi.getFeeds(undefined, false)

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/feeds/?enabled_only=false')
    })
  })

  describe('getFeed', () => {
    it('should fetch single feed by ID', async () => {
      const mockResponse = {
        data: {
          id: 'feed-123',
          provider: 'YouTube',
          feed_type: 'keyword',
          feed_value: 'fashion trends 2024',
          label: 'Fashion Trends',
          enabled: true,
          fetch_count: 200,
          fetch_count_success: 180,
          fetch_count_failed: 20,
          last_fetched: '2024-01-15T10:00:00Z',
        },
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await feedsApi.getFeed('feed-123')

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/feeds/feed-123')
      expect(result.provider).toBe('YouTube')
      expect(result.label).toBe('Fashion Trends')
      expect(result.fetch_count_success).toBe(180)
    })

    it('should propagate errors for non-existent feeds', async () => {
      const error = new Error('Feed not found')
      vi.mocked(apiClient.get).mockRejectedValue(error)

      await expect(feedsApi.getFeed('non-existent')).rejects.toThrow('Feed not found')
    })
  })

  describe('createFeed', () => {
    it('should create feed with required fields', async () => {
      const newFeed = {
        provider: 'RSS',
        feed_type: 'rss_url',
        feed_value: 'https://news.example.com/rss',
      }
      const mockResponse = {
        data: {
          id: 'new-feed-id',
          tenant_id: 'tenant-123',
          enabled: true,
          fetch_count: 0,
          fetch_count_success: 0,
          fetch_count_failed: 0,
          created_at: '2024-01-15T12:00:00Z',
          updated_at: '2024-01-15T12:00:00Z',
          ...newFeed,
        },
      }
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

      const result = await feedsApi.createFeed(newFeed)

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/feeds/', newFeed)
      expect(result.id).toBe('new-feed-id')
      expect(result.provider).toBe('RSS')
      expect(result.fetch_count).toBe(0)
    })

    it('should create feed with optional fields', async () => {
      const newFeed = {
        provider: 'TikTok',
        feed_type: 'hashtag',
        feed_value: '#streetwear',
        label: 'Streetwear Trends',
        enabled: false,
        fetch_count: 25,
        config: { min_views: 1000 },
      }
      const mockResponse = {
        data: {
          id: 'new-feed-id',
          tenant_id: 'tenant-123',
          fetch_count_success: 0,
          fetch_count_failed: 0,
          created_at: '2024-01-15T12:00:00Z',
          updated_at: '2024-01-15T12:00:00Z',
          ...newFeed,
        },
      }
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

      const result = await feedsApi.createFeed(newFeed)

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/feeds/', newFeed)
      expect(result.label).toBe('Streetwear Trends')
      expect(result.enabled).toBe(false)
      expect(result.config).toEqual({ min_views: 1000 })
    })

    it('should propagate validation errors', async () => {
      const error = new Error('Invalid feed URL')
      vi.mocked(apiClient.post).mockRejectedValue(error)

      await expect(
        feedsApi.createFeed({
          provider: 'RSS',
          feed_type: 'rss_url',
          feed_value: 'not-a-valid-url',
        })
      ).rejects.toThrow('Invalid feed URL')
    })
  })

  describe('updateFeed', () => {
    it('should update feed enabled status', async () => {
      const updateData = { enabled: false }
      const mockResponse = {
        data: {
          id: 'feed-123',
          provider: 'Instagram',
          feed_type: 'user',
          feed_value: '@brand',
          enabled: false,
          fetch_count: 50,
        },
      }
      vi.mocked(apiClient.put).mockResolvedValue(mockResponse)

      const result = await feedsApi.updateFeed('feed-123', updateData)

      expect(apiClient.put).toHaveBeenCalledWith('/api/v1/feeds/feed-123', updateData)
      expect(result.enabled).toBe(false)
    })

    it('should update feed label', async () => {
      const updateData = { label: 'New Label' }
      const mockResponse = {
        data: {
          id: 'feed-123',
          provider: 'RSS',
          feed_type: 'rss_url',
          feed_value: 'https://example.com/feed',
          label: 'New Label',
          enabled: true,
        },
      }
      vi.mocked(apiClient.put).mockResolvedValue(mockResponse)

      const result = await feedsApi.updateFeed('feed-123', updateData)

      expect(result.label).toBe('New Label')
    })

    it('should update feed config', async () => {
      const updateData = {
        config: { priority: 'high', max_items: 100 },
      }
      const mockResponse = {
        data: {
          id: 'feed-123',
          provider: 'TikTok',
          feed_type: 'hashtag',
          feed_value: '#fashion',
          enabled: true,
          config: updateData.config,
        },
      }
      vi.mocked(apiClient.put).mockResolvedValue(mockResponse)

      const result = await feedsApi.updateFeed('feed-123', updateData)

      expect(result.config).toEqual({ priority: 'high', max_items: 100 })
    })

    it('should update fetch_count', async () => {
      const updateData = { fetch_count: 50 }
      const mockResponse = {
        data: {
          id: 'feed-123',
          provider: 'YouTube',
          feed_type: 'keyword',
          feed_value: 'fashion',
          enabled: true,
          fetch_count: 50,
        },
      }
      vi.mocked(apiClient.put).mockResolvedValue(mockResponse)

      const result = await feedsApi.updateFeed('feed-123', updateData)

      expect(result.fetch_count).toBe(50)
    })
  })

  describe('deleteFeed', () => {
    it('should delete feed by ID', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({})

      await feedsApi.deleteFeed('feed-123')

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/feeds/feed-123')
    })

    it('should propagate deletion errors', async () => {
      const error = new Error('Feed in use by active job')
      vi.mocked(apiClient.delete).mockRejectedValue(error)

      await expect(feedsApi.deleteFeed('feed-123')).rejects.toThrow('Feed in use by active job')
    })
  })
})
