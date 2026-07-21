/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { t, tUnsafe } from '@/utils/i18n';
import { showNotification } from '@/utils/notifications';
import { confirmAsync } from '@/utils/dialogs';
import {
  bulkDeleteTagsRequest,
  exportTagsRequest,
  fetchTagAnalytics,
  findReplaceTagsRequest,
  importTagsRequest,
  mergeTagsRequest,
  undoTagsRequest,
} from './api';
import type { TagItem } from './types';

export function parseIdList(value: string): number[] {
  return value
    .split(',')
    .map((id) => Number(id.trim()))
    .filter((id) => Number.isFinite(id) && id > 0);
}

export async function mergeTags(
  targetId: number,
  sourceIds: number[],
  handleError: (error: unknown, fallback: string) => void
): Promise<void> {
  const confirmed = await confirmAsync({
    title: t('actions.confirm') || 'Confirm',
    message: tUnsafe('management.mergeConfirm'),
    confirmLabel: t('actions.merge') || 'Merge',
    cancelLabel: t('actions.cancel') || 'Cancel',
  });
  if (!confirmed) {
    return;
  }
  try {
    await mergeTagsRequest(targetId, sourceIds);
    showNotification(tUnsafe('management.mergeSuccess'), 'success');
  } catch (error) {
    handleError(error, 'Failed to merge tags');
    throw error;
  }
}

export async function findReplaceTags(
  findValue: string,
  replaceValue: string,
  handleError: (error: unknown, fallback: string) => void
): Promise<void> {
  const confirmed = await confirmAsync({
    title: t('actions.confirm') || 'Confirm',
    message: tUnsafe('management.replaceConfirm'),
    confirmLabel: t('actions.replace') || 'Replace',
    cancelLabel: t('actions.cancel') || 'Cancel',
  });
  if (!confirmed) {
    return;
  }
  try {
    await findReplaceTagsRequest(findValue, replaceValue);
    showNotification(tUnsafe('management.replaceSuccess'), 'success');
  } catch (error) {
    handleError(error, 'Failed to replace tag');
    throw error;
  }
}

export async function bulkDeleteTags(
  ids: number[],
  force: boolean,
  handleError: (error: unknown, fallback: string) => void
): Promise<void> {
  const confirmed = await confirmAsync({
    title: t('actions.confirm') || 'Confirm',
    message: tUnsafe('management.bulkDeleteConfirm'),
    confirmLabel: t('actions.bulkDelete') || 'Delete Selected',
    cancelLabel: t('actions.cancel') || 'Cancel',
  });
  if (!confirmed) {
    return;
  }
  try {
    await bulkDeleteTagsRequest(ids, force);
    showNotification(tUnsafe('management.bulkDeleteSuccess'), 'success');
  } catch (error) {
    handleError(error, 'Failed to delete tags');
    throw error;
  }
}

export async function exportTags(handleError: (error: unknown, fallback: string) => void): Promise<void> {
  try {
    const data = await exportTagsRequest();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'tags.json';
    anchor.click();
    URL.revokeObjectURL(url);
    showNotification(tUnsafe('management.exportSuccess'), 'success');
  } catch (error) {
    handleError(error, 'Failed to export tags');
  }
}

export async function importTags(
  file: File,
  handleError: (error: unknown, fallback: string) => void
): Promise<void> {
  try {
    const text = await file.text();
    const parsed = JSON.parse(text) as { items?: TagItem[] };
    const items = (parsed.items ?? []).map((item) => ({
      name: item.name,
      description: item.description ?? undefined,
      color: item.color ?? undefined,
      parent_tag_id: item.parent_tag_id ?? undefined,
    }));
    await importTagsRequest(items);
    showNotification(tUnsafe('management.importSuccess'), 'success');
  } catch (error) {
    handleError(error, 'Failed to import tags');
    throw error;
  }
}

export async function undoLastOperation(
  handleError: (error: unknown, fallback: string) => void
): Promise<void> {
  try {
    await undoTagsRequest();
    showNotification(tUnsafe('management.undoSuccess'), 'success');
  } catch (error) {
    handleError(error, 'No operation to undo.');
    throw error;
  }
}

export interface AnalyticsElements {
  analyticsTotal: HTMLElement | null;
  analyticsUsed: HTMLElement | null;
  analyticsUnused: HTMLElement | null;
  analyticsTop: HTMLElement | null;
  analyticsCooccurrence: HTMLElement | null;
}

export async function loadAnalytics(
  elements: AnalyticsElements,
  handleError: (error: unknown, fallback: string) => void
): Promise<void> {
  try {
    const data = await fetchTagAnalytics();
    if (elements.analyticsTotal) elements.analyticsTotal.textContent = String(data.total ?? 0);
    if (elements.analyticsUsed) elements.analyticsUsed.textContent = String(data.used ?? 0);
    if (elements.analyticsUnused) elements.analyticsUnused.textContent = String(data.unused ?? 0);
    if (elements.analyticsTop) {
      elements.analyticsTop.innerHTML = '';
      data.top.forEach((item) => {
        const li = document.createElement('li');
        li.textContent = `${item.name} (${item.count})`;
        elements.analyticsTop?.appendChild(li);
      });
    }
    if (elements.analyticsCooccurrence) {
      elements.analyticsCooccurrence.innerHTML = '';
      data.co_occurrence.forEach((item) => {
        const li = document.createElement('li');
        li.textContent = `${item.tag_a} + ${item.tag_b} (${item.count})`;
        elements.analyticsCooccurrence?.appendChild(li);
      });
    }
  } catch (error) {
    handleError(error, 'Failed to load analytics');
  }
}
