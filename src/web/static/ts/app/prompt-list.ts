/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import type { PromptResponse, PromptListResponse } from '@/types';
import { t, tUnsafe } from '@/utils/i18n';
import { apiGet } from '@/utils/api';
import { showNotification } from '@/utils/notifications';
import { attachSwipeReveal } from '@/gestures';
import {
  createInitialPaginationState,
  mergePrompts,
  canLoadMore,
  type PaginationState,
  type PageSize,
} from '@/utils/pagination';
import {
  applyPromptColorStyles,
  buildPillStyleFilled,
  buildPillStyleOutline,
  getCategoryColorMap,
  getTagColorMap,
  normalizeTagItems,
  resolveCssColor,
  setCategoryColorMap,
  setTagColorMap,
  clearCategoryColorMap,
} from './colors';
import { escapeHtml, hideElement, reportAppIssue, showElement, toggleElement } from './shared';
import { initializePromptsListKeyboardNavigation, syncRovingTabindexForList } from './keyboard-nav';
import { selectedPromptIds, handleCheckboxChange } from './bulk-actions';
import type { CategoryItem, PromptId, TagInfo, TagItem } from './types';

export let promptCache: Record<string, PromptResponse> = {};
export let lastSelectedPromptId: number | null = null; // Track the last selected prompt for keyboard shortcuts

export function setLastSelectedPromptId(id: number | null): void {
  lastSelectedPromptId = id;
}

// Global search state
export const searchState: {
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

// Global pagination state for the "Load More" prompt list flow
export let paginationState: PaginationState = createInitialPaginationState({
  searchTerm: '',
  category: 'all',
  tag: 'all',
  favorites: false,
  caseSensitive: false,
});

export function currentFilters() {
  return {
    searchTerm: searchState.searchTerm,
    category: searchState.category,
    tag: searchState.tag,
    favorites: searchState.favorites,
    caseSensitive: searchState.caseSensitive,
  };
}

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
      ? buildSearchUrl(nextPage)
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

export function buildSearchUrl(page: number): string {
  const params = new URLSearchParams();
  if (searchState.searchTerm) params.append('search', searchState.searchTerm);
  if (searchState.category && searchState.category !== 'all')
    params.append('category', searchState.category);
  if (searchState.tag && searchState.tag !== 'all') params.append('tag', searchState.tag);
  if (searchState.favorites) params.append('favorites', 'true');
  if (searchState.caseSensitive) params.append('case_sensitive', 'true');
  params.append('page', String(page));
  params.append('limit', String(paginationState.pageSize));
  return `/api/prompts/search?${params.toString()}`;
}

export async function performSearch(): Promise<void> {
  if (searchState.isLoading) {
    return; // Don't start new search if one is already running
  }

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
    const data = await apiGet<PromptListResponse>(buildSearchUrl(1));

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

function updateSearchResultsInfo(
  prompts: Record<string, PromptResponse>,
  totalCount: number
): void {
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

export async function loadCategories(): Promise<void> {
  try {
    try {
      const data = await apiGet<{ items: CategoryItem[] }>('/api/categories/manage');
      const categories = (data.items || []).map((item) => item.name);
      setCategoryColorMap(data.items || []);
      renderCategories(categories);
      applyPromptColorStyles();
      return;
    } catch (error) {
      reportAppIssue('loadCategoriesMetadata', error, {}, 'warning');
    }

    const data = await apiGet<{ categories: string[] }>('/api/categories');
    clearCategoryColorMap();
    renderCategories(data.categories || []);
    applyPromptColorStyles();
  } catch (error) {
    reportAppIssue('loadCategories', error);
  }
}

export async function loadTags(): Promise<void> {
  try {
    try {
      const data = await apiGet<{ items: TagItem[] }>('/api/tags/manage');
      const normalized = normalizeTagItems(data.items || []);
      setTagColorMap(normalized);
      renderTags(normalized);
      applyPromptColorStyles();
      return;
    } catch (error) {
      reportAppIssue('loadTagsMetadata', error, {}, 'warning');
    }

    const data = await apiGet<{ tags: TagInfo[] }>('/api/tags');
    setTagColorMap(data.tags || []);
    renderTags(data.tags || []);
    applyPromptColorStyles();
  } catch (error) {
    reportAppIssue('loadTags', error);
  }
}

export function renderPrompts(prompts: Record<string, PromptResponse>): void {
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

export function isAnyFilterActive(): boolean {
  const searchInput = document.getElementById('search-input') as HTMLInputElement | null;
  const favoritesFilter = document.getElementById('favorites-filter') as HTMLInputElement | null;
  const selectedCategory = document
    .querySelector('#categories-list li.active')
    ?.getAttribute('data-category');
  const selectedTag = document.querySelector('#tags-list li.active')?.getAttribute('data-tag');

  return !!(
    (searchInput && searchInput.value.trim()) ||
    (favoritesFilter && favoritesFilter.checked) ||
    (selectedCategory && selectedCategory !== 'all') ||
    (selectedTag && selectedTag !== 'all')
  );
}

export interface PromptElementHandlers {
  onCopy: (id: PromptId) => void;
  onEdit: (id: PromptId) => void;
  onDelete: (id: PromptId) => void;
  onToggleFavorite: (id: PromptId) => void;
  onShowHistory: (id: number) => void;
  onCopyWithVersion: (id: PromptId) => void;
}

let promptElementHandlers: PromptElementHandlers | null = null;

export function setPromptElementHandlers(handlers: PromptElementHandlers): void {
  promptElementHandlers = handlers;
}

function createPromptElement(id: string, prompt: PromptResponse): HTMLDivElement {
  const handlers = promptElementHandlers;
  if (!handlers) {
    throw new Error('Prompt element handlers not initialized');
  }

  const div = document.createElement('div');
  div.className =
    'prompt-item bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 transition-all hover:scale-[1.02] cursor-pointer';
  div.dataset.id = id;
  div.dataset.navLabel = prompt.title || '';

  // Add selected class if prompt is in selection
  if (selectedPromptIds.has(parseInt(id))) {
    div.classList.add('selected');
  }

  // Create checkbox for bulk selection
  const titleId = `prompt-title-${id}`;
  const checkbox = document.createElement('input');
  checkbox.type = 'checkbox';
  checkbox.className =
    'prompt-checkbox w-5 h-5 md:w-4 md:h-4 rounded text-blue-500 focus:ring-blue-500';
  checkbox.dataset.promptId = id;
  checkbox.setAttribute('aria-labelledby', titleId);
  checkbox.checked = selectedPromptIds.has(parseInt(id));
  checkbox.addEventListener('change', (event) => {
    const target = event.target as HTMLInputElement | null;
    handleCheckboxChange(parseInt(id, 10), target?.checked ?? false);
    event.stopPropagation(); // Prevent triggering the div click event
  });

  const tagColorMap = getTagColorMap();
  const categoryColorMap = getCategoryColorMap();

  // Build tags HTML
  const tagColorLookup = prompt.tag_colors ?? {};
  const tagsHTML =
    prompt.tags && prompt.tags.length > 0
      ? prompt.tags
          .map((tag) => {
            const color = tagColorLookup[tag] ?? tagColorMap[tag];
            const style = buildPillStyleOutline(color);
            return `<span class="px-2 py-1 text-xs font-medium rounded-full border border-gray-300 dark:border-gray-600 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200" data-tag-pill="true" data-tag-name="${escapeHtml(tag)}"${style}>
                ${escapeHtml(tag)}
              </span>`;
          })
          .join('')
      : '';

  const categoryColor = prompt.category_color ?? categoryColorMap[prompt.category];
  const categoryStyle = buildPillStyleFilled(categoryColor);

  const semVerBadge = prompt.semantic_version
    ? `<span class="version-badge px-2 py-0.5 text-xs font-semibold rounded-full bg-blue-100 text-blue-700 ml-2">v${prompt.semantic_version}</span>`
    : '';

  // eslint-disable-next-line no-restricted-properties -- every interpolation is wrapped in escapeHtml()
  div.innerHTML = `
	        <div class="flex items-start justify-between mb-3">
	            <h4 id="${titleId}" class="text-prompt-title font-semibold text-gray-900 dark:text-gray-100 flex-1 flex items-center flex-wrap gap-1">${escapeHtml(prompt.title)}${semVerBadge}</h4>
	            <div class="flex items-center gap-1 ml-2" id="prompt-actions-${id}">
	                <button class="favorite-btn flex items-center justify-center min-w-[44px] min-h-[44px] md:min-w-0 md:min-h-0 text-xl hover:scale-110 transition-transform focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-700 rounded" data-id="${id}">
	                    ${prompt.favorite ? '★' : '☆'}
	                </button>
	            </div>
	        </div>
        <div class="flex flex-wrap gap-2 mb-3">
            <span class="px-2 py-1 text-xs font-semibold rounded-md bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200" data-category-pill="true" data-category-name="${escapeHtml(prompt.category)}"${categoryStyle}>
              ${escapeHtml(prompt.category) || t('categories.noCategory')}
            </span>
            ${tagsHTML}
        </div>
        <p class="prompt-body-text text-prompt-body text-gray-600 dark:text-gray-300 mb-1 line-clamp-3">${escapeHtml(prompt.prompt)}</p>
        <button type="button" class="read-more-btn hidden min-h-[44px] md:min-h-0 -ml-2 px-2 mb-3 text-xs font-medium text-blue-700 hover:text-blue-800 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-700 rounded" data-i18n="prompt.readMore">Read More</button>
        <div class="flex flex-wrap gap-2">
            <button class="history-btn min-h-[44px] md:min-h-0 px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 transition-all hover:scale-105 active:scale-95" data-id="${id}" data-i18n="version.history">History</button>
            <button class="copy-btn min-h-[44px] md:min-h-0 px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 transition-all hover:scale-105 active:scale-95" data-id="${id}" data-i18n="actions.copy">Copy</button>
            <button class="copy-with-version-btn min-h-[44px] md:min-h-0 px-3 py-1.5 text-xs font-medium rounded-lg bg-purple-100 text-purple-700 hover:bg-purple-200 transition-all hover:scale-105 active:scale-95" data-id="${id}" data-i18n="version.copyWithMetadata">Copy+Version</button>
            <button class="edit-btn min-h-[44px] md:min-h-0 px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-100 text-blue-700 hover:bg-blue-200 transition-all hover:scale-105 active:scale-95" data-id="${id}" data-i18n="actions.edit">Edit</button>
            <button class="delete-btn min-h-[44px] md:min-h-0 px-3 py-1.5 text-xs font-medium rounded-lg bg-red-100 text-red-700 hover:bg-red-200 transition-all hover:scale-105 active:scale-95" data-id="${id}" data-i18n="actions.delete">Delete</button>
        </div>
    `;

  // Insert checkbox at the beginning of prompt-actions
  const promptActions = div.querySelector(`#prompt-actions-${id}`) as HTMLElement | null;
  if (promptActions) {
    promptActions.insertBefore(checkbox, promptActions.firstChild);
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
    handlers.onCopy(id);
  });
  if (copyBtn) {
    copyBtn.title = t('actions.copy');
  }

  const editBtn = div.querySelector('.edit-btn') as HTMLButtonElement | null;
  editBtn?.addEventListener('click', () => {
    lastSelectedPromptId = parseInt(id, 10);
    handlers.onEdit(id);
  });
  if (editBtn) {
    editBtn.title = t('actions.edit');
  }

  const deleteBtn = div.querySelector('.delete-btn') as HTMLButtonElement | null;
  deleteBtn?.addEventListener('click', () => {
    lastSelectedPromptId = parseInt(id, 10);
    handlers.onDelete(id);
  });
  if (deleteBtn) {
    deleteBtn.title = t('actions.delete');
  }

  const favoriteBtn = div.querySelector('.favorite-btn') as HTMLButtonElement | null;
  favoriteBtn?.addEventListener('click', () => {
    lastSelectedPromptId = parseInt(id, 10);
    handlers.onToggleFavorite(id);
  });
  if (favoriteBtn) {
    setFavoriteButtonA11y(favoriteBtn, Boolean(prompt.favorite));
  }

  const historyBtn = div.querySelector('.history-btn') as HTMLButtonElement | null;
  historyBtn?.addEventListener('click', () => {
    lastSelectedPromptId = parseInt(id, 10);
    handlers.onShowHistory(parseInt(id, 10));
  });
  if (historyBtn) {
    historyBtn.title = t('version.history');
  }

  const copyWithVersionBtn = div.querySelector(
    '.copy-with-version-btn'
  ) as HTMLButtonElement | null;
  copyWithVersionBtn?.addEventListener('click', () => {
    lastSelectedPromptId = parseInt(id, 10);
    handlers.onCopyWithVersion(id);
  });
  if (copyWithVersionBtn) {
    copyWithVersionBtn.title = t('version.copyWithMetadata');
  }

  // Track prompt selection on click and open editor
  div.addEventListener('click', (event) => {
    const target = event.target as Element | null;
    if (target && (target.closest('button') || target.closest('input') || target.closest('a'))) {
      return;
    }
    lastSelectedPromptId = parseInt(id, 10);
    handlers.onEdit(id);
  });

  // "Read More" — reveal the full prompt body when the clamped text overflows.
  const bodyText = div.querySelector('.prompt-body-text') as HTMLElement | null;
  const readMoreBtn = div.querySelector('.read-more-btn') as HTMLButtonElement | null;
  if (bodyText && readMoreBtn) {
    requestAnimationFrame(() => {
      if (bodyText.scrollHeight > bodyText.clientHeight + 1) {
        readMoreBtn.classList.remove('hidden');
      }
    });
    readMoreBtn.addEventListener('click', (event) => {
      event.stopPropagation();
      const isNowClamped = bodyText.classList.toggle('line-clamp-3');
      readMoreBtn.textContent = isNowClamped ? t('prompt.readMore') : t('prompt.readLess');
    });
  }

  // Swipe gestures (FR-007): left reveals delete (with confirmation, same as
  // the visible Delete button), right opens the editor (same as tapping the
  // card). Both are shortcuts for the existing, always-visible controls above.
  // The returned detach fn is intentionally unused: each card is a fresh,
  // never-reused element (unlike the version carousel's persistent
  // versionList, which stores/calls its detach fn before re-initializing in
  // place) and renderPrompts() always discards prior cards wholesale via
  // container.innerHTML = '', which drops the listeners with the node.
  attachSwipeReveal(div, {
    onSwipeLeft: () => {
      lastSelectedPromptId = parseInt(id, 10);
      handlers.onDelete(id);
    },
    onSwipeRight: () => {
      lastSelectedPromptId = parseInt(id, 10);
      handlers.onEdit(id);
    },
  });

  return div;
}

function setFavoriteButtonA11y(button: HTMLButtonElement, isFavorite: boolean): void {
  button.setAttribute('aria-pressed', isFavorite ? 'true' : 'false');
  const label = isFavorite ? t('actions.removeFavorite') : t('actions.addFavorite');
  button.setAttribute('aria-label', label);
  button.title = label;
}

function renderCategories(categories: string[]): void {
  const list = document.getElementById('categories-list');
  const listMobile = document.getElementById('categories-list-mobile');
  const emptyState = document.getElementById('categories-sidebar-empty');
  const emptyStateMobile = document.getElementById('categories-sidebar-empty-mobile');

  if (!list) return;

  // Clear existing categories except "All Categories"
  const allPromptsItem = list.querySelector('[data-category="all"]');
  // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
  list.innerHTML = '';
  if (allPromptsItem) {
    list.appendChild(allPromptsItem);
  }

  // Handle mobile list
  if (listMobile) {
    const allPromptsItemMobile = listMobile.querySelector('[data-category="all"]');
    // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
    listMobile.innerHTML = '';
    if (allPromptsItemMobile) {
      listMobile.appendChild(allPromptsItemMobile);
    }
  }

  // Show/hide empty states
  if (categories.length === 0) {
    showElement(emptyState);
    showElement(emptyStateMobile);
    syncRovingTabindexForList(list);
    syncRovingTabindexForList(listMobile);
    return;
  } else {
    hideElement(emptyState);
    hideElement(emptyStateMobile);
  }

  const categoryColorMap = getCategoryColorMap();
  categories.forEach((category) => {
    const li = document.createElement('li');
    li.dataset.category = category;
    li.setAttribute('role', 'option');
    li.setAttribute('aria-selected', 'false');
    li.classList.add('flex', 'items-center', 'gap-2');

    const color = categoryColorMap[category];
    const background = resolveCssColor(color);
    if (background) {
      const swatch = document.createElement('span');
      swatch.className = 'inline-block h-2.5 w-2.5 rounded-full';
      swatch.style.backgroundColor = background;
      li.appendChild(swatch);
    }

    const label = document.createElement('span');
    label.textContent = category;
    li.appendChild(label);

    list.appendChild(li);

    // Add to mobile list too
    if (listMobile) {
      const liMobile = li.cloneNode(true) as HTMLElement;
      listMobile.appendChild(liMobile);
    }
  });

  syncRovingTabindexForList(list);
  syncRovingTabindexForList(listMobile);

  // Restore active filter state from searchState
  if (searchState.category && searchState.category !== 'all') {
    const desktopItem = list.querySelector(`[data-category="${searchState.category}"]`);
    const mobileItem = listMobile?.querySelector(`[data-category="${searchState.category}"]`);
    if (desktopItem) {
      desktopItem.classList.add('active');
      desktopItem.setAttribute('aria-selected', 'true');
    }
    if (mobileItem) {
      mobileItem.classList.add('active');
      mobileItem.setAttribute('aria-selected', 'true');
    }
  } else {
    const desktopAllItem = list.querySelector('[data-category="all"]');
    const mobileAllItem = listMobile?.querySelector('[data-category="all"]');
    if (desktopAllItem) {
      desktopAllItem.classList.add('active');
      desktopAllItem.setAttribute('aria-selected', 'true');
    }
    if (mobileAllItem) {
      mobileAllItem.classList.add('active');
      mobileAllItem.setAttribute('aria-selected', 'true');
    }
  }
  syncRovingTabindexForList(list);
  syncRovingTabindexForList(listMobile);
}

function renderTags(tags: TagInfo[]): void {
  const list = document.getElementById('tags-list');
  const listMobile = document.getElementById('tags-list-mobile');
  const emptyState = document.getElementById('tags-sidebar-empty');
  const emptyStateMobile = document.getElementById('tags-sidebar-empty-mobile');

  if (!list) return;

  // Clear existing tags except "All Tags"
  const allTagsItem = list.querySelector('[data-tag="all"]');
  // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
  list.innerHTML = '';
  if (allTagsItem) {
    list.appendChild(allTagsItem);
  }

  // Handle mobile list
  if (listMobile) {
    const allTagsItemMobile = listMobile.querySelector('[data-tag="all"]');
    // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
    listMobile.innerHTML = '';
    if (allTagsItemMobile) {
      listMobile.appendChild(allTagsItemMobile);
    }
  }

  // Show/hide empty states
  if (tags.length === 0) {
    showElement(emptyState);
    showElement(emptyStateMobile);
    syncRovingTabindexForList(list);
    syncRovingTabindexForList(listMobile);
    return;
  } else {
    hideElement(emptyState);
    hideElement(emptyStateMobile);
  }

  const tagColorMap = getTagColorMap();
  tags.forEach((tag) => {
    const li = document.createElement('li');
    li.dataset.tag = tag.name;
    li.setAttribute('role', 'option');
    li.setAttribute('aria-selected', 'false');
    li.classList.add('flex', 'items-center', 'justify-between', 'gap-2');

    const left = document.createElement('div');
    left.className = 'flex items-center gap-2';

    const background = resolveCssColor(tag.color ?? tagColorMap[tag.name]);
    if (background) {
      const swatch = document.createElement('span');
      swatch.className = 'inline-block h-2.5 w-2.5 rounded-full';
      swatch.style.backgroundColor = background;
      left.appendChild(swatch);
    }

    const nameSpan = document.createElement('span');
    nameSpan.textContent = tag.name;
    left.appendChild(nameSpan);
    li.appendChild(left);

    const countSpan = document.createElement('span');
    countSpan.className = 'text-xs text-gray-500';
    countSpan.textContent = `(${tag.count})`;
    li.appendChild(countSpan);

    list.appendChild(li);

    // Add to mobile list too
    if (listMobile) {
      const liMobile = li.cloneNode(true) as HTMLElement;
      listMobile.appendChild(liMobile);
    }
  });

  syncRovingTabindexForList(list);
  syncRovingTabindexForList(listMobile);

  // Restore active filter state from searchState
  if (searchState.tag && searchState.tag !== 'all') {
    const desktopItem = list.querySelector(`[data-tag="${searchState.tag}"]`);
    const mobileItem = listMobile?.querySelector(`[data-tag="${searchState.tag}"]`);
    if (desktopItem) {
      desktopItem.classList.add('active');
      desktopItem.setAttribute('aria-selected', 'true');
    }
    if (mobileItem) {
      mobileItem.classList.add('active');
      mobileItem.setAttribute('aria-selected', 'true');
    }
  } else {
    const desktopAllItem = list.querySelector('[data-tag="all"]');
    const mobileAllItem = listMobile?.querySelector('[data-tag="all"]');
    if (desktopAllItem) {
      desktopAllItem.classList.add('active');
      desktopAllItem.setAttribute('aria-selected', 'true');
    }
    if (mobileAllItem) {
      mobileAllItem.classList.add('active');
      mobileAllItem.setAttribute('aria-selected', 'true');
    }
  }
  syncRovingTabindexForList(list);
  syncRovingTabindexForList(listMobile);
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
