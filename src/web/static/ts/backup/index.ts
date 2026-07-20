/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import '../../css/tailwind-globals.css';
import { reportError } from '@/telemetry';
import '@/form-validation';
import { initI18n, t, updateStaticTranslations, changeLanguage } from '@/utils/i18n';
import { initSecondaryNav } from '@/utils/secondary-nav';
import { loadMonitoringDashboard, loadAuditLog } from '../components/backup-monitoring-dashboard';
import { BACKUP_COMPONENT } from './types';
import { clearLiveFieldError, setLiveFieldError, setRefreshMonitoring } from './ui';
import {
  clearBackupForm,
  confirmDelete,
  confirmDeleteAll,
  confirmRestore,
  createBackup,
  hideDeleteAllModal,
  hideDeleteModal,
  hideRestoreModal,
  loadBackups,
  loadBackupStats,
  showDeleteAllModal,
  showDeleteModal,
  showRestoreModal,
} from './list';
import { cleanupBackups, compressBackups } from './maintenance';
import { addCloudProvider, deleteCloudProvider, loadCloudProviders, testCloudProvider } from './cloud';
import { loadEncryptionConfig, rotateEncryptionKey, saveEncryptionConfig } from './encryption';
import { loadSchedule, saveSchedule, updateDayFieldVisibility } from './schedule';

const liveValidationState = new Map<string, boolean>();

function refreshMonitoring(): void {
  void loadMonitoringDashboard();
  void loadAuditLog();
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
          t('validation.compressionDaysTooLow') || 'Compression threshold is too low.'
        );
        return;
      }
      if (value > 365) {
        setLiveFieldError(
          'compress-days',
          'compress-days-error',
          t('validation.compressionDaysTooHigh') || 'Compression threshold is too high.'
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

function refreshBackups(): void {
  void loadBackups();
  void loadBackupStats();
  void loadMonitoringDashboard();
  void loadAuditLog();
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

setRefreshMonitoring(refreshMonitoring);

initI18n(() => {
  try {
    updateStaticTranslations();
    exposeGlobalHandlers();
    initializeBackupManagement();
  } catch (error) {
    reportError(BACKUP_COMPONENT, 'initialize', error);
  }
});
