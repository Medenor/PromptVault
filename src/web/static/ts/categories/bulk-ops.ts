/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { t, tUnsafe } from '@/utils/i18n';
import { showNotification } from '@/utils/notifications';
import { confirmAsync } from '@/utils/dialogs';
import {
  bulkDeleteCategoriesRequest,
  exportCategoriesRequest,
  findReplaceCategoriesRequest,
  importCategoriesRequest,
  mergeCategoriesRequest,
  undoCategoriesRequest,
} from './api';
import type { CategoryItem } from './types';

export function parseIdList(value: string): number[] {
  return value
    .split(',')
    .map((id) => Number(id.trim()))
    .filter((id) => Number.isFinite(id) && id > 0);
}

export async function mergeCategories(
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
    await mergeCategoriesRequest(targetId, sourceIds);
    showNotification(tUnsafe('management.mergeSuccess'), 'success');
  } catch (error) {
    handleError(error, 'Failed to merge categories');
    throw error;
  }
}

export async function findReplaceCategories(
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
    await findReplaceCategoriesRequest(findValue, replaceValue);
    showNotification(tUnsafe('management.replaceSuccess'), 'success');
  } catch (error) {
    handleError(error, 'Failed to replace category');
    throw error;
  }
}

export async function bulkDeleteCategories(
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
    await bulkDeleteCategoriesRequest(ids, force);
    showNotification(tUnsafe('management.bulkDeleteSuccess'), 'success');
  } catch (error) {
    handleError(error, 'Failed to delete categories');
    throw error;
  }
}

export async function exportCategories(
  handleError: (error: unknown, fallback: string) => void
): Promise<void> {
  try {
    const data = await exportCategoriesRequest();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'categories.json';
    anchor.click();
    URL.revokeObjectURL(url);
    showNotification(tUnsafe('management.exportSuccess'), 'success');
  } catch (error) {
    handleError(error, 'Failed to export categories');
  }
}

export async function importCategories(
  file: File,
  handleError: (error: unknown, fallback: string) => void
): Promise<void> {
  try {
    const text = await file.text();
    const parsed = JSON.parse(text) as { items?: CategoryItem[] };
    const items = (parsed.items ?? []).map((item) => ({
      name: item.name,
      description: item.description ?? undefined,
      color: item.color ?? undefined,
      sort_order: item.sort_order ?? undefined,
    }));
    await importCategoriesRequest(items);
    showNotification(tUnsafe('management.importSuccess'), 'success');
  } catch (error) {
    handleError(error, 'Failed to import categories');
    throw error;
  }
}

export async function undoLastOperation(
  handleError: (error: unknown, fallback: string) => void
): Promise<void> {
  try {
    await undoCategoriesRequest();
    showNotification(tUnsafe('management.undoSuccess'), 'success');
  } catch (error) {
    handleError(error, 'No operation to undo.');
    throw error;
  }
}
