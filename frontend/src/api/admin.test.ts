import { describe, it, expect, vi, beforeEach } from 'vitest';
import { adminApi } from './admin';
import apiClient from './client';

// Mock the API client
vi.mock('./client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('adminApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('listTenants', () => {
    it('should call GET /api/v1/admin/tenants', async () => {
      const mockResponse = {
        data: {
          items: [],
          total: 0,
          page: 1,
          page_size: 10,
          pages: 0,
        },
      };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      const result = await adminApi.listTenants();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/admin/tenants', { params: undefined });
      expect(result).toEqual(mockResponse.data);
    });

    it('should pass filter params', async () => {
      const mockResponse = { data: { items: [], total: 0, page: 1, page_size: 10, pages: 0 } };
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse);

      await adminApi.listTenants({ status_filter: 'active', plan_filter: 'enterprise' });

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/admin/tenants', {
        params: { status_filter: 'active', plan_filter: 'enterprise' },
      });
    });
  });

  describe('getTenant', () => {
    it('should call GET /api/v1/admin/tenants/{id}', async () => {
      const mockTenant = { id: 'test-id', name: 'Test Tenant' };
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockTenant });

      const result = await adminApi.getTenant('test-id');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/admin/tenants/test-id');
      expect(result).toEqual(mockTenant);
    });
  });

  describe('updateTenantStatus', () => {
    it('should call PATCH /api/v1/admin/tenants/{id}/status', async () => {
      const mockTenant = { id: 'test-id', status: 'suspended' };
      vi.mocked(apiClient.patch).mockResolvedValue({ data: mockTenant });

      const result = await adminApi.updateTenantStatus('test-id', 'suspended');

      expect(apiClient.patch).toHaveBeenCalledWith('/api/v1/admin/tenants/test-id/status', {
        status: 'suspended',
      });
      expect(result).toEqual(mockTenant);
    });
  });

  describe('updateTenantPlan', () => {
    it('should call PATCH /api/v1/admin/tenants/{id}/plan', async () => {
      const mockTenant = { id: 'test-id', plan: 'enterprise' };
      vi.mocked(apiClient.patch).mockResolvedValue({ data: mockTenant });

      const result = await adminApi.updateTenantPlan('test-id', 'enterprise');

      expect(apiClient.patch).toHaveBeenCalledWith('/api/v1/admin/tenants/test-id/plan', {
        plan: 'enterprise',
      });
      expect(result).toEqual(mockTenant);
    });
  });

  describe('impersonateUser', () => {
    it('should call POST /api/v1/admin/impersonate/{userId}', async () => {
      const mockResponse = {
        access_token: 'test-token',
        token_type: 'bearer',
        expires_in: 3600,
        impersonated_user: { id: 'user-id', email: 'test@example.com' },
        impersonated_by: 'super_admin:admin@example.com',
      };
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockResponse });

      const result = await adminApi.impersonateUser('user-id');

      expect(apiClient.post).toHaveBeenCalledWith('/api/v1/admin/impersonate/user-id');
      expect(result).toEqual(mockResponse);
    });
  });

  describe('searchUsers', () => {
    it('should call GET /api/v1/admin/search/users with query', async () => {
      const mockUsers = [{ id: 'user-1', email: 'test@example.com' }];
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockUsers });

      const result = await adminApi.searchUsers('test');

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/admin/search/users', {
        params: { query: 'test', limit: undefined },
      });
      expect(result).toEqual(mockUsers);
    });

    it('should pass limit param', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: [] });

      await adminApi.searchUsers('test', 50);

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/admin/search/users', {
        params: { query: 'test', limit: 50 },
      });
    });
  });

  describe('getStats', () => {
    it('should call GET /api/v1/admin/stats', async () => {
      const mockStats = {
        tenants: { total: 10, active: 8 },
        users: { total: 50, active: 45 },
        reports: { total: 1000 },
        plans: { free: 5, starter: 3, professional: 2 },
      };
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockStats });

      const result = await adminApi.getStats();

      expect(apiClient.get).toHaveBeenCalledWith('/api/v1/admin/stats');
      expect(result).toEqual(mockStats);
    });
  });
});
