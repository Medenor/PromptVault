/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import type { PromptResponse } from '@/types';
import { t, tUnsafe } from '@/utils/i18n';
import { attachSwipeReveal } from '@/gestures';
import {
  buildPillStyleFilled,
  buildPillStyleOutline,
  getCategoryColorMap,
  getTagColorMap,
} from './colors';
import { escapeHtml } from './shared';
import { selectedPromptIds, handleCheckboxChange } from './bulk-actions';
import type { PromptId } from './types';

export interface PromptElementHandlers {
  onCopy: (id: PromptId) => void;
  onEdit: (id: PromptId) => void;
  onDelete: (id: PromptId) => void;
  onToggleFavorite: (id: PromptId) => void;
  onShowHistory: (id: number) => void;
  onCopyWithVersion: (id: PromptId) => void;
}

let promptElementHandlers: PromptElementHandlers | null = null;
let lastSelectedPromptIdSetter: (id: number) => void = () => {};

export function setPromptElementHandlers(handlers: PromptElementHandlers): void {
  promptElementHandlers = handlers;
}

// Card interactions (copy/edit/delete/etc.) also need to update the
// orchestrator's "last selected prompt" tracker. Injected via callback rather
// than importing prompt-list.ts back, to avoid a cycle (prompt-list.ts is the
// consumer of this module, not the other way around).
export function setLastSelectedPromptIdSetter(setter: (id: number) => void): void {
  lastSelectedPromptIdSetter = setter;
}

export function createPromptElement(id: string, prompt: PromptResponse): HTMLDivElement {
  const handlers = promptElementHandlers;
  if (!handlers) {
    throw new Error('Prompt element handlers not initialized');
  }

  const div = document.createElement('div');
  div.className =
    'prompt-item bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 transition-all hover:scale-[1.02] cursor-pointer';
  div.dataset.id = id;
  div.dataset.navLabel = prompt.title || '';

  // Add selected class if prompt is in selection
  if (selectedPromptIds.has(parseInt(id))) {
    div.classList.add('selected');
  }

  // Create checkbox for bulk selection
  const titleId = `prompt-title-${id}`;
  const checkbox = document.createElement('input');
  checkbox.type = 'checkbox';
  checkbox.className =
    'prompt-checkbox w-5 h-5 md:w-4 md:h-4 rounded text-blue-500 focus:ring-blue-500';
  checkbox.dataset.promptId = id;
  checkbox.setAttribute('aria-labelledby', titleId);
  checkbox.checked = selectedPromptIds.has(parseInt(id));
  checkbox.addEventListener('change', (event) => {
    const target = event.target as HTMLInputElement | null;
    handleCheckboxChange(parseInt(id, 10), target?.checked ?? false);
    event.stopPropagation(); // Prevent triggering the div click event
  });

  const tagColorMap = getTagColorMap();
  const categoryColorMap = getCategoryColorMap();

  // Build tags HTML
  const tagColorLookup = prompt.tag_colors ?? {};
  const tagsHTML =
    prompt.tags && prompt.tags.length > 0
      ? prompt.tags
          .map((tag) => {
            const color = tagColorLookup[tag] ?? tagColorMap[tag];
            const style = buildPillStyleOutline(color);
            return `<span class="px-2 py-1 text-xs font-medium rounded-full border border-gray-300 dark:border-gray-600 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200" data-tag-pill="true" data-tag-name="${escapeHtml(tag)}"${style}>
                ${escapeHtml(tag)}
              </span>`;
          })
          .join('')
      : '';

  const categoryColor = prompt.category_color ?? categoryColorMap[prompt.category];
  const categoryStyle = buildPillStyleFilled(categoryColor);

  const semVerBadge = prompt.semantic_version
    ? `<span class="version-badge px-2 py-0.5 text-xs font-semibold rounded-full bg-blue-100 text-blue-700 ml-2">v${prompt.semantic_version}</span>`
    : '';

  // eslint-disable-next-line no-restricted-properties -- every interpolation is wrapped in escapeHtml()
  div.innerHTML = `
	        <div class="flex items-start justify-between mb-3">
	            <h4 id="${titleId}" class="text-prompt-title font-semibold text-gray-900 dark:text-gray-100 flex-1 flex items-center flex-wrap gap-1">${escapeHtml(prompt.title)}${semVerBadge}</h4>
	            <div class="flex items-center gap-1 ml-2" id="prompt-actions-${id}">
	                <button class="favorite-btn flex items-center justify-center min-w-[44px] min-h-[44px] md:min-w-0 md:min-h-0 text-xl hover:scale-110 transition-transform focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-700 rounded" data-id="${id}">
	                    ${prompt.favorite ? '★' : '☆'}
	                </button>
	            </div>
	        </div>
        <div class="flex flex-wrap gap-2 mb-3">
            <span class="px-2 py-1 text-xs font-semibold rounded-md bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200" data-category-pill="true" data-category-name="${escapeHtml(prompt.category)}"${categoryStyle}>
              ${escapeHtml(prompt.category) || t('categories.noCategory')}
            </span>
            ${tagsHTML}
        </div>
        <p class="prompt-body-text text-prompt-body text-gray-600 dark:text-gray-300 mb-1 line-clamp-3">${escapeHtml(prompt.prompt)}</p>
        <button type="button" class="read-more-btn hidden min-h-[44px] md:min-h-0 -ml-2 px-2 mb-3 text-xs font-medium text-blue-700 hover:text-blue-800 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-700 rounded" data-i18n="prompt.readMore">Read More</button>
        <div class="flex flex-wrap gap-2">
            <button class="history-btn min-h-[44px] md:min-h-0 px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 transition-all hover:scale-105 active:scale-95" data-id="${id}" data-i18n="version.history">History</button>
            <button class="copy-btn min-h-[44px] md:min-h-0 px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 transition-all hover:scale-105 active:scale-95" data-id="${id}" data-i18n="actions.copy">Copy</button>
            <button class="copy-with-version-btn min-h-[44px] md:min-h-0 px-3 py-1.5 text-xs font-medium rounded-lg bg-purple-100 text-purple-700 hover:bg-purple-200 transition-all hover:scale-105 active:scale-95" data-id="${id}" data-i18n="version.copyWithMetadata">Copy+Version</button>
            <button class="edit-btn min-h-[44px] md:min-h-0 px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-100 text-blue-700 hover:bg-blue-200 transition-all hover:scale-105 active:scale-95" data-id="${id}" data-i18n="actions.edit">Edit</button>
            <button class="delete-btn min-h-[44px] md:min-h-0 px-3 py-1.5 text-xs font-medium rounded-lg bg-red-100 text-red-700 hover:bg-red-200 transition-all hover:scale-105 active:scale-95" data-id="${id}" data-i18n="actions.delete">Delete</button>
        </div>
    `;

  // Insert checkbox at the beginning of prompt-actions
  const promptActions = div.querySelector(`#prompt-actions-${id}`) as HTMLElement | null;
  if (promptActions) {
    promptActions.insertBefore(checkbox, promptActions.firstChild);
  }

  // Update translations for dynamically created elements
  div.querySelectorAll('[data-i18n]').forEach((element) => {
    const key = element.getAttribute('data-i18n');
    if (key) {
      element.textContent = tUnsafe(key);
    }
  });

  // Add event listeners and tooltips
  const copyBtn = div.querySelector('.copy-btn') as HTMLButtonElement | null;
  copyBtn?.addEventListener('click', () => {
    lastSelectedPromptIdSetter(parseInt(id, 10));
    handlers.onCopy(id);
  });
  if (copyBtn) {
    copyBtn.title = t('actions.copy');
  }

  const editBtn = div.querySelector('.edit-btn') as HTMLButtonElement | null;
  editBtn?.addEventListener('click', () => {
    lastSelectedPromptIdSetter(parseInt(id, 10));
    handlers.onEdit(id);
  });
  if (editBtn) {
    editBtn.title = t('actions.edit');
  }

  const deleteBtn = div.querySelector('.delete-btn') as HTMLButtonElement | null;
  deleteBtn?.addEventListener('click', () => {
    lastSelectedPromptIdSetter(parseInt(id, 10));
    handlers.onDelete(id);
  });
  if (deleteBtn) {
    deleteBtn.title = t('actions.delete');
  }

  const favoriteBtn = div.querySelector('.favorite-btn') as HTMLButtonElement | null;
  favoriteBtn?.addEventListener('click', () => {
    lastSelectedPromptIdSetter(parseInt(id, 10));
    handlers.onToggleFavorite(id);
  });
  if (favoriteBtn) {
    setFavoriteButtonA11y(favoriteBtn, Boolean(prompt.favorite));
  }

  const historyBtn = div.querySelector('.history-btn') as HTMLButtonElement | null;
  historyBtn?.addEventListener('click', () => {
    lastSelectedPromptIdSetter(parseInt(id, 10));
    handlers.onShowHistory(parseInt(id, 10));
  });
  if (historyBtn) {
    historyBtn.title = t('version.history');
  }

  const copyWithVersionBtn = div.querySelector(
    '.copy-with-version-btn'
  ) as HTMLButtonElement | null;
  copyWithVersionBtn?.addEventListener('click', () => {
    lastSelectedPromptIdSetter(parseInt(id, 10));
    handlers.onCopyWithVersion(id);
  });
  if (copyWithVersionBtn) {
    copyWithVersionBtn.title = t('version.copyWithMetadata');
  }

  // Track prompt selection on click and open editor
  div.addEventListener('click', (event) => {
    const target = event.target as Element | null;
    if (target && (target.closest('button') || target.closest('input') || target.closest('a'))) {
      return;
    }
    lastSelectedPromptIdSetter(parseInt(id, 10));
    handlers.onEdit(id);
  });

  // "Read More" — reveal the full prompt body when the clamped text overflows.
  const bodyText = div.querySelector('.prompt-body-text') as HTMLElement | null;
  const readMoreBtn = div.querySelector('.read-more-btn') as HTMLButtonElement | null;
  if (bodyText && readMoreBtn) {
    requestAnimationFrame(() => {
      if (bodyText.scrollHeight > bodyText.clientHeight + 1) {
        readMoreBtn.classList.remove('hidden');
      }
    });
    readMoreBtn.addEventListener('click', (event) => {
      event.stopPropagation();
      const isNowClamped = bodyText.classList.toggle('line-clamp-3');
      readMoreBtn.textContent = isNowClamped ? t('prompt.readMore') : t('prompt.readLess');
    });
  }

  // Swipe gestures (FR-007): left reveals delete (with confirmation, same as
  // the visible Delete button), right opens the editor (same as tapping the
  // card). Both are shortcuts for the existing, always-visible controls above.
  // The returned detach fn is intentionally unused: each card is a fresh,
  // never-reused element (unlike the version carousel's persistent
  // versionList, which stores/calls its detach fn before re-initializing in
  // place) and renderPrompts() always discards prior cards wholesale via
  // container.innerHTML = '', which drops the listeners with the node.
  attachSwipeReveal(div, {
    onSwipeLeft: () => {
      lastSelectedPromptIdSetter(parseInt(id, 10));
      handlers.onDelete(id);
    },
    onSwipeRight: () => {
      lastSelectedPromptIdSetter(parseInt(id, 10));
      handlers.onEdit(id);
    },
  });

  return div;
}

export function setFavoriteButtonA11y(button: HTMLButtonElement, isFavorite: boolean): void {
  button.setAttribute('aria-pressed', isFavorite ? 'true' : 'false');
  const label = isFavorite ? t('actions.removeFavorite') : t('actions.addFavorite');
  button.setAttribute('aria-label', label);
  button.title = label;
}
