/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { apiFetch } from '@/utils/api';
import { t } from '@/utils/i18n';
import { showNotification } from '@/utils/notifications';
import { focusFirstElement, announceToScreenReader } from '@/utils/focus-management';
import { HIDDEN_CLASS, guardOnlineOnly, reportAppIssue } from './shared';
import { parseTagInput } from './tag-autocomplete';
import type { BulkDeleteResponse } from './types';

export const selectedPromptIds: Set<number> = new Set(); // Track selected prompts for bulk operations

let bulkDeleteModalTrigger: HTMLElement | null = null;
let bulkTagModalTrigger: HTMLElement | null = null;

export interface BulkActionsRefreshCallbacks {
  loadPrompts: () => Promise<void>;
  loadAvailableTags: () => Promise<void>;
  loadTags: () => Promise<void>;
}

export function initializeBulkActions(callbacks: BulkActionsRefreshCallbacks): void {
  const selectAllCheckbox = document.getElementById('select-all-checkbox');
  const bulkDeleteBtn = document.getElementById('bulk-delete-btn');
  const bulkTagBtn = document.getElementById('bulk-tag-btn');
  const clearSelectionBtn = document.getElementById('clear-selection-btn');
  const confirmBulkDeleteBtn = document.getElementById('confirm-bulk-delete-btn');
  const cancelBulkDeleteBtn = document.getElementById('cancel-bulk-delete-btn');
  const confirmBulkTagBtn = document.getElementById('confirm-bulk-tag-btn');
  const cancelBulkTagBtn = document.getElementById('cancel-bulk-tag-btn');

  if (selectAllCheckbox) {
    selectAllCheckbox.addEventListener('change', handleSelectAll);
  }

  if (bulkDeleteBtn) {
    bulkDeleteBtn.addEventListener('click', showBulkDeleteConfirmation);
  }
  if (bulkTagBtn) {
    bulkTagBtn.addEventListener('click', showBulkTagModal);
  }

  if (clearSelectionBtn) {
    clearSelectionBtn.addEventListener('click', clearSelection);
  }

  if (confirmBulkDeleteBtn) {
    confirmBulkDeleteBtn.addEventListener('click', () => {
      void performBulkDelete(callbacks);
    });
  }

  if (cancelBulkDeleteBtn) {
    cancelBulkDeleteBtn.addEventListener('click', hideBulkDeleteModal);
  }

  if (confirmBulkTagBtn) {
    confirmBulkTagBtn.addEventListener('click', () => {
      void performBulkTagUpdate(callbacks);
    });
  }

  if (cancelBulkTagBtn) {
    cancelBulkTagBtn.addEventListener('click', hideBulkTagModal);
  }
}

export function handleCheckboxChange(promptId: number, isChecked: boolean): void {
  if (isChecked) {
    selectedPromptIds.add(promptId);
  } else {
    selectedPromptIds.delete(promptId);
  }
  updateBulkActionsUI();
}

function handleSelectAll(event: Event): void {
  const target = event.target as HTMLInputElement | null;
  const isChecked = target?.checked ?? false;
  const checkboxes = document.querySelectorAll<HTMLInputElement>('.prompt-checkbox');

  checkboxes.forEach((checkbox) => {
    checkbox.checked = isChecked;
    const promptId = parseInt(checkbox.dataset.promptId || '', 10);
    if (isChecked) {
      selectedPromptIds.add(promptId);
    } else {
      selectedPromptIds.delete(promptId);
    }
  });

  updateBulkActionsUI();
}

export function updateBulkActionsUI(): void {
  const toolbar = document.getElementById('bulk-actions-toolbar') as HTMLElement | null;
  const countElement = document.getElementById('selected-count') as HTMLElement | null;
  const selectAllCheckbox = document.getElementById(
    'select-all-checkbox'
  ) as HTMLInputElement | null;

  if (selectedPromptIds.size > 0) {
    if (toolbar) {
      toolbar.style.display = 'block';
    }
    if (countElement) {
      countElement.textContent = t('bulkDelete.selectedCount', { count: selectedPromptIds.size });
    }
  } else {
    if (toolbar) {
      toolbar.style.display = 'none';
    }
  }

  // Update select all checkbox state
  const allCheckboxes = document.querySelectorAll<HTMLInputElement>('.prompt-checkbox');
  const allChecked = allCheckboxes.length > 0 && selectedPromptIds.size === allCheckboxes.length;
  if (selectAllCheckbox) {
    selectAllCheckbox.checked = allChecked;
  }

  // Update selected styling on prompt items
  allCheckboxes.forEach((checkbox) => {
    const promptId = parseInt(checkbox.dataset.promptId || '', 10);
    const promptItem = checkbox.closest('.prompt-item');
    if (promptItem) {
      if (selectedPromptIds.has(promptId)) {
        promptItem.classList.add('selected');
      } else {
        promptItem.classList.remove('selected');
      }
    }
  });
}

export function clearSelection(): void {
  selectedPromptIds.clear();
  const checkboxes = document.querySelectorAll<HTMLInputElement>('.prompt-checkbox');
  checkboxes.forEach((checkbox) => (checkbox.checked = false));
  updateBulkActionsUI();
}

function showBulkDeleteConfirmation(): void {
  if (selectedPromptIds.size === 0) return;

  // Store trigger element for focus return
  bulkDeleteModalTrigger = (event as unknown as { target: HTMLElement }).target || null;
  const modal = document.getElementById('bulk-delete-modal');
  const countElement = document.getElementById('bulk-delete-count');
  if (countElement) {
    countElement.textContent = String(selectedPromptIds.size);
  }
  if (modal) {
    modal.classList.remove(HIDDEN_CLASS);
    // Move focus to first focusable element in modal
    focusFirstElement(modal);
  }
}

export function hideBulkDeleteModal(): void {
  const modal = document.getElementById('bulk-delete-modal');
  if (modal) {
    modal.classList.add(HIDDEN_CLASS);
  }
  // Return focus to trigger element
  if (bulkDeleteModalTrigger) {
    bulkDeleteModalTrigger.focus();
  }
}

function showBulkTagModal(): void {
  if (selectedPromptIds.size === 0) return;

  // Store trigger element for focus return
  bulkTagModalTrigger = (event as unknown as { target: HTMLElement }).target || null;
  const modal = document.getElementById('bulk-tag-modal');
  const countElement = document.getElementById('bulk-tag-count');
  if (countElement) {
    countElement.textContent = String(selectedPromptIds.size);
  }
  if (modal) {
    modal.classList.remove(HIDDEN_CLASS);
    // Move focus to first focusable element in modal
    focusFirstElement(modal);
  }
}

function hideBulkTagModal(): void {
  const modal = document.getElementById('bulk-tag-modal');
  if (modal) {
    modal.classList.add(HIDDEN_CLASS);
  }
  // Return focus to trigger element
  if (bulkTagModalTrigger) {
    bulkTagModalTrigger.focus();
  }
}

// Expose modal close handlers for inline template hooks
(
  window as typeof window & { hideBulkDeleteModal?: () => void; hideBulkTagModal?: () => void }
).hideBulkDeleteModal = hideBulkDeleteModal;
(window as typeof window & { hideBulkTagModal?: () => void }).hideBulkTagModal = hideBulkTagModal;

async function performBulkDelete(callbacks: BulkActionsRefreshCallbacks): Promise<void> {
  if (selectedPromptIds.size === 0) return;

  if (!guardOnlineOnly()) return;

  const promptIdsArray = Array.from(selectedPromptIds);

  try {
    const result = await apiFetch<BulkDeleteResponse>('/api/prompts/bulk', {
      method: 'DELETE',
      body: JSON.stringify({
        prompt_ids: promptIdsArray,
      }),
    });

    if (result.success) {
      hideBulkDeleteModal();
      clearSelection();

      // Show success message
      const message = t('bulkDelete.successMessage', {
        deleted: result.deleted_count,
        failed: result.failed_count,
      });
      showNotification(message, 'success');

      // Announce deletion result to screen reader
      announceToScreenReader(
        `${result.deleted_count} prompt(s) deleted successfully. Focus returned to bulk delete button.`,
        'polite'
      );

      // Refresh UI
      await callbacks.loadPrompts();
      await callbacks.loadAvailableTags();
      await callbacks.loadTags();

      // Report errors if any
      if (result.failed_count > 0) {
        reportAppIssue(
          'bulk-delete-partial-failure',
          new Error(`${result.failed_count} prompts failed to delete`),
          { failed_ids: result.failed_ids },
          'warning'
        );
      }
    } else {
      throw new Error(result.detail || 'Bulk deletion failed');
    }
  } catch (error) {
    console.error('Bulk delete error:', error);
    showNotification(t('bulkDelete.errorMessage'), 'error');
    reportAppIssue('bulk-delete-failed', error, {
      prompt_ids: promptIdsArray,
    });
  }
}

async function performBulkTagUpdate(callbacks: BulkActionsRefreshCallbacks): Promise<void> {
  if (selectedPromptIds.size === 0) return;

  if (!guardOnlineOnly()) return;

  const addInput = document.getElementById('bulk-tag-add') as HTMLInputElement | null;
  const removeInput = document.getElementById('bulk-tag-remove') as HTMLInputElement | null;

  const addTags = parseTagInput(addInput?.value ?? '');
  const removeTags = parseTagInput(removeInput?.value ?? '');

  if (addTags.length === 0 && removeTags.length === 0) {
    showNotification(t('messages.bulkTagProvideAtLeastOne'), 'info');
    return;
  }

  try {
    await apiFetch('/api/tags/bulk-update', {
      method: 'POST',
      body: JSON.stringify({
        prompt_ids: Array.from(selectedPromptIds),
        add: addTags,
        remove: removeTags,
        confirm: true,
      }),
    });

    hideBulkTagModal();
    clearSelection();
    if (addInput) addInput.value = '';
    if (removeInput) removeInput.value = '';

    await callbacks.loadPrompts();
    await callbacks.loadAvailableTags();
    await callbacks.loadTags();

    showNotification(t('messages.bulkTagUpdateSuccess'), 'success');
  } catch (error) {
    reportAppIssue('bulk-tag-update', error, {
      promptCount: selectedPromptIds.size,
    });
    showNotification(t('messages.bulkTagUpdateFailed'), 'error');
  }
}
