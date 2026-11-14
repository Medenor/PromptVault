/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import type { PromptResponse } from '@/types';
import { deleteSkill, isSkillItem } from '@/skills/skill-api';
import { t, tUnsafe } from '@/utils/i18n';
import { apiFetch, apiGet } from '@/utils/api';
import { showNotification } from '@/utils/notifications';
import { confirmAsync } from '@/utils/dialogs';
import {
  detectPlaceholders,
  substitutePlaceholders,
  type PlaceholderToken,
} from '@/utils/placeholders';
import { createModal } from '@components';
import { escapeHtml, guardOnlineOnly, hideElement, reportAppIssue, showElement } from './shared';
import { clearPromptFormErrors, showPromptErrorSummary, showPromptFieldError } from './prompt-form';
import {
  commitTagInput,
  getTagInputElement,
  loadAvailableTags,
  setSelectedTags,
} from './tag-autocomplete';
import { clearVersionCache } from './versions';
import { promptCache } from './prompt-list';
import type { PromptFieldError, PromptId } from './types';

export interface PromptEditorRefreshCallbacks {
  isAnyFilterActive: () => boolean;
  performSearch: () => Promise<void>;
  loadPrompts: () => Promise<void>;
  loadTags: () => Promise<void>;
  setPaginationControlsVisible: (visible: boolean) => void;
}

let refreshCallbacks: PromptEditorRefreshCallbacks | null = null;

export function setPromptEditorRefreshCallbacks(callbacks: PromptEditorRefreshCallbacks): void {
  refreshCallbacks = callbacks;
}

function requireCallbacks(): PromptEditorRefreshCallbacks {
  if (!refreshCallbacks) {
    throw new Error('Prompt editor refresh callbacks not initialized');
  }
  return refreshCallbacks;
}

export function showNewPromptForm(): void {
  if (!guardOnlineOnly()) return;

  const promptEditor = document.getElementById('prompt-editor');
  const promptsList = document.getElementById('prompts-list');
  const pullRefreshToolbar = document.getElementById('pull-refresh-toolbar');

  history.pushState({ modal: 'editor' }, '');
  showElement(promptEditor);
  const promptForm = document.getElementById('prompt-form') as HTMLFormElement | null;
  promptForm?.reset();
  setSelectedTags([]);
  const tagInput = getTagInputElement();
  if (tagInput) {
    tagInput.value = '';
  }
  hideElement(promptsList);
  hideElement(pullRefreshToolbar);
  requireCallbacks().setPaginationControlsVisible(false);
}

export function hidePromptEditor(): void {
  const promptEditor = document.getElementById('prompt-editor');
  const promptsList = document.getElementById('prompts-list');
  const pullRefreshToolbar = document.getElementById('pull-refresh-toolbar');

  hideElement(promptEditor);
  showElement(promptsList);
  showElement(pullRefreshToolbar);
  requireCallbacks().setPaginationControlsVisible(true);
}

export async function handlePromptSubmit(event: SubmitEvent): Promise<void> {
  event.preventDefault();

  const form = event.currentTarget as HTMLFormElement | null;
  if (!form) {
    return;
  }

  if (!guardOnlineOnly()) return;

  const tagInput = getTagInputElement();
  if (tagInput) {
    commitTagInput(tagInput);
  }
  const formData = new FormData(form);
  const isEditMode = form.dataset.mode === 'edit';
  const promptId = form.dataset.id;

  clearPromptFormErrors();

  // Client-side required checks to avoid native browser messages
  const titleValue = formData.get('title');
  const title = typeof titleValue === 'string' ? titleValue.trim() : '';
  const promptValue = formData.get('prompt');
  const promptContent = typeof promptValue === 'string' ? promptValue.trim() : '';
  const errors: PromptFieldError[] = [];

  if (!title) {
    errors.push({
      fieldId: 'prompt-title',
      errorId: 'prompt-title-error',
      messageKey: 'validation.titleRequired',
    });
  }

  if (!promptContent) {
    errors.push({
      fieldId: 'prompt-content',
      errorId: 'prompt-content-error',
      messageKey: 'validation.contentRequired',
    });
  }

  // Validate semantic version format if provided
  const semVerValue = formData.get('semantic_version');
  const semVer = typeof semVerValue === 'string' ? semVerValue.trim() : '';
  if (semVer && !/^\d+\.\d+\.\d+$/.test(semVer)) {
    const semVerError = document.getElementById('semantic-version-error');
    if (semVerError) {
      semVerError.textContent = t('validation.semanticVersionFormat');
    }
    const semVerInput = document.getElementById('semantic-version') as HTMLInputElement | null;
    semVerInput?.focus();
    return;
  } else {
    const semVerError = document.getElementById('semantic-version-error');
    if (semVerError) semVerError.textContent = '';
  }

  if (errors.length > 0) {
    errors.forEach((err) => {
      showPromptFieldError(err.fieldId, err.errorId, err.messageKey, false);
    });
    showPromptErrorSummary(errors, escapeHtml);
    return;
  }

  try {
    let url = '/api/prompts';
    let method = 'POST';

    if (isEditMode && promptId) {
      url = `/api/prompts/${promptId}`;
      method = 'PUT';
    }

    const response = await fetch(url, {
      method: method,
      body: formData,
    });

    const responseData = (await response.json()) as { error?: string };

    if (response.ok) {
      history.back();
      // Clear version cache for this prompt since a new version was created
      clearVersionCache(promptId);
      const callbacks = requireCallbacks();
      // Preserve filter state when refreshing the list
      if (callbacks.isAnyFilterActive()) {
        void callbacks.performSearch();
      } else {
        void callbacks.loadPrompts();
      }
      void loadAvailableTags(); // Refresh tag counts for autocomplete
      void callbacks.loadTags(); // Refresh sidebar tag list
      // Reset form mode
      delete form.dataset.mode;
      delete form.dataset.id;
    } else {
      showNotification(
        `${t('messages.error')}: ${responseData.error || t('messages.unknownError')}`,
        'error'
      );
    }
  } catch (error) {
    reportAppIssue('savePrompt', error, {
      mode: isEditMode ? 'edit' : 'create',
      promptId: promptId || null,
    });
    showNotification(t('messages.error'), 'error');
  }
}

export function openPlaceholderForm(
  tokens: PlaceholderToken[],
  onConfirm: (values: Map<string, string>) => void
): void {
  const content = document.createElement('div');
  content.className = 'space-y-3 text-sm text-gray-700';

  const description = document.createElement('p');
  description.className = 'text-gray-600';
  description.textContent = t('placeholders.modalDescription');
  content.appendChild(description);

  const fieldsContainer = document.createElement('div');
  fieldsContainer.className = 'space-y-3';

  const inputs = new Map<string, HTMLInputElement>();
  tokens.forEach((token, index) => {
    const fieldId = `placeholder-field-${index}`;

    const wrapper = document.createElement('div');

    const label = document.createElement('label');
    label.setAttribute('for', fieldId);
    label.className = 'block text-sm font-medium text-gray-700 mb-1';
    label.textContent = token.label;
    wrapper.appendChild(label);

    const input = document.createElement('input');
    input.type = 'text';
    input.id = fieldId;
    input.className =
      'w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500';
    wrapper.appendChild(input);

    fieldsContainer.appendChild(wrapper);
    inputs.set(token.raw, input);
  });

  content.appendChild(fieldsContainer);

  const modal = createModal({
    id: 'placeholder-fill-modal',
    title: t('placeholders.modalTitle'),
    content,
    ariaLabel: t('placeholders.modalAriaLabel'),
    size: 'md',
    actions: [
      {
        label: t('placeholders.cancelButton'),
        variant: 'secondary',
        onClick: () => {
          modal.close();
        },
      },
      {
        label: t('placeholders.copyButton'),
        variant: 'primary',
        onClick: () => {
          const values = new Map<string, string>();
          inputs.forEach((input, raw) => {
            if (input.value !== '') {
              values.set(raw, input.value);
            }
          });
          modal.close();
          onConfirm(values);
        },
      },
    ],
    closeOnEscape: true,
    closeOnBackdrop: true,
    showClose: true,
  });

  document.body.appendChild(modal.element);
  modal.open();
}

async function writeTextToClipboardRaw(text: string): Promise<void> {
  if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
    try {
      await navigator.clipboard.writeText(text);
      return;
    } catch (error) {
      reportAppIssue('clipboardWrite', error, { strategy: 'navigator.clipboard' }, 'warning');
    }
  }

  const textArea = document.createElement('textarea');
  textArea.value = text;
  textArea.setAttribute('readonly', '');
  textArea.className = 'clipboard-helper';
  document.body.appendChild(textArea);
  try {
    textArea.focus();
    textArea.select();
    document.execCommand('copy');
  } finally {
    document.body.removeChild(textArea);
  }
}

export async function copyPromptWithVersion(id: PromptId): Promise<void> {
  try {
    const response = await fetch(`/api/prompts/${id}/copy-with-version`, { method: 'POST' });

    if (response.status === 409) {
      showNotification(t('version.noVersionForCopy'), 'error');
      return;
    }

    if (!response.ok) {
      showNotification(t('messages.copyFailed'), 'error');
      return;
    }

    const data = (await response.json()) as { content: string; semantic_version: string };

    const tokens = detectPlaceholders(data.content);
    if (tokens.length === 0) {
      await writeTextToClipboardRaw(data.content);
      showNotification(t('version.copiedWithMetadata'), 'success');
      return;
    }

    openPlaceholderForm(tokens, (values) => {
      try {
        const finalText = substitutePlaceholders(data.content, values);
        void writeTextToClipboardRaw(finalText)
          .then(() => {
            showNotification(t('version.copiedWithMetadata'), 'success');
          })
          .catch((error) => {
            reportAppIssue('copyPromptWithVersion', error, { promptId: id });
            showNotification(t('messages.copyFailed'), 'error');
          });
      } catch (error) {
        reportAppIssue('copyPromptWithVersion', error, { promptId: id });
        showNotification(t('messages.copyFailed'), 'error');
      }
    });
  } catch (error) {
    reportAppIssue('copyPromptWithVersion', error, { promptId: id });
    showNotification(t('messages.copyFailed'), 'error');
  }
}

export async function copyPrompt(id: PromptId): Promise<void> {
  const cachedPrompt = promptCache[id];

  if (cachedPrompt && !isSkillItem(cachedPrompt) && typeof cachedPrompt.prompt === 'string') {
    copyPromptContent(cachedPrompt.prompt, id);
    return;
  }

  try {
    const prompt = await apiGet<PromptResponse>(`/api/prompts/${id}`);
    promptCache[id] = prompt;
    copyPromptContent(prompt.prompt, id);
  } catch (error) {
    reportAppIssue('copyPrompt', error, { promptId: id });
    showCopyFeedback(id, 'messages.copyFailed');
  }
}

function copyPromptContent(content: string, id: PromptId): void {
  const tokens = detectPlaceholders(content);
  if (tokens.length === 0) {
    copyTextToClipboard(content, id);
    return;
  }

  openPlaceholderForm(tokens, (values) => {
    try {
      const finalText = substitutePlaceholders(content, values);
      copyTextToClipboard(finalText, id);
    } catch (error) {
      reportAppIssue('copyPromptContent', error, { promptId: id });
      showCopyFeedback(id, 'messages.copyFailed');
    }
  });
}

function copyTextToClipboard(textToCopy: string, id: PromptId): void {
  if (typeof textToCopy !== 'string') {
    showCopyFeedback(id, 'messages.copyFailed');
    return;
  }

  // Try modern Clipboard API first
  if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
    navigator.clipboard
      .writeText(textToCopy)
      .then(() => {
        showCopyFeedback(id, 'messages.copied');
      })
      .catch((error) => {
        reportAppIssue('clipboardWrite', error, { strategy: 'navigator.clipboard' }, 'warning');
        fallbackCopyTextToClipboard(textToCopy, id);
      });
    return;
  }

  // Fallback for older browsers or non-HTTPS
  fallbackCopyTextToClipboard(textToCopy, id);
}

function fallbackCopyTextToClipboard(text: string, id: PromptId): void {
  // Create a temporary textarea element
  const textArea = document.createElement('textarea');
  textArea.value = text;
  textArea.setAttribute('readonly', '');
  textArea.className = 'clipboard-helper';
  document.body.appendChild(textArea);

  try {
    textArea.focus();
    textArea.select();
    textArea.setSelectionRange(0, textArea.value.length);

    // Modern Clipboard API is tried first, this fallback is for older browsers/non-HTTPS
    // Note: document.execCommand is deprecated but necessary for browser compatibility
    const successful = document.execCommand('copy');
    if (successful) {
      showCopyFeedback(id, 'messages.copied');
    } else {
      showCopyFeedback(id, 'messages.copyFailed');
    }
  } catch (error) {
    reportAppIssue('clipboardFallback', error, {}, 'warning');
    showCopyFeedback(id, 'messages.copyFailed');
  } finally {
    document.body.removeChild(textArea);
  }
}

function showCopyFeedback(id: PromptId, message: string): void {
  const btn = document.querySelector<HTMLButtonElement>(`.copy-btn[data-id="${id}"]`);
  if (btn) {
    const originalText = btn.textContent ?? '';
    // Use translated message if it's a key, otherwise use as-is
    const translatedMessage = tUnsafe(message) !== message ? tUnsafe(message) : message;
    btn.textContent = translatedMessage;
    setTimeout(() => (btn.textContent = originalText), 2000);
  }
}

export async function editPrompt(id: PromptId): Promise<void> {
  if (!guardOnlineOnly()) return;

  let prompt: PromptResponse;
  try {
    prompt = await apiGet<PromptResponse>(`/api/prompts/${id}`);
    promptCache[id] = prompt;
  } catch (error) {
    reportAppIssue('loadPromptForEdit', error, { promptId: id });
    showNotification(t('messages.error'), 'error');
    return;
  }

  try {
    // Show editor without resetting form
    history.pushState({ modal: 'editor' }, '');
    showElement(document.getElementById('prompt-editor'));
    hideElement(document.getElementById('prompts-list'));
    hideElement(document.getElementById('pull-refresh-toolbar'));
    requireCallbacks().setPaginationControlsVisible(false);

    // Populate form
    const promptTitle = document.getElementById('prompt-title') as HTMLInputElement | null;
    const promptContent = document.getElementById('prompt-content') as HTMLTextAreaElement | null;
    const promptCategory = document.getElementById('prompt-category') as HTMLInputElement | null;
    const commitMessage = document.getElementById('commit-message') as HTMLInputElement | null;
    if (promptTitle) promptTitle.value = prompt.title || '';
    if (promptContent) promptContent.value = prompt.prompt || '';
    if (promptCategory) promptCategory.value = prompt.category || '';
    setSelectedTags(prompt.tags ? prompt.tags : []);
    if (commitMessage) commitMessage.value = ''; // Clear commit message for new edit
    const semVerInput = document.getElementById('semantic-version') as HTMLInputElement | null;
    if (semVerInput) semVerInput.value = prompt.semantic_version || '';

    // Change form to update mode
    const form = document.getElementById('prompt-form') as HTMLFormElement | null;
    if (form) {
      form.dataset.mode = 'edit';
      form.dataset.id = id;
    }
  } catch (error) {
    reportAppIssue('loadPromptForEdit', error, { promptId: id });
  }
}

export async function deletePrompt(id: PromptId): Promise<void> {
  if (!guardOnlineOnly()) return;

  // A skill is deleted permanently (no undo), so it gets its own wording
  // (FR-023) and goes through the skills endpoint.
  const cached = promptCache[id];
  const isSkill = cached !== undefined && isSkillItem(cached);

  const confirmed = await confirmAsync(
    isSkill
      ? {
          title: t('skills.delete.confirmTitle'),
          message: t('skills.delete.confirmPermanent'),
          confirmLabel: t('skills.delete.confirmButton'),
          cancelLabel: t('actions.cancel') || 'Cancel',
        }
      : {
          title: t('actions.confirmDelete') || 'Confirm',
          message: t('messages.confirmDelete') || 'Are you sure?',
          confirmLabel: t('actions.delete') || 'Delete',
          cancelLabel: t('actions.cancel') || 'Cancel',
        }
  );
  if (!confirmed) return;

  try {
    if (isSkill) {
      await deleteSkill(parseInt(id, 10));
    } else {
      await apiFetch<void>(`/api/prompts/${id}`, { method: 'DELETE' });
    }
    // If we get here, delete succeeded (apiFetch throws on error)
    const callbacks = requireCallbacks();
    // Preserve filter state when refreshing the list
    if (callbacks.isAnyFilterActive()) {
      void callbacks.performSearch();
    } else {
      void callbacks.loadPrompts();
    }
    void loadAvailableTags(); // Refresh tag counts for autocomplete
    void callbacks.loadTags(); // Refresh sidebar tag list
  } catch (error) {
    reportAppIssue('deletePrompt', error, { promptId: id });
    showNotification(t('messages.error'), 'error');
  }
}

function setFavoriteButtonA11y(button: HTMLButtonElement, isFavorite: boolean): void {
  button.setAttribute('aria-pressed', isFavorite ? 'true' : 'false');
  const label = isFavorite ? t('actions.removeFavorite') : t('actions.addFavorite');
  button.setAttribute('aria-label', label);
  button.title = label;
}

export async function toggleFavorite(id: PromptId): Promise<void> {
  try {
    // Optimistic update - immediately toggle the UI
    const favoriteBtn = document.querySelector<HTMLButtonElement>(`.favorite-btn[data-id="${id}"]`);
    if (favoriteBtn) {
      const currentFavorite =
        typeof promptCache[id]?.favorite === 'boolean'
          ? promptCache[id].favorite
          : favoriteBtn.getAttribute('aria-pressed') === 'true' ||
            (favoriteBtn.textContent ?? '').trim() === '★';
      const nextFavorite = !currentFavorite;

      favoriteBtn.textContent = nextFavorite ? '★' : '☆';
      setFavoriteButtonA11y(favoriteBtn, nextFavorite);

      // Also update the cached prompt data
      if (promptCache[id]) {
        promptCache[id].favorite = nextFavorite;
      }
    }

    // Make API call to persist the change
    await apiFetch<void>(`/api/prompts/${id}/favorite`, {
      method: 'PUT',
    });
  } catch (error) {
    // Revert optimistic update on error
    const favoriteBtn = document.querySelector<HTMLButtonElement>(`.favorite-btn[data-id="${id}"]`);
    if (favoriteBtn) {
      const currentFavorite =
        typeof promptCache[id]?.favorite === 'boolean'
          ? promptCache[id].favorite
          : favoriteBtn.getAttribute('aria-pressed') === 'true' ||
            (favoriteBtn.textContent ?? '').trim() === '★';
      const revertedFavorite = !currentFavorite;

      favoriteBtn.textContent = revertedFavorite ? '★' : '☆';
      setFavoriteButtonA11y(favoriteBtn, revertedFavorite);

      // Also revert the cached prompt data
      if (promptCache[id]) {
        promptCache[id].favorite = revertedFavorite;
      }
    }

    reportAppIssue('toggleFavorite', error, { promptId: id });
    showNotification(t('messages.error'), 'error');
  }
}
