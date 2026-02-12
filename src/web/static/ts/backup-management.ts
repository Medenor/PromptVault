/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Backup management - TypeScript migration in progress
 */

import '../css/tailwind-globals.css';
import { reportError } from '@/telemetry';
import '@/form-validation';
import { changeLanguage, initI18n, t, updateStaticTranslations } from '@/utils/i18n';
import type { TranslationKey } from '@/types/i18n';
import { hideElement, showElement } from '@/utils/dom';
import { apiFetch, apiGet, apiPost, APIRequestError } from '@/utils/api';
import { announce } from '@/utils/a11y';

interface BackupItem {
  backup_id: string;
  timestamp: string;
  size_bytes: number;
  compressed: boolean;
  prompt_count: number;
  created_by?: string | null;
}

interface BackupStats {
  total_backups?: number;
  total_size?: number;
  compressed_count?: number;
  newest_backup?: string | null;
  oldest_backup?: string | null;
}

interface BackupResponse {
  success: boolean;
  backup_id?: string;
}

interface RestoreResponse {
  success: boolean;
}

interface DeleteResponse {
  success: boolean;
}

interface CleanupResponse {
  success: boolean;
  removed_count?: number;
}

interface CompressResponse {
  success: boolean;
  compressed_count?: number;
}

interface AuthResponse {
  role?: string;
}

interface FormValidationError {
  inputId: string;
  message: string;
}

const BACKUP_COMPONENT = 'backupManagement';
const liveValidationState = new Map<string, boolean>();

let currentBackups: BackupItem[] = [];
let selectedBackupId: string | null = null;

// Focus management for modals
let restoreConfirmationModalTrigger: HTMLElement | null = null;
let deleteConfirmationModalTrigger: HTMLElement | null = null;

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

function initializeBackupManagement(): void {
  setupEventListeners();
  void checkAdminAccess();
  void loadBackups();
  void loadBackupStats();
}

function setupEventListeners(): void {
  const languageSelector = document.getElementById('language-selector');
  languageSelector?.addEventListener('change', handleLanguageChange);

  const backupNameInput = document.getElementById('backup-name') as HTMLInputElement | null;
  if (backupNameInput) {
    const validateBackupName = () => {
      const value = backupNameInput.value.trim();
      if (!value) {
        clearLiveFieldError('backup-name', 'backup-name-error');
        return;
      }
      if (!/^[A-Za-z0-9_-]*$/.test(value)) {
        setLiveFieldError(
          'backup-name',
          'backup-name-error',
          t('validation.backupNameInvalid') || 'Backup name is invalid.'
        );
        return;
      }
      clearLiveFieldError('backup-name', 'backup-name-error');
    };
    backupNameInput.addEventListener('blur', validateBackupName);
    backupNameInput.addEventListener('input', () => {
      if (liveValidationState.get('backup-name') === true) {
        validateBackupName();
      }
    });
  }

  const retentionInput = document.getElementById('retention-days') as HTMLInputElement | null;
  if (retentionInput) {
    const validateRetention = () => {
      const raw = retentionInput.value.trim();
      const value = Number(raw);
      if (!raw) {
        clearLiveFieldError('retention-days', 'retention-days-error');
        return;
      }
      if (!Number.isFinite(value)) {
        setLiveFieldError(
          'retention-days',
          'retention-days-error',
          t('validation.retentionDaysInvalid') || 'Retention days must be a valid number.'
        );
        return;
      }
      if (value < 1) {
        setLiveFieldError(
          'retention-days',
          'retention-days-error',
          t('validation.retentionDaysTooLow') || 'Retention days is too low.'
        );
        return;
      }
      if (value > 3650) {
        setLiveFieldError(
          'retention-days',
          'retention-days-error',
          t('validation.retentionDaysTooHigh') || 'Retention days is too high.'
        );
        return;
      }
      clearLiveFieldError('retention-days', 'retention-days-error');
    };
    retentionInput.addEventListener('blur', validateRetention);
    retentionInput.addEventListener('input', () => {
      if (liveValidationState.get('retention-days') === true) {
        validateRetention();
      }
    });
  }

  const compressInput = document.getElementById('compress-days') as HTMLInputElement | null;
  if (compressInput) {
    const validateCompress = () => {
      const raw = compressInput.value.trim();
      const value = Number(raw);
      if (!raw) {
        clearLiveFieldError('compress-days', 'compress-days-error');
        return;
      }
      if (!Number.isFinite(value)) {
        setLiveFieldError(
          'compress-days',
          'compress-days-error',
          t('validation.compressionDaysInvalid') || 'Compression days must be a valid number.'
        );
        return;
      }
      if (value < 1) {
        setLiveFieldError(
          'compress-days',
          'compress-days-error',
          t('validation.compressionDaysTooLow') || 'Compression days is too low.'
        );
        return;
      }
      if (value > 365) {
        setLiveFieldError(
          'compress-days',
          'compress-days-error',
          t('validation.compressionDaysTooHigh') || 'Compression days is too high.'
        );
        return;
      }
      clearLiveFieldError('compress-days', 'compress-days-error');
    };
    compressInput.addEventListener('blur', validateCompress);
    compressInput.addEventListener('input', () => {
      if (liveValidationState.get('compress-days') === true) {
        validateCompress();
      }
    });
  }

  const confirmRestoreBtn = document.getElementById('confirm-restore-btn');
  confirmRestoreBtn?.addEventListener('click', confirmRestore);

  const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
  confirmDeleteBtn?.addEventListener('click', confirmDelete);
}

function handleLanguageChange(event: Event): void {
  const target = event.target as HTMLSelectElement | null;
  const selectedLanguage = target?.value;
  if (!selectedLanguage) return;

  changeLanguage(selectedLanguage).catch((err) => {
    reportError(BACKUP_COMPONENT, 'changeLanguage', err, { language: selectedLanguage });
  });
}

async function loadBackups(): Promise<void> {
  try {
    const data = await apiGet<{ backups: BackupItem[] }>('/api/backups');

    currentBackups = data.backups || [];
    renderBackupList(currentBackups);
  } catch (error) {
    reportError(BACKUP_COMPONENT, 'loadBackups', error);
    showStatus('backup-status', t('backup.errorLoading'), 'error');
  }
}

async function loadBackupStats(): Promise<void> {
  try {
    const stats = (await apiGet('/api/backups/stats')) as BackupStats;
    updateStatsDisplay(stats);
  } catch (error) {
    reportError(BACKUP_COMPONENT, 'loadBackupStats', error);
  }
}

function updateStatsDisplay(stats: BackupStats): void {
  const totalBackups = document.getElementById('total-backups');
  const totalSize = document.getElementById('total-size');
  const compressedCount = document.getElementById('compressed-count');
  const newestBackup = document.getElementById('newest-backup');
  const oldestBackup = document.getElementById('oldest-backup');

  if (totalBackups) totalBackups.textContent = String(stats.total_backups || 0);
  if (totalSize) totalSize.textContent = formatBytes(stats.total_size || 0);
  if (compressedCount) compressedCount.textContent = String(stats.compressed_count || 0);

  if (newestBackup) {
    newestBackup.textContent = stats.newest_backup
      ? new Date(stats.newest_backup).toLocaleString()
      : 'None';
  }
  if (oldestBackup) {
    oldestBackup.textContent = stats.oldest_backup
      ? new Date(stats.oldest_backup).toLocaleString()
      : 'None';
  }
}

function renderBackupList(backups: BackupItem[]): void {
  const container = document.getElementById('backup-list');
  if (!container) return;

  if (backups.length === 0) {
    container.innerHTML = '<div class="text-gray-500 text-sm">No backups found</div>';
    return;
  }

  const backupItems = backups.map((backup) => createBackupItem(backup)).join('');
  container.innerHTML = backupItems;
}

function createBackupItem(backup: BackupItem): string {
  const timestamp = new Date(backup.timestamp).toLocaleString();
  const size = formatBytes(backup.size_bytes);
  const isCompressed = backup.compressed ? ' (compressed)' : '';
  const compressionIcon = backup.compressed ? '🗜️' : '📄';
  const createdBy = backup.created_by || 'unknown';

  return `
        <div class="bg-gray-50 rounded-lg p-4 border border-gray-200 hover:border-blue-300 transition" data-id="${backup.backup_id}">
            <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-3 md:gap-0 mb-3">
                <h4 class="font-semibold text-gray-900 md:min-w-0">${backup.backup_id}${isCompressed}</h4>
                <div class="flex gap-2 flex-shrink-0">
                    <button class="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-medium transition whitespace-nowrap" onclick="showRestoreModal('${backup.backup_id}')">Restore</button>
                    <button class="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-xs font-medium transition whitespace-nowrap" onclick="showDeleteModal('${backup.backup_id}')">Delete</button>
                </div>
            </div>
            <div class="space-y-1">
                <div class="flex items-center justify-between text-sm text-gray-600">
                    <span>${timestamp}</span>
                    <span>${compressionIcon} ${size}</span>
                </div>
                <div class="text-sm text-gray-600">${backup.prompt_count} prompts</div>
                <div class="text-xs text-gray-500">Created by: ${createdBy}</div>
            </div>
        </div>
    `;
}

async function createBackup(): Promise<void> {
  const backupNameInput = document.getElementById('backup-name') as HTMLInputElement | null;
  const backupName = backupNameInput?.value.trim() ?? '';
  resetFieldError('backup-name', 'backup-name-error');
  resetErrorSummary('backup-create-error-summary');
  const validationErrors: FormValidationError[] = [];

  if (backupName && !/^[A-Za-z0-9_-]*$/.test(backupName)) {
    addFieldError(
      validationErrors,
      'backup-name',
      'backup-name-error',
      t('validation.backupNameInvalid') || 'Backup name is invalid.'
    );
  }

  if (validationErrors.length > 0) {
    renderErrorSummary('backup-create-error-summary', validationErrors);
    return;
  }

  showProgress('backup-progress', 'Creating backup...');

  try {
    const formData = new FormData();
    formData.append('name', backupName);

    const result = await apiFetch<BackupResponse>('/api/backups', {
      method: 'POST',
      body: formData,
    });

    if (result.success) {
      showStatus('backup-status', `Backup created successfully: ${result.backup_id}`, 'success');
      if (backupNameInput) backupNameInput.value = '';
      void loadBackups();
      void loadBackupStats();
    } else {
      showStatus('backup-status', t('backup.createFailed'), 'error');
    }
  } catch (error) {
    reportError(BACKUP_COMPONENT, 'createBackup', error, { backupName });
    showStatus('backup-status', t('backup.createError'), 'error');
  } finally {
    hideProgress('backup-progress');
  }
}

function showRestoreModal(backupId: string): void {
  selectedBackupId = backupId;
  const backup = currentBackups.find((item) => item.backup_id === backupId);
  if (!backup) return;

  // Store trigger element for focus return
  restoreConfirmationModalTrigger = (event as unknown as { target: HTMLElement }).target || null;
  const infoDiv = document.getElementById('restore-backup-info');
  if (infoDiv) {
    infoDiv.innerHTML = `
        <strong>Backup:</strong> ${backup.backup_id}<br>
        <strong>Created:</strong> ${new Date(backup.timestamp).toLocaleString()}<br>
        <strong>Size:</strong> ${formatBytes(backup.size_bytes)}<br>
        <strong>Prompts:</strong> ${backup.prompt_count}
    `;
  }

  const modal = document.getElementById('restore-modal') as HTMLElement | null;
  showElement(modal);
  // Move focus to first focusable element in modal
  if (modal) {
    const firstFocusable = modal.querySelector('h2, button, input, [tabindex="0"]') as HTMLElement;
    if (firstFocusable) {
      firstFocusable.focus();
    }
  }
  setRestoreInProgress(false);
}

function hideRestoreModal(): void {
  hideElement(document.getElementById('restore-modal') as HTMLElement | null);
  selectedBackupId = null;
  // Return focus to trigger element
  if (restoreConfirmationModalTrigger) {
    restoreConfirmationModalTrigger.focus();
  }
}

async function confirmRestore(): Promise<void> {
  if (!selectedBackupId) return;

  const backupIdToRestore = selectedBackupId;
  setRestoreInProgress(true, 'backup.restoreInProgress');
  showProgress('backup-progress', 'Restoring backup...');

  try {
    const result = await apiPost<RestoreResponse>(`/api/backups/${backupIdToRestore}/restore`);

    if (result.success) {
      showStatus('backup-status', t('backup.restoreSuccess'), 'success');
      setRestoreInProgress(true, 'backup.restoreRedirect');
      setTimeout(() => {
        window.location.href = '/';
      }, 2000);
    } else {
      showStatus('backup-status', t('backup.restoreFailed'), 'error');
      setRestoreInProgress(false);
    }
  } catch (error) {
    reportError(BACKUP_COMPONENT, 'restoreBackup', error, { backupId: backupIdToRestore });
    showStatus('backup-status', t('backup.restoreError'), 'error');
    setRestoreInProgress(false);
  } finally {
    hideProgress('backup-progress');
  }
}

function showDeleteModal(backupId: string): void {
  selectedBackupId = backupId;
  const backup = currentBackups.find((item) => item.backup_id === backupId);
  if (!backup) return;

  // Store trigger element for focus return
  deleteConfirmationModalTrigger = (event as unknown as { target: HTMLElement }).target || null;
  const infoDiv = document.getElementById('delete-backup-info');
  if (infoDiv) {
    infoDiv.innerHTML = `
        <strong>Backup:</strong> ${backup.backup_id}<br>
        <strong>Created:</strong> ${new Date(backup.timestamp).toLocaleString()}<br>
        <strong>Size:</strong> ${formatBytes(backup.size_bytes)}
    `;
  }

  const modal = document.getElementById('delete-modal') as HTMLElement | null;
  showElement(modal);
  // Move focus to first focusable element in modal
  if (modal) {
    const firstFocusable = modal.querySelector('h2, button, input, [tabindex="0"]') as HTMLElement;
    if (firstFocusable) {
      firstFocusable.focus();
    }
  }
}

function hideDeleteModal(): void {
  hideElement(document.getElementById('delete-modal') as HTMLElement | null);
  selectedBackupId = null;
  // Return focus to trigger element
  if (deleteConfirmationModalTrigger) {
    deleteConfirmationModalTrigger.focus();
  }
}

async function confirmDelete(): Promise<void> {
  if (!selectedBackupId) return;

  const backupIdToDelete = selectedBackupId;
  hideDeleteModal();
  showProgress('backup-progress', 'Deleting backup...');

  try {
    const result = await apiFetch<DeleteResponse>(`/api/backups/${backupIdToDelete}`, {
      method: 'DELETE',
    });

    if (result.success) {
      showStatus('backup-status', t('backup.deleteSuccess'), 'success');
      void loadBackups();
      void loadBackupStats();
    } else {
      showStatus('backup-status', t('backup.deleteFailed'), 'error');
    }
  } catch (error) {
    reportError(BACKUP_COMPONENT, 'deleteBackup', error, { backupId: backupIdToDelete });
    showStatus('backup-status', t('backup.deleteError'), 'error');
  } finally {
    hideProgress('backup-progress');
  }
}

async function cleanupBackups(): Promise<void> {
  const retentionInput = document.getElementById('retention-days') as HTMLInputElement | null;
  const retentionDays = retentionInput?.value ?? '';
  resetFieldError('retention-days', 'retention-days-error');
  resetErrorSummary('cleanup-error-summary');
  const validationErrors: FormValidationError[] = [];
  const retentionValue = Number(retentionDays);
  if (!Number.isFinite(retentionValue) || retentionValue < 1 || retentionValue > 3650) {
    addFieldError(
      validationErrors,
      'retention-days',
      'retention-days-error',
      !Number.isFinite(retentionValue)
        ? t('validation.retentionDaysInvalid') || 'Retention days must be a valid number.'
        : retentionValue < 1
          ? t('validation.retentionDaysTooLow') || 'Retention period is too low.'
          : t('validation.retentionDaysTooHigh') || 'Retention period is too high.'
    );
  }
  if (validationErrors.length > 0) {
    renderErrorSummary('cleanup-error-summary', validationErrors);
    return;
  }

  showProgress('maintenance-progress', 'Cleaning up old backups...');

  try {
    const formData = new FormData();
    formData.append('retention_days', retentionDays);

    const result = await apiFetch<CleanupResponse>('/api/backups/cleanup', {
      method: 'POST',
      body: formData,
    });

    if (result.success) {
      showStatus(
        'maintenance-status',
        `Cleanup completed: ${result.removed_count || 0} backups removed`,
        'success'
      );
      void loadBackups();
      void loadBackupStats();
    } else {
      showStatus('maintenance-status', t('backup.cleanupFailed'), 'error');
    }
  } catch (error) {
    reportError(BACKUP_COMPONENT, 'cleanupBackups', error, { retentionDays });
    showStatus('maintenance-status', t('backup.cleanupError'), 'error');
  } finally {
    hideProgress('maintenance-progress');
  }
}

async function compressBackups(): Promise<void> {
  const compressInput = document.getElementById('compress-days') as HTMLInputElement | null;
  const compressDays = compressInput?.value ?? '';
  resetFieldError('compress-days', 'compress-days-error');
  resetErrorSummary('compress-error-summary');
  const validationErrors: FormValidationError[] = [];
  const compressValue = Number(compressDays);
  if (!Number.isFinite(compressValue) || compressValue < 1 || compressValue > 365) {
    addFieldError(
      validationErrors,
      'compress-days',
      'compress-days-error',
      !Number.isFinite(compressValue)
        ? t('validation.compressionDaysInvalid') || 'Compression days must be a valid number.'
        : compressValue < 1
          ? t('validation.compressionDaysTooLow') || 'Compression threshold is too low.'
          : t('validation.compressionDaysTooHigh') || 'Compression threshold is too high.'
    );
  }
  if (validationErrors.length > 0) {
    renderErrorSummary('compress-error-summary', validationErrors);
    return;
  }

  showProgress('maintenance-progress', 'Compressing old backups...');

  try {
    const formData = new FormData();
    formData.append('days_threshold', compressDays);

    const result = await apiFetch<CompressResponse>('/api/backups/compress', {
      method: 'POST',
      body: formData,
    });

    if (result.success) {
      showStatus(
        'maintenance-status',
        `Compression completed: ${result.compressed_count || 0} backups compressed`,
        'success'
      );
      void loadBackups();
      void loadBackupStats();
    } else {
      showStatus('maintenance-status', t('backup.compressionFailed'), 'error');
    }
  } catch (error) {
    reportError(BACKUP_COMPONENT, 'compressBackups', error, { daysThreshold: compressDays });
    showStatus('maintenance-status', t('backup.compressionError'), 'error');
  } finally {
    hideProgress('maintenance-progress');
  }
}

function refreshBackups(): void {
  void loadBackups();
  void loadBackupStats();
}

function clearBackupForm(): void {
  const backupNameInput = document.getElementById('backup-name') as HTMLInputElement | null;
  if (backupNameInput) backupNameInput.value = '';
  resetFieldError('backup-name', 'backup-name-error');
  resetErrorSummary('backup-create-error-summary');
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

function showProgress(containerId: string, message: string): void {
  const container = document.getElementById(containerId);
  const fill = document.getElementById(`${containerId}-fill`);
  const status = document.getElementById(containerId.replace('-progress', '-status'));

  container?.classList.remove('hidden');
  if (fill instanceof HTMLElement) {
    fill.style.width = '50%';
  }
  if (status) {
    status.textContent = message;
    status.className = 'text-sm text-blue-600 mt-2';
  }
}

function hideProgress(containerId: string): void {
  const container = document.getElementById(containerId);
  container?.classList.add('hidden');
}

function showStatus(elementId: string, message: string, type: 'info' | 'success' | 'error'): void {
  const element = document.getElementById(elementId);
  if (!element) return;

  element.textContent = message;
  const colorClass =
    type === 'success' ? 'text-green-600' : type === 'error' ? 'text-red-600' : 'text-blue-600';
  element.className = `text-sm ${colorClass} mt-2`;

  const container = element.parentElement;
  if (container && container.id.includes('progress')) {
    container.classList.remove('hidden');
  }

  if (type === 'success') {
    setTimeout(() => {
      if (container && container.id.includes('progress')) {
        container.classList.add('hidden');
      }
    }, 5000);
  }
}

function setRestoreInProgress(isRestoring: boolean, messageKey?: TranslationKey): void {
  const modal = document.getElementById('restore-modal');
  const status = document.getElementById('restore-status');
  const closeButton = modal?.querySelector('.close') as HTMLElement | null;
  const buttons = modal?.querySelectorAll('button');

  if (status) {
    if (isRestoring) {
      showElement(status);
      status.textContent = messageKey ? t(messageKey) : t('backup.restoreInProgress');
      status.className = 'text-sm text-blue-600 mt-4';
    } else {
      hideElement(status);
      status.textContent = '';
    }
  }

  buttons?.forEach((button) => {
    if (button instanceof HTMLButtonElement) {
      button.disabled = isRestoring;
      if (isRestoring) {
        button.classList.add('opacity-50', 'cursor-not-allowed');
      } else {
        button.classList.remove('opacity-50', 'cursor-not-allowed');
      }
    }
  });

  if (closeButton) {
    closeButton.style.display = isRestoring ? 'none' : '';
  }

  if (modal) {
    modal.setAttribute('aria-busy', isRestoring ? 'true' : 'false');
  }
}

async function checkAdminAccess(): Promise<void> {
  try {
    const data = await apiGet<AuthResponse>('/api/auth/me');
    if (data.role === 'admin') {
      const adminBtn = document.getElementById('admin-btn');
      if (adminBtn) {
        (adminBtn as HTMLElement).style.display = '';
      }
    }
  } catch (error) {
    reportError(BACKUP_COMPONENT, 'checkAdminAccess', error);
    if (error instanceof APIRequestError && error.status === 401) {
      window.location.href = '/auth/login';
    } else {
      window.location.href = '/auth/login';
    }
  }
}

function exposeGlobalHandlers(): void {
  const backupWindow = window as Window & {
    createBackup?: () => Promise<void>;
    clearBackupForm?: () => void;
    refreshBackups?: () => void;
    cleanupBackups?: () => Promise<void>;
    compressBackups?: () => Promise<void>;
    showRestoreModal?: (backupId: string) => void;
    hideRestoreModal?: () => void;
    confirmRestore?: () => Promise<void>;
    showDeleteModal?: (backupId: string) => void;
    hideDeleteModal?: () => void;
    confirmDelete?: () => Promise<void>;
  };

  backupWindow.createBackup = createBackup;
  backupWindow.clearBackupForm = clearBackupForm;
  backupWindow.refreshBackups = refreshBackups;
  backupWindow.cleanupBackups = cleanupBackups;
  backupWindow.compressBackups = compressBackups;
  backupWindow.showRestoreModal = showRestoreModal;
  backupWindow.hideRestoreModal = hideRestoreModal;
  backupWindow.confirmRestore = confirmRestore;
  backupWindow.showDeleteModal = showDeleteModal;
  backupWindow.hideDeleteModal = hideDeleteModal;
  backupWindow.confirmDelete = confirmDelete;
}

initI18n(() => {
  try {
    updateStaticTranslations();
    exposeGlobalHandlers();
    initializeBackupManagement();
  } catch (error) {
    reportError(BACKUP_COMPONENT, 'initialize', error);
  }
});
