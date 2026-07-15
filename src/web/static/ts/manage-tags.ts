/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import '../css/tailwind-globals.css';
import { apiFetch, APIRequestError } from '@/utils/api';
import { initI18n, t, tUnsafe, updateStaticTranslations } from '@/utils/i18n';
import { initializeColorPicker } from '@/utils/color-picker';
import { setupScrollIndicators } from '@/utils/dom';
import { showNotification } from '@/utils/notifications';
import { createTypeahead } from '@/utils/typeahead';
import { announce } from '@/utils/a11y';
import { confirmAsync } from '@/utils/dialogs';
import { announceToScreenReader } from '@/utils/focus-management';
import { initSecondaryNav } from '@/utils/secondary-nav';

type TagItem = {
  id: number;
  name: string;
  description?: string | null;
  color?: string | null;
  parent_tag_id?: number | null;
  usage_count: number;
};

type TagListResponse = {
  items: TagItem[];
};
type FormValidationError = {
  inputId: string;
  errorId: string;
  message: string;
};

// Global focus style handler for all interactive elements
function applyFocusStyles(element: HTMLElement, ringColor: string = '#3b82f6'): void {
  const focusHandler = () => {
    element.style.outline = 'none';
    element.style.boxShadow = `0 0 0 3px rgba(255, 255, 255, 0.5), 0 0 0 5px ${ringColor}`;
  };

  const blurHandler = () => {
    element.style.boxShadow = '';
  };

  element.addEventListener('focus', focusHandler);
  element.addEventListener('blur', blurHandler);
}

const elements = {
  tableBody: document.getElementById('tags-table-body') as HTMLTableSectionElement | null,
  searchInput: document.getElementById('tag-search') as HTMLInputElement | null,
  createForm: document.getElementById('tag-create-form') as HTMLFormElement | null,
  createName: document.getElementById('tag-create-name') as HTMLInputElement | null,
  createDescription: document.getElementById('tag-create-description') as HTMLInputElement | null,
  createColor: document.getElementById('tag-create-color') as HTMLInputElement | null,
  createParent: document.getElementById('tag-create-parent') as HTMLSelectElement | null,
  createColorPicker: document.getElementById('tag-create-color-picker') as HTMLInputElement | null,
  mergeTarget: document.getElementById('tag-merge-target') as HTMLInputElement | null,
  mergeSources: document.getElementById('tag-merge-sources') as HTMLInputElement | null,
  mergeButton: document.getElementById('tag-merge-btn') as HTMLButtonElement | null,
  findInput: document.getElementById('tag-find') as HTMLInputElement | null,
  replaceInput: document.getElementById('tag-replace') as HTMLInputElement | null,
  findReplaceButton: document.getElementById('tag-find-replace-btn') as HTMLButtonElement | null,
  bulkDeleteIds: document.getElementById('tag-bulk-delete-ids') as HTMLInputElement | null,
  bulkDeleteForce: document.getElementById('tag-bulk-delete-force') as HTMLInputElement | null,
  bulkDeleteButton: document.getElementById('tag-bulk-delete-btn') as HTMLButtonElement | null,
  exportButton: document.getElementById('tag-export-btn') as HTMLButtonElement | null,
  importFile: document.getElementById('tag-import-file') as HTMLInputElement | null,
  importButton: document.getElementById('tag-import-btn') as HTMLButtonElement | null,
  selectionMergeButton: document.getElementById(
    'tag-selection-merge-btn'
  ) as HTMLButtonElement | null,
  selectionFindReplaceButton: document.getElementById(
    'tag-selection-find-replace-btn'
  ) as HTMLButtonElement | null,
  saveAllButton: document.getElementById('tag-save-all-btn') as HTMLButtonElement | null,
  undoButton: document.getElementById('tag-undo-btn') as HTMLButtonElement | null,
  analyticsTotal: document.getElementById('tag-analytics-total') as HTMLElement | null,
  analyticsUsed: document.getElementById('tag-analytics-used') as HTMLElement | null,
  analyticsUnused: document.getElementById('tag-analytics-unused') as HTMLElement | null,
  analyticsTop: document.getElementById('tag-analytics-top') as HTMLElement | null,
  analyticsCooccurrence: document.getElementById(
    'tag-analytics-cooccurrence'
  ) as HTMLElement | null,
  hierarchyTree: document.getElementById('tag-hierarchy-tree') as HTMLElement | null,
  orphansCount: document.getElementById('tag-orphans-count') as HTMLElement | null,
  orphansList: document.getElementById('tag-orphans-list') as HTMLElement | null,
  orphansPromptCount: document.getElementById('tag-orphans-prompts-count') as HTMLElement | null,
  orphansPromptDetails: document.getElementById(
    'tag-orphans-prompts-details'
  ) as HTMLElement | null,
};

let cachedItems: TagItem[] = [];
let tableKeyboardNavInitialized = false;
let rovingTabindexInitialized = false;
let currentTagFocusIndex = 0;
const liveValidationState = new Map<string, boolean>();
type OrphanPromptDetailsResponse = {
  items: Array<{ id: number; title: string }>;
  count: number;
};

function normalizeSearch(value: string): string {
  return value.trim().toLowerCase();
}

function announceKeyboardNavigation(message: string): void {
  const announcer = document.getElementById('keyboard-navigation-announcer');
  if (!announcer) {
    return;
  }
  announcer.textContent = '';
  requestAnimationFrame(() => {
    announcer.textContent = message;
  });
}

function isTextEditingTarget(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  if (!el) return false;
  return (
    el.tagName === 'INPUT' ||
    el.tagName === 'TEXTAREA' ||
    el.tagName === 'SELECT' ||
    el.isContentEditable
  );
}

/**
 * Initialize roving tabindex pattern for tag list
 * Sets first item's checkbox to tabindex="0" and others to tabindex="-1"
 * Handles arrow key navigation to move focus and update tabindex values
 */
function initializeRovingTabindex(): void {
  if (rovingTabindexInitialized) {
    return;
  }
  rovingTabindexInitialized = true;

  const container = document.getElementById('tags-table-container');
  if (!container) {
    return;
  }

  // Update roving tabindex attributes on all checkboxes in rows
  const updateTabindexAttributes = (): void => {
    const checkboxes = Array.from(
      container.querySelectorAll<HTMLInputElement>('tbody input[type="checkbox"]')
    );
    checkboxes.forEach((checkbox, index) => {
      if (index === currentTagFocusIndex) {
        checkbox.setAttribute('tabindex', '0');
      } else {
        checkbox.setAttribute('tabindex', '-1');
      }
    });
  };

  // Initial setup
  updateTabindexAttributes();

  // Handle arrow key navigation
  container.addEventListener('keydown', (event: Event) => {
    const keyEvent = event as KeyboardEvent;
    const checkboxes = Array.from(
      container.querySelectorAll<HTMLInputElement>('tbody input[type="checkbox"]')
    );

    if (checkboxes.length === 0) {
      return;
    }

    // Check if target is a checkbox or inside a row containing a checkbox
    const target = keyEvent.target as HTMLElement | null;
    const row = target?.closest('tr');
    if (!row) {
      return;
    }

    let newIndex = currentTagFocusIndex;
    let shouldMove = false;

    switch (keyEvent.key) {
      case 'ArrowDown':
      case 'ArrowRight':
        keyEvent.preventDefault();
        newIndex = Math.min(currentTagFocusIndex + 1, checkboxes.length - 1);
        shouldMove = true;
        break;
      case 'ArrowUp':
      case 'ArrowLeft':
        keyEvent.preventDefault();
        newIndex = Math.max(currentTagFocusIndex - 1, 0);
        shouldMove = true;
        break;
      case 'Home':
        keyEvent.preventDefault();
        newIndex = 0;
        shouldMove = true;
        break;
      case 'End':
        keyEvent.preventDefault();
        newIndex = checkboxes.length - 1;
        shouldMove = true;
        break;
    }

    if (shouldMove && newIndex !== currentTagFocusIndex) {
      currentTagFocusIndex = newIndex;
      updateTabindexAttributes();
      checkboxes[newIndex]?.focus();
      const row = checkboxes[newIndex]?.closest('tr');
      const nameInput = row?.querySelector<HTMLInputElement>('input[data-field="name"]');
      announceKeyboardNavigation(
        t('accessibility.navigateTo', { item: nameInput?.value || `Item ${newIndex + 1}` })
      );
    }
  });

  // Update focus index when user clicks a checkbox
  container.addEventListener('click', (event: Event) => {
    const target = event.target as HTMLElement | null;
    const checkbox = target?.closest('input[type="checkbox"]') as HTMLInputElement | null;
    if (checkbox) {
      const checkboxes = Array.from(
        container.querySelectorAll<HTMLInputElement>('tbody input[type="checkbox"]')
      );
      const index = checkboxes.indexOf(checkbox);
      if (index !== -1) {
        currentTagFocusIndex = index;
        updateTabindexAttributes();
      }
    }
  });

  // Update focus index when user tabs to a checkbox
  container.addEventListener(
    'focus',
    (event: Event) => {
      const target = event.target as HTMLElement | null;
      const checkbox = target?.closest('input[type="checkbox"]') as HTMLInputElement | null;
      if (checkbox) {
        const checkboxes = Array.from(
          container.querySelectorAll<HTMLInputElement>('tbody input[type="checkbox"]')
        );
        const index = checkboxes.indexOf(checkbox);
        if (index !== -1) {
          currentTagFocusIndex = index;
          updateTabindexAttributes();
        }
      }
    },
    true
  );
}

function initializeTableFirstCharNavigation(): void {
  if (tableKeyboardNavInitialized) {
    return;
  }
  tableKeyboardNavInitialized = true;

  const typeahead = createTypeahead();

  const container = document.getElementById('tags-table-container');
  const body = elements.tableBody;
  if (!container || !body) {
    return;
  }

  container.addEventListener('keydown', (event) => {
    if (event.metaKey || event.ctrlKey || event.altKey) {
      return;
    }
    if (isTextEditingTarget(event.target)) {
      return;
    }
    if ((event as KeyboardEvent).isComposing || event.key === 'Process') {
      return;
    }
    if (event.key.length !== 1) {
      return;
    }

    const rows = Array.from(body.querySelectorAll<HTMLTableRowElement>('tr'));
    if (rows.length === 0) {
      return;
    }

    const target = event.target as HTMLElement | null;
    const currentRow = target?.closest('tr');
    const currentIndex = currentRow ? rows.indexOf(currentRow) : -1;

    const query = typeahead.pushKey(event.key);
    if (!query) {
      return;
    }

    for (let offset = 1; offset <= rows.length; offset++) {
      const index = (currentIndex + offset + rows.length) % rows.length;
      const row = rows[index];
      if (!row) continue;
      const nameInput = row.querySelector<HTMLInputElement>('input[data-field="name"]');
      const label = (nameInput?.value ?? '').trim();
      if (!label.toLocaleLowerCase().startsWith(query)) {
        continue;
      }

      const checkbox = row.querySelector<HTMLInputElement>(
        'input[type="checkbox"][data-select-id]'
      );
      if (!checkbox) {
        return;
      }

      event.preventDefault();
      checkbox.focus();
      announceKeyboardNavigation(t('accessibility.navigateTo', { item: label }));
      return;
    }
  });

  container.addEventListener('compositionend', (event) => {
    const composed = (event as CompositionEvent).data ?? '';
    const query = typeahead.pushText(composed);
    if (!query) {
      return;
    }

    const rows = Array.from(body.querySelectorAll<HTMLTableRowElement>('tr'));
    if (rows.length === 0) {
      return;
    }
    const active = document.activeElement as HTMLElement | null;
    const currentRow = active?.closest?.('tr') as HTMLTableRowElement | null;
    const currentIndex = currentRow ? rows.indexOf(currentRow) : -1;

    for (let offset = 1; offset <= rows.length; offset++) {
      const index = (currentIndex + offset + rows.length) % rows.length;
      const row = rows[index];
      if (!row) continue;
      const nameInput = row.querySelector<HTMLInputElement>('input[data-field="name"]');
      const label = (nameInput?.value ?? '').trim();
      if (!label.toLocaleLowerCase().startsWith(query)) {
        continue;
      }
      const checkbox = row.querySelector<HTMLInputElement>(
        'input[type="checkbox"][data-select-id]'
      );
      if (!checkbox) return;
      checkbox.focus();
      announceKeyboardNavigation(t('accessibility.navigateTo', { item: label }));
      return;
    }
  });
}

function resetFieldError(inputId: string, errorId: string): void {
  const input = document.getElementById(inputId) as HTMLElement | null;
  const error = document.getElementById(errorId);
  input?.setAttribute('aria-invalid', 'false');
  if (error) {
    error.textContent = '';
  }
}

function setLiveFieldError(inputId: string, errorId: string, message: string): void {
  const input = document.getElementById(inputId) as HTMLElement | null;
  const error = document.getElementById(errorId) as HTMLElement | null;
  const hadError = liveValidationState.get(inputId) === true;

  input?.setAttribute('aria-invalid', 'true');
  if (error) {
    error.textContent = message;
  }
  liveValidationState.set(inputId, true);

  if (!hadError) {
    announce(message, { id: 'validation-announcer', politeness: 'polite' });
  }
}

function clearLiveFieldError(inputId: string, errorId: string): void {
  const input = document.getElementById(inputId) as HTMLElement | null;
  const error = document.getElementById(errorId) as HTMLElement | null;
  const hadError = liveValidationState.get(inputId) === true;

  input?.setAttribute('aria-invalid', 'false');
  if (error) {
    error.textContent = '';
  }
  liveValidationState.set(inputId, false);

  if (hadError) {
    announce(t('validation.fieldValid') || 'Field is valid.', {
      id: 'validation-announcer',
      politeness: 'polite',
    });
  }
}

function attachRequiredLiveValidation(
  input: HTMLInputElement | null,
  inputId: string,
  errorId: string,
  message: string
): void {
  if (!input) return;

  input.addEventListener('blur', () => {
    if (!input.value.trim()) {
      setLiveFieldError(inputId, errorId, message);
    } else {
      clearLiveFieldError(inputId, errorId);
    }
  });

  input.addEventListener('input', () => {
    if (liveValidationState.get(inputId) !== true) {
      return;
    }
    if (input.value.trim()) {
      clearLiveFieldError(inputId, errorId);
    }
  });
}

function attachFileRequiredLiveValidation(
  input: HTMLInputElement | null,
  inputId: string,
  errorId: string,
  message: string
): void {
  if (!input) return;
  input.addEventListener('change', () => {
    const file = input.files?.[0];
    if (!file) {
      setLiveFieldError(inputId, errorId, message);
    } else {
      clearLiveFieldError(inputId, errorId);
    }
  });
}

function addFieldError(
  errors: FormValidationError[],
  inputId: string,
  errorId: string,
  message: string
): void {
  const input = document.getElementById(inputId) as HTMLElement | null;
  const error = document.getElementById(errorId);
  if (input) {
    const existing =
      input
        .getAttribute('aria-describedby')
        ?.split(/\s+/)
        .map((s) => s.trim())
        .filter(Boolean) ?? [];
    const next = Array.from(new Set([...existing, errorId]));
    input.setAttribute('aria-describedby', next.join(' '));
  }
  input?.setAttribute('aria-invalid', 'true');
  if (error) {
    error.textContent = message;
  }
  errors.push({ inputId, errorId, message });
}

function resetErrorSummary(summaryId: string): void {
  const summary = document.getElementById(summaryId);
  if (!summary) return;
  summary.textContent = '';
  summary.style.display = 'none';
}

function renderErrorSummary(summaryId: string, errors: FormValidationError[]): void {
  if (errors.length === 0) {
    return;
  }

  const summary = document.getElementById(summaryId);
  if (!summary) {
    const firstInput = document.getElementById(errors[0]?.inputId ?? '') as HTMLElement | null;
    firstInput?.focus();
    return;
  }

  summary.textContent = '';
  const header = document.createElement('p');
  header.className = 'error-banner-header';
  header.textContent =
    tUnsafe('validation.errorSummaryHeader') || 'Please correct the following errors:';
  summary.appendChild(header);

  const list = document.createElement('ul');
  list.className = 'error-banner-list';
  errors.forEach((error) => {
    const item = document.createElement('li');
    const link = document.createElement('a');
    link.href = `#${error.inputId}`;
    link.className = 'underline';
    link.textContent = error.message;
    link.addEventListener('click', (event) => {
      event.preventDefault();
      const target = document.getElementById(error.inputId) as HTMLElement | null;
      target?.focus();
    });
    item.appendChild(link);
    list.appendChild(item);
  });
  summary.appendChild(list);
  summary.style.display = 'block';

  // Per plan T-ACC023: focus the first invalid field after rendering the summary.
  const firstInput = document.getElementById(errors[0]?.inputId ?? '') as HTMLElement | null;
  if (firstInput) {
    firstInput.focus();
  } else {
    summary.focus();
  }
}

function resolveTagInputs(rawTags: string): string[] | null {
  const tokens = rawTags
    .split(',')
    .map((tag) => tag.trim())
    .filter((tag) => tag.length > 0);
  if (tokens.length === 0) {
    return null;
  }
  const resolved: string[] = [];
  for (const token of tokens) {
    if (/^\d+$/.test(token)) {
      const id = Number(token);
      const match = cachedItems.find((item) => item.id === id);
      if (!match) {
        showNotification(tUnsafe('management.idNotFound', { id }), 'error');
        return null;
      }
      resolved.push(match.name);
    } else {
      resolved.push(token);
    }
  }
  return resolved;
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

function filterItems(items: TagItem[], query: string): TagItem[] {
  if (!query) {
    return items;
  }
  return items.filter((item) => item.name.toLowerCase().includes(query));
}

function buildTagPayload(row: HTMLTableRowElement): Record<string, unknown> {
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

function renderRows(items: TagItem[]): void {
  if (!elements.tableBody) {
    return;
  }
  elements.tableBody.innerHTML = '';

  const emptyState = document.getElementById('tags-empty-state');
  const tableContainer = document.getElementById('tags-table-container');

  // Show/hide empty state
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

    row.innerHTML = `
      <td class="py-2 pr-4">
        <input type="checkbox" id="checkbox-${item.id}" data-select-id="${item.id}" aria-label="${selectLabel} #${item.id}" tabindex="-1" />
      </td>
      <td class="py-2 pr-4 text-gray-600 dark:text-gray-400">#${item.id}</td>
      <td class="py-2 pr-4">
        <input id="name-input-${item.id}" data-field="name" aria-label="${nameLabel}" class="w-full px-2 py-1 border border-gray-300 rounded dark:border-gray-600" value="${item.name}" />
      </td>
      <td class="py-2 pr-4">
        <input id="desc-input-${item.id}" data-field="description" aria-label="${descriptionLabel}" class="w-full px-2 py-1 border border-gray-300 rounded dark:border-gray-600" value="${item.description ?? ''}" />
      </td>
      <td class="py-2 pr-4">
        <div class="flex items-center gap-2">
          <input id="color-input-${item.id}" data-field="color" aria-label="${colorLabel}" class="w-full px-2 py-1 border border-gray-300 rounded dark:border-gray-600" value="${item.color ?? ''}" />
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
        <select id="parent-select-${item.id}" data-field="parent_tag_id" aria-label="${parentLabel}" class="w-36 px-2 py-1 border border-gray-300 rounded dark:border-gray-600">
          ${renderParentOptions(item.id, item.parent_tag_id ?? null, parentNoneLabel)}
        </select>
      </td>
      <td class="py-2 pr-4 text-gray-600 dark:text-gray-400">${item.usage_count}</td>
      <td class="py-2 pr-4">
        <div class="flex items-center gap-2">
          <button id="save-btn-${item.id}" data-action="save" class="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700">${saveLabel}</button>
          <button id="delete-btn-${item.id}" data-action="delete" class="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700">${deleteLabel}</button>
        </div>
      </td>
    `;

    // Apply focus styles using event listeners
    const checkbox = row.querySelector<HTMLInputElement>('input[type="checkbox"]');
    const nameInput = row.querySelector<HTMLInputElement>('input[data-field="name"]');
    const descInput = row.querySelector<HTMLInputElement>('input[data-field="description"]');
    const colorInput = row.querySelector<HTMLInputElement>('input[data-field="color"]');
    const colorPickerInput = row.querySelector<HTMLInputElement>('input[data-color-picker]');
    const parentSelect = row.querySelector<HTMLSelectElement>('select[data-field="parent_tag_id"]');
    const saveBtn = row.querySelector<HTMLButtonElement>('[data-action="save"]');
    const deleteBtn = row.querySelector<HTMLButtonElement>('[data-action="delete"]');

    // Add focus styles to all interactive elements
    if (checkbox) applyFocusStyles(checkbox);
    if (nameInput) applyFocusStyles(nameInput);
    if (descInput) applyFocusStyles(descInput);
    if (colorInput) applyFocusStyles(colorInput);
    if (colorPickerInput) applyFocusStyles(colorPickerInput);
    if (parentSelect) applyFocusStyles(parentSelect);
    if (saveBtn) applyFocusStyles(saveBtn);
    if (deleteBtn) applyFocusStyles(deleteBtn, '#ef4444');

    saveBtn?.addEventListener('click', () => {
      void saveTag(item.id, row);
    });

    if (deleteBtn) {
      deleteBtn.addEventListener('click', () => {
        void deleteTag(item.id);
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

    elements.tableBody.appendChild(row);
  }

  // Setup scroll indicators for table container
  setupScrollIndicators(tableContainer);
  initializeTableFirstCharNavigation();

  // Reset and reinitialize roving tabindex pattern
  rovingTabindexInitialized = false;
  currentTagFocusIndex = 0;
  initializeRovingTabindex();
}

function parseIdList(value: string): number[] {
  return value
    .split(',')
    .map((id) => Number(id.trim()))
    .filter((id) => Number.isFinite(id) && id > 0);
}

async function loadTags(): Promise<void> {
  try {
    const data = await apiFetch<TagListResponse>('/api/tags/manage');
    cachedItems = data.items ?? [];
    populateCreateParentSelect();
    applySearchFilter();
    renderHierarchyTree();
    await loadAnalytics();
    await loadOrphans();
  } catch (error) {
    handleError(error, 'Failed to load tags');
  }
}

function applySearchFilter(): void {
  const query = normalizeSearch(elements.searchInput?.value ?? '');
  renderRows(filterItems(cachedItems, query));
}

async function createTag(event: Event): Promise<void> {
  event.preventDefault();
  if (!elements.createName) {
    return;
  }
  resetFieldError('tag-create-name', 'tag-create-name-error');
  resetErrorSummary('tag-create-error-summary');
  const validationErrors: FormValidationError[] = [];

  const payload = {
    name: elements.createName.value.trim(),
    description: elements.createDescription?.value.trim() || undefined,
    color: elements.createColor?.value.trim() || undefined,
    parent_tag_id: elements.createParent?.value ? Number(elements.createParent.value) : undefined,
  };

  if (!payload.name) {
    addFieldError(
      validationErrors,
      'tag-create-name',
      'tag-create-name-error',
      tUnsafe('management.nameRequired')
    );
    renderErrorSummary('tag-create-error-summary', validationErrors);
    return;
  }

  try {
    await apiFetch('/api/tags', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    showNotification(tUnsafe('management.createSuccess'), 'success');
    if (elements.createForm) {
      elements.createForm.reset();
    }
    await loadTags();
  } catch (error) {
    handleError(error, 'Failed to create tag');
  }
}

async function saveTag(tagId: number, row: HTMLTableRowElement): Promise<void> {
  const payload = buildTagPayload(row);
  try {
    await apiFetch(`/api/tags/${tagId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
    showNotification(tUnsafe('management.saveSuccess'), 'success');
    await loadTags();
  } catch (error) {
    handleError(error, 'Failed to update tag');
  }
}

async function deleteTag(tagId: number): Promise<void> {
  const confirmed = await confirmAsync({
    title: t('actions.confirmDelete') || 'Confirm',
    message: tUnsafe('management.deleteConfirm'),
    confirmLabel: t('actions.delete') || 'Delete',
    cancelLabel: t('actions.cancel') || 'Cancel',
  });
  if (!confirmed) {
    return;
  }
  try {
    await apiFetch(`/api/tags/${tagId}?confirm=true`, {
      method: 'DELETE',
    });
    showNotification(tUnsafe('management.deleteSuccess'), 'success');
    await loadTags();

    // Restore focus after delete completes
    restoreFocusAfterDelete();
  } catch (error) {
    if (error instanceof APIRequestError && error.status === 422) {
      const forceConfirmed = await confirmAsync({
        title: t('actions.confirmDelete') || 'Confirm',
        message: tUnsafe('management.forceDeleteConfirm'),
        confirmLabel: t('actions.delete') || 'Delete',
        cancelLabel: t('actions.cancel') || 'Cancel',
      });
      if (!forceConfirmed) {
        return;
      }
      try {
        await apiFetch(`/api/tags/${tagId}?confirm=true&force=true`, {
          method: 'DELETE',
        });
        showNotification(tUnsafe('management.deleteSuccess'), 'success');
        await loadTags();

        // Restore focus after delete completes
        restoreFocusAfterDelete();
        return;
      } catch (forceError) {
        handleError(forceError, 'Failed to delete tag');
        return;
      }
    }
    handleError(error, 'Failed to delete tag');
  }
}

async function mergeTags(): Promise<void> {
  resetFieldError('tag-merge-target', 'tag-merge-target-error');
  resetFieldError('tag-merge-sources', 'tag-merge-sources-error');
  resetErrorSummary('tag-merge-error-summary');
  const validationErrors: FormValidationError[] = [];
  const targetId = Number(elements.mergeTarget?.value || '');
  const sourceIds = parseIdList(elements.mergeSources?.value || '');
  if (!targetId) {
    addFieldError(
      validationErrors,
      'tag-merge-target',
      'tag-merge-target-error',
      tUnsafe('management.mergeRequireIds')
    );
  }
  if (sourceIds.length === 0) {
    addFieldError(
      validationErrors,
      'tag-merge-sources',
      'tag-merge-sources-error',
      tUnsafe('management.mergeRequireIds')
    );
  }
  if (validationErrors.length > 0) {
    renderErrorSummary('tag-merge-error-summary', validationErrors);
    return;
  }
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
    await apiFetch('/api/tags/merge', {
      method: 'POST',
      body: JSON.stringify({ target_id: targetId, source_ids: sourceIds, confirm: true }),
    });
    showNotification(tUnsafe('management.mergeSuccess'), 'success');
    await loadTags();
  } catch (error) {
    handleError(error, 'Failed to merge tags');
  }
}

async function findReplaceTags(): Promise<void> {
  resetFieldError('tag-find', 'tag-find-error');
  resetFieldError('tag-replace', 'tag-replace-error');
  resetErrorSummary('tag-find-replace-error-summary');
  const validationErrors: FormValidationError[] = [];
  const findValue = elements.findInput?.value.trim() || '';
  const replaceValue = elements.replaceInput?.value.trim() || '';
  if (!findValue) {
    addFieldError(
      validationErrors,
      'tag-find',
      'tag-find-error',
      tUnsafe('management.findReplaceRequired')
    );
  }
  if (!replaceValue) {
    addFieldError(
      validationErrors,
      'tag-replace',
      'tag-replace-error',
      tUnsafe('management.findReplaceRequired')
    );
  }
  if (validationErrors.length > 0) {
    renderErrorSummary('tag-find-replace-error-summary', validationErrors);
    return;
  }
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
    await apiFetch('/api/tags/find-replace', {
      method: 'POST',
      body: JSON.stringify({ find: findValue, replace: replaceValue, confirm: true }),
    });
    showNotification(tUnsafe('management.replaceSuccess'), 'success');
    await loadTags();
  } catch (error) {
    handleError(error, 'Failed to replace tag');
  }
}

async function bulkDeleteTags(): Promise<void> {
  resetFieldError('tag-bulk-delete-ids', 'tag-bulk-delete-ids-error');
  resetErrorSummary('tag-bulk-delete-error-summary');
  const validationErrors: FormValidationError[] = [];
  const ids = parseIdList(elements.bulkDeleteIds?.value || '');
  if (ids.length === 0) {
    addFieldError(
      validationErrors,
      'tag-bulk-delete-ids',
      'tag-bulk-delete-ids-error',
      tUnsafe('management.bulkDeleteRequireIds')
    );
    renderErrorSummary('tag-bulk-delete-error-summary', validationErrors);
    return;
  }
  const confirmed = await confirmAsync({
    title: t('actions.confirm') || 'Confirm',
    message: tUnsafe('management.bulkDeleteConfirm'),
    confirmLabel: t('actions.bulkDelete') || 'Delete Selected',
    cancelLabel: t('actions.cancel') || 'Cancel',
  });
  if (!confirmed) {
    return;
  }
  const force = elements.bulkDeleteForce?.checked ?? false;
  try {
    await apiFetch('/api/tags/bulk-delete', {
      method: 'POST',
      body: JSON.stringify({ ids, force, confirm: true }),
    });
    showNotification(tUnsafe('management.bulkDeleteSuccess'), 'success');
    await loadTags();
  } catch (error) {
    handleError(error, 'Failed to delete tags');
  }
}

async function exportTags(): Promise<void> {
  try {
    const data = await apiFetch<{ items: TagItem[] }>('/api/tags/export');
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

async function importTags(): Promise<void> {
  resetFieldError('tag-import-file', 'tag-import-file-error');
  resetErrorSummary('tag-import-error-summary');
  const validationErrors: FormValidationError[] = [];
  const file = elements.importFile?.files?.[0];
  if (!file) {
    addFieldError(
      validationErrors,
      'tag-import-file',
      'tag-import-file-error',
      tUnsafe('management.importSelectFile')
    );
    renderErrorSummary('tag-import-error-summary', validationErrors);
    return;
  }
  try {
    const text = await file.text();
    const parsed = JSON.parse(text) as { items?: TagItem[] };
    const items = (parsed.items ?? []).map((item) => ({
      name: item.name,
      description: item.description ?? undefined,
      color: item.color ?? undefined,
      parent_tag_id: item.parent_tag_id ?? undefined,
    }));
    await apiFetch('/api/tags/import', {
      method: 'POST',
      body: JSON.stringify({ items }),
    });
    showNotification(tUnsafe('management.importSuccess'), 'success');
    await loadTags();
  } catch (error) {
    handleError(error, 'Failed to import tags');
  }
}

function renderParentOptions(
  currentId: number,
  selectedId: number | null,
  parentNoneLabel: string
): string {
  const options = [`<option value="">${parentNoneLabel}</option>`];
  cachedItems.forEach((item) => {
    if (item.id === currentId) {
      return;
    }
    const selected = selectedId === item.id ? 'selected' : '';
    options.push(`<option value="${item.id}" ${selected}>${item.name}</option>`);
  });
  return options.join('');
}

function populateCreateParentSelect(): void {
  if (!elements.createParent) {
    return;
  }
  elements.createParent.innerHTML = `<option value="">${tUnsafe('management.parentNone')}</option>`;
  cachedItems.forEach((item) => {
    const option = document.createElement('option');
    option.value = String(item.id);
    option.textContent = item.name;
    elements.createParent?.appendChild(option);
  });
}

function renderHierarchyTree(): void {
  if (!elements.hierarchyTree) {
    return;
  }
  elements.hierarchyTree.innerHTML = '';

  const byParent: Record<string, TagItem[]> = {};
  cachedItems.forEach((item) => {
    const key = item.parent_tag_id ? String(item.parent_tag_id) : 'root';
    if (!byParent[key]) {
      byParent[key] = [];
    }
    byParent[key].push(item);
  });

  Object.values(byParent).forEach((items) => items.sort((a, b) => a.name.localeCompare(b.name)));

  const rootItems = byParent['root'] ?? [];
  if (rootItems.length === 0) {
    elements.hierarchyTree.textContent = tUnsafe('management.noHierarchyDefined');
    return;
  }

  const container = document.createElement('ul');
  container.className = 'space-y-2';
  rootItems.forEach((item) => {
    container.appendChild(buildNode(item, byParent));
  });
  elements.hierarchyTree.appendChild(container);

  // Setup scroll indicators for hierarchy tree
  setupScrollIndicators(elements.hierarchyTree);
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

function getSelectedIds(): number[] {
  if (!elements.tableBody) {
    return [];
  }
  const checkboxes = elements.tableBody.querySelectorAll<HTMLInputElement>('input[data-select-id]');
  return Array.from(checkboxes)
    .filter((checkbox) => checkbox.checked)
    .map((checkbox) => Number(checkbox.dataset.selectId))
    .filter((value) => Number.isFinite(value));
}

async function mergeSelected(): Promise<void> {
  const ids = getSelectedIds();
  if (ids.length < 2) {
    showNotification(tUnsafe('management.mergeSelectedRequire'), 'error');
    return;
  }
  const targetId = ids[0];
  const sourceIds = ids.slice(1);
  const confirmed = await confirmAsync({
    title: t('actions.confirm') || 'Confirm',
    message: tUnsafe('management.mergeSelectedConfirm'),
    confirmLabel: t('actions.mergeSelected') || t('actions.merge') || 'Merge',
    cancelLabel: t('actions.cancel') || 'Cancel',
  });
  if (!confirmed) {
    return;
  }
  try {
    await apiFetch('/api/tags/merge', {
      method: 'POST',
      body: JSON.stringify({ target_id: targetId, source_ids: sourceIds, confirm: true }),
    });
    showNotification(tUnsafe('management.mergeSuccess'), 'success');
    await loadTags();
  } catch (error) {
    handleError(error, 'Failed to merge tags');
  }
}

async function saveAllTags(): Promise<void> {
  if (!elements.tableBody) {
    return;
  }
  const rows = Array.from(elements.tableBody.querySelectorAll<HTMLTableRowElement>('tr'));
  if (rows.length === 0) {
    showNotification(tUnsafe('management.noRows'), 'error');
    return;
  }

  let failed = 0;
  for (const row of rows) {
    const idValue = Number(row.dataset.id || '');
    if (!Number.isFinite(idValue)) {
      continue;
    }
    const payload = buildTagPayload(row);
    try {
      await apiFetch(`/api/tags/${idValue}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
      });
    } catch (error) {
      failed += 1;
      console.error(error);
    }
  }

  if (failed === 0) {
    showNotification(tUnsafe('management.saveSuccess'), 'success');
  } else {
    showNotification(tUnsafe('messages.error'), 'error');
  }

  await loadTags();
}

async function findReplaceSelected(): Promise<void> {
  const ids = getSelectedIds();
  if (ids.length !== 1) {
    showNotification(tUnsafe('management.replaceSelectedRequireOne'), 'error');
    return;
  }
  const selected = cachedItems.find((item) => item.id === ids[0]);
  if (!selected) {
    showNotification(tUnsafe('management.replaceSelectedNotFound'), 'error');
    return;
  }
  const replaceValue = window.prompt(tUnsafe('management.replacePrompt', { name: selected.name }));
  if (!replaceValue) {
    return;
  }
  const confirmed = await confirmAsync({
    title: t('actions.confirm') || 'Confirm',
    message: tUnsafe('management.replaceConfirm'),
    confirmLabel: t('actions.findReplaceSelected') || t('actions.replace') || 'Replace',
    cancelLabel: t('actions.cancel') || 'Cancel',
  });
  if (!confirmed) {
    return;
  }
  try {
    await apiFetch('/api/tags/find-replace', {
      method: 'POST',
      body: JSON.stringify({ find: selected.name, replace: replaceValue, confirm: true }),
    });
    showNotification(tUnsafe('management.replaceSuccess'), 'success');
    await loadTags();
  } catch (error) {
    handleError(error, 'Failed to replace tag');
  }
}

async function undoLastOperation(): Promise<void> {
  try {
    await apiFetch('/api/tags/undo', {
      method: 'POST',
    });
    showNotification(tUnsafe('management.undoSuccess'), 'success');
    await loadTags();
  } catch (error) {
    handleError(error, 'No operation to undo.');
  }
}

async function loadAnalytics(): Promise<void> {
  try {
    const data = await apiFetch<{
      total: number;
      used: number;
      unused: number;
      top: Array<{ name: string; count: number }>;
      co_occurrence: Array<{ tag_a: string; tag_b: string; count: number }>;
    }>('/api/tags/analytics');
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

async function loadOrphans(): Promise<void> {
  try {
    const data = await apiFetch<TagListResponse>('/api/tags/orphans');
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
    const data = await apiFetch<{ prompt_ids: number[]; count: number }>(
      '/api/tags/orphan-prompts'
    );
    if (elements.orphansPromptCount) {
      elements.orphansPromptCount.textContent = String(data.count ?? 0);
    }
    if (elements.orphansPromptDetails) {
      await renderPromptDetails(data.prompt_ids ?? [], elements.orphansPromptDetails);
      setupScrollIndicators(elements.orphansPromptDetails);
    }
  } catch (error) {
    handleError(error, 'Failed to load prompts without tags');
  }
}

async function renderPromptDetails(promptIds: number[], container: HTMLElement): Promise<void> {
  container.innerHTML = '';
  if (promptIds.length === 0) {
    return;
  }

  let details: OrphanPromptDetailsResponse | null = null;
  try {
    details = await apiFetch<OrphanPromptDetailsResponse>('/api/tags/orphan-prompts/details');
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
      void assignTagsToPrompt(promptId, tags);
    });
  });
}

async function assignTagsToPrompt(promptId: number, tags: string[]): Promise<void> {
  try {
    await apiFetch('/api/tags/bulk-update', {
      method: 'POST',
      body: JSON.stringify({ prompt_ids: [promptId], add: tags, remove: [], confirm: true }),
    });
    showNotification(tUnsafe('management.bulkUpdateSuccess'), 'success');
    await loadTags();
  } catch (error) {
    handleError(error, 'Failed to apply tags');
  }
}

function handleError(error: unknown, fallback: string): void {
  if (error instanceof APIRequestError) {
    showNotification(error.message, 'error');
    return;
  }
  console.error(error);
  showNotification(fallback, 'error');
}

function init(): void {
  initSecondaryNav({ component: 'manage-tags', requireAuth: true });

  // Initialize enhanced color picker
  try {
    initializeColorPicker({
      containerId: 'tag-create-color-picker-container',
      colorInputId: 'tag-create-color',
      colorPickerId: 'tag-create-color-picker',
      initialColor: '#3B82F6',
    });
  } catch (error) {
    console.error('Failed to initialize color picker:', error);
  }

  if (elements.searchInput) {
    elements.searchInput.addEventListener('input', applySearchFilter);
  }
  // Live validation (T-ACC025) for the main form inputs.
  attachRequiredLiveValidation(
    elements.createName,
    'tag-create-name',
    'tag-create-name-error',
    tUnsafe('management.nameRequired')
  );
  attachRequiredLiveValidation(
    elements.mergeTarget,
    'tag-merge-target',
    'tag-merge-target-error',
    tUnsafe('management.mergeRequireIds')
  );
  attachRequiredLiveValidation(
    elements.mergeSources,
    'tag-merge-sources',
    'tag-merge-sources-error',
    tUnsafe('management.mergeRequireIds')
  );
  attachRequiredLiveValidation(
    elements.findInput,
    'tag-find',
    'tag-find-error',
    tUnsafe('management.findReplaceRequired')
  );
  attachRequiredLiveValidation(
    elements.replaceInput,
    'tag-replace',
    'tag-replace-error',
    tUnsafe('management.findReplaceRequired')
  );
  attachRequiredLiveValidation(
    elements.bulkDeleteIds,
    'tag-bulk-delete-ids',
    'tag-bulk-delete-ids-error',
    tUnsafe('management.bulkDeleteRequireIds')
  );
  attachFileRequiredLiveValidation(
    elements.importFile,
    'tag-import-file',
    'tag-import-file-error',
    tUnsafe('management.importSelectFile')
  );
  if (elements.createForm) {
    elements.createForm.addEventListener('submit', (event) => {
      void createTag(event);
    });
  }
  elements.mergeButton?.addEventListener('click', () => {
    void mergeTags();
  });
  elements.findReplaceButton?.addEventListener('click', () => {
    void findReplaceTags();
  });
  elements.bulkDeleteButton?.addEventListener('click', () => {
    void bulkDeleteTags();
  });
  elements.exportButton?.addEventListener('click', () => {
    void exportTags();
  });
  elements.importButton?.addEventListener('click', () => {
    void importTags();
  });
  elements.selectionMergeButton?.addEventListener('click', () => {
    void mergeSelected();
  });
  elements.selectionFindReplaceButton?.addEventListener('click', () => {
    void findReplaceSelected();
  });
  elements.saveAllButton?.addEventListener('click', () => {
    void saveAllTags();
  });
  elements.undoButton?.addEventListener('click', () => {
    void undoLastOperation();
  });

  // Apply focus styles to all form inputs and selects on the page
  // This ensures proper focus visibility for keyboard navigation users
  document
    .querySelectorAll<
      HTMLInputElement | HTMLSelectElement
    >('input[type="text"], input[type="number"], input[type="color"], input[type="checkbox"], select')
    .forEach((el) => {
      if (el.id !== 'tag-import-file' && el.id !== 'tag-create-color-picker') {
        applyFocusStyles(el);
      }
    });

  // Apply focus styles to all buttons on the page
  document.querySelectorAll<HTMLButtonElement>('button').forEach((btn) => {
    // Determine ring color based on button type
    const ringColor =
      btn.classList.contains('bg-red-600') || btn.classList.contains('bg-red-700')
        ? '#ef4444'
        : '#3b82f6';
    applyFocusStyles(btn, ringColor);
  });

  // Apply focus styles to the file input specifically (since it's often hidden)
  if (elements.importFile) {
    applyFocusStyles(elements.importFile);
  }

  // Apply focus styles to the color picker (despite being hidden initially)
  if (elements.createColorPicker) {
    applyFocusStyles(elements.createColorPicker);
  }

  void loadTags();
}

/**
 * Restores focus after a tag is deleted from the table
 * Focuses the next row's delete button, or previous row's button, or the table body
 */
function restoreFocusAfterDelete(): void {
  if (!elements.tableBody) return;

  // Find the row that would have been after the deleted item
  const rows = Array.from(elements.tableBody.querySelectorAll<HTMLTableRowElement>('tr'));
  if (rows.length === 0) {
    // Table is empty, focus the empty state or search input
    const emptyState = document.getElementById('tags-empty-state');
    if (emptyState && !emptyState.classList.contains('hidden')) {
      const createBtn = emptyState.querySelector<HTMLButtonElement>('button');
      if (createBtn) {
        createBtn.focus();
        announceToScreenReader('Tag deleted. No tags remaining.', 'polite');
        return;
      }
    }
    // Focus search input if available
    if (elements.searchInput) {
      elements.searchInput.focus();
      announceToScreenReader('Tag deleted. Table is now empty.', 'polite');
    }
    return;
  }

  // Focus the first row's delete button
  const firstRow = rows[0];
  if (firstRow) {
    const deleteBtn = firstRow.querySelector<HTMLElement>('[data-action="delete"]');
    if (deleteBtn) {
      deleteBtn.focus();
      announceToScreenReader('Tag deleted. Focus moved to next tag.', 'polite');
      return;
    }
  }

  // Fall back to table body
  if (elements.tableBody) {
    (elements.tableBody as HTMLElement).setAttribute('tabindex', '-1');
    (elements.tableBody as HTMLElement).focus();
    announceToScreenReader('Tag deleted.', 'polite');
  }
}

initI18n(() => {
  try {
    updateStaticTranslations();
    init();
  } catch (error) {
    console.error('Failed to initialize tag management', error);
  }
});
