/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { apiGet } from '@/utils/api';
import { reportError } from '@/telemetry';
import { t } from '@/utils/i18n';

const COMPONENT = 'backupMonitoringDashboard';

interface MonitoringStats {
  total_backups: number;
  success_rate_30d: number;
  total_size_bytes: number;
  storage_quota_bytes: number;
  quota_warning: boolean;
  last_backup_at: string | null;
  last_backup_status: string | null;
  history: Array<{
    date: string;
    count: number;
    success: number;
    failure: number;
    total_size_bytes: number;
  }>;
}

interface AuditEntry {
  id: string;
  occurred_at: string;
  operation: string;
  outcome: string;
  backup_id: string | null;
  performed_by: string | null;
  detail: Record<string, unknown> | null;
}

export async function loadMonitoringDashboard(): Promise<void> {
  try {
    const stats = await apiGet<MonitoringStats>('/api/backup-monitoring');
    renderDashboard(stats);
  } catch (error) {
    reportError(COMPONENT, 'loadMonitoringDashboard', error);
  }
}

function renderDashboard(stats: MonitoringStats): void {
  const totalEl = document.getElementById('monitoring-total-backups');
  const rateEl = document.getElementById('monitoring-success-rate');
  const sizeEl = document.getElementById('monitoring-total-size');
  const lastEl = document.getElementById('monitoring-last-backup');
  const quotaEl = document.getElementById('monitoring-quota-warning');
  const historyEl = document.getElementById('monitoring-history');

  if (totalEl) totalEl.textContent = String(stats.total_backups);
  if (rateEl) rateEl.textContent = `${Math.round(stats.success_rate_30d * 100)}%`;
  if (sizeEl) sizeEl.textContent = formatBytes(stats.total_size_bytes);
  if (lastEl) {
    lastEl.textContent = stats.last_backup_at
      ? `${new Date(stats.last_backup_at).toLocaleString()} (${stats.last_backup_status})`
      : t('backup.neverValue');
  }
  if (quotaEl) {
    if (stats.quota_warning) {
      quotaEl.textContent = t('backup.quotaWarningMessage');
      quotaEl.className = 'text-sm text-red-600 font-medium';
    } else {
      quotaEl.textContent = '';
    }
  }

  if (historyEl && stats.history.length > 0) {
    historyEl.innerHTML = `
      <table class="w-full text-sm">
        <thead><tr class="border-b"><th class="text-left py-1">${t('backup.columnDate')}</th><th class="text-right py-1">${t('backup.columnCount')}</th><th class="text-right py-1">${t('backup.columnSuccess')}</th><th class="text-right py-1">${t('backup.columnSize')}</th></tr></thead>
        <tbody>${stats.history.map((h) => `<tr class="border-b border-gray-100"><td class="py-1">${h.date}</td><td class="text-right py-1">${h.count}</td><td class="text-right py-1">${h.success}</td><td class="text-right py-1">${formatBytes(h.total_size_bytes)}</td></tr>`).join('')}</tbody>
      </table>`;
  } else if (historyEl) {
    historyEl.innerHTML =
      `<div class="text-gray-500 text-sm">${t('backup.noHistoryData')}</div>`;
  }
}

export async function loadAuditLog(): Promise<void> {
  try {
    const data = await apiGet<{ entries: AuditEntry[]; total: number }>(
      '/api/backup-audit-log?limit=20'
    );
    renderAuditLog(data.entries);
  } catch (error) {
    reportError(COMPONENT, 'loadAuditLog', error);
  }
}

function renderAuditLog(entries: AuditEntry[]): void {
  const el = document.getElementById('audit-log-table');
  if (!el) return;

  if (entries.length === 0) {
    el.innerHTML = `<div class="text-gray-500 text-sm">${t('backup.noAuditEntries')}</div>`;
    return;
  }

  el.innerHTML = `
    <table class="w-full text-sm">
      <thead><tr class="border-b"><th class="text-left py-1">${t('backup.columnTime')}</th><th class="text-left py-1">${t('backup.columnOperation')}</th><th class="text-left py-1">${t('backup.columnOutcome')}</th><th class="text-left py-1">${t('backup.columnPerformedBy')}</th></tr></thead>
      <tbody>${entries.map((e) => `<tr class="border-b border-gray-100"><td class="py-1">${new Date(e.occurred_at).toLocaleString()}</td><td class="py-1">${e.operation}</td><td class="py-1"><span class="${e.outcome === 'success' ? 'text-green-600' : 'text-red-600'}">${e.outcome}</span></td><td class="py-1">${e.performed_by || '-'}</td></tr>`).join('')}</tbody>
    </table>`;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

(
  window as Window & {
    loadMonitoringDashboard?: typeof loadMonitoringDashboard;
    loadAuditLog?: typeof loadAuditLog;
  }
).loadMonitoringDashboard = loadMonitoringDashboard;
(
  window as Window & {
    loadMonitoringDashboard?: typeof loadMonitoringDashboard;
    loadAuditLog?: typeof loadAuditLog;
  }
).loadAuditLog = loadAuditLog;
