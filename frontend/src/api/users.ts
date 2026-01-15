/**
 * Users API client
 * Handles user management operations for tenant admins
 */
import apiClient from './client';

export interface UserResponse {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  full_name: string | null;
  role: 'admin' | 'editor' | 'viewer';
  is_active: boolean;
  last_login: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateUserRequest {
  email: string;
  first_name?: string;
  last_name?: string;
  role?: 'admin' | 'editor' | 'viewer';
}

export interface UpdateUserRoleRequest {
  role: 'admin' | 'editor' | 'viewer';
}

export const usersApi = {
  /**
   * List all users for the current tenant (admin only)
   */
  listUsers: async (params?: { active_only?: boolean; skip?: number; limit?: number }): Promise<UserResponse[]> => {
    const response = await apiClient.get<UserResponse[]>('/api/v1/users/', { params });
    return response.data;
  },

  /**
   * Get user count for the current tenant (admin only)
   */
  getUserCount: async (active_only?: boolean): Promise<{ count: number }> => {
    const response = await apiClient.get<{ count: number }>('/api/v1/users/count', {
      params: { active_only },
    });
    return response.data;
  },

  /**
   * Get a specific user by ID (admin only)
   */
  getUser: async (userId: string): Promise<UserResponse> => {
    const response = await apiClient.get<UserResponse>(`/api/v1/users/${userId}`);
    return response.data;
  },

  /**
   * Create a new user in the tenant (admin only)
   * User is created with default password "Welcome123"
   */
  createUser: async (data: CreateUserRequest): Promise<UserResponse> => {
    const response = await apiClient.post<UserResponse>('/api/v1/users/', data);
    return response.data;
  },

  /**
   * Update a user's role (admin only)
   */
  updateUserRole: async (userId: string, data: UpdateUserRoleRequest): Promise<UserResponse> => {
    const response = await apiClient.patch<UserResponse>(`/api/v1/users/${userId}/role`, data);
    return response.data;
  },

  /**
   * Activate a user (admin only)
   */
  activateUser: async (userId: string): Promise<UserResponse> => {
    const response = await apiClient.patch<UserResponse>(`/api/v1/users/${userId}/activate`);
    return response.data;
  },

  /**
   * Deactivate a user (admin only)
   */
  deactivateUser: async (userId: string): Promise<UserResponse> => {
    const response = await apiClient.patch<UserResponse>(`/api/v1/users/${userId}/deactivate`);
    return response.data;
  },

  /**
   * Delete a user (admin only)
   */
  deleteUser: async (userId: string): Promise<void> => {
    await apiClient.delete(`/api/v1/users/${userId}`);
  },
};

export default usersApi;
