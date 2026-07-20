/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { reportError } from '@/telemetry';
import { t } from '@/utils/i18n';
import { apiFetch, apiGet, apiPost } from '@/utils/api';
import { BACKUP_COMPONENT, type CloudProvider } from './types';
import { escapeHtml } from './ui';
import { cloudProviderNames, currentBackups, renderBackupList } from './list';

export async function loadCloudProviders(): Promise<void> {
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

export function populateCloudProviderSelect(selectId: string, providers: CloudProvider[]): void {
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

export async function addCloudProvider(): Promise<void> {
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

export async function testCloudProvider(providerId: string): Promise<void> {
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

export async function deleteCloudProvider(providerId: string): Promise<void> {
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
