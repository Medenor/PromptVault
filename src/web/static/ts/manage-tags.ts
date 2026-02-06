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
  selectionMergeButton: document.getElementById('tag-selection-merge-btn') as HTMLButtonElement | null,
  selectionFindReplaceButton: document.getElementById('tag-selection-find-replace-btn') as HTMLButtonElement | null,
  saveAllButton: document.getElementById('tag-save-all-btn') as HTMLButtonElement | null,
  undoButton: document.getElementById('tag-undo-btn') as HTMLButtonElement | null,
  analyticsTotal: document.getElementById('tag-analytics-total') as HTMLElement | null,
  analyticsUsed: document.getElementById('tag-analytics-used') as HTMLElement | null,
  analyticsUnused: document.getElementById('tag-analytics-unused') as HTMLElement | null,
  analyticsTop: document.getElementById('tag-analytics-top') as HTMLElement | null,
  analyticsCooccurrence: document.getElementById('tag-analytics-cooccurrence') as HTMLElement | null,
  hierarchyTree: document.getElementById('tag-hierarchy-tree') as HTMLElement | null,
  orphansCount: document.getElementById('tag-orphans-count') as HTMLElement | null,
  orphansList: document.getElementById('tag-orphans-list') as HTMLElement | null,
  orphansPromptCount: document.getElementById('tag-orphans-prompts-count') as HTMLElement | null,
  orphansPromptDetails: document.getElementById('tag-orphans-prompts-details') as HTMLElement | null,
};

let cachedItems: TagItem[] = [];
// @ts-expect-error - Used for cleanup, but not referenced directly
let colorPickerInstance: ColorPicker | null = null;
type OrphanPromptDetailsResponse = {
  items: Array<{ id: number; title: string }>;
  count: number;
};

function normalizeSearch(value: string): string {
  return value.trim().toLowerCase();
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
        alert(tUnsafe('management.idNotFound', { id }));
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
    row.className = 'border-b border-gray-100';
    row.dataset.id = String(item.id);

    row.innerHTML = `
      <td class="py-2 pr-4">
        <input type="checkbox" data-select-id="${item.id}" aria-label="${selectLabel} #${item.id}" />
      </td>
      <td class="py-2 pr-4 text-gray-600">#${item.id}</td>
      <td class="py-2 pr-4">
        <input data-field="name" aria-label="${nameLabel}" class="w-full px-2 py-1 border border-gray-300 rounded" value="${item.name}" />
      </td>
      <td class="py-2 pr-4">
        <input data-field="description" aria-label="${descriptionLabel}" class="w-full px-2 py-1 border border-gray-300 rounded" value="${item.description ?? ''}" />
      </td>
      <td class="py-2 pr-4">
        <div class="flex items-center gap-2">
          <input data-field="color" aria-label="${colorLabel}" class="w-full px-2 py-1 border border-gray-300 rounded" value="${item.color ?? ''}" />
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
      <td class="py-2 pr-4">
        <select data-field="parent_tag_id" aria-label="${parentLabel}" class="w-36 px-2 py-1 border border-gray-300 rounded">
          ${renderParentOptions(item.id, item.parent_tag_id ?? null, parentNoneLabel)}
        </select>
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
      void saveTag(item.id, row);
    });

    row.querySelector('[data-action="delete"]')?.addEventListener('click', () => {
      void deleteTag(item.id);
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

  const payload = {
    name: elements.createName.value.trim(),
    description: elements.createDescription?.value.trim() || undefined,
    color: elements.createColor?.value.trim() || undefined,
    parent_tag_id: elements.createParent?.value ? Number(elements.createParent.value) : undefined,
  };

  if (!payload.name) {
    alert(tUnsafe('management.nameRequired'));
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
  const confirmed = window.confirm(tUnsafe('management.deleteConfirm'));
  if (!confirmed) {
    return;
  }
  try {
    await apiFetch(`/api/tags/${tagId}?confirm=true`, {
      method: 'DELETE',
    });
    showNotification(tUnsafe('management.deleteSuccess'), 'success');
    await loadTags();
  } catch (error) {
    if (error instanceof APIRequestError && error.status === 422) {
      const forceConfirmed = window.confirm(tUnsafe('management.forceDeleteConfirm'));
      if (!forceConfirmed) {
        return;
      }
      try {
        await apiFetch(`/api/tags/${tagId}?confirm=true&force=true`, {
          method: 'DELETE',
        });
        showNotification(tUnsafe('management.deleteSuccess'), 'success');
        await loadTags();
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
  const file = elements.importFile?.files?.[0];
  if (!file) {
    alert(tUnsafe('management.importSelectFile'));
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
    alert(tUnsafe('management.noRows'));
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
    const data = await apiFetch<{ prompt_ids: number[]; count: number }>('/api/tags/orphan-prompts');
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
      <span class="text-gray-800">#${id} — ${title || tUnsafe('management.untitledPrompt')}</span>
      <div class="flex flex-col gap-2 md:flex-row md:items-center md:gap-3">
        <input
          type="text"
          data-prompt-tags="${id}"
          placeholder="${tUnsafe('management.tagsPlaceholder')}"
          class="w-full md:w-56 px-2 py-1 border border-gray-300 rounded"
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
        alert(tUnsafe('management.tagsPlaceholder'));
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
  void loadTags();
}

initI18n(() => {
  try {
    updateStaticTranslations();
    init();
  } catch (error) {
    console.error('Failed to initialize tag management', error);
  }
});
