/**
 * Tests for the Brands API client
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { brandsApi } from '../brands'
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

describe('brandsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getBrands', () => {
    it('should fetch brands with default pagination', async () => {
      const mockResponse = {
        data: [
          { id: 'brand-1', brand_name: 'Nike', mention_count: 100 },
          { id: 'brand-2', brand_name: 'Adidas', mention_count: 80 },
        ],
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await brandsApi.getBrands()

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/brands/?skip=0&limit=1000')
      expect(result).toHaveLength(2)
      expect(result[0].brand_name).toBe('Nike')
    })

    it('should support custom skip and limit parameters', async () => {
      const mockResponse = { data: [] }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      await brandsApi.getBrands(10, 25)

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/brands/?skip=10&limit=25')
    })
  })

  describe('getBrand', () => {
    it('should fetch single brand by ID', async () => {
      const mockResponse = {
        data: {
          id: 'brand-123',
          brand_name: 'Nike',
          is_known_brand: true,
          mention_count: 100,
        },
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await brandsApi.getBrand('brand-123')

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/brands/brand-123')
      expect(result.brand_name).toBe('Nike')
      expect(result.is_known_brand).toBe(true)
    })

    it('should propagate errors for non-existent brands', async () => {
      const error = new Error('Brand not found')
      vi.mocked(apiClient.get).mockRejectedValue(error)

      await expect(brandsApi.getBrand('non-existent')).rejects.toThrow('Brand not found')
    })
  })

  describe('createBrand', () => {
    it('should create brand with provided data', async () => {
      const newBrand = {
        brand_name: 'New Brand',
        is_known_brand: true,
        category: 'Fashion',
      }
      const mockResponse = {
        data: { id: 'new-brand-id', mention_count: 0, ...newBrand },
      }
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

      const result = await brandsApi.createBrand(newBrand)

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/brands/', newBrand)
      expect(result.id).toBe('new-brand-id')
      expect(result.brand_name).toBe('New Brand')
    })
  })

  describe('updateBrand', () => {
    it('should update brand with provided data', async () => {
      const updateData = { brand_name: 'Updated Name', is_known_brand: false }
      const mockResponse = {
        data: { id: 'brand-123', brand_name: 'Updated Name', is_known_brand: false, mention_count: 50 },
      }
      vi.mocked(apiClient.put).mockResolvedValue(mockResponse)

      const result = await brandsApi.updateBrand('brand-123', updateData)

      expect(apiClient.put).toHaveBeenCalledWith('/api/v1/brands/brand-123', updateData)
      expect(result.brand_name).toBe('Updated Name')
      expect(result.is_known_brand).toBe(false)
    })
  })

  describe('deleteBrand', () => {
    it('should delete brand by ID', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({})

      await brandsApi.deleteBrand('brand-123')

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/brands/brand-123')
    })
  })

  describe('getBrandByName', () => {
    it('should fetch brand by name with URL encoding', async () => {
      const mockResponse = {
        data: { id: 'brand-123', brand_name: 'Nike Air Max' },
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await brandsApi.getBrandByName('Nike Air Max')

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/brands/name/Nike%20Air%20Max')
      expect(result.brand_name).toBe('Nike Air Max')
    })

    it('should handle special characters in brand names', async () => {
      const mockResponse = {
        data: { id: 'brand-456', brand_name: 'H&M' },
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      await brandsApi.getBrandByName('H&M')

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/brands/name/H%26M')
    })
  })

  describe('getTopBrands', () => {
    it('should fetch top brands with default parameters', async () => {
      const mockResponse = {
        data: {
          items: [
            { id: 'brand-1', brand_name: 'Nike', mention_count: 1000 },
            { id: 'brand-2', brand_name: 'Adidas', mention_count: 800 },
          ],
          total: 2,
          page: 1,
          page_size: 10,
          pages: 1,
        },
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await brandsApi.getTopBrands()

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/public/brands/top?limit=10&skip=0')
      expect(result.items).toHaveLength(2)
      expect(result.items[0].mention_count).toBe(1000)
    })

    it('should support custom limit and skip', async () => {
      const mockResponse = {
        data: { items: [], total: 0, page: 1, page_size: 5, pages: 0 },
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      await brandsApi.getTopBrands(5, 10)

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/public/brands/top?limit=5&skip=10')
    })
  })
})
