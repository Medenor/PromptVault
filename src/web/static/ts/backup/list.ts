/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { reportError } from '@/telemetry';
import { t } from '@/utils/i18n';
import { hideElement, showElement } from '@/utils/dom';
import { apiFetch, apiGet, apiPost, apiPostForm, handleApiError } from '@/utils/api';
import type { TranslationKey } from '@/types/i18n';
import {
  BACKUP_COMPONENT,
  type BackupItem,
  type BackupResponse,
  type BackupStats,
  type DeleteResponse,
  type FormValidationError,
  type RestoreResponse,
} from './types';
import {
  addFieldError,
  escapeHtml,
  formatBytes,
  hideProgress,
  refreshMonitoring,
  resetErrorSummary,
  resetFieldError,
  renderErrorSummary,
  setLiveFieldError,
  showProgress,
  showStatus,
} from './ui';

export let currentBackups: BackupItem[] = [];
export const cloudProviderNames = new Map<string, string>();
let selectedBackupId: string | null = null;
let encryptionEnabledFlag = false;

// Focus management for modals
let restoreConfirmationModalTrigger: HTMLElement | null = null;
let deleteConfirmationModalTrigger: HTMLElement | null = null;

export function setEncryptionEnabled(enabled: boolean): void {
  encryptionEnabledFlag = enabled;
}

export async function loadBackups(): Promise<void> {
  try {
    const data = await apiGet<{ backups: BackupItem[] }>('/api/backups');

    currentBackups = data.backups || [];
    renderBackupList(currentBackups);
  } catch (error) {
    reportError(BACKUP_COMPONENT, 'loadBackups', error);
    showStatus('backup-status', t('backup.errorLoading'), 'error');
  }
}

export async function loadBackupStats(): Promise<void> {
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

export function renderBackupList(backups: BackupItem[]): void {
  const container = document.getElementById('backup-list');
  if (!container) return;

  if (backups.length === 0) {
    container.innerHTML = `<div class="text-gray-500 text-sm dark:text-gray-400">${escapeHtml(t('backup.noBackupsFound'))}</div>`;
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

export async function createBackup(): Promise<void> {
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

  if (encryptionEnabledFlag && !passphrase) {
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
    if (encryptionEnabledFlag) {
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
      void refreshMonitoring();
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

export function showRestoreModal(backupId: string): void {
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

export function hideRestoreModal(): void {
  hideElement(document.getElementById('restore-modal') as HTMLElement | null);
  selectedBackupId = null;
  // Return focus to trigger element
  if (restoreConfirmationModalTrigger) {
    restoreConfirmationModalTrigger.focus();
  }
}

export async function confirmRestore(): Promise<void> {
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
    const message = handleApiError(error, t('backup.restoreError'));
    setRestoreInProgress(false);
    showStatus('restore-status', message, 'error');
    showElement(document.getElementById('restore-status'));
  } finally {
    hideProgress('backup-progress');
  }
}

export function showDeleteModal(backupId: string): void {
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

export function hideDeleteModal(): void {
  hideElement(document.getElementById('delete-modal') as HTMLElement | null);
  selectedBackupId = null;
  // Return focus to trigger element
  if (deleteConfirmationModalTrigger) {
    deleteConfirmationModalTrigger.focus();
  }
}

export async function confirmDelete(): Promise<void> {
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
      void refreshMonitoring();
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

export function showDeleteAllModal(): void {
  const modal = document.getElementById('delete-all-modal') as HTMLElement | null;
  showElement(modal);
  const firstFocusable = modal?.querySelector('h2, button') as HTMLElement | null;
  firstFocusable?.focus();
}

export function hideDeleteAllModal(): void {
  hideElement(document.getElementById('delete-all-modal') as HTMLElement | null);
}

export async function confirmDeleteAll(): Promise<void> {
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
    void refreshMonitoring();
  } catch (error) {
    reportError(BACKUP_COMPONENT, 'deleteAllBackups', error, {});
    showStatus('backup-status', t('backup.deleteError'), 'error');
  } finally {
    hideProgress('backup-progress');
  }
}

export function clearBackupForm(): void {
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

