/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { apiFetch } from '@/utils/api';
import type { OrphanPromptDetailsResponse, TagItem, TagListResponse } from './types';

export function fetchTags(): Promise<TagListResponse> {
  return apiFetch<TagListResponse>('/api/tags/manage');
}

export function createTagRequest(payload: Record<string, unknown>): Promise<unknown> {
  return apiFetch('/api/tags', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function updateTagRequest(tagId: number, payload: Record<string, unknown>): Promise<unknown> {
  return apiFetch(`/api/tags/${tagId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export function deleteTagRequest(tagId: number, force = false): Promise<unknown> {
  const query = force ? '?confirm=true&force=true' : '?confirm=true';
  return apiFetch(`/api/tags/${tagId}${query}`, {
    method: 'DELETE',
  });
}

export function mergeTagsRequest(targetId: number, sourceIds: number[]): Promise<unknown> {
  return apiFetch('/api/tags/merge', {
    method: 'POST',
    body: JSON.stringify({ target_id: targetId, source_ids: sourceIds, confirm: true }),
  });
}

export function findReplaceTagsRequest(find: string, replace: string): Promise<unknown> {
  return apiFetch('/api/tags/find-replace', {
    method: 'POST',
    body: JSON.stringify({ find, replace, confirm: true }),
  });
}

export function bulkDeleteTagsRequest(ids: number[], force: boolean): Promise<unknown> {
  return apiFetch('/api/tags/bulk-delete', {
    method: 'POST',
    body: JSON.stringify({ ids, force, confirm: true }),
  });
}

export function exportTagsRequest(): Promise<{ items: TagItem[] }> {
  return apiFetch<{ items: TagItem[] }>('/api/tags/export');
}

export function importTagsRequest(items: Array<Record<string, unknown>>): Promise<unknown> {
  return apiFetch('/api/tags/import', {
    method: 'POST',
    body: JSON.stringify({ items }),
  });
}

export function undoTagsRequest(): Promise<unknown> {
  return apiFetch('/api/tags/undo', {
    method: 'POST',
  });
}

export function fetchTagAnalytics(): Promise<{
  total: number;
  used: number;
  unused: number;
  top: Array<{ name: string; count: number }>;
  co_occurrence: Array<{ tag_a: string; tag_b: string; count: number }>;
}> {
  return apiFetch('/api/tags/analytics');
}

export function fetchOrphanTags(): Promise<TagListResponse> {
  return apiFetch<TagListResponse>('/api/tags/orphans');
}

export function fetchOrphanPrompts(): Promise<{ prompt_ids: number[]; count: number }> {
  return apiFetch<{ prompt_ids: number[]; count: number }>('/api/tags/orphan-prompts');
}

export function fetchOrphanPromptDetails(): Promise<OrphanPromptDetailsResponse> {
  return apiFetch<OrphanPromptDetailsResponse>('/api/tags/orphan-prompts/details');
}

export function assignTagsToPromptRequest(promptId: number, tags: string[]): Promise<unknown> {
  return apiFetch('/api/tags/bulk-update', {
    method: 'POST',
    body: JSON.stringify({ prompt_ids: [promptId], add: tags, remove: [], confirm: true }),
  });
}
