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
import { initI18n, t, updateStaticTranslations } from '@/utils/i18n';
import { reportError } from '@/telemetry';
import { initSecondaryNav } from '@/utils/secondary-nav';
import {
  clearLiveFieldError,
  getLiveValidationState,
  resetErrorSummary,
  resetFieldError,
  setLiveFieldError,
} from './import-export/validation';
import {
  cancelPreview,
  confirmOperation,
  loadStatistics,
  performExport,
  performImport,
  previewExport,
  previewImport,
  showStatus,
  hideProgress,
} from './import-export/operations';

const IMPORT_EXPORT_COMPONENT = 'importExport';

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
      if (getLiveValidationState('export-filename')) {
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

function clearExportSettings(): void {
  const exportFormat = document.getElementById('export-format') as HTMLSelectElement | null;
  const filenameInput = document.getElementById('export-filename') as HTMLInputElement | null;
  const includeFavorites = document.getElementById('include-favorites') as HTMLInputElement | null;
  const includeMetadata = document.getElementById('include-metadata') as HTMLInputElement | null;

  if (exportFormat) exportFormat.value = 'csv';
  if (filenameInput) filenameInput.value = 'promptvault_export';
  if (includeFavorites) includeFavorites.checked = false;
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
