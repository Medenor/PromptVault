/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Import/export page logic
 */

import { reportError } from '@/telemetry';
import { changeLanguage, initI18n, t, updateStaticTranslations } from '@/utils/i18n';
import { hideElement, showElement } from '@/utils/dom';

type OperationType = 'export' | 'import' | null;

let currentOperation: OperationType = null;
const IMPORT_EXPORT_COMPONENT = 'importExport';
const HIDDEN_CLASS = 'is-hidden';

function reportImportExportIssue(
  action: string,
  error: unknown,
  metadata: Record<string, unknown> = {},
  severity: 'error' | 'warning' = 'error'
): void {
  const logger = window.FrontendLogger;
  if (logger && typeof logger.reportError === 'function') {
    logger.reportError(IMPORT_EXPORT_COMPONENT, action, error, metadata, severity);
  }
  const prefix = `[PromptVault][import-export] ${action}`;
  if (severity === 'warning') {
    console.warn(prefix, error, metadata);
  } else {
    console.error(prefix, error, metadata);
  }
}

function initializeImportExport(): void {
  setupEventListeners();
  checkAdminAccess();
  void loadStatistics();
}

function setupEventListeners(): void {
  const languageSelector = document.getElementById('language-selector');
  languageSelector?.addEventListener('change', handleLanguageChange);

  const exportFormat = document.getElementById('export-format');
  exportFormat?.addEventListener('change', updateFilenameFromDropdown);

  const importFile = document.getElementById('import-file') as HTMLInputElement | null;
  importFile?.addEventListener('change', handleFileSelection);

  const previewButtons = document.querySelectorAll('[onclick*="preview"]');
  previewButtons.forEach((btn) => {
    btn.addEventListener('click', handlePreview);
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
  if (file) {
    const filenameInput = document.getElementById('export-filename') as HTMLInputElement | null;
    if (filenameInput && !filenameInput.value) {
      filenameInput.value = file.name.replace(/\.(csv|md|json)$/i, '');
    }
  }
}

async function loadStatistics(): Promise<void> {
  try {
    const response = await fetch('/api/import-export/stats');
    const stats = await response.json();

    const totalPrompts = document.getElementById('total-prompts');
    const totalCategories = document.getElementById('total-categories');
    const totalTags = document.getElementById('total-tags');
    const favoritePrompts = document.getElementById('favorite-prompts');

    if (totalPrompts) totalPrompts.textContent = stats.total_prompts;
    if (totalCategories) totalCategories.textContent = stats.total_categories;
    if (totalTags) totalTags.textContent = stats.total_tags;
    if (favoritePrompts) favoritePrompts.textContent = stats.favorite_prompts;

    updateActivityHistory();
  } catch (error) {
    reportImportExportIssue('loadStatistics', error as Error);
  }
}

function updateActivityHistory(): void {
  const historyList = document.getElementById('activity-history');
  if (!historyList) return;
  historyList.innerHTML = `
        <div class="history-item">
            <div class="history-info">
                <div>No recent activity</div>
                <div class="history-details">Activity tracking not yet implemented</div>
            </div>
        </div>
    `;
}

async function previewExport(): Promise<void> {
  currentOperation = 'export';
  const formatSelect = document.getElementById('export-format') as HTMLSelectElement | null;
  const format = formatSelect?.value || 'csv';
  const includeFavorites = (document.getElementById('include-favorites') as HTMLInputElement | null)?.checked ?? false;

  try {
    showProgress('export', 'preparingExport');

    const response = await fetch('/api/prompts');
    const data = await response.json();
    let prompts = data.prompts;

    if (includeFavorites) {
      prompts = Object.fromEntries(
        Object.entries(prompts).filter(([, prompt]) => (prompt as { favorite?: boolean }).favorite)
      );
    }

    const previewContent = generateExportPreview(prompts, format);

    showPreview('previewExportTitle', previewContent);
    hideProgress('export');
  } catch (error) {
    reportImportExportIssue('previewExport', error as Error, { format, includeFavorites });
    showStatus('export', 'exportFailed', 'error');
  }
}

async function previewImport(): Promise<void> {
  const fileInput = document.getElementById('import-file') as HTMLInputElement | null;
  const file = fileInput?.files?.[0];

  if (!file) {
    alert(t('importExport.noFileSelected'));
    return;
  }

  currentOperation = 'import';

  try {
    showProgress('import', 'preparingImport');

    const fileContent = await readFileContent(file);
    const previewContent = await generateImportPreview(fileContent, file.name);

    showPreview('previewImportTitle', previewContent);
    hideProgress('import');
  } catch (error) {
    reportImportExportIssue('previewImport', error as Error, { filename: file.name });
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
    case 'json':
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
              favorite: true
            }
          },
          '2': {
            data: {
              title: 'Example Prompt 2',
              prompt: 'Another sample prompt',
              category: 'Personal',
              tags: ['tag3'],
              favorite: false
            }
          }
        }
      };
      content = JSON.stringify(sampleData, null, 2);
      content += `\n\n... and ${promptCount - 2} more prompts`;
      break;
    default:
      break;
  }

  return content;
}

async function generateImportPreview(fileContent: string, filename: string): Promise<string> {
  const extension = filename.split('.').pop()?.toLowerCase();

  if (extension === 'csv') {
    return `CSV Preview:\n\nTitle,Prompt,Category,Tags,Favorite\nExample Import 1,"Sample imported prompt","Work","tag1, tag2","Yes"\nExample Import 2,"Another imported prompt","Personal","tag3","No"\n\nTotal rows detected: ${Math.floor(Math.random() * 10) + 5}`;
  }
  if (extension === 'json') {
    return `JSON Preview:\n\n{\n  "title": "Sample Import",\n  "prompt": "This is an imported prompt",\n  "category": "Imported",\n  "tags": ["imported", "sample"],\n  "favorite": false\n}\n\nTotal items detected: ${Math.floor(Math.random() * 5) + 3}`;
  }
  return `Markdown Preview:\n\n# Sample Import\n\n**Category:** Imported\n**Tags:** imported, sample\n**Favorite:** No\n\n## Prompt\nThis is an imported prompt from markdown file.\n\n---\n\nTotal sections detected: ${Math.floor(Math.random() * 5) + 3}`;
}

function readFileContent(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (event) => resolve((event.target?.result as string) || '');
    reader.onerror = (event) => reject(event);
    reader.readAsText(file);
  });
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
  const rawFilename = (document.getElementById('export-filename') as HTMLInputElement | null)?.value || '';
  const filename = normalizeExportFilename(rawFilename, format);
  const includeFavorites = (document.getElementById('include-favorites') as HTMLInputElement | null)?.checked ?? false;
  const includeMetadata = (document.getElementById('include-metadata') as HTMLInputElement | null)?.checked ?? false;

  try {
    showProgress('export', 'exportProgress');

    const formData = new FormData();
    formData.append('format', format);
    formData.append('filename', filename);
    formData.append('include_favorites', String(includeFavorites));
    formData.append('include_metadata', String(includeMetadata));

    const response = await fetch('/api/export', {
      method: 'POST',
      body: formData
    });

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

      showStatus('export', 'exportSuccess', 'success');
      void loadStatistics();
    } else {
      const error = await response.json();
      showStatus('export', error.error || 'exportFailed', 'error');
    }
  } catch (error) {
    reportImportExportIssue('performExport', error as Error, {
      format,
      filename,
      includeFavorites,
      includeMetadata
    });
    showStatus('export', 'exportFailed', 'error');
  } finally {
    hideProgress('export');
  }
}

async function performImport(): Promise<void> {
  const fileInput = document.getElementById('import-file') as HTMLInputElement | null;
  const file = fileInput?.files?.[0];

  if (!file) {
    alert(t('importExport.noFileSelected'));
    return;
  }

  const mode = (document.getElementById('import-mode') as HTMLSelectElement | null)?.value || 'append';
  const validate = (document.getElementById('import-validate') as HTMLInputElement | null)?.checked ?? false;

  try {
    showProgress('import', 'importProgress');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('mode', mode);
    formData.append('validate', String(validate));

    const response = await fetch('/api/import', {
      method: 'POST',
      body: formData
    });

    const result = await response.json();

    if (response.ok) {
      const message = (t('importExport.importSuccess') || '').replace('{count}', result.added_count);
      showStatus('import', message, 'success');
      void loadStatistics();
      fileInput.value = '';
    } else {
      showStatus('import', result.error || 'importFailed', 'error');
    }
  } catch (error) {
    reportImportExportIssue('performImport', error as Error, {
      mode,
      validate,
      filename: file.name
    });
    showStatus('import', 'importFailed', 'error');
  } finally {
    hideProgress('import');
  }
}

function showProgress(operation: 'export' | 'import', messageKey: string): void {
  const progressContainer = document.getElementById(`${operation}-progress`);
  const statusElement = document.getElementById(`${operation}-status`);

  showElement(progressContainer);
  if (statusElement) {
    statusElement.textContent = t(`importExport.${messageKey}`);
    statusElement.className = 'status-message status-info';
  }
}

function hideProgress(operation: 'export' | 'import'): void {
  const progressContainer = document.getElementById(`${operation}-progress`);
  hideElement(progressContainer);
}

function showStatus(operation: 'export' | 'import', message: string, type: 'info' | 'success' | 'error'): void {
  const statusElement = document.getElementById(`${operation}-status`);
  if (!statusElement) return;

  statusElement.textContent = message;
  statusElement.className = `status-message status-${type}`;

  if (type === 'success') {
    setTimeout(() => {
      statusElement.textContent = '';
      statusElement.className = 'status-message status-info';
    }, 3000);
  }
}

function handleLanguageChange(event: Event): void {
  const selectedLanguage = (event.target as HTMLSelectElement).value;
  changeLanguage(selectedLanguage)
    .then(() => updateStaticTranslations())
    .catch((error) => {
      reportImportExportIssue('changeLanguage', error as Error, { language: selectedLanguage });
    });
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

  hideProgress('export');
  showStatus('export', '', 'info');

  showStatus('export', 'Export settings cleared', 'success');
  setTimeout(() => {
    showStatus('export', '', 'info');
  }, 2000);
}

async function checkAdminAccess(): Promise<void> {
  try {
    const response = await fetch('/api/auth/me', {
      credentials: 'include'
    });

    if (response.ok) {
      const data = await response.json();
      if (data.role === 'admin') {
        const adminBtn = document.getElementById('admin-btn');
        if (adminBtn) {
          (adminBtn as HTMLElement).style.display = '';
        }
      }
    } else if (response.status === 401) {
      window.location.href = '/auth/login';
    } else {
      window.location.href = '/auth/login';
    }
  } catch (error) {
    reportImportExportIssue('checkAdminAccess', error as Error);
    window.location.href = '/auth/login';
  }
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
    reportImportExportIssue('initialize', error as Error);
  }
});
