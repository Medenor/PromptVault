/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { reportError } from '@/telemetry';
import { t } from '@/utils/i18n';
import { apiFetch, apiGet } from '@/utils/api';
import { BACKUP_COMPONENT, type BackupSchedule } from './types';

export async function loadSchedule(): Promise<void> {
  try {
    const schedule = await apiGet<BackupSchedule>('/api/backup-schedule');
    populateScheduleForm(schedule);
  } catch {
    // No schedule configured yet — that's fine
  }
}

export function populateScheduleForm(schedule: BackupSchedule): void {
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

export function updateDayFieldVisibility(frequency: string): void {
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

export async function saveSchedule(): Promise<void> {
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
