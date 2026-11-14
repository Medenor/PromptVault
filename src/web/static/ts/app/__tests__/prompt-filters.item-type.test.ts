/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('i18next', () => ({ default: { t: vi.fn((key: string) => key), language: 'en' } }));

const performSearchMock = vi.fn();
const loadPromptsMock = vi.fn();
vi.mock('../prompt-list', () => ({
  performSearch: (...args: unknown[]) => performSearchMock(...args),
  loadPrompts: (...args: unknown[]) => loadPromptsMock(...args),
}));

import { buildSearchUrl, currentFilters, isAnyFilterActive, searchState } from '../prompt-filters';
import { clearAllFilters, handleItemTypeFilter } from '../search';

function mountSelects(): [HTMLSelectElement, HTMLSelectElement] {
  document.body.innerHTML = `
    <select id="a" class="item-type-filter"><option value="all"></option><option value="prompt"></option><option value="skill"></option></select>
    <select id="b" class="item-type-filter"><option value="all"></option><option value="prompt"></option><option value="skill"></option></select>
  `;
  return [
    document.getElementById('a') as HTMLSelectElement,
    document.getElementById('b') as HTMLSelectElement,
  ];
}

beforeEach(() => {
  searchState.itemType = 'all';
  searchState.searchTerm = '';
  performSearchMock.mockReset();
  loadPromptsMock.mockReset();
  document.body.innerHTML = '';
});

describe('item type in the search URL', () => {
  it('omits item_type when showing everything', () => {
    expect(buildSearchUrl(1, 25)).not.toContain('item_type');
  });

  it.each(['prompt', 'skill'] as const)('adds item_type=%s', (type) => {
    searchState.itemType = type;
    expect(new URL(buildSearchUrl(2, 50), 'http://x').searchParams.get('item_type')).toBe(type);
  });

  it('composes with the other filters', () => {
    searchState.itemType = 'skill';
    searchState.searchTerm = 'pdf';
    const params = new URL(buildSearchUrl(1, 25), 'http://x').searchParams;
    expect(params.get('search')).toBe('pdf');
    expect(params.get('item_type')).toBe('skill');
  });

  it('is part of the pagination filters', () => {
    searchState.itemType = 'skill';
    expect(currentFilters().itemType).toBe('skill');
  });

  it('counts as an active filter', () => {
    expect(isAnyFilterActive()).toBe(false);
    searchState.itemType = 'prompt';
    expect(isAnyFilterActive()).toBe(true);
  });
});

describe('handleItemTypeFilter', () => {
  it('stores the choice, syncs every selector and searches', () => {
    const [a, b] = mountSelects();
    a.value = 'skill';
    handleItemTypeFilter({ target: a } as unknown as Event);
    expect(searchState.itemType).toBe('skill');
    expect(b.value).toBe('skill');
    expect(performSearchMock).toHaveBeenCalledTimes(1);
  });

  it('reloads the plain list when going back to All', () => {
    const [a] = mountSelects();
    searchState.itemType = 'skill';
    a.value = 'all';
    handleItemTypeFilter({ target: a } as unknown as Event);
    expect(searchState.itemType).toBe('all');
    expect(loadPromptsMock).toHaveBeenCalledTimes(1);
    expect(performSearchMock).not.toHaveBeenCalled();
  });

  it('treats an unknown value as All', () => {
    const [a] = mountSelects();
    const option = document.createElement('option');
    option.value = 'banana';
    a.appendChild(option);
    a.value = 'banana';
    handleItemTypeFilter({ target: a } as unknown as Event);
    expect(searchState.itemType).toBe('all');
  });

  it('is cleared with the other filters', () => {
    const [a, b] = mountSelects();
    searchState.itemType = 'prompt';
    a.value = 'prompt';
    clearAllFilters();
    expect(searchState.itemType).toBe('all');
    expect(a.value).toBe('all');
    expect(b.value).toBe('all');
  });
});
