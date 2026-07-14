/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Client-side pagination state and helpers for the prompt list "Load More"
 * flow (offset pagination: page/limit + accumulated results).
 */

export const PAGE_SIZE_OPTIONS = [25, 50, 100] as const;
export type PageSize = (typeof PAGE_SIZE_OPTIONS)[number];
export const DEFAULT_PAGE_SIZE: PageSize = 50;

/** Filter values that determine whether pagination should reset to page 1. */
export interface PaginationFilters {
  searchTerm: string;
  category: string;
  tag: string;
  favorites: boolean;
  caseSensitive: boolean;
}

export interface PaginationState {
  currentPage: number;
  pageSize: PageSize;
  hasNext: boolean;
  isLoadingMore: boolean;
  activeFilters: PaginationFilters;
}

export function createInitialPaginationState(
  filters: PaginationFilters,
  pageSize: PageSize = DEFAULT_PAGE_SIZE
): PaginationState {
  return {
    currentPage: 1,
    pageSize,
    hasNext: false,
    isLoadingMore: false,
    activeFilters: { ...filters },
  };
}

/** True if any filter field differs from the state's last-known filters. */
export function filtersChanged(state: PaginationState, filters: PaginationFilters): boolean {
  const prev = state.activeFilters;
  return (
    prev.searchTerm !== filters.searchTerm ||
    prev.category !== filters.category ||
    prev.tag !== filters.tag ||
    prev.favorites !== filters.favorites ||
    prev.caseSensitive !== filters.caseSensitive
  );
}

/**
 * Merge a newly-fetched page of prompts into the accumulated set.
 *
 * @param mode - 'replace' clears prior results (fresh load / filter change);
 *   'append' merges into the existing dict (Load More), keyed by ID.
 */
export function mergePrompts<T>(
  existing: Record<string, T>,
  incoming: Record<string, T>,
  mode: 'replace' | 'append'
): Record<string, T> {
  if (mode === 'replace') {
    return { ...incoming };
  }
  return { ...existing, ...incoming };
}

/**
 * Determine whether a "Load More" click should be allowed to proceed.
 * Guards against duplicate concurrent requests and fetching past the last page.
 */
export function canLoadMore(state: PaginationState): boolean {
  return state.hasNext && !state.isLoadingMore;
}
