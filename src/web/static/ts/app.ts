/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * PromptVault main app logic (TypeScript).
 */

import '../css/tailwind-globals.css';
import '@/form-validation';
import type { PromptResponse, PromptListResponse } from '@/types';
import type { TranslationKey } from '@/types/i18n';
import { initI18n, t, tUnsafe, updateStaticTranslations } from '@/utils/i18n';
import { apiFetch, apiGet, apiPostForm, APIRequestError } from '@/utils/api';
import { setupScrollIndicators } from '@/utils/dom';
import { showNotification } from '@/utils/notifications';
import { createTypeahead } from '@/utils/typeahead';
import { createModal } from '@components';
import { announce } from '@/utils/a11y';
import { confirmAsync } from '@/utils/dialogs';
import { focusFirstElement, announceToScreenReader } from '@/utils/focus-management';
import {
  createInitialPaginationState,
  mergePrompts,
  canLoadMore,
  type PaginationState,
  type PageSize,
} from '@/utils/pagination';
import { closeMobileDrawer, initKeyboardSafeScroll, initMobileNav } from '@/mobile-nav';
import { closeSearchOverlay, initSearchOverlay, isSearchOverlayOpen } from '@/search-overlay';
import { clearOfflineDataOnLogout, initOfflineIndicator, registerServiceWorker } from '@/sw-register';
import { syncOfflineQueue } from '@/offline-sync';
import { addQueueEntry } from '@/utils/offline-queue';
import { attachPullToRefresh, attachSwipeReveal } from '@/gestures';

interface TagInfo {
  name: string;
  count: number;
  color?: string | null;
}

interface CategoryItem {
  name: string;
  color?: string | null;
}

interface TagItem {
  name: string;
  color?: string | null;
  usage_count?: number | null;
  count?: number | null;
}

interface VersionSummary {
  version_id: string;
  version_number: number;
  timestamp: string;
  author: string;
  message: string;
  parents: string[];
  semantic_version: string | null;
}

interface VersionHistoryResponse {
  versions: VersionSummary[];
}

interface DiffOperation {
  op: 'equal' | 'delete' | 'insert';
  text: string;
}

interface FieldChange {
  old: string | string[] | null;
  new: string | string[] | null;
  diff?: DiffOperation[];
}

interface VersionDiffResponse {
  v1_id: string;
  v2_id: string;
  changes: Record<string, FieldChange>;
}

interface VersionCacheEntry {
  timestamp: number;
  data: VersionHistoryResponse;
}

interface DiffCacheEntry {
  timestamp: number;
  data: VersionDiffResponse;
}

interface VersionSortItem {
  id: string;
  number: number;
}

interface BulkDeleteResponse {
  success: boolean;
  deleted_count: number;
  failed_count: number;
  failed_ids: number[];
  detail?: string;
}

type PromptId = string;

let promptCache: Record<string, PromptResponse> = {};
let lastSelectedPromptId: number | null = null; // Track the last selected prompt for keyboard shortcuts
const selectedPromptIds: Set<number> = new Set(); // Track selected prompts for bulk operations
let tagColorMap: Record<string, string> = {};
let categoryColorMap: Record<string, string> = {};
const colorTextCache = new Map<string, string>();
let selectedTags: string[] = [];
let keyboardHelpModal: {
  element: HTMLDivElement;
  open: () => void;
  close: () => void;
} | null = null;

const HIDDEN_CLASS = 'hidden';
const ERROR_VISIBLE_CLASS = 'validation-error-visible';
const APP_COMPONENT = 'app';
const MAX_TAGS = 15;
const promptLiveValidationState = new Map<string, boolean>();
const FILTER_LIST_IDS = [
  'categories-list',
  'tags-list',
  'categories-list-mobile',
  'tags-list-mobile',
] as const;

// Focus management for modals
let versionHistoryModalTrigger: HTMLElement | null = null;
let diffModalTrigger: HTMLElement | null = null;
let revertConfirmationModalTrigger: HTMLElement | null = null;
let bulkDeleteModalTrigger: HTMLElement | null = null;
let bulkTagModalTrigger: HTMLElement | null = null;

function reportAppIssue(
  action: string,
  error: unknown,
  metadata: Record<string, unknown> = {},
  severity: 'error' | 'warning' = 'error'
): void {
  const logger = window.FrontendLogger;
  if (logger && typeof logger.reportError === 'function') {
    logger.reportError(APP_COMPONENT, action, error, metadata, severity);
  }
  const message = `[PromptVault][app] ${action}`;
  if (severity === 'warning') {
    console.warn(message, error, metadata);
  } else {
    console.error(message, error, metadata);
  }
}

function showElement(element: HTMLElement | null): void {
  if (element) {
    element.classList.remove(HIDDEN_CLASS);
  }
}

function hideElement(element: HTMLElement | null): void {
  if (element) {
    element.classList.add(HIDDEN_CLASS);
  }
}

function announceKeyboardNavigation(message: string): void {
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

let promptsListKeyboardNavInitialized = false;

function isTextEditingTarget(target: EventTarget | null): boolean {
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

function initializePromptsListKeyboardNavigation(container: HTMLElement): void {
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

function getListItems(list: HTMLElement): HTMLLIElement[] {
  return Array.from(list.querySelectorAll<HTMLLIElement>('li'));
}

function syncRovingTabindexForList(list: HTMLElement | null): void {
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

function syncFilterListsRovingTabindex(): void {
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

function initializeFilterListKeyboardNavigation(): void {
  FILTER_LIST_IDS.forEach((id) => {
    const list = document.getElementById(id);
    if (list) {
      setupFilterListKeyboardNavigation(list);
    }
  });
  syncFilterListsRovingTabindex();
}

function resolveCssColor(color?: string | null): string | null {
  if (!color) {
    return null;
  }
  const trimmed = color.trim();
  if (!trimmed) {
    return null;
  }
  if (trimmed.startsWith('#')) {
    return trimmed;
  }
  return `var(--color-${trimmed}, ${trimmed})`;
}

/**
 * Convert hex color to RGB
 */
function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? {
        r: parseInt(result[1]!, 16),
        g: parseInt(result[2]!, 16),
        b: parseInt(result[3]!, 16),
      }
    : null;
}

/**
 * Convert RGB to HSL
 */
function rgbToHsl(r: number, g: number, b: number): { h: number; s: number; l: number } {
  r /= 255;
  g /= 255;
  b /= 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h = 0;
  let s = 0;
  const l = (max + min) / 2;

  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r:
        h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
        break;
      case g:
        h = ((b - r) / d + 2) / 6;
        break;
      case b:
        h = ((r - g) / d + 4) / 6;
        break;
    }
  }

  return { h, s, l };
}

/**
 * Convert HSL to RGB
 */
function hslToRgb(h: number, s: number, l: number): { r: number; g: number; b: number } {
  let r, g, b;

  if (s === 0) {
    r = g = b = l;
  } else {
    const hue2rgb = (p: number, q: number, t: number) => {
      if (t < 0) t += 1;
      if (t > 1) t -= 1;
      if (t < 1 / 6) return p + (q - p) * 6 * t;
      if (t < 1 / 2) return q;
      if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
      return p;
    };

    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    r = hue2rgb(p, q, h + 1 / 3);
    g = hue2rgb(p, q, h);
    b = hue2rgb(p, q, h - 1 / 3);
  }

  return {
    r: Math.round(r * 255),
    g: Math.round(g * 255),
    b: Math.round(b * 255),
  };
}

/**
 * Convert RGB to hex
 */
function rgbToHex(r: number, g: number, b: number): string {
  return (
    '#' +
    [r, g, b]
      .map((x) => {
        const hex = x.toString(16);
        return hex.length === 1 ? '0' + hex : hex;
      })
      .join('')
  );
}

/**
 * Get soft/muted color scheme for tag pills (Option B design)
 * Converts any color (hex or named) to a light background + colored border + darker text
 */
function getSoftMutedColorScheme(colorInput: string | undefined | null): {
  background: string;
  text: string;
  border: string;
} {
  // Resolve color to hex
  const borderColor = resolveCssColor(colorInput);
  if (!borderColor) {
    // Default fallback if no color provided
    return {
      background: '#f3f4f6',
      text: '#374151',
      border: '#d1d5db',
    };
  }

  // Convert to RGB
  const rgb = hexToRgb(borderColor);
  if (!rgb) {
    // Fallback if color parsing fails
    return {
      background: '#f3f4f6',
      text: '#374151',
      border: '#d1d5db',
    };
  }

  // Convert RGB to HSL
  const hsl = rgbToHsl(rgb.r, rgb.g, rgb.b);

  // Create soft/muted version:
  // - Reduce saturation to 60% (less aggressive, more recognizable)
  // - Increase lightness to 78% (light but more visible than 90%)
  const softHsl = {
    h: hsl.h,
    s: 0.6, // 60% saturation (more visible, less aggressive)
    l: 0.78, // 78% lightness (soft but not too pale)
  };

  // Create border color version:
  // - Keep hue
  // - Increase saturation to 70% (more vibrant)
  // - Set lightness to 52% (more visible)
  const borderHsl = {
    h: hsl.h,
    s: 0.7, // 70% saturation (more vibrant)
    l: 0.52, // 52% lightness (medium tone, more visible)
  };

  // Convert back to RGB and then to hex
  const softRgb = hslToRgb(softHsl.h, softHsl.s, softHsl.l);
  const borderRgb = hslToRgb(borderHsl.h, borderHsl.s, borderHsl.l);

  const background = rgbToHex(softRgb.r, softRgb.g, softRgb.b);
  const borderColorHex = rgbToHex(borderRgb.r, borderRgb.g, borderRgb.b);

  // Determine text color based on background luminance
  // Use darker text for light backgrounds
  const textColor = '#374151'; // dark gray (works well on light backgrounds)

  return {
    background,
    text: textColor,
    border: borderColorHex,
  };
}

function getReadableTextColor(background: string): string {
  const cached = colorTextCache.get(background);
  if (cached) {
    return cached;
  }
  const swatch = document.createElement('span');
  swatch.style.backgroundColor = background;
  swatch.style.display = 'none';
  document.body.appendChild(swatch);
  const computed = window.getComputedStyle(swatch).backgroundColor;
  swatch.remove();

  const match = computed.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
  if (!match) {
    colorTextCache.set(background, '#374151');
    return '#374151';
  }
  const r = Number(match[1]) / 255;
  const g = Number(match[2]) / 255;
  const b = Number(match[3]) / 255;
  const luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  const textColor = luminance > 0.6 ? '#1f2937' : '#f9fafb';
  colorTextCache.set(background, textColor);
  return textColor;
}

function buildPillStyleFilled(color?: string | null): string {
  const background = resolveCssColor(color);
  if (!background) {
    return '';
  }
  const textColor = getReadableTextColor(background);
  return ` style="background-color: ${background}; color: ${textColor};"`;
}

function buildPillStyleOutline(color?: string | null): string {
  if (!color) {
    return '';
  }
  // Use soft/muted color scheme (Option B)
  const colorScheme = getSoftMutedColorScheme(color);
  return ` style="background-color: ${colorScheme.background}; color: ${colorScheme.text}; border-color: ${colorScheme.border};"`;
}

function applyPromptColorStyles(): void {
  document.querySelectorAll<HTMLElement>('[data-category-pill]').forEach((pill) => {
    const category = pill.dataset.categoryName || '';
    const color = categoryColorMap[category];
    if (!color) {
      return;
    }
    const background = resolveCssColor(color);
    if (!background) {
      return;
    }
    pill.style.backgroundColor = background;
    pill.style.color = getReadableTextColor(background);
  });

  document.querySelectorAll<HTMLElement>('[data-tag-pill]').forEach((pill) => {
    const tagName = pill.dataset.tagName || '';
    const color = tagColorMap[tagName];
    if (!color) {
      return;
    }
    // Use soft/muted color scheme (Option B design)
    const colorScheme = getSoftMutedColorScheme(color);
    pill.style.backgroundColor = colorScheme.background;
    pill.style.color = colorScheme.text;
    pill.style.borderColor = colorScheme.border;
  });
}

function normalizeTagItems(items: TagItem[]): TagInfo[] {
  return items.map((item) => ({
    name: item.name,
    count: item.count ?? item.usage_count ?? 0,
    color: item.color ?? null,
  }));
}

function setTagColorMap(tags: TagInfo[]): void {
  tagColorMap = {};
  tags.forEach((tag) => {
    if (tag.color) {
      tagColorMap[tag.name] = tag.color;
    }
  });
}

function setCategoryColorMap(items: CategoryItem[]): void {
  categoryColorMap = {};
  items.forEach((item) => {
    if (item.color) {
      categoryColorMap[item.name] = item.color;
    }
  });
}

function clearPromptFormErrors(): void {
  const errorFields = [
    'prompt-title-error',
    'prompt-content-error',
    'prompt-tags-error',
    'commit-message-error',
  ];
  errorFields.forEach((id) => {
    const el = document.getElementById(id);
    if (el) {
      el.textContent = '';
      delete el.dataset.errorKey;
      el.classList.remove(ERROR_VISIBLE_CLASS);
    }
  });
  const inputs = [
    'prompt-title',
    'prompt-content',
    'prompt-tags',
    'prompt-tags-input',
    'commit-message',
  ];
  inputs.forEach((id) => {
    const field = document.getElementById(id);
    if (field) {
      field.classList.remove('field-error');
      field.removeAttribute('aria-invalid');
    }
  });
  const tagChipInput = document.getElementById('tag-chip-input');
  if (tagChipInput) {
    tagChipInput.classList.remove('field-error');
    tagChipInput.removeAttribute('aria-invalid');
  }
  const banner = document.getElementById('validation-error-banner');
  if (banner) {
    banner.textContent = '';
    banner.style.display = 'none';
  }
}

function showPromptFieldError(
  fieldId: string,
  errorId: string,
  messageKey: TranslationKey,
  shouldFocus: boolean = true,
  shouldAnnounce: boolean = false
): void {
  const errorEl = document.getElementById(errorId);
  const field = document.getElementById(fieldId);
  const message = t(messageKey);
  if (errorEl) {
    errorEl.textContent = message;
    errorEl.dataset.errorKey = messageKey;
    errorEl.classList.add(ERROR_VISIBLE_CLASS);
  }

  const mergeDescribedBy = (el: HTMLElement | null, ids: string[]) => {
    if (!el) return;
    const existing =
      el
        .getAttribute('aria-describedby')
        ?.split(/\s+/)
        .map((s) => s.trim())
        .filter(Boolean) ?? [];
    const next = Array.from(new Set([...existing, ...ids.filter(Boolean)]));
    if (next.length) el.setAttribute('aria-describedby', next.join(' '));
  };

  const hadError = promptLiveValidationState.get(fieldId) === true;
  const maybeAnnounce = () => {
    if (!shouldAnnounce) return;
    if (!hadError) {
      announce(message, { id: 'validation-announcer', politeness: 'polite' });
    }
    promptLiveValidationState.set(fieldId, true);
  };

  // Special-case tags: the "real" form field is hidden, but the focusable control is #prompt-tags-input.
  if (fieldId === 'prompt-tags') {
    const hidden = field as HTMLInputElement | null;
    const tagInput = getTagInputElement();
    const tagChipInput = document.getElementById('tag-chip-input');

    hidden?.setAttribute('aria-invalid', 'true');

    if (tagInput) {
      tagInput.classList.add('field-error');
      tagInput.setAttribute('aria-invalid', 'true');
      mergeDescribedBy(tagInput, [errorId]);
      if (shouldFocus) {
        tagInput.focus();
      }
    }

    if (tagChipInput) {
      tagChipInput.classList.add('field-error');
      tagChipInput.setAttribute('aria-invalid', 'true');
    }

    maybeAnnounce();
    return;
  }

  if (field) {
    field.classList.add('field-error');
    field.setAttribute('aria-invalid', 'true');
    mergeDescribedBy(field, [errorId]);
    if (shouldFocus) {
      field.focus();
    }
    maybeAnnounce();
  }
}

type PromptFieldError = {
  fieldId: string;
  errorId: string;
  messageKey: TranslationKey;
};

function showPromptErrorSummary(errors: PromptFieldError[]): void {
  const banner = document.getElementById('validation-error-banner');
  if (!banner) {
    return;
  }
  if (errors.length === 0) {
    banner.textContent = '';
    banner.style.display = 'none';
    return;
  }

  const itemsHtml = errors
    .map((err) => {
      const message = t(err.messageKey);
      return `<li><a href="#${escapeHtml(err.fieldId)}" class="underline">${escapeHtml(message)}</a></li>`;
    })
    .join('');

  banner.innerHTML = `
    <p class="font-semibold">${escapeHtml(t('validation.errorSummaryHeader'))}</p>
    <ul class="list-disc list-inside mt-2 space-y-1">${itemsHtml}</ul>
  `;
  banner.style.display = 'block';

  banner.querySelectorAll<HTMLAnchorElement>('a[href^="#"]').forEach((a) => {
    a.addEventListener('click', (event) => {
      event.preventDefault();
      const targetId = a.getAttribute('href')?.slice(1);
      if (!targetId) {
        return;
      }
      const field = document.getElementById(targetId) as HTMLElement | null;
      field?.focus();
    });
  });

  // Per plan T-ACC023: focus the first invalid field after rendering the summary.
  const firstFieldId = errors[0]?.fieldId;
  const firstField = firstFieldId
    ? (document.getElementById(firstFieldId) as HTMLElement | null)
    : null;
  if (firstField) {
    firstField.focus();
  } else {
    banner.focus();
  }
}

function clearPromptFieldError(
  fieldId: string,
  errorId: string,
  shouldAnnounce: boolean = false
): void {
  const errorEl = document.getElementById(errorId);
  if (errorEl) {
    errorEl.textContent = '';
    delete errorEl.dataset.errorKey;
    errorEl.classList.remove(ERROR_VISIBLE_CLASS);
  }
  const field = document.getElementById(fieldId);
  if (field) {
    field.classList.remove('field-error');
    field.removeAttribute('aria-invalid');
  }
  if (fieldId === 'prompt-tags') {
    const tagInput = getTagInputElement();
    if (tagInput) {
      tagInput.classList.remove('field-error');
      tagInput.removeAttribute('aria-invalid');
    }
    const tagChipInput = document.getElementById('tag-chip-input');
    if (tagChipInput) {
      tagChipInput.classList.remove('field-error');
      tagChipInput.removeAttribute('aria-invalid');
    }
  }

  const hadError = promptLiveValidationState.get(fieldId) === true;
  promptLiveValidationState.set(fieldId, false);
  if (shouldAnnounce && hadError) {
    announce(t('validation.fieldValid') || 'Field is valid.', {
      id: 'validation-announcer',
      politeness: 'polite',
    });
  }
}

function toggleElement(element: HTMLElement | null, shouldShow: boolean): void {
  if (element) {
    element.classList.toggle(HIDDEN_CLASS, !shouldShow);
  }
}

async function initializeApp(): Promise<void> {
  // Event listeners (safe to setup before auth)
  setupEventListeners();
  initializeBulkActions();

  // CRITICAL: Check authentication BEFORE loading any data
  // This prevents content flash before redirect
  await checkAdminAccess();

  // Only load data if authentication succeeded
  // (if auth failed, checkAdminAccess redirects to login)
  void loadPrompts();
  void loadCategories();
  void loadTags();
}

function hideAuthOnlyElements(): void {
  // Hide elements that only make sense when authentication is enabled.
  const idsToHide = ['profile-btn', 'logout-btn', 'mobile-drawer-account-section'];
  idsToHide.forEach((id) => {
    const el = document.getElementById(id);
    if (el) {
      el.style.display = 'none';
    }
  });
  // Hide profile navigation links (desktop button + mobile dropdown entries).
  document.querySelectorAll<HTMLElement>('[onclick*="/auth/profile"]').forEach((el) => {
    el.style.display = 'none';
  });
}

async function checkAdminAccess(): Promise<void> {
  // Anonymous mode (AUTH_ENABLED=false): show the app immediately without an
  // auth check and hide auth-only UI elements (profile, logout, etc.).
  if (window.__AUTH_ENABLED__ === false) {
    const loadingOverlay = document.getElementById('auth-loading-overlay');
    const appDiv = document.querySelector('.app') as HTMLElement | null;
    if (loadingOverlay) loadingOverlay.style.display = 'none';
    if (appDiv) appDiv.style.display = 'block';
    hideAuthOnlyElements();
    return;
  }

  try {
    const data = await apiGet<{ role?: string }>('/api/auth/me');

    // Authentication successful - show the app
    const loadingOverlay = document.getElementById('auth-loading-overlay');
    const appDiv = document.querySelector('.app') as HTMLElement | null;
    if (loadingOverlay) loadingOverlay.style.display = 'none';
    if (appDiv) appDiv.style.display = 'block';

    if (data.role === 'admin') {
      const adminBtn = document.getElementById('admin-btn');
      const adminBtnMobile = document.getElementById('admin-btn-mobile');
      if (adminBtn) {
        adminBtn.style.display = '';
      }
      if (adminBtnMobile) {
        adminBtnMobile.style.display = '';
      }
    }
  } catch (error) {
    reportAppIssue('checkAdminAccess', error);

    // Offline (network failure, not a real auth rejection): show the cached
    // app shell instead of redirecting to login, so previously-viewed content
    // remains accessible per FR-009. apiFetch already handles a genuine 401
    // (server reachable, session invalid) with its own redirect.
    if (!navigator.onLine || !(error instanceof APIRequestError)) {
      const loadingOverlay = document.getElementById('auth-loading-overlay');
      const appDiv = document.querySelector('.app') as HTMLElement | null;
      if (loadingOverlay) loadingOverlay.style.display = 'none';
      if (appDiv) appDiv.style.display = 'block';
      return;
    }

    // On a genuine auth error while online, redirect to login for security.
    window.location.href = '/auth/login';
  }
}

// Global search state
let searchState: {
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
let paginationState: PaginationState = createInitialPaginationState({
  searchTerm: '',
  category: 'all',
  tag: 'all',
  favorites: false,
  caseSensitive: false,
});

function currentFilters() {
  return {
    searchTerm: searchState.searchTerm,
    category: searchState.category,
    tag: searchState.tag,
    favorites: searchState.favorites,
    caseSensitive: searchState.caseSensitive,
  };
}

function updateLoadMoreControl(): void {
  const loadMoreBtn = document.getElementById('load-more-btn') as HTMLButtonElement | null;
  const loadMoreContainer = document.getElementById('load-more-container');
  if (!loadMoreBtn || !loadMoreContainer) {
    return;
  }
  toggleElement(loadMoreContainer, paginationState.hasNext);
  loadMoreBtn.disabled = paginationState.isLoadingMore;
  loadMoreBtn.textContent = paginationState.isLoadingMore ? 'Loading...' : 'Load More';
}

function setupEventListeners(): void {
  // Unified mobile navigation drawer (hamburger triggers, close button,
  // backdrop, outside-tap/Escape close, focus trap) — see mobile-nav.ts
  initMobileNav();

  // Full-screen mobile search overlay (FR-016) — see search-overlay.ts
  initSearchOverlay();

  // Keep the prompt editor's fields visible above the on-screen keyboard (FR-005)
  initKeyboardSafeScroll(['#prompt-title', '#prompt-content']);

  // Offline resilience: Service Worker caching, persistent offline indicator,
  // and automatic queue sync on reconnect (FR-009, FR-010, FR-011)
  registerServiceWorker();
  initOfflineIndicator(() => {
    void syncOfflineQueue();
  });
  if (navigator.onLine) {
    void syncOfflineQueue();
  }

  // Pull-to-refresh on the prompt list (FR-008), with an accessible refresh
  // button as the always-visible equivalent control.
  const promptsList = document.getElementById('prompts-list');
  const pullRefreshIndicator = document.getElementById('pull-refresh-indicator');
  const refreshPromptsBtn = document.getElementById('refresh-prompts-btn');

  const showRefreshLoading = (): void => {
    pullRefreshIndicator?.classList.remove('hidden');
    pullRefreshIndicator?.classList.add('flex');
  };
  const hideRefreshLoading = (): void => {
    pullRefreshIndicator?.classList.add('hidden');
    pullRefreshIndicator?.classList.remove('flex');
  };
  const refreshPrompts = async (): Promise<void> => {
    if (isAnyFilterActive()) {
      await performSearch();
    } else {
      await loadPrompts();
    }
  };

  if (promptsList) {
    attachPullToRefresh(promptsList, {
      onRefresh: refreshPrompts,
      showLoading: showRefreshLoading,
      hideLoading: hideRefreshLoading,
    });
  }

  refreshPromptsBtn?.addEventListener('click', () => {
    showRefreshLoading();
    void refreshPrompts().finally(hideRefreshLoading);
  });

  // New prompt button
  const newPromptBtn = document.getElementById('new-prompt-btn');
  newPromptBtn?.addEventListener('click', showNewPromptForm);

  // New prompt button (mobile)
  const newPromptBtnMobile = document.getElementById('new-prompt-btn-mobile');
  newPromptBtnMobile?.addEventListener('click', () => {
    showNewPromptForm();
    closeMobileDrawer();
  });

  // New prompt floating action button (mobile, FR-006)
  const newPromptFab = document.getElementById('new-prompt-fab');
  newPromptFab?.addEventListener('click', showNewPromptForm);

  // Import/Export button (navigates to import/export page)
  const importExportBtn = document.getElementById('import-export-btn');
  importExportBtn?.addEventListener('click', function () {
    window.location.href = '/import-export';
  });

  // Logout button
  const logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      void logout();
    });
  }

  // Logout button (mobile)
  const logoutBtnMobile = document.getElementById('logout-btn-mobile');
  if (logoutBtnMobile) {
    logoutBtnMobile.addEventListener('click', () => {
      void logout();
    });
  }

  // Form handling
  const promptForm = document.getElementById('prompt-form');
  promptForm?.addEventListener('submit', (event) => {
    void handlePromptSubmit(event as SubmitEvent);
  });
  const cancelBtn = document.getElementById('cancel-btn-edit-modal');
  cancelBtn?.addEventListener('click', () => history.back());
  const suggestTagsBtn = document.getElementById('suggest-tags-btn');
  suggestTagsBtn?.addEventListener('click', () => {
    void handleSuggestTags();
  });

  // Live validation (T-ACC025) for the prompt editor required fields.
  const titleInput = document.getElementById('prompt-title') as HTMLInputElement | null;
  if (titleInput) {
    const validate = () => {
      if (!titleInput.value.trim()) {
        showPromptFieldError(
          'prompt-title',
          'prompt-title-error',
          'validation.titleRequired',
          false,
          true
        );
      } else {
        clearPromptFieldError('prompt-title', 'prompt-title-error', true);
      }
    };
    titleInput.addEventListener('blur', validate);
    titleInput.addEventListener('input', () => {
      if (promptLiveValidationState.get('prompt-title') === true) {
        validate();
      }
    });
  }

  const contentInput = document.getElementById('prompt-content') as HTMLTextAreaElement | null;
  if (contentInput) {
    const validate = () => {
      if (!contentInput.value.trim()) {
        showPromptFieldError(
          'prompt-content',
          'prompt-content-error',
          'validation.contentRequired',
          false,
          true
        );
      } else {
        clearPromptFieldError('prompt-content', 'prompt-content-error', true);
      }
    };
    contentInput.addEventListener('blur', validate);
    contentInput.addEventListener('input', () => {
      if (promptLiveValidationState.get('prompt-content') === true) {
        validate();
      }
    });
  }

  // Category and tag filtering (desktop and mobile)
  const categoriesList = document.getElementById('categories-list');
  categoriesList?.addEventListener('click', handleCategoryFilter);
  const categoriesListMobile = document.getElementById('categories-list-mobile');
  categoriesListMobile?.addEventListener('click', (event) => {
    handleCategoryFilter(event);
    closeMobileDrawer();
  });

  const tagsList = document.getElementById('tags-list');
  tagsList?.addEventListener('click', handleTagFilter);
  const tagsListMobile = document.getElementById('tags-list-mobile');
  tagsListMobile?.addEventListener('click', (event) => {
    handleTagFilter(event);
    closeMobileDrawer();
  });
  initializeFilterListKeyboardNavigation();

  const favoritesFilter = document.getElementById('favorites-filter');
  favoritesFilter?.addEventListener('change', handleFavoritesFilter);
  const favoritesFilterMobile = document.getElementById('favorites-filter-mobile');
  favoritesFilterMobile?.addEventListener('change', handleFavoritesFilter);

  // Modal close
  const closeBtn = document.querySelector('.close');
  closeBtn?.addEventListener('click', hideModal);
  window.addEventListener('click', function (event) {
    const modal = document.getElementById('prompt-modal');
    if (event.target === modal) {
      hideModal();
    }
  });

  // Version history modal close buttons
  const closeVersionHistoryBtns = document.querySelectorAll('#close-version-history-btn');
  closeVersionHistoryBtns.forEach((btn) => {
    btn.addEventListener('click', hideVersionHistoryModal);
  });

  // Back button closes modals/editor instead of leaving the app.
  // When popstate fires we've already moved back in history, so event.state is
  // the *previous* entry — not our pushed one. Check what's visible instead.
  window.addEventListener('popstate', () => {
    const versionHistoryModal = document.getElementById('version-history-modal');
    const promptEditor = document.getElementById('prompt-editor');
    if (versionHistoryModal && !versionHistoryModal.classList.contains('hidden')) {
      hideVersionHistoryModal();
    } else if (promptEditor && !promptEditor.classList.contains('hidden')) {
      hidePromptEditor();
    }
  });

  // Diff modal close
  const closeDiffBtn = document.getElementById('close-diff-btn');
  if (closeDiffBtn) {
    closeDiffBtn.addEventListener('click', hideDiffModal);
  }

  // Revert confirmation modal close
  const cancelRevertBtn = document.getElementById('cancel-revert-btn');
  if (cancelRevertBtn) {
    cancelRevertBtn.addEventListener('click', hideRevertConfirmationModal);
  }

  // Compare versions button
  const compareVersionsBtn = document.getElementById('compare-versions-btn');
  if (compareVersionsBtn) {
    compareVersionsBtn.addEventListener('click', () => {
      void showDiffModal();
    });
  }

  // Keyboard shortcuts
  document.addEventListener('keydown', handleKeyboardShortcuts);
  document.addEventListener('promptvault:open-keyboard-help', (event) => {
    const customEvent = event as CustomEvent<{ markHandled?: () => void }>;
    customEvent.detail?.markHandled?.();
    showKeyboardShortcutsHelpModal();
  });

  // Button keyboard activation (Enter and Space keys)
  // Enables keyboard accessibility for all buttons across the application
  document.addEventListener('keydown', (e) => {
    if (document.activeElement instanceof HTMLButtonElement) {
      const button = document.activeElement;
      // Enter and Space keys should activate buttons (standard keyboard behavior)
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        button.click();
      }
    }
  });

  // Add tooltips
  addTooltips();

  // Search functionality
  setupSearchEventListeners();

  // Tag autocomplete
  setupTagAutocomplete();

  // Empty state buttons
  const emptyStateNewPromptBtn = document.getElementById('empty-state-new-prompt-btn');
  emptyStateNewPromptBtn?.addEventListener('click', showNewPromptForm);

  const emptyStateClearFiltersBtn = document.getElementById('empty-state-clear-filters-btn');
  emptyStateClearFiltersBtn?.addEventListener('click', clearAllFilters);

  // Load More button (pagination)
  const loadMoreBtn = document.getElementById('load-more-btn');
  loadMoreBtn?.addEventListener('click', () => {
    void loadMorePrompts();
  });

  // Page size selector (pagination)
  const pageSizeSelect = document.getElementById('page-size-select') as HTMLSelectElement | null;
  pageSizeSelect?.addEventListener('change', (event) => {
    const target = event.target as HTMLSelectElement | null;
    const value = Number(target?.value) as PageSize;
    paginationState.pageSize = value;
    if (isAnyFilterActive()) {
      void performSearch();
    } else {
      void loadPrompts();
    }
  });

  // Setup scroll indicators for scrollable containers
  setupScrollIndicators(document.getElementById('categories-list'));
  setupScrollIndicators(document.getElementById('tags-list'));
  setupScrollIndicators(document.getElementById('categories-list-mobile'));
  setupScrollIndicators(document.getElementById('tags-list-mobile'));
  // NOTE: tag autocomplete is absolutely positioned; wrapping it for scroll fades
  // would clip the dropdown. Keep it unwrapped so suggestions remain visible.
}

async function loadPrompts(): Promise<void> {
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

async function loadMorePrompts(): Promise<void> {
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

function buildSearchUrl(page: number): string {
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

async function loadCategories(): Promise<void> {
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
    categoryColorMap = {};
    renderCategories(data.categories || []);
    applyPromptColorStyles();
  } catch (error) {
    reportAppIssue('loadCategories', error);
  }
}

async function loadTags(): Promise<void> {
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

function renderPrompts(prompts: Record<string, PromptResponse>): void {
  const container = document.getElementById('prompts-list') as HTMLElement | null;
  const searchResultsInfo = document.getElementById('search-results-info');
  const promptsEmptyState = document.getElementById('prompts-empty-state');
  const searchEmptyState = document.getElementById('search-empty-state');

  if (!container) {
    return;
  }
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

function isAnyFilterActive(): boolean {
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

function createPromptElement(id: string, prompt: PromptResponse): HTMLDivElement {
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

  // Build tags HTML
  const tagColorLookup = prompt.tag_colors ?? {};
  const tagsHTML =
    prompt.tags && prompt.tags.length > 0
      ? prompt.tags
          .map((tag) => {
            const color = tagColorLookup[tag] ?? tagColorMap[tag];
            const style = buildPillStyleOutline(color);
            return `<span class="px-2 py-1 text-xs font-medium rounded-full border" data-tag-pill="true" data-tag-name="${escapeHtml(tag)}"${style}>
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

  div.innerHTML = `
	        <div class="flex items-start justify-between mb-3">
	            <h4 id="${titleId}" class="text-prompt-title font-semibold text-gray-900 flex-1 flex items-center flex-wrap gap-1">${escapeHtml(prompt.title)}${semVerBadge}</h4>
	            <div class="flex items-center gap-1 ml-2" id="prompt-actions-${id}">
	                <button class="favorite-btn flex items-center justify-center min-w-[44px] min-h-[44px] md:min-w-0 md:min-h-0 text-xl hover:scale-110 transition-transform focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-700 rounded" data-id="${id}">
	                    ${prompt.favorite ? '★' : '☆'}
	                </button>
	            </div>
	        </div>
        <div class="flex flex-wrap gap-2 mb-3">
            <span class="px-2 py-1 text-xs font-semibold rounded-md" data-category-pill="true" data-category-name="${escapeHtml(prompt.category)}"${categoryStyle}>
              ${escapeHtml(prompt.category) || t('categories.noCategory')}
            </span>
            ${tagsHTML}
        </div>
        <p class="prompt-body-text text-prompt-body text-gray-600 mb-1 line-clamp-3">${escapeHtml(prompt.prompt)}</p>
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
    void copyPrompt(id);
  });
  if (copyBtn) {
    copyBtn.title = t('actions.copy');
  }

  const editBtn = div.querySelector('.edit-btn') as HTMLButtonElement | null;
  editBtn?.addEventListener('click', () => {
    lastSelectedPromptId = parseInt(id, 10);
    void editPrompt(id);
  });
  if (editBtn) {
    editBtn.title = t('actions.edit');
  }

  const deleteBtn = div.querySelector('.delete-btn') as HTMLButtonElement | null;
  deleteBtn?.addEventListener('click', () => {
    lastSelectedPromptId = parseInt(id, 10);
    void deletePrompt(id);
  });
  if (deleteBtn) {
    deleteBtn.title = t('actions.delete');
  }

  const favoriteBtn = div.querySelector('.favorite-btn') as HTMLButtonElement | null;
  favoriteBtn?.addEventListener('click', () => {
    lastSelectedPromptId = parseInt(id, 10);
    void toggleFavorite(id);
  });
  if (favoriteBtn) {
    setFavoriteButtonA11y(favoriteBtn, Boolean(prompt.favorite));
  }

  const historyBtn = div.querySelector('.history-btn') as HTMLButtonElement | null;
  historyBtn?.addEventListener('click', () => {
    lastSelectedPromptId = parseInt(id, 10);
    showVersionHistoryModal(parseInt(id, 10));
  });
  if (historyBtn) {
    historyBtn.title = t('version.history');
  }

  const copyWithVersionBtn = div.querySelector(
    '.copy-with-version-btn'
  ) as HTMLButtonElement | null;
  copyWithVersionBtn?.addEventListener('click', () => {
    lastSelectedPromptId = parseInt(id, 10);
    void copyPromptWithVersion(id);
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
    void editPrompt(id);
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
  attachSwipeReveal(div, {
    onSwipeLeft: () => {
      lastSelectedPromptId = parseInt(id, 10);
      void deletePrompt(id);
    },
    onSwipeRight: () => {
      lastSelectedPromptId = parseInt(id, 10);
      void editPrompt(id);
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
  list.innerHTML = '';
  if (allPromptsItem) {
    list.appendChild(allPromptsItem);
  }

  // Handle mobile list
  if (listMobile) {
    const allPromptsItemMobile = listMobile.querySelector('[data-category="all"]');
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
  list.innerHTML = '';
  if (allTagsItem) {
    list.appendChild(allTagsItem);
  }

  // Handle mobile list
  if (listMobile) {
    const allTagsItemMobile = listMobile.querySelector('[data-tag="all"]');
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

function setPaginationControlsVisible(visible: boolean): void {
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

function showNewPromptForm() {
  const promptEditor = document.getElementById('prompt-editor');
  const promptsList = document.getElementById('prompts-list');
  const pullRefreshToolbar = document.getElementById('pull-refresh-toolbar');

  history.pushState({ modal: 'editor' }, '');
  showElement(promptEditor);
  const promptForm = document.getElementById('prompt-form') as HTMLFormElement | null;
  promptForm?.reset();
  setSelectedTags([]);
  const tagInput = getTagInputElement();
  if (tagInput) {
    tagInput.value = '';
  }
  hideElement(promptsList);
  hideElement(pullRefreshToolbar);
  setPaginationControlsVisible(false);
}

function hidePromptEditor() {
  const promptEditor = document.getElementById('prompt-editor');
  const promptsList = document.getElementById('prompts-list');
  const pullRefreshToolbar = document.getElementById('pull-refresh-toolbar');

  hideElement(promptEditor);
  showElement(promptsList);
  showElement(pullRefreshToolbar);
  setPaginationControlsVisible(true);
}

async function handlePromptSubmit(event: SubmitEvent): Promise<void> {
  event.preventDefault();

  const form = event.currentTarget as HTMLFormElement | null;
  if (!form) {
    return;
  }
  const tagInput = getTagInputElement();
  if (tagInput) {
    commitTagInput(tagInput);
  }
  const formData = new FormData(form);
  const isEditMode = form.dataset.mode === 'edit';
  const promptId = form.dataset.id;

  clearPromptFormErrors();

  // Client-side required checks to avoid native browser messages
  const titleValue = formData.get('title');
  const title = typeof titleValue === 'string' ? titleValue.trim() : '';
  const promptValue = formData.get('prompt');
  const promptContent = typeof promptValue === 'string' ? promptValue.trim() : '';
  const errors: PromptFieldError[] = [];

  if (!title) {
    errors.push({
      fieldId: 'prompt-title',
      errorId: 'prompt-title-error',
      messageKey: 'validation.titleRequired',
    });
  }

  if (!promptContent) {
    errors.push({
      fieldId: 'prompt-content',
      errorId: 'prompt-content-error',
      messageKey: 'validation.contentRequired',
    });
  }

  // Validate semantic version format if provided
  const semVerValue = formData.get('semantic_version');
  const semVer = typeof semVerValue === 'string' ? semVerValue.trim() : '';
  if (semVer && !/^\d+\.\d+\.\d+$/.test(semVer)) {
    const semVerError = document.getElementById('semantic-version-error');
    if (semVerError) {
      semVerError.textContent = t('validation.semanticVersionFormat');
    }
    const semVerInput = document.getElementById('semantic-version') as HTMLInputElement | null;
    semVerInput?.focus();
    return;
  } else {
    const semVerError = document.getElementById('semantic-version-error');
    if (semVerError) semVerError.textContent = '';
  }

  if (errors.length > 0) {
    errors.forEach((err) => {
      showPromptFieldError(err.fieldId, err.errorId, err.messageKey, false);
    });
    showPromptErrorSummary(errors);
    return;
  }

  try {
    let url = '/api/prompts';
    let method = 'POST';

    if (isEditMode && promptId) {
      url = `/api/prompts/${promptId}`;
      method = 'PUT';
    }

    const response = await fetch(url, {
      method: method,
      body: formData,
    });

    const responseData = (await response.json()) as { error?: string };

    if (response.ok) {
      history.back();
      // Clear version cache for this prompt since a new version was created
      clearVersionCache(promptId);
      // Preserve filter state when refreshing the list
      if (isAnyFilterActive()) {
        void performSearch();
      } else {
        void loadPrompts();
      }
      void loadAvailableTags(); // Refresh tag counts for autocomplete
      void loadTags(); // Refresh sidebar tag list
      // Reset form mode
      delete form.dataset.mode;
      delete form.dataset.id;
    } else {
      showNotification(
        `${t('messages.error')}: ${responseData.error || t('messages.unknownError')}`,
        'error'
      );
    }
  } catch (error) {
    if (!navigator.onLine) {
      await queueOfflinePromptSave(form, formData, isEditMode, promptId);
      return;
    }
    reportAppIssue('savePrompt', error, {
      mode: isEditMode ? 'edit' : 'create',
      promptId: promptId || null,
    });
    showNotification(t('messages.error'), 'error');
  }
}

/**
 * Queues a prompt create/edit made while offline (FR-011). The queued change
 * syncs automatically via syncOfflineQueue() on the next `online` event.
 */
async function queueOfflinePromptSave(
  form: HTMLFormElement,
  formData: FormData,
  isEditMode: boolean,
  promptId: PromptId | undefined
): Promise<void> {
  const payload: Record<string, unknown> = {};
  formData.forEach((value, key) => {
    payload[key] = value;
  });

  if (isEditMode && promptId) {
    const baseVersionRaw = form.dataset.baseVersion;
    const baseVersion = baseVersionRaw ? Number(baseVersionRaw) : null;
    await addQueueEntry({
      operation: 'update',
      promptId: String(promptId),
      baseVersion,
      payload,
    });
  } else {
    await addQueueEntry({ operation: 'create', payload });
  }

  history.back();
  showNotification(t('offline.changeQueued'), 'info');
}

async function copyPromptWithVersion(id: PromptId): Promise<void> {
  try {
    const response = await fetch(`/api/prompts/${id}/copy-with-version`, { method: 'POST' });

    if (response.status === 409) {
      showNotification(t('version.noVersionForCopy'), 'error');
      return;
    }

    if (!response.ok) {
      showNotification(t('messages.copyFailed'), 'error');
      return;
    }

    const data = (await response.json()) as { content: string; semantic_version: string };

    if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
      await navigator.clipboard.writeText(data.content);
    } else {
      const textArea = document.createElement('textarea');
      textArea.value = data.content;
      textArea.setAttribute('readonly', '');
      textArea.className = 'clipboard-helper';
      document.body.appendChild(textArea);
      try {
        textArea.focus();
        textArea.select();
        document.execCommand('copy');
      } finally {
        document.body.removeChild(textArea);
      }
    }

    showNotification(t('version.copiedWithMetadata'), 'success');
  } catch (error) {
    reportAppIssue('copyPromptWithVersion', error, { promptId: id });
    showNotification(t('messages.copyFailed'), 'error');
  }
}

async function copyPrompt(id: PromptId): Promise<void> {
  const cachedPrompt = promptCache[id];

  if (cachedPrompt && typeof cachedPrompt.prompt === 'string') {
    copyTextToClipboard(cachedPrompt.prompt, id);
    return;
  }

  try {
    const prompt = await apiGet<PromptResponse>(`/api/prompts/${id}`);
    promptCache[id] = prompt;
    copyTextToClipboard(prompt.prompt, id);
  } catch (error) {
    reportAppIssue('copyPrompt', error, { promptId: id });
    showCopyFeedback(id, 'messages.copyFailed');
  }
}

function copyTextToClipboard(textToCopy: string, id: PromptId): void {
  if (typeof textToCopy !== 'string') {
    showCopyFeedback(id, 'messages.copyFailed');
    return;
  }

  // Try modern Clipboard API first
  if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
    navigator.clipboard
      .writeText(textToCopy)
      .then(() => {
        showCopyFeedback(id, 'messages.copied');
      })
      .catch((error) => {
        reportAppIssue('clipboardWrite', error, { strategy: 'navigator.clipboard' }, 'warning');
        fallbackCopyTextToClipboard(textToCopy, id);
      });
    return;
  }

  // Fallback for older browsers or non-HTTPS
  fallbackCopyTextToClipboard(textToCopy, id);
}

function fallbackCopyTextToClipboard(text: string, id: PromptId): void {
  // Create a temporary textarea element
  const textArea = document.createElement('textarea');
  textArea.value = text;
  textArea.setAttribute('readonly', '');
  textArea.className = 'clipboard-helper';
  document.body.appendChild(textArea);

  try {
    textArea.focus();
    textArea.select();
    textArea.setSelectionRange(0, textArea.value.length);

    // Modern Clipboard API is tried first, this fallback is for older browsers/non-HTTPS
    // Note: document.execCommand is deprecated but necessary for browser compatibility
    const successful = document.execCommand('copy');
    if (successful) {
      showCopyFeedback(id, 'messages.copied');
    } else {
      showCopyFeedback(id, 'messages.copyFailed');
    }
  } catch (error) {
    reportAppIssue('clipboardFallback', error, {}, 'warning');
    showCopyFeedback(id, 'messages.copyFailed');
  } finally {
    document.body.removeChild(textArea);
  }
}

function showCopyFeedback(id: PromptId, message: string): void {
  const btn = document.querySelector<HTMLButtonElement>(`.copy-btn[data-id="${id}"]`);
  if (btn) {
    const originalText = btn.textContent ?? '';
    // Use translated message if it's a key, otherwise use as-is
    const translatedMessage = tUnsafe(message) !== message ? tUnsafe(message) : message;
    btn.textContent = translatedMessage;
    setTimeout(() => (btn.textContent = originalText), 2000);
  }
}

async function editPrompt(id: PromptId): Promise<void> {
  try {
    const prompt = await apiGet<PromptResponse>(`/api/prompts/${id}`);

    promptCache[id] = prompt;

    // Show editor without resetting form
    history.pushState({ modal: 'editor' }, '');
    showElement(document.getElementById('prompt-editor'));
    hideElement(document.getElementById('prompts-list'));
    hideElement(document.getElementById('pull-refresh-toolbar'));
    setPaginationControlsVisible(false);

    // Populate form
    const promptTitle = document.getElementById('prompt-title') as HTMLInputElement | null;
    const promptContent = document.getElementById('prompt-content') as HTMLTextAreaElement | null;
    const promptCategory = document.getElementById('prompt-category') as HTMLInputElement | null;
    const commitMessage = document.getElementById('commit-message') as HTMLInputElement | null;
    if (promptTitle) promptTitle.value = prompt.title || '';
    if (promptContent) promptContent.value = prompt.prompt || '';
    if (promptCategory) promptCategory.value = prompt.category || '';
    setSelectedTags(prompt.tags ? prompt.tags : []);
    if (commitMessage) commitMessage.value = ''; // Clear commit message for new edit
    const semVerInput = document.getElementById('semantic-version') as HTMLInputElement | null;
    if (semVerInput) semVerInput.value = prompt.semantic_version || '';

    // Change form to update mode
    const form = document.getElementById('prompt-form') as HTMLFormElement | null;
    if (form) {
      form.dataset.mode = 'edit';
      form.dataset.id = id;
    }

    // Track the current version for offline-sync conflict detection (FR-012):
    // best-effort — if this fails (e.g. offline), the form simply has no
    // baseVersion and the offline queue omits expected_version on sync.
    try {
      const history_ = await apiGet<{ versions: VersionSummary[] }>(`/api/prompts/${id}/versions`);
      const latest = history_.versions[0];
      if (form && latest) {
        form.dataset.baseVersion = String(latest.version_number);
      }
    } catch {
      // Non-fatal: offline-sync conflict detection degrades to "no check requested".
    }
  } catch (error) {
    reportAppIssue('loadPromptForEdit', error, { promptId: id });
  }
}

async function deletePrompt(id: PromptId): Promise<void> {
  const confirmed = await confirmAsync({
    title: t('actions.confirmDelete') || 'Confirm',
    message: t('messages.confirmDelete') || 'Are you sure?',
    confirmLabel: t('actions.delete') || 'Delete',
    cancelLabel: t('actions.cancel') || 'Cancel',
  });
  if (!confirmed) return;

  try {
    await apiFetch<void>(`/api/prompts/${id}`, { method: 'DELETE' });
    // If we get here, delete succeeded (apiFetch throws on error)
    // Preserve filter state when refreshing the list
    if (isAnyFilterActive()) {
      void performSearch();
    } else {
      void loadPrompts();
    }
    void loadAvailableTags(); // Refresh tag counts for autocomplete
    void loadTags(); // Refresh sidebar tag list
  } catch (error) {
    reportAppIssue('deletePrompt', error, { promptId: id });
    showNotification(t('messages.error'), 'error');
  }
}

async function toggleFavorite(id: PromptId): Promise<void> {
  try {
    // Optimistic update - immediately toggle the UI
    const favoriteBtn = document.querySelector<HTMLButtonElement>(`.favorite-btn[data-id="${id}"]`);
    if (favoriteBtn) {
      const currentFavorite =
        typeof promptCache[id]?.favorite === 'boolean'
          ? promptCache[id].favorite
          : favoriteBtn.getAttribute('aria-pressed') === 'true' ||
            (favoriteBtn.textContent ?? '').trim() === '★';
      const nextFavorite = !currentFavorite;

      favoriteBtn.textContent = nextFavorite ? '★' : '☆';
      setFavoriteButtonA11y(favoriteBtn, nextFavorite);

      // Also update the cached prompt data
      if (promptCache[id]) {
        promptCache[id].favorite = nextFavorite;
      }
    }

    // Make API call to persist the change
    await apiFetch<void>(`/api/prompts/${id}/favorite`, {
      method: 'PUT',
    });
  } catch (error) {
    // Revert optimistic update on error
    const favoriteBtn = document.querySelector<HTMLButtonElement>(`.favorite-btn[data-id="${id}"]`);
    if (favoriteBtn) {
      const currentFavorite =
        typeof promptCache[id]?.favorite === 'boolean'
          ? promptCache[id].favorite
          : favoriteBtn.getAttribute('aria-pressed') === 'true' ||
            (favoriteBtn.textContent ?? '').trim() === '★';
      const revertedFavorite = !currentFavorite;

      favoriteBtn.textContent = revertedFavorite ? '★' : '☆';
      setFavoriteButtonA11y(favoriteBtn, revertedFavorite);

      // Also revert the cached prompt data
      if (promptCache[id]) {
        promptCache[id].favorite = revertedFavorite;
      }
    }

    reportAppIssue('toggleFavorite', error, { promptId: id });
    showNotification(t('messages.error'), 'error');
  }
}

function handleCategoryFilter(event: Event): void {
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

function handleTagFilter(event: Event): void {
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

function handleFavoritesFilter(event: Event): void {
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

function hideModal() {
  hideElement(document.getElementById('prompt-modal'));
}

// Search and Filter Functions
let searchTimeout: ReturnType<typeof setTimeout> | null = null;

function setupSearchEventListeners() {
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
function updateSearchClearButtons(): void {
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
function clearSearchTerm(sourceInputId: string): void {
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

  // Clear previous timeout
  if (searchTimeout) {
    clearTimeout(searchTimeout);
  }

  // Debounce search
  const isOverlayInput = target.id === 'search-input-overlay';
  searchTimeout = setTimeout(() => {
    void performSearch().then(() => {
      // Close the full-screen overlay once results are ready so the user
      // can see the filtered list without an extra manual dismiss (FR-016).
      if (isOverlayInput && isSearchOverlayOpen()) {
        closeSearchOverlay();
      }
    });
  }, 300);
}

async function performSearch(): Promise<void> {
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
  const promptsList = document.getElementById('prompts-list');

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
    if (promptsList) {
      promptsList.innerHTML = `<div class="col-span-full text-center text-gray-500 py-12">${t('search.noResultsMessage')}</div>`;
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

function clearAllFilters(): void {
  // Reset search state
  searchState = {
    searchTerm: '',
    category: 'all',
    tag: 'all',
    favorites: false,
    caseSensitive: false,
    isLoading: false,
  };

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

// Version Control Functions
let currentVersionPromptId: number | null = null;
let selectedVersions: Set<string> = new Set();
let versionCache: Record<string, VersionCacheEntry> = {}; // Cache for version history
let diffCache: Record<string, DiffCacheEntry> = {}; // Cache for diff results
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes in milliseconds

function showVersionHistoryModal(promptId: number): void {
  currentVersionPromptId = promptId;
  selectedVersions.clear();
  // Store trigger element for focus return
  versionHistoryModalTrigger = (event as unknown as { target: HTMLElement }).target || null;
  history.pushState({ modal: 'version-history' }, '');
  showElement(document.getElementById('version-history-modal'));
  // Move focus to first focusable element in modal
  const modal = document.getElementById('version-history-modal');
  if (modal) {
    const focusableElements = Array.from(
      modal.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      )
    ).filter((el) => {
      const style = window.getComputedStyle(el);
      return style.display !== 'none' && style.visibility !== 'hidden';
    });
    if (focusableElements.length > 0) {
      const first = focusableElements[0];
      if (first) first.focus();
    }
  }
  // Update search placeholder with current language
  const searchInput = document.getElementById('version-search') as HTMLInputElement | null;
  if (searchInput) {
    searchInput.placeholder = t('version.searchPlaceholder');
  }
  void loadVersionHistory(promptId);
}

function hideVersionHistoryModal(): void {
  hideElement(document.getElementById('version-history-modal'));
  currentVersionPromptId = null;
  selectedVersions.clear();
  // Return focus to trigger element
  if (versionHistoryModalTrigger) {
    versionHistoryModalTrigger.focus();
  }
}

function hideDiffModal(): void {
  hideElement(document.getElementById('diff-modal'));
  // Return focus to trigger element
  if (diffModalTrigger) {
    diffModalTrigger.focus();
  }
}

function hideRevertConfirmationModal(): void {
  hideElement(document.getElementById('revert-confirmation-modal'));
  // Return focus to trigger element
  if (revertConfirmationModalTrigger) {
    revertConfirmationModalTrigger.focus();
  }
}

async function loadVersionHistory(promptId: number): Promise<void> {
  try {
    const versionList = document.getElementById('version-list');
    if (versionList) {
      versionList.innerHTML =
        '<div class="text-center text-gray-500 py-8">' + t('messages.loading') + '</div>';
    }

    // Check cache first
    const cacheKey = `versions_${promptId}`;
    if (versionCache[cacheKey] && Date.now() - versionCache[cacheKey].timestamp < CACHE_DURATION) {
      const cachedData = versionCache[cacheKey].data;
      renderVersionHistory(cachedData.versions || []);
      updateCompareButton();
      return;
    }

    const data = await apiGet<VersionHistoryResponse>(`/api/prompts/${promptId}/versions`);

    // Cache the result
    versionCache[cacheKey] = {
      data: data,
      timestamp: Date.now(),
    };

    // Store all versions for diff operations
    allVersions = data.versions || [];

    renderVersionHistory(data.versions || []);
    updateCompareButton();
  } catch (error) {
    reportAppIssue('loadVersionHistory', error, { promptId });
    const versionList = document.getElementById('version-list');
    if (versionList) {
      versionList.innerHTML =
        '<div class="text-center text-red-600 py-8">Error loading versions</div>';
    }
  }
}

function renderVersionHistory(versions: VersionSummary[]): void {
  const versionList = document.getElementById('version-list');
  if (!versionList) {
    return;
  }

  if (versions.length === 0) {
    versionList.innerHTML =
      '<div class="text-center text-gray-500 py-8">' + t('version.noVersions') + '</div>';
    hideVersionCarouselNav();
    return;
  }

  versionList.innerHTML = '';
  versions.forEach((version, index) => {
    const versionItem = createVersionItem(version, index, versions.length);
    versionList.appendChild(versionItem);
  });

  initializeVersionListKeyboardNavigation(versionList);
  initVersionCarousel(versionList, versions.length);
}

// Mobile swipeable version-history carousel (FR-018): pages through one
// version at a time via swipe or the visible prev/next buttons.
let versionCarouselIndex = 0;
let detachVersionCarouselSwipe: (() => void) | null = null;
let detachVersionCarouselButtons: (() => void) | null = null;

function hideVersionCarouselNav(): void {
  document.getElementById('version-carousel-nav')?.classList.add('hidden');
  document.getElementById('version-list')?.classList.remove('carousel-mode');
}

function updateVersionCarouselPosition(total: number): void {
  const position = document.getElementById('version-carousel-position');
  const prevBtn = document.getElementById('version-carousel-prev') as HTMLButtonElement | null;
  const nextBtn = document.getElementById('version-carousel-next') as HTMLButtonElement | null;
  if (position) {
    position.textContent = `${versionCarouselIndex + 1} / ${total}`;
  }
  if (prevBtn) prevBtn.disabled = versionCarouselIndex === 0;
  if (nextBtn) nextBtn.disabled = versionCarouselIndex === total - 1;
}

function showVersionCarouselItem(versionList: HTMLElement, index: number): void {
  const items = versionList.querySelectorAll<HTMLElement>('.version-item');
  items.forEach((item, i) => {
    item.classList.toggle('carousel-active', i === index);
  });
}

function initVersionCarousel(versionList: HTMLElement, total: number): void {
  const nav = document.getElementById('version-carousel-nav');
  if (!nav || total === 0) return;

  // Only enabled on mobile viewports; desktop keeps the vertical list (md:hidden on nav).
  if (window.matchMedia('(min-width: 768px)').matches) {
    hideVersionCarouselNav();
    return;
  }

  nav.classList.remove('hidden');
  nav.classList.add('flex');
  versionList.classList.add('carousel-mode');
  versionCarouselIndex = 0;
  showVersionCarouselItem(versionList, versionCarouselIndex);
  updateVersionCarouselPosition(total);

  const prevBtn = document.getElementById('version-carousel-prev');
  const nextBtn = document.getElementById('version-carousel-next');

  const goToPrev = (): void => {
    if (versionCarouselIndex === 0) return;
    versionCarouselIndex -= 1;
    showVersionCarouselItem(versionList, versionCarouselIndex);
    updateVersionCarouselPosition(total);
  };
  const goToNext = (): void => {
    if (versionCarouselIndex === total - 1) return;
    versionCarouselIndex += 1;
    showVersionCarouselItem(versionList, versionCarouselIndex);
    updateVersionCarouselPosition(total);
  };

  detachVersionCarouselButtons?.();
  prevBtn?.addEventListener('click', goToPrev);
  nextBtn?.addEventListener('click', goToNext);
  detachVersionCarouselButtons = () => {
    prevBtn?.removeEventListener('click', goToPrev);
    nextBtn?.removeEventListener('click', goToNext);
  };

  detachVersionCarouselSwipe?.();
  detachVersionCarouselSwipe = attachSwipeReveal(versionList, {
    onSwipeLeft: goToNext,
    onSwipeRight: goToPrev,
  });
}

function createVersionItem(
  version: VersionSummary,
  index: number,
  totalVersions: number
): HTMLDivElement {
  const div = document.createElement('div');
  div.className =
    'version-item bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors';
  div.dataset.versionId = version.version_id;
  div.dataset.navLabel = version.message;
  div.setAttribute('role', 'button');
  div.setAttribute('aria-pressed', 'false');
  div.tabIndex = -1;

  // Format timestamp with fallback for invalid dates
  let timestamp = 'Invalid Date';
  try {
    // Handle timestamps with microseconds by truncating to milliseconds
    const cleanTimestamp = version.timestamp.replace(/(\.\d{3})\d*/, '$1');
    const date = new Date(cleanTimestamp);
    if (isNaN(date.getTime())) {
      timestamp = 'Invalid Date';
    } else {
      timestamp = date.toLocaleString();
    }
  } catch {
    timestamp = 'Invalid Date';
  }
  const isLatest = index === 0;

  const semVerBadge = version.semantic_version
    ? `<span class="px-2 py-0.5 text-xs font-semibold rounded-full bg-blue-100 text-blue-700">${version.semantic_version}</span>`
    : `<span class="px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 text-gray-500" data-i18n="version.unversioned">${t('version.unversioned')}</span>`;

  div.innerHTML =
    `
        <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2">
              <span class="text-sm font-semibold text-gray-900 dark:text-gray-100">#${totalVersions - index} ${version.version_id.substring(0, 8)}...</span>
              ${semVerBadge}
            </div>
            <span class="text-xs text-gray-500 dark:text-gray-400">${timestamp}</span>
        </div>
        <div class="text-xs text-gray-600 dark:text-gray-400 mb-1">${t('version.author')}: ${escapeHtml(version.author)}</div>
        <div class="text-sm text-gray-700 dark:text-gray-300 mb-3">${escapeHtml(version.message)}</div>
        <div class="flex gap-2">
            ${!isLatest ? `<button class="px-3 py-1.5 text-xs font-semibold rounded-lg bg-red-500 text-white hover:bg-red-600 transition-all hover:scale-105 active:scale-95" onclick="showRevertConfirmation('${version.version_id}')" data-i18n="version.revert">` + t('version.revert') + `</button>` : ''}
            <button class="px-3 py-1.5 text-xs font-medium rounded-lg bg-blue-100 text-blue-700 hover:bg-blue-200 transition-all hover:scale-105 active:scale-95" onclick="selectVersionForComparison('${version.version_id}')" data-i18n="version.select">` +
    t('version.select') +
    `</button>
        </div>
    `;

  div.addEventListener('click', function (event: MouseEvent) {
    const target = event.target as Element | null;
    if (!target || !target.closest('button')) {
      toggleVersionSelection(version.version_id, div);
    }
  });

  return div;
}

function toggleVersionSelection(versionId: string, element: HTMLElement | null): void {
  if (!element) {
    return;
  }
  if (selectedVersions.has(versionId)) {
    selectedVersions.delete(versionId);
    element.classList.remove('selected', 'ring-2', 'ring-blue-500', 'bg-blue-50');
    element.setAttribute('aria-pressed', 'false');
  } else {
    selectedVersions.add(versionId);
    element.classList.add('selected', 'ring-2', 'ring-blue-500', 'bg-blue-50');
    element.setAttribute('aria-pressed', 'true');
  }
  updateCompareButton();
}

function selectVersionForComparison(versionId: string): void {
  const target = document.querySelector<HTMLElement>(`[data-version-id="${versionId}"]`);
  toggleVersionSelection(versionId, target);
}

function updateCompareButton() {
  const compareBtn = document.getElementById('compare-versions-btn');
  if (compareBtn) {
    toggleElement(compareBtn, selectedVersions.size === 2);
  }
}

function showRevertConfirmation(versionId: string): void {
  // Store trigger element for focus return
  revertConfirmationModalTrigger = (event as unknown as { target: HTMLElement }).target || null;
  showElement(document.getElementById('revert-confirmation-modal'));
  // Move focus to first focusable element in modal
  const modal = document.getElementById('revert-confirmation-modal');
  if (modal) {
    const focusableElements = Array.from(
      modal.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      )
    ).filter((el) => {
      const style = window.getComputedStyle(el);
      return style.display !== 'none' && style.visibility !== 'hidden';
    });
    if (focusableElements.length > 0) {
      const first = focusableElements[0];
      if (first) first.focus();
    }
  }
  const confirmRevertBtn = document.getElementById(
    'confirm-revert-btn'
  ) as HTMLButtonElement | null;
  if (confirmRevertBtn) {
    confirmRevertBtn.onclick = function () {
      performRevert(versionId);
    };
  }
}

async function performRevert(versionId: string): Promise<void> {
  try {
    if (currentVersionPromptId === null) {
      return;
    }
    const revertMessageInput = document.getElementById(
      'revert-commit-message'
    ) as HTMLInputElement | null;
    const commitMessage = revertMessageInput?.value || 'Revert to previous version';

    const formData = new FormData();
    formData.append('commit_message', commitMessage);

    await apiPostForm<void>(
      `/api/prompts/${currentVersionPromptId}/versions/${versionId}/revert`,
      formData
    );

    hideRevertConfirmationModal();
    showNotification(t('version.revertSuccess'), 'success');
    // Clear version cache since a new version was created
    clearVersionCache(currentVersionPromptId);
    void loadVersionHistory(currentVersionPromptId);
    void loadPrompts(); // Refresh main list
    void loadAvailableTags(); // Refresh tag counts for autocomplete
    void loadTags(); // Refresh sidebar tag list
  } catch (error) {
    reportAppIssue('revertVersion', error, {
      promptId: currentVersionPromptId,
      versionId,
    });
    showNotification(t('version.revertError'), 'error');
  }
}

// Diff Visualization Functions
let allVersions: VersionSummary[] = [];

async function showDiffModal(): Promise<void> {
  if (selectedVersions.size !== 2) {
    showNotification(t('messages.selectTwoVersions'), 'error');
    return;
  }

  // Store trigger element for focus return
  diffModalTrigger = (event as unknown as { target: HTMLElement }).target || null;
  showElement(document.getElementById('diff-modal'));
  // Move focus to first focusable element in modal
  const modal = document.getElementById('diff-modal');
  if (modal) {
    const focusableElements = Array.from(
      modal.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      )
    ).filter((el) => {
      const style = window.getComputedStyle(el);
      return style.display !== 'none' && style.visibility !== 'hidden';
    });
    if (focusableElements.length > 0) {
      const first = focusableElements[0];
      if (first) first.focus();
    }
  }
  let versionIds = Array.from(selectedVersions);

  // Sort versions by their version_number to ensure older is first (for old/new comparison)
  const versionsWithNumbers: VersionSortItem[] = versionIds.map((vId) => {
    const version = allVersions.find((v) => v.version_id === vId);
    return { id: vId, number: version ? version.version_number : 0 };
  });

  // Sort by version number (ascending - older first)
  versionsWithNumbers.sort((a, b) => a.number - b.number);
  versionIds = versionsWithNumbers.map((v) => v.id);

  // Populate version selectors
  populateDiffSelectors(versionIds);

  // Load and display diff - older version as v1 (old), newer as v2 (new)
  const [firstVersion, secondVersion] = versionIds;
  if (!firstVersion || !secondVersion) {
    return;
  }
  await loadAndDisplayDiff(firstVersion, secondVersion);
}

function populateDiffSelectors(selectedIds: string[]): void {
  const v1Selector = document.getElementById('diff-v1-selector') as HTMLSelectElement | null;
  const v2Selector = document.getElementById('diff-v2-selector') as HTMLSelectElement | null;

  if (!v1Selector || !v2Selector) {
    return;
  }

  v1Selector.innerHTML = '';
  v2Selector.innerHTML = '';

  allVersions.forEach((version, index) => {
    const option1 = document.createElement('option');
    option1.value = version.version_id;
    option1.textContent = `#${allVersions.length - index} - ${version.message}`;
    if (version.version_id === selectedIds[0]) option1.selected = true;
    v1Selector.appendChild(option1);

    const option2 = document.createElement('option');
    option2.value = version.version_id;
    option2.textContent = `#${allVersions.length - index} - ${version.message}`;
    if (version.version_id === selectedIds[1]) option2.selected = true;
    v2Selector.appendChild(option2);
  });

  // Add change listener
  v1Selector.addEventListener('change', () => updateDiff());
  v2Selector.addEventListener('change', () => updateDiff());
}

async function updateDiff(): Promise<void> {
  const v1Selector = document.getElementById('diff-v1-selector') as HTMLSelectElement | null;
  const v2Selector = document.getElementById('diff-v2-selector') as HTMLSelectElement | null;
  const v1 = v1Selector?.value || '';
  const v2 = v2Selector?.value || '';

  if (v1 === v2) {
    const diffView = document.getElementById('diff-view');
    if (diffView) {
      diffView.innerHTML =
        '<div class="text-center text-gray-500 py-8">Select different versions to compare</div>';
    }
    return;
  }

  await loadAndDisplayDiff(v1, v2);
}

async function loadAndDisplayDiff(v1Id: string, v2Id: string): Promise<void> {
  try {
    if (currentVersionPromptId === null) {
      return;
    }
    const diffView = document.getElementById('diff-view');
    if (diffView) {
      diffView.innerHTML =
        '<div class="text-center text-gray-500 py-8">' + t('messages.loading') + '</div>';
    }

    // Check cache first
    const cacheKey = `diff_${currentVersionPromptId}_${v1Id}_${v2Id}`;
    if (diffCache[cacheKey] && Date.now() - diffCache[cacheKey].timestamp < CACHE_DURATION) {
      displayDiff(diffCache[cacheKey].data);
      return;
    }

    const diff = await apiGet<VersionDiffResponse>(
      `/api/prompts/${currentVersionPromptId}/versions/compare?v1=${v1Id}&v2=${v2Id}`
    );

    // Cache the result
    diffCache[cacheKey] = {
      data: diff,
      timestamp: Date.now(),
    };

    displayDiff(diff);
  } catch (error) {
    reportAppIssue('loadDiff', error, {
      promptId: currentVersionPromptId,
      fromVersion: v1Id,
      toVersion: v2Id,
    });
    const diffView = document.getElementById('diff-view');
    if (diffView) {
      diffView.innerHTML = '<div class="text-center text-red-600 py-8">Error loading diff</div>';
    }
  }
}

function renderCharacterDiff(operations: DiffOperation[]): HTMLElement {
  const container = document.createElement('div');
  container.className = 'whitespace-pre-wrap break-words';

  if (!operations || operations.length === 0) {
    container.textContent = '';
    return container;
  }

  operations.forEach((op) => {
    if (!op || !op.text) {
      return;
    }

    const span = document.createElement('span');
    span.textContent = op.text;

    switch (op.op) {
      case 'equal':
        span.className = 'text-gray-700';
        break;
      case 'delete':
        span.className = 'bg-red-100 line-through text-red-800';
        break;
      case 'insert':
        span.className = 'bg-green-100 font-semibold text-green-800';
        break;
      default:
        span.className = 'text-gray-700';
    }

    container.appendChild(span);
  });

  return container;
}

function displayDiff(diff: VersionDiffResponse): void {
  const diffView = document.getElementById('diff-view');
  if (!diffView) {
    return;
  }
  diffView.innerHTML = '';

  if (!diff.changes || Object.keys(diff.changes).length === 0) {
    diffView.innerHTML =
      '<div class="text-center text-gray-500 py-8">No changes between these versions</div>';
    return;
  }

  const section = document.createElement('div');
  section.className = 'space-y-4';

  const fieldDisplayNames: Record<string, string> = {
    semantic_version: 'Semantic Version',
  };

  Object.entries(diff.changes).forEach(([field, change]) => {
    const fieldDiv = document.createElement('div');
    fieldDiv.className =
      'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4';

    const fieldName = document.createElement('div');
    fieldName.className = 'text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3';
    fieldName.textContent =
      fieldDisplayNames[field] || field.charAt(0).toUpperCase() + field.slice(1);
    fieldDiv.appendChild(fieldName);

    // If character-level diff is available, render it
    if (change.diff && change.diff.length > 0) {
      const diffContainer = renderCharacterDiff(change.diff);
      diffContainer.className =
        'p-3 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg ' +
        diffContainer.className;
      fieldDiv.appendChild(diffContainer);
    } else {
      // Fallback to old/new display for backward compatibility
      // Old value
      if (change.old !== null && change.old !== undefined) {
        const oldDiv = document.createElement('div');
        oldDiv.className = 'mb-2 p-3 bg-red-50 border border-red-200 rounded-lg';
        oldDiv.innerHTML = `<strong class="text-red-700">Old:</strong> <span class="text-gray-700">${escapeHtml(formatValue(change.old))}</span>`;
        fieldDiv.appendChild(oldDiv);
      }

      // New value
      if (change.new !== null && change.new !== undefined) {
        const newDiv = document.createElement('div');
        newDiv.className = 'p-3 bg-emerald-50 border border-emerald-200 rounded-lg';
        newDiv.innerHTML = `<strong class="text-emerald-700">New:</strong> <span class="text-gray-700">${escapeHtml(formatValue(change.new))}</span>`;
        fieldDiv.appendChild(newDiv);
      }
    }

    section.appendChild(fieldDiv);
  });

  diffView.appendChild(section);
}

function formatValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.join(', ');
  }
  if (typeof value === 'object' && value !== null) {
    return JSON.stringify(value);
  }
  return String(value);
}

function escapeHtml(text: string): string {
  const map: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
  };
  return text.replace(/[&<>"']/g, (m) => map[m] ?? m);
}

// Cache management functions
function clearVersionCache(promptId: number | string | null | undefined): void {
  if (promptId === null || promptId === undefined) {
    return;
  }
  const cacheKey = `versions_${promptId}`;
  delete versionCache[cacheKey];
}

// Keyboard Shortcuts (Phase 6)
function handleKeyboardShortcuts(event: KeyboardEvent): void {
  // Ctrl/Cmd + H: Open version history for last selected prompt
  if ((event.ctrlKey || event.metaKey) && event.key === 'h') {
    event.preventDefault();
    if (lastSelectedPromptId) {
      showVersionHistoryModal(lastSelectedPromptId);
    } else {
      showNotification(t('messages.selectPromptFirst'), 'info');
    }
  }

  // Ctrl/Cmd + N: New prompt
  if ((event.ctrlKey || event.metaKey) && event.key === 'n') {
    event.preventDefault();
    showNewPromptForm();
  }

  // Escape: Close modals.
  // For views that pushed a history entry (editor, version-history), use
  // history.back() so the entry is cleaned up; only do so when the view is
  // actually visible to avoid spurious back-navigations.
  if (event.key === 'Escape') {
    const versionHistoryModal = document.getElementById('version-history-modal');
    const promptEditor = document.getElementById('prompt-editor');
    if (versionHistoryModal && !versionHistoryModal.classList.contains('hidden')) {
      history.back();
    } else if (promptEditor && !promptEditor.classList.contains('hidden')) {
      history.back();
    }
    hideDiffModal();
    hideRevertConfirmationModal();
  }
}

function showKeyboardShortcutsHelpModal(): void {
  const buildLandmarksHelpList = (): string => {
    const landmarks = Array.from(
      document.querySelectorAll<HTMLElement>(
        'header[role="banner"], nav[role="navigation"], main[role="main"], aside[role="complementary"], footer[role="contentinfo"]'
      )
    );

    if (landmarks.length === 0) {
      return `<li>${escapeHtml(t('accessibility.keyboardHelp.noLandmarks'))}</li>`;
    }

    return landmarks
      .map((landmark, index) => {
        const role = landmark.getAttribute('role') ?? landmark.tagName.toLowerCase();
        const ariaLabel = landmark.getAttribute('aria-label')?.trim();
        const ariaLabelledBy = landmark.getAttribute('aria-labelledby');
        const labelledByText = ariaLabelledBy
          ? document.getElementById(ariaLabelledBy)?.textContent?.trim()
          : '';
        const label = ariaLabel || labelledByText;
        const description = label ? `${role} (${label})` : role;
        return `<li><strong>${index + 1}.</strong> ${escapeHtml(description)}</li>`;
      })
      .join('');
  };

  if (!keyboardHelpModal) {
    const content = document.createElement('div');
    content.className = 'space-y-3 text-sm text-gray-700';
    content.innerHTML = `
      <p class="text-gray-600">${escapeHtml(t('accessibility.keyboardHelp.shortcutsHeading'))}</p>
      <ul class="list-disc list-inside space-y-1">
        <li><strong>Ctrl/Cmd + H</strong>: ${escapeHtml(t('accessibility.keyboardHelp.shortcutHistory'))}</li>
        <li><strong>Ctrl/Cmd + N</strong>: ${escapeHtml(t('accessibility.keyboardHelp.shortcutNewPrompt'))}</li>
        <li><strong>Escape</strong>: ${escapeHtml(t('accessibility.keyboardHelp.shortcutEscape'))}</li>
        <li><strong>?</strong>: ${escapeHtml(t('accessibility.keyboardHelp.shortcutQuestion'))}</li>
        <li><strong>Arrow keys</strong>: ${escapeHtml(t('accessibility.keyboardHelp.shortcutArrows'))}</li>
        <li><strong>Enter / Space</strong>: ${escapeHtml(t('accessibility.keyboardHelp.shortcutActivate'))}</li>
        <li><strong>Home / End</strong>: ${escapeHtml(t('accessibility.keyboardHelp.shortcutHomeEnd'))}</li>
        <li><strong>${escapeHtml(t('accessibility.keyboardHelp.shortcutCharacterKey'))}</strong>: ${escapeHtml(t('accessibility.keyboardHelp.shortcutCharacter'))}</li>
      </ul>
      <div class="pt-2 border-t border-gray-200">
        <p class="text-gray-600">${escapeHtml(t('accessibility.keyboardHelp.landmarksHeading'))}</p>
        <ul id="keyboard-help-landmarks-list" class="list-disc list-inside space-y-1">
          ${buildLandmarksHelpList()}
        </ul>
      </div>
    `;

    keyboardHelpModal = createModal({
      id: 'keyboard-shortcuts-help-modal',
      title: t('accessibility.keyboardHelp.title'),
      content,
      ariaLabel: t('accessibility.keyboardHelp.ariaLabel'),
      size: 'md',
      actions: [
        {
          label: t('actions.close'),
          variant: 'primary',
          onClick: () => {
            keyboardHelpModal?.close();
          },
        },
      ],
      closeOnEscape: true,
      closeOnBackdrop: true,
      showClose: true,
    });

    document.body.appendChild(keyboardHelpModal.element);
  }

  const landmarksList = keyboardHelpModal.element.querySelector<HTMLElement>(
    '#keyboard-help-landmarks-list'
  );
  if (landmarksList) {
    landmarksList.innerHTML = buildLandmarksHelpList();
  }

  keyboardHelpModal.open();
}

// Tooltips (Phase 6 & 8)
function addTooltips() {
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

// Lazy Loading for Version List (Phase 9)
let versionListObserver: IntersectionObserver | null = null;
const VERSIONS_PER_PAGE = 10;
let currentVersionPage = 0;

function initializeLazyLoading() {
  if ('IntersectionObserver' in window) {
    versionListObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            loadMoreVersions();
          }
        });
      },
      { threshold: 0.1 }
    );
  }
}

function loadMoreVersions() {
  const versionList = document.getElementById('version-list');
  if (!versionList) return;

  const items = versionList.querySelectorAll('.version-item');
  const totalItems = allVersions.length;
  const itemsToShow = (currentVersionPage + 1) * VERSIONS_PER_PAGE;

  if (items.length < totalItems && items.length < itemsToShow) {
    currentVersionPage++;
    const startIdx = currentVersionPage * VERSIONS_PER_PAGE;
    const endIdx = Math.min(startIdx + VERSIONS_PER_PAGE, totalItems);

    for (let i = startIdx; i < endIdx; i++) {
      const version = allVersions[i];
      if (!version) {
        continue;
      }
      const versionItem = createVersionItem(version, i, totalItems);
      versionList.appendChild(versionItem);
    }

    // Observe the last item for lazy loading
    const lastItem = versionList.lastElementChild;
    if (versionListObserver && lastItem) {
      versionListObserver.observe(lastItem);
    }
  }
}

let versionListKeyboardNavInitialized = false;

function syncVersionListRovingTabindex(versionList: HTMLElement): void {
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

function initializeVersionListKeyboardNavigation(versionList: HTMLElement): void {
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

// API Response Time Profiling (Phase 9)
const apiMetrics: Record<
  string,
  { calls: number; totalTime: number; avgTime: number; minTime: number; maxTime: number }
> = {};

function recordApiCall(endpoint: string, duration: number): void {
  if (!apiMetrics[endpoint]) {
    apiMetrics[endpoint] = {
      calls: 0,
      totalTime: 0,
      avgTime: 0,
      minTime: Infinity,
      maxTime: 0,
    };
  }

  const metric = apiMetrics[endpoint];
  metric.calls++;
  metric.totalTime += duration;
  metric.avgTime = metric.totalTime / metric.calls;
  metric.minTime = Math.min(metric.minTime, duration);
  metric.maxTime = Math.max(metric.maxTime, duration);
}

// Wrap fetch to track API performance
const originalFetch = window.fetch;
window.fetch = async function (...args: Parameters<typeof fetch>) {
  const startTime = performance.now();
  const response = await originalFetch.apply(this, args);
  const duration = performance.now() - startTime;
  const endpoint = typeof args[0] === 'string' ? args[0] : String(args[0]);
  recordApiCall(endpoint, duration);
  return response;
};

// Tag Autocomplete Implementation
let availableTags: TagInfo[] = [];
let tagAutocompleteState = {
  isOpen: false,
  highlightedIndex: -1,
  filteredTags: [] as TagInfo[],
  currentPartialTag: '',
};

function getTagInputElement(): HTMLInputElement | null {
  return document.getElementById('prompt-tags-input') as HTMLInputElement | null;
}

function getTagHiddenInput(): HTMLInputElement | null {
  return document.getElementById('prompt-tags') as HTMLInputElement | null;
}

function parseTagInput(value: string): string[] {
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

function syncHiddenTags(): void {
  const hidden = getTagHiddenInput();
  if (!hidden) {
    return;
  }
  hidden.value = selectedTags.join(', ');
}

function renderTagChips(): void {
  const chipContainer = document.getElementById('tag-chips');
  const input = getTagInputElement();
  if (!chipContainer) {
    return;
  }
  chipContainer.innerHTML = '';

  // Don't show empty state - the input placeholder already provides guidance

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

function setSelectedTags(tags: string[]): void {
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

function addTags(tags: string[]): void {
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

function removeTag(tagName: string): void {
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

async function handleSuggestTags(): Promise<void> {
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

async function loadAvailableTags(): Promise<void> {
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

function setupTagAutocomplete() {
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

function handleTagInput(input: HTMLInputElement) {
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

function commitTagInput(input: HTMLInputElement): void {
  const tags = parseTagInput(input.value);
  if (tags.length === 0) {
    return;
  }
  addTags(tags);
  input.value = '';
  handleTagInput(input);
}

function filterTags(partialTag: string, selected: string[]) {
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

function showTagAutocomplete(filteredTags: TagInfo[]) {
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

function closeTagAutocomplete() {
  const autocompleteDiv = document.getElementById('tag-autocomplete');
  if (autocompleteDiv) {
    hideElement(autocompleteDiv);
  }
  tagAutocompleteState.isOpen = false;
  tagAutocompleteState.highlightedIndex = -1;
}

function handleTagInputKeydown(event: KeyboardEvent) {
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

function highlightTagItem(index: number) {
  const autocompleteDiv = document.getElementById('tag-autocomplete');
  if (!autocompleteDiv) {
    return;
  }

  // Remove previous highlight
  autocompleteDiv.querySelectorAll('.tag-autocomplete-item').forEach((item) => {
    item.classList.remove('highlighted', 'bg-blue-50');
  });

  // Add new highlight
  const items = autocompleteDiv.querySelectorAll('.tag-autocomplete-item');
  if (items[index]) {
    items[index].classList.add('highlighted', 'bg-blue-50');
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

// ============================================
// Bulk Actions & Selection Functions
// ============================================

function initializeBulkActions() {
  const selectAllCheckbox = document.getElementById('select-all-checkbox');
  const bulkDeleteBtn = document.getElementById('bulk-delete-btn');
  const bulkTagBtn = document.getElementById('bulk-tag-btn');
  const clearSelectionBtn = document.getElementById('clear-selection-btn');
  const confirmBulkDeleteBtn = document.getElementById('confirm-bulk-delete-btn');
  const cancelBulkDeleteBtn = document.getElementById('cancel-bulk-delete-btn');
  const confirmBulkTagBtn = document.getElementById('confirm-bulk-tag-btn');
  const cancelBulkTagBtn = document.getElementById('cancel-bulk-tag-btn');

  if (selectAllCheckbox) {
    selectAllCheckbox.addEventListener('change', handleSelectAll);
  }

  if (bulkDeleteBtn) {
    bulkDeleteBtn.addEventListener('click', showBulkDeleteConfirmation);
  }
  if (bulkTagBtn) {
    bulkTagBtn.addEventListener('click', showBulkTagModal);
  }

  if (clearSelectionBtn) {
    clearSelectionBtn.addEventListener('click', clearSelection);
  }

  if (confirmBulkDeleteBtn) {
    confirmBulkDeleteBtn.addEventListener('click', () => {
      void performBulkDelete();
    });
  }

  if (cancelBulkDeleteBtn) {
    cancelBulkDeleteBtn.addEventListener('click', hideBulkDeleteModal);
  }

  if (confirmBulkTagBtn) {
    confirmBulkTagBtn.addEventListener('click', () => {
      void performBulkTagUpdate();
    });
  }

  if (cancelBulkTagBtn) {
    cancelBulkTagBtn.addEventListener('click', hideBulkTagModal);
  }
}

function handleCheckboxChange(promptId: number, isChecked: boolean) {
  if (isChecked) {
    selectedPromptIds.add(promptId);
  } else {
    selectedPromptIds.delete(promptId);
  }
  updateBulkActionsUI();
}

function handleSelectAll(event: Event) {
  const target = event.target as HTMLInputElement | null;
  const isChecked = target?.checked ?? false;
  const checkboxes = document.querySelectorAll<HTMLInputElement>('.prompt-checkbox');

  checkboxes.forEach((checkbox) => {
    checkbox.checked = isChecked;
    const promptId = parseInt(checkbox.dataset.promptId || '', 10);
    if (isChecked) {
      selectedPromptIds.add(promptId);
    } else {
      selectedPromptIds.delete(promptId);
    }
  });

  updateBulkActionsUI();
}

function updateBulkActionsUI() {
  const toolbar = document.getElementById('bulk-actions-toolbar') as HTMLElement | null;
  const countElement = document.getElementById('selected-count') as HTMLElement | null;
  const selectAllCheckbox = document.getElementById(
    'select-all-checkbox'
  ) as HTMLInputElement | null;

  if (selectedPromptIds.size > 0) {
    if (toolbar) {
      toolbar.style.display = 'block';
    }
    if (countElement) {
      countElement.textContent = t('bulkDelete.selectedCount', { count: selectedPromptIds.size });
    }
  } else {
    if (toolbar) {
      toolbar.style.display = 'none';
    }
  }

  // Update select all checkbox state
  const allCheckboxes = document.querySelectorAll<HTMLInputElement>('.prompt-checkbox');
  const allChecked = allCheckboxes.length > 0 && selectedPromptIds.size === allCheckboxes.length;
  if (selectAllCheckbox) {
    selectAllCheckbox.checked = allChecked;
  }

  // Update selected styling on prompt items
  allCheckboxes.forEach((checkbox) => {
    const promptId = parseInt(checkbox.dataset.promptId || '', 10);
    const promptItem = checkbox.closest('.prompt-item');
    if (promptItem) {
      if (selectedPromptIds.has(promptId)) {
        promptItem.classList.add('selected');
      } else {
        promptItem.classList.remove('selected');
      }
    }
  });
}

function clearSelection() {
  selectedPromptIds.clear();
  const checkboxes = document.querySelectorAll<HTMLInputElement>('.prompt-checkbox');
  checkboxes.forEach((checkbox) => (checkbox.checked = false));
  updateBulkActionsUI();
}

function showBulkDeleteConfirmation() {
  if (selectedPromptIds.size === 0) return;

  // Store trigger element for focus return
  bulkDeleteModalTrigger = (event as unknown as { target: HTMLElement }).target || null;
  const modal = document.getElementById('bulk-delete-modal');
  const countElement = document.getElementById('bulk-delete-count');
  if (countElement) {
    countElement.textContent = String(selectedPromptIds.size);
  }
  if (modal) {
    modal.classList.remove(HIDDEN_CLASS);
    // Move focus to first focusable element in modal
    focusFirstElement(modal);
  }
}

function hideBulkDeleteModal() {
  const modal = document.getElementById('bulk-delete-modal');
  if (modal) {
    modal.classList.add(HIDDEN_CLASS);
  }
  // Return focus to trigger element
  if (bulkDeleteModalTrigger) {
    bulkDeleteModalTrigger.focus();
  }
}

function showBulkTagModal() {
  if (selectedPromptIds.size === 0) return;

  // Store trigger element for focus return
  bulkTagModalTrigger = (event as unknown as { target: HTMLElement }).target || null;
  const modal = document.getElementById('bulk-tag-modal');
  const countElement = document.getElementById('bulk-tag-count');
  if (countElement) {
    countElement.textContent = String(selectedPromptIds.size);
  }
  if (modal) {
    modal.classList.remove(HIDDEN_CLASS);
    // Move focus to first focusable element in modal
    focusFirstElement(modal);
  }
}

function hideBulkTagModal() {
  const modal = document.getElementById('bulk-tag-modal');
  if (modal) {
    modal.classList.add(HIDDEN_CLASS);
  }
  // Return focus to trigger element
  if (bulkTagModalTrigger) {
    bulkTagModalTrigger.focus();
  }
}

// Expose modal close handlers for inline template hooks
(
  window as typeof window & { hideBulkDeleteModal?: () => void; hideBulkTagModal?: () => void }
).hideBulkDeleteModal = hideBulkDeleteModal;
(window as typeof window & { hideBulkTagModal?: () => void }).hideBulkTagModal = hideBulkTagModal;

async function performBulkDelete(): Promise<void> {
  if (selectedPromptIds.size === 0) return;

  const promptIdsArray = Array.from(selectedPromptIds);

  try {
    const result = await apiFetch<BulkDeleteResponse>('/api/prompts/bulk', {
      method: 'DELETE',
      body: JSON.stringify({
        prompt_ids: promptIdsArray,
      }),
    });

    if (result.success) {
      hideBulkDeleteModal();
      clearSelection();

      // Show success message
      const message = t('bulkDelete.successMessage', {
        deleted: result.deleted_count,
        failed: result.failed_count,
      });
      showNotification(message, 'success');

      // Announce deletion result to screen reader
      announceToScreenReader(
        `${result.deleted_count} prompt(s) deleted successfully. Focus returned to bulk delete button.`,
        'polite'
      );

      // Refresh UI
      await loadPrompts();
      await loadAvailableTags();
      await loadTags();

      // Report errors if any
      if (result.failed_count > 0) {
        reportAppIssue(
          'bulk-delete-partial-failure',
          new Error(`${result.failed_count} prompts failed to delete`),
          { failed_ids: result.failed_ids },
          'warning'
        );
      }
    } else {
      throw new Error(result.detail || 'Bulk deletion failed');
    }
  } catch (error) {
    console.error('Bulk delete error:', error);
    showNotification(t('bulkDelete.errorMessage'), 'error');
    reportAppIssue('bulk-delete-failed', error, {
      prompt_ids: promptIdsArray,
    });
  }
}

async function performBulkTagUpdate(): Promise<void> {
  if (selectedPromptIds.size === 0) return;

  const addInput = document.getElementById('bulk-tag-add') as HTMLInputElement | null;
  const removeInput = document.getElementById('bulk-tag-remove') as HTMLInputElement | null;

  const addTags = parseTagInput(addInput?.value ?? '');
  const removeTags = parseTagInput(removeInput?.value ?? '');

  if (addTags.length === 0 && removeTags.length === 0) {
    showNotification(t('messages.bulkTagProvideAtLeastOne'), 'info');
    return;
  }

  try {
    await apiFetch('/api/tags/bulk-update', {
      method: 'POST',
      body: JSON.stringify({
        prompt_ids: Array.from(selectedPromptIds),
        add: addTags,
        remove: removeTags,
        confirm: true,
      }),
    });

    hideBulkTagModal();
    clearSelection();
    if (addInput) addInput.value = '';
    if (removeInput) removeInput.value = '';

    await loadPrompts();
    await loadAvailableTags();
    await loadTags();

    showNotification(t('messages.bulkTagUpdateSuccess'), 'success');
  } catch (error) {
    reportAppIssue('bulk-tag-update', error, {
      promptCount: selectedPromptIds.size,
    });
    showNotification(t('messages.bulkTagUpdateFailed'), 'error');
  }
}

// Mobile navigation drawer (hamburger, close, backdrop, focus trap) lives in
// mobile-nav.ts — see initMobileNav() wired in setupEventListeners() above.

initI18n(() => {
  try {
    updateStaticTranslations();
    void initializeApp();
  } catch (error) {
    reportAppIssue('initialize', error);
  }
});

// Initialize lazy loading on app start
initializeLazyLoading();

// Logout function
async function logout() {
  // Anonymous mode: no session to revoke, just navigate home.
  if (window.__AUTH_ENABLED__ === false) {
    window.location.href = '/';
    return;
  }

  try {
    // Get refresh token from localStorage (if it exists from old implementation)
    const refreshToken =
      localStorage.getItem('refresh_token') || sessionStorage.getItem('refresh_token');

    // Call logout endpoint with cookies
    await fetch('/api/auth/logout', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
      body: refreshToken ? JSON.stringify({ refresh_token: refreshToken }) : '{}',
    });
  } catch (error) {
    console.error('Logout error:', error);
    reportAppIssue('logout-error', error, {}, 'warning');
  } finally {
    // Clear cached prompt API responses and any queued offline writes so a
    // different user signing in on this device afterward can't see or replay
    // this user's data.
    await clearOfflineDataOnLogout();

    // Always clear storage and redirect
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    sessionStorage.clear();

    window.location.href = '/auth/login';
  }
}

const appWindow = window as unknown as Window & {
  selectVersionForComparison: (versionId: string) => void;
  showRevertConfirmation: (versionId: string) => void;
  hideVersionHistoryModal: () => void;
  hideDiffModal: () => void;
  hideRevertConfirmationModal: () => void;
  hideBulkDeleteModal: () => void;
};

appWindow.selectVersionForComparison = selectVersionForComparison;
appWindow.showRevertConfirmation = showRevertConfirmation;
appWindow.hideVersionHistoryModal = hideVersionHistoryModal;
appWindow.hideDiffModal = hideDiffModal;
appWindow.hideRevertConfirmationModal = hideRevertConfirmationModal;
appWindow.hideBulkDeleteModal = hideBulkDeleteModal;
