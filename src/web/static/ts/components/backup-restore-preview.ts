/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { apiFetch, apiPost } from '@/utils/api';
import { reportError } from '@/telemetry';

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

const COMPONENT = 'backupRestorePreview';

interface RestoreDiff {
  backup_id: string;
  summary: { added: number; updated: number; deleted: number };
  changes: {
    added: Array<{ id: string; title: string; content: string }>;
    updated: Array<{
      id: string;
      title: string;
      before: { title: string; content: string };
      after: { title: string; content: string };
    }>;
    deleted: Array<{ id: string; title: string }>;
  };
}

export async function showRestorePreview(backupId: string, passphrase?: string): Promise<void> {
  const modal = document.getElementById('restore-preview-modal') as HTMLElement | null;
  const content = document.getElementById('restore-preview-content');
  const statusEl = document.getElementById('restore-preview-status');

  if (!modal || !content) return;

  if (statusEl) {
    statusEl.textContent = 'Loading preview...';
    statusEl.className = 'text-sm text-blue-600';
  }

  try {
    const body: Record<string, unknown> = {};
    if (passphrase) body.passphrase = passphrase;

    const diff = await apiFetch<RestoreDiff>(`/api/backups/${backupId}/restore-preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    renderDiff(diff, backupId);
    modal.classList.remove('hidden');
  } catch (error) {
    reportError(COMPONENT, 'showRestorePreview', error, { backupId });
    if (statusEl) {
      statusEl.textContent = 'Failed to load preview';
      statusEl.className = 'text-sm text-red-600';
    }
  }
}

function renderDiff(diff: RestoreDiff, backupId: string): void {
  const content = document.getElementById('restore-preview-content');
  if (!content) return;

  const { summary, changes } = diff;

  let html = `<div class="mb-4 text-sm font-medium text-gray-700 dark:text-gray-300">
    Summary: <span class="text-green-600">${summary.added} added</span>,
    <span class="text-yellow-600">${summary.updated} updated</span>,
    <span class="text-red-600">${summary.deleted} deleted</span>
  </div>`;

  html += '<div class="space-y-2 max-h-96 overflow-y-auto">';

  for (const item of changes.added) {
    html += `<div class="flex items-start gap-2 p-2 bg-green-50 rounded border border-green-200">
      <input type="checkbox" class="restore-select mt-1" data-id="${escapeHtml(item.id)}" checked />
      <div><span class="text-green-700 font-medium text-xs">ADDED</span>
      <div class="text-sm text-gray-900 dark:text-gray-100">${escapeHtml(item.title)}</div></div>
    </div>`;
  }

  for (const item of changes.updated) {
    html += `<div class="flex items-start gap-2 p-2 bg-yellow-50 rounded border border-yellow-200">
      <input type="checkbox" class="restore-select mt-1" data-id="${escapeHtml(item.id)}" checked />
      <div><span class="text-yellow-700 font-medium text-xs">UPDATED</span>
      <div class="text-sm text-gray-900 dark:text-gray-100">${escapeHtml(item.title)}</div>
      <div class="text-xs text-gray-500 dark:text-gray-400">"${escapeHtml(item.before.title)}" → "${escapeHtml(item.after.title)}"</div></div>
    </div>`;
  }

  for (const item of changes.deleted) {
    html += `<div class="flex items-start gap-2 p-2 bg-red-50 rounded border border-red-200">
      <input type="checkbox" class="restore-select mt-1" data-id="${escapeHtml(item.id)}" checked />
      <div><span class="text-red-700 font-medium text-xs">DELETED</span>
      <div class="text-sm text-gray-900 dark:text-gray-100">${escapeHtml(item.title)}</div></div>
    </div>`;
  }

  html += '</div>';
  content.innerHTML = html;

  const confirmBtn = document.getElementById('confirm-selective-restore-btn');
  if (confirmBtn) {
    confirmBtn.onclick = () => void executeSelectiveRestore(backupId);
  }
}

async function executeSelectiveRestore(backupId: string): Promise<void> {
  const checkboxes = document.querySelectorAll<HTMLInputElement>('.restore-select:checked');
  const promptIds = Array.from(checkboxes)
    .map((cb) => cb.dataset.id)
    .filter(Boolean) as string[];

  if (promptIds.length === 0) return;

  const statusEl = document.getElementById('restore-preview-status');
  if (statusEl) {
    statusEl.textContent = 'Restoring selected prompts...';
    statusEl.className = 'text-sm text-blue-600';
  }

  try {
    const result = await apiPost<{ restored: boolean; pre_restore_backup_id: string }>(
      `/api/backups/${backupId}/restore`,
      { prompt_ids: promptIds }
    );
    if (result.restored) {
      if (statusEl) {
        statusEl.textContent = `Restored ${promptIds.length} prompts. Pre-restore backup: ${result.pre_restore_backup_id}`;
        statusEl.className = 'text-sm text-green-600';
      }
    }
  } catch (error) {
    reportError(COMPONENT, 'executeSelectiveRestore', error, { backupId });
    if (statusEl) {
      statusEl.textContent = 'Selective restore failed';
      statusEl.className = 'text-sm text-red-600';
    }
  }
}

export function hideRestorePreview(): void {
  const modal = document.getElementById('restore-preview-modal') as HTMLElement | null;
  if (modal) modal.classList.add('hidden');
}

(
  window as Window & {
    showRestorePreview?: typeof showRestorePreview;
    hideRestorePreview?: typeof hideRestorePreview;
  }
).showRestorePreview = showRestorePreview;
(
  window as Window & {
    showRestorePreview?: typeof showRestorePreview;
    hideRestorePreview?: typeof hideRestorePreview;
  }
).hideRestorePreview = hideRestorePreview;
