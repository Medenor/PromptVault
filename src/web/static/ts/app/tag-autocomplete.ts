/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { apiFetch, apiGet } from '@/utils/api';
import { t } from '@/utils/i18n';
import { showNotification } from '@/utils/notifications';
import { getSoftMutedColorScheme, getTagColorMap, normalizeTagItems, setTagColorMap, applyPromptColorStyles } from './colors';
import { showElement, hideElement, reportAppIssue, MAX_TAGS } from './shared';
import { showPromptFieldError, clearPromptFieldError } from './prompt-form';
import type { TagInfo, TagItem } from './types';

let selectedTags: string[] = [];
let availableTags: TagInfo[] = [];
const tagAutocompleteState = {
  isOpen: false,
  highlightedIndex: -1,
  filteredTags: [] as TagInfo[],
  currentPartialTag: '',
};

export function getSelectedTags(): string[] {
  return selectedTags;
}

export function getAvailableTags(): TagInfo[] {
  return availableTags;
}

export function getTagInputElement(): HTMLInputElement | null {
  return document.getElementById('prompt-tags-input') as HTMLInputElement | null;
}

export function getTagHiddenInput(): HTMLInputElement | null {
  return document.getElementById('prompt-tags') as HTMLInputElement | null;
}

export function parseTagInput(value: string): string[] {
  return value
    .split(',')
    .map((tag) => tag.trim())
    .filter((tag) => tag.length > 0);
}

function dedupeTags(tags: string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const tag of tags) {
    const normalized = tag.toLowerCase();
    if (!normalized || seen.has(normalized)) {
      continue;
    }
    seen.add(normalized);
    result.push(tag);
  }
  return result;
}

export function syncHiddenTags(): void {
  const hidden = getTagHiddenInput();
  if (!hidden) {
    return;
  }
  hidden.value = selectedTags.join(', ');
}

export function renderTagChips(): void {
  const chipContainer = document.getElementById('tag-chips');
  const input = getTagInputElement();
  if (!chipContainer) {
    return;
  }
  chipContainer.innerHTML = '';

  // Don't show empty state - the input placeholder already provides guidance

  const tagColorMap = getTagColorMap();
  selectedTags.forEach((tag) => {
    const color = tagColorMap[tag];
    const chip = document.createElement('span');
    chip.className =
      'inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-full border';

    // Apply soft/muted color scheme (Option B)
    const colorScheme = getSoftMutedColorScheme(color || '');
    chip.style.backgroundColor = colorScheme.background;
    chip.style.color = colorScheme.text;
    chip.style.borderColor = colorScheme.border;

    chip.dataset.tagName = tag;
    chip.innerHTML = `
      <span>${tag}</span>
      <button type="button" class="text-xs leading-none px-1 opacity-70 hover:opacity-100 transition-opacity" aria-label="${t(
        'actions.remove'
      )}">×</button>
    `;
    chipContainer.appendChild(chip);
  });

  if (input) {
    input.placeholder = selectedTags.length === 0 ? t('form.tagPlaceholder') : '';
  }
}

export function setSelectedTags(tags: string[]): void {
  selectedTags = dedupeTags(tags);
  if (selectedTags.length > MAX_TAGS) {
    selectedTags = selectedTags.slice(0, MAX_TAGS);
    showPromptFieldError('prompt-tags', 'prompt-tags-error', 'validation.tagsMax', false, true);
  } else {
    clearPromptFieldError('prompt-tags', 'prompt-tags-error');
  }
  renderTagChips();
  syncHiddenTags();
}

export function addTags(tags: string[]): void {
  const existing = selectedTags.map((tag) => tag.toLowerCase());
  let added = 0;
  const incoming = dedupeTags(tags);
  for (const tag of incoming) {
    if (selectedTags.length >= MAX_TAGS) {
      showPromptFieldError('prompt-tags', 'prompt-tags-error', 'validation.tagsMax', false, true);
      break;
    }
    if (!existing.includes(tag.toLowerCase())) {
      selectedTags.push(tag);
      existing.push(tag.toLowerCase());
      added++;
    }
  }
  if (added > 0) {
    clearPromptFieldError('prompt-tags', 'prompt-tags-error', true);
  }
  renderTagChips();
  syncHiddenTags();
}

export function removeTag(tagName: string): void {
  const normalized = tagName.toLowerCase();
  selectedTags = selectedTags.filter((tag) => tag.toLowerCase() !== normalized);
  renderTagChips();
  syncHiddenTags();
}

function mergeTagSuggestions(existing: string[], suggestions: string[]): string[] {
  const existingSet = new Set(existing.map((tag) => tag.toLowerCase()));
  const merged = [...existing];
  for (const suggestion of suggestions) {
    if (!existingSet.has(suggestion.toLowerCase())) {
      merged.push(suggestion);
      existingSet.add(suggestion.toLowerCase());
    }
  }
  return merged;
}

export async function handleSuggestTags(): Promise<void> {
  const promptInput = document.getElementById('prompt-content') as HTMLTextAreaElement | null;
  const tagInput = getTagInputElement();
  if (!promptInput || !tagInput) {
    return;
  }

  const content = promptInput.value.trim();
  if (!content) {
    showNotification(t('messages.suggestTagsMissingContent'), 'info');
    return;
  }

  try {
    const response = await apiFetch<{ suggestions: Array<{ name: string; score: number }> }>(
      '/api/tags/suggest',
      {
        method: 'POST',
        body: JSON.stringify({ content, limit: 10 }),
      }
    );
    const suggestedNames = response.suggestions.map((item) => item.name);
    if (suggestedNames.length === 0) {
      showNotification(t('messages.suggestTagsNoSuggestions'), 'info');
      return;
    }
    const merged = mergeTagSuggestions(selectedTags, suggestedNames);
    setSelectedTags(merged);
    tagInput.value = '';
  } catch (error) {
    reportAppIssue('suggestTags', error);
    showNotification(t('messages.suggestTagsFailed'), 'error');
  }
}

export async function loadAvailableTags(): Promise<void> {
  try {
    try {
      const data = await apiGet<{ items: TagItem[] }>('/api/tags/manage');
      availableTags = normalizeTagItems(data.items || []);
      setTagColorMap(availableTags);
      applyPromptColorStyles();
      return;
    } catch (error) {
      reportAppIssue('loadTagsAutocompleteMetadata', error, {}, 'warning');
    }

    const data = await apiGet<{ tags: TagInfo[] }>('/api/tags');
    // Store tags with counts
    availableTags = data.tags || [];
    setTagColorMap(availableTags);
    applyPromptColorStyles();
  } catch (error) {
    reportAppIssue('loadTagsAutocomplete', error);
    availableTags = [];
  }
}

export function setupTagAutocomplete(): void {
  const tagInput = getTagInputElement();
  const autocompleteDiv = document.getElementById('tag-autocomplete') as HTMLElement | null;
  const chipContainer = document.getElementById('tag-chips');
  const chipInputWrapper = document.getElementById('tag-chip-input');

  if (!tagInput || !autocompleteDiv || !chipContainer || !chipInputWrapper) {
    return;
  }

  // Load available tags when setting up
  void loadAvailableTags();

  // Input event - show suggestions as user types
  tagInput.addEventListener('input', (event) => {
    const target = event.target as HTMLInputElement | null;
    if (target) {
      handleTagInput(target);
    }
  });

  // Keydown event - handle keyboard navigation
  tagInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      if (tagAutocompleteState.isOpen && tagAutocompleteState.highlightedIndex >= 0) {
        handleTagInputKeydown(event);
        return;
      }
      event.preventDefault();
      commitTagInput(tagInput);
      return;
    }
    if (event.key === ',') {
      event.preventDefault();
      commitTagInput(tagInput);
      return;
    }
    if (event.key === 'Backspace' && tagInput.value.trim() === '' && selectedTags.length > 0) {
      event.preventDefault();
      const lastTag = selectedTags[selectedTags.length - 1];
      if (lastTag) {
        removeTag(lastTag);
      }
      return;
    }
    handleTagInputKeydown(event);
  });

  // Focus event - show suggestions if there's partial input
  tagInput.addEventListener('focus', (event) => {
    const target = event.target as HTMLInputElement | null;
    if (!target) {
      return;
    }
    void loadAvailableTags().then(() => {
      handleTagInput(target);
    });
  });

  // Click event - reopen suggestions even if already focused
  tagInput.addEventListener('click', (event) => {
    const target = event.target as HTMLInputElement | null;
    if (!target) {
      return;
    }
    if (!tagAutocompleteState.isOpen) {
      handleTagInput(target);
    }
  });

  chipInputWrapper.addEventListener('click', () => {
    tagInput.focus();
    if (!tagAutocompleteState.isOpen) {
      handleTagInput(tagInput);
    }
  });

  chipContainer.addEventListener('click', (event) => {
    const target = event.target as HTMLElement | null;
    if (!target) {
      return;
    }
    if (target.tagName.toLowerCase() === 'button') {
      const chip = target.closest('[data-tag-name]') as HTMLElement | null;
      const tagName = chip?.dataset.tagName;
      if (tagName) {
        removeTag(tagName);
      }
      return;
    }
    tagInput.focus();
  });

  // Blur event - close dropdown with delay to allow clicks
  tagInput.addEventListener('blur', () => {
    commitTagInput(tagInput);
    setTimeout(() => {
      closeTagAutocomplete();
    }, 200);
  });

  // Click outside to close
  document.addEventListener('click', (event) => {
    if (
      !tagInput.contains(event.target as Node) &&
      !autocompleteDiv.contains(event.target as Node)
    ) {
      closeTagAutocomplete();
    }
  });

  const hidden = getTagHiddenInput();
  if (hidden && hidden.value) {
    setSelectedTags(parseTagInput(hidden.value));
  } else {
    setSelectedTags([]);
  }
}

function handleTagInput(input: HTMLInputElement): void {
  const value = input.value;
  const cursorPosition = input.selectionStart ?? input.value.length;

  // Find the current tag being typed (based on cursor position)
  const beforeCursor = value.substring(0, cursorPosition);
  const lastCommaIndex = beforeCursor.lastIndexOf(',');
  const partialTag = beforeCursor.substring(lastCommaIndex + 1).trim();

  tagAutocompleteState.currentPartialTag = partialTag;

  // Filter available tags
  const filtered = filterTags(partialTag, selectedTags);
  tagAutocompleteState.filteredTags = filtered;
  tagAutocompleteState.highlightedIndex = -1;

  // Show or hide autocomplete
  if (filtered.length > 0 || partialTag.length > 0) {
    showTagAutocomplete(filtered);
  } else {
    closeTagAutocomplete();
  }
}

export function commitTagInput(input: HTMLInputElement): void {
  const tags = parseTagInput(input.value);
  if (tags.length === 0) {
    return;
  }
  addTags(tags);
  input.value = '';
  handleTagInput(input);
}

function filterTags(partialTag: string, selected: string[]): TagInfo[] {
  if (!availableTags || availableTags.length === 0) {
    return [];
  }

  // Case-insensitive filtering
  const searchTerm = partialTag.toLowerCase();
  const selectedSet = new Set(selected.map((tag) => tag.toLowerCase()));

  const filtered = availableTags.filter((tag) => {
    const tagName = tag.name;
    const tagLower = tagName.toLowerCase();
    // Don't suggest tags already entered
    if (selectedSet.has(tagLower)) {
      return false;
    }
    // Match tags that contain the search term
    return searchTerm === '' || tagLower.includes(searchTerm);
  });

  if (searchTerm === '') {
    return filtered.sort((a, b) => a.name.localeCompare(b.name)).slice(0, 50);
  }

  return filtered.sort((a, b) => b.count - a.count).slice(0, 10); // Limit to 10 suggestions
}

function showTagAutocomplete(filteredTags: TagInfo[]): void {
  const autocompleteDiv = document.getElementById('tag-autocomplete');
  if (!autocompleteDiv) {
    return;
  }

  autocompleteDiv.innerHTML = '';

  if (filteredTags.length === 0) {
    // Show "No matching tags" message
    const noResults = document.createElement('div');
    noResults.className = 'px-4 py-3 text-sm text-gray-500 text-center';
    noResults.textContent = 'No matching tags';
    autocompleteDiv.appendChild(noResults);
  } else {
    // Show tag suggestions
    filteredTags.forEach((tag, index) => {
      const tagName = tag.name;
      const tagCount = tag.count;

      const item = document.createElement('div');
      item.className =
        'tag-autocomplete-item px-4 py-2 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center justify-between';
      item.dataset.index = String(index);
      item.dataset.tagName = tagName;

      const nameSpan = document.createElement('span');
      nameSpan.className = 'text-sm text-gray-900 dark:text-gray-100';
      nameSpan.textContent = tagName;
      item.appendChild(nameSpan);

      if (tagCount !== null) {
        const countSpan = document.createElement('span');
        countSpan.className = 'text-xs text-gray-500';
        countSpan.textContent = `(${tagCount})`;
        item.appendChild(countSpan);
      }

      // Click handler
      const usePointerEvents = 'PointerEvent' in window;
      const selectHandler = (event: Event) => {
        // Prevent input blur so we don't commit the partial tag.
        event.preventDefault();
        selectTag(tagName);
      };
      if (usePointerEvents) {
        item.addEventListener('pointerdown', selectHandler);
      } else {
        item.addEventListener('mousedown', selectHandler);
      }

      // Hover handler
      item.addEventListener('mouseenter', function () {
        highlightTagItem(index);
      });

      autocompleteDiv.appendChild(item);
    });
  }

  showElement(autocompleteDiv);
  tagAutocompleteState.isOpen = true;
}

function closeTagAutocomplete(): void {
  const autocompleteDiv = document.getElementById('tag-autocomplete');
  if (autocompleteDiv) {
    hideElement(autocompleteDiv);
  }
  tagAutocompleteState.isOpen = false;
  tagAutocompleteState.highlightedIndex = -1;
}

function handleTagInputKeydown(event: KeyboardEvent): void {
  if (!tagAutocompleteState.isOpen) {
    return;
  }

  const filteredTags = tagAutocompleteState.filteredTags;

  switch (event.key) {
    case 'ArrowDown':
      event.preventDefault();
      if (filteredTags.length > 0) {
        tagAutocompleteState.highlightedIndex =
          (tagAutocompleteState.highlightedIndex + 1) % filteredTags.length;
        highlightTagItem(tagAutocompleteState.highlightedIndex);
      }
      break;

    case 'ArrowUp':
      event.preventDefault();
      if (filteredTags.length > 0) {
        tagAutocompleteState.highlightedIndex =
          tagAutocompleteState.highlightedIndex <= 0
            ? filteredTags.length - 1
            : tagAutocompleteState.highlightedIndex - 1;
        highlightTagItem(tagAutocompleteState.highlightedIndex);
      }
      break;

    case 'Enter':
      if (
        tagAutocompleteState.highlightedIndex >= 0 &&
        tagAutocompleteState.highlightedIndex < filteredTags.length
      ) {
        event.preventDefault();
        const selectedTag = filteredTags[tagAutocompleteState.highlightedIndex];
        if (selectedTag) {
          selectTag(selectedTag.name);
        }
      }
      break;

    case 'Escape':
      event.preventDefault();
      event.stopPropagation();
      closeTagAutocomplete();
      break;

    case 'Tab':
      if (
        tagAutocompleteState.highlightedIndex >= 0 &&
        tagAutocompleteState.highlightedIndex < filteredTags.length
      ) {
        event.preventDefault();
        const selectedTag = filteredTags[tagAutocompleteState.highlightedIndex];
        if (selectedTag) {
          selectTag(selectedTag.name);
        }
      }
      break;
  }
}

function highlightTagItem(index: number): void {
  const autocompleteDiv = document.getElementById('tag-autocomplete');
  if (!autocompleteDiv) {
    return;
  }

  // Remove previous highlight
  autocompleteDiv.querySelectorAll('.tag-autocomplete-item').forEach((item) => {
    item.classList.remove('highlighted', 'bg-blue-50', 'dark:bg-blue-950');
  });

  // Add new highlight
  const items = autocompleteDiv.querySelectorAll('.tag-autocomplete-item');
  if (items[index]) {
    items[index].classList.add('highlighted', 'bg-blue-50', 'dark:bg-blue-950');
    // Scroll into view if needed
    items[index].scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }

  tagAutocompleteState.highlightedIndex = index;
}

function selectTag(tagName: string): void {
  const tagInput = getTagInputElement();
  if (!tagInput) {
    return;
  }
  addTags([tagName]);
  tagInput.value = '';
  tagInput.focus();

  // Close autocomplete
  closeTagAutocomplete();

  // Trigger input event to potentially show new suggestions
  setTimeout(() => {
    handleTagInput(tagInput);
  }, 50);
}
