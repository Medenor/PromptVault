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
  attachFileRequiredLiveValidation,
  attachRequiredLiveValidation,
  addFieldError,
  resetErrorSummary,
  resetFieldError,
  renderErrorSummary,
} from './a11y';
import { buildCategoryPayload, filterItems, normalizeSearch, renderRows } from './table';
import { loadAnalytics, loadOrphans } from './orphans';
import {
  bulkDeleteCategories,
  exportCategories,
  findReplaceCategories,
  importCategories,
  mergeCategories,
  parseIdList,
  undoLastOperation,
} from './bulk-ops';
import {
  assignCategoryToPromptRequest,
  createCategoryRequest,
  deleteCategoryRequest,
  fetchCategories,
  findReplaceCategoriesRequest,
  mergeCategoriesRequest,
  updateCategoryRequest,
} from './api';
import type { CategoryItem, FormValidationError } from './types';

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

function handleError(error: unknown, fallback: string): void {
  if (!(error instanceof APIRequestError)) {
    console.error(error);
  }
  showNotification(handleApiError(error, fallback), 'error');
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

async function loadCategories(): Promise<void> {
  try {
    const data = await fetchCategories();
    cachedItems = data.items ?? [];
    applySearchFilter();
    await loadAnalytics(elements, handleError);
    await loadOrphans(
      elements,
      handleError,
      (promptId, category) => {
        void assignCategoryToPrompt(promptId, category);
      },
      resolveCategoryInput
    );
  } catch (error) {
    handleError(error, 'Failed to load categories');
  }
}

function applySearchFilter(): void {
  const query = normalizeSearch(elements.searchInput?.value ?? '');
  renderRows(elements.tableBody, filterItems(cachedItems, query), {
    onSave: (categoryId, row) => {
      void saveCategory(categoryId, row);
    },
    onDelete: (categoryId) => {
      void deleteCategory(categoryId);
    },
  });
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
    await createCategoryRequest(payload);
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
    await updateCategoryRequest(categoryId, payload);
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
    await deleteCategoryRequest(categoryId);
    showNotification(tUnsafe('management.deleteSuccess'), 'success');
    await loadCategories();
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
        await deleteCategoryRequest(categoryId, true);
        showNotification(tUnsafe('management.deleteSuccess'), 'success');
        await loadCategories();
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
    await mergeCategoriesRequest(targetId, sourceIds);
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
      await updateCategoryRequest(idValue, payload);
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
    await findReplaceCategoriesRequest(selected.name, replaceValue);
    showNotification(tUnsafe('management.replaceSuccess'), 'success');
    await loadCategories();
  } catch (error) {
    handleError(error, 'Failed to replace category');
  }
}

async function assignCategoryToPrompt(promptId: number, category: string): Promise<void> {
  try {
    await assignCategoryToPromptRequest(promptId, category);
    showNotification(tUnsafe('management.assignSuccess'), 'success');
    await loadCategories();
  } catch (error) {
    handleError(error, 'Failed to assign category');
  }
}

/**
 * Restores focus after a category is deleted from the table
 * Focuses the next row's delete button, or previous row's button, or the table body
 */
function restoreFocusAfterDelete(): void {
  if (!elements.tableBody) return;

  const rows = Array.from(elements.tableBody.querySelectorAll<HTMLTableRowElement>('tr'));
  if (rows.length === 0) {
    const emptyState = document.getElementById('categories-empty-state');
    if (emptyState && !emptyState.classList.contains('hidden')) {
      const createBtn = emptyState.querySelector<HTMLButtonElement>('button');
      if (createBtn) {
        createBtn.focus();
        announceToScreenReader('Category deleted. No categories remaining.', 'polite');
        return;
      }
    }
    if (elements.searchInput) {
      elements.searchInput.focus();
      announceToScreenReader('Category deleted. Table is now empty.', 'polite');
    }
    return;
  }

  const firstRow = rows[0];
  if (firstRow) {
    const deleteBtn = firstRow.querySelector<HTMLElement>('[data-action="delete"]');
    if (deleteBtn) {
      deleteBtn.focus();
      announceToScreenReader('Category deleted. Focus moved to next category.', 'polite');
      return;
    }
  }

  if (elements.tableBody) {
    (elements.tableBody as HTMLElement).setAttribute('tabindex', '-1');
    (elements.tableBody as HTMLElement).focus();
    announceToScreenReader('Category deleted.', 'polite');
  }
}

function init(): void {
  initSecondaryNav({ component: 'manage-categories', requireAuth: true });

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
    void (async () => {
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
      try {
        await mergeCategories(targetId, sourceIds, handleError);
        await loadCategories();
      } catch {
        // handled by mergeCategories via handleError
      }
    })();
  });
  elements.findReplaceButton?.addEventListener('click', () => {
    void (async () => {
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
      try {
        await findReplaceCategories(findValue, replaceValue, handleError);
        await loadCategories();
      } catch {
        // handled by findReplaceCategories via handleError
      }
    })();
  });
  elements.bulkDeleteButton?.addEventListener('click', () => {
    void (async () => {
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
      const force = elements.bulkDeleteForce?.checked ?? false;
      try {
        await bulkDeleteCategories(ids, force, handleError);
        await loadCategories();
      } catch {
        // handled by bulkDeleteCategories via handleError
      }
    })();
  });
  elements.exportButton?.addEventListener('click', () => {
    void exportCategories(handleError);
  });
  elements.importButton?.addEventListener('click', () => {
    void (async () => {
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
        await importCategories(file, handleError);
        await loadCategories();
      } catch {
        // handled by importCategories via handleError
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
    void saveAllCategories();
  });
  elements.undoButton?.addEventListener('click', () => {
    void (async () => {
      try {
        await undoLastOperation(handleError);
        await loadCategories();
      } catch {
        // handled by undoLastOperation via handleError
      }
    })();
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
