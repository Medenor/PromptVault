/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * PromptVault main app logic (TypeScript).
 */

import '../../css/tailwind-globals.css';
import '@/form-validation';
import { initI18n, t, updateStaticTranslations } from '@/utils/i18n';
import { setupScrollIndicators } from '@/utils/dom';
import { showNotification } from '@/utils/notifications';
import { createModal } from '@components';
import { closeMobileDrawer, initKeyboardSafeScroll, initMobileNav } from '@/mobile-nav';
import { initSearchOverlay } from '@/search-overlay';
import { initOfflineIndicator, registerServiceWorker } from '@/sw-register';
import { attachPullToRefresh } from '@/gestures';
import { logout, hideAuthOnlyElements, fetchRoleAndRevealAdmin } from '@/utils/auth-nav';
import { APP_COMPONENT, reportAppIssue } from './shared';
import { addTooltips, initializeFilterListKeyboardNavigation } from './keyboard-nav';
import {
  isAnyFilterActive,
  lastSelectedPromptId,
  loadCategories,
  loadMorePrompts,
  loadPrompts,
  loadTags,
  performSearch,
  setPaginationControlsVisible,
  setPaginationPageSize,
  setPromptElementHandlers,
} from './prompt-list';
import {
  clearAllFilters,
  handleCategoryFilter,
  handleFavoritesFilter,
  handleTagFilter,
  setupSearchEventListeners,
} from './search';
import {
  clearPromptFieldError,
  showPromptFieldError,
  getPromptLiveValidationState,
} from './prompt-form';
import {
  copyPrompt,
  copyPromptWithVersion,
  deletePrompt,
  editPrompt,
  handlePromptSubmit,
  hidePromptEditor,
  setPromptEditorRefreshCallbacks,
  showNewPromptForm,
  toggleFavorite,
} from './prompt-crud';
import { handleSuggestTags, loadAvailableTags, setupTagAutocomplete } from './tag-autocomplete';
import {
  hideDiffModal,
  hideRevertConfirmationModal,
  hideVersionHistoryModal,
  initializeLazyLoading,
  selectVersionForComparison,
  setVersionRefreshCallbacks,
  showDiffModal,
  showRevertConfirmation,
  showVersionHistoryModal,
} from './versions';
import { hideBulkDeleteModal, initializeBulkActions } from './bulk-actions';
import type { PromptId } from './types';
import type { PageSize } from '@/utils/pagination';

function removePromptsSkeleton(): void {
  document.getElementById('prompts-skeleton')?.remove();
}

async function checkAdminAccess(): Promise<void> {
  // Anonymous mode (AUTH_ENABLED=false): the shell and real prompts are
  // already rendered server-side; just hide auth-only UI elements.
  if (window.__AUTH_ENABLED__ === false) {
    hideAuthOnlyElements();
    return;
  }

  try {
    await fetchRoleAndRevealAdmin();
    // Authentication successful. The skeleton is left in place here;
    // the subsequent loadPrompts() call replaces #prompts-list's
    // innerHTML with real data, which removes it.
  } catch (error) {
    reportAppIssue('checkAdminAccess', error);

    // Offline or request timeout (network failure, not a real auth
    // rejection): the app shell is already visible, so just stop showing
    // the skeleton and let the cached-shell/offline indicator behavior
    // stand, so previously-viewed content remains accessible per FR-009.
    // apiFetch already handles a genuine 401 (server reachable, session
    // invalid) with its own redirect. Any other error (including a genuine
    // APIRequestError or an unexpected bug) is treated as a real failure
    // and redirects to login for security.
    const isNetworkFailure =
      !navigator.onLine || (error instanceof Error && error.message === 'Request timeout');
    if (isNetworkFailure) {
      removePromptsSkeleton();
      return;
    }

    // On a genuine auth error while online, redirect to login for security.
    // The skeleton (not real data) is what's on screen, so no private
    // content leaks during this redirect.
    window.location.href = '/auth/login';
  }
}

function hideModal(): void {
  const modal = document.getElementById('prompt-modal');
  if (modal) {
    modal.classList.add('hidden');
  }
}

// Keyboard Shortcuts (Phase 6)
function handleKeyboardShortcuts(event: KeyboardEvent): void {
  // Ctrl/Cmd + H: Open version history for last selected prompt
  if ((event.ctrlKey || event.metaKey) && event.key === 'h') {
    event.preventDefault();
    if (lastSelectedPromptId) {
      showVersionHistoryModal(lastSelectedPromptId);
    } else {
      showNotification(t('messages.selectPromptFirst'), 'info');
    }
  }

  // Ctrl/Cmd + N: New prompt
  if ((event.ctrlKey || event.metaKey) && event.key === 'n') {
    event.preventDefault();
    showNewPromptForm();
  }

  // Escape: Close modals.
  // For views that pushed a history entry (editor, version-history), use
  // history.back() so the entry is cleaned up; only do so when the view is
  // actually visible to avoid spurious back-navigations.
  if (event.key === 'Escape') {
    const versionHistoryModal = document.getElementById('version-history-modal');
    const promptEditor = document.getElementById('prompt-editor');
    if (versionHistoryModal && !versionHistoryModal.classList.contains('hidden')) {
      history.back();
    } else if (promptEditor && !promptEditor.classList.contains('hidden')) {
      history.back();
    }
    hideDiffModal();
    hideRevertConfirmationModal();
  }
}

let keyboardHelpModal: {
  element: HTMLDivElement;
  open: () => void;
  close: () => void;
} | null = null;

function escapeHtmlLocal(text: string): string {
  const map: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
  };
  return text.replace(/[&<>"']/g, (m) => map[m] ?? m);
}

function showKeyboardShortcutsHelpModal(): void {
  const buildLandmarksHelpList = (): string => {
    const landmarks = Array.from(
      document.querySelectorAll<HTMLElement>(
        'header[role="banner"], nav[role="navigation"], main[role="main"], aside[role="complementary"], footer[role="contentinfo"]'
      )
    );

    if (landmarks.length === 0) {
      return `<li>${escapeHtmlLocal(t('accessibility.keyboardHelp.noLandmarks'))}</li>`;
    }

    return landmarks
      .map((landmark, index) => {
        const role = landmark.getAttribute('role') ?? landmark.tagName.toLowerCase();
        const ariaLabel = landmark.getAttribute('aria-label')?.trim();
        const ariaLabelledBy = landmark.getAttribute('aria-labelledby');
        const labelledByText = ariaLabelledBy
          ? document.getElementById(ariaLabelledBy)?.textContent?.trim()
          : '';
        const label = ariaLabel || labelledByText;
        const description = label ? `${role} (${label})` : role;
        return `<li><strong>${index + 1}.</strong> ${escapeHtmlLocal(description)}</li>`;
      })
      .join('');
  };

  if (!keyboardHelpModal) {
    const content = document.createElement('div');
    content.className = 'space-y-3 text-sm text-gray-700';
    content.innerHTML = `
      <p class="text-gray-600">${escapeHtmlLocal(t('accessibility.keyboardHelp.shortcutsHeading'))}</p>
      <ul class="list-disc list-inside space-y-1">
        <li><strong>Ctrl/Cmd + H</strong>: ${escapeHtmlLocal(t('accessibility.keyboardHelp.shortcutHistory'))}</li>
        <li><strong>Ctrl/Cmd + N</strong>: ${escapeHtmlLocal(t('accessibility.keyboardHelp.shortcutNewPrompt'))}</li>
        <li><strong>Escape</strong>: ${escapeHtmlLocal(t('accessibility.keyboardHelp.shortcutEscape'))}</li>
        <li><strong>?</strong>: ${escapeHtmlLocal(t('accessibility.keyboardHelp.shortcutQuestion'))}</li>
        <li><strong>Arrow keys</strong>: ${escapeHtmlLocal(t('accessibility.keyboardHelp.shortcutArrows'))}</li>
        <li><strong>Enter / Space</strong>: ${escapeHtmlLocal(t('accessibility.keyboardHelp.shortcutActivate'))}</li>
        <li><strong>Home / End</strong>: ${escapeHtmlLocal(t('accessibility.keyboardHelp.shortcutHomeEnd'))}</li>
        <li><strong>${escapeHtmlLocal(t('accessibility.keyboardHelp.shortcutCharacterKey'))}</strong>: ${escapeHtmlLocal(t('accessibility.keyboardHelp.shortcutCharacter'))}</li>
      </ul>
      <div class="pt-2 border-t border-gray-200">
        <p class="text-gray-600">${escapeHtmlLocal(t('accessibility.keyboardHelp.landmarksHeading'))}</p>
        <ul id="keyboard-help-landmarks-list" class="list-disc list-inside space-y-1">
          ${buildLandmarksHelpList()}
        </ul>
      </div>
    `;

    keyboardHelpModal = createModal({
      id: 'keyboard-shortcuts-help-modal',
      title: t('accessibility.keyboardHelp.title'),
      content,
      ariaLabel: t('accessibility.keyboardHelp.ariaLabel'),
      size: 'md',
      actions: [
        {
          label: t('actions.close'),
          variant: 'primary',
          onClick: () => {
            keyboardHelpModal?.close();
          },
        },
      ],
      closeOnEscape: true,
      closeOnBackdrop: true,
      showClose: true,
    });

    document.body.appendChild(keyboardHelpModal.element);
  }

  const landmarksList = keyboardHelpModal.element.querySelector<HTMLElement>(
    '#keyboard-help-landmarks-list'
  );
  if (landmarksList) {
    landmarksList.innerHTML = buildLandmarksHelpList();
  }

  keyboardHelpModal.open();
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
window.fetch = async function (...args: Parameters<typeof fetch>) {
  const startTime = performance.now();
  const response = await originalFetch.apply(this, args);
  const duration = performance.now() - startTime;
  const endpoint = typeof args[0] === 'string' ? args[0] : String(args[0]);
  recordApiCall(endpoint, duration);
  return response;
};

function setupEventListeners(): void {
  // Unified mobile navigation drawer (hamburger triggers, close button,
  // backdrop, outside-tap/Escape close, focus trap) — see mobile-nav.ts
  initMobileNav();

  // Full-screen mobile search overlay (FR-016) — see search-overlay.ts
  initSearchOverlay();

  // Keep the prompt editor's fields visible above the on-screen keyboard (FR-005)
  initKeyboardSafeScroll(['#prompt-title', '#prompt-content']);

  // Offline resilience: Service Worker caching + persistent offline indicator.
  // Offline mode is read/copy-only (FR-009, FR-010) — editing is gated behind
  // connectivity rather than queued, so there's no write-sync step here.
  registerServiceWorker();
  initOfflineIndicator();

  // Secondary pages (Import/Export, Manage Categories/Tags, Backup) require
  // connectivity and aren't reachable offline (FR-012) — their nav buttons
  // call this instead of navigating directly when offline.
  window.__requireOnlineNav = (path: string): void => {
    if (navigator.onLine) {
      window.location.href = path;
      return;
    }
    showNotification(t('offline.editUnavailable'), 'error');
  };

  // Pull-to-refresh on the prompt list (FR-008), with an accessible refresh
  // button as the always-visible equivalent control.
  const promptsList = document.getElementById('prompts-list');
  const pullRefreshIndicator = document.getElementById('pull-refresh-indicator');
  const refreshPromptsBtn = document.getElementById('refresh-prompts-btn');

  const showRefreshLoading = (): void => {
    pullRefreshIndicator?.classList.remove('hidden');
    pullRefreshIndicator?.classList.add('flex');
  };
  const hideRefreshLoading = (): void => {
    pullRefreshIndicator?.classList.add('hidden');
    pullRefreshIndicator?.classList.remove('flex');
  };
  const refreshPrompts = async (): Promise<void> => {
    if (isAnyFilterActive()) {
      await performSearch();
    } else {
      await loadPrompts();
    }
  };

  if (promptsList) {
    attachPullToRefresh(promptsList, {
      onRefresh: refreshPrompts,
      showLoading: showRefreshLoading,
      hideLoading: hideRefreshLoading,
    });
  }

  refreshPromptsBtn?.addEventListener('click', () => {
    showRefreshLoading();
    void refreshPrompts().finally(hideRefreshLoading);
  });

  // New prompt button
  const newPromptBtn = document.getElementById('new-prompt-btn');
  newPromptBtn?.addEventListener('click', showNewPromptForm);

  // New prompt button (mobile)
  const newPromptBtnMobile = document.getElementById('new-prompt-btn-mobile');
  newPromptBtnMobile?.addEventListener('click', () => {
    showNewPromptForm();
    closeMobileDrawer();
  });

  // New prompt floating action button (mobile, FR-006)
  const newPromptFab = document.getElementById('new-prompt-fab');
  newPromptFab?.addEventListener('click', showNewPromptForm);

  // Logout button
  const logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      void logout(APP_COMPONENT);
    });
  }

  // Logout button (mobile)
  const logoutBtnMobile = document.getElementById('logout-btn-mobile');
  if (logoutBtnMobile) {
    logoutBtnMobile.addEventListener('click', () => {
      void logout(APP_COMPONENT);
    });
  }

  // Form handling
  const promptForm = document.getElementById('prompt-form');
  promptForm?.addEventListener('submit', (event) => {
    void handlePromptSubmit(event as SubmitEvent);
  });
  const cancelBtn = document.getElementById('cancel-btn-edit-modal');
  cancelBtn?.addEventListener('click', () => history.back());
  const suggestTagsBtn = document.getElementById('suggest-tags-btn');
  suggestTagsBtn?.addEventListener('click', () => {
    void handleSuggestTags();
  });

  // Live validation (T-ACC025) for the prompt editor required fields.
  const titleInput = document.getElementById('prompt-title') as HTMLInputElement | null;
  if (titleInput) {
    const validate = () => {
      if (!titleInput.value.trim()) {
        showPromptFieldError(
          'prompt-title',
          'prompt-title-error',
          'validation.titleRequired',
          false,
          true
        );
      } else {
        clearPromptFieldError('prompt-title', 'prompt-title-error', true);
      }
    };
    titleInput.addEventListener('blur', validate);
    titleInput.addEventListener('input', () => {
      if (getPromptLiveValidationState('prompt-title')) {
        validate();
      }
    });
  }

  const contentInput = document.getElementById('prompt-content') as HTMLTextAreaElement | null;
  if (contentInput) {
    const validate = () => {
      if (!contentInput.value.trim()) {
        showPromptFieldError(
          'prompt-content',
          'prompt-content-error',
          'validation.contentRequired',
          false,
          true
        );
      } else {
        clearPromptFieldError('prompt-content', 'prompt-content-error', true);
      }
    };
    contentInput.addEventListener('blur', validate);
    contentInput.addEventListener('input', () => {
      if (getPromptLiveValidationState('prompt-content')) {
        validate();
      }
    });
  }

  // Category and tag filtering (desktop and mobile)
  const categoriesList = document.getElementById('categories-list');
  categoriesList?.addEventListener('click', handleCategoryFilter);
  const categoriesListMobile = document.getElementById('categories-list-mobile');
  categoriesListMobile?.addEventListener('click', (event) => {
    handleCategoryFilter(event);
    closeMobileDrawer();
  });

  const tagsList = document.getElementById('tags-list');
  tagsList?.addEventListener('click', handleTagFilter);
  const tagsListMobile = document.getElementById('tags-list-mobile');
  tagsListMobile?.addEventListener('click', (event) => {
    handleTagFilter(event);
    closeMobileDrawer();
  });
  initializeFilterListKeyboardNavigation();

  const favoritesFilter = document.getElementById('favorites-filter');
  favoritesFilter?.addEventListener('change', handleFavoritesFilter);
  const favoritesFilterMobile = document.getElementById('favorites-filter-mobile');
  favoritesFilterMobile?.addEventListener('change', handleFavoritesFilter);

  // Modal close
  const closeBtn = document.querySelector('.close');
  closeBtn?.addEventListener('click', hideModal);
  window.addEventListener('click', function (event) {
    const modal = document.getElementById('prompt-modal');
    if (event.target === modal) {
      hideModal();
    }
  });

  // Version history modal close buttons
  const closeVersionHistoryBtns = document.querySelectorAll('#close-version-history-btn');
  closeVersionHistoryBtns.forEach((btn) => {
    btn.addEventListener('click', hideVersionHistoryModal);
  });

  // Back button closes modals/editor instead of leaving the app.
  // When popstate fires we've already moved back in history, so event.state is
  // the *previous* entry — not our pushed one. Check what's visible instead.
  window.addEventListener('popstate', () => {
    const versionHistoryModal = document.getElementById('version-history-modal');
    const promptEditor = document.getElementById('prompt-editor');
    if (versionHistoryModal && !versionHistoryModal.classList.contains('hidden')) {
      hideVersionHistoryModal();
    } else if (promptEditor && !promptEditor.classList.contains('hidden')) {
      hidePromptEditor();
    }
  });

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
  document.addEventListener('promptvault:open-keyboard-help', (event) => {
    const customEvent = event as CustomEvent<{ markHandled?: () => void }>;
    customEvent.detail?.markHandled?.();
    showKeyboardShortcutsHelpModal();
  });

  // Button keyboard activation (Enter and Space keys)
  // Enables keyboard accessibility for all buttons across the application
  document.addEventListener('keydown', (e) => {
    if (document.activeElement instanceof HTMLButtonElement) {
      const button = document.activeElement;
      // Enter and Space keys should activate buttons (standard keyboard behavior)
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        button.click();
      }
    }
  });

  // Add tooltips
  addTooltips();

  // Search functionality
  setupSearchEventListeners(clearAllFilters);

  // Tag autocomplete
  setupTagAutocomplete();

  // Empty state buttons
  const emptyStateNewPromptBtn = document.getElementById('empty-state-new-prompt-btn');
  emptyStateNewPromptBtn?.addEventListener('click', showNewPromptForm);

  const emptyStateClearFiltersBtn = document.getElementById('empty-state-clear-filters-btn');
  emptyStateClearFiltersBtn?.addEventListener('click', clearAllFilters);

  // Load More button (pagination)
  const loadMoreBtn = document.getElementById('load-more-btn');
  loadMoreBtn?.addEventListener('click', () => {
    void loadMorePrompts();
  });

  // Page size selector (pagination)
  const pageSizeSelect = document.getElementById('page-size-select') as HTMLSelectElement | null;
  pageSizeSelect?.addEventListener('change', (event) => {
    const target = event.target as HTMLSelectElement | null;
    const value = Number(target?.value) as PageSize;
    setPaginationPageSize(value);
    if (isAnyFilterActive()) {
      void performSearch();
    } else {
      void loadPrompts();
    }
  });

  // Setup scroll indicators for scrollable containers
  setupScrollIndicators(document.getElementById('categories-list'));
  setupScrollIndicators(document.getElementById('tags-list'));
  setupScrollIndicators(document.getElementById('categories-list-mobile'));
  setupScrollIndicators(document.getElementById('tags-list-mobile'));
  // NOTE: tag autocomplete is absolutely positioned; wrapping it for scroll fades
  // would clip the dropdown. Keep it unwrapped so suggestions remain visible.
}

async function initializeApp(): Promise<void> {
  // Event listeners (safe to setup before auth)
  setupEventListeners();
  initializeBulkActions({
    loadPrompts,
    loadAvailableTags,
    loadTags,
  });

  // CRITICAL: Check authentication BEFORE loading any data
  // This prevents content flash before redirect
  await checkAdminAccess();

  // Only load data if authentication succeeded
  // (if auth failed, checkAdminAccess redirects to login)
  void loadPrompts();
  void loadCategories();
  void loadTags();
}

// Wire cross-module callbacks before anything runs.
setPromptElementHandlers({
  onCopy: (id: PromptId) => {
    void copyPrompt(id);
  },
  onEdit: (id: PromptId) => {
    void editPrompt(id);
  },
  onDelete: (id: PromptId) => {
    void deletePrompt(id);
  },
  onToggleFavorite: (id: PromptId) => {
    void toggleFavorite(id);
  },
  onShowHistory: (id: number) => {
    showVersionHistoryModal(id);
  },
  onCopyWithVersion: (id: PromptId) => {
    void copyPromptWithVersion(id);
  },
});

setPromptEditorRefreshCallbacks({
  isAnyFilterActive,
  performSearch,
  loadPrompts,
  loadTags,
  setPaginationControlsVisible,
});

setVersionRefreshCallbacks({
  loadPrompts,
  loadAvailableTags,
  loadTags,
});

// Mobile navigation drawer (hamburger, close, backdrop, focus trap) lives in
// mobile-nav.ts — see initMobileNav() wired in setupEventListeners() above.

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
