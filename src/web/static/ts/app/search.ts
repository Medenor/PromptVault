/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { debounce } from '@/utils/debounce';
import { closeSearchOverlay, isSearchOverlayOpen } from '@/search-overlay';
import { hideElement, toggleElement } from './shared';
import { syncFilterListsRovingTabindex } from './keyboard-nav';
import { loadPrompts, performSearch } from './prompt-list';
import { searchState } from './prompt-filters';

// How long the search overlay stays open, with no typing, after results load
// before auto-closing (FR-016). Kept well above the search debounce so the
// overlay doesn't feel like it's snapping shut while results are still being
// read.
const SEARCH_OVERLAY_AUTO_CLOSE_MS = 1200;
let overlayCloseTimeout: ReturnType<typeof setTimeout> | null = null;

export function setupSearchEventListeners(clearAllFilters: () => void): void {
  // Search input with debouncing (desktop)
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

  // Search input (mobile drawer)
  const searchInputMobile = document.getElementById(
    'search-input-mobile'
  ) as HTMLInputElement | null;
  if (searchInputMobile) {
    searchInputMobile.addEventListener('input', handleSearchInput);
    searchInputMobile.addEventListener('keydown', function (event) {
      // Clear search on Escape
      if (event.key === 'Escape') {
        clearAllFilters();
      }
    });
  }

  // Search input (full-screen mobile overlay, FR-016)
  const searchInputOverlay = document.getElementById(
    'search-input-overlay'
  ) as HTMLInputElement | null;
  if (searchInputOverlay) {
    searchInputOverlay.addEventListener('input', handleSearchInput);
  }

  // Inline clear (×) buttons: clear just the search term, not other filters.
  updateSearchClearButtons();
  const searchInputClearPairs: Array<[string, string]> = [
    ['search-input-clear', 'search-input'],
    ['search-input-mobile-clear', 'search-input-mobile'],
    ['search-input-overlay-clear', 'search-input-overlay'],
  ];
  for (const [clearBtnId, inputId] of searchInputClearPairs) {
    const clearBtn = document.getElementById(clearBtnId);
    clearBtn?.addEventListener('click', () => clearSearchTerm(inputId));
  }

  // Case sensitive toggle (desktop)
  const caseSensitiveToggle = document.getElementById(
    'case-sensitive-toggle'
  ) as HTMLInputElement | null;
  if (caseSensitiveToggle) {
    caseSensitiveToggle.addEventListener('change', (event) => {
      const target = event.target as HTMLInputElement | null;
      searchState.caseSensitive = target?.checked ?? false;
      // Sync mobile checkbox
      const caseSensitiveToggleMobile = document.getElementById(
        'case-sensitive-toggle-mobile'
      ) as HTMLInputElement | null;
      if (caseSensitiveToggleMobile) caseSensitiveToggleMobile.checked = searchState.caseSensitive;
      void performSearch();
    });
  }

  // Case sensitive toggle (mobile)
  const caseSensitiveToggleMobile = document.getElementById(
    'case-sensitive-toggle-mobile'
  ) as HTMLInputElement | null;
  if (caseSensitiveToggleMobile) {
    caseSensitiveToggleMobile.addEventListener('change', (event) => {
      const target = event.target as HTMLInputElement | null;
      searchState.caseSensitive = target?.checked ?? false;
      // Sync desktop checkbox
      const caseSensitiveToggle = document.getElementById(
        'case-sensitive-toggle'
      ) as HTMLInputElement | null;
      if (caseSensitiveToggle) caseSensitiveToggle.checked = searchState.caseSensitive;
      void performSearch();
    });
  }

  // Clear all filters button (desktop)
  const clearAllFiltersBtn = document.getElementById('clear-all-filters-btn');
  if (clearAllFiltersBtn) {
    clearAllFiltersBtn.addEventListener('click', clearAllFilters);
  }

  // Clear all filters button (mobile)
  const clearAllFiltersBtnMobile = document.getElementById('clear-all-filters-btn-mobile');
  if (clearAllFiltersBtnMobile) {
    clearAllFiltersBtnMobile.addEventListener('click', clearAllFilters);
  }
}

/** Show each search input's inline × button only while it has text. */
export function updateSearchClearButtons(): void {
  const pairs: Array<[string, string]> = [
    ['search-input', 'search-input-clear'],
    ['search-input-mobile', 'search-input-mobile-clear'],
    ['search-input-overlay', 'search-input-overlay-clear'],
  ];
  for (const [inputId, clearBtnId] of pairs) {
    const input = document.getElementById(inputId) as HTMLInputElement | null;
    const clearBtn = document.getElementById(clearBtnId);
    const icon = input?.parentElement?.querySelector('.search-input-icon');
    const hasValue = !!input?.value;
    toggleElement(clearBtn, hasValue);
    if (icon instanceof SVGElement || icon instanceof HTMLElement) {
      icon.classList.toggle('hidden', hasValue);
    }
  }
}

/** Clear only the search term (all synced inputs), preserving other active filters. */
export function clearSearchTerm(sourceInputId: string): void {
  searchState.searchTerm = '';

  const searchInput = document.getElementById('search-input') as HTMLInputElement | null;
  const searchInputMobile = document.getElementById(
    'search-input-mobile'
  ) as HTMLInputElement | null;
  const searchInputOverlay = document.getElementById(
    'search-input-overlay'
  ) as HTMLInputElement | null;
  if (searchInput) searchInput.value = '';
  if (searchInputMobile) searchInputMobile.value = '';
  if (searchInputOverlay) searchInputOverlay.value = '';

  updateSearchClearButtons();

  const sourceInput = document.getElementById(sourceInputId) as HTMLInputElement | null;
  sourceInput?.focus();

  void performSearch();
}

function handleSearchInput(event: Event): void {
  const target = event.target as HTMLInputElement | null;
  if (!target) {
    return;
  }
  const searchTerm = target.value;
  searchState.searchTerm = searchTerm;

  // Sync all search inputs (desktop, mobile drawer, mobile overlay)
  const searchInput = document.getElementById('search-input') as HTMLInputElement | null;
  const searchInputMobile = document.getElementById(
    'search-input-mobile'
  ) as HTMLInputElement | null;
  const searchInputOverlay = document.getElementById(
    'search-input-overlay'
  ) as HTMLInputElement | null;
  if (searchInput && target.id !== 'search-input') searchInput.value = searchTerm;
  if (searchInputMobile && target.id !== 'search-input-mobile')
    searchInputMobile.value = searchTerm;
  if (searchInputOverlay && target.id !== 'search-input-overlay')
    searchInputOverlay.value = searchTerm;

  updateSearchClearButtons();

  // Clear previous overlay-close timeout
  if (overlayCloseTimeout) {
    clearTimeout(overlayCloseTimeout);
    overlayCloseTimeout = null;
  }

  debouncedSearch(target.id === 'search-input-overlay');
}

const debouncedSearch = debounce((isOverlayInput: boolean) => {
  void performSearch().then(() => {
    // Auto-close the full-screen overlay after results have been visible
    // and idle for a bit, so the user can see the filtered list without an
    // extra manual dismiss (FR-016) but isn't rushed off it while reading.
    if (isOverlayInput && isSearchOverlayOpen()) {
      overlayCloseTimeout = setTimeout(() => {
        closeSearchOverlay();
      }, SEARCH_OVERLAY_AUTO_CLOSE_MS);
    }
  });
}, 300);

export function handleCategoryFilter(event: Event): void {
  const target = event.target as HTMLElement | null;
  const item = target?.closest('li');
  if (item) {
    // Update active state in both desktop and mobile lists
    document.querySelectorAll('#categories-list li').forEach((li) => li.classList.remove('active'));
    document
      .querySelectorAll('#categories-list-mobile li')
      .forEach((li) => li.classList.remove('active'));

    // Add active to the clicked item
    item.classList.add('active');

    // Sync the corresponding item in the other list
    const category = item.dataset.category || 'all';
    const desktopItem = document.querySelector(`#categories-list li[data-category="${category}"]`);
    const mobileItem = document.querySelector(
      `#categories-list-mobile li[data-category="${category}"]`
    );

    if (desktopItem) desktopItem.classList.add('active');
    if (mobileItem) mobileItem.classList.add('active');
    syncFilterListsRovingTabindex();

    // Update search state and trigger search
    searchState.category = category;
    void performSearch();
  }
}

export function handleTagFilter(event: Event): void {
  const target = event.target as HTMLElement | null;
  const item = target?.closest('li');
  if (item) {
    // Update active state in both desktop and mobile lists
    document.querySelectorAll('#tags-list li').forEach((li) => li.classList.remove('active'));
    document
      .querySelectorAll('#tags-list-mobile li')
      .forEach((li) => li.classList.remove('active'));

    // Add active to the clicked item
    item.classList.add('active');

    // Sync the corresponding item in the other list
    const tag = item.dataset.tag || 'all';
    const desktopItem = document.querySelector(`#tags-list li[data-tag="${tag}"]`);
    const mobileItem = document.querySelector(`#tags-list-mobile li[data-tag="${tag}"]`);

    if (desktopItem) desktopItem.classList.add('active');
    if (mobileItem) mobileItem.classList.add('active');
    syncFilterListsRovingTabindex();

    // Update search state and trigger search
    searchState.tag = tag;
    void performSearch();
  }
}

export function handleFavoritesFilter(event: Event): void {
  const target = event.target as HTMLInputElement | null;
  if (!target) return;
  // Update search state and trigger search
  searchState.favorites = target.checked;

  // Sync both checkboxes (desktop and mobile)
  const favoritesFilter = document.getElementById('favorites-filter') as HTMLInputElement | null;
  const favoritesFilterMobile = document.getElementById(
    'favorites-filter-mobile'
  ) as HTMLInputElement | null;

  if (favoritesFilter && target.id !== 'favorites-filter') {
    favoritesFilter.checked = searchState.favorites;
  }
  if (favoritesFilterMobile && target.id !== 'favorites-filter-mobile') {
    favoritesFilterMobile.checked = searchState.favorites;
  }

  void performSearch();
}

export function clearAllFilters(): void {
  // Reset search state
  searchState.searchTerm = '';
  searchState.category = 'all';
  searchState.tag = 'all';
  searchState.favorites = false;
  searchState.caseSensitive = false;
  searchState.isLoading = false;

  // Reset UI elements (desktop)
  const searchInput = document.getElementById('search-input') as HTMLInputElement | null;
  if (searchInput) {
    searchInput.value = '';
  }

  const searchInputOverlay = document.getElementById(
    'search-input-overlay'
  ) as HTMLInputElement | null;
  if (searchInputOverlay) {
    searchInputOverlay.value = '';
  }

  updateSearchClearButtons();

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

  // Reset UI elements (mobile)
  const searchInputMobile = document.getElementById(
    'search-input-mobile'
  ) as HTMLInputElement | null;
  if (searchInputMobile) {
    searchInputMobile.value = '';
  }

  const caseSensitiveToggleMobile = document.getElementById(
    'case-sensitive-toggle-mobile'
  ) as HTMLInputElement | null;
  if (caseSensitiveToggleMobile) {
    caseSensitiveToggleMobile.checked = false;
  }

  const favoritesFilterMobile = document.getElementById(
    'favorites-filter-mobile'
  ) as HTMLInputElement | null;
  if (favoritesFilterMobile) {
    favoritesFilterMobile.checked = false;
  }

  // Reset active states in sidebar (desktop)
  document.querySelectorAll('#categories-list li').forEach((li) => li.classList.remove('active'));
  document.querySelector('[data-category="all"]')?.classList.add('active');

  document.querySelectorAll('#tags-list li').forEach((li) => li.classList.remove('active'));
  document.querySelector('[data-tag="all"]')?.classList.add('active');

  // Reset active states in sidebar (mobile)
  document
    .querySelectorAll('#categories-list-mobile li')
    .forEach((li) => li.classList.remove('active'));
  document
    .querySelectorAll('#categories-list-mobile [data-category="all"]')
    .forEach((li) => li.classList.add('active'));

  document.querySelectorAll('#tags-list-mobile li').forEach((li) => li.classList.remove('active'));
  document
    .querySelectorAll('#tags-list-mobile [data-tag="all"]')
    .forEach((li) => li.classList.add('active'));
  syncFilterListsRovingTabindex();

  // Hide clear filters button and search results info
  const clearAllFiltersBtn = document.getElementById('clear-all-filters-btn');
  if (clearAllFiltersBtn) {
    hideElement(clearAllFiltersBtn);
  }

  const clearAllFiltersBtnMobile = document.getElementById('clear-all-filters-btn-mobile');
  if (clearAllFiltersBtnMobile) {
    hideElement(clearAllFiltersBtnMobile);
  }

  const searchResultsInfo = document.getElementById('search-results-info');
  if (searchResultsInfo) {
    hideElement(searchResultsInfo);
  }

  // Load all prompts
  void loadPrompts();
}
