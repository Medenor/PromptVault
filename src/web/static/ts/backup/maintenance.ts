/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { reportError } from '@/telemetry';
import { t } from '@/utils/i18n';
import { apiPostForm } from '@/utils/api';
import {
  BACKUP_COMPONENT,
  type CleanupResponse,
  type CompressResponse,
  type FormValidationError,
} from './types';
import {
  addFieldError,
  hideProgress,
  refreshMonitoring,
  resetErrorSummary,
  resetFieldError,
  renderErrorSummary,
  showProgress,
  showStatus,
} from './ui';
import { loadBackups, loadBackupStats } from './list';

export async function cleanupBackups(): Promise<void> {
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
      refreshMonitoring();
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

export async function compressBackups(): Promise<void> {
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
      refreshMonitoring();
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
