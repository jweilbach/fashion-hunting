/**
 * Providers API client (Brand 360)
 *
 * Handles fetching provider metadata and search types from the backend.
 */
import apiClient from './client';
import type { ProviderMetadata, SearchTypeOption } from '../types';

/**
 * Get search types for all registered providers
 */
export async function getAllSearchTypes(): Promise<Record<string, SearchTypeOption[]>> {
  const response = await apiClient.get<Record<string, SearchTypeOption[]>>(
    '/api/v1/providers/search-types'
  );
  return response.data;
}

/**
 * Get full metadata for all registered providers
 */
export async function getAllProviderMetadata(): Promise<ProviderMetadata[]> {
  const response = await apiClient.get<ProviderMetadata[]>(
    '/api/v1/providers/metadata'
  );
  return response.data;
}

/**
 * Get search types for a specific provider
 */
export async function getProviderSearchTypes(
  providerName: string
): Promise<SearchTypeOption[]> {
  const response = await apiClient.get<SearchTypeOption[]>(
    `/api/v1/providers/${providerName}/search-types`
  );
  return response.data;
}

/**
 * Get metadata for a specific provider
 */
export async function getProviderMetadata(
  providerName: string
): Promise<ProviderMetadata> {
  const response = await apiClient.get<ProviderMetadata>(
    `/api/v1/providers/${providerName}/metadata`
  );
  return response.data;
}

export const providersApi = {
  getAllSearchTypes,
  getAllProviderMetadata,
  getProviderSearchTypes,
  getProviderMetadata,
};
