/**
 * Tests for the Lists API client
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { listsApi } from '../lists'
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

describe('listsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getListTypes', () => {
    it('should fetch list types from correct endpoint', async () => {
      const mockResponse = {
        data: {
          types: [
            { id: 'report', label: 'Reports', description: 'Collection of reports' },
          ],
        },
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await listsApi.getListTypes()

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/lists/types/')
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('getLists', () => {
    it('should fetch lists with default pagination', async () => {
      const mockResponse = {
        data: {
          items: [],
          total: 0,
          page: 1,
          page_size: 50,
          pages: 1,
        },
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await listsApi.getLists()

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/lists/?page=1&page_size=50')
      expect(result).toEqual(mockResponse.data)
    })

    it('should include list_type filter when provided', async () => {
      const mockResponse = { data: { items: [], total: 0, page: 1, page_size: 50, pages: 1 } }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      await listsApi.getLists('report')

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/lists/?list_type=report&page=1&page_size=50')
    })

    it('should handle custom pagination', async () => {
      const mockResponse = { data: { items: [], total: 100, page: 2, page_size: 25, pages: 4 } }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      await listsApi.getLists(undefined, 2, 25)

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/lists/?page=2&page_size=25')
    })
  })

  describe('getList', () => {
    it('should fetch single list with items by default', async () => {
      const mockResponse = {
        data: {
          id: 'list-123',
          name: 'Test List',
          reports: [],
        },
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await listsApi.getList('list-123')

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/lists/list-123?include_items=true')
      expect(result).toEqual(mockResponse.data)
    })

    it('should fetch list without items when specified', async () => {
      const mockResponse = { data: { id: 'list-123', name: 'Test List' } }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      await listsApi.getList('list-123', false)

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/lists/list-123?include_items=false')
    })
  })

  describe('createList', () => {
    it('should create list with provided data', async () => {
      const mockResponse = { data: { id: 'new-list', name: 'New List', list_type: 'report' } }
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

      const createData = {
        name: 'New List',
        list_type: 'report' as const,
        description: 'A new list',
      }

      const result = await listsApi.createList(createData)

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/lists/', createData)
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('updateList', () => {
    it('should update list with provided data', async () => {
      const mockResponse = { data: { id: 'list-123', name: 'Updated Name' } }
      vi.mocked(apiClient.put).mockResolvedValue(mockResponse)

      const result = await listsApi.updateList('list-123', { name: 'Updated Name' })

      expect(apiClient.put).toHaveBeenCalledWith('/api/v1/lists/list-123', { name: 'Updated Name' })
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('deleteList', () => {
    it('should delete list by ID', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({})

      await listsApi.deleteList('list-123')

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/lists/list-123')
    })
  })

  describe('addItems', () => {
    it('should add items to list in bulk', async () => {
      const mockResponse = {
        data: {
          added_count: 2,
          items: [{ id: 'item-1' }, { id: 'item-2' }],
        },
      }
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

      const result = await listsApi.addItems('list-123', ['item-1', 'item-2'])

      expect(apiClient.post).toHaveBeenCalledWith(
        '/api/v1/lists/list-123/items/bulk/',
        { item_ids: ['item-1', 'item-2'] }
      )
      expect(result.added_count).toBe(2)
    })
  })

  describe('removeItems', () => {
    it('should remove items from list in bulk', async () => {
      const mockResponse = { data: { removed_count: 2 } }
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse)

      const result = await listsApi.removeItems('list-123', ['item-1', 'item-2'])

      expect(apiClient.delete).toHaveBeenCalledWith(
        '/api/v1/lists/list-123/items/bulk/',
        { data: { item_ids: ['item-1', 'item-2'] } }
      )
      expect(result.removed_count).toBe(2)
    })
  })

  describe('addItemsToMultipleLists', () => {
    it('should add items to multiple lists at once', async () => {
      const mockResponse = {
        data: {
          results: {
            'list-1': { added_count: 2 },
            'list-2': { added_count: 2 },
          },
        },
      }
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

      const result = await listsApi.addItemsToMultipleLists(
        ['list-1', 'list-2'],
        ['item-1', 'item-2']
      )

      expect(apiClient.post).toHaveBeenCalledWith(
        '/api/v1/lists/bulk-add/',
        { list_ids: ['list-1', 'list-2'], item_ids: ['item-1', 'item-2'] }
      )
      expect(result.results).toHaveProperty('list-1')
      expect(result.results).toHaveProperty('list-2')
    })
  })

  describe('getListsContainingItem', () => {
    it('should fetch lists containing specific item', async () => {
      const mockResponse = {
        data: [
          { id: 'list-1', name: 'List 1' },
          { id: 'list-2', name: 'List 2' },
        ],
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await listsApi.getListsContainingItem('item-123')

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/lists/containing/item-123')
      expect(result).toHaveLength(2)
    })
  })
})
