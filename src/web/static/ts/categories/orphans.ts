/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { tUnsafe } from '@/utils/i18n';
import { setupScrollIndicators } from '@/utils/dom';
import { showNotification } from '@/utils/notifications';
import { html } from '@/utils/safe-html';
import {
  fetchCategoryAnalytics,
  fetchOrphanPromptDetails,
  fetchOrphanPrompts,
  fetchUnusedCategories,
} from './api';

export interface AnalyticsElements {
  analyticsTotal: HTMLElement | null;
  analyticsUsed: HTMLElement | null;
  analyticsUnused: HTMLElement | null;
  analyticsTop: HTMLElement | null;
}

export async function loadAnalytics(
  elements: AnalyticsElements,
  handleError: (error: unknown, fallback: string) => void
): Promise<void> {
  try {
    const data = await fetchCategoryAnalytics();
    if (elements.analyticsTotal) elements.analyticsTotal.textContent = String(data.total ?? 0);
    if (elements.analyticsUsed) elements.analyticsUsed.textContent = String(data.used ?? 0);
    if (elements.analyticsUnused) elements.analyticsUnused.textContent = String(data.unused ?? 0);
    if (elements.analyticsTop) {
      // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
      elements.analyticsTop.innerHTML = '';
      data.top.forEach((item) => {
        const li = document.createElement('li');
        li.textContent = `${item.name} (${item.count})`;
        elements.analyticsTop?.appendChild(li);
      });
    }
  } catch (error) {
    handleError(error, 'Failed to load analytics');
  }
}

export interface OrphanElements {
  orphansCount: HTMLElement | null;
  orphansDetails: HTMLElement | null;
  unusedCount: HTMLElement | null;
  unusedList: HTMLElement | null;
}

export async function loadOrphans(
  elements: OrphanElements,
  handleError: (error: unknown, fallback: string) => void,
  onAssignCategory: (promptId: number, category: string) => void,
  resolveCategoryInput: (rawCategory: string) => string | null
): Promise<void> {
  try {
    const data = await fetchOrphanPrompts();
    if (elements.orphansCount) {
      elements.orphansCount.textContent = String(data.count ?? 0);
    }
    if (elements.orphansDetails) {
      await renderPromptDetails(
        data.prompt_ids ?? [],
        elements.orphansDetails,
        handleError,
        onAssignCategory,
        resolveCategoryInput
      );
      setupScrollIndicators(elements.orphansDetails);
    }
  } catch (error) {
    handleError(error, 'Failed to load orphans');
  }

  try {
    const data = await fetchUnusedCategories();
    if (elements.unusedCount) {
      elements.unusedCount.textContent = String(data.items?.length ?? 0);
    }
    if (elements.unusedList) {
      // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
      elements.unusedList.innerHTML = '';
      (data.items ?? []).forEach((item) => {
        const li = document.createElement('li');
        li.textContent = `${item.name} (#${item.id})`;
        elements.unusedList?.appendChild(li);
      });
      setupScrollIndicators(elements.unusedList);
    }
  } catch (error) {
    handleError(error, 'Failed to load unused categories');
  }
}

async function renderPromptDetails(
  promptIds: number[],
  container: HTMLElement,
  handleError: (error: unknown, fallback: string) => void,
  onAssignCategory: (promptId: number, category: string) => void,
  resolveCategoryInput: (rawCategory: string) => string | null
): Promise<void> {
  // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
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
    // eslint-disable-next-line no-restricted-properties -- structurally escaped via html`` tagged template (utils/safe-html.ts)
    li.innerHTML = html`
      <span class="text-gray-800 dark:text-gray-100"
        >#${id} — ${title || tUnsafe('management.untitledPrompt')}</span
      >
      <div class="flex flex-col gap-2 md:flex-row md:items-center md:gap-3">
        <input
          type="text"
          data-prompt-category="${id}"
          placeholder="${tUnsafe('management.assignPlaceholder')}"
          class="w-full md:w-56 px-2 py-1 border border-gray-300 rounded dark:border-gray-600"
        />
        <button
          type="button"
          data-assign-category="${id}"
          class="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
        >
          ${tUnsafe('categories.assignOrphans')}
        </button>
      </div>
    `;
    container.appendChild(li);
  });

  container.querySelectorAll<HTMLButtonElement>('[data-assign-category]').forEach((button) => {
    button.addEventListener('click', () => {
      const promptId = Number(button.dataset.assignCategory || '');
      const input = container.querySelector<HTMLInputElement>(
        `input[data-prompt-category="${promptId}"]`
      );
      if (!promptId || !input) {
        return;
      }
      const category = input.value.trim();
      if (!category) {
        showNotification(tUnsafe('management.assignPlaceholder'), 'error');
        return;
      }
      const resolved = resolveCategoryInput(category);
      if (!resolved) {
        return;
      }
      onAssignCategory(promptId, resolved);
    });
  });
}
