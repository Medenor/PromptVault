/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { apiGet, apiPostForm } from '@/utils/api';
import { t } from '@/utils/i18n';
import { showNotification } from '@/utils/notifications';
import { attachSwipeReveal } from '@/gestures';
import {
  escapeHtml,
  guardOnlineOnly,
  hideElement,
  reportAppIssue,
  showElement,
  toggleElement,
} from './shared';
import { initializeVersionListKeyboardNavigation } from './keyboard-nav';
import type {
  DiffCacheEntry,
  DiffOperation,
  VersionCacheEntry,
  VersionDiffResponse,
  VersionHistoryResponse,
  VersionSortItem,
  VersionSummary,
} from './types';

// Focus management for modals
let versionHistoryModalTrigger: HTMLElement | null = null;
let diffModalTrigger: HTMLElement | null = null;
let revertConfirmationModalTrigger: HTMLElement | null = null;

let currentVersionPromptId: number | null = null;
const selectedVersions: Set<string> = new Set();
let versionCache: Record<string, VersionCacheEntry> = {}; // Cache for version history
let diffCache: Record<string, DiffCacheEntry> = {}; // Cache for diff results
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes in milliseconds
let allVersions: VersionSummary[] = [];

export interface VersionRefreshCallbacks {
  loadPrompts: () => Promise<void>;
  loadAvailableTags: () => Promise<void>;
  loadTags: () => Promise<void>;
}

function focusFirstModalElement(modal: HTMLElement): void {
  const focusableElements = Array.from(
    modal.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )
  ).filter((el) => {
    const style = window.getComputedStyle(el);
    return style.display !== 'none' && style.visibility !== 'hidden';
  });
  if (focusableElements.length > 0) {
    const first = focusableElements[0];
    if (first) first.focus();
  }
}

export function showVersionHistoryModal(promptId: number): void {
  currentVersionPromptId = promptId;
  selectedVersions.clear();
  // Store trigger element for focus return
  versionHistoryModalTrigger = (event as unknown as { target: HTMLElement }).target || null;
  history.pushState({ modal: 'version-history' }, '');
  showElement(document.getElementById('version-history-modal'));
  // Move focus to first focusable element in modal
  const modal = document.getElementById('version-history-modal');
  if (modal) {
    focusFirstModalElement(modal);
  }
  // Update search placeholder with current language
  const searchInput = document.getElementById('version-search') as HTMLInputElement | null;
  if (searchInput) {
    searchInput.placeholder = t('version.searchPlaceholder');
  }
  void loadVersionHistory(promptId);
}

export function hideVersionHistoryModal(): void {
  hideElement(document.getElementById('version-history-modal'));
  currentVersionPromptId = null;
  selectedVersions.clear();
  // Return focus to trigger element
  if (versionHistoryModalTrigger) {
    versionHistoryModalTrigger.focus();
  }
}

export function hideDiffModal(): void {
  hideElement(document.getElementById('diff-modal'));
  // Return focus to trigger element
  if (diffModalTrigger) {
    diffModalTrigger.focus();
  }
}

export function hideRevertConfirmationModal(): void {
  hideElement(document.getElementById('revert-confirmation-modal'));
  // Return focus to trigger element
  if (revertConfirmationModalTrigger) {
    revertConfirmationModalTrigger.focus();
  }
}

async function loadVersionHistory(promptId: number): Promise<void> {
  try {
    const versionList = document.getElementById('version-list');
    if (versionList) {
      // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
      versionList.innerHTML =
        '<div class="text-center text-gray-500 py-8">' + t('messages.loading') + '</div>';
    }

    // Check cache first
    const cacheKey = `versions_${promptId}`;
    if (versionCache[cacheKey] && Date.now() - versionCache[cacheKey].timestamp < CACHE_DURATION) {
      const cachedData = versionCache[cacheKey].data;
      renderVersionHistory(cachedData.versions || []);
      updateCompareButton();
      return;
    }

    const data = await apiGet<VersionHistoryResponse>(`/api/prompts/${promptId}/versions`);

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
      // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
      versionList.innerHTML =
        '<div class="text-center text-red-600 py-8">Error loading versions</div>';
    }
  }
}

function renderVersionHistory(versions: VersionSummary[]): void {
  const versionList = document.getElementById('version-list');
  if (!versionList) {
    return;
  }

  if (versions.length === 0) {
    // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
    versionList.innerHTML =
      '<div class="text-center text-gray-500 py-8">' + t('version.noVersions') + '</div>';
    hideVersionCarouselNav();
    return;
  }

  // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
  versionList.innerHTML = '';
  versions.forEach((version, index) => {
    const versionItem = createVersionItem(version, index, versions.length);
    versionList.appendChild(versionItem);
  });

  initializeVersionListKeyboardNavigation(versionList, toggleVersionSelection);
  initVersionCarousel(versionList, versions.length);
}

// Mobile swipeable version-history carousel (FR-018): pages through one
// version at a time via swipe or the visible prev/next buttons.
let versionCarouselIndex = 0;
let detachVersionCarouselSwipe: (() => void) | null = null;
let detachVersionCarouselButtons: (() => void) | null = null;

function hideVersionCarouselNav(): void {
  document.getElementById('version-carousel-nav')?.classList.add('hidden');
  document.getElementById('version-list')?.classList.remove('carousel-mode');
}

function updateVersionCarouselPosition(total: number): void {
  const position = document.getElementById('version-carousel-position');
  const prevBtn = document.getElementById('version-carousel-prev') as HTMLButtonElement | null;
  const nextBtn = document.getElementById('version-carousel-next') as HTMLButtonElement | null;
  if (position) {
    position.textContent = `${versionCarouselIndex + 1} / ${total}`;
  }
  if (prevBtn) prevBtn.disabled = versionCarouselIndex === 0;
  if (nextBtn) nextBtn.disabled = versionCarouselIndex === total - 1;
}

function showVersionCarouselItem(versionList: HTMLElement, index: number): void {
  const items = versionList.querySelectorAll<HTMLElement>('.version-item');
  items.forEach((item, i) => {
    item.classList.toggle('carousel-active', i === index);
  });
}

function initVersionCarousel(versionList: HTMLElement, total: number): void {
  const nav = document.getElementById('version-carousel-nav');
  if (!nav || total === 0) return;

  // Only enabled on mobile viewports; desktop keeps the vertical list (md:hidden on nav).
  if (window.matchMedia('(min-width: 768px)').matches) {
    hideVersionCarouselNav();
    return;
  }

  nav.classList.remove('hidden');
  nav.classList.add('flex');
  versionList.classList.add('carousel-mode');
  versionCarouselIndex = 0;
  showVersionCarouselItem(versionList, versionCarouselIndex);
  updateVersionCarouselPosition(total);

  const prevBtn = document.getElementById('version-carousel-prev');
  const nextBtn = document.getElementById('version-carousel-next');

  const goToPrev = (): void => {
    if (versionCarouselIndex === 0) return;
    versionCarouselIndex -= 1;
    showVersionCarouselItem(versionList, versionCarouselIndex);
    updateVersionCarouselPosition(total);
  };
  const goToNext = (): void => {
    if (versionCarouselIndex === total - 1) return;
    versionCarouselIndex += 1;
    showVersionCarouselItem(versionList, versionCarouselIndex);
    updateVersionCarouselPosition(total);
  };

  detachVersionCarouselButtons?.();
  prevBtn?.addEventListener('click', goToPrev);
  nextBtn?.addEventListener('click', goToNext);
  detachVersionCarouselButtons = () => {
    prevBtn?.removeEventListener('click', goToPrev);
    nextBtn?.removeEventListener('click', goToNext);
  };

  detachVersionCarouselSwipe?.();
  detachVersionCarouselSwipe = attachSwipeReveal(versionList, {
    onSwipeLeft: goToNext,
    onSwipeRight: goToPrev,
  });
}

function createVersionItem(
  version: VersionSummary,
  index: number,
  totalVersions: number
): HTMLDivElement {
  const div = document.createElement('div');
  div.className =
    'version-item bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors';
  div.dataset.versionId = version.version_id;
  div.dataset.navLabel = version.message;
  div.setAttribute('role', 'button');
  div.setAttribute('aria-pressed', 'false');
  div.tabIndex = -1;

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
  } catch {
    timestamp = 'Invalid Date';
  }
  const isLatest = index === 0;

  const semVerBadge = version.semantic_version
    ? `<span class="px-2 py-0.5 text-xs font-semibold rounded-full bg-blue-100 text-blue-700">${version.semantic_version}</span>`
    : `<span class="px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 text-gray-500" data-i18n="version.unversioned">${t('version.unversioned')}</span>`;

  // eslint-disable-next-line no-restricted-properties -- every interpolation is wrapped in escapeHtml()
  div.innerHTML =
    `
        <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2">
              <span class="text-sm font-semibold text-gray-900 dark:text-gray-100">#${totalVersions - index} ${version.version_id.substring(0, 8)}...</span>
              ${semVerBadge}
            </div>
            <span class="text-xs text-gray-500 dark:text-gray-400">${timestamp}</span>
        </div>
        <div class="text-xs text-gray-600 dark:text-gray-400 mb-1">${t('version.author')}: ${escapeHtml(version.author)}</div>
        <div class="text-sm text-gray-700 dark:text-gray-300 mb-3">${escapeHtml(version.message)}</div>
        <div class="flex gap-2">
            ${!isLatest ? `<button class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-red-500 text-white hover:bg-red-600 transition-all hover:scale-105 active:scale-95" onclick="showRevertConfirmation('${version.version_id}')" data-i18n="version.revert">` + t('version.revert') + `</button>` : ''}
            <button class="px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-100 text-blue-700 hover:bg-blue-200 transition-all hover:scale-105 active:scale-95" onclick="selectVersionForComparison('${version.version_id}')" data-i18n="version.select">` +
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
    element.classList.remove(
      'selected',
      'ring-2',
      'ring-blue-500',
      'bg-blue-50',
      'dark:bg-blue-950'
    );
    element.setAttribute('aria-pressed', 'false');
  } else {
    selectedVersions.add(versionId);
    element.classList.add('selected', 'ring-2', 'ring-blue-500', 'bg-blue-50', 'dark:bg-blue-950');
    element.setAttribute('aria-pressed', 'true');
  }
  updateCompareButton();
}

export function selectVersionForComparison(versionId: string): void {
  const target = document.querySelector<HTMLElement>(`[data-version-id="${versionId}"]`);
  toggleVersionSelection(versionId, target);
}

function updateCompareButton(): void {
  const compareBtn = document.getElementById('compare-versions-btn');
  if (compareBtn) {
    toggleElement(compareBtn, selectedVersions.size === 2);
  }
}

export function showRevertConfirmation(versionId: string): void {
  // Store trigger element for focus return
  revertConfirmationModalTrigger = (event as unknown as { target: HTMLElement }).target || null;
  showElement(document.getElementById('revert-confirmation-modal'));
  // Move focus to first focusable element in modal
  const modal = document.getElementById('revert-confirmation-modal');
  if (modal) {
    focusFirstModalElement(modal);
  }
  const confirmRevertBtn = document.getElementById(
    'confirm-revert-btn'
  ) as HTMLButtonElement | null;
  if (confirmRevertBtn) {
    confirmRevertBtn.onclick = function () {
      void performRevert(versionId);
    };
  }
}

let versionRefreshCallbacks: VersionRefreshCallbacks | null = null;

export function setVersionRefreshCallbacks(callbacks: VersionRefreshCallbacks): void {
  versionRefreshCallbacks = callbacks;
}

async function performRevert(versionId: string): Promise<void> {
  try {
    if (currentVersionPromptId === null) {
      return;
    }

    if (!guardOnlineOnly()) return;
    const revertMessageInput = document.getElementById(
      'revert-commit-message'
    ) as HTMLInputElement | null;
    const commitMessage = revertMessageInput?.value || 'Revert to previous version';

    const formData = new FormData();
    formData.append('commit_message', commitMessage);

    await apiPostForm<void>(
      `/api/prompts/${currentVersionPromptId}/versions/${versionId}/revert`,
      formData
    );

    hideRevertConfirmationModal();
    showNotification(t('version.revertSuccess'), 'success');
    // Clear version cache since a new version was created
    clearVersionCache(currentVersionPromptId);
    void loadVersionHistory(currentVersionPromptId);
    void versionRefreshCallbacks?.loadPrompts(); // Refresh main list
    void versionRefreshCallbacks?.loadAvailableTags(); // Refresh tag counts for autocomplete
    void versionRefreshCallbacks?.loadTags(); // Refresh sidebar tag list
  } catch (error) {
    reportAppIssue('revertVersion', error, {
      promptId: currentVersionPromptId,
      versionId,
    });
    showNotification(t('version.revertError'), 'error');
  }
}

export async function showDiffModal(): Promise<void> {
  if (selectedVersions.size !== 2) {
    showNotification(t('messages.selectTwoVersions'), 'error');
    return;
  }

  // Store trigger element for focus return
  diffModalTrigger = (event as unknown as { target: HTMLElement }).target || null;
  showElement(document.getElementById('diff-modal'));
  // Move focus to first focusable element in modal
  const modal = document.getElementById('diff-modal');
  if (modal) {
    focusFirstModalElement(modal);
  }
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

  // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
  v1Selector.innerHTML = '';
  // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
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
      // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
      diffView.innerHTML =
        '<div class="text-center text-gray-500 py-8">Select different versions to compare</div>';
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
      // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
      diffView.innerHTML =
        '<div class="text-center text-gray-500 py-8">' + t('messages.loading') + '</div>';
    }

    // Check cache first
    const cacheKey = `diff_${currentVersionPromptId}_${v1Id}_${v2Id}`;
    if (diffCache[cacheKey] && Date.now() - diffCache[cacheKey].timestamp < CACHE_DURATION) {
      displayDiff(diffCache[cacheKey].data);
      return;
    }

    const diff = await apiGet<VersionDiffResponse>(
      `/api/prompts/${currentVersionPromptId}/versions/compare?v1=${v1Id}&v2=${v2Id}`
    );

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
      // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
      diffView.innerHTML = '<div class="text-center text-red-600 py-8">Error loading diff</div>';
    }
  }
}

function renderCharacterDiff(operations: DiffOperation[]): HTMLElement {
  const container = document.createElement('div');
  container.className = 'whitespace-pre-wrap break-words';

  if (!operations || operations.length === 0) {
    container.textContent = '';
    return container;
  }

  operations.forEach((op) => {
    if (!op || !op.text) {
      return;
    }

    const span = document.createElement('span');
    span.textContent = op.text;

    switch (op.op) {
      case 'equal':
        span.className = 'text-gray-700';
        break;
      case 'delete':
        span.className = 'bg-red-100 line-through text-red-800';
        break;
      case 'insert':
        span.className = 'bg-green-100 font-semibold text-green-800';
        break;
      default:
        span.className = 'text-gray-700';
    }

    container.appendChild(span);
  });

  return container;
}

function displayDiff(diff: VersionDiffResponse): void {
  const diffView = document.getElementById('diff-view');
  if (!diffView) {
    return;
  }
  // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
  diffView.innerHTML = '';

  if (!diff.changes || Object.keys(diff.changes).length === 0) {
    // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
    diffView.innerHTML =
      '<div class="text-center text-gray-500 py-8">No changes between these versions</div>';
    return;
  }

  const section = document.createElement('div');
  section.className = 'space-y-4';

  const fieldDisplayNames: Record<string, string> = {
    semantic_version: 'Semantic Version',
  };

  Object.entries(diff.changes).forEach(([field, change]) => {
    const fieldDiv = document.createElement('div');
    fieldDiv.className =
      'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4';

    const fieldName = document.createElement('div');
    fieldName.className = 'text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3';
    fieldName.textContent =
      fieldDisplayNames[field] || field.charAt(0).toUpperCase() + field.slice(1);
    fieldDiv.appendChild(fieldName);

    // If character-level diff is available, render it
    if (change.diff && change.diff.length > 0) {
      const diffContainer = renderCharacterDiff(change.diff);
      diffContainer.className =
        'p-3 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg ' +
        diffContainer.className;
      fieldDiv.appendChild(diffContainer);
    } else {
      // Fallback to old/new display for backward compatibility
      // Old value
      if (change.old !== null && change.old !== undefined) {
        const oldDiv = document.createElement('div');
        oldDiv.className = 'mb-2 p-3 bg-red-50 border border-red-200 rounded-lg';
        // eslint-disable-next-line no-restricted-properties -- every interpolation is wrapped in escapeHtml()
        oldDiv.innerHTML = `<strong class="text-red-700">Old:</strong> <span class="text-gray-700">${escapeHtml(formatValue(change.old))}</span>`;
        fieldDiv.appendChild(oldDiv);
      }

      // New value
      if (change.new !== null && change.new !== undefined) {
        const newDiv = document.createElement('div');
        newDiv.className = 'p-3 bg-emerald-50 border border-emerald-200 rounded-lg';
        // eslint-disable-next-line no-restricted-properties -- every interpolation is wrapped in escapeHtml()
        newDiv.innerHTML = `<strong class="text-emerald-700">New:</strong> <span class="text-gray-700">${escapeHtml(formatValue(change.new))}</span>`;
        fieldDiv.appendChild(newDiv);
      }
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

// Cache management functions
export function clearVersionCache(promptId: number | string | null | undefined): void {
  if (promptId === null || promptId === undefined) {
    return;
  }
  const cacheKey = `versions_${promptId}`;
  delete versionCache[cacheKey];
}

// Lazy Loading for Version List (Phase 9)
let versionListObserver: IntersectionObserver | null = null;
const VERSIONS_PER_PAGE = 10;
let currentVersionPage = 0;

export function initializeLazyLoading(): void {
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

function loadMoreVersions(): void {
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
