/**
 * Admin API client
 * Handles super admin operations for cross-tenant management
 */
import apiClient from './client';

export interface TenantAdminResponse {
  id: string;
  name: string;
  slug: string;
  email: string;
  company_name: string | null;
  plan: 'free' | 'starter' | 'professional' | 'enterprise';
  status: 'active' | 'suspended' | 'cancelled';
  user_count: number;
  report_count: number;
  created_at: string;
  updated_at: string;
  last_report_run: string | null;
}

export interface TenantListResponse {
  items: TenantAdminResponse[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface AdminUserSearchResult {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  full_name: string | null;
  role: 'admin' | 'editor' | 'viewer';
  is_active: boolean;
  is_superuser: boolean;
  tenant_id: string;
  tenant_name: string;
  created_at: string;
}

export interface ImpersonationResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  impersonated_user: {
    id: string;
    email: string;
    first_name: string | null;
    last_name: string | null;
    full_name: string | null;
    role: string;
  };
  impersonated_by: string;
}

export interface AdminStats {
  tenants: {
    total: number;
    active: number;
  };
  users: {
    total: number;
    active: number;
  };
  reports: {
    total: number;
  };
  plans: Record<string, number>;
}

export interface TenantListParams {
  status_filter?: 'active' | 'suspended' | 'cancelled';
  plan_filter?: 'free' | 'starter' | 'professional' | 'enterprise';
  search?: string;
  page?: number;
  page_size?: number;
}

export const adminApi = {
  /**
   * List all tenants with their stats (superuser only)
   */
  listTenants: async (params?: TenantListParams): Promise<TenantListResponse> => {
    const response = await apiClient.get<TenantListResponse>('/api/v1/admin/tenants', { params });
    return response.data;
  },

  /**
   * Get detailed tenant information (superuser only)
   */
  getTenant: async (tenantId: string): Promise<TenantAdminResponse> => {
    const response = await apiClient.get<TenantAdminResponse>(`/api/v1/admin/tenants/${tenantId}`);
    return response.data;
  },

  /**
   * Update tenant status (suspend/activate/cancel) (superuser only)
   */
  updateTenantStatus: async (
    tenantId: string,
    status: 'active' | 'suspended' | 'cancelled'
  ): Promise<TenantAdminResponse> => {
    const response = await apiClient.patch<TenantAdminResponse>(
      `/api/v1/admin/tenants/${tenantId}/status`,
      { status }
    );
    return response.data;
  },

  /**
   * Update tenant subscription plan (superuser only)
   */
  updateTenantPlan: async (
    tenantId: string,
    plan: 'free' | 'starter' | 'professional' | 'enterprise'
  ): Promise<TenantAdminResponse> => {
    const response = await apiClient.patch<TenantAdminResponse>(
      `/api/v1/admin/tenants/${tenantId}/plan`,
      { plan }
    );
    return response.data;
  },

  /**
   * Get an impersonation token to act as another user (superuser only)
   * Cannot impersonate other superusers
   */
  impersonateUser: async (userId: string): Promise<ImpersonationResponse> => {
    const response = await apiClient.post<ImpersonationResponse>(
      `/api/v1/admin/impersonate/${userId}`
    );
    return response.data;
  },

  /**
   * Search for users across all tenants (superuser only)
   */
  searchUsers: async (query: string, limit?: number): Promise<AdminUserSearchResult[]> => {
    const response = await apiClient.get<AdminUserSearchResult[]>('/api/v1/admin/search/users', {
      params: { query, limit },
    });
    return response.data;
  },

  /**
   * Get high-level system statistics (superuser only)
   */
  getStats: async (): Promise<AdminStats> => {
    const response = await apiClient.get<AdminStats>('/api/v1/admin/stats');
    return response.data;
  },
};

export default adminApi;
