/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import '../css/tailwind-globals.css';
import { apiFetch, APIRequestError } from '@/utils/api';
import { initI18n, tUnsafe, updateStaticTranslations } from '@/utils/i18n';
import { initializeColorPicker, ColorPicker } from '@/utils/color-picker';
import { setupScrollIndicators } from '@/utils/dom';
import { showNotification } from '@/utils/notifications';

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

const elements = {
  tableBody: document.getElementById('categories-table-body') as HTMLTableSectionElement | null,
  searchInput: document.getElementById('category-search') as HTMLInputElement | null,
  createForm: document.getElementById('category-create-form') as HTMLFormElement | null,
  createName: document.getElementById('category-create-name') as HTMLInputElement | null,
  createDescription: document.getElementById('category-create-description') as HTMLInputElement | null,
  createColor: document.getElementById('category-create-color') as HTMLInputElement | null,
  createColorPicker: document.getElementById('category-create-color-picker') as HTMLInputElement | null,
  mergeTarget: document.getElementById('category-merge-target') as HTMLInputElement | null,
  mergeSources: document.getElementById('category-merge-sources') as HTMLInputElement | null,
  mergeButton: document.getElementById('category-merge-btn') as HTMLButtonElement | null,
  findInput: document.getElementById('category-find') as HTMLInputElement | null,
  replaceInput: document.getElementById('category-replace') as HTMLInputElement | null,
  findReplaceButton: document.getElementById('category-find-replace-btn') as HTMLButtonElement | null,
  bulkDeleteIds: document.getElementById('category-bulk-delete-ids') as HTMLInputElement | null,
  bulkDeleteForce: document.getElementById('category-bulk-delete-force') as HTMLInputElement | null,
  bulkDeleteButton: document.getElementById('category-bulk-delete-btn') as HTMLButtonElement | null,
  exportButton: document.getElementById('category-export-btn') as HTMLButtonElement | null,
  importFile: document.getElementById('category-import-file') as HTMLInputElement | null,
  importButton: document.getElementById('category-import-btn') as HTMLButtonElement | null,
  selectionMergeButton: document.getElementById('category-selection-merge-btn') as HTMLButtonElement | null,
  selectionFindReplaceButton: document.getElementById('category-selection-find-replace-btn') as HTMLButtonElement | null,
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
// @ts-expect-error - Used for cleanup, but not referenced directly
let colorPickerInstance: ColorPicker | null = null;
type OrphanPromptDetailsResponse = {
  items: Array<{ id: number; title: string }>;
  count: number;
};

function normalizeSearch(value: string): string {
  return value.trim().toLowerCase();
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
      alert(tUnsafe('management.idNotFound', { id }));
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

  for (const item of items) {
    const row = document.createElement('tr');
    row.className = 'border-b border-gray-100';
    row.dataset.id = String(item.id);

    row.innerHTML = `
      <td class="py-2 pr-4">
        <input type="checkbox" data-select-id="${item.id}" />
      </td>
      <td class="py-2 pr-4 text-gray-600">#${item.id}</td>
      <td class="py-2 pr-4">
        <input data-field="name" class="w-full px-2 py-1 border border-gray-300 rounded" value="${item.name}" />
      </td>
      <td class="py-2 pr-4">
        <input data-field="description" class="w-full px-2 py-1 border border-gray-300 rounded" value="${item.description ?? ''}" />
      </td>
      <td class="py-2 pr-4">
        <div class="flex items-center gap-2">
          <input data-field="color" class="w-full px-2 py-1 border border-gray-300 rounded" value="${item.color ?? ''}" />
          <input
            data-color-picker
            type="color"
            value="${normalizeHexForPicker(item.color)}"
            title="${colorLabel}"
            aria-label="${colorLabel}"
            class="h-8 w-8 rounded border border-gray-300 p-0"
          />
        </div>
      </td>
      <td class="py-2 pr-4 text-gray-600">${item.usage_count}</td>
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

    row.querySelector('[data-action="delete"]')?.addEventListener('click', () => {
      void deleteCategory(item.id);
    });

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

  const payload = {
    name: elements.createName.value.trim(),
    description: elements.createDescription?.value.trim() || undefined,
    color: elements.createColor?.value.trim() || undefined,
  };

  if (!payload.name) {
    alert(tUnsafe('management.nameRequired'));
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
  const confirmed = window.confirm(tUnsafe('management.deleteConfirm'));
  if (!confirmed) {
    return;
  }
  try {
    await apiFetch(`/api/categories/${categoryId}?confirm=true`, {
      method: 'DELETE',
    });
    showNotification(tUnsafe('management.deleteSuccess'), 'success');
    await loadCategories();
  } catch (error) {
    if (error instanceof APIRequestError && error.status === 422) {
      const forceConfirmed = window.confirm(tUnsafe('management.forceDeleteConfirm'));
      if (!forceConfirmed) {
        return;
      }
      try {
        await apiFetch(`/api/categories/${categoryId}?confirm=true&force=true`, {
          method: 'DELETE',
        });
        showNotification(tUnsafe('management.deleteSuccess'), 'success');
        await loadCategories();
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
  const targetId = Number(elements.mergeTarget?.value || '');
  const sourceIds = parseIdList(elements.mergeSources?.value || '');
  if (!targetId || sourceIds.length === 0) {
    alert(tUnsafe('management.mergeRequireIds'));
    return;
  }
  const confirmed = window.confirm(tUnsafe('management.mergeConfirm'));
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
  const findValue = elements.findInput?.value.trim() || '';
  const replaceValue = elements.replaceInput?.value.trim() || '';
  if (!findValue || !replaceValue) {
    alert(tUnsafe('management.findReplaceRequired'));
    return;
  }
  const confirmed = window.confirm(tUnsafe('management.replaceConfirm'));
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
  const ids = parseIdList(elements.bulkDeleteIds?.value || '');
  if (ids.length === 0) {
    alert(tUnsafe('management.bulkDeleteRequireIds'));
    return;
  }
  const confirmed = window.confirm(tUnsafe('management.bulkDeleteConfirm'));
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
  const file = elements.importFile?.files?.[0];
  if (!file) {
    alert(tUnsafe('management.importSelectFile'));
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
    alert(tUnsafe('management.mergeSelectedRequire'));
    return;
  }
  const targetId = ids[0];
  const sourceIds = ids.slice(1);
  const confirmed = window.confirm(tUnsafe('management.mergeSelectedConfirm'));
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
    alert(tUnsafe('management.noRows'));
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
    alert(tUnsafe('management.replaceSelectedRequireOne'));
    return;
  }
  const selected = cachedItems.find((item) => item.id === ids[0]);
  if (!selected) {
    alert(tUnsafe('management.replaceSelectedNotFound'));
    return;
  }
  const replaceValue = window.prompt(
    tUnsafe('management.replacePrompt', { name: selected.name })
  );
  if (!replaceValue) {
    return;
  }
  const confirmed = window.confirm(tUnsafe('management.replaceConfirm'));
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
      <span class="text-gray-800">#${id} — ${title || tUnsafe('management.untitledPrompt')}</span>
      <div class="flex flex-col gap-2 md:flex-row md:items-center md:gap-3">
        <input
          type="text"
          data-prompt-category="${id}"
          placeholder="${tUnsafe('management.assignPlaceholder')}"
          class="w-full md:w-56 px-2 py-1 border border-gray-300 rounded"
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
        alert(tUnsafe('management.assignPlaceholder'));
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
  if (error instanceof APIRequestError) {
    alert(error.message);
    return;
  }
  console.error(error);
  alert(fallback);
}

function init(): void {
  // Initialize enhanced color picker
  try {
    colorPickerInstance = initializeColorPicker({
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

initI18n(() => {
  try {
    updateStaticTranslations();
    init();
  } catch (error) {
    console.error('Failed to initialize category management', error);
  }
});
