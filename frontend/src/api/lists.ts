import apiClient from './client';
import type { List, ListWithReports, ListCreate, ListUpdate, ListItem } from '../types';

export interface ListsResponse {
  items: List[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface BulkAddResult {
  added_count: number;
  items: ListItem[];
}

export interface MultiListAddResult {
  results: {
    [listId: string]: BulkAddResult;
  };
}

export interface ListType {
  id: string;
  label: string;
  description: string;
}

export interface ListTypesResponse {
  types: ListType[];
}

export const listsApi = {
  // Get supported list types
  getListTypes: async (): Promise<ListTypesResponse> => {
    const response = await apiClient.get<ListTypesResponse>('/api/v1/lists/types/');
    return response.data;
  },

  // Get all lists for the tenant
  getLists: async (
    listType?: string,
    page: number = 1,
    pageSize: number = 50
  ): Promise<ListsResponse> => {
    const params = new URLSearchParams();
    if (listType) params.append('list_type', listType);
    params.append('page', page.toString());
    params.append('page_size', pageSize.toString());

    const response = await apiClient.get<ListsResponse>(
      `/api/v1/lists/?${params.toString()}`
    );
    return response.data;
  },

  // Get a single list by ID (with reports if report-type list)
  getList: async (id: string, includeItems: boolean = true): Promise<ListWithReports> => {
    const response = await apiClient.get<ListWithReports>(
      `/api/v1/lists/${id}?include_items=${includeItems}`
    );
    return response.data;
  },

  // Create a new list
  createList: async (data: ListCreate): Promise<List> => {
    const response = await apiClient.post<List>('/api/v1/lists/', data);
    return response.data;
  },

  // Update a list
  updateList: async (id: string, data: ListUpdate): Promise<List> => {
    const response = await apiClient.put<List>(`/api/v1/lists/${id}`, data);
    return response.data;
  },

  // Delete a list
  deleteList: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/v1/lists/${id}`);
  },

  // Add a single item to a list
  addItem: async (listId: string, itemId: string): Promise<ListItem> => {
    const response = await apiClient.post<ListItem>(
      `/api/v1/lists/${listId}/items/`,
      { item_id: itemId }
    );
    return response.data;
  },

  // Add multiple items to a single list
  addItems: async (listId: string, itemIds: string[]): Promise<BulkAddResult> => {
    const response = await apiClient.post<BulkAddResult>(
      `/api/v1/lists/${listId}/items/bulk/`,
      { item_ids: itemIds }
    );
    return response.data;
  },

  // Add items to multiple lists at once
  addItemsToMultipleLists: async (
    listIds: string[],
    itemIds: string[]
  ): Promise<MultiListAddResult> => {
    const response = await apiClient.post<MultiListAddResult>(
      '/api/v1/lists/bulk-add/',
      { list_ids: listIds, item_ids: itemIds }
    );
    return response.data;
  },

  // Remove a single item from a list
  removeItem: async (listId: string, itemId: string): Promise<void> => {
    await apiClient.delete(`/api/v1/lists/${listId}/items/${itemId}`);
  },

  // Remove multiple items from a list
  removeItems: async (listId: string, itemIds: string[]): Promise<{ removed_count: number }> => {
    const response = await apiClient.delete<{ removed_count: number }>(
      `/api/v1/lists/${listId}/items/bulk/`,
      { data: { item_ids: itemIds } }
    );
    return response.data;
  },

  // Get all lists that contain a specific item
  getListsContainingItem: async (itemId: string): Promise<List[]> => {
    const response = await apiClient.get<List[]>(
      `/api/v1/lists/containing/${itemId}`
    );
    return response.data;
  },

  // Export a list to CSV or Excel
  exportList: async (listId: string, format: 'csv' | 'excel' = 'csv'): Promise<void> => {
    const response = await apiClient.post(
      `/api/v1/lists/${listId}/export/?format=${format}`,
      null,
      { responseType: 'blob' }
    );

    // Create download link
    const blob = new Blob([response.data], {
      type: format === 'excel'
        ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        : 'text/csv'
    });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = format === 'excel' ? 'list_export.xlsx' : 'list_export.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  },
};
