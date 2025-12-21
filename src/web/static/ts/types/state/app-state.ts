/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import type { PromptResponse, VersionInfo } from '../api/responses';

/**
 * Search and filter state for prompt list
 */
export interface SearchState {
  searchTerm: string;
  category: string;
  tag: string;
  favorites: boolean;
  caseSensitive: boolean;
  isLoading: boolean;
}

/**
 * Generic cache entry with timestamp for TTL
 */
export interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

/**
 * Tag autocomplete state
 */
export interface TagAutocompleteState {
  isOpen: boolean;
  suggestions: string[];
  selectedIndex: number;
  inputValue: string;
}

/**
 * Main application state (app.ts)
 */
export interface AppState {
  /** Cache of loaded prompts by ID */
  promptCache: Record<string, PromptResponse>;
  /** Last selected prompt ID for details view */
  lastSelectedPromptId: string | null;
  /** Set of selected prompt IDs for bulk operations */
  selectedPromptIds: Set<number>;
  /** Current search/filter state */
  searchState: SearchState;
  /** Cached version histories (TTL: 5 minutes) */
  versionCache: Record<string, CacheEntry<VersionInfo[]>>;
  /** Cached diff results (TTL: 5 minutes) */
  diffCache: Record<string, CacheEntry<unknown>>;
  /** Tag autocomplete state */
  tagAutocompleteState: TagAutocompleteState;
  /** Selected versions for comparison */
  selectedVersionIds: {
    left: string | null;
    right: string | null;
  };
  /** UI flags for modals and panels */
  uiState: {
    isLoading: boolean;
    isVersionHistoryOpen: boolean;
    isDiffModalOpen: boolean;
    isPromptEditorOpen: boolean;
  };
}
