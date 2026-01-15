/**
 * Tests for the Users API client
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { usersApi } from '../users'
import apiClient from '../client'

// Mock the axios client
vi.mock('../client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

describe('usersApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('listUsers', () => {
    it('should fetch users from the correct endpoint', async () => {
      const mockResponse = {
        data: [
          {
            id: 'user-123',
            email: 'user@example.com',
            first_name: 'Test',
            last_name: 'User',
            full_name: 'Test User',
            role: 'viewer',
            is_active: true,
            last_login: '2025-01-14T12:00:00Z',
            created_at: '2025-01-01T00:00:00Z',
            updated_at: '2025-01-14T12:00:00Z',
          },
        ],
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await usersApi.listUsers()

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/users/', { params: undefined })
      expect(result).toHaveLength(1)
      expect(result[0].email).toBe('user@example.com')
    })

    it('should pass query parameters for filtering', async () => {
      const mockResponse = { data: [] }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      await usersApi.listUsers({ active_only: true, skip: 10, limit: 50 })

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/users/', {
        params: { active_only: true, skip: 10, limit: 50 },
      })
    })

    it('should propagate errors from the API', async () => {
      const error = new Error('Forbidden')
      vi.mocked(apiClient.get).mockRejectedValue(error)

      await expect(usersApi.listUsers()).rejects.toThrow('Forbidden')
    })
  })

  describe('getUserCount', () => {
    it('should fetch user count from the correct endpoint', async () => {
      const mockResponse = { data: { count: 5 } }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await usersApi.getUserCount()

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/users/count', {
        params: { active_only: undefined },
      })
      expect(result.count).toBe(5)
    })

    it('should pass active_only parameter', async () => {
      const mockResponse = { data: { count: 3 } }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      await usersApi.getUserCount(true)

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/users/count', {
        params: { active_only: true },
      })
    })
  })

  describe('getUser', () => {
    it('should fetch a specific user by ID', async () => {
      const mockResponse = {
        data: {
          id: 'user-123',
          email: 'user@example.com',
          first_name: 'Test',
          last_name: 'User',
          full_name: 'Test User',
          role: 'editor',
          is_active: true,
          last_login: null,
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-14T12:00:00Z',
        },
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await usersApi.getUser('user-123')

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/users/user-123')
      expect(result.id).toBe('user-123')
      expect(result.role).toBe('editor')
    })

    it('should propagate 404 errors', async () => {
      const error = new Error('Not Found')
      vi.mocked(apiClient.get).mockRejectedValue(error)

      await expect(usersApi.getUser('nonexistent')).rejects.toThrow('Not Found')
    })
  })

  describe('createUser', () => {
    it('should send create user request to the correct endpoint', async () => {
      const mockResponse = {
        data: {
          id: 'new-user-123',
          email: 'newuser@example.com',
          first_name: 'New',
          last_name: 'User',
          full_name: 'New User',
          role: 'viewer',
          is_active: true,
          last_login: null,
          created_at: '2025-01-15T00:00:00Z',
          updated_at: '2025-01-15T00:00:00Z',
        },
      }
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

      const result = await usersApi.createUser({
        email: 'newuser@example.com',
        first_name: 'New',
        last_name: 'User',
        role: 'viewer',
      })

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/users/', {
        email: 'newuser@example.com',
        first_name: 'New',
        last_name: 'User',
        role: 'viewer',
      })
      expect(result.email).toBe('newuser@example.com')
      expect(result.role).toBe('viewer')
    })

    it('should handle email-only creation', async () => {
      const mockResponse = {
        data: {
          id: 'new-user-456',
          email: 'minimal@example.com',
          first_name: null,
          last_name: null,
          full_name: null,
          role: 'viewer',
          is_active: true,
          last_login: null,
          created_at: '2025-01-15T00:00:00Z',
          updated_at: '2025-01-15T00:00:00Z',
        },
      }
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

      const result = await usersApi.createUser({ email: 'minimal@example.com' })

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/users/', {
        email: 'minimal@example.com',
      })
      expect(result.email).toBe('minimal@example.com')
    })

    it('should propagate duplicate email errors', async () => {
      const error = new Error('User already exists')
      vi.mocked(apiClient.post).mockRejectedValue(error)

      await expect(
        usersApi.createUser({ email: 'existing@example.com' })
      ).rejects.toThrow('User already exists')
    })
  })

  describe('updateUserRole', () => {
    it('should send role update to the correct endpoint', async () => {
      const mockResponse = {
        data: {
          id: 'user-123',
          email: 'user@example.com',
          first_name: 'Test',
          last_name: 'User',
          full_name: 'Test User',
          role: 'admin',
          is_active: true,
          last_login: null,
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-15T00:00:00Z',
        },
      }
      vi.mocked(apiClient.patch).mockResolvedValue(mockResponse)

      const result = await usersApi.updateUserRole('user-123', { role: 'admin' })

      expect(apiClient.patch).toHaveBeenCalledWith('/api/v1/users/user-123/role', {
        role: 'admin',
      })
      expect(result.role).toBe('admin')
    })

    it('should propagate self-modification errors', async () => {
      const error = new Error('Cannot change your own role')
      vi.mocked(apiClient.patch).mockRejectedValue(error)

      await expect(
        usersApi.updateUserRole('my-user-id', { role: 'viewer' })
      ).rejects.toThrow('Cannot change your own role')
    })
  })

  describe('activateUser', () => {
    it('should send activate request to the correct endpoint', async () => {
      const mockResponse = {
        data: {
          id: 'user-123',
          email: 'user@example.com',
          first_name: 'Test',
          last_name: 'User',
          full_name: 'Test User',
          role: 'viewer',
          is_active: true,
          last_login: null,
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-15T00:00:00Z',
        },
      }
      vi.mocked(apiClient.patch).mockResolvedValue(mockResponse)

      const result = await usersApi.activateUser('user-123')

      expect(apiClient.patch).toHaveBeenCalledWith('/api/v1/users/user-123/activate')
      expect(result.is_active).toBe(true)
    })
  })

  describe('deactivateUser', () => {
    it('should send deactivate request to the correct endpoint', async () => {
      const mockResponse = {
        data: {
          id: 'user-123',
          email: 'user@example.com',
          first_name: 'Test',
          last_name: 'User',
          full_name: 'Test User',
          role: 'viewer',
          is_active: false,
          last_login: null,
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-15T00:00:00Z',
        },
      }
      vi.mocked(apiClient.patch).mockResolvedValue(mockResponse)

      const result = await usersApi.deactivateUser('user-123')

      expect(apiClient.patch).toHaveBeenCalledWith('/api/v1/users/user-123/deactivate')
      expect(result.is_active).toBe(false)
    })

    it('should propagate self-deactivation errors', async () => {
      const error = new Error('Cannot deactivate yourself')
      vi.mocked(apiClient.patch).mockRejectedValue(error)

      await expect(usersApi.deactivateUser('my-user-id')).rejects.toThrow(
        'Cannot deactivate yourself'
      )
    })
  })

  describe('deleteUser', () => {
    it('should send delete request to the correct endpoint', async () => {
      vi.mocked(apiClient.delete).mockResolvedValue({})

      await usersApi.deleteUser('user-123')

      expect(apiClient.delete).toHaveBeenCalledWith('/api/v1/users/user-123')
    })

    it('should propagate self-deletion errors', async () => {
      const error = new Error('Cannot delete yourself')
      vi.mocked(apiClient.delete).mockRejectedValue(error)

      await expect(usersApi.deleteUser('my-user-id')).rejects.toThrow(
        'Cannot delete yourself'
      )
    })
  })
})
