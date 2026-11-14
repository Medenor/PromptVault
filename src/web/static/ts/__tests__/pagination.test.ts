import { describe, expect, it } from 'vitest';
import {
  PAGE_SIZE_OPTIONS,
  DEFAULT_PAGE_SIZE,
  createInitialPaginationState,
  filtersChanged,
  mergePrompts,
  canLoadMore,
  type PaginationFilters,
} from '@/utils/pagination';

const noFilters: PaginationFilters = {
  searchTerm: '',
  category: 'all',
  tag: 'all',
  favorites: false,
  sharedWithMe: false,
  itemType: 'all' as const,
  caseSensitive: false,
};

describe('pagination utils', () => {
  it('exposes the three supported page size options with a default of 25', () => {
    expect(PAGE_SIZE_OPTIONS).toEqual([25, 50, 100]);
    expect(DEFAULT_PAGE_SIZE).toBe(25);
  });

  it('creates initial state at page 1 with hasNext false and no loading', () => {
    const state = createInitialPaginationState(noFilters);
    expect(state.currentPage).toBe(1);
    expect(state.pageSize).toBe(25);
    expect(state.hasNext).toBe(false);
    expect(state.isLoadingMore).toBe(false);
    expect(state.activeFilters).toEqual(noFilters);
  });

  it('accepts a custom initial page size', () => {
    const state = createInitialPaginationState(noFilters, 25);
    expect(state.pageSize).toBe(25);
  });

  describe('filtersChanged', () => {
    it('returns false when filters are identical', () => {
      const state = createInitialPaginationState(noFilters);
      expect(filtersChanged(state, { ...noFilters })).toBe(false);
    });

    it.each<[keyof PaginationFilters, string | boolean]>([
      ['searchTerm', 'hello'],
      ['category', 'Marketing'],
      ['tag', 'email'],
      ['favorites', true],
      ['sharedWithMe', true],
      ['caseSensitive', true],
    ])('returns true when %s changes', (key, value) => {
      const state = createInitialPaginationState(noFilters);
      const changed = { ...noFilters, [key]: value } as PaginationFilters;
      expect(filtersChanged(state, changed)).toBe(true);
    });
  });

  describe('mergePrompts', () => {
    it('replace mode discards prior results entirely', () => {
      const existing = { '1': { id: 1 } };
      const incoming = { '2': { id: 2 } };
      const result = mergePrompts(existing, incoming, 'replace');
      expect(result).toEqual({ '2': { id: 2 } });
    });

    it('append mode merges into the existing dict without losing prior entries', () => {
      const existing = { '1': { id: 1 } };
      const incoming = { '2': { id: 2 } };
      const result = mergePrompts(existing, incoming, 'append');
      expect(result).toEqual({ '1': { id: 1 }, '2': { id: 2 } });
    });

    it('append mode does not mutate the existing object', () => {
      const existing = { '1': { id: 1 } };
      mergePrompts(existing, { '2': { id: 2 } }, 'append');
      expect(existing).toEqual({ '1': { id: 1 } });
    });
  });

  describe('canLoadMore', () => {
    it('allows loading more when hasNext is true and not already loading', () => {
      const state = createInitialPaginationState(noFilters);
      state.hasNext = true;
      expect(canLoadMore(state)).toBe(true);
    });

    it('blocks loading more when hasNext is false', () => {
      const state = createInitialPaginationState(noFilters);
      state.hasNext = false;
      expect(canLoadMore(state)).toBe(false);
    });

    it('blocks a duplicate concurrent request while one is already in flight', () => {
      const state = createInitialPaginationState(noFilters);
      state.hasNext = true;
      state.isLoadingMore = true;
      expect(canLoadMore(state)).toBe(false);
    });
  });
});
