/**
 * Profile API client
 * Handles user profile operations
 */
import apiClient from './client';

export interface ProfileResponse {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  full_name: string | null;
  role: 'admin' | 'editor' | 'viewer';
  tenant_id: string;
  tenant_name: string | null;
  tenant_plan: string | null;
  is_active: boolean;
  last_login: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProfileUpdate {
  first_name?: string;
  last_name?: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export const profileApi = {
  /**
   * Get current user's full profile including tenant information
   */
  getProfile: async (): Promise<ProfileResponse> => {
    const response = await apiClient.get<ProfileResponse>('/api/v1/auth/profile');
    return response.data;
  },

  /**
   * Update current user's profile (name fields)
   */
  updateProfile: async (data: ProfileUpdate): Promise<ProfileResponse> => {
    const response = await apiClient.patch<ProfileResponse>('/api/v1/auth/profile', data);
    return response.data;
  },

  /**
   * Change current user's password
   */
  changePassword: async (data: ChangePasswordRequest): Promise<{ message: string }> => {
    const response = await apiClient.post<{ message: string }>('/api/v1/auth/change-password', data);
    return response.data;
  },
};

export default profileApi;
