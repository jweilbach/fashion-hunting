/**
 * Tests for the Auth API client
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { authApi } from '../auth'
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

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

describe('authApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('login', () => {
    it('should send credentials to token endpoint with correct format', async () => {
      const mockResponse = {
        data: {
          access_token: 'test-token-123',
          token_type: 'bearer',
        },
      }
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

      const result = await authApi.login('test@example.com', 'password123')

      // Verify the endpoint
      expect(apiClient.post).toHaveBeenCalledWith(
        '/api/v1/auth/token',
        expect.any(URLSearchParams),
        expect.objectContaining({
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        })
      )

      // Verify the form data
      const callArgs = vi.mocked(apiClient.post).mock.calls[0]
      const formData = callArgs[1] as URLSearchParams
      expect(formData.get('username')).toBe('test@example.com')
      expect(formData.get('password')).toBe('password123')

      expect(result.access_token).toBe('test-token-123')
      expect(result.token_type).toBe('bearer')
    })

    it('should propagate errors from the API', async () => {
      const error = new Error('Invalid credentials')
      vi.mocked(apiClient.post).mockRejectedValue(error)

      await expect(authApi.login('test@example.com', 'wrongpassword'))
        .rejects.toThrow('Invalid credentials')
    })
  })

  describe('signup', () => {
    it('should send signup data to correct endpoint', async () => {
      const mockResponse = {
        data: {
          access_token: 'new-user-token',
          token_type: 'bearer',
        },
      }
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)

      const result = await authApi.signup('new@example.com', 'securepass', 'My Company')

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/auth/signup', {
        email: 'new@example.com',
        password: 'securepass',
        tenant_name: 'My Company',
      })
      expect(result.access_token).toBe('new-user-token')
    })

    it('should propagate signup errors', async () => {
      const error = new Error('Email already exists')
      vi.mocked(apiClient.post).mockRejectedValue(error)

      await expect(authApi.signup('existing@example.com', 'pass', 'Company'))
        .rejects.toThrow('Email already exists')
    })
  })

  describe('getCurrentUser', () => {
    it('should fetch current user from me endpoint', async () => {
      const mockResponse = {
        data: {
          id: 'user-123',
          email: 'user@example.com',
          role: 'admin',
          tenant_id: 'tenant-456',
          tenant_name: 'Test Tenant',
        },
      }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)

      const result = await authApi.getCurrentUser()

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/auth/me')
      expect(result.email).toBe('user@example.com')
      expect(result.role).toBe('admin')
      expect(result.tenant_id).toBe('tenant-456')
    })

    it('should propagate auth errors (e.g., 401)', async () => {
      const error = new Error('Unauthorized')
      vi.mocked(apiClient.get).mockRejectedValue(error)

      await expect(authApi.getCurrentUser()).rejects.toThrow('Unauthorized')
    })
  })

  describe('logout', () => {
    it('should remove access_token from localStorage', () => {
      authApi.logout()

      expect(localStorageMock.removeItem).toHaveBeenCalledWith('access_token')
    })
  })
})
