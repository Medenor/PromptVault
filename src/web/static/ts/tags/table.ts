/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { tUnsafe } from '@/utils/i18n';
import { setupScrollIndicators } from '@/utils/dom';
import { html, raw } from '@/utils/safe-html';
import {
  applyFocusStyles,
  initializeTableFirstCharNavigation,
  initializeRovingTabindex,
  resetRovingTabindexState,
} from './a11y';
import type { TagItem } from './types';

export function normalizeSearch(value: string): string {
  return value.trim().toLowerCase();
}

export function filterItems(items: TagItem[], query: string): TagItem[] {
  if (!query) {
    return items;
  }
  return items.filter((item) => item.name.toLowerCase().includes(query));
}

export function buildTagPayload(row: HTMLTableRowElement): Record<string, unknown> {
  const fields = row.querySelectorAll<HTMLInputElement | HTMLSelectElement>('[data-field]');
  const payload: Record<string, unknown> = {};

  fields.forEach((field) => {
    const key = field.dataset.field as string;
    if (!key) {
      return;
    }
    if (key === 'parent_tag_id') {
      payload[key] = field.value ? Number(field.value) : null;
    } else {
      payload[key] = field.value.trim();
    }
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

function renderParentOptions(
  items: TagItem[],
  currentId: number,
  selectedId: number | null,
  parentNoneLabel: string
): string {
  const options = [html`<option value="">${parentNoneLabel}</option>`];
  items.forEach((item) => {
    if (item.id === currentId) {
      return;
    }
    const selected = selectedId === item.id ? 'selected' : '';
    options.push(html`<option value="${item.id}" ${raw(selected)}>${item.name}</option>`);
  });
  return options.join('');
}

export function populateCreateParentSelect(
  createParent: HTMLSelectElement | null,
  items: TagItem[]
): void {
  if (!createParent) {
    return;
  }
  // eslint-disable-next-line no-restricted-properties -- structurally escaped via html`` tagged template (utils/safe-html.ts)
  createParent.innerHTML = html`<option value="">${tUnsafe('management.parentNone')}</option>`;
  items.forEach((item) => {
    const option = document.createElement('option');
    option.value = String(item.id);
    option.textContent = item.name;
    createParent.appendChild(option);
  });
}

export interface RenderRowsCallbacks {
  onSave: (tagId: number, row: HTMLTableRowElement) => void;
  onDelete: (tagId: number) => void;
}

export function renderRows(
  tableBody: HTMLTableSectionElement | null,
  items: TagItem[],
  allItems: TagItem[],
  callbacks: RenderRowsCallbacks
): void {
  if (!tableBody) {
    return;
  }
  // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
  tableBody.innerHTML = '';

  const emptyState = document.getElementById('tags-empty-state');
  const tableContainer = document.getElementById('tags-table-container');

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
  const parentNoneLabel = tUnsafe('management.parentNone');
  const colorLabel = tUnsafe('management.color');
  const nameLabel = tUnsafe('management.name');
  const descriptionLabel = tUnsafe('management.description');
  const parentLabel = tUnsafe('management.parent');
  const selectLabel = tUnsafe('management.select');

  for (const item of items) {
    const row = document.createElement('tr');
    row.className = 'border-b border-gray-100 tag-item';
    row.setAttribute('role', 'option');
    row.dataset.id = String(item.id);
    row.id = `data-tag-id-${item.id}`;

    // eslint-disable-next-line no-restricted-properties -- structurally escaped via html`` tagged template (utils/safe-html.ts)
    row.innerHTML = html`
      <td class="py-2 pr-4">
        <input
          type="checkbox"
          id="checkbox-${item.id}"
          data-select-id="${item.id}"
          aria-label="${selectLabel} #${item.id}"
          tabindex="-1"
        />
      </td>
      <td class="py-2 pr-4 text-gray-600 dark:text-gray-400">#${item.id}</td>
      <td class="py-2 pr-4">
        <input
          id="name-input-${item.id}"
          data-field="name"
          aria-label="${nameLabel}"
          class="w-full px-2 py-1 border border-gray-300 rounded dark:border-gray-600"
          value="${item.name}"
        />
      </td>
      <td class="py-2 pr-4">
        <input
          id="desc-input-${item.id}"
          data-field="description"
          aria-label="${descriptionLabel}"
          class="w-full px-2 py-1 border border-gray-300 rounded dark:border-gray-600"
          value="${item.description ?? ''}"
        />
      </td>
      <td class="py-2 pr-4">
        <div class="flex items-center gap-2">
          <input
            id="color-input-${item.id}"
            data-field="color"
            aria-label="${colorLabel}"
            class="w-full px-2 py-1 border border-gray-300 rounded dark:border-gray-600"
            value="${item.color ?? ''}"
          />
          <input
            id="color-picker-${item.id}"
            data-color-picker
            type="color"
            value="${normalizeHexForPicker(item.color)}"
            title="${colorLabel}"
            aria-label="${colorLabel}"
            class="h-8 w-8 rounded border border-gray-300 p-0 dark:border-gray-600"
          />
        </div>
      </td>
      <td class="py-2 pr-4">
        <select
          id="parent-select-${item.id}"
          data-field="parent_tag_id"
          aria-label="${parentLabel}"
          class="w-36 px-2 py-1 border border-gray-300 rounded dark:border-gray-600"
        >
          ${raw(
            renderParentOptions(allItems, item.id, item.parent_tag_id ?? null, parentNoneLabel)
          )}
        </select>
      </td>
      <td class="py-2 pr-4 text-gray-600 dark:text-gray-400">${item.usage_count}</td>
      <td class="py-2 pr-4">
        <div class="flex items-center gap-2">
          <button
            id="save-btn-${item.id}"
            data-action="save"
            class="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            ${saveLabel}
          </button>
          <button
            id="delete-btn-${item.id}"
            data-action="delete"
            class="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700"
          >
            ${deleteLabel}
          </button>
        </div>
      </td>
    `;

    const checkbox = row.querySelector<HTMLInputElement>('input[type="checkbox"]');
    const nameInput = row.querySelector<HTMLInputElement>('input[data-field="name"]');
    const descInput = row.querySelector<HTMLInputElement>('input[data-field="description"]');
    const colorInput = row.querySelector<HTMLInputElement>('input[data-field="color"]');
    const colorPickerInput = row.querySelector<HTMLInputElement>('input[data-color-picker]');
    const parentSelect = row.querySelector<HTMLSelectElement>('select[data-field="parent_tag_id"]');
    const saveBtn = row.querySelector<HTMLButtonElement>('[data-action="save"]');
    const deleteBtn = row.querySelector<HTMLButtonElement>('[data-action="delete"]');

    if (checkbox) applyFocusStyles(checkbox);
    if (nameInput) applyFocusStyles(nameInput);
    if (descInput) applyFocusStyles(descInput);
    if (colorInput) applyFocusStyles(colorInput);
    if (colorPickerInput) applyFocusStyles(colorPickerInput);
    if (parentSelect) applyFocusStyles(parentSelect);
    if (saveBtn) applyFocusStyles(saveBtn);
    if (deleteBtn) applyFocusStyles(deleteBtn, '#ef4444');

    saveBtn?.addEventListener('click', () => {
      callbacks.onSave(item.id, row);
    });

    if (deleteBtn) {
      deleteBtn.addEventListener('click', () => {
        callbacks.onDelete(item.id);
      });
    }

    if (colorInput && colorPickerInput) {
      colorPickerInput.addEventListener('input', () => {
        colorInput.value = colorPickerInput.value;
      });
      colorInput.addEventListener('input', () => {
        const normalized = normalizeHexValue(colorInput.value);
        if (normalized) {
          colorPickerInput.value = normalized;
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
