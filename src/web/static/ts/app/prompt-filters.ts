/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import type { TagInfo } from '@/types';
import { apiGet } from '@/utils/api';
import {
  applyPromptColorStyles,
  clearCategoryColorMap,
  getCategoryColorMap,
  getTagColorMap,
  normalizeTagItems,
  resolveCssColor,
  setCategoryColorMap,
  setTagColorMap,
} from './colors';
import { hideElement, reportAppIssue, showElement } from './shared';
import { syncRovingTabindexForList } from './keyboard-nav';
import type { CategoryItem, TagItem } from './types';

// Global search/filter state shared by the prompt list orchestrator.
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

export function currentFilters() {
  return {
    searchTerm: searchState.searchTerm,
    category: searchState.category,
    tag: searchState.tag,
    favorites: searchState.favorites,
    caseSensitive: searchState.caseSensitive,
  };
}

export function buildSearchUrl(page: number, pageSize: number): string {
  const params = new URLSearchParams();
  if (searchState.searchTerm) params.append('search', searchState.searchTerm);
  if (searchState.category && searchState.category !== 'all')
    params.append('category', searchState.category);
  if (searchState.tag && searchState.tag !== 'all') params.append('tag', searchState.tag);
  if (searchState.favorites) params.append('favorites', 'true');
  if (searchState.caseSensitive) params.append('case_sensitive', 'true');
  params.append('page', String(page));
  params.append('limit', String(pageSize));
  return `/api/prompts/search?${params.toString()}`;
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

export function renderCategories(categories: string[]): void {
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

export function renderTags(tags: TagInfo[]): void {
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
