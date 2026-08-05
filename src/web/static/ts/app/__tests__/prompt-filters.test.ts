/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { beforeEach, describe, expect, it } from 'vitest';
import {
  buildSearchUrl,
  currentFilters,
  isAnyFilterActive,
  renderCategories,
  renderTags,
  searchState,
} from '../prompt-filters';

function resetSearchState(): void {
  searchState.searchTerm = '';
  searchState.category = 'all';
  searchState.tag = 'all';
  searchState.favorites = false;
  searchState.sharedWithMe = false;
  searchState.caseSensitive = false;
  searchState.isLoading = false;
}

describe('currentFilters / buildSearchUrl', () => {
  beforeEach(() => {
    resetSearchState();
  });

  it('reflects the current searchState snapshot', () => {
    searchState.searchTerm = 'foo';
    searchState.category = 'dev';
    expect(currentFilters()).toEqual({
      searchTerm: 'foo',
      category: 'dev',
      tag: 'all',
      favorites: false,
      sharedWithMe: false,
      caseSensitive: false,
    });
  });

  it('omits default/empty filters from the query string', () => {
    const url = buildSearchUrl(1, 25);
    expect(url).toBe('/api/prompts/search?page=1&limit=25');
  });

  it('includes only the active filters', () => {
    searchState.searchTerm = 'hello world';
    searchState.category = 'writing';
    searchState.favorites = true;
    searchState.caseSensitive = true;

    const url = buildSearchUrl(2, 10);
    expect(url).toContain('search=hello+world');
    expect(url).toContain('category=writing');
    expect(url).toContain('favorites=true');
    expect(url).toContain('case_sensitive=true');
    expect(url).toContain('page=2');
    expect(url).toContain('limit=10');
    expect(url).not.toContain('filter=shared-with-me');
  });

  it('includes filter=shared-with-me when sharedWithMe is active (007-prompt-sharing US2)', () => {
    searchState.sharedWithMe = true;
    const url = buildSearchUrl(1, 25);
    expect(url).toContain('filter=shared-with-me');
  });
});

describe('isAnyFilterActive', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <input id="search-input" value="" />
      <input id="favorites-filter" type="checkbox" />
      <input id="shared-with-me-filter" type="checkbox" />
      <ul id="categories-list"><li data-category="all" class="active"></li></ul>
      <ul id="tags-list"><li data-tag="all" class="active"></li></ul>
    `;
  });

  it('returns false when no filters are active', () => {
    expect(isAnyFilterActive()).toBe(false);
  });

  it('returns true when the search input has text', () => {
    (document.getElementById('search-input') as HTMLInputElement).value = 'abc';
    expect(isAnyFilterActive()).toBe(true);
  });

  it('returns true when the favorites checkbox is checked', () => {
    (document.getElementById('favorites-filter') as HTMLInputElement).checked = true;
    expect(isAnyFilterActive()).toBe(true);
  });

  it('returns true when the shared-with-me checkbox is checked', () => {
    (document.getElementById('shared-with-me-filter') as HTMLInputElement).checked = true;
    expect(isAnyFilterActive()).toBe(true);
  });

  it('returns true when a non-"all" category is active', () => {
    document.querySelector('#categories-list li')?.setAttribute('data-category', 'writing');
    expect(isAnyFilterActive()).toBe(true);
  });
});

describe('renderCategories', () => {
  beforeEach(() => {
    resetSearchState();
    document.body.innerHTML = `
      <ul id="categories-list"><li data-category="all"></li></ul>
      <ul id="categories-list-mobile"><li data-category="all"></li></ul>
      <div id="categories-sidebar-empty" class="hidden"></div>
      <div id="categories-sidebar-empty-mobile" class="hidden"></div>
    `;
  });

  it('renders one <li> per category plus the preserved "all" item', () => {
    renderCategories(['writing', 'coding']);
    const items = document.querySelectorAll('#categories-list li');
    expect(items.length).toBe(3);
    expect(document.querySelector('#categories-list [data-category="writing"]')).not.toBeNull();
  });

  it('shows the empty state when there are no categories', () => {
    renderCategories([]);
    expect(document.getElementById('categories-sidebar-empty')?.classList.contains('hidden')).toBe(
      false
    );
  });

  it('marks the item matching searchState.category as active', () => {
    searchState.category = 'writing';
    renderCategories(['writing', 'coding']);
    const active = document.querySelector('#categories-list [data-category="writing"]');
    expect(active?.classList.contains('active')).toBe(true);
  });
});

describe('renderTags', () => {
  beforeEach(() => {
    resetSearchState();
    document.body.innerHTML = `
      <ul id="tags-list"><li data-tag="all"></li></ul>
      <ul id="tags-list-mobile"><li data-tag="all"></li></ul>
      <div id="tags-sidebar-empty" class="hidden"></div>
      <div id="tags-sidebar-empty-mobile" class="hidden"></div>
    `;
  });

  it('renders tag items with their usage count', () => {
    renderTags([{ name: 'urgent', count: 3 }]);
    const item = document.querySelector('#tags-list [data-tag="urgent"]');
    expect(item?.textContent).toContain('urgent');
    expect(item?.textContent).toContain('(3)');
  });

  it('shows the empty state when there are no tags', () => {
    renderTags([]);
    expect(document.getElementById('tags-sidebar-empty')?.classList.contains('hidden')).toBe(false);
  });
});
