/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * PromptVault main app logic (TypeScript).
 */

import '@/form-validation';
import type { PromptResponse, PromptListResponse } from '@/types';
import type { TranslationKey } from '@/types/i18n';
import { initI18n, t, tUnsafe, updateStaticTranslations, changeLanguage } from '@/utils/i18n';

interface TagInfo {
  name: string;
  count: number;
}

interface VersionSummary {
  version_id: string;
  version_number: number;
  timestamp: string;
  author: string;
  message: string;
  parents: string[];
}

interface VersionHistoryResponse {
  versions: VersionSummary[];
}

interface VersionDiffResponse {
  v1_id: string;
  v2_id: string;
  changes: Record<string, { old: unknown; new: unknown }>;
}

interface VersionCacheEntry {
  timestamp: number;
  data: VersionHistoryResponse;
}

interface DiffCacheEntry {
  timestamp: number;
  data: VersionDiffResponse;
}

interface VersionSortItem {
  id: string;
  number: number;
}

interface BulkDeleteResponse {
  success: boolean;
  deleted_count: number;
  failed_count: number;
  failed_ids: number[];
  detail?: string;
}

type PromptId = string;

let promptCache: Record<string, PromptResponse> = {};
let lastSelectedPromptId: number | null = null; // Track the last selected prompt for keyboard shortcuts
const selectedPromptIds: Set<number> = new Set(); // Track selected prompts for bulk operations

const HIDDEN_CLASS = 'is-hidden';
const ERROR_VISIBLE_CLASS = 'validation-error-visible';
const APP_COMPONENT = 'app';

function reportAppIssue(
  action: string,
  error: unknown,
  metadata: Record<string, unknown> = {},
  severity: 'error' | 'warning' = 'error'
): void {
  const logger = window.FrontendLogger;
  if (logger && typeof logger.reportError === 'function') {
    logger.reportError(APP_COMPONENT, action, error, metadata, severity);
  }
  const message = `[PromptVault][app] ${action}`;
  if (severity === 'warning') {
    console.warn(message, error, metadata);
  } else {
    console.error(message, error, metadata);
  }
}

function showElement(element: HTMLElement | null): void {
  if (element) {
    element.classList.remove(HIDDEN_CLASS);
  }
}

function hideElement(element: HTMLElement | null): void {
  if (element) {
    element.classList.add(HIDDEN_CLASS);
  }
}

function clearPromptFormErrors(): void {
  const errorFields = [
    'prompt-title-error',
    'prompt-content-error',
    'prompt-tags-error',
    'commit-message-error',
  ];
  errorFields.forEach((id) => {
    const el = document.getElementById(id);
    if (el) {
      el.textContent = '';
      delete el.dataset.errorKey;
      el.classList.remove(ERROR_VISIBLE_CLASS);
    }
  });
  const inputs = ['prompt-title', 'prompt-content', 'prompt-tags', 'commit-message'];
  inputs.forEach((id) => {
    const field = document.getElementById(id);
    if (field) {
      field.classList.remove('field-error');
      field.removeAttribute('aria-invalid');
    }
  });
  const banner = document.getElementById('validation-error-banner');
  if (banner) {
    banner.style.display = 'none';
  }
}

function showPromptFieldError(fieldId: string, errorId: string, messageKey: TranslationKey): void {
  const errorEl = document.getElementById(errorId);
  const field = document.getElementById(fieldId);
  const message = t(messageKey);
  if (errorEl) {
    errorEl.textContent = message;
    errorEl.dataset.errorKey = messageKey;
    errorEl.classList.add(ERROR_VISIBLE_CLASS);
  }
  if (field) {
    field.classList.add('field-error');
    field.setAttribute('aria-invalid', 'true');
    field.focus();
  }
}

function toggleElement(element: HTMLElement | null, shouldShow: boolean): void {
  if (element) {
    element.classList.toggle(HIDDEN_CLASS, !shouldShow);
  }
}

async function initializeApp(): Promise<void> {
  // Event listeners (safe to setup before auth)
  setupEventListeners();
  initializeBulkActions();

  // CRITICAL: Check authentication BEFORE loading any data
  // This prevents content flash before redirect
  await checkAdminAccess();

  // Only load data if authentication succeeded
  // (if auth failed, checkAdminAccess redirects to login)
  void loadPrompts();
  void loadCategories();
  void loadTags();
}

async function checkAdminAccess(): Promise<void> {
  try {
    console.log('Checking authentication...');
    const response = await fetch('/api/auth/me', {
      credentials: 'include',
    });

    console.log('Response status:', response.status);
    if (response.ok) {
      const data = (await response.json()) as { role?: string };
      console.log('User data:', data);
      console.log('User role:', data.role);

      // Authentication successful - show the app
      const loadingOverlay = document.getElementById('auth-loading-overlay');
      const appDiv = document.querySelector('.app') as HTMLElement | null;
      if (loadingOverlay) loadingOverlay.style.display = 'none';
      if (appDiv) appDiv.style.display = 'block';

      if (data.role === 'admin') {
        console.log('User is admin, showing button');
        const adminBtn = document.getElementById('admin-btn');
        console.log('Admin button element:', adminBtn);
        if (adminBtn) {
          adminBtn.style.display = '';
          console.log('Admin button should now be visible');
        }
      } else {
        console.log('User is not admin, role is:', data.role);
      }
    } else if (response.status === 401) {
      // Session revoked or expired, redirect to login immediately
      console.log('Session invalid, redirecting to login');
      window.location.href = '/auth/login';
    } else {
      console.log('Response not OK:', response.statusText);
      // For other errors, also redirect to login for security
      window.location.href = '/auth/login';
    }
  } catch (error) {
    console.error('Failed to check authentication:', error);
    // On error, redirect to login for security
    window.location.href = '/auth/login';
  }
}

// Global search state
let searchState: {
  searchTerm: string;
  category: string;
  tag: string;
  favorites: boolean;
  caseSensitive: boolean;
  isLoading: boolean;
} = {
  searchTerm: '',
  category: 'all',
  tag: 'all',
  favorites: false,
  caseSensitive: false,
  isLoading: false,
};

function setupEventListeners(): void {
  // Language selector
  const languageSelector = document.getElementById('language-selector') as HTMLSelectElement | null;
  languageSelector?.addEventListener('change', handleLanguageChange);

  // New prompt button
  const newPromptBtn = document.getElementById('new-prompt-btn');
  newPromptBtn?.addEventListener('click', showNewPromptForm);

  // Import/Export button (navigates to import/export page)
  const importExportBtn = document.getElementById('import-export-btn');
  importExportBtn?.addEventListener('click', function () {
    window.location.href = '/import-export';
  });

  // Logout button
  const logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      void logout();
    });
  }

  // Form handling
  const promptForm = document.getElementById('prompt-form');
  promptForm?.addEventListener('submit', (event) => {
    void handlePromptSubmit(event as SubmitEvent);
  });
  const cancelBtn = document.getElementById('cancel-btn');
  cancelBtn?.addEventListener('click', hidePromptEditor);

  // Category and tag filtering
  const categoriesList = document.getElementById('categories-list');
  categoriesList?.addEventListener('click', handleCategoryFilter);
  const tagsList = document.getElementById('tags-list');
  tagsList?.addEventListener('click', handleTagFilter);
  const favoritesFilter = document.getElementById('favorites-filter');
  favoritesFilter?.addEventListener('change', handleFavoritesFilter);

  // Modal close
  const closeBtn = document.querySelector('.close');
  closeBtn?.addEventListener('click', hideModal);
  window.addEventListener('click', function (event) {
    const modal = document.getElementById('prompt-modal');
    if (event.target === modal) {
      hideModal();
    }
  });

  // Version history modal close
  const closeVersionHistoryBtn = document.getElementById('close-version-history-btn');
  if (closeVersionHistoryBtn) {
    closeVersionHistoryBtn.addEventListener('click', hideVersionHistoryModal);
  }

  // Diff modal close
  const closeDiffBtn = document.getElementById('close-diff-btn');
  if (closeDiffBtn) {
    closeDiffBtn.addEventListener('click', hideDiffModal);
  }

  // Revert confirmation modal close
  const cancelRevertBtn = document.getElementById('cancel-revert-btn');
  if (cancelRevertBtn) {
    cancelRevertBtn.addEventListener('click', hideRevertConfirmationModal);
  }

  // Compare versions button
  const compareVersionsBtn = document.getElementById('compare-versions-btn');
  if (compareVersionsBtn) {
    compareVersionsBtn.addEventListener('click', () => {
      void showDiffModal();
    });
  }

  // Keyboard shortcuts
  document.addEventListener('keydown', handleKeyboardShortcuts);

  // Add tooltips
  addTooltips();

  // Search functionality
  setupSearchEventListeners();

  // Tag autocomplete
  setupTagAutocomplete();
}

async function loadPrompts(): Promise<void> {
  try {
    const response = await fetch('/api/prompts');
    const data = (await response.json()) as PromptListResponse;

    // Hide search results info when loading all prompts initially
    const searchResultsInfo = document.getElementById('search-results-info');
    if (searchResultsInfo) {
      hideElement(searchResultsInfo);
    }

    renderPrompts(data.prompts || {});
  } catch (error) {
    reportAppIssue('loadPrompts', error);
  }
}

async function loadCategories(): Promise<void> {
  try {
    const response = await fetch('/api/categories');
    const data = (await response.json()) as { categories: string[] };
    renderCategories(data.categories || []);
  } catch (error) {
    reportAppIssue('loadCategories', error);
  }
}

async function loadTags(): Promise<void> {
  try {
    const response = await fetch('/api/tags');
    const data = (await response.json()) as { tags: TagInfo[] };
    renderTags(data.tags || []);
  } catch (error) {
    reportAppIssue('loadTags', error);
  }
}

function renderPrompts(prompts: Record<string, PromptResponse>): void {
  promptCache = { ...prompts };
  const container = document.getElementById('prompts-list') as HTMLElement | null;
  const searchResultsInfo = document.getElementById('search-results-info');
  if (!container) {
    return;
  }
  container.innerHTML = '';

  // Handle case when there are no prompts at all
  if (Object.keys(prompts).length === 0) {
    container.innerHTML = `<div class="no-results-message">${t('search.emptyState')}</div>`;
    if (searchResultsInfo) {
      hideElement(searchResultsInfo);
    }
    return;
  }

  for (const [id, prompt] of Object.entries(prompts)) {
    const promptElement = createPromptElement(id, prompt);
    container.appendChild(promptElement);
  }
}

function createPromptElement(id: string, prompt: PromptResponse): HTMLDivElement {
  const div = document.createElement('div');
  div.className = 'prompt-item';
  div.dataset.id = id;

  // Add selected class if prompt is in selection
  if (selectedPromptIds.has(parseInt(id))) {
    div.classList.add('selected');
  }

  // Create checkbox for bulk selection
  const checkbox = document.createElement('input');
  checkbox.type = 'checkbox';
  checkbox.className = 'prompt-checkbox';
  checkbox.dataset.promptId = id;
  checkbox.checked = selectedPromptIds.has(parseInt(id));
  checkbox.addEventListener('change', (event) => {
    const target = event.target as HTMLInputElement | null;
    handleCheckboxChange(parseInt(id, 10), target?.checked ?? false);
    event.stopPropagation(); // Prevent triggering the div click event
  });

  div.innerHTML = `
        <div class="prompt-header">
            <h4>${prompt.title}</h4>
            <div class="prompt-actions">
                <button class="favorite-btn" data-id="${id}">
                    ${prompt.favorite ? '★' : '☆'}
                </button>
                <button class="history-btn" data-id="${id}" data-i18n="version.history">History</button>
                <button class="copy-btn" data-id="${id}" data-i18n="actions.copy">Copy</button>
                <button class="edit-btn" data-id="${id}" data-i18n="actions.edit">Edit</button>
                <button class="delete-btn" data-id="${id}" data-i18n="actions.delete">Delete</button>
            </div>
        </div>
        <div class="prompt-meta">
            <span class="category">${prompt.category || t('categories.noCategory')}</span>
            ${prompt.tags ? `<span class="tags">${prompt.tags.join(', ')}</span>` : ''}
        </div>
        <div class="prompt-content">${truncateText(prompt.prompt, 100)}</div>
    `;

  // Insert checkbox before the favorite button in prompt-actions
  const promptActions = div.querySelector('.prompt-actions') as HTMLElement | null;
  const favBtn = promptActions?.querySelector('.favorite-btn') as HTMLElement | null;
  if (promptActions && favBtn) {
    promptActions.insertBefore(checkbox, favBtn);
  } else if (promptActions) {
    promptActions.appendChild(checkbox);
  }

  // Update translations for dynamically created elements
  div.querySelectorAll('[data-i18n]').forEach((element) => {
    const key = element.getAttribute('data-i18n');
    if (key) {
      element.textContent = tUnsafe(key);
    }
  });

  // Add event listeners and tooltips
  const copyBtn = div.querySelector('.copy-btn') as HTMLButtonElement | null;
  copyBtn?.addEventListener('click', () => {
    lastSelectedPromptId = parseInt(id, 10);
    void copyPrompt(id);
  });
  if (copyBtn) {
    copyBtn.title = t('actions.copy');
  }

  const editBtn = div.querySelector('.edit-btn') as HTMLButtonElement | null;
  editBtn?.addEventListener('click', () => {
    lastSelectedPromptId = parseInt(id, 10);
    void editPrompt(id);
  });
  if (editBtn) {
    editBtn.title = t('actions.edit');
  }

  const deleteBtn = div.querySelector('.delete-btn') as HTMLButtonElement | null;
  deleteBtn?.addEventListener('click', () => {
    lastSelectedPromptId = parseInt(id, 10);
    void deletePrompt(id);
  });
  if (deleteBtn) {
    deleteBtn.title = t('actions.delete');
  }

  const favoriteBtn = div.querySelector('.favorite-btn') as HTMLButtonElement | null;
  favoriteBtn?.addEventListener('click', () => {
    lastSelectedPromptId = parseInt(id, 10);
    void toggleFavorite(id);
  });
  if (favoriteBtn) {
    favoriteBtn.title = t('actions.favorite');
  }

  const historyBtn = div.querySelector('.history-btn') as HTMLButtonElement | null;
  historyBtn?.addEventListener('click', () => {
    lastSelectedPromptId = parseInt(id, 10);
    showVersionHistoryModal(parseInt(id, 10));
  });
  if (historyBtn) {
    historyBtn.title = t('version.history');
  }

  // Track prompt selection on click
  div.addEventListener('click', () => {
    lastSelectedPromptId = parseInt(id, 10);
  });

  return div;
}

function renderCategories(categories: string[]): void {
  const list = document.getElementById('categories-list');
  if (!list) return;
  // Clear existing categories except "All Prompts"
  const allPromptsItem = list.querySelector('[data-category="all"]');
  list.innerHTML = '';
  if (allPromptsItem) {
    list.appendChild(allPromptsItem);
  }

  categories.forEach((category) => {
    const li = document.createElement('li');
    li.dataset.category = category;
    li.textContent = category;
    list.appendChild(li);
  });
}

function renderTags(tags: TagInfo[]): void {
  const list = document.getElementById('tags-list');
  if (!list) return;
  // Clear existing tags except "All Tags"
  const allTagsItem = list.querySelector('[data-tag="all"]');
  list.innerHTML = '';
  if (allTagsItem) {
    list.appendChild(allTagsItem);
  }

  tags.forEach((tag) => {
    const li = document.createElement('li');
    li.dataset.tag = tag.name;
    li.textContent = `${tag.name} (${tag.count})`;
    list.appendChild(li);
  });
}

function showNewPromptForm() {
  const promptEditor = document.getElementById('prompt-editor');
  const promptsList = document.getElementById('prompts-list');

  showElement(promptEditor);
  const promptForm = document.getElementById('prompt-form') as HTMLFormElement | null;
  promptForm?.reset();
  hideElement(promptsList);
}

function hidePromptEditor() {
  const promptEditor = document.getElementById('prompt-editor');
  const promptsList = document.getElementById('prompts-list');

  hideElement(promptEditor);
  showElement(promptsList);
}

async function handlePromptSubmit(event: SubmitEvent): Promise<void> {
  event.preventDefault();

  const form = event.currentTarget as HTMLFormElement | null;
  if (!form) {
    return;
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
  let hasError = false;

  if (!title) {
    showPromptFieldError('prompt-title', 'prompt-title-error', 'validation.titleRequired');
    hasError = true;
  }

  if (!promptContent) {
    showPromptFieldError('prompt-content', 'prompt-content-error', 'validation.contentRequired');
    hasError = true;
  }

  if (hasError) {
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
      hidePromptEditor();
      // Clear version cache for this prompt since a new version was created
      clearVersionCache(promptId);
      void loadPrompts(); // Refresh the list
      void loadAvailableTags(); // Refresh tag counts for autocomplete
      void loadTags(); // Refresh sidebar tag list
      // Reset form mode
      delete form.dataset.mode;
      delete form.dataset.id;
    } else {
      alert(`${t('messages.error')}: ${responseData.error || t('messages.unknownError')}`);
    }
  } catch (error) {
    reportAppIssue('savePrompt', error, {
      mode: isEditMode ? 'edit' : 'create',
      promptId: promptId || null,
    });
    alert(t('messages.error'));
  }
}

async function copyPrompt(id: PromptId): Promise<void> {
  const cachedPrompt = promptCache[id];

  if (cachedPrompt && typeof cachedPrompt.prompt === 'string') {
    copyTextToClipboard(cachedPrompt.prompt, id);
    return;
  }

  try {
    const response = await fetch(`/api/prompts/${id}`);
    if (!response.ok) {
      throw new Error(`Failed to load prompt ${id}: ${response.status}`);
    }
    const prompt = (await response.json()) as PromptResponse;
    promptCache[id] = prompt;
    copyTextToClipboard(prompt.prompt, id);
  } catch (error) {
    reportAppIssue('copyPrompt', error, { promptId: id });
    showCopyFeedback(id, 'messages.copyFailed');
  }
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

async function editPrompt(id: PromptId): Promise<void> {
  try {
    const response = await fetch(`/api/prompts/${id}`);
    if (!response.ok) {
      throw new Error(`Failed to load prompt ${id}: ${response.status}`);
    }
    const prompt = (await response.json()) as PromptResponse;

    promptCache[id] = prompt;

    // Show editor without resetting form
    showElement(document.getElementById('prompt-editor'));
    hideElement(document.getElementById('prompts-list'));

    // Populate form
    const promptTitle = document.getElementById('prompt-title') as HTMLInputElement | null;
    const promptContent = document.getElementById('prompt-content') as HTMLTextAreaElement | null;
    const promptCategory = document.getElementById('prompt-category') as HTMLInputElement | null;
    const promptTags = document.getElementById('prompt-tags') as HTMLInputElement | null;
    const commitMessage = document.getElementById('commit-message') as HTMLInputElement | null;
    if (promptTitle) promptTitle.value = prompt.title || '';
    if (promptContent) promptContent.value = prompt.prompt || '';
    if (promptCategory) promptCategory.value = prompt.category || '';
    if (promptTags) promptTags.value = prompt.tags ? prompt.tags.join(', ') : '';
    if (commitMessage) commitMessage.value = ''; // Clear commit message for new edit

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

async function deletePrompt(id: PromptId): Promise<void> {
  if (!confirm(t('messages.confirmDelete'))) {
    return;
  }

  try {
    const response = await fetch(`/api/prompts/${id}`, {
      method: 'DELETE',
    });

    if (response.ok) {
      void loadPrompts(); // Refresh the list
      void loadAvailableTags(); // Refresh tag counts for autocomplete
      void loadTags(); // Refresh sidebar tag list
    } else {
      alert(t('messages.error'));
    }
  } catch (error) {
    reportAppIssue('deletePrompt', error, { promptId: id });
    alert(t('messages.error'));
  }
}

async function toggleFavorite(id: PromptId): Promise<void> {
  try {
    // Optimistic update - immediately toggle the UI
    const favoriteBtn = document.querySelector<HTMLButtonElement>(`.favorite-btn[data-id="${id}"]`);
    if (favoriteBtn) {
      const currentIcon = favoriteBtn.textContent ?? '';
      const newIcon = currentIcon === '★' ? '☆' : '★';
      favoriteBtn.textContent = newIcon;

      // Also update the cached prompt data
      if (promptCache[id]) {
        promptCache[id].favorite = !promptCache[id].favorite;
      }
    }

    // Make API call to persist the change
    const response = await fetch(`/api/prompts/${id}/favorite`, {
      method: 'PUT',
    });

    if (!response.ok) {
      // Revert optimistic update on error
      const favoriteBtn = document.querySelector<HTMLButtonElement>(
        `.favorite-btn[data-id="${id}"]`
      );
      if (favoriteBtn) {
        const currentIcon = favoriteBtn.textContent ?? '';
        const revertedIcon = currentIcon === '★' ? '☆' : '★';
        favoriteBtn.textContent = revertedIcon;

        // Also revert the cached prompt data
        if (promptCache[id]) {
          promptCache[id].favorite = !promptCache[id].favorite;
        }
      }

      const errorData = (await response.json()) as { error?: string };
      alert(`${t('messages.error')}: ${errorData.error || t('messages.unknownError')}`);
    } else {
      await response.json();
    }
  } catch (error) {
    // Revert optimistic update on network error
    const favoriteBtn = document.querySelector<HTMLButtonElement>(`.favorite-btn[data-id="${id}"]`);
    if (favoriteBtn) {
      const currentIcon = favoriteBtn.textContent ?? '';
      const revertedIcon = currentIcon === '★' ? '☆' : '★';
      favoriteBtn.textContent = revertedIcon;

      // Also revert the cached prompt data
      if (promptCache[id]) {
        promptCache[id].favorite = !promptCache[id].favorite;
      }
    }

    reportAppIssue('toggleFavorite', error, { promptId: id });
    alert(t('messages.error'));
  }
}

function handleCategoryFilter(event: Event): void {
  const target = event.target as HTMLElement | null;
  if (target?.tagName === 'LI') {
    // Update active state
    document.querySelectorAll('#categories-list li').forEach((li) => li.classList.remove('active'));
    target.classList.add('active');

    // Update search state and trigger search
    searchState.category = target.dataset.category || 'all';
    void performSearch();
  }
}

function handleTagFilter(event: Event): void {
  const target = event.target as HTMLElement | null;
  if (target?.tagName === 'LI') {
    // Update active state
    document.querySelectorAll('#tags-list li').forEach((li) => li.classList.remove('active'));
    target.classList.add('active');

    // Update search state and trigger search
    searchState.tag = target.dataset.tag || 'all';
    void performSearch();
  }
}

function handleFavoritesFilter(event: Event): void {
  const target = event.target as HTMLInputElement | null;
  if (!target) return;
  // Update search state and trigger search
  searchState.favorites = target.checked;
  void performSearch();
}

function handleLanguageChange(event: Event): void {
  const target = event.target as HTMLSelectElement | null;
  const selectedLanguage = target?.value;
  if (!selectedLanguage) return;

  changeLanguage(selectedLanguage)
    .then(() => {
      updateStaticTranslations();
      updateVersionHistoryTranslations();
      void loadPrompts();
    })
    .catch((err) => {
      reportAppIssue('changeLanguage', err, { language: selectedLanguage });
    });
}

function updateVersionHistoryTranslations(): void {
  // Update search placeholder
  const searchInput = document.getElementById('version-search') as HTMLInputElement | null;
  if (searchInput) {
    searchInput.placeholder = t('version.searchPlaceholder');
  }

  // Update version item buttons
  document.querySelectorAll('[data-i18n="version.select"]').forEach((element) => {
    element.textContent = t('version.select');
  });

  document.querySelectorAll('[data-i18n="version.revert"]').forEach((element) => {
    element.textContent = t('version.revert');
  });
}

function hideModal() {
  hideElement(document.getElementById('prompt-modal'));
}

function truncateText(text: string, maxLength: number): string {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
}

// Search and Filter Functions
let searchTimeout: ReturnType<typeof setTimeout> | null = null;

function setupSearchEventListeners() {
  // Search input with debouncing
  const searchInput = document.getElementById('search-input') as HTMLInputElement | null;
  if (searchInput) {
    searchInput.addEventListener('input', handleSearchInput);
    searchInput.addEventListener('keydown', function (event) {
      // Clear search on Escape
      if (event.key === 'Escape') {
        clearAllFilters();
      }
    });
  }

  // Clear search button
  const clearSearchBtn = document.getElementById('clear-search-btn');
  if (clearSearchBtn) {
    clearSearchBtn.addEventListener('click', function () {
      const searchInput = document.getElementById('search-input') as HTMLInputElement | null;
      if (searchInput) {
        searchInput.value = '';
        searchState.searchTerm = '';
        toggleElement(clearSearchBtn, false);
        void performSearch();
      }
    });
  }

  // Case sensitive toggle
  const caseSensitiveToggle = document.getElementById(
    'case-sensitive-toggle'
  ) as HTMLInputElement | null;
  if (caseSensitiveToggle) {
    caseSensitiveToggle.addEventListener('change', (event) => {
      const target = event.target as HTMLInputElement | null;
      searchState.caseSensitive = target?.checked ?? false;
      void performSearch();
    });
  }

  // Clear all filters button
  const clearAllFiltersBtn = document.getElementById('clear-all-filters-btn');
  if (clearAllFiltersBtn) {
    clearAllFiltersBtn.addEventListener('click', clearAllFilters);
  }
}

function handleSearchInput(event: Event): void {
  const target = event.target as HTMLInputElement | null;
  if (!target) {
    return;
  }
  const searchTerm = target.value;
  searchState.searchTerm = searchTerm;

  // Show/hide clear search button
  const clearSearchBtn = document.getElementById('clear-search-btn');
  if (clearSearchBtn) {
    toggleElement(clearSearchBtn, searchTerm.length > 0);
  }

  // Clear previous timeout
  if (searchTimeout) {
    clearTimeout(searchTimeout);
  }

  // Debounce search
  searchTimeout = setTimeout(() => {
    void performSearch();
  }, 300);
}

async function performSearch(): Promise<void> {
  if (searchState.isLoading) {
    return; // Don't start new search if one is already running
  }

  searchState.isLoading = true;

  try {
    // Show loading state
    const promptsList = document.getElementById('prompts-list');
    if (promptsList) {
      promptsList.style.opacity = '0.6';
      promptsList.style.pointerEvents = 'none';
    }

    // Build query parameters
    const params = new URLSearchParams();

    if (searchState.searchTerm) {
      params.append('search', searchState.searchTerm);
    }

    if (searchState.category && searchState.category !== 'all') {
      params.append('category', searchState.category);
    }

    if (searchState.tag && searchState.tag !== 'all') {
      params.append('tag', searchState.tag);
    }

    if (searchState.favorites) {
      params.append('favorites', 'true');
    }

    if (searchState.caseSensitive) {
      params.append('case_sensitive', 'true');
    }

    // Make API call
    const response = await fetch(`/api/prompts/search?${params.toString()}`);

    if (!response.ok) {
      throw new Error(`Search failed: ${response.status}`);
    }

    const data = (await response.json()) as PromptListResponse;

    // Update prompts list
    renderPrompts(data.prompts || {});

    // Update result count and handle empty results
    updateSearchResultsInfo(data.prompts || {});
  } catch (error) {
    reportAppIssue('searchPrompts', error, {
      filters: {
        searchTerm: searchState.searchTerm,
        category: searchState.category,
        tag: searchState.tag,
        favorites: searchState.favorites,
        caseSensitive: searchState.caseSensitive,
      },
    });
    showNotification(t('search.error'), 'error');

    // Fallback to showing all prompts
    void loadPrompts();
  } finally {
    searchState.isLoading = false;

    // Remove loading state
    const promptsList = document.getElementById('prompts-list');
    if (promptsList) {
      promptsList.style.opacity = '';
      promptsList.style.pointerEvents = '';
    }
  }
}

function updateSearchResultsInfo(prompts: Record<string, PromptResponse>): void {
  const resultCount = Object.keys(prompts || {}).length;
  const totalCount = Object.keys(promptCache).length;
  const searchResultsInfo = document.getElementById('search-results-info');
  const promptsList = document.getElementById('prompts-list');

  // Handle empty results
  if (resultCount === 0) {
    // Show "No results found" message
    if (searchResultsInfo) {
      searchResultsInfo.className = 'search-results-info no-results';
      searchResultsInfo.textContent = t('search.noResultsInfo');
      showElement(searchResultsInfo);
    }

    // Show empty state in prompts list
    if (promptsList) {
      promptsList.innerHTML = `<div class="no-results-message">${t('search.noResultsMessage')}</div>`;
    }

    // Hide clear filters button
    const clearAllFiltersBtn = document.getElementById('clear-all-filters-btn');
    if (clearAllFiltersBtn) {
      hideElement(clearAllFiltersBtn);
    }

    return;
  }

  // Show results count info
  if (searchResultsInfo) {
    searchResultsInfo.className = 'search-results-info';

    const hasAllResults = resultCount === totalCount;
    let infoText = '';

    if (hasAllResults) {
      infoText = t('search.resultsCount', { count: resultCount });
    } else {
      infoText = t('search.resultsCountWithTotal', { count: resultCount, total: totalCount });
    }

    // Add active filter indicators
    const activeFilters: string[] = [];
    if (searchState.searchTerm) {
      activeFilters.push(
        t('search.filter.search', {
          term: searchState.searchTerm,
          interpolation: { escapeValue: false },
        })
      );
    }
    if (searchState.category && searchState.category !== 'all') {
      activeFilters.push(
        t('search.filter.category', {
          category: searchState.category,
          interpolation: { escapeValue: false },
        })
      );
    }
    if (searchState.tag && searchState.tag !== 'all') {
      activeFilters.push(
        t('search.filter.tag', {
          tag: searchState.tag,
          interpolation: { escapeValue: false },
        })
      );
    }
    if (searchState.favorites) {
      activeFilters.push(t('search.filter.favorites'));
    }
    if (searchState.caseSensitive) {
      activeFilters.push(t('search.filter.caseSensitive'));
    }

    if (activeFilters.length > 0) {
      infoText += ` ${t('search.filteredBy', {
        filters: activeFilters.join(', '),
        interpolation: { escapeValue: false },
      })}`;
    }

    searchResultsInfo.textContent = infoText;
    showElement(searchResultsInfo);
  }

  // Update the clear filters button text to show result count
  const clearAllFiltersBtn = document.getElementById('clear-all-filters-btn');
  if (clearAllFiltersBtn) {
    if (
      resultCount !== totalCount ||
      searchState.searchTerm ||
      searchState.category !== 'all' ||
      searchState.tag !== 'all' ||
      searchState.favorites ||
      searchState.caseSensitive
    ) {
      clearAllFiltersBtn.textContent = t('search.clearFiltersWithCount', { count: resultCount });
      showElement(clearAllFiltersBtn);
    } else {
      hideElement(clearAllFiltersBtn);
    }
  }
}

function clearAllFilters(): void {
  // Reset search state
  searchState = {
    searchTerm: '',
    category: 'all',
    tag: 'all',
    favorites: false,
    caseSensitive: false,
    isLoading: false,
  };

  // Reset UI elements
  const searchInput = document.getElementById('search-input') as HTMLInputElement | null;
  if (searchInput) {
    searchInput.value = '';
  }

  const clearSearchBtn = document.getElementById('clear-search-btn');
  if (clearSearchBtn) {
    hideElement(clearSearchBtn);
  }

  const caseSensitiveToggle = document.getElementById(
    'case-sensitive-toggle'
  ) as HTMLInputElement | null;
  if (caseSensitiveToggle) {
    caseSensitiveToggle.checked = false;
  }

  const favoritesFilter = document.getElementById('favorites-filter') as HTMLInputElement | null;
  if (favoritesFilter) {
    favoritesFilter.checked = false;
  }

  // Reset active states in sidebar
  document.querySelectorAll('#categories-list li').forEach((li) => li.classList.remove('active'));
  document.querySelector('[data-category="all"]')?.classList.add('active');

  document.querySelectorAll('#tags-list li').forEach((li) => li.classList.remove('active'));
  document.querySelector('[data-tag="all"]')?.classList.add('active');

  // Hide clear filters button and search results info
  const clearAllFiltersBtn = document.getElementById('clear-all-filters-btn');
  if (clearAllFiltersBtn) {
    hideElement(clearAllFiltersBtn);
  }

  const searchResultsInfo = document.getElementById('search-results-info');
  if (searchResultsInfo) {
    hideElement(searchResultsInfo);
  }

  // Load all prompts
  void loadPrompts();
}

// Version Control Functions
let currentVersionPromptId: number | null = null;
let selectedVersions: Set<string> = new Set();
let versionCache: Record<string, VersionCacheEntry> = {}; // Cache for version history
let diffCache: Record<string, DiffCacheEntry> = {}; // Cache for diff results
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes in milliseconds

function showVersionHistoryModal(promptId: number): void {
  currentVersionPromptId = promptId;
  selectedVersions.clear();
  showElement(document.getElementById('version-history-modal'));
  // Update search placeholder with current language
  const searchInput = document.getElementById('version-search') as HTMLInputElement | null;
  if (searchInput) {
    searchInput.placeholder = t('version.searchPlaceholder');
  }
  void loadVersionHistory(promptId);
}

function hideVersionHistoryModal(): void {
  hideElement(document.getElementById('version-history-modal'));
  currentVersionPromptId = null;
  selectedVersions.clear();
}

function hideDiffModal(): void {
  hideElement(document.getElementById('diff-modal'));
}

function hideRevertConfirmationModal(): void {
  hideElement(document.getElementById('revert-confirmation-modal'));
}

async function loadVersionHistory(promptId: number): Promise<void> {
  try {
    const versionList = document.getElementById('version-list');
    if (versionList) {
      versionList.innerHTML = '<div class="loading">' + t('messages.loading') + '</div>';
    }

    // Check cache first
    const cacheKey = `versions_${promptId}`;
    if (versionCache[cacheKey] && Date.now() - versionCache[cacheKey].timestamp < CACHE_DURATION) {
      const cachedData = versionCache[cacheKey].data;
      renderVersionHistory(cachedData.versions || []);
      updateCompareButton();
      return;
    }

    const response = await fetch(`/api/prompts/${promptId}/versions`);
    if (!response.ok) {
      throw new Error('Failed to load version history');
    }

    const data = (await response.json()) as VersionHistoryResponse;

    // Cache the result
    versionCache[cacheKey] = {
      data: data,
      timestamp: Date.now(),
    };

    // Store all versions for diff operations
    allVersions = data.versions || [];

    renderVersionHistory(data.versions || []);
    updateCompareButton();
  } catch (error) {
    reportAppIssue('loadVersionHistory', error, { promptId });
    const versionList = document.getElementById('version-list');
    if (versionList) {
      versionList.innerHTML = '<div class="loading">Error loading versions</div>';
    }
  }
}

function renderVersionHistory(versions: VersionSummary[]): void {
  const versionList = document.getElementById('version-list');
  if (!versionList) {
    return;
  }

  if (versions.length === 0) {
    versionList.innerHTML = '<div class="loading">' + t('version.noVersions') + '</div>';
    return;
  }

  versionList.innerHTML = '';
  versions.forEach((version, index) => {
    const versionItem = createVersionItem(version, index, versions.length);
    versionList.appendChild(versionItem);
  });
}

function createVersionItem(
  version: VersionSummary,
  index: number,
  totalVersions: number
): HTMLDivElement {
  const div = document.createElement('div');
  div.className = 'version-item';
  div.dataset.versionId = version.version_id;

  // Format timestamp with fallback for invalid dates
  let timestamp = 'Invalid Date';
  try {
    // Handle timestamps with microseconds by truncating to milliseconds
    const cleanTimestamp = version.timestamp.replace(/(\.\d{3})\d*/, '$1');
    const date = new Date(cleanTimestamp);
    if (isNaN(date.getTime())) {
      timestamp = 'Invalid Date';
    } else {
      timestamp = date.toLocaleString();
    }
  } catch (error) {
    timestamp = 'Invalid Date';
  }
  const isLatest = index === 0;

  div.innerHTML =
    `
        <div class="version-item-header">
            <span class="version-item-id">#${totalVersions - index} ${version.version_id.substring(0, 8)}...</span>
            <span class="version-item-timestamp">${timestamp}</span>
        </div>
        <div class="version-item-author">${t('version.author')}: ${version.author}</div>
        <div class="version-item-message">${version.message}</div>
        <div class="version-item-actions">
            ${!isLatest ? `<button class="btn btn-danger" onclick="showRevertConfirmation('${version.version_id}')" data-i18n="version.revert">` + t('version.revert') + `</button>` : ''}
            <button class="btn btn-secondary" onclick="selectVersionForComparison('${version.version_id}')" data-i18n="version.select">` +
    t('version.select') +
    `</button>
        </div>
    `;

  div.addEventListener('click', function (event: MouseEvent) {
    const target = event.target as Element | null;
    if (!target || !target.closest('button')) {
      toggleVersionSelection(version.version_id, div);
    }
  });

  return div;
}

function toggleVersionSelection(versionId: string, element: HTMLElement | null): void {
  if (!element) {
    return;
  }
  if (selectedVersions.has(versionId)) {
    selectedVersions.delete(versionId);
    element.classList.remove('selected');
  } else {
    selectedVersions.add(versionId);
    element.classList.add('selected');
  }
  updateCompareButton();
}

function selectVersionForComparison(versionId: string): void {
  const target = document.querySelector<HTMLElement>(`[data-version-id="${versionId}"]`);
  toggleVersionSelection(versionId, target);
}

function updateCompareButton() {
  const compareBtn = document.getElementById('compare-versions-btn');
  if (compareBtn) {
    toggleElement(compareBtn, selectedVersions.size === 2);
  }
}

function showRevertConfirmation(versionId: string): void {
  showElement(document.getElementById('revert-confirmation-modal'));
  const confirmRevertBtn = document.getElementById(
    'confirm-revert-btn'
  ) as HTMLButtonElement | null;
  if (confirmRevertBtn) {
    confirmRevertBtn.onclick = function () {
      performRevert(versionId);
    };
  }
}

async function performRevert(versionId: string): Promise<void> {
  try {
    if (currentVersionPromptId === null) {
      return;
    }
    const revertMessageInput = document.getElementById(
      'revert-commit-message'
    ) as HTMLInputElement | null;
    const commitMessage = revertMessageInput?.value || 'Revert to previous version';

    const formData = new FormData();
    formData.append('commit_message', commitMessage);

    const response = await fetch(
      `/api/prompts/${currentVersionPromptId}/versions/${versionId}/revert`,
      {
        method: 'POST',
        body: formData,
      }
    );

    if (!response.ok) {
      throw new Error('Failed to revert version');
    }

    hideRevertConfirmationModal();
    showNotification(t('version.revertSuccess'), 'success');
    // Clear version cache since a new version was created
    clearVersionCache(currentVersionPromptId);
    void loadVersionHistory(currentVersionPromptId);
    void loadPrompts(); // Refresh main list
    void loadAvailableTags(); // Refresh tag counts for autocomplete
    void loadTags(); // Refresh sidebar tag list
  } catch (error) {
    reportAppIssue('revertVersion', error, {
      promptId: currentVersionPromptId,
      versionId,
    });
    showNotification(t('version.revertError'), 'error');
  }
}

function showNotification(message: string, type: 'info' | 'success' | 'error' = 'info'): void {
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.textContent = message;
  document.body.appendChild(notification);
  setTimeout(() => notification.remove(), 3000);
}

// Diff Visualization Functions
let allVersions: VersionSummary[] = [];

async function showDiffModal(): Promise<void> {
  if (selectedVersions.size !== 2) {
    showNotification('Please select exactly 2 versions to compare', 'error');
    return;
  }

  showElement(document.getElementById('diff-modal'));
  let versionIds = Array.from(selectedVersions);

  // Sort versions by their version_number to ensure older is first (for old/new comparison)
  const versionsWithNumbers: VersionSortItem[] = versionIds.map((vId) => {
    const version = allVersions.find((v) => v.version_id === vId);
    return { id: vId, number: version ? version.version_number : 0 };
  });

  // Sort by version number (ascending - older first)
  versionsWithNumbers.sort((a, b) => a.number - b.number);
  versionIds = versionsWithNumbers.map((v) => v.id);

  // Populate version selectors
  populateDiffSelectors(versionIds);

  // Load and display diff - older version as v1 (old), newer as v2 (new)
  const [firstVersion, secondVersion] = versionIds;
  if (!firstVersion || !secondVersion) {
    return;
  }
  await loadAndDisplayDiff(firstVersion, secondVersion);
}

function populateDiffSelectors(selectedIds: string[]): void {
  const v1Selector = document.getElementById('diff-v1-selector') as HTMLSelectElement | null;
  const v2Selector = document.getElementById('diff-v2-selector') as HTMLSelectElement | null;

  if (!v1Selector || !v2Selector) {
    return;
  }

  v1Selector.innerHTML = '';
  v2Selector.innerHTML = '';

  allVersions.forEach((version, index) => {
    const option1 = document.createElement('option');
    option1.value = version.version_id;
    option1.textContent = `#${allVersions.length - index} - ${version.message}`;
    if (version.version_id === selectedIds[0]) option1.selected = true;
    v1Selector.appendChild(option1);

    const option2 = document.createElement('option');
    option2.value = version.version_id;
    option2.textContent = `#${allVersions.length - index} - ${version.message}`;
    if (version.version_id === selectedIds[1]) option2.selected = true;
    v2Selector.appendChild(option2);
  });

  // Add change listener
  v1Selector.addEventListener('change', () => updateDiff());
  v2Selector.addEventListener('change', () => updateDiff());
}

async function updateDiff(): Promise<void> {
  const v1Selector = document.getElementById('diff-v1-selector') as HTMLSelectElement | null;
  const v2Selector = document.getElementById('diff-v2-selector') as HTMLSelectElement | null;
  const v1 = v1Selector?.value || '';
  const v2 = v2Selector?.value || '';

  if (v1 === v2) {
    const diffView = document.getElementById('diff-view');
    if (diffView) {
      diffView.innerHTML = '<div class="loading">Select different versions to compare</div>';
    }
    return;
  }

  await loadAndDisplayDiff(v1, v2);
}

async function loadAndDisplayDiff(v1Id: string, v2Id: string): Promise<void> {
  try {
    if (currentVersionPromptId === null) {
      return;
    }
    const diffView = document.getElementById('diff-view');
    if (diffView) {
      diffView.innerHTML = '<div class="loading">' + t('messages.loading') + '</div>';
    }

    // Check cache first
    const cacheKey = `diff_${currentVersionPromptId}_${v1Id}_${v2Id}`;
    if (diffCache[cacheKey] && Date.now() - diffCache[cacheKey].timestamp < CACHE_DURATION) {
      displayDiff(diffCache[cacheKey].data);
      return;
    }

    const response = await fetch(
      `/api/prompts/${currentVersionPromptId}/versions/compare?v1=${v1Id}&v2=${v2Id}`
    );
    if (!response.ok) {
      throw new Error('Failed to load diff');
    }

    const diff = (await response.json()) as VersionDiffResponse;

    // Cache the result
    diffCache[cacheKey] = {
      data: diff,
      timestamp: Date.now(),
    };

    displayDiff(diff);
  } catch (error) {
    reportAppIssue('loadDiff', error, {
      promptId: currentVersionPromptId,
      fromVersion: v1Id,
      toVersion: v2Id,
    });
    const diffView = document.getElementById('diff-view');
    if (diffView) {
      diffView.innerHTML = '<div class="loading">Error loading diff</div>';
    }
  }
}

function displayDiff(diff: VersionDiffResponse): void {
  const diffView = document.getElementById('diff-view');
  if (!diffView) {
    return;
  }
  diffView.innerHTML = '';

  if (!diff.changes || Object.keys(diff.changes).length === 0) {
    diffView.innerHTML = '<div class="loading">No changes between these versions</div>';
    return;
  }

  const section = document.createElement('div');
  section.className = 'diff-section';

  Object.entries(diff.changes).forEach(([field, change]) => {
    const fieldDiv = document.createElement('div');
    fieldDiv.className = 'diff-field';

    const fieldName = document.createElement('div');
    fieldName.className = 'diff-field-name';
    fieldName.textContent = field.charAt(0).toUpperCase() + field.slice(1);
    fieldDiv.appendChild(fieldName);

    // Old value
    if (change.old !== null && change.old !== undefined) {
      const oldDiv = document.createElement('div');
      oldDiv.className = 'diff-old';
      oldDiv.innerHTML = `<strong>Old:</strong> ${escapeHtml(formatValue(change.old))}`;
      fieldDiv.appendChild(oldDiv);
    }

    // New value
    if (change.new !== null && change.new !== undefined) {
      const newDiv = document.createElement('div');
      newDiv.className = 'diff-new';
      newDiv.innerHTML = `<strong>New:</strong> ${escapeHtml(formatValue(change.new))}`;
      fieldDiv.appendChild(newDiv);
    }

    section.appendChild(fieldDiv);
  });

  diffView.appendChild(section);
}

function formatValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.join(', ');
  }
  if (typeof value === 'object' && value !== null) {
    return JSON.stringify(value);
  }
  return String(value);
}

function escapeHtml(text: string): string {
  const map: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
  };
  return text.replace(/[&<>"']/g, (m) => map[m] ?? m);
}

// Cache management functions
function clearVersionCache(promptId: number | string | null | undefined): void {
  if (promptId === null || promptId === undefined) {
    return;
  }
  const cacheKey = `versions_${promptId}`;
  delete versionCache[cacheKey];
}

// Keyboard Shortcuts (Phase 6)
function handleKeyboardShortcuts(event: KeyboardEvent): void {
  // Ctrl/Cmd + H: Open version history for last selected prompt
  if ((event.ctrlKey || event.metaKey) && event.key === 'h') {
    event.preventDefault();
    if (lastSelectedPromptId) {
      showVersionHistoryModal(lastSelectedPromptId);
    } else {
      showNotification('Please select a prompt first', 'info');
    }
  }

  // Ctrl/Cmd + N: New prompt
  if ((event.ctrlKey || event.metaKey) && event.key === 'n') {
    event.preventDefault();
    showNewPromptForm();
  }

  // Escape: Close modals
  if (event.key === 'Escape') {
    hideVersionHistoryModal();
    hideDiffModal();
    hideRevertConfirmationModal();
    hidePromptEditor();
  }
}

// Tooltips (Phase 6 & 8)
function addTooltips() {
  const tooltips = {
    '.history-btn': t('version.history') + ' - ' + t('version.searchPlaceholder'),
    '.copy-btn': t('actions.copy'),
    '.edit-btn': t('actions.edit'),
    '.delete-btn': t('actions.delete'),
    '.favorite-btn': 'Toggle favorite',
  };

  Object.entries(tooltips).forEach(([selector, title]) => {
    document.querySelectorAll(selector).forEach((element) => {
      const htmlElement = element as HTMLElement;
      htmlElement.title = title;
      htmlElement.setAttribute('data-tooltip', title);
    });
  });
}

// Lazy Loading for Version List (Phase 9)
let versionListObserver: IntersectionObserver | null = null;
const VERSIONS_PER_PAGE = 10;
let currentVersionPage = 0;

function initializeLazyLoading() {
  if ('IntersectionObserver' in window) {
    versionListObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            loadMoreVersions();
          }
        });
      },
      { threshold: 0.1 }
    );
  }
}

function loadMoreVersions() {
  const versionList = document.getElementById('version-list');
  if (!versionList) return;

  const items = versionList.querySelectorAll('.version-item');
  const totalItems = allVersions.length;
  const itemsToShow = (currentVersionPage + 1) * VERSIONS_PER_PAGE;

  if (items.length < totalItems && items.length < itemsToShow) {
    currentVersionPage++;
    const startIdx = currentVersionPage * VERSIONS_PER_PAGE;
    const endIdx = Math.min(startIdx + VERSIONS_PER_PAGE, totalItems);

    for (let i = startIdx; i < endIdx; i++) {
      const version = allVersions[i];
      if (!version) {
        continue;
      }
      const versionItem = createVersionItem(version, i, totalItems);
      versionList.appendChild(versionItem);
    }

    // Observe the last item for lazy loading
    const lastItem = versionList.lastElementChild;
    if (versionListObserver && lastItem) {
      versionListObserver.observe(lastItem);
    }
  }
}

// API Response Time Profiling (Phase 9)
const apiMetrics: Record<
  string,
  { calls: number; totalTime: number; avgTime: number; minTime: number; maxTime: number }
> = {};

function recordApiCall(endpoint: string, duration: number): void {
  if (!apiMetrics[endpoint]) {
    apiMetrics[endpoint] = {
      calls: 0,
      totalTime: 0,
      avgTime: 0,
      minTime: Infinity,
      maxTime: 0,
    };
  }

  const metric = apiMetrics[endpoint];
  metric.calls++;
  metric.totalTime += duration;
  metric.avgTime = metric.totalTime / metric.calls;
  metric.minTime = Math.min(metric.minTime, duration);
  metric.maxTime = Math.max(metric.maxTime, duration);
}

// Wrap fetch to track API performance
const originalFetch = window.fetch;
window.fetch = function (...args: Parameters<typeof fetch>) {
  const startTime = performance.now();
  return originalFetch.apply(this, args).then((response) => {
    const duration = performance.now() - startTime;
    const endpoint = typeof args[0] === 'string' ? args[0] : String(args[0]);
    recordApiCall(endpoint, duration);
    return response;
  });
};

// Tag Autocomplete Implementation
let availableTags: TagInfo[] = [];
let tagAutocompleteState = {
  isOpen: false,
  highlightedIndex: -1,
  filteredTags: [] as TagInfo[],
  currentPartialTag: '',
};

async function loadAvailableTags(): Promise<void> {
  try {
    const response = await fetch('/api/tags');
    const data = (await response.json()) as { tags: TagInfo[] };
    // Store tags with counts
    availableTags = data.tags || [];
  } catch (error) {
    reportAppIssue('loadTagsAutocomplete', error);
    availableTags = [];
  }
}

function setupTagAutocomplete() {
  const tagInput = document.getElementById('prompt-tags') as HTMLInputElement | null;
  const autocompleteDiv = document.getElementById('tag-autocomplete') as HTMLElement | null;

  if (!tagInput || !autocompleteDiv) {
    return;
  }

  // Load available tags when setting up
  void loadAvailableTags();

  // Input event - show suggestions as user types
  tagInput.addEventListener('input', (event) => {
    const target = event.target as HTMLInputElement | null;
    if (target) {
      handleTagInput(target);
    }
  });

  // Keydown event - handle keyboard navigation
  tagInput.addEventListener('keydown', (event) => {
    handleTagInputKeydown(event);
  });

  // Focus event - show suggestions if there's partial input
  tagInput.addEventListener('focus', (event) => {
    const target = event.target as HTMLInputElement | null;
    if (target) {
      handleTagInput(target);
    }
  });

  // Blur event - close dropdown with delay to allow clicks
  tagInput.addEventListener('blur', () => {
    setTimeout(() => {
      closeTagAutocomplete();
    }, 200);
  });

  // Click outside to close
  document.addEventListener('click', (event) => {
    if (
      !tagInput.contains(event.target as Node) &&
      !autocompleteDiv.contains(event.target as Node)
    ) {
      closeTagAutocomplete();
    }
  });
}

function handleTagInput(input: HTMLInputElement) {
  const value = input.value;
  const cursorPosition = input.selectionStart ?? input.value.length;

  // Find the current tag being typed (based on cursor position)
  const beforeCursor = value.substring(0, cursorPosition);
  const lastCommaIndex = beforeCursor.lastIndexOf(',');
  const partialTag = beforeCursor.substring(lastCommaIndex + 1).trim();

  tagAutocompleteState.currentPartialTag = partialTag;

  // Get already entered tags to filter them out
  const enteredTags = getEnteredTags(input);

  // Filter available tags
  const filtered = filterTags(partialTag, enteredTags);
  tagAutocompleteState.filteredTags = filtered;
  tagAutocompleteState.highlightedIndex = -1;

  // Show or hide autocomplete
  if (filtered.length > 0 || partialTag.length > 0) {
    showTagAutocomplete(filtered);
  } else {
    closeTagAutocomplete();
  }
}

function getEnteredTags(input: HTMLInputElement) {
  const value = input.value;
  const tags = value
    .split(',')
    .map((tag) => tag.trim().toLowerCase())
    .filter((tag) => tag.length > 0);
  return new Set(tags);
}

function filterTags(partialTag: string, enteredTags: Set<string>) {
  if (!availableTags || availableTags.length === 0) {
    return [];
  }

  // Case-insensitive filtering
  const searchTerm = partialTag.toLowerCase();

  return availableTags
    .filter((tag) => {
      const tagName = tag.name;
      const tagLower = tagName.toLowerCase();
      // Don't suggest tags already entered
      if (enteredTags.has(tagLower)) {
        return false;
      }
      // Match tags that contain the search term
      return tagLower.includes(searchTerm);
    })
    .sort((a, b) => b.count - a.count)
    .slice(0, 10); // Limit to 10 suggestions
}

function showTagAutocomplete(filteredTags: TagInfo[]) {
  const autocompleteDiv = document.getElementById('tag-autocomplete');
  if (!autocompleteDiv) {
    return;
  }

  autocompleteDiv.innerHTML = '';

  if (filteredTags.length === 0) {
    // Show "No matching tags" message
    const noResults = document.createElement('div');
    noResults.className = 'tag-autocomplete-no-results';
    noResults.textContent = 'No matching tags';
    autocompleteDiv.appendChild(noResults);
  } else {
    // Show tag suggestions
    filteredTags.forEach((tag, index) => {
      const tagName = tag.name;
      const tagCount = tag.count;

      const item = document.createElement('div');
      item.className = 'tag-autocomplete-item';
      item.dataset.index = String(index);
      item.dataset.tagName = tagName;

      const nameSpan = document.createElement('span');
      nameSpan.className = 'tag-autocomplete-item-name';
      nameSpan.textContent = tagName;
      item.appendChild(nameSpan);

      if (tagCount !== null) {
        const countSpan = document.createElement('span');
        countSpan.className = 'tag-autocomplete-item-count';
        countSpan.textContent = `(${tagCount})`;
        item.appendChild(countSpan);
      }

      // Click handler
      item.addEventListener('click', function () {
        selectTag(tagName);
      });

      // Hover handler
      item.addEventListener('mouseenter', function () {
        highlightTagItem(index);
      });

      autocompleteDiv.appendChild(item);
    });
  }

  showElement(autocompleteDiv);
  tagAutocompleteState.isOpen = true;
}

function closeTagAutocomplete() {
  const autocompleteDiv = document.getElementById('tag-autocomplete');
  if (autocompleteDiv) {
    hideElement(autocompleteDiv);
  }
  tagAutocompleteState.isOpen = false;
  tagAutocompleteState.highlightedIndex = -1;
}

function handleTagInputKeydown(event: KeyboardEvent) {
  if (!tagAutocompleteState.isOpen) {
    return;
  }

  const filteredTags = tagAutocompleteState.filteredTags;

  switch (event.key) {
    case 'ArrowDown':
      event.preventDefault();
      if (filteredTags.length > 0) {
        tagAutocompleteState.highlightedIndex =
          (tagAutocompleteState.highlightedIndex + 1) % filteredTags.length;
        highlightTagItem(tagAutocompleteState.highlightedIndex);
      }
      break;

    case 'ArrowUp':
      event.preventDefault();
      if (filteredTags.length > 0) {
        tagAutocompleteState.highlightedIndex =
          tagAutocompleteState.highlightedIndex <= 0
            ? filteredTags.length - 1
            : tagAutocompleteState.highlightedIndex - 1;
        highlightTagItem(tagAutocompleteState.highlightedIndex);
      }
      break;

    case 'Enter':
      if (
        tagAutocompleteState.highlightedIndex >= 0 &&
        tagAutocompleteState.highlightedIndex < filteredTags.length
      ) {
        event.preventDefault();
        const selectedTag = filteredTags[tagAutocompleteState.highlightedIndex];
        if (selectedTag) {
          selectTag(selectedTag.name);
        }
      }
      break;

    case 'Escape':
      event.preventDefault();
      event.stopPropagation();
      closeTagAutocomplete();
      break;

    case 'Tab':
      if (
        tagAutocompleteState.highlightedIndex >= 0 &&
        tagAutocompleteState.highlightedIndex < filteredTags.length
      ) {
        event.preventDefault();
        const selectedTag = filteredTags[tagAutocompleteState.highlightedIndex];
        if (selectedTag) {
          selectTag(selectedTag.name);
        }
      }
      break;
  }
}

function highlightTagItem(index: number) {
  const autocompleteDiv = document.getElementById('tag-autocomplete');
  if (!autocompleteDiv) {
    return;
  }

  // Remove previous highlight
  autocompleteDiv.querySelectorAll('.tag-autocomplete-item').forEach((item) => {
    item.classList.remove('highlighted');
  });

  // Add new highlight
  const items = autocompleteDiv.querySelectorAll('.tag-autocomplete-item');
  if (items[index]) {
    items[index].classList.add('highlighted');
    // Scroll into view if needed
    items[index].scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }

  tagAutocompleteState.highlightedIndex = index;
}

function selectTag(tagName: string): void {
  const tagInput = document.getElementById('prompt-tags') as HTMLInputElement | null;
  if (!tagInput) {
    return;
  }

  const value = tagInput.value;
  const cursorPosition = tagInput.selectionStart ?? tagInput.value.length;

  // Find the position of the last comma before cursor
  const beforeCursor = value.substring(0, cursorPosition);
  const lastCommaIndex = beforeCursor.lastIndexOf(',');

  // Build the new value
  let newValue = '';
  let newCursorPosition = 0;

  if (lastCommaIndex === -1) {
    // No comma yet - replace entire input
    newValue = tagName + ', ';
    newCursorPosition = newValue.length;
  } else {
    // Replace text after last comma
    const beforeTag = value.substring(0, lastCommaIndex + 1);
    const afterCursor = value.substring(cursorPosition);
    // Remove any existing partial tag and add the selected tag
    newValue = beforeTag + ' ' + tagName + ', ' + afterCursor;
    newCursorPosition = (beforeTag + ' ' + tagName + ', ').length;
  }

  // Update input
  tagInput.value = newValue;
  tagInput.setSelectionRange(newCursorPosition, newCursorPosition);
  tagInput.focus();

  // Close autocomplete
  closeTagAutocomplete();

  // Trigger input event to potentially show new suggestions
  setTimeout(() => {
    handleTagInput(tagInput);
  }, 50);
}

// ============================================
// Bulk Actions & Selection Functions
// ============================================

function initializeBulkActions() {
  const selectAllCheckbox = document.getElementById('select-all-checkbox');
  const bulkDeleteBtn = document.getElementById('bulk-delete-btn');
  const clearSelectionBtn = document.getElementById('clear-selection-btn');
  const confirmBulkDeleteBtn = document.getElementById('confirm-bulk-delete-btn');
  const cancelBulkDeleteBtn = document.getElementById('cancel-bulk-delete-btn');

  if (selectAllCheckbox) {
    selectAllCheckbox.addEventListener('change', handleSelectAll);
  }

  if (bulkDeleteBtn) {
    bulkDeleteBtn.addEventListener('click', showBulkDeleteConfirmation);
  }

  if (clearSelectionBtn) {
    clearSelectionBtn.addEventListener('click', clearSelection);
  }

  if (confirmBulkDeleteBtn) {
    confirmBulkDeleteBtn.addEventListener('click', () => {
      void performBulkDelete();
    });
  }

  if (cancelBulkDeleteBtn) {
    cancelBulkDeleteBtn.addEventListener('click', hideBulkDeleteModal);
  }
}

function handleCheckboxChange(promptId: number, isChecked: boolean) {
  if (isChecked) {
    selectedPromptIds.add(promptId);
  } else {
    selectedPromptIds.delete(promptId);
  }
  updateBulkActionsUI();
}

function handleSelectAll(event: Event) {
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

function updateBulkActionsUI() {
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

function clearSelection() {
  selectedPromptIds.clear();
  const checkboxes = document.querySelectorAll<HTMLInputElement>('.prompt-checkbox');
  checkboxes.forEach((checkbox) => (checkbox.checked = false));
  updateBulkActionsUI();
}

function showBulkDeleteConfirmation() {
  if (selectedPromptIds.size === 0) return;

  const modal = document.getElementById('bulk-delete-modal');
  const countElement = document.getElementById('bulk-delete-count');
  if (countElement) {
    countElement.textContent = String(selectedPromptIds.size);
  }
  if (modal) {
    modal.classList.remove(HIDDEN_CLASS);
  }
}

function hideBulkDeleteModal() {
  const modal = document.getElementById('bulk-delete-modal');
  if (modal) {
    modal.classList.add(HIDDEN_CLASS);
  }
}

async function performBulkDelete(): Promise<void> {
  if (selectedPromptIds.size === 0) return;

  const promptIdsArray = Array.from(selectedPromptIds);

  try {
    const response = await fetch('/api/prompts/bulk', {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        prompt_ids: promptIdsArray,
      }),
    });

    const result = (await response.json()) as BulkDeleteResponse;

    if (response.ok && result.success) {
      hideBulkDeleteModal();
      clearSelection();

      // Show success message
      const message = t('bulkDelete.successMessage', {
        deleted: result.deleted_count,
        failed: result.failed_count,
      });
      alert(message);

      // Refresh UI
      await loadPrompts();
      await loadAvailableTags();
      await loadTags();

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
    alert(t('bulkDelete.errorMessage'));
    reportAppIssue('bulk-delete-failed', error, {
      prompt_ids: promptIdsArray,
    });
  }
}

initI18n(() => {
  try {
    updateStaticTranslations();
    void initializeApp();
  } catch (error) {
    reportAppIssue('initialize', error);
  }
});

// Initialize lazy loading on app start
initializeLazyLoading();

// Logout function
async function logout() {
  try {
    // Get refresh token from localStorage (if it exists from old implementation)
    const refreshToken =
      localStorage.getItem('refresh_token') || sessionStorage.getItem('refresh_token');

    // Call logout endpoint with cookies
    await fetch('/api/auth/logout', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
      body: refreshToken ? JSON.stringify({ refresh_token: refreshToken }) : '{}',
    });
  } catch (error) {
    console.error('Logout error:', error);
    reportAppIssue('logout-error', error, {}, 'warning');
  } finally {
    // Always clear storage and redirect
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    sessionStorage.clear();

    window.location.href = '/auth/login';
  }
}

const appWindow = window as unknown as Window & {
  selectVersionForComparison: (versionId: string) => void;
  showRevertConfirmation: (versionId: string) => void;
  hideVersionHistoryModal: () => void;
  hideDiffModal: () => void;
  hideRevertConfirmationModal: () => void;
  hideBulkDeleteModal: () => void;
};

appWindow.selectVersionForComparison = selectVersionForComparison;
appWindow.showRevertConfirmation = showRevertConfirmation;
appWindow.hideVersionHistoryModal = hideVersionHistoryModal;
appWindow.hideDiffModal = hideDiffModal;
appWindow.hideRevertConfirmationModal = hideRevertConfirmationModal;
appWindow.hideBulkDeleteModal = hideBulkDeleteModal;
