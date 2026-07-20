/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import '../css/tailwind-globals.css';
import { apiFetch, APIRequestError, handleApiError } from '@/utils/api';
import { initI18n, t, tUnsafe, updateStaticTranslations } from '@/utils/i18n';
import { initializeColorPicker } from '@/utils/color-picker';
import { setupScrollIndicators } from '@/utils/dom';
import { showNotification } from '@/utils/notifications';
import { createTypeahead } from '@/utils/typeahead';
import { announce } from '@/utils/a11y';
import { confirmAsync } from '@/utils/dialogs';
import { announceToScreenReader } from '@/utils/focus-management';
import { initSecondaryNav } from '@/utils/secondary-nav';

type CategoryItem = {
  id: number;
  name: string;
  description?: string | null;
  color?: string | null;
  sort_order?: number | null;
  usage_count: number;
};

type CategoryListResponse = {
  items: CategoryItem[];
};
type FormValidationError = {
  inputId: string;
  errorId: string;
  message: string;
};

const elements = {
  tableBody: document.getElementById('categories-table-body') as HTMLTableSectionElement | null,
  searchInput: document.getElementById('category-search') as HTMLInputElement | null,
  createForm: document.getElementById('category-create-form') as HTMLFormElement | null,
  createName: document.getElementById('category-create-name') as HTMLInputElement | null,
  createDescription: document.getElementById(
    'category-create-description'
  ) as HTMLInputElement | null,
  createColor: document.getElementById('category-create-color') as HTMLInputElement | null,
  createColorPicker: document.getElementById(
    'category-create-color-picker'
  ) as HTMLInputElement | null,
  mergeTarget: document.getElementById('category-merge-target') as HTMLInputElement | null,
  mergeSources: document.getElementById('category-merge-sources') as HTMLInputElement | null,
  mergeButton: document.getElementById('category-merge-btn') as HTMLButtonElement | null,
  findInput: document.getElementById('category-find') as HTMLInputElement | null,
  replaceInput: document.getElementById('category-replace') as HTMLInputElement | null,
  findReplaceButton: document.getElementById(
    'category-find-replace-btn'
  ) as HTMLButtonElement | null,
  bulkDeleteIds: document.getElementById('category-bulk-delete-ids') as HTMLInputElement | null,
  bulkDeleteForce: document.getElementById('category-bulk-delete-force') as HTMLInputElement | null,
  bulkDeleteButton: document.getElementById('category-bulk-delete-btn') as HTMLButtonElement | null,
  exportButton: document.getElementById('category-export-btn') as HTMLButtonElement | null,
  importFile: document.getElementById('category-import-file') as HTMLInputElement | null,
  importButton: document.getElementById('category-import-btn') as HTMLButtonElement | null,
  selectionMergeButton: document.getElementById(
    'category-selection-merge-btn'
  ) as HTMLButtonElement | null,
  selectionFindReplaceButton: document.getElementById(
    'category-selection-find-replace-btn'
  ) as HTMLButtonElement | null,
  saveAllButton: document.getElementById('category-save-all-btn') as HTMLButtonElement | null,
  undoButton: document.getElementById('category-undo-btn') as HTMLButtonElement | null,
  analyticsTotal: document.getElementById('category-analytics-total') as HTMLElement | null,
  analyticsUsed: document.getElementById('category-analytics-used') as HTMLElement | null,
  analyticsUnused: document.getElementById('category-analytics-unused') as HTMLElement | null,
  analyticsTop: document.getElementById('category-analytics-top') as HTMLElement | null,
  orphansCount: document.getElementById('category-orphans-count') as HTMLElement | null,
  orphansDetails: document.getElementById('category-orphans-details') as HTMLElement | null,
  unusedCount: document.getElementById('category-unused-count') as HTMLElement | null,
  unusedList: document.getElementById('category-unused-list') as HTMLElement | null,
};

let cachedItems: CategoryItem[] = [];
let tableKeyboardNavInitialized = false;
let rovingTabindexInitialized = false;
let currentCategoryFocusIndex = 0;
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
 * Initialize roving tabindex pattern for category list
 * Sets first item's checkbox to tabindex="0" and others to tabindex="-1"
 * Handles arrow key navigation to move focus and update tabindex values
 */
function initializeRovingTabindex(): void {
  if (rovingTabindexInitialized) {
    return;
  }
  rovingTabindexInitialized = true;

  const container = document.getElementById('categories-table-container');
  if (!container) {
    return;
  }

  // Update roving tabindex attributes on all checkboxes in rows
  const updateTabindexAttributes = (): void => {
    const checkboxes = Array.from(
      container.querySelectorAll<HTMLInputElement>('tbody input[type="checkbox"]')
    );
    checkboxes.forEach((checkbox, index) => {
      if (index === currentCategoryFocusIndex) {
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

    let newIndex = currentCategoryFocusIndex;
    let shouldMove = false;

    switch (keyEvent.key) {
      case 'ArrowDown':
      case 'ArrowRight':
        keyEvent.preventDefault();
        newIndex = Math.min(currentCategoryFocusIndex + 1, checkboxes.length - 1);
        shouldMove = true;
        break;
      case 'ArrowUp':
      case 'ArrowLeft':
        keyEvent.preventDefault();
        newIndex = Math.max(currentCategoryFocusIndex - 1, 0);
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

    if (shouldMove && newIndex !== currentCategoryFocusIndex) {
      currentCategoryFocusIndex = newIndex;
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
        currentCategoryFocusIndex = index;
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
          currentCategoryFocusIndex = index;
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

  const container = document.getElementById('categories-table-container');
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

function resolveCategoryInput(rawCategory: string): string | null {
  const trimmed = rawCategory.trim();
  if (!trimmed) {
    return null;
  }
  if (/^\d+$/.test(trimmed)) {
    const id = Number(trimmed);
    const match = cachedItems.find((item) => item.id === id);
    if (!match) {
      showNotification(tUnsafe('management.idNotFound', { id }), 'error');
      return null;
    }
    return match.name;
  }
  return trimmed;
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

function filterItems(items: CategoryItem[], query: string): CategoryItem[] {
  if (!query) {
    return items;
  }
  return items.filter((item) => item.name.toLowerCase().includes(query));
}

function buildCategoryPayload(row: HTMLTableRowElement): Record<string, unknown> {
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

function renderRows(items: CategoryItem[]): void {
  if (!elements.tableBody) {
    return;
  }
  elements.tableBody.innerHTML = '';

  const emptyState = document.getElementById('categories-empty-state');
  const tableContainer = document.getElementById('categories-table-container');

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
  const colorLabel = tUnsafe('management.color');
  const nameLabel = tUnsafe('management.name');
  const descriptionLabel = tUnsafe('management.description');
  const selectLabel = tUnsafe('management.select');

  for (const item of items) {
    const row = document.createElement('tr');
    row.className = 'border-b border-gray-100 category-item';
    row.setAttribute('role', 'option');
    row.dataset.id = String(item.id);

    row.innerHTML = `
      <td class="py-2 pr-4">
        <input type="checkbox" data-select-id="${item.id}" aria-label="${selectLabel} #${item.id}" tabindex="-1" />
      </td>
      <td class="py-2 pr-4 text-gray-600 dark:text-gray-400">#${item.id}</td>
      <td class="py-2 pr-4">
        <input data-field="name" aria-label="${nameLabel}" class="w-full px-2 py-1 border border-gray-300 rounded dark:border-gray-600" value="${item.name}" />
      </td>
      <td class="py-2 pr-4">
        <input data-field="description" aria-label="${descriptionLabel}" class="w-full px-2 py-1 border border-gray-300 rounded dark:border-gray-600" value="${item.description ?? ''}" />
      </td>
      <td class="py-2 pr-4">
        <div class="flex items-center gap-2">
          <input data-field="color" aria-label="${colorLabel}" class="w-full px-2 py-1 border border-gray-300 rounded dark:border-gray-600" value="${item.color ?? ''}" />
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
          <button data-action="save" class="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700">${saveLabel}</button>
          <button data-action="delete" class="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700">${deleteLabel}</button>
        </div>
      </td>
    `;

    row.querySelector('[data-action="save"]')?.addEventListener('click', () => {
      void saveCategory(item.id, row);
    });

    const deleteBtn = row.querySelector<HTMLButtonElement>('[data-action="delete"]');
    if (deleteBtn) {
      deleteBtn.addEventListener('click', () => {
        void deleteCategory(item.id);
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

    elements.tableBody.appendChild(row);
  }

  // Setup scroll indicators for table container
  setupScrollIndicators(tableContainer);
  initializeTableFirstCharNavigation();

  // Reset and reinitialize roving tabindex pattern
  rovingTabindexInitialized = false;
  currentCategoryFocusIndex = 0;
  initializeRovingTabindex();
}

function parseIdList(value: string): number[] {
  return value
    .split(',')
    .map((id) => Number(id.trim()))
    .filter((id) => Number.isFinite(id) && id > 0);
}

async function loadCategories(): Promise<void> {
  try {
    const data = await apiFetch<CategoryListResponse>('/api/categories/manage');
    cachedItems = data.items ?? [];
    applySearchFilter();
    await loadAnalytics();
    await loadOrphans();
  } catch (error) {
    handleError(error, 'Failed to load categories');
  }
}

function applySearchFilter(): void {
  const query = normalizeSearch(elements.searchInput?.value ?? '');
  renderRows(filterItems(cachedItems, query));
}

async function createCategory(event: Event): Promise<void> {
  event.preventDefault();
  if (!elements.createName) {
    return;
  }
  resetFieldError('category-create-name', 'category-create-name-error');
  resetErrorSummary('category-create-error-summary');
  const validationErrors: FormValidationError[] = [];

  const payload = {
    name: elements.createName.value.trim(),
    description: elements.createDescription?.value.trim() || undefined,
    color: elements.createColor?.value.trim() || undefined,
  };

  if (!payload.name) {
    addFieldError(
      validationErrors,
      'category-create-name',
      'category-create-name-error',
      tUnsafe('management.nameRequired')
    );
    renderErrorSummary('category-create-error-summary', validationErrors);
    return;
  }

  try {
    await apiFetch('/api/categories', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    showNotification(tUnsafe('management.createSuccess'), 'success');
    if (elements.createForm) {
      elements.createForm.reset();
    }
    await loadCategories();
  } catch (error) {
    handleError(error, 'Failed to create category');
  }
}

async function saveCategory(categoryId: number, row: HTMLTableRowElement): Promise<void> {
  const payload = buildCategoryPayload(row);
  try {
    await apiFetch(`/api/categories/${categoryId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
    showNotification(tUnsafe('management.saveSuccess'), 'success');
    await loadCategories();
  } catch (error) {
    handleError(error, 'Failed to update category');
  }
}

async function deleteCategory(categoryId: number): Promise<void> {
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
    await apiFetch(`/api/categories/${categoryId}?confirm=true`, {
      method: 'DELETE',
    });
    showNotification(tUnsafe('management.deleteSuccess'), 'success');
    await loadCategories();

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
        await apiFetch(`/api/categories/${categoryId}?confirm=true&force=true`, {
          method: 'DELETE',
        });
        showNotification(tUnsafe('management.deleteSuccess'), 'success');
        await loadCategories();

        // Restore focus after delete completes
        restoreFocusAfterDelete();
        return;
      } catch (forceError) {
        handleError(forceError, 'Failed to delete category');
        return;
      }
    }
    handleError(error, 'Failed to delete category');
  }
}

async function mergeCategories(): Promise<void> {
  resetFieldError('category-merge-target', 'category-merge-target-error');
  resetFieldError('category-merge-sources', 'category-merge-sources-error');
  resetErrorSummary('category-merge-error-summary');
  const validationErrors: FormValidationError[] = [];
  const targetId = Number(elements.mergeTarget?.value || '');
  const sourceIds = parseIdList(elements.mergeSources?.value || '');
  if (!targetId) {
    addFieldError(
      validationErrors,
      'category-merge-target',
      'category-merge-target-error',
      tUnsafe('management.mergeRequireIds')
    );
  }
  if (sourceIds.length === 0) {
    addFieldError(
      validationErrors,
      'category-merge-sources',
      'category-merge-sources-error',
      tUnsafe('management.mergeRequireIds')
    );
  }
  if (validationErrors.length > 0) {
    renderErrorSummary('category-merge-error-summary', validationErrors);
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
    await apiFetch('/api/categories/merge', {
      method: 'POST',
      body: JSON.stringify({ target_id: targetId, source_ids: sourceIds, confirm: true }),
    });
    showNotification(tUnsafe('management.mergeSuccess'), 'success');
    await loadCategories();
  } catch (error) {
    handleError(error, 'Failed to merge categories');
  }
}

async function findReplaceCategories(): Promise<void> {
  resetFieldError('category-find', 'category-find-error');
  resetFieldError('category-replace', 'category-replace-error');
  resetErrorSummary('category-find-replace-error-summary');
  const validationErrors: FormValidationError[] = [];
  const findValue = elements.findInput?.value.trim() || '';
  const replaceValue = elements.replaceInput?.value.trim() || '';
  if (!findValue) {
    addFieldError(
      validationErrors,
      'category-find',
      'category-find-error',
      tUnsafe('management.findReplaceRequired')
    );
  }
  if (!replaceValue) {
    addFieldError(
      validationErrors,
      'category-replace',
      'category-replace-error',
      tUnsafe('management.findReplaceRequired')
    );
  }
  if (validationErrors.length > 0) {
    renderErrorSummary('category-find-replace-error-summary', validationErrors);
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
    await apiFetch('/api/categories/find-replace', {
      method: 'POST',
      body: JSON.stringify({ find: findValue, replace: replaceValue, confirm: true }),
    });
    showNotification(tUnsafe('management.replaceSuccess'), 'success');
    await loadCategories();
  } catch (error) {
    handleError(error, 'Failed to replace category');
  }
}

async function bulkDeleteCategories(): Promise<void> {
  resetFieldError('category-bulk-delete-ids', 'category-bulk-delete-ids-error');
  resetErrorSummary('category-bulk-delete-error-summary');
  const validationErrors: FormValidationError[] = [];
  const ids = parseIdList(elements.bulkDeleteIds?.value || '');
  if (ids.length === 0) {
    addFieldError(
      validationErrors,
      'category-bulk-delete-ids',
      'category-bulk-delete-ids-error',
      tUnsafe('management.bulkDeleteRequireIds')
    );
    renderErrorSummary('category-bulk-delete-error-summary', validationErrors);
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
    await apiFetch('/api/categories/bulk-delete', {
      method: 'POST',
      body: JSON.stringify({ ids, force, confirm: true }),
    });
    showNotification(tUnsafe('management.bulkDeleteSuccess'), 'success');
    await loadCategories();
  } catch (error) {
    handleError(error, 'Failed to delete categories');
  }
}

async function exportCategories(): Promise<void> {
  try {
    const data = await apiFetch<{ items: CategoryItem[] }>('/api/categories/export');
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

async function importCategories(): Promise<void> {
  resetFieldError('category-import-file', 'category-import-file-error');
  resetErrorSummary('category-import-error-summary');
  const validationErrors: FormValidationError[] = [];
  const file = elements.importFile?.files?.[0];
  if (!file) {
    addFieldError(
      validationErrors,
      'category-import-file',
      'category-import-file-error',
      tUnsafe('management.importSelectFile')
    );
    renderErrorSummary('category-import-error-summary', validationErrors);
    return;
  }
  try {
    const text = await file.text();
    const parsed = JSON.parse(text) as { items?: CategoryItem[] };
    const items = (parsed.items ?? []).map((item) => ({
      name: item.name,
      description: item.description ?? undefined,
      color: item.color ?? undefined,
      sort_order: item.sort_order ?? undefined,
    }));
    await apiFetch('/api/categories/import', {
      method: 'POST',
      body: JSON.stringify({ items }),
    });
    showNotification(tUnsafe('management.importSuccess'), 'success');
    await loadCategories();
  } catch (error) {
    handleError(error, 'Failed to import categories');
  }
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
    await apiFetch('/api/categories/merge', {
      method: 'POST',
      body: JSON.stringify({ target_id: targetId, source_ids: sourceIds, confirm: true }),
    });
    showNotification(tUnsafe('management.mergeSuccess'), 'success');
    await loadCategories();
  } catch (error) {
    handleError(error, 'Failed to merge categories');
  }
}

async function saveAllCategories(): Promise<void> {
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
    const payload = buildCategoryPayload(row);
    try {
      await apiFetch(`/api/categories/${idValue}`, {
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

  await loadCategories();
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
    await apiFetch('/api/categories/find-replace', {
      method: 'POST',
      body: JSON.stringify({ find: selected.name, replace: replaceValue, confirm: true }),
    });
    showNotification(tUnsafe('management.replaceSuccess'), 'success');
    await loadCategories();
  } catch (error) {
    handleError(error, 'Failed to replace category');
  }
}

async function undoLastOperation(): Promise<void> {
  try {
    await apiFetch('/api/categories/undo', {
      method: 'POST',
    });
    showNotification(tUnsafe('management.undoSuccess'), 'success');
    await loadCategories();
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
    }>('/api/categories/analytics');
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
  } catch (error) {
    handleError(error, 'Failed to load analytics');
  }
}

async function loadOrphans(): Promise<void> {
  try {
    const data = await apiFetch<{ prompt_ids: number[]; count: number }>('/api/categories/orphans');
    if (elements.orphansCount) {
      elements.orphansCount.textContent = String(data.count ?? 0);
    }
    if (elements.orphansDetails) {
      await renderPromptDetails(data.prompt_ids ?? [], elements.orphansDetails);
      setupScrollIndicators(elements.orphansDetails);
    }
  } catch (error) {
    handleError(error, 'Failed to load orphans');
  }

  try {
    const data = await apiFetch<CategoryListResponse>('/api/categories/unused');
    if (elements.unusedCount) {
      elements.unusedCount.textContent = String(data.items?.length ?? 0);
    }
    if (elements.unusedList) {
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

async function renderPromptDetails(promptIds: number[], container: HTMLElement): Promise<void> {
  container.innerHTML = '';
  if (promptIds.length === 0) {
    return;
  }
  let details: OrphanPromptDetailsResponse | null = null;
  try {
    details = await apiFetch<OrphanPromptDetailsResponse>('/api/categories/orphans/details');
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
      void assignCategoryToPrompt(promptId, resolved);
    });
  });
}

async function assignCategoryToPrompt(promptId: number, category: string): Promise<void> {
  try {
    await apiFetch('/api/categories/assign-orphans', {
      method: 'POST',
      body: JSON.stringify({ prompt_ids: [promptId], category, confirm: true }),
    });
    showNotification(tUnsafe('management.assignSuccess'), 'success');
    await loadCategories();
  } catch (error) {
    handleError(error, 'Failed to assign category');
  }
}

function handleError(error: unknown, fallback: string): void {
  if (!(error instanceof APIRequestError)) {
    console.error(error);
  }
  showNotification(handleApiError(error, fallback), 'error');
}

function init(): void {
  initSecondaryNav({ component: 'manage-categories', requireAuth: true });

  // Initialize enhanced color picker
  try {
    initializeColorPicker({
      containerId: 'category-create-color-picker-container',
      colorInputId: 'category-create-color',
      colorPickerId: 'category-create-color-picker',
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
    'category-create-name',
    'category-create-name-error',
    tUnsafe('management.nameRequired')
  );
  attachRequiredLiveValidation(
    elements.mergeTarget,
    'category-merge-target',
    'category-merge-target-error',
    tUnsafe('management.mergeRequireIds')
  );
  attachRequiredLiveValidation(
    elements.mergeSources,
    'category-merge-sources',
    'category-merge-sources-error',
    tUnsafe('management.mergeRequireIds')
  );
  attachRequiredLiveValidation(
    elements.findInput,
    'category-find',
    'category-find-error',
    tUnsafe('management.findReplaceRequired')
  );
  attachRequiredLiveValidation(
    elements.replaceInput,
    'category-replace',
    'category-replace-error',
    tUnsafe('management.findReplaceRequired')
  );
  attachRequiredLiveValidation(
    elements.bulkDeleteIds,
    'category-bulk-delete-ids',
    'category-bulk-delete-ids-error',
    tUnsafe('management.bulkDeleteRequireIds')
  );
  attachFileRequiredLiveValidation(
    elements.importFile,
    'category-import-file',
    'category-import-file-error',
    tUnsafe('management.importSelectFile')
  );
  if (elements.createForm) {
    elements.createForm.addEventListener('submit', (event) => {
      void createCategory(event);
    });
  }
  elements.mergeButton?.addEventListener('click', () => {
    void mergeCategories();
  });
  elements.findReplaceButton?.addEventListener('click', () => {
    void findReplaceCategories();
  });
  elements.bulkDeleteButton?.addEventListener('click', () => {
    void bulkDeleteCategories();
  });
  elements.exportButton?.addEventListener('click', () => {
    void exportCategories();
  });
  elements.importButton?.addEventListener('click', () => {
    void importCategories();
  });
  elements.selectionMergeButton?.addEventListener('click', () => {
    void mergeSelected();
  });
  elements.selectionFindReplaceButton?.addEventListener('click', () => {
    void findReplaceSelected();
  });
  elements.saveAllButton?.addEventListener('click', () => {
    void saveAllCategories();
  });
  elements.undoButton?.addEventListener('click', () => {
    void undoLastOperation();
  });

  void loadCategories();
}

/**
 * Restores focus after a category is deleted from the table
 * Focuses the next row's delete button, or previous row's button, or the table body
 */
function restoreFocusAfterDelete(): void {
  if (!elements.tableBody) return;

  // Find the row that would have been after the deleted item
  const rows = Array.from(elements.tableBody.querySelectorAll<HTMLTableRowElement>('tr'));
  if (rows.length === 0) {
    // Table is empty, focus the empty state or search input
    const emptyState = document.getElementById('categories-empty-state');
    if (emptyState && !emptyState.classList.contains('hidden')) {
      const createBtn = emptyState.querySelector<HTMLButtonElement>('button');
      if (createBtn) {
        createBtn.focus();
        announceToScreenReader('Category deleted. No categories remaining.', 'polite');
        return;
      }
    }
    // Focus search input if available
    if (elements.searchInput) {
      elements.searchInput.focus();
      announceToScreenReader('Category deleted. Table is now empty.', 'polite');
    }
    return;
  }

  // Focus the first row's delete button
  const firstRow = rows[0];
  if (firstRow) {
    const deleteBtn = firstRow.querySelector<HTMLElement>('[data-action="delete"]');
    if (deleteBtn) {
      deleteBtn.focus();
      announceToScreenReader('Category deleted. Focus moved to next category.', 'polite');
      return;
    }
  }

  // Fall back to table body
  if (elements.tableBody) {
    (elements.tableBody as HTMLElement).setAttribute('tabindex', '-1');
    (elements.tableBody as HTMLElement).focus();
    announceToScreenReader('Category deleted.', 'polite');
  }
}

initI18n(() => {
  try {
    updateStaticTranslations();
    init();
  } catch (error) {
    console.error('Failed to initialize category management', error);
  }
});
