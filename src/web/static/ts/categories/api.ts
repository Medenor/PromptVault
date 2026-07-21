/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { apiFetch } from '@/utils/api';
import type { CategoryItem, CategoryListResponse, OrphanPromptDetailsResponse } from './types';

export function fetchCategories(): Promise<CategoryListResponse> {
  return apiFetch<CategoryListResponse>('/api/categories/manage');
}

export function createCategoryRequest(payload: Record<string, unknown>): Promise<unknown> {
  return apiFetch('/api/categories', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateCategoryRequest(
  categoryId: number,
  payload: Record<string, unknown>
): Promise<unknown> {
  return apiFetch(`/api/categories/${categoryId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function deleteCategoryRequest(categoryId: number, force = false): Promise<unknown> {
  const query = force ? '?confirm=true&force=true' : '?confirm=true';
  return apiFetch(`/api/categories/${categoryId}${query}`, {
    method: 'DELETE',
  });
}

export function mergeCategoriesRequest(targetId: number, sourceIds: number[]): Promise<unknown> {
  return apiFetch('/api/categories/merge', {
    method: 'POST',
    body: JSON.stringify({ target_id: targetId, source_ids: sourceIds, confirm: true }),
  });
}

export function findReplaceCategoriesRequest(find: string, replace: string): Promise<unknown> {
  return apiFetch('/api/categories/find-replace', {
    method: 'POST',
    body: JSON.stringify({ find, replace, confirm: true }),
  });
}

export function bulkDeleteCategoriesRequest(ids: number[], force: boolean): Promise<unknown> {
  return apiFetch('/api/categories/bulk-delete', {
    method: 'POST',
    body: JSON.stringify({ ids, force, confirm: true }),
  });
}

export function exportCategoriesRequest(): Promise<{ items: CategoryItem[] }> {
  return apiFetch<{ items: CategoryItem[] }>('/api/categories/export');
}

export function importCategoriesRequest(items: Array<Record<string, unknown>>): Promise<unknown> {
  return apiFetch('/api/categories/import', {
    method: 'POST',
    body: JSON.stringify({ items }),
  });
}

export function undoCategoriesRequest(): Promise<unknown> {
  return apiFetch('/api/categories/undo', {
    method: 'POST',
  });
}

export function fetchCategoryAnalytics(): Promise<{
  total: number;
  used: number;
  unused: number;
  top: Array<{ name: string; count: number }>;
}> {
  return apiFetch('/api/categories/analytics');
}

export function fetchOrphanPrompts(): Promise<{ prompt_ids: number[]; count: number }> {
  return apiFetch<{ prompt_ids: number[]; count: number }>('/api/categories/orphans');
}

export function fetchOrphanPromptDetails(): Promise<OrphanPromptDetailsResponse> {
  return apiFetch<OrphanPromptDetailsResponse>('/api/categories/orphans/details');
}

export function fetchUnusedCategories(): Promise<CategoryListResponse> {
  return apiFetch<CategoryListResponse>('/api/categories/unused');
}

export function assignCategoryToPromptRequest(promptId: number, category: string): Promise<unknown> {
  return apiFetch('/api/categories/assign-orphans', {
    method: 'POST',
    body: JSON.stringify({ prompt_ids: [promptId], category, confirm: true }),
  });
}
