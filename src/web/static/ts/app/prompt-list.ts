/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import type { ItemResponse, PromptListResponse } from '@/types';
import { t } from '@/utils/i18n';
import { apiGet } from '@/utils/api';
import { showNotification } from '@/utils/notifications';
import {
  createInitialPaginationState,
  mergePrompts,
  canLoadMore,
  type PaginationState,
  type PageSize,
} from '@/utils/pagination';
import { applyPromptColorStyles } from './colors';
import { hideElement, reportAppIssue, showElement, toggleElement } from './shared';
import { initializePromptsListKeyboardNavigation } from './keyboard-nav';
import { buildSearchUrl, currentFilters, isAnyFilterActive, searchState } from './prompt-filters';
import { createPromptElement, setLastSelectedPromptIdSetter } from './prompt-card';

export let promptCache: Record<string, ItemResponse> = {};
export let lastSelectedPromptId: number | null = null; // Track the last selected prompt for keyboard shortcuts

export function setLastSelectedPromptId(id: number | null): void {
  lastSelectedPromptId = id;
}

setLastSelectedPromptIdSetter((id: number) => {
  lastSelectedPromptId = id;
});

// Global pagination state for the "Load More" prompt list flow
export let paginationState: PaginationState = createInitialPaginationState({
  searchTerm: '',
  category: 'all',
  tag: 'all',
  favorites: false,
  sharedWithMe: false,
  caseSensitive: false,
  itemType: 'all',
});

export function updateLoadMoreControl(): void {
  const loadMoreBtn = document.getElementById('load-more-btn') as HTMLButtonElement | null;
  const loadMoreContainer = document.getElementById('load-more-container');
  if (!loadMoreBtn || !loadMoreContainer) {
    return;
  }
  toggleElement(loadMoreContainer, paginationState.hasNext);
  loadMoreBtn.disabled = paginationState.isLoadingMore;
  loadMoreBtn.textContent = paginationState.isLoadingMore ? 'Loading...' : 'Load More';
}

export async function loadPrompts(): Promise<void> {
  // Fresh load always resets to page 1 and replaces the current list.
  paginationState = createInitialPaginationState(currentFilters(), paginationState.pageSize);

  try {
    const data = await apiGet<PromptListResponse>(
      `/api/prompts?page=1&limit=${paginationState.pageSize}`
    );

    // Hide search results info when loading all prompts initially
    const searchResultsInfo = document.getElementById('search-results-info');
    if (searchResultsInfo) {
      hideElement(searchResultsInfo);
    }

    paginationState.hasNext = data.has_next;
    promptCache = mergePrompts({}, data.prompts || {}, 'replace');
    renderPrompts(promptCache);
    updateLoadMoreControl();
  } catch (error) {
    reportAppIssue('loadPrompts', error);
  }
}

export async function loadMorePrompts(): Promise<void> {
  if (!canLoadMore(paginationState)) {
    return;
  }

  paginationState.isLoadingMore = true;
  updateLoadMoreControl();

  try {
    const nextPage = paginationState.currentPage + 1;
    const isFiltered = isAnyFilterActive();
    const endpoint = isFiltered
      ? buildSearchUrl(nextPage, paginationState.pageSize)
      : `/api/prompts?page=${nextPage}&limit=${paginationState.pageSize}`;
    const data = await apiGet<PromptListResponse>(endpoint);

    paginationState.currentPage = nextPage;
    paginationState.hasNext = data.has_next;
    promptCache = mergePrompts(promptCache, data.prompts || {}, 'append');
    renderPrompts(promptCache);
  } catch (error) {
    reportAppIssue('loadMorePrompts', error);
  } finally {
    paginationState.isLoadingMore = false;
    updateLoadMoreControl();
  }
}

export function setPaginationPageSize(size: PageSize): void {
  paginationState.pageSize = size;
}

/**
 * Close the prompt editor if it is open and restore the list view.
 * A new search/filter replaces the list, so an editor opened for a prompt
 * from the previous results must not stay visible.
 */
export function closePromptEditorForListChange(): void {
  const promptEditor = document.getElementById('prompt-editor');
  if (!promptEditor || promptEditor.classList.contains('hidden')) {
    return;
  }
  hideElement(promptEditor);
  showElement(document.getElementById('prompts-list'));
  showElement(document.getElementById('pull-refresh-toolbar'));
  setPaginationControlsVisible(true);
}

export async function performSearch(): Promise<void> {
  if (searchState.isLoading) {
    return; // Don't start new search if one is already running
  }

  closePromptEditorForListChange();
  searchState.isLoading = true;

  // Any filter change (this is only called on filter change or initial
  // search) resets pagination to page 1 and replaces the current list.
  paginationState = createInitialPaginationState(currentFilters(), paginationState.pageSize);

  try {
    // Show loading state
    const promptsList = document.getElementById('prompts-list');
    if (promptsList) {
      promptsList.style.opacity = '0.6';
      promptsList.style.pointerEvents = 'none';
    }

    // Make API call with automatic token refresh
    const data = await apiGet<PromptListResponse>(buildSearchUrl(1, paginationState.pageSize));

    paginationState.hasNext = data.has_next;
    promptCache = mergePrompts({}, data.prompts || {}, 'replace');

    // Update prompts list
    renderPrompts(promptCache);
    updateLoadMoreControl();

    // Update result count and handle empty results
    updateSearchResultsInfo(promptCache, data.total_count);
  } catch (error) {
    reportAppIssue('searchPrompts', error, {
      filters: {
        searchTerm: searchState.searchTerm,
        category: searchState.category,
        tag: searchState.tag,
        favorites: searchState.favorites,
        caseSensitive: searchState.caseSensitive,
        itemType: searchState.itemType,
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

function updateSearchResultsInfo(prompts: Record<string, ItemResponse>, totalCount: number): void {
  const resultCount = Object.keys(prompts || {}).length;
  const searchResultsInfo = document.getElementById('search-results-info');
  const promptsListEl = document.getElementById('prompts-list');

  // Handle empty results
  if (resultCount === 0) {
    // Show "No results found" message
    if (searchResultsInfo) {
      searchResultsInfo.className =
        'mb-4 px-4 py-3 bg-amber-50 border border-amber-200 text-amber-800 rounded-lg text-sm';
      searchResultsInfo.textContent = t('search.noResultsInfo');
      showElement(searchResultsInfo);
    }

    // Show empty state in prompts list
    if (promptsListEl) {
      // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
      promptsListEl.innerHTML = `<div class="col-span-full text-center text-gray-500 py-12">${t('search.noResultsMessage')}</div>`;
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
    searchResultsInfo.className = 'mb-4 px-4 py-3 bg-blue-50 text-blue-800 rounded-lg text-sm';

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
    if (searchState.itemType !== 'all') {
      activeFilters.push(
        t('search.filter.type', { type: t(`filters.itemType.${searchState.itemType}`) })
      );
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
      searchState.caseSensitive ||
      searchState.itemType !== 'all'
    ) {
      clearAllFiltersBtn.textContent = t('search.clearFiltersWithCount', { count: resultCount });
      showElement(clearAllFiltersBtn);
    } else {
      hideElement(clearAllFiltersBtn);
    }
  }
}

export function renderPrompts(prompts: Record<string, ItemResponse>): void {
  const container = document.getElementById('prompts-list') as HTMLElement | null;
  const searchResultsInfo = document.getElementById('search-results-info');
  const promptsEmptyState = document.getElementById('prompts-empty-state');
  const searchEmptyState = document.getElementById('search-empty-state');

  if (!container) {
    return;
  }
  // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
  container.innerHTML = '';

  // Handle case when there are no prompts at all
  if (Object.keys(prompts).length === 0) {
    // Determine if this is a search/filter result or truly no prompts
    const hasActiveFilters = isAnyFilterActive();

    if (hasActiveFilters) {
      // Show search empty state
      showElement(searchEmptyState);
      hideElement(promptsEmptyState);
      hideElement(container);
    } else {
      // Show prompts empty state
      showElement(promptsEmptyState);
      hideElement(searchEmptyState);
      hideElement(container);
    }

    if (searchResultsInfo) {
      hideElement(searchResultsInfo);
    }
    return;
  }

  // Hide empty states and show prompts container
  hideElement(promptsEmptyState);
  hideElement(searchEmptyState);
  showElement(container);

  for (const [id, prompt] of Object.entries(prompts)) {
    const promptElement = createPromptElement(id, prompt);
    container.appendChild(promptElement);
  }

  applyPromptColorStyles();
  initializePromptsListKeyboardNavigation(container);
}

export function setPaginationControlsVisible(visible: boolean): void {
  const pageSizeControl = document.getElementById('page-size-control');
  const loadMoreContainer = document.getElementById('load-more-container');
  if (visible) {
    showElement(pageSizeControl);
    toggleElement(loadMoreContainer, paginationState.hasNext);
  } else {
    hideElement(pageSizeControl);
    hideElement(loadMoreContainer);
  }
}
