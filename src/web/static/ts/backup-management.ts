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

const BACKUP_COMPONENT = 'backupManagement';

let currentBackups: BackupItem[] = [];
let selectedBackupId: string | null = null;

function reportBackupIssue(
  action: string,
  error: unknown,
  metadata: Record<string, unknown> = {},
  severity: 'error' | 'warning' = 'error'
): void {
  const logger = window.FrontendLogger;
  if (logger && typeof logger.reportError === 'function') {
    logger.reportError(BACKUP_COMPONENT, action, error, metadata, severity);
  } else {
    reportError(BACKUP_COMPONENT, action, error, metadata, severity);
  }

  const prefix = `[PromptVault][backup] ${action}`;
  if (severity === 'warning') {
    console.warn(prefix, error, metadata);
  } else {
    console.error(prefix, error, metadata);
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
    reportBackupIssue('changeLanguage', err, { language: selectedLanguage });
  });
}

async function loadBackups(): Promise<void> {
  try {
    const response = await fetch('/api/backups');
    const data = await response.json();

    currentBackups = data.backups || [];
    renderBackupList(currentBackups);
  } catch (error) {
    reportBackupIssue('loadBackups', error as Error);
    showStatus('backup-status', 'Error loading backups', 'error');
  }
}

async function loadBackupStats(): Promise<void> {
  try {
    const response = await fetch('/api/backups/stats');
    const stats = (await response.json()) as BackupStats;
    updateStatsDisplay(stats);
  } catch (error) {
    reportBackupIssue('loadBackupStats', error as Error);
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
            <div class="flex items-start justify-between mb-3">
                <h4 class="font-semibold text-gray-900">${backup.backup_id}${isCompressed}</h4>
                <div class="flex space-x-2">
                    <button class="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-medium transition" onclick="showRestoreModal('${backup.backup_id}')">Restore</button>
                    <button class="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-xs font-medium transition" onclick="showDeleteModal('${backup.backup_id}')">Delete</button>
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

  showProgress('backup-progress', 'Creating backup...');

  try {
    const formData = new FormData();
    formData.append('name', backupName);

    const response = await fetch('/api/backups', {
      method: 'POST',
      body: formData,
    });

    const result = await response.json();

    if (result.success) {
      showStatus('backup-status', `Backup created successfully: ${result.backup_id}`, 'success');
      if (backupNameInput) backupNameInput.value = '';
      void loadBackups();
      void loadBackupStats();
    } else {
      showStatus('backup-status', 'Failed to create backup', 'error');
    }
  } catch (error) {
    reportBackupIssue('createBackup', error as Error, { backupName });
    showStatus('backup-status', 'Error creating backup', 'error');
  } finally {
    hideProgress('backup-progress');
  }
}

function showRestoreModal(backupId: string): void {
  selectedBackupId = backupId;
  const backup = currentBackups.find((item) => item.backup_id === backupId);
  if (!backup) return;

  const infoDiv = document.getElementById('restore-backup-info');
  if (infoDiv) {
    infoDiv.innerHTML = `
        <strong>Backup:</strong> ${backup.backup_id}<br>
        <strong>Created:</strong> ${new Date(backup.timestamp).toLocaleString()}<br>
        <strong>Size:</strong> ${formatBytes(backup.size_bytes)}<br>
        <strong>Prompts:</strong> ${backup.prompt_count}
    `;
  }

  showElement(document.getElementById('restore-modal') as HTMLElement | null);
  setRestoreInProgress(false);
}

function hideRestoreModal(): void {
  hideElement(document.getElementById('restore-modal') as HTMLElement | null);
  selectedBackupId = null;
}

async function confirmRestore(): Promise<void> {
  if (!selectedBackupId) return;

  const backupIdToRestore = selectedBackupId;
  setRestoreInProgress(true, 'backup.restoreInProgress');
  showProgress('backup-progress', 'Restoring backup...');

  try {
    const response = await fetch(`/api/backups/${backupIdToRestore}/restore`, {
      method: 'POST',
    });

    const result = await response.json();

    if (result.success) {
      showStatus('backup-status', 'Backup restored successfully', 'success');
      setRestoreInProgress(true, 'backup.restoreRedirect');
      setTimeout(() => {
        window.location.href = '/';
      }, 2000);
    } else {
      showStatus('backup-status', 'Failed to restore backup', 'error');
      setRestoreInProgress(false);
    }
  } catch (error) {
    reportBackupIssue('restoreBackup', error as Error, { backupId: backupIdToRestore });
    showStatus('backup-status', 'Error restoring backup', 'error');
    setRestoreInProgress(false);
  } finally {
    hideProgress('backup-progress');
  }
}

function showDeleteModal(backupId: string): void {
  selectedBackupId = backupId;
  const backup = currentBackups.find((item) => item.backup_id === backupId);
  if (!backup) return;

  const infoDiv = document.getElementById('delete-backup-info');
  if (infoDiv) {
    infoDiv.innerHTML = `
        <strong>Backup:</strong> ${backup.backup_id}<br>
        <strong>Created:</strong> ${new Date(backup.timestamp).toLocaleString()}<br>
        <strong>Size:</strong> ${formatBytes(backup.size_bytes)}
    `;
  }

  showElement(document.getElementById('delete-modal') as HTMLElement | null);
}

function hideDeleteModal(): void {
  hideElement(document.getElementById('delete-modal') as HTMLElement | null);
  selectedBackupId = null;
}

async function confirmDelete(): Promise<void> {
  if (!selectedBackupId) return;

  const backupIdToDelete = selectedBackupId;
  hideDeleteModal();
  showProgress('backup-progress', 'Deleting backup...');

  try {
    const response = await fetch(`/api/backups/${backupIdToDelete}`, {
      method: 'DELETE',
    });

    const result = await response.json();

    if (result.success) {
      showStatus('backup-status', 'Backup deleted successfully', 'success');
      void loadBackups();
      void loadBackupStats();
    } else {
      showStatus('backup-status', 'Failed to delete backup', 'error');
    }
  } catch (error) {
    reportBackupIssue('deleteBackup', error as Error, { backupId: backupIdToDelete });
    showStatus('backup-status', 'Error deleting backup', 'error');
  } finally {
    hideProgress('backup-progress');
  }
}

async function cleanupBackups(): Promise<void> {
  const retentionInput = document.getElementById('retention-days') as HTMLInputElement | null;
  const retentionDays = retentionInput?.value ?? '';

  showProgress('maintenance-progress', 'Cleaning up old backups...');

  try {
    const formData = new FormData();
    formData.append('retention_days', retentionDays);

    const response = await fetch('/api/backups/cleanup', {
      method: 'POST',
      body: formData,
    });

    const result = await response.json();

    if (result.success) {
      showStatus(
        'maintenance-status',
        `Cleanup completed: ${result.removed_count} backups removed`,
        'success'
      );
      void loadBackups();
      void loadBackupStats();
    } else {
      showStatus('maintenance-status', 'Cleanup failed', 'error');
    }
  } catch (error) {
    reportBackupIssue('cleanupBackups', error as Error, { retentionDays });
    showStatus('maintenance-status', 'Error cleaning up backups', 'error');
  } finally {
    hideProgress('maintenance-progress');
  }
}

async function compressBackups(): Promise<void> {
  const compressInput = document.getElementById('compress-days') as HTMLInputElement | null;
  const compressDays = compressInput?.value ?? '';

  showProgress('maintenance-progress', 'Compressing old backups...');

  try {
    const formData = new FormData();
    formData.append('days_threshold', compressDays);

    const response = await fetch('/api/backups/compress', {
      method: 'POST',
      body: formData,
    });

    const result = await response.json();

    if (result.success) {
      showStatus(
        'maintenance-status',
        `Compression completed: ${result.compressed_count} backups compressed`,
        'success'
      );
      void loadBackups();
      void loadBackupStats();
    } else {
      showStatus('maintenance-status', 'Compression failed', 'error');
    }
  } catch (error) {
    reportBackupIssue('compressBackups', error as Error, { daysThreshold: compressDays });
    showStatus('maintenance-status', 'Error compressing backups', 'error');
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

  container?.classList.remove('is-hidden');
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
  container?.classList.add('is-hidden');
}

function showStatus(elementId: string, message: string, type: 'info' | 'success' | 'error'): void {
  const element = document.getElementById(elementId);
  if (!element) return;

  element.textContent = message;
  const colorClass = type === 'success' ? 'text-green-600' : type === 'error' ? 'text-red-600' : 'text-blue-600';
  element.className = `text-sm ${colorClass} mt-2`;

  const container = element.parentElement;
  if (container && container.id.includes('progress')) {
    container.classList.remove('is-hidden');
  }

  if (type === 'success') {
    setTimeout(() => {
      if (container && container.id.includes('progress')) {
        container.classList.add('is-hidden');
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
      status.className = 'status-message status-info';
    } else {
      hideElement(status);
      status.textContent = '';
    }
  }

  buttons?.forEach((button) => {
    if (button instanceof HTMLButtonElement) {
      button.disabled = isRestoring;
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
    const response = await fetch('/api/auth/me', {
      credentials: 'include',
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
    reportBackupIssue('checkAdminAccess', error as Error);
    window.location.href = '/auth/login';
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
    reportBackupIssue('initialize', error as Error);
  }
});
