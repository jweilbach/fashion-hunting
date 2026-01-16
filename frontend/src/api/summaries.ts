/**
 * Summaries API client (Brand 360)
 *
 * Handles CRUD operations for AI-generated PDF summary documents.
 */
import apiClient from './client';
import type { Summary, SummaryListResponse } from '../types';

/**
 * List summaries with pagination and optional status filter
 */
export async function getSummaries(
  page: number = 1,
  pageSize: number = 20,
  statusFilter?: string
): Promise<SummaryListResponse> {
  const params: Record<string, unknown> = { page, page_size: pageSize };
  if (statusFilter) {
    params.status_filter = statusFilter;
  }

  const response = await apiClient.get<SummaryListResponse>(
    '/api/v1/summaries/',
    { params }
  );
  return response.data;
}

/**
 * Get recent summaries for dashboard display
 */
export async function getRecentSummaries(limit: number = 3): Promise<Summary[]> {
  const response = await apiClient.get<Summary[]>('/api/v1/summaries/recent', {
    params: { limit },
  });
  return response.data;
}

/**
 * Get a specific summary by ID
 */
export async function getSummary(summaryId: string): Promise<Summary> {
  const response = await apiClient.get<Summary>(
    `/api/v1/summaries/${summaryId}`
  );
  return response.data;
}

/**
 * Get the download URL for a summary PDF
 * Returns the URL that can be used to download the PDF file
 */
export function getSummaryDownloadUrl(summaryId: string): string {
  const baseUrl = apiClient.defaults.baseURL || '';
  const token = localStorage.getItem('access_token');
  // Return URL with auth token as query param for direct download
  return `${baseUrl}/api/v1/summaries/${summaryId}/download?token=${token}`;
}

/**
 * Download a summary PDF using axios (for programmatic downloads)
 */
export async function downloadSummary(summaryId: string): Promise<Blob> {
  const response = await apiClient.get<Blob>(
    `/api/v1/summaries/${summaryId}/download`,
    { responseType: 'blob' }
  );
  return response.data;
}

/**
 * Trigger PDF download in browser
 */
export async function triggerSummaryDownload(
  summaryId: string,
  filename?: string
): Promise<void> {
  const blob = await downloadSummary(summaryId);
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename || `summary_${summaryId}.pdf`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

/**
 * Delete a summary and its associated PDF file
 */
export async function deleteSummary(summaryId: string): Promise<void> {
  await apiClient.delete(`/api/v1/summaries/${summaryId}`);
}

export const summariesApi = {
  getSummaries,
  getRecentSummaries,
  getSummary,
  getSummaryDownloadUrl,
  downloadSummary,
  triggerSummaryDownload,
  deleteSummary,
};
