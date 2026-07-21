/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { t } from '@/utils/i18n';
import { createTypeahead } from '@/utils/typeahead';

export const FILTER_LIST_IDS = [
  'categories-list',
  'tags-list',
  'categories-list-mobile',
  'tags-list-mobile',
] as const;

export function announceKeyboardNavigation(message: string): void {
  const announcer = document.getElementById('keyboard-navigation-announcer');
  if (!announcer) {
    return;
  }
  announcer.textContent = '';
  // Force text change so screen readers always announce the update.
  requestAnimationFrame(() => {
    announcer.textContent = message;
  });
}

export function isTextEditingTarget(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  if (!el) {
    return false;
  }
  if (el.tagName === 'TEXTAREA' || el.tagName === 'SELECT' || el.isContentEditable) {
    return true;
  }
  if (el.tagName !== 'INPUT') {
    return false;
  }
  const input = el as HTMLInputElement;
  const type = (input.type || 'text').toLowerCase();
  return (
    type === 'text' ||
    type === 'search' ||
    type === 'email' ||
    type === 'url' ||
    type === 'tel' ||
    type === 'password' ||
    type === 'number'
  );
}

let promptsListKeyboardNavInitialized = false;

export function initializePromptsListKeyboardNavigation(container: HTMLElement): void {
  if (promptsListKeyboardNavInitialized) {
    return;
  }
  promptsListKeyboardNavInitialized = true;

  const typeahead = createTypeahead();

  container.addEventListener('keydown', (event) => {
    if (event.metaKey || event.ctrlKey || event.altKey) {
      return;
    }
    if (isTextEditingTarget(event.target)) {
      return;
    }
    if ((event as KeyboardEvent).isComposing || event.key === 'Process') {
      return;
    }

    const isCharacterNavigation = event.key.length === 1;
    if (!isCharacterNavigation) {
      return;
    }

    const target = event.target as HTMLElement | null;
    if (!target) {
      return;
    }
    if (!container.contains(target)) {
      return;
    }

    const items = Array.from(container.querySelectorAll<HTMLElement>('.prompt-item'));
    if (items.length === 0) {
      return;
    }

    const currentItem = target.closest<HTMLElement>('.prompt-item');
    const currentIndex = currentItem ? items.indexOf(currentItem) : -1;

    const query = typeahead.pushKey(event.key);
    if (!query) {
      return;
    }

    for (let offset = 1; offset <= items.length; offset++) {
      const index = (currentIndex + offset + items.length) % items.length;
      const candidate = items[index];
      if (!candidate) {
        continue;
      }
      const label =
        (candidate.dataset.navLabel || '').trim() ||
        candidate.querySelector('h4')?.textContent?.trim() ||
        '';
      const normalizedLabel = label.toLocaleLowerCase();
      if (!normalizedLabel.startsWith(query)) {
        continue;
      }

      const checkbox = candidate.querySelector<HTMLInputElement>('input.prompt-checkbox');
      if (checkbox) {
        event.preventDefault();
        checkbox.focus();
        announceKeyboardNavigation(t('accessibility.navigateTo', { item: label }));
      }
      return;
    }
  });

  container.addEventListener('compositionend', (event) => {
    const composed = (event as CompositionEvent).data ?? '';
    const query = typeahead.pushText(composed);
    if (!query) {
      return;
    }

    const items = Array.from(container.querySelectorAll<HTMLElement>('.prompt-item'));
    if (items.length === 0) {
      return;
    }
    const active = document.activeElement as HTMLElement | null;
    const currentItem = active?.closest?.('.prompt-item') as HTMLElement | null;
    const currentIndex = currentItem ? items.indexOf(currentItem) : -1;

    for (let offset = 1; offset <= items.length; offset++) {
      const index = (currentIndex + offset + items.length) % items.length;
      const candidate = items[index];
      if (!candidate) continue;
      const label =
        (candidate.dataset.navLabel || '').trim() ||
        candidate.querySelector('h4')?.textContent?.trim() ||
        '';
      if (!label.toLocaleLowerCase().startsWith(query)) {
        continue;
      }
      const checkbox = candidate.querySelector<HTMLInputElement>('input.prompt-checkbox');
      if (checkbox) {
        checkbox.focus();
        announceKeyboardNavigation(t('accessibility.navigateTo', { item: label }));
      }
      return;
    }
  });
}

export function getListItems(list: HTMLElement): HTMLLIElement[] {
  return Array.from(list.querySelectorAll<HTMLLIElement>('li'));
}

export function syncRovingTabindexForList(list: HTMLElement | null): void {
  if (!list) return;

  const items = getListItems(list);
  if (items.length === 0) return;

  const activeItem = list.querySelector<HTMLLIElement>('li.active');
  const tabbableItem = activeItem ?? items[0];

  items.forEach((item) => {
    // Use role="option" for listbox items (set in HTML)
    // Update aria-selected based on active state
    const isActive = item === activeItem || item === tabbableItem;
    item.setAttribute('aria-selected', isActive ? 'true' : 'false');
    item.tabIndex = item === tabbableItem ? 0 : -1;
  });
}

export function syncFilterListsRovingTabindex(): void {
  FILTER_LIST_IDS.forEach((id) => {
    syncRovingTabindexForList(document.getElementById(id));
  });
}

function findNextItemByCharacter(
  items: HTMLLIElement[],
  currentIndex: number,
  key: string
): HTMLLIElement | null {
  const normalizedKey = key.trim().toLocaleLowerCase();
  if (!normalizedKey) {
    return null;
  }

  for (let offset = 1; offset <= items.length; offset += 1) {
    const index = (currentIndex + offset) % items.length;
    const candidate = items[index];
    if (!candidate) {
      continue;
    }
    const text = candidate?.textContent?.trim().toLocaleLowerCase() ?? '';
    if (text.startsWith(normalizedKey)) {
      return candidate;
    }
  }

  return null;
}

function setupFilterListKeyboardNavigation(list: HTMLElement): void {
  const typeahead = createTypeahead();

  list.addEventListener('click', (event) => {
    const target = event.target as HTMLElement | null;
    const item = target?.closest('li');
    if (!item || !list.contains(item)) {
      return;
    }
    syncRovingTabindexForList(list);
    item.tabIndex = 0;
    item.focus();
  });

  list.addEventListener('keydown', (event) => {
    if ((event as KeyboardEvent).isComposing || event.key === 'Process') {
      return;
    }
    const target = event.target as HTMLElement | null;
    const currentItem = target?.closest('li');
    if (!currentItem || !list.contains(currentItem)) {
      return;
    }

    const items = getListItems(list);
    if (items.length === 0) {
      return;
    }

    const currentIndex = items.indexOf(currentItem);
    if (currentIndex < 0) {
      return;
    }

    const focusItem = (item: HTMLLIElement): void => {
      items.forEach((listItem) => {
        listItem.tabIndex = listItem === item ? 0 : -1;
      });
      item.focus();
    };

    switch (event.key) {
      case 'ArrowDown':
      case 'ArrowRight': {
        event.preventDefault();
        const nextItem = items[(currentIndex + 1) % items.length];
        if (nextItem) focusItem(nextItem);
        return;
      }
      case 'ArrowUp':
      case 'ArrowLeft': {
        event.preventDefault();
        const previousItem = items[(currentIndex - 1 + items.length) % items.length];
        if (previousItem) focusItem(previousItem);
        return;
      }
      case 'Home': {
        event.preventDefault();
        const firstItem = items[0];
        if (firstItem) focusItem(firstItem);
        return;
      }
      case 'End': {
        event.preventDefault();
        const lastItem = items[items.length - 1];
        if (lastItem) focusItem(lastItem);
        return;
      }
      case 'Enter':
      case ' ': {
        event.preventDefault();
        currentItem.click();
        return;
      }
      default:
        break;
    }

    const isCharacterNavigation =
      event.key.length === 1 && !event.metaKey && !event.ctrlKey && !event.altKey;
    if (!isCharacterNavigation) {
      return;
    }

    const query = typeahead.pushKey(event.key);
    const matchedItem = findNextItemByCharacter(items, currentIndex, query);
    if (!matchedItem) {
      return;
    }

    event.preventDefault();
    focusItem(matchedItem);
    const matchedText = matchedItem.textContent?.trim() ?? '';
    announceKeyboardNavigation(t('accessibility.navigateTo', { item: matchedText }));
  });

  list.addEventListener('compositionend', (event) => {
    const composed = (event as CompositionEvent).data ?? '';
    const target = event.target as HTMLElement | null;
    const currentItem = target?.closest('li');
    if (!currentItem || !list.contains(currentItem)) {
      return;
    }
    const items = getListItems(list);
    if (items.length === 0) {
      return;
    }
    const currentIndex = items.indexOf(currentItem);
    if (currentIndex < 0) {
      return;
    }

    const query = typeahead.pushText(composed);
    const matchedItem = findNextItemByCharacter(items, currentIndex, query);
    if (!matchedItem) {
      return;
    }

    items.forEach((listItem) => {
      listItem.tabIndex = listItem === matchedItem ? 0 : -1;
    });
    matchedItem.focus();
    const matchedText = matchedItem.textContent?.trim() ?? '';
    announceKeyboardNavigation(t('accessibility.navigateTo', { item: matchedText }));
  });
}

export function initializeFilterListKeyboardNavigation(): void {
  FILTER_LIST_IDS.forEach((id) => {
    const list = document.getElementById(id);
    if (list) {
      setupFilterListKeyboardNavigation(list);
    }
  });
  syncFilterListsRovingTabindex();
}

let versionListKeyboardNavInitialized = false;

export function syncVersionListRovingTabindex(versionList: HTMLElement): void {
  const items = Array.from(versionList.querySelectorAll<HTMLElement>('.version-item'));
  if (items.length === 0) {
    return;
  }

  const selectedItem = versionList.querySelector<HTMLElement>('.version-item.selected');
  const tabbableItem = selectedItem ?? items[0];

  items.forEach((item) => {
    item.tabIndex = item === tabbableItem ? 0 : -1;
  });
}

function findNextVersionItemByCharacter(
  items: HTMLElement[],
  currentIndex: number,
  key: string
): HTMLElement | null {
  const normalizedKey = key.trim().toLocaleLowerCase();
  if (!normalizedKey) {
    return null;
  }

  for (let offset = 1; offset <= items.length; offset++) {
    const index = (currentIndex + offset) % items.length;
    const candidate = items[index];
    if (!candidate) {
      continue;
    }
    const text = (candidate.dataset.navLabel ?? '').trim().toLocaleLowerCase();
    if (text.startsWith(normalizedKey)) {
      return candidate;
    }
  }

  return null;
}

export function initializeVersionListKeyboardNavigation(
  versionList: HTMLElement,
  toggleVersionSelection: (versionId: string, element: HTMLElement | null) => void
): void {
  syncVersionListRovingTabindex(versionList);

  if (versionListKeyboardNavInitialized) {
    return;
  }
  versionListKeyboardNavInitialized = true;

  const typeahead = createTypeahead();

  versionList.addEventListener('click', (event) => {
    const target = event.target as HTMLElement | null;
    const item = target?.closest<HTMLElement>('.version-item');
    if (!item || !versionList.contains(item)) {
      return;
    }
    syncVersionListRovingTabindex(versionList);
    item.tabIndex = 0;
    item.focus();
  });

  versionList.addEventListener('keydown', (event) => {
    if ((event as KeyboardEvent).isComposing || event.key === 'Process') {
      return;
    }
    const target = event.target as HTMLElement | null;
    if (!target || !target.classList.contains('version-item')) {
      return;
    }

    const items = Array.from(versionList.querySelectorAll<HTMLElement>('.version-item'));
    if (items.length === 0) {
      return;
    }

    const currentIndex = items.indexOf(target);
    if (currentIndex < 0) {
      return;
    }

    const focusItem = (item: HTMLElement): void => {
      items.forEach((listItem) => {
        listItem.tabIndex = listItem === item ? 0 : -1;
      });
      item.focus();
    };

    switch (event.key) {
      case 'ArrowDown': {
        event.preventDefault();
        const nextItem = items[(currentIndex + 1) % items.length];
        if (nextItem) focusItem(nextItem);
        return;
      }
      case 'ArrowUp': {
        event.preventDefault();
        const previousItem = items[(currentIndex - 1 + items.length) % items.length];
        if (previousItem) focusItem(previousItem);
        return;
      }
      case 'Home': {
        event.preventDefault();
        const firstItem = items[0];
        if (firstItem) focusItem(firstItem);
        return;
      }
      case 'End': {
        event.preventDefault();
        const lastItem = items[items.length - 1];
        if (lastItem) focusItem(lastItem);
        return;
      }
      case 'Enter':
      case ' ': {
        event.preventDefault();
        const versionId = target.dataset.versionId;
        if (versionId) {
          toggleVersionSelection(versionId, target);
        }
        return;
      }
      default:
        break;
    }

    const isCharacterNavigation =
      event.key.length === 1 && !event.metaKey && !event.ctrlKey && !event.altKey;
    if (!isCharacterNavigation) {
      return;
    }

    const query = typeahead.pushKey(event.key);
    const matchedItem = findNextVersionItemByCharacter(items, currentIndex, query);
    if (!matchedItem) {
      return;
    }

    event.preventDefault();
    focusItem(matchedItem);
    const matchedText = matchedItem.dataset.navLabel ?? matchedItem.textContent?.trim() ?? '';
    announceKeyboardNavigation(t('accessibility.navigateTo', { item: matchedText }));
  });

  versionList.addEventListener('compositionend', (event) => {
    const composed = (event as CompositionEvent).data ?? '';
    const active = document.activeElement as HTMLElement | null;
    const currentItem = active?.closest?.('.version-item') as HTMLElement | null;
    if (!currentItem || !versionList.contains(currentItem)) {
      return;
    }

    const items = Array.from(versionList.querySelectorAll<HTMLElement>('.version-item'));
    if (items.length === 0) {
      return;
    }
    const currentIndex = items.indexOf(currentItem);
    if (currentIndex < 0) {
      return;
    }

    const query = typeahead.pushText(composed);
    const matchedItem = findNextVersionItemByCharacter(items, currentIndex, query);
    if (!matchedItem) {
      return;
    }

    items.forEach((listItem) => {
      listItem.tabIndex = listItem === matchedItem ? 0 : -1;
    });
    matchedItem.focus();
    const matchedText = matchedItem.dataset.navLabel ?? matchedItem.textContent?.trim() ?? '';
    announceKeyboardNavigation(t('accessibility.navigateTo', { item: matchedText }));
  });
}

// Tooltips (Phase 6 & 8)
export function addTooltips(): void {
  const tooltips = {
    '.history-btn': t('version.history') + ' - ' + t('version.searchPlaceholder'),
    '.copy-btn': t('actions.copy'),
    '.edit-btn': t('actions.edit'),
    '.delete-btn': t('actions.delete'),
    '.favorite-btn': t('actions.favorite'),
  };

  Object.entries(tooltips).forEach(([selector, title]) => {
    document.querySelectorAll(selector).forEach((element) => {
      const htmlElement = element as HTMLElement;
      const derivedTitle =
        selector === '.favorite-btn' ? htmlElement.getAttribute('aria-label') || title : title;
      htmlElement.title = derivedTitle;
      htmlElement.setAttribute('data-tooltip', derivedTitle);
    });
  });
}
