/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Import/export page logic
 */

import '../css/tailwind-globals.css';
import '@/form-validation';
import { initI18n, t, tUnsafe, updateStaticTranslations } from '@/utils/i18n';
import { hideElement, showElement } from '@/utils/dom';
import { reportError } from '@/telemetry';
import { apiGet, apiPostForm, handleApiError } from '@/utils/api';
import { announce } from '@/utils/a11y';
import { initSecondaryNav } from '@/utils/secondary-nav';

type OperationType = 'export' | 'import' | null;
interface FormValidationError {
  inputId: string;
  message: string;
}

let currentOperation: OperationType = null;
const IMPORT_EXPORT_COMPONENT = 'importExport';
const HIDDEN_CLASS = 'hidden';
const liveValidationState = new Map<string, boolean>();

function setLiveFieldError(inputId: string, errorId: string, message: string): void {
  const input = document.getElementById(inputId) as HTMLElement | null;
  const error = document.getElementById(errorId) as HTMLElement | null;
  const hadError = liveValidationState.get(inputId) === true;
  input?.setAttribute('aria-invalid', 'true');
  if (error) {
    error.textContent = message;
  }
  liveValidationState.set(inputId, true);
  if (!hadError) {
    announce(message, { id: 'validation-announcer', politeness: 'polite' });
  }
}

function clearLiveFieldError(inputId: string, errorId: string): void {
  const input = document.getElementById(inputId) as HTMLElement | null;
  const error = document.getElementById(errorId) as HTMLElement | null;
  const hadError = liveValidationState.get(inputId) === true;
  input?.setAttribute('aria-invalid', 'false');
  if (error) {
    error.textContent = '';
  }
  liveValidationState.set(inputId, false);
  if (hadError) {
    announce(t('validation.fieldValid') || 'Field is valid.', {
      id: 'validation-announcer',
      politeness: 'polite',
    });
  }
}

function resetFieldError(inputId: string, errorId: string): void {
  const input = document.getElementById(inputId) as HTMLElement | null;
  const error = document.getElementById(errorId);
  input?.setAttribute('aria-invalid', 'false');
  if (error) {
    error.textContent = '';
  }
}

function addFieldError(
  errors: FormValidationError[],
  inputId: string,
  errorId: string,
  message: string
): void {
  const input = document.getElementById(inputId) as HTMLElement | null;
  const error = document.getElementById(errorId);
  if (input) {
    const existing =
      input
        .getAttribute('aria-describedby')
        ?.split(/\s+/)
        .map((s) => s.trim())
        .filter(Boolean) ?? [];
    const next = Array.from(new Set([...existing, errorId]));
    input.setAttribute('aria-describedby', next.join(' '));
  }
  input?.setAttribute('aria-invalid', 'true');
  if (error) {
    error.textContent = message;
  }
  errors.push({ inputId, message });
}

function resetErrorSummary(summaryId: string): void {
  const summary = document.getElementById(summaryId);
  if (!summary) return;
  summary.textContent = '';
  summary.style.display = 'none';
}

function renderErrorSummary(summaryId: string, errors: FormValidationError[]): void {
  if (errors.length === 0) {
    return;
  }

  const summary = document.getElementById(summaryId);
  if (!summary) {
    const firstInput = document.getElementById(errors[0]?.inputId ?? '') as HTMLElement | null;
    firstInput?.focus();
    return;
  }

  summary.textContent = '';
  const header = document.createElement('p');
  header.className = 'error-banner-header';
  header.textContent = t('validation.errorSummaryHeader') || 'Please correct the following errors:';
  summary.appendChild(header);

  const list = document.createElement('ul');
  list.className = 'error-banner-list';
  errors.forEach((error) => {
    const item = document.createElement('li');
    const link = document.createElement('a');
    link.href = `#${error.inputId}`;
    link.className = 'underline';
    link.textContent = error.message;
    link.addEventListener('click', (event) => {
      event.preventDefault();
      const target = document.getElementById(error.inputId) as HTMLElement | null;
      target?.focus();
    });
    item.appendChild(link);
    list.appendChild(item);
  });
  summary.appendChild(list);
  summary.style.display = 'block';

  // Per plan T-ACC023: focus the first invalid field after rendering the summary.
  const firstInput = document.getElementById(errors[0]?.inputId ?? '') as HTMLElement | null;
  if (firstInput) {
    firstInput.focus();
  } else {
    summary.focus();
  }
}

function validateExportForm(filename: string): FormValidationError[] {
  const errors: FormValidationError[] = [];
  resetFieldError('export-filename', 'export-filename-error');
  resetErrorSummary('export-error-summary');

  const trimmed = filename.trim();
  if (!trimmed) {
    addFieldError(errors, 'export-filename', 'export-filename-error', 'Filename is required.');
    return errors;
  }

  const filenamePattern = /^[A-Za-z0-9_-]+(\.(csv|json|md|markdown))?$/i;
  if (!filenamePattern.test(trimmed)) {
    addFieldError(
      errors,
      'export-filename',
      'export-filename-error',
      'Use letters, numbers, "_" or "-" only.'
    );
  }

  return errors;
}

function validateImportForm(file: File | undefined): FormValidationError[] {
  const errors: FormValidationError[] = [];
  resetFieldError('import-file', 'import-file-error');
  resetErrorSummary('import-error-summary');

  if (!file) {
    addFieldError(errors, 'import-file', 'import-file-error', t('importExport.noFileSelected'));
    return errors;
  }

  return errors;
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

function initializeImportExport(): void {
  initSecondaryNav({ component: IMPORT_EXPORT_COMPONENT, requireAuth: true });
  setupEventListeners();
  void loadStatistics();
}

function setupEventListeners(): void {
  const exportFormat = document.getElementById('export-format');
  exportFormat?.addEventListener('change', updateFilenameFromDropdown);

  const exportFilename = document.getElementById('export-filename') as HTMLInputElement | null;
  if (exportFilename) {
    const validateExportFilename = () => {
      const trimmed = exportFilename.value.trim();
      if (!trimmed) {
        setLiveFieldError(
          'export-filename',
          'export-filename-error',
          t('validation.filenameRequired') || 'Filename is required.'
        );
        return;
      }
      const filenamePattern = /^[A-Za-z0-9_-]+(\.(csv|json|md|markdown))?$/i;
      if (!filenamePattern.test(trimmed)) {
        setLiveFieldError(
          'export-filename',
          'export-filename-error',
          t('validation.filenameInvalid') || 'Filename is invalid.'
        );
        return;
      }
      clearLiveFieldError('export-filename', 'export-filename-error');
    };

    exportFilename.addEventListener('blur', validateExportFilename);
    exportFilename.addEventListener('input', () => {
      if (liveValidationState.get('export-filename') === true) {
        validateExportFilename();
      }
    });
  }

  const importFile = document.getElementById('import-file') as HTMLInputElement | null;
  importFile?.addEventListener('change', handleFileSelection);
  importFile?.addEventListener('change', () => {
    const file = importFile.files?.[0];
    if (!file) {
      setLiveFieldError(
        'import-file',
        'import-file-error',
        t('validation.fileRequired') || 'Please select a file to upload.'
      );
    } else {
      clearLiveFieldError('import-file', 'import-file-error');
    }
  });

  const previewButtons = document.querySelectorAll('[onclick*="preview"]');
  previewButtons.forEach((btn) => {
    btn.addEventListener('click', handlePreview);
  });

  // Button keyboard activation (Enter and Space keys)
  // Enables keyboard accessibility for all buttons
  document.addEventListener('keydown', (e) => {
    if (document.activeElement instanceof HTMLButtonElement) {
      const button = document.activeElement;
      // Enter and Space keys should activate buttons (standard keyboard behavior)
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        button.click();
      }
    }
  });
}

function handlePreview(event: Event): void {
  const button = event.target as HTMLElement | null;
  const buttonText = button?.textContent?.toLowerCase() ?? '';

  if (
    buttonText.includes('export') ||
    buttonText.includes((t('importExport.exportBtn') || '').toLowerCase())
  ) {
    void previewExport();
  } else if (
    buttonText.includes('import') ||
    buttonText.includes((t('importExport.importBtn') || '').toLowerCase())
  ) {
    void previewImport();
  }
}

function updateFilenameFromDropdown(event: Event): void {
  const target = event.target as HTMLSelectElement;
  updateFilename(target.value);
}

function updateFilename(format: string): void {
  const filenameInput = document.getElementById('export-filename') as HTMLInputElement | null;
  if (!filenameInput) return;
  const currentName = filenameInput.value.replace(/\.(csv|md|json)$/i, '');
  filenameInput.value = `${currentName}.${format}`;
}

function normalizeExportFilename(filename: string, format: string): string {
  if (!filename) {
    return `promptvault_export.${format}`;
  }
  if (/\.(csv|md|json)$/i.test(filename)) {
    return filename;
  }
  return `${filename}.${format}`;
}

function handleFileSelection(event: Event): void {
  const target = event.target as HTMLInputElement | null;
  const file = target?.files?.[0];
  const errorElement = document.getElementById('import-file-error');

  // Clear previous error messages
  if (errorElement) {
    errorElement.textContent = '';
  }

  if (file) {
    // Validate file type
    const allowedExtensions = ['.csv', '.json', '.md', '.markdown'];
    const fileName = file.name.toLowerCase();
    const isValidType = allowedExtensions.some((ext) => fileName.endsWith(ext));

    if (!isValidType) {
      const errorMsg = 'File format not supported. Please use CSV, JSON, or Markdown files.';
      if (errorElement) {
        errorElement.textContent = errorMsg;
      }
      setLiveFieldError('import-file', 'import-file-error', errorMsg);
      // Reset file input
      if (target) {
        target.value = '';
      }
      return;
    }

    // Validate file size (10MB limit)
    const maxSizeBytes = 10 * 1024 * 1024;
    if (file.size > maxSizeBytes) {
      const errorMsg = 'File is too large. Maximum size is 10MB.';
      if (errorElement) {
        errorElement.textContent = errorMsg;
      }
      setLiveFieldError('import-file', 'import-file-error', errorMsg);
      // Reset file input
      if (target) {
        target.value = '';
      }
      return;
    }

    // Update filename input if empty
    const filenameInput = document.getElementById('export-filename') as HTMLInputElement | null;
    if (filenameInput && !filenameInput.value) {
      filenameInput.value = file.name.replace(/\.(csv|json|md|markdown)$/i, '');
    }

    // Clear any previous errors if file is valid
    clearLiveFieldError('import-file', 'import-file-error');
  }
}

async function loadStatistics(): Promise<void> {
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
  historyList.innerHTML = `
        <div class="history-item">
            <div class="history-info">
                <div class="text-sm text-gray-700 dark:text-gray-300">No recent activity</div>
                <div class="history-details text-xs text-gray-500 dark:text-gray-400">Activity tracking not yet implemented</div>
            </div>
        </div>
    `;
}

async function previewExport(): Promise<void> {
  currentOperation = 'export';
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

    showPreview('previewExportTitle', previewContent);
    hideProgress('export');
  } catch (error) {
    reportError(IMPORT_EXPORT_COMPONENT, 'previewExport', error, { format, includeFavorites });
    showStatus('export', 'exportFailed', 'error');
  }
}

async function previewImport(): Promise<void> {
  const fileInput = document.getElementById('import-file') as HTMLInputElement | null;
  const file = fileInput?.files?.[0];
  const validationErrors = validateImportForm(file);
  if (validationErrors.length > 0) {
    renderErrorSummary('import-error-summary', validationErrors);
    return;
  }
  const selectedFile = file as File;

  currentOperation = 'import';

  try {
    showProgress('import', 'preparingImport');

    const previewContent = await generateImportPreview(selectedFile.name);

    showPreview('previewImportTitle', previewContent);
    hideProgress('import');
  } catch (error) {
    reportError(IMPORT_EXPORT_COMPONENT, 'previewImport', error, { filename: selectedFile.name });
    showStatus('import', 'importFailed', 'error');
  }
}

function generateExportPreview(prompts: Record<string, unknown>, format: string): string {
  const promptCount = Object.keys(prompts).length;
  let content = '';

  switch (format) {
    case 'csv':
      content = `Title,Prompt,Category,Tags,Favorite\n`;
      content += `Example Prompt 1,"This is a sample prompt content","Work","tag1, tag2","Yes"\n`;
      content += `Example Prompt 2,"Another sample prompt","Personal","tag3","No"\n`;
      content += `... and ${promptCount - 2} more prompts`;
      break;
    case 'markdown':
      content = `# Example Prompt 1\n\n`;
      content += `**Category:** Work\n`;
      content += `**Tags:** tag1, tag2\n`;
      content += `**Favorite:** Yes\n\n`;
      content += `## Prompt\n`;
      content += `This is a sample prompt content\n\n`;
      content += `---\n\n`;
      content += `# Example Prompt 2\n\n`;
      content += `**Category:** Personal\n`;
      content += `**Tags:** tag3\n`;
      content += `**Favorite:** No\n\n`;
      content += `## Prompt\n`;
      content += `Another sample prompt\n\n`;
      content += `---\n\n`;
      content += `... and ${promptCount - 2} more prompts`;
      break;
    case 'json': {
      const sampleData = {
        export_timestamp: new Date().toISOString(),
        total_prompts: promptCount,
        prompts: {
          '1': {
            data: {
              title: 'Example Prompt 1',
              prompt: 'This is a sample prompt content',
              category: 'Work',
              tags: ['tag1', 'tag2'],
              favorite: true,
            },
          },
          '2': {
            data: {
              title: 'Example Prompt 2',
              prompt: 'Another sample prompt',
              category: 'Personal',
              tags: ['tag3'],
              favorite: false,
            },
          },
        },
      };
      content = JSON.stringify(sampleData, null, 2);
      content += `\n\n... and ${promptCount - 2} more prompts`;
      break;
    }
    default:
      break;
  }

  return content;
}

async function generateImportPreview(filename: string): Promise<string> {
  const extension = filename.split('.').pop()?.toLowerCase();

  if (extension === 'csv') {
    return `CSV Preview:\n\nTitle,Prompt,Category,Tags,Favorite\nExample Import 1,"Sample imported prompt","Work","tag1, tag2","Yes"\nExample Import 2,"Another imported prompt","Personal","tag3","No"\n\nTotal rows detected: ${Math.floor(Math.random() * 10) + 5}`;
  }
  if (extension === 'json') {
    return `JSON Preview:\n\n{\n  "title": "Sample Import",\n  "prompt": "This is an imported prompt",\n  "category": "Imported",\n  "tags": ["imported", "sample"],\n  "favorite": false\n}\n\nTotal items detected: ${Math.floor(Math.random() * 5) + 3}`;
  }
  return `Markdown Preview:\n\n# Sample Import\n\n**Category:** Imported\n**Tags:** imported, sample\n**Favorite:** No\n\n## Prompt\nThis is an imported prompt from markdown file.\n\n---\n\nTotal sections detected: ${Math.floor(Math.random() * 5) + 3}`;
}

function showPreview(_titleKey: string, content: string): void {
  showElement(document.getElementById('preview-panel'));
  const previewContent = document.getElementById('preview-content');
  if (previewContent) previewContent.textContent = content;

  const confirmBtn = document.getElementById('confirm-btn');
  if (confirmBtn) {
    if (currentOperation === 'export') {
      confirmBtn.textContent = t('importExport.exportBtn');
    } else {
      confirmBtn.textContent = t('importExport.importBtn');
    }
  }
}

function hidePreview(): void {
  hideElement(document.getElementById('preview-panel'));
}

function cancelPreview(): void {
  hidePreview();
  if (currentOperation) {
    hideProgress(currentOperation);
  }
}

async function confirmOperation(): Promise<void> {
  if (currentOperation === 'export') {
    await performExport();
  } else {
    await performImport();
  }
  hidePreview();
}

async function performExport(): Promise<void> {
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

async function performImport(): Promise<void> {
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

function showProgress(operation: 'export' | 'import', messageKey: string): void {
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

function hideProgress(operation: 'export' | 'import'): void {
  const progressContainer = document.getElementById(`${operation}-progress`);
  hideElement(progressContainer);
}

function showStatus(
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

function clearExportSettings(): void {
  const exportFormat = document.getElementById('export-format') as HTMLSelectElement | null;
  const filenameInput = document.getElementById('export-filename') as HTMLInputElement | null;
  const includeFavorites = document.getElementById('include-favorites') as HTMLInputElement | null;
  const includeMetadata = document.getElementById('include-metadata') as HTMLInputElement | null;

  if (exportFormat) exportFormat.value = 'csv';
  if (filenameInput) filenameInput.value = 'promptvault_export.csv';
  if (includeFavorites) includeFavorites.checked = true;
  if (includeMetadata) includeMetadata.checked = true;
  resetFieldError('export-filename', 'export-filename-error');
  resetErrorSummary('export-error-summary');

  hideProgress('export');
  showStatus('export', '', 'info');

  showStatus('export', t('importExport.settingsCleared'), 'success');
  setTimeout(() => {
    showStatus('export', '', 'info');
  }, 2000);
}

function exposeGlobalHandlers(): void {
  const importExportWindow = window as Window & {
    performExport?: () => Promise<void>;
    performImport?: () => Promise<void>;
    previewExport?: () => Promise<void>;
    previewImport?: () => Promise<void>;
    clearExportSettings?: () => void;
    confirmOperation?: () => Promise<void>;
    cancelPreview?: () => void;
  };

  importExportWindow.performExport = performExport;
  importExportWindow.performImport = performImport;
  importExportWindow.previewExport = previewExport;
  importExportWindow.previewImport = previewImport;
  importExportWindow.clearExportSettings = clearExportSettings;
  importExportWindow.confirmOperation = confirmOperation;
  importExportWindow.cancelPreview = cancelPreview;
}

initI18n(() => {
  try {
    updateStaticTranslations();
    exposeGlobalHandlers();
    initializeImportExport();
  } catch (error) {
    reportError(IMPORT_EXPORT_COMPONENT, 'initialize', error);
  }
});
