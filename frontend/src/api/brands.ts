import apiClient from './client';
import type { Brand, PaginatedResponse } from '../types';

export const brandsApi = {
  // Get all brands
  getBrands: async (skip: number = 0, limit: number = 1000): Promise<Brand[]> => {
    const response = await apiClient.get<Brand[]>(
      `/api/v1/brands/?skip=${skip}&limit=${limit}`
    );
    return response.data;
  },

  // Get single brand by ID
  getBrand: async (id: string): Promise<Brand> => {
    const response = await apiClient.get<Brand>(`/api/v1/brands/${id}`);
    return response.data;
  },

  // Create new brand
  createBrand: async (data: any): Promise<Brand> => {
    const response = await apiClient.post<Brand>(`/api/v1/brands/`, data);
    return response.data;
  },

  // Update brand
  updateBrand: async (id: string, data: any): Promise<Brand> => {
    const response = await apiClient.put<Brand>(`/api/v1/brands/${id}`, data);
    return response.data;
  },

  // Delete brand
  deleteBrand: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/v1/brands/${id}`);
  },

  // Get brand by name
  getBrandByName: async (brandName: string): Promise<Brand> => {
    const response = await apiClient.get<Brand>(`/api/v1/brands/name/${encodeURIComponent(brandName)}`);
    return response.data;
  },

  // Get top brands by mention count
  getTopBrands: async (limit: number = 10, skip: number = 0): Promise<PaginatedResponse<Brand>> => {
    const response = await apiClient.get<PaginatedResponse<Brand>>(`/api/v1/public/brands/top?limit=${limit}&skip=${skip}`);
    return response.data;
  },
};
