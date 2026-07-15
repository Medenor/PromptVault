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
import { initI18n, t, updateStaticTranslations, changeLanguage } from '@/utils/i18n';
import type { TranslationKey } from '@/types/i18n';
import { hideElement, showElement } from '@/utils/dom';
import { apiFetch, apiGet, apiPost, apiPostForm, APIRequestError } from '@/utils/api';
import { announce } from '@/utils/a11y';
import { loadMonitoringDashboard, loadAuditLog } from './components/backup-monitoring-dashboard';
import { initSecondaryNav } from '@/utils/secondary-nav';

interface CloudProvider {
  id: string;
  name: string;
  provider_type: string;
  endpoint_url: string | null;
  bucket_name: string;
  prefix: string;
  region: string | null;
  enabled: boolean;
}

interface EncryptionConfig {
  is_enabled: boolean;
  algorithm: string;
  kdf: string;
  key_version: number;
  rotated_at: string | null;
}

interface BackupSchedule {
  id: string;
  enabled: boolean;
  frequency: string;
  hour: number;
  minute: number;
  day_of_week: number | null;
  day_of_month: number | null;
  retention_days: number;
  cloud_provider_id: string | null;
  last_run_at: string | null;
  last_run_status: string | null;
}

interface BackupItem {
  backup_id: string;
  timestamp: string;
  size_bytes: number;
  compressed: boolean;
  prompt_count: number;
  created_by?: string | null;
  storage_path?: string | null;
  cloud_provider_id?: string | null;
  cloud_path?: string | null;
  is_encrypted?: boolean;
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
  dry_run?: boolean;
  removed_count?: number;
}

interface CompressResponse {
  success: boolean;
  compressed_count?: number;
}

interface FormValidationError {
  inputId: string;
  message: string;
}

const BACKUP_COMPONENT = 'backupManagement';
const liveValidationState = new Map<string, boolean>();

let currentBackups: BackupItem[] = [];
const cloudProviderNames = new Map<string, string>();
let selectedBackupId: string | null = null;
let encryptionEnabled = false;

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
  initSecondaryNav({ component: BACKUP_COMPONENT, requireAuth: true });
  setupEventListeners();
  void loadBackups();
  void loadBackupStats();
  void loadMonitoringDashboard();
  void loadAuditLog();
  void loadSchedule();
  void loadEncryptionConfig();
  void loadCloudProviders();

  // Monitoring/audit tables are rendered with translated headers at fetch
  // time, so a language switch needs to re-fetch them to pick up the new
  // strings (updateStaticTranslations() only covers data-i18n elements).
  // initI18n() also binds its own 'change' listener that calls
  // changeLanguage() to swap the active i18next language; that call is
  // idempotent, so awaiting our own changeLanguage() here (rather than
  // racing a plain synchronous reload) guarantees the dashboard is
  // re-fetched only after the new language is actually active.
  document.querySelectorAll('.language-selector').forEach((el) => {
    el.addEventListener('change', () => {
      if (!(el instanceof HTMLSelectElement)) return;
      void changeLanguage(el.value).then(() => {
        void loadMonitoringDashboard();
        void loadAuditLog();
      });
    });
  });
}

function setupEventListeners(): void {
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

  const retentionInput = document.getElementById(
    'cleanup-retention-days'
  ) as HTMLInputElement | null;
  if (retentionInput) {
    const validateRetention = () => {
      const raw = retentionInput.value.trim();
      const value = Number(raw);
      if (!raw) {
        clearLiveFieldError('cleanup-retention-days', 'retention-days-error');
        return;
      }
      if (!Number.isFinite(value)) {
        setLiveFieldError(
          'cleanup-retention-days',
          'retention-days-error',
          t('validation.retentionDaysInvalid') || 'Retention days must be a valid number.'
        );
        return;
      }
      if (value < 1) {
        setLiveFieldError(
          'cleanup-retention-days',
          'retention-days-error',
          t('validation.retentionDaysTooLow') || 'Retention days is too low.'
        );
        return;
      }
      if (value > 3650) {
        setLiveFieldError(
          'cleanup-retention-days',
          'retention-days-error',
          t('validation.retentionDaysTooHigh') || 'Retention days is too high.'
        );
        return;
      }
      clearLiveFieldError('cleanup-retention-days', 'retention-days-error');
    };
    retentionInput.addEventListener('blur', validateRetention);
    retentionInput.addEventListener('input', () => {
      if (liveValidationState.get('cleanup-retention-days') === true) {
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

  const frequencySelect = document.getElementById('schedule-frequency') as HTMLSelectElement | null;
  frequencySelect?.addEventListener('change', () => {
    updateDayFieldVisibility(frequencySelect.value);
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
  const compressedCount = document.getElementById('compressed-count');
  const newestBackup = document.getElementById('newest-backup');
  const oldestBackup = document.getElementById('oldest-backup');

  if (compressedCount) compressedCount.textContent = String(stats.compressed_count || 0);

  if (newestBackup) {
    newestBackup.textContent = stats.newest_backup
      ? new Date(stats.newest_backup).toLocaleString()
      : t('backup.noneValue');
  }
  if (oldestBackup) {
    oldestBackup.textContent = stats.oldest_backup
      ? new Date(stats.oldest_backup).toLocaleString()
      : t('backup.noneValue');
  }
}

function renderBackupList(backups: BackupItem[]): void {
  const container = document.getElementById('backup-list');
  if (!container) return;

  if (backups.length === 0) {
    container.innerHTML = `<div class="text-gray-500 text-sm dark:text-gray-400">${escapeHtml(t('backup.noBackupsFound'))}</div>`;
    return;
  }

  const backupItems = backups.map((backup) => createBackupItem(backup)).join('');
  container.innerHTML = backupItems;
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function createBackupItem(backup: BackupItem): string {
  const timestamp = new Date(backup.timestamp).toLocaleString();
  const size = formatBytes(backup.size_bytes);
  const isCompressed = backup.compressed ? ' (compressed)' : '';
  const compressionIcon = backup.compressed ? '🗜️' : '📄';
  const createdBy = escapeHtml(backup.created_by || 'unknown');
  const backupId = escapeHtml(backup.backup_id);
  const cloudProviderName = backup.cloud_provider_id
    ? cloudProviderNames.get(backup.cloud_provider_id) || backup.cloud_provider_id
    : '';
  const localBadge = backup.storage_path
    ? `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-gray-200 text-gray-700 text-xs font-medium dark:bg-gray-700 dark:text-gray-300">💻 ${escapeHtml(t('backup.localBadge'))}</span>`
    : '';
  const cloudBadge = backup.cloud_provider_id
    ? `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 text-xs font-medium" title="${escapeHtml(cloudProviderName)}">☁️ ${escapeHtml(t('backup.cloudBadge'))}</span>`
    : '';
  const storageBadge = `${localBadge}${cloudBadge}`;
  const encryptedBadge = backup.is_encrypted
    ? `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 text-xs font-medium" title="${escapeHtml(t('backup.encryptedTooltip'))}">🔒 ${escapeHtml(t('backup.encryptedBadge'))}</span>`
    : '';

  return `
        <div class="bg-gray-50 rounded-lg p-4 border border-gray-200 hover:border-blue-300 transition dark:bg-gray-900 dark:border-gray-700" data-id="${backupId}" data-encrypted="${backup.is_encrypted ? 'true' : 'false'}">
            <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-3 md:gap-0 mb-3">
                <h4 class="font-semibold text-gray-900 min-w-0 truncate dark:text-gray-100" title="${backupId}${isCompressed}">${backupId}${isCompressed}</h4>
                <div class="flex gap-2 flex-shrink-0">
                    <button class="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-medium transition whitespace-nowrap" data-backup-id="${backupId}" data-i18n="backup.restoreBtn" onclick="showRestoreModal(this.dataset.backupId)">${escapeHtml(t('backup.restoreBtn'))}</button>
                    <button class="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-xs font-medium transition whitespace-nowrap" data-backup-id="${backupId}" data-i18n="backup.deleteBtn" onclick="showDeleteModal(this.dataset.backupId)">${escapeHtml(t('backup.deleteBtn'))}</button>
                </div>
            </div>
            <div class="flex items-center gap-2 mb-2">${storageBadge}${encryptedBadge}</div>
            <div class="space-y-1">
                <div class="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
                    <span>${escapeHtml(timestamp)}</span>
                    <span>${compressionIcon} ${escapeHtml(size)}</span>
                </div>
                <div class="text-sm text-gray-600 dark:text-gray-400">${backup.prompt_count} <span data-i18n="backup.promptsCount">${escapeHtml(t('backup.promptsCount'))}</span></div>
                <div class="text-xs text-gray-500 dark:text-gray-400"><span data-i18n="backup.createdByLabel">${escapeHtml(t('backup.createdByLabel'))}</span> ${createdBy}</div>
            </div>
        </div>
    `;
}

async function createBackup(): Promise<void> {
  const backupNameInput = document.getElementById('backup-name') as HTMLInputElement | null;
  const backupName = backupNameInput?.value.trim() ?? '';
  const passphraseInput = document.getElementById(
    'backup-create-passphrase'
  ) as HTMLInputElement | null;
  const passphrase = passphraseInput?.value ?? '';
  const cloudProviderInput = document.getElementById(
    'backup-create-cloud-provider'
  ) as HTMLSelectElement | null;
  const cloudProviderId = cloudProviderInput?.value ?? '';
  resetFieldError('backup-name', 'backup-name-error');
  resetFieldError('backup-create-passphrase', 'backup-create-passphrase-error');
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

  if (encryptionEnabled && !passphrase) {
    addFieldError(
      validationErrors,
      'backup-create-passphrase',
      'backup-create-passphrase-error',
      t('validation.passphraseRequired') || 'Encryption passphrase is required.'
    );
  }

  if (validationErrors.length > 0) {
    renderErrorSummary('backup-create-error-summary', validationErrors);
    return;
  }

  showProgress('backup-progress', t('backup.creatingBackupProgress'));

  try {
    const formData = new FormData();
    formData.append('name', backupName);
    if (encryptionEnabled) {
      formData.append('encrypt', 'true');
      formData.append('passphrase', passphrase);
    }
    if (cloudProviderId) {
      formData.append('cloud_provider_id', cloudProviderId);
    }

    const result = await apiPostForm<BackupResponse>('/api/backups', formData);

    if (result.success) {
      showStatus('backup-status', `Backup created successfully: ${result.backup_id}`, 'success');
      if (backupNameInput) backupNameInput.value = '';
      if (passphraseInput) passphraseInput.value = '';
      void loadBackups();
      void loadBackupStats();
      void loadMonitoringDashboard();
      void loadAuditLog();
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
        <strong>${escapeHtml(t('backup.backupLabel'))}</strong> ${escapeHtml(backup.backup_id)}<br>
        <strong>${escapeHtml(t('backup.createdLabel'))}</strong> ${escapeHtml(new Date(backup.timestamp).toLocaleString())}<br>
        <strong>${escapeHtml(t('backup.sizeLabel'))}</strong> ${escapeHtml(formatBytes(backup.size_bytes))}<br>
        <strong>${escapeHtml(t('backup.promptsLabel'))}</strong> ${backup.prompt_count}
    `;
  }

  const passphraseContainer = document.getElementById('restore-passphrase-container');
  const passphraseInput = document.getElementById('restore-passphrase') as HTMLInputElement | null;
  if (backup.is_encrypted) {
    showElement(passphraseContainer);
  } else {
    hideElement(passphraseContainer);
  }
  if (passphraseInput) passphraseInput.value = '';
  resetFieldError('restore-passphrase', 'restore-passphrase-error');

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
  const backup = currentBackups.find((item) => item.backup_id === backupIdToRestore);
  const passphraseInput = document.getElementById('restore-passphrase') as HTMLInputElement | null;
  const passphrase = passphraseInput?.value ?? '';

  resetFieldError('restore-passphrase', 'restore-passphrase-error');
  if (backup?.is_encrypted && !passphrase) {
    setLiveFieldError(
      'restore-passphrase',
      'restore-passphrase-error',
      t('validation.passphraseRequired') || 'Encryption passphrase is required.'
    );
    passphraseInput?.focus();
    return;
  }

  setRestoreInProgress(true, 'backup.restoreInProgress');
  showProgress('backup-progress', t('backup.restoringBackupProgress'));

  try {
    const result = await apiPost<RestoreResponse>(`/api/backups/${backupIdToRestore}/restore`, {
      passphrase: passphrase || undefined,
    });

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
    const message = error instanceof APIRequestError ? error.message : t('backup.restoreError');
    setRestoreInProgress(false);
    showStatus('restore-status', message, 'error');
    showElement(document.getElementById('restore-status'));
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
        <strong>${escapeHtml(t('backup.backupLabel'))}</strong> ${escapeHtml(backup.backup_id)}<br>
        <strong>${escapeHtml(t('backup.createdLabel'))}</strong> ${escapeHtml(new Date(backup.timestamp).toLocaleString())}<br>
        <strong>${escapeHtml(t('backup.sizeLabel'))}</strong> ${escapeHtml(formatBytes(backup.size_bytes))}
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
  showProgress('backup-progress', t('backup.deletingBackupProgress'));

  try {
    const result = await apiFetch<DeleteResponse>(`/api/backups/${backupIdToDelete}`, {
      method: 'DELETE',
    });

    if (result.success) {
      showStatus('backup-status', t('backup.deleteSuccess'), 'success');
      void loadBackups();
      void loadBackupStats();
      void loadMonitoringDashboard();
      void loadAuditLog();
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

function showDeleteAllModal(): void {
  const modal = document.getElementById('delete-all-modal') as HTMLElement | null;
  showElement(modal);
  const firstFocusable = modal?.querySelector('h2, button') as HTMLElement | null;
  firstFocusable?.focus();
}

function hideDeleteAllModal(): void {
  hideElement(document.getElementById('delete-all-modal') as HTMLElement | null);
}

async function confirmDeleteAll(): Promise<void> {
  hideDeleteAllModal();
  showProgress('backup-progress', t('backup.deletingAllBackupsProgress'));

  try {
    const result = await apiFetch<{ deleted: string[]; failed: string[] }>(
      '/api/backups?confirm=DELETE_ALL',
      {
        method: 'DELETE',
      }
    );

    const count = result.deleted?.length ?? 0;
    const failCount = result.failed?.length ?? 0;
    if (failCount > 0) {
      showStatus('backup-status', `Deleted ${count} backup(s), ${failCount} failed.`, 'error');
    } else {
      showStatus('backup-status', `Deleted ${count} backup(s).`, 'success');
    }
    void loadBackups();
    void loadBackupStats();
    void loadMonitoringDashboard();
    void loadAuditLog();
  } catch (error) {
    reportError(BACKUP_COMPONENT, 'deleteAllBackups', error, {});
    showStatus('backup-status', t('backup.deleteError'), 'error');
  } finally {
    hideProgress('backup-progress');
  }
}

async function cleanupBackups(): Promise<void> {
  const retentionInput = document.getElementById(
    'cleanup-retention-days'
  ) as HTMLInputElement | null;
  const retentionDays = retentionInput?.value ?? '';
  resetFieldError('cleanup-retention-days', 'retention-days-error');
  resetErrorSummary('cleanup-error-summary');
  const validationErrors: FormValidationError[] = [];
  const retentionValue = Number(retentionDays);
  if (!Number.isFinite(retentionValue) || retentionValue < 1 || retentionValue > 3650) {
    addFieldError(
      validationErrors,
      'cleanup-retention-days',
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

  showProgress('maintenance-progress', t('backup.cleaningUpBackupsProgress'));

  try {
    const formData = new FormData();
    formData.append('retention_days', retentionDays);
    formData.append('dry_run', 'false');

    const result = await apiPostForm<CleanupResponse>('/api/backups/cleanup', formData);

    if (result.success) {
      showStatus(
        'maintenance-status',
        `Cleanup completed: ${result.removed_count || 0} backups removed`,
        'success'
      );
      void loadBackups();
      void loadBackupStats();
      void loadMonitoringDashboard();
      void loadAuditLog();
    } else {
      showStatus('maintenance-status', t('backup.cleanupFailed'), 'error');
    }
  } catch (error) {
    reportError(BACKUP_COMPONENT, 'cleanupBackups', error, {});
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

  showProgress('maintenance-progress', t('backup.compressingBackupsProgress'));

  try {
    const formData = new FormData();
    formData.append('days_threshold', compressDays);

    const result = await apiPostForm<CompressResponse>('/api/backups/compress', formData);

    if (result.success) {
      showStatus(
        'maintenance-status',
        `Compression completed: ${result.compressed_count || 0} backups compressed`,
        'success'
      );
      void loadBackups();
      void loadBackupStats();
      void loadMonitoringDashboard();
      void loadAuditLog();
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
  void loadMonitoringDashboard();
  void loadAuditLog();
}

function clearBackupForm(): void {
  const backupNameInput = document.getElementById('backup-name') as HTMLInputElement | null;
  if (backupNameInput) backupNameInput.value = '';
  const passphraseInput = document.getElementById(
    'backup-create-passphrase'
  ) as HTMLInputElement | null;
  if (passphraseInput) passphraseInput.value = '';
  resetFieldError('backup-name', 'backup-name-error');
  resetFieldError('backup-create-passphrase', 'backup-create-passphrase-error');
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

async function loadCloudProviders(): Promise<void> {
  try {
    const data = await apiGet<{ providers: CloudProvider[] }>('/api/backup-providers');
    renderCloudProviders(data.providers || []);
    populateCloudProviderSelect('schedule-cloud-provider', data.providers || []);
    populateCloudProviderSelect('backup-create-cloud-provider', data.providers || []);
    cloudProviderNames.clear();
    for (const provider of data.providers || []) {
      cloudProviderNames.set(provider.id, provider.name);
    }
    renderBackupList(currentBackups);
  } catch {
    const list = document.getElementById('cloud-providers-list');
    if (list)
      list.innerHTML = `<div class="text-gray-500 text-sm dark:text-gray-400">${escapeHtml(t('backup.noProvidersConfigured'))}</div>`;
  }
}

function populateCloudProviderSelect(selectId: string, providers: CloudProvider[]): void {
  const select = document.getElementById(selectId) as HTMLSelectElement | null;
  if (!select) return;

  const previousValue = select.value;
  const noneLabel = escapeHtml(t('backup.scheduleCloudProviderNone') || 'Local only');
  const optionsHtml = providers
    .map((p) => `<option value="${escapeHtml(p.id)}">${escapeHtml(p.name)}</option>`)
    .join('');
  select.innerHTML = `<option value="">${noneLabel}</option>${optionsHtml}`;

  if (providers.some((p) => p.id === previousValue)) {
    select.value = previousValue;
  }
}

function renderCloudProviders(providers: CloudProvider[]): void {
  const list = document.getElementById('cloud-providers-list');
  if (!list) return;

  if (providers.length === 0) {
    list.innerHTML = `<div class="text-gray-500 text-sm dark:text-gray-400">${escapeHtml(t('backup.noProvidersConfigured'))}</div>`;
    return;
  }

  list.innerHTML = providers
    .map((p) => {
      const pid = escapeHtml(p.id);
      const endpointPart = p.endpoint_url ? ` (${escapeHtml(p.endpoint_url)})` : '';
      return `
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-gray-50 rounded-lg p-3 border border-gray-200 dark:bg-gray-900 dark:border-gray-700">
      <div class="min-w-0">
        <div class="font-medium text-gray-900 break-words dark:text-gray-100">${escapeHtml(p.name)}</div>
        <div class="text-xs text-gray-500 break-words dark:text-gray-400">${escapeHtml(p.provider_type)} — ${escapeHtml(p.bucket_name)}${endpointPart}</div>
      </div>
      <div class="flex gap-2 shrink-0">
        <button class="px-2 py-1 text-xs bg-green-600 hover:bg-green-700 text-white rounded" data-provider-id="${pid}" data-i18n="backup.testBtn" onclick="testCloudProvider(this.dataset.providerId)">${escapeHtml(t('backup.testBtn'))}</button>
        <button class="px-2 py-1 text-xs bg-red-600 hover:bg-red-700 text-white rounded" data-provider-id="${pid}" data-i18n="backup.deleteBtn" onclick="deleteCloudProvider(this.dataset.providerId)">${escapeHtml(t('backup.deleteBtn'))}</button>
      </div>
    </div>`;
    })
    .join('');
}

async function addCloudProvider(): Promise<void> {
  const name = (document.getElementById('provider-name') as HTMLInputElement)?.value ?? '';
  const endpoint = (document.getElementById('provider-endpoint') as HTMLInputElement)?.value ?? '';
  const bucket = (document.getElementById('provider-bucket') as HTMLInputElement)?.value ?? '';
  const region = (document.getElementById('provider-region') as HTMLInputElement)?.value ?? '';
  const accessKey =
    (document.getElementById('provider-access-key') as HTMLInputElement)?.value ?? '';
  const secretKey =
    (document.getElementById('provider-secret-key') as HTMLInputElement)?.value ?? '';
  const statusEl = document.getElementById('cloud-status');

  if (!name || !bucket || !accessKey || !secretKey) {
    if (statusEl) {
      statusEl.textContent = t('backup.cloudProviderFieldsRequired');
      statusEl.className = 'text-sm text-red-600 mt-2';
    }
    return;
  }

  try {
    await apiFetch('/api/backup-providers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        provider_type: 's3',
        endpoint_url: endpoint || null,
        bucket_name: bucket,
        region: region || null,
        access_key: accessKey,
        secret_key: secretKey,
      }),
    });
    if (statusEl) {
      statusEl.textContent = t('backup.cloudProviderAdded');
      statusEl.className = 'text-sm text-green-600 mt-2';
    }
    void loadCloudProviders();
  } catch (error) {
    reportError(BACKUP_COMPONENT, 'addCloudProvider', error);
    if (statusEl) {
      statusEl.textContent = t('backup.cloudProviderAddFailed');
      statusEl.className = 'text-sm text-red-600 mt-2';
    }
  }
}

async function testCloudProvider(providerId: string): Promise<void> {
  const statusEl = document.getElementById('cloud-status');
  try {
    const result = await apiPost<{ success: boolean; message: string }>(
      `/api/backup-providers/${providerId}/test`
    );
    if (statusEl) {
      statusEl.textContent = result.success ? `✓ ${result.message}` : `✗ ${result.message}`;
      statusEl.className = `text-sm mt-2 ${result.success ? 'text-green-600' : 'text-red-600'}`;
    }
  } catch (error) {
    reportError(BACKUP_COMPONENT, 'testCloudProvider', error, { providerId });
    if (statusEl) {
      statusEl.textContent = t('backup.cloudProviderTestFailed');
      statusEl.className = 'text-sm text-red-600 mt-2';
    }
  }
}

async function deleteCloudProvider(providerId: string): Promise<void> {
  const statusEl = document.getElementById('cloud-status');
  try {
    await apiFetch(`/api/backup-providers/${providerId}`, { method: 'DELETE' });
    if (statusEl) {
      statusEl.textContent = t('backup.cloudProviderDeleted');
      statusEl.className = 'text-sm text-green-600 mt-2';
    }
    void loadCloudProviders();
  } catch (error) {
    reportError(BACKUP_COMPONENT, 'deleteCloudProvider', error, { providerId });
    if (statusEl) {
      statusEl.textContent = t('backup.cloudProviderDeleteFailed');
      statusEl.className = 'text-sm text-red-600 mt-2';
    }
  }
}

async function loadEncryptionConfig(): Promise<void> {
  try {
    const config = await apiGet<EncryptionConfig>('/api/backup-encryption');
    const enabledEl = document.getElementById('encryption-enabled') as HTMLInputElement | null;
    const infoEl = document.getElementById('encryption-info');
    const rotationEl = document.getElementById('encryption-key-rotation');
    const rotateBtnEl = document.getElementById('encryption-rotate-btn');

    if (enabledEl) enabledEl.checked = config.is_enabled;
    if (infoEl) {
      infoEl.textContent = `Algorithm: ${config.algorithm} | KDF: ${config.kdf} | Key version: ${config.key_version}${config.rotated_at ? ` | Rotated: ${new Date(config.rotated_at).toLocaleString()}` : ''}`;
    }
    rotationEl?.classList.toggle('hidden', !config.is_enabled);
    rotateBtnEl?.classList.toggle('hidden', !config.is_enabled);
    encryptionEnabled = config.is_enabled;
  } catch {
    // Encryption not configured
    encryptionEnabled = false;
  }

  const createPassphraseContainer = document.getElementById('backup-create-passphrase-container');
  if (createPassphraseContainer) {
    createPassphraseContainer.classList.toggle('hidden', !encryptionEnabled);
  }
}

async function saveEncryptionConfig(): Promise<void> {
  const enabledEl = document.getElementById('encryption-enabled') as HTMLInputElement | null;
  const passphraseEl = document.getElementById('encryption-passphrase') as HTMLInputElement | null;
  const statusEl = document.getElementById('encryption-status');

  const isEnabled = enabledEl?.checked ?? false;
  const body: Record<string, unknown> = { is_enabled: isEnabled };

  if (isEnabled) {
    const passphrase = passphraseEl?.value ?? '';
    if (!passphrase) {
      if (statusEl) {
        statusEl.textContent = t('backup.encryptionPassphraseRequiredToEnable');
        statusEl.className = 'text-sm text-red-600 mt-2';
      }
      return;
    }
    body.passphrase = passphrase;
  }

  try {
    await apiFetch<EncryptionConfig>('/api/backup-encryption', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (statusEl) {
      statusEl.textContent = isEnabled
        ? t('backup.encryptionEnabledStatus')
        : t('backup.encryptionDisabledStatus');
      statusEl.className = 'text-sm text-green-600 mt-2';
    }
    if (passphraseEl) passphraseEl.value = '';
    void loadEncryptionConfig();
  } catch (error) {
    reportError(BACKUP_COMPONENT, 'saveEncryptionConfig', error);
    if (statusEl) {
      statusEl.textContent = t('backup.encryptionSaveFailed');
      statusEl.className = 'text-sm text-red-600 mt-2';
    }
  }
}

async function rotateEncryptionKey(): Promise<void> {
  const oldPassphraseEl = document.getElementById(
    'encryption-old-passphrase'
  ) as HTMLInputElement | null;
  const newPassphraseEl = document.getElementById(
    'encryption-new-passphrase'
  ) as HTMLInputElement | null;
  const statusEl = document.getElementById('encryption-status');

  const oldPassphrase = oldPassphraseEl?.value ?? '';
  const newPassphrase = newPassphraseEl?.value ?? '';

  if (!oldPassphrase || !newPassphrase) {
    if (statusEl) {
      statusEl.textContent = t('backup.encryptionRotationPassphrasesRequired');
      statusEl.className = 'text-sm text-red-600 mt-2';
    }
    return;
  }

  try {
    await apiFetch<EncryptionConfig>('/api/backup-encryption', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        rotate_key: true,
        old_passphrase: oldPassphrase,
        new_passphrase: newPassphrase,
      }),
    });
    if (statusEl) {
      statusEl.textContent = t('backup.encryptionRotationSuccess');
      statusEl.className = 'text-sm text-green-600 mt-2';
    }
    if (oldPassphraseEl) oldPassphraseEl.value = '';
    if (newPassphraseEl) newPassphraseEl.value = '';
    void loadEncryptionConfig();
  } catch (error) {
    reportError(BACKUP_COMPONENT, 'rotateEncryptionKey', error);
    if (statusEl) {
      statusEl.textContent = t('backup.encryptionRotationFailed');
      statusEl.className = 'text-sm text-red-600 mt-2';
    }
  }
}

async function loadSchedule(): Promise<void> {
  try {
    const schedule = await apiGet<BackupSchedule>('/api/backup-schedule');
    populateScheduleForm(schedule);
  } catch {
    // No schedule configured yet — that's fine
  }
}

function populateScheduleForm(schedule: BackupSchedule): void {
  const enabledEl = document.getElementById('schedule-enabled') as HTMLInputElement | null;
  const frequencyEl = document.getElementById('schedule-frequency') as HTMLSelectElement | null;
  const hourEl = document.getElementById('schedule-hour') as HTMLInputElement | null;
  const minuteEl = document.getElementById('schedule-minute') as HTMLInputElement | null;
  const dayEl = document.getElementById('schedule-day') as HTMLInputElement | null;
  const dayLabel = document.getElementById('schedule-day-label');
  const lastRun = document.getElementById('schedule-last-run');
  const cloudProviderEl = document.getElementById(
    'schedule-cloud-provider'
  ) as HTMLSelectElement | null;
  const cleanupRetentionDays = document.getElementById(
    'cleanup-retention-days'
  ) as HTMLInputElement | null;

  if (enabledEl) enabledEl.checked = schedule.enabled;
  if (frequencyEl) frequencyEl.value = schedule.frequency;
  if (hourEl) hourEl.value = String(schedule.hour);
  if (minuteEl) minuteEl.value = String(schedule.minute);
  if (cleanupRetentionDays) cleanupRetentionDays.value = String(schedule.retention_days);
  if (cloudProviderEl) cloudProviderEl.value = schedule.cloud_provider_id ?? '';

  updateDayFieldVisibility(schedule.frequency);

  if (schedule.frequency === 'weekly' && dayEl) {
    dayEl.value = String(schedule.day_of_week ?? 0);
    if (dayLabel) dayLabel.textContent = t('backup.scheduleDayOfWeek') || 'Day of week (0=Mon)';
    if (dayEl) dayEl.max = '6';
  } else if (schedule.frequency === 'monthly' && dayEl) {
    dayEl.value = String(schedule.day_of_month ?? 1);
    if (dayLabel) dayLabel.textContent = t('backup.scheduleDayOfMonth') || 'Day of month';
    if (dayEl) {
      dayEl.min = '1';
      dayEl.max = '31';
    }
  }

  if (lastRun && schedule.last_run_at) {
    lastRun.classList.remove('hidden');
    const status = schedule.last_run_status === 'success' ? '✓' : '✗';
    lastRun.textContent = `Last run: ${new Date(schedule.last_run_at).toLocaleString()} (${status} ${schedule.last_run_status})`;
  }
}

function updateDayFieldVisibility(frequency: string): void {
  const dayContainer = document.getElementById('schedule-day-container');
  const dayLabel = document.getElementById('schedule-day-label');
  const dayEl = document.getElementById('schedule-day') as HTMLInputElement | null;

  if (!dayContainer || !dayEl) return;

  if (frequency === 'daily') {
    dayContainer.classList.add('hidden');
  } else {
    dayContainer.classList.remove('hidden');
    if (frequency === 'weekly') {
      if (dayLabel) dayLabel.textContent = t('backup.scheduleDayOfWeek') || 'Day of week (0=Mon)';
      dayEl.min = '0';
      dayEl.max = '6';
      dayEl.value = '0';
    } else if (frequency === 'monthly') {
      if (dayLabel) dayLabel.textContent = t('backup.scheduleDayOfMonth') || 'Day of month';
      dayEl.min = '1';
      dayEl.max = '31';
      dayEl.value = '1';
    }
  }
}

async function saveSchedule(): Promise<void> {
  const enabledEl = document.getElementById('schedule-enabled') as HTMLInputElement | null;
  const frequencyEl = document.getElementById('schedule-frequency') as HTMLSelectElement | null;
  const hourEl = document.getElementById('schedule-hour') as HTMLInputElement | null;
  const minuteEl = document.getElementById('schedule-minute') as HTMLInputElement | null;
  const dayEl = document.getElementById('schedule-day') as HTMLInputElement | null;
  const cloudProviderEl = document.getElementById(
    'schedule-cloud-provider'
  ) as HTMLSelectElement | null;
  const cleanupRetentionDays = document.getElementById(
    'cleanup-retention-days'
  ) as HTMLInputElement | null;
  const statusEl = document.getElementById('schedule-status');

  const frequency = frequencyEl?.value ?? 'daily';
  const body: Record<string, unknown> = {
    enabled: enabledEl?.checked ?? false,
    frequency,
    hour: Number(hourEl?.value ?? 2),
    minute: Number(minuteEl?.value ?? 0),
    retention_days: Number(cleanupRetentionDays?.value ?? 30),
    cloud_provider_id: cloudProviderEl?.value || null,
  };

  if (frequency === 'weekly') {
    body.day_of_week = Number(dayEl?.value ?? 0);
  } else if (frequency === 'monthly') {
    body.day_of_month = Number(dayEl?.value ?? 1);
  }

  try {
    const result = await apiFetch<BackupSchedule>('/api/backup-schedule', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (statusEl) {
      statusEl.textContent = t('backup.scheduleSaved');
      statusEl.className = 'text-sm text-green-600 mt-2';
    }
    populateScheduleForm(result);
  } catch (error) {
    reportError(BACKUP_COMPONENT, 'saveSchedule', error);
    if (statusEl) {
      statusEl.textContent = t('backup.scheduleSaveFailed');
      statusEl.className = 'text-sm text-red-600 mt-2';
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
    showDeleteAllModal?: () => void;
    hideDeleteAllModal?: () => void;
    confirmDeleteAll?: () => Promise<void>;
    saveSchedule?: () => Promise<void>;
    saveEncryptionConfig?: () => Promise<void>;
    rotateEncryptionKey?: () => Promise<void>;
    addCloudProvider?: () => Promise<void>;
    testCloudProvider?: (id: string) => Promise<void>;
    deleteCloudProvider?: (id: string) => Promise<void>;
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
  backupWindow.showDeleteAllModal = showDeleteAllModal;
  backupWindow.hideDeleteAllModal = hideDeleteAllModal;
  backupWindow.confirmDeleteAll = confirmDeleteAll;
  backupWindow.saveSchedule = saveSchedule;
  backupWindow.saveEncryptionConfig = saveEncryptionConfig;
  backupWindow.rotateEncryptionKey = rotateEncryptionKey;
  backupWindow.addCloudProvider = addCloudProvider;
  backupWindow.testCloudProvider = testCloudProvider;
  backupWindow.deleteCloudProvider = deleteCloudProvider;
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
