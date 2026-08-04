/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { t, tUnsafe } from '@/utils/i18n';
import { hideElement, showElement } from '@/utils/dom';
import { reportError } from '@/telemetry';
import { apiGet, apiPostForm, handleApiError } from '@/utils/api';
import { generateExportPreview, generateImportPreview, hidePreview, showPreview } from './preview';
import { renderErrorSummary, validateExportForm, validateImportForm } from './validation';

export type OperationType = 'export' | 'import' | null;

const IMPORT_EXPORT_COMPONENT = 'importExport';
const HIDDEN_CLASS = 'hidden';

export let currentOperation: OperationType = null;

function setCurrentOperation(operation: OperationType): void {
  currentOperation = operation;
}

/**
 * Helper function to handle blob downloads with automatic token refresh
 */
async function downloadBlob(url: string, formData: FormData, filename: string): Promise<void> {
  const performDownload = async (isRetry = false): Promise<Response> => {
    const response = await fetch(url, {
      method: 'POST',
      credentials: 'include',
      body: formData,
    });

    // Handle 401 with automatic token refresh
    if (response.status === 401 && !isRetry) {
      // Try to refresh the token
      const refreshToken =
        localStorage.getItem('refresh_token') || sessionStorage.getItem('refresh_token');

      if (refreshToken) {
        const refreshResponse = await fetch('/api/auth/refresh', {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (refreshResponse.ok) {
          const data = await refreshResponse.json();
          // Update stored tokens
          if (localStorage.getItem('refresh_token')) {
            localStorage.setItem('access_token', data.access_token);
            localStorage.setItem('refresh_token', data.refresh_token);
          } else {
            sessionStorage.setItem('access_token', data.access_token);
            sessionStorage.setItem('refresh_token', data.refresh_token);
          }
          // Retry the download with refreshed token
          return performDownload(true);
        }
      }

      // Refresh failed - clear tokens and redirect
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      sessionStorage.removeItem('access_token');
      sessionStorage.removeItem('refresh_token');
      window.location.href = '/auth/login';
      throw new Error('Authentication failed');
    }

    return response;
  };

  const response = await performDownload();

  if (response.ok) {
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.classList.add(HIDDEN_CLASS);
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(anchor);
  } else {
    const error = await response.json();
    throw new Error(error.error || 'Download failed');
  }
}

export function showProgress(operation: 'export' | 'import', messageKey: string): void {
  const progressContainer = document.getElementById(`${operation}-progress`);
  const statusElement = document.getElementById(`${operation}-status`);
  const progressFill = document.getElementById(`${operation}-progress-fill`);

  showElement(progressContainer);
  if (progressFill) {
    progressFill.style.width = '50%';
  }
  if (statusElement) {
    statusElement.textContent = tUnsafe(`importExport.${messageKey}`);
    statusElement.className = 'text-sm text-blue-600 mt-2';
  }
}

export function hideProgress(operation: 'export' | 'import'): void {
  const progressContainer = document.getElementById(`${operation}-progress`);
  hideElement(progressContainer);
}

export function showStatus(
  operation: 'export' | 'import',
  message: string,
  type: 'info' | 'success' | 'error'
): void {
  const statusElement = document.getElementById(`${operation}-status`);
  const progressContainer = document.getElementById(`${operation}-progress`);
  if (!statusElement) return;

  statusElement.textContent = message;
  const colorClass =
    type === 'success' ? 'text-green-600' : type === 'error' ? 'text-red-600' : 'text-blue-600';
  statusElement.className = `text-sm ${colorClass} mt-2`;

  showElement(progressContainer);

  if (type === 'success') {
    setTimeout(() => {
      statusElement.textContent = '';
      statusElement.className = 'text-sm text-blue-600 mt-2';
      hideElement(progressContainer);
    }, 3000);
  }
}

export async function loadStatistics(): Promise<void> {
  try {
    const stats = await apiGet<{
      total_prompts: number;
      total_categories: number;
      total_tags: number;
      favorite_prompts: number;
    }>('/api/import-export/stats');

    const totalPrompts = document.getElementById('total-prompts');
    const totalCategories = document.getElementById('total-categories');
    const totalTags = document.getElementById('total-tags');
    const favoritePrompts = document.getElementById('favorite-prompts');

    if (totalPrompts) totalPrompts.textContent = String(stats.total_prompts);
    if (totalCategories) totalCategories.textContent = String(stats.total_categories);
    if (totalTags) totalTags.textContent = String(stats.total_tags);
    if (favoritePrompts) favoritePrompts.textContent = String(stats.favorite_prompts);

    updateActivityHistory();
  } catch (error) {
    reportError(IMPORT_EXPORT_COMPONENT, 'loadStatistics', error);
  }
}

function updateActivityHistory(): void {
  const historyList = document.getElementById('activity-history');
  if (!historyList) return;
  // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
  historyList.innerHTML = `
        <div class="history-item">
            <div class="history-info">
                <div class="text-sm text-gray-700 dark:text-gray-300">No recent activity</div>
                <div class="history-details text-xs text-gray-500 dark:text-gray-400">Activity tracking not yet implemented</div>
            </div>
        </div>
    `;
}

export function normalizeExportFilename(filename: string, format: string): string {
  if (!filename) {
    return `promptvault_export.${format}`;
  }
  if (/\.(csv|md|json)$/i.test(filename)) {
    return filename;
  }
  return `${filename}.${format}`;
}

export async function previewExport(): Promise<void> {
  setCurrentOperation('export');
  const formatSelect = document.getElementById('export-format') as HTMLSelectElement | null;
  const format = formatSelect?.value || 'csv';
  const includeFavorites =
    (document.getElementById('include-favorites') as HTMLInputElement | null)?.checked ?? false;

  try {
    showProgress('export', 'preparingExport');

    const data = await apiGet<{ prompts: Record<string, { favorite?: boolean }> }>('/api/prompts');
    let prompts = data.prompts;

    if (includeFavorites) {
      prompts = Object.fromEntries(Object.entries(prompts).filter(([, prompt]) => prompt.favorite));
    }

    const previewContent = generateExportPreview(prompts, format);

    showPreview(currentOperation, previewContent);
    hideProgress('export');
  } catch (error) {
    reportError(IMPORT_EXPORT_COMPONENT, 'previewExport', error, { format, includeFavorites });
    showStatus('export', 'exportFailed', 'error');
  }
}

export async function previewImport(): Promise<void> {
  const fileInput = document.getElementById('import-file') as HTMLInputElement | null;
  const file = fileInput?.files?.[0];
  const validationErrors = validateImportForm(file);
  if (validationErrors.length > 0) {
    renderErrorSummary('import-error-summary', validationErrors);
    return;
  }
  const selectedFile = file as File;

  setCurrentOperation('import');

  try {
    showProgress('import', 'preparingImport');

    const previewContent = await generateImportPreview(selectedFile.name);

    showPreview(currentOperation, previewContent);
    hideProgress('import');
  } catch (error) {
    reportError(IMPORT_EXPORT_COMPONENT, 'previewImport', error, { filename: selectedFile.name });
    showStatus('import', 'importFailed', 'error');
  }
}

export function cancelPreview(): void {
  hidePreview();
  if (currentOperation) {
    hideProgress(currentOperation);
  }
}

export async function confirmOperation(): Promise<void> {
  if (currentOperation === 'export') {
    await performExport();
  } else {
    await performImport();
  }
  hidePreview();
}

export async function performExport(): Promise<void> {
  const formatSelect = document.getElementById('export-format') as HTMLSelectElement | null;
  const format = formatSelect?.value || 'csv';
  const rawFilename =
    (document.getElementById('export-filename') as HTMLInputElement | null)?.value || '';
  const filename = normalizeExportFilename(rawFilename, format);
  const includeFavorites =
    (document.getElementById('include-favorites') as HTMLInputElement | null)?.checked ?? false;
  const includeMetadata =
    (document.getElementById('include-metadata') as HTMLInputElement | null)?.checked ?? false;

  const validationErrors = validateExportForm(rawFilename);
  if (validationErrors.length > 0) {
    renderErrorSummary('export-error-summary', validationErrors);
    return;
  }

  try {
    showProgress('export', 'exportProgress');

    const formData = new FormData();
    formData.append('format', format);
    formData.append('filename', filename);
    formData.append('include_favorites', String(includeFavorites));
    formData.append('include_metadata', String(includeMetadata));

    await downloadBlob('/api/export', formData, filename);

    showStatus('export', 'exportSuccess', 'success');
    void loadStatistics();
  } catch (error) {
    reportError(IMPORT_EXPORT_COMPONENT, 'performExport', error, {
      format,
      filename,
      includeFavorites,
      includeMetadata,
    });
    showStatus('export', 'exportFailed', 'error');
  } finally {
    hideProgress('export');
  }
}

export async function performImport(): Promise<void> {
  const fileInput = document.getElementById('import-file') as HTMLInputElement | null;
  const file = fileInput?.files?.[0];
  const errorElement = document.getElementById('import-file-error');

  // Clear previous error messages
  if (errorElement) {
    errorElement.textContent = '';
  }

  const validationErrors = validateImportForm(file);
  if (validationErrors.length > 0) {
    renderErrorSummary('import-error-summary', validationErrors);
    return;
  }
  if (!fileInput || !file) {
    return;
  }
  const selectedFile = file as File;

  // Re-validate file before import (in case conditions changed)
  const allowedExtensions = ['.csv', '.json', '.md', '.markdown'];
  const fileName = selectedFile.name.toLowerCase();
  const isValidType = allowedExtensions.some((ext) => fileName.endsWith(ext));

  if (!isValidType) {
    const errorMsg = 'File format not supported. Please use CSV, JSON, or Markdown files.';
    if (errorElement) {
      errorElement.textContent = errorMsg;
    }
    showStatus('import', errorMsg, 'error');
    return;
  }

  const maxSizeBytes = 10 * 1024 * 1024;
  if (selectedFile.size > maxSizeBytes) {
    const errorMsg = 'File is too large. Maximum size is 10MB.';
    if (errorElement) {
      errorElement.textContent = errorMsg;
    }
    showStatus('import', errorMsg, 'error');
    return;
  }

  const mode =
    (document.getElementById('import-mode') as HTMLSelectElement | null)?.value || 'append';
  const validate =
    (document.getElementById('import-validate') as HTMLInputElement | null)?.checked ?? false;

  try {
    showProgress('import', 'importProgress');

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('mode', mode);
    formData.append('validate', String(validate));

    const result = await apiPostForm<{ added_count: number; error?: string }>(
      '/api/import',
      formData
    );

    const message = (t('importExport.importSuccess') || '').replace(
      '{count}',
      String(result.added_count)
    );
    showStatus('import', message, 'success');
    void loadStatistics();
    fileInput.value = '';
  } catch (error) {
    reportError(IMPORT_EXPORT_COMPONENT, 'performImport', error, {
      mode,
      validate,
      filename: selectedFile.name,
    });
    showStatus('import', handleApiError(error, 'importFailed'), 'error');
  } finally {
    hideProgress('import');
  }
}
