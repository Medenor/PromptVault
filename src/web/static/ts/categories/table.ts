/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { tUnsafe } from '@/utils/i18n';
import { setupScrollIndicators } from '@/utils/dom';
import { html } from '@/utils/safe-html';
import {
  initializeTableFirstCharNavigation,
  initializeRovingTabindex,
  resetRovingTabindexState,
} from './a11y';
import type { CategoryItem } from './types';

export function normalizeSearch(value: string): string {
  return value.trim().toLowerCase();
}

export function filterItems(items: CategoryItem[], query: string): CategoryItem[] {
  if (!query) {
    return items;
  }
  return items.filter((item) => item.name.toLowerCase().includes(query));
}

export function buildCategoryPayload(row: HTMLTableRowElement): Record<string, unknown> {
  const fields = row.querySelectorAll<HTMLInputElement>('input[data-field]');
  const payload: Record<string, unknown> = {};

  fields.forEach((field) => {
    const key = field.dataset.field as string;
    if (!key) {
      return;
    }
    payload[key] = field.value.trim();
  });

  return payload;
}

function normalizeHexValue(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  const trimmed = value.trim();
  const normalized = trimmed.startsWith('#') ? trimmed : `#${trimmed}`;
  return /^#[0-9a-fA-F]{6}$/.test(normalized) ? normalized.toUpperCase() : null;
}

function normalizeHexForPicker(value: string | null | undefined): string {
  return normalizeHexValue(value) ?? '#3B82F6';
}

export interface RenderRowsCallbacks {
  onSave: (categoryId: number, row: HTMLTableRowElement) => void;
  onDelete: (categoryId: number) => void;
}

export function renderRows(
  tableBody: HTMLTableSectionElement | null,
  items: CategoryItem[],
  callbacks: RenderRowsCallbacks
): void {
  if (!tableBody) {
    return;
  }
  // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
  tableBody.innerHTML = '';

  const emptyState = document.getElementById('categories-empty-state');
  const tableContainer = document.getElementById('categories-table-container');

  if (items.length === 0) {
    if (emptyState) {
      emptyState.classList.remove('hidden');
    }
    if (tableContainer) {
      tableContainer.classList.add('hidden');
    }
    return;
  } else {
    if (emptyState) {
      emptyState.classList.add('hidden');
    }
    if (tableContainer) {
      tableContainer.classList.remove('hidden');
    }
  }

  const saveLabel = tUnsafe('actions.save');
  const deleteLabel = tUnsafe('actions.delete');
  const colorLabel = tUnsafe('management.color');
  const nameLabel = tUnsafe('management.name');
  const descriptionLabel = tUnsafe('management.description');
  const selectLabel = tUnsafe('management.select');

  for (const item of items) {
    const row = document.createElement('tr');
    row.className = 'border-b border-gray-100 category-item';
    row.setAttribute('role', 'option');
    row.dataset.id = String(item.id);

    // eslint-disable-next-line no-restricted-properties -- structurally escaped via html`` tagged template (utils/safe-html.ts)
    row.innerHTML = html`
      <td class="py-2 pr-4">
        <input
          type="checkbox"
          data-select-id="${item.id}"
          aria-label="${selectLabel} #${item.id}"
          tabindex="-1"
        />
      </td>
      <td class="py-2 pr-4 text-gray-600 dark:text-gray-400">#${item.id}</td>
      <td class="py-2 pr-4">
        <input
          data-field="name"
          aria-label="${nameLabel}"
          class="w-full px-2 py-1 border border-gray-300 rounded dark:border-gray-600"
          value="${item.name}"
        />
      </td>
      <td class="py-2 pr-4">
        <input
          data-field="description"
          aria-label="${descriptionLabel}"
          class="w-full px-2 py-1 border border-gray-300 rounded dark:border-gray-600"
          value="${item.description ?? ''}"
        />
      </td>
      <td class="py-2 pr-4">
        <div class="flex items-center gap-2">
          <input
            data-field="color"
            aria-label="${colorLabel}"
            class="w-full px-2 py-1 border border-gray-300 rounded dark:border-gray-600"
            value="${item.color ?? ''}"
          />
          <input
            data-color-picker
            type="color"
            value="${normalizeHexForPicker(item.color)}"
            title="${colorLabel}"
            aria-label="${colorLabel}"
            class="h-8 w-8 rounded border border-gray-300 p-0 dark:border-gray-600"
          />
        </div>
      </td>
      <td class="py-2 pr-4 text-gray-600 dark:text-gray-400">${item.usage_count}</td>
      <td class="py-2 pr-4">
        <div class="flex items-center gap-2">
          <button
            data-action="save"
            class="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            ${saveLabel}
          </button>
          <button
            data-action="delete"
            class="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700"
          >
            ${deleteLabel}
          </button>
        </div>
      </td>
    `;

    row.querySelector('[data-action="save"]')?.addEventListener('click', () => {
      callbacks.onSave(item.id, row);
    });

    const deleteBtn = row.querySelector<HTMLButtonElement>('[data-action="delete"]');
    if (deleteBtn) {
      deleteBtn.addEventListener('click', () => {
        callbacks.onDelete(item.id);
      });
    }

    const colorInput = row.querySelector<HTMLInputElement>('input[data-field="color"]');
    const colorPicker = row.querySelector<HTMLInputElement>('input[data-color-picker]');
    if (colorInput && colorPicker) {
      colorPicker.addEventListener('input', () => {
        colorInput.value = colorPicker.value;
      });
      colorInput.addEventListener('input', () => {
        const normalized = normalizeHexValue(colorInput.value);
        if (normalized) {
          colorPicker.value = normalized;
        }
      });
    }

    tableBody.appendChild(row);
  }

  setupScrollIndicators(tableContainer);
  initializeTableFirstCharNavigation(tableBody);

  resetRovingTabindexState();
  initializeRovingTabindex();
}
