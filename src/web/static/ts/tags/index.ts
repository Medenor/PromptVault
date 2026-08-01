/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import '../../css/tailwind-globals.css';
import { APIRequestError, handleApiError } from '@/utils/api';
import { initI18n, t, tUnsafe, updateStaticTranslations } from '@/utils/i18n';
import { initializeColorPicker } from '@/utils/color-picker';
import { showNotification } from '@/utils/notifications';
import { confirmAsync } from '@/utils/dialogs';
import { announceToScreenReader } from '@/utils/focus-management';
import { initSecondaryNav } from '@/utils/secondary-nav';
import {
  applyFocusStyles,
  attachFileRequiredLiveValidation,
  attachRequiredLiveValidation,
  addFieldError,
  resetErrorSummary,
  resetFieldError,
  renderErrorSummary,
} from './a11y';
import {
  buildTagPayload,
  filterItems,
  normalizeSearch,
  populateCreateParentSelect,
  renderRows,
} from './table';
import { loadOrphans, renderHierarchyTree } from './hierarchy';
import {
  bulkDeleteTags,
  exportTags,
  findReplaceTags,
  importTags,
  loadAnalytics,
  mergeTags,
  parseIdList,
  undoLastOperation,
} from './bulk-ops';
import {
  assignTagsToPromptRequest,
  createTagRequest,
  deleteTagRequest,
  fetchTags,
  findReplaceTagsRequest,
  mergeTagsRequest,
  updateTagRequest,
} from './api';
import type { FormValidationError, TagItem } from './types';

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

function handleError(error: unknown, fallback: string): void {
  if (!(error instanceof APIRequestError)) {
    console.error(error);
  }
  showNotification(handleApiError(error, fallback), 'error');
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

async function loadTags(): Promise<void> {
  try {
    const data = await fetchTags();
    cachedItems = data.items ?? [];
    populateCreateParentSelect(elements.createParent, cachedItems);
    applySearchFilter();
    renderHierarchyTree(elements.hierarchyTree, cachedItems);
    await loadAnalytics(elements, handleError);
    await loadOrphans(
      elements,
      handleError,
      (promptId, tags) => {
        void assignTagsToPrompt(promptId, tags);
      },
      resolveTagInputs
    );
  } catch (error) {
    handleError(error, 'Failed to load tags');
  }
}

function applySearchFilter(): void {
  const query = normalizeSearch(elements.searchInput?.value ?? '');
  renderRows(elements.tableBody, filterItems(cachedItems, query), cachedItems, {
    onSave: (tagId, row) => {
      void saveTag(tagId, row);
    },
    onDelete: (tagId) => {
      void deleteTag(tagId);
    },
  });
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
    await createTagRequest(payload);
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
    await updateTagRequest(tagId, payload);
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
    await deleteTagRequest(tagId);
    showNotification(tUnsafe('management.deleteSuccess'), 'success');
    await loadTags();
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
        await deleteTagRequest(tagId, true);
        showNotification(tUnsafe('management.deleteSuccess'), 'success');
        await loadTags();
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
  if (targetId === undefined) {
    return;
  }
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
    await mergeTagsRequest(targetId, sourceIds);
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
      await updateTagRequest(idValue, payload);
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
    await findReplaceTagsRequest(selected.name, replaceValue);
    showNotification(tUnsafe('management.replaceSuccess'), 'success');
    await loadTags();
  } catch (error) {
    handleError(error, 'Failed to replace tag');
  }
}

async function assignTagsToPrompt(promptId: number, tags: string[]): Promise<void> {
  try {
    await assignTagsToPromptRequest(promptId, tags);
    showNotification(tUnsafe('management.bulkUpdateSuccess'), 'success');
    await loadTags();
  } catch (error) {
    handleError(error, 'Failed to apply tags');
  }
}

/**
 * Restores focus after a tag is deleted from the table
 * Focuses the next row's delete button, or previous row's button, or the table body
 */
function restoreFocusAfterDelete(): void {
  if (!elements.tableBody) return;

  const rows = Array.from(elements.tableBody.querySelectorAll<HTMLTableRowElement>('tr'));
  if (rows.length === 0) {
    const emptyState = document.getElementById('tags-empty-state');
    if (emptyState && !emptyState.classList.contains('hidden')) {
      const createBtn = emptyState.querySelector<HTMLButtonElement>('button');
      if (createBtn) {
        createBtn.focus();
        announceToScreenReader('Tag deleted. No tags remaining.', 'polite');
        return;
      }
    }
    if (elements.searchInput) {
      elements.searchInput.focus();
      announceToScreenReader('Tag deleted. Table is now empty.', 'polite');
    }
    return;
  }

  const firstRow = rows[0];
  if (firstRow) {
    const deleteBtn = firstRow.querySelector<HTMLElement>('[data-action="delete"]');
    if (deleteBtn) {
      deleteBtn.focus();
      announceToScreenReader('Tag deleted. Focus moved to next tag.', 'polite');
      return;
    }
  }

  if (elements.tableBody) {
    (elements.tableBody as HTMLElement).setAttribute('tabindex', '-1');
    (elements.tableBody as HTMLElement).focus();
    announceToScreenReader('Tag deleted.', 'polite');
  }
}

function init(): void {
  initSecondaryNav({ component: 'manage-tags', requireAuth: true });

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
    void (async () => {
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
      try {
        await mergeTags(targetId, sourceIds, handleError);
        await loadTags();
      } catch {
        // handled by mergeTags via handleError
      }
    })();
  });
  elements.findReplaceButton?.addEventListener('click', () => {
    void (async () => {
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
      try {
        await findReplaceTags(findValue, replaceValue, handleError);
        await loadTags();
      } catch {
        // handled by findReplaceTags via handleError
      }
    })();
  });
  elements.bulkDeleteButton?.addEventListener('click', () => {
    void (async () => {
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
      const force = elements.bulkDeleteForce?.checked ?? false;
      try {
        await bulkDeleteTags(ids, force, handleError);
        await loadTags();
      } catch {
        // handled by bulkDeleteTags via handleError
      }
    })();
  });
  elements.exportButton?.addEventListener('click', () => {
    void exportTags(handleError);
  });
  elements.importButton?.addEventListener('click', () => {
    void (async () => {
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
        await importTags(file, handleError);
        await loadTags();
      } catch {
        // handled by importTags via handleError
      }
    })();
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
    void (async () => {
      try {
        await undoLastOperation(handleError);
        await loadTags();
      } catch {
        // handled by undoLastOperation via handleError
      }
    })();
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

  document.querySelectorAll<HTMLButtonElement>('button').forEach((btn) => {
    const ringColor =
      btn.classList.contains('bg-red-600') || btn.classList.contains('bg-red-700')
        ? '#ef4444'
        : '#3b82f6';
    applyFocusStyles(btn, ringColor);
  });

  if (elements.importFile) {
    applyFocusStyles(elements.importFile);
  }

  if (elements.createColorPicker) {
    applyFocusStyles(elements.createColorPicker);
  }

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
