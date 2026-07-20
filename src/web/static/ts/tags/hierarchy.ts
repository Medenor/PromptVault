/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { tUnsafe } from '@/utils/i18n';
import { setupScrollIndicators } from '@/utils/dom';
import { showNotification } from '@/utils/notifications';
import { fetchOrphanPromptDetails, fetchOrphanPrompts, fetchOrphanTags } from './api';
import type { TagItem } from './types';

export function renderHierarchyTree(hierarchyTree: HTMLElement | null, items: TagItem[]): void {
  if (!hierarchyTree) {
    return;
  }
  hierarchyTree.innerHTML = '';

  const byParent: Record<string, TagItem[]> = {};
  items.forEach((item) => {
    const key = item.parent_tag_id ? String(item.parent_tag_id) : 'root';
    if (!byParent[key]) {
      byParent[key] = [];
    }
    byParent[key].push(item);
  });

  Object.values(byParent).forEach((group) => group.sort((a, b) => a.name.localeCompare(b.name)));

  const rootItems = byParent['root'] ?? [];
  if (rootItems.length === 0) {
    hierarchyTree.textContent = tUnsafe('management.noHierarchyDefined');
    return;
  }

  const container = document.createElement('ul');
  container.className = 'space-y-2';
  rootItems.forEach((item) => {
    container.appendChild(buildNode(item, byParent));
  });
  hierarchyTree.appendChild(container);

  setupScrollIndicators(hierarchyTree);
}

function buildNode(item: TagItem, byParent: Record<string, TagItem[]>): HTMLLIElement {
  const li = document.createElement('li');
  li.className = 'border border-gray-200 rounded-lg p-3 bg-gray-50';
  li.textContent = item.name;

  const children = byParent[String(item.id)] ?? [];
  if (children.length > 0) {
    const list = document.createElement('ul');
    list.className = 'mt-2 space-y-2 pl-4';
    children.forEach((child) => {
      list.appendChild(buildNode(child, byParent));
    });
    li.appendChild(list);
  }

  return li;
}

export interface OrphanElements {
  orphansCount: HTMLElement | null;
  orphansList: HTMLElement | null;
  orphansPromptCount: HTMLElement | null;
  orphansPromptDetails: HTMLElement | null;
}

export async function loadOrphans(
  elements: OrphanElements,
  handleError: (error: unknown, fallback: string) => void,
  onAssignTags: (promptId: number, tags: string[]) => void,
  resolveTagInputs: (rawTags: string) => string[] | null
): Promise<void> {
  try {
    const data = await fetchOrphanTags();
    if (elements.orphansCount) {
      elements.orphansCount.textContent = String(data.items.length);
    }
    if (elements.orphansList) {
      elements.orphansList.innerHTML = '';
      data.items.forEach((item) => {
        const li = document.createElement('li');
        li.textContent = item.name;
        elements.orphansList?.appendChild(li);
      });
      setupScrollIndicators(elements.orphansList);
    }
  } catch (error) {
    handleError(error, 'Failed to load orphan tags');
  }

  try {
    const data = await fetchOrphanPrompts();
    if (elements.orphansPromptCount) {
      elements.orphansPromptCount.textContent = String(data.count ?? 0);
    }
    if (elements.orphansPromptDetails) {
      await renderPromptDetails(
        data.prompt_ids ?? [],
        elements.orphansPromptDetails,
        handleError,
        onAssignTags,
        resolveTagInputs
      );
      setupScrollIndicators(elements.orphansPromptDetails);
    }
  } catch (error) {
    handleError(error, 'Failed to load prompts without tags');
  }
}

async function renderPromptDetails(
  promptIds: number[],
  container: HTMLElement,
  handleError: (error: unknown, fallback: string) => void,
  onAssignTags: (promptId: number, tags: string[]) => void,
  resolveTagInputs: (rawTags: string) => string[] | null
): Promise<void> {
  container.innerHTML = '';
  if (promptIds.length === 0) {
    return;
  }

  let details: Awaited<ReturnType<typeof fetchOrphanPromptDetails>> | null = null;
  try {
    details = await fetchOrphanPromptDetails();
  } catch (error) {
    handleError(error, 'Failed to load prompt details');
  }

  const detailsMap = new Map<number, string>();
  (details?.items ?? []).forEach((item) => {
    detailsMap.set(item.id, item.title);
  });

  promptIds.forEach((id) => {
    const title = detailsMap.get(id)?.trim() || tUnsafe('management.promptNotFound');
    const li = document.createElement('li');
    li.className = 'flex flex-col gap-2 md:flex-row md:items-center md:justify-between';
    li.innerHTML = `
      <span class="text-gray-800 dark:text-gray-100">#${id} — ${title || tUnsafe('management.untitledPrompt')}</span>
      <div class="flex flex-col gap-2 md:flex-row md:items-center md:gap-3">
        <input
          type="text"
          data-prompt-tags="${id}"
          placeholder="${tUnsafe('management.tagsPlaceholder')}"
          class="w-full md:w-56 px-2 py-1 border border-gray-300 rounded dark:border-gray-600"
        />
        <button
          type="button"
          data-assign-tags="${id}"
          class="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
        >
          ${tUnsafe('actions.applyTags')}
        </button>
      </div>
    `;
    container.appendChild(li);
  });

  container.querySelectorAll<HTMLButtonElement>('[data-assign-tags]').forEach((button) => {
    button.addEventListener('click', () => {
      const promptId = Number(button.dataset.assignTags || '');
      const input = container.querySelector<HTMLInputElement>(
        `input[data-prompt-tags="${promptId}"]`
      );
      if (!promptId || !input) {
        return;
      }
      const rawTags = input.value.trim();
      if (!rawTags) {
        showNotification(tUnsafe('management.tagsPlaceholder'), 'error');
        return;
      }
      const tags = resolveTagInputs(rawTags);
      if (!tags || tags.length === 0) {
        return;
      }
      onAssignTags(promptId, tags);
    });
  });
}
