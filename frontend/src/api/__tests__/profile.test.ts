/**
 * Tests for the Profile API client
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { profileApi } from '../profile'
import apiClient from '../client'

// Mock the axios client
vi.mock('../client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
}))

describe('profileApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getProfile', () => {
    it('should fetch profile from the correct endpoint', async () => {
      const mockResponse = {
        data: {
          id: 'user-123',
          email: 'user@example.com',
          first_name: 'Test',
          last_name: 'User',
          full_name: 'Test User',
          role: 'admin',
          tenant_id: 'tenant-456',
          tenant_name: 'Test Tenant',
          tenant_plan: 'professional',
          is_active: true,
          last_login: '2025-01-14T12:00:00Z',
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-14T12:00:00Z',
        },
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await profileApi.getProfile()

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/auth/profile')
      expect(result.email).toBe('user@example.com')
      expect(result.first_name).toBe('Test')
      expect(result.last_name).toBe('User')
      expect(result.tenant_plan).toBe('professional')
    })

    it('should propagate errors from the API', async () => {
      const error = new Error('Unauthorized')
      vi.mocked(apiClient.get).mockRejectedValue(error)

      await expect(profileApi.getProfile()).rejects.toThrow('Unauthorized')
    })
  })

  describe('updateProfile', () => {
    it('should send profile update to the correct endpoint', async () => {
      const mockResponse = {
        data: {
          id: 'user-123',
          email: 'user@example.com',
          first_name: 'Updated',
          last_name: 'Name',
          full_name: 'Updated Name',
          role: 'admin',
          tenant_id: 'tenant-456',
          tenant_name: 'Test Tenant',
          tenant_plan: 'professional',
          is_active: true,
          last_login: null,
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-14T13:00:00Z',
        },
      }
      vi.mocked(apiClient.patch).mockResolvedValue(mockResponse)

      const result = await profileApi.updateProfile({
        first_name: 'Updated',
        last_name: 'Name',
      })

      expect(apiClient.patch).toHaveBeenCalledWith('/api/v1/auth/profile', {
        first_name: 'Updated',
        last_name: 'Name',
      })
      expect(result.first_name).toBe('Updated')
      expect(result.last_name).toBe('Name')
    })

    it('should handle partial updates', async () => {
      const mockResponse = {
        data: {
          id: 'user-123',
          email: 'user@example.com',
          first_name: 'OnlyFirst',
          last_name: 'Original',
          full_name: 'OnlyFirst Original',
          role: 'admin',
          tenant_id: 'tenant-456',
          tenant_name: 'Test Tenant',
          tenant_plan: null,
          is_active: true,
          last_login: null,
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-14T13:00:00Z',
        },
      }
      vi.mocked(apiClient.patch).mockResolvedValue(mockResponse)

      const result = await profileApi.updateProfile({ first_name: 'OnlyFirst' })

      expect(apiClient.patch).toHaveBeenCalledWith('/api/v1/auth/profile', {
        first_name: 'OnlyFirst',
      })
      expect(result.first_name).toBe('OnlyFirst')
    })
  })

  describe('changePassword', () => {
    it('should send password change to the correct endpoint', async () => {
      const mockResponse = {
        data: { message: 'Password changed successfully' },
      }
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

      const result = await profileApi.changePassword({
        current_password: 'oldpass123',
        new_password: 'newpass456',
      })

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/auth/change-password', {
        current_password: 'oldpass123',
        new_password: 'newpass456',
      })
      expect(result.message).toBe('Password changed successfully')
    })

    it('should propagate password change errors', async () => {
      const error = new Error('Current password is incorrect')
      vi.mocked(apiClient.post).mockRejectedValue(error)

      await expect(
        profileApi.changePassword({
          current_password: 'wrongpass',
          new_password: 'newpass456',
        })
      ).rejects.toThrow('Current password is incorrect')
    })
  })
})
