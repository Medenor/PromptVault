/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { t, tUnsafe } from '@/utils/i18n';
import { createTypeahead } from '@/utils/typeahead';
import { announce } from '@/utils/a11y';
import type { FormValidationError } from './types';

let tableKeyboardNavInitialized = false;
let rovingTabindexInitialized = false;
let currentCategoryFocusIndex = 0;
const liveValidationState = new Map<string, boolean>();

export function resetRovingTabindexState(): void {
  rovingTabindexInitialized = false;
  currentCategoryFocusIndex = 0;
}

export function announceKeyboardNavigation(message: string): void {
  const announcer = document.getElementById('keyboard-navigation-announcer');
  if (!announcer) {
    return;
  }
  announcer.textContent = '';
  requestAnimationFrame(() => {
    announcer.textContent = message;
  });
}

function isTextEditingTarget(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  if (!el) return false;
  return (
    el.tagName === 'INPUT' ||
    el.tagName === 'TEXTAREA' ||
    el.tagName === 'SELECT' ||
    el.isContentEditable
  );
}

/**
 * Initialize roving tabindex pattern for category list
 * Sets first item's checkbox to tabindex="0" and others to tabindex="-1"
 * Handles arrow key navigation to move focus and update tabindex values
 */
export function initializeRovingTabindex(): void {
  if (rovingTabindexInitialized) {
    return;
  }
  rovingTabindexInitialized = true;

  const container = document.getElementById('categories-table-container');
  if (!container) {
    return;
  }

  const updateTabindexAttributes = (): void => {
    const checkboxes = Array.from(
      container.querySelectorAll<HTMLInputElement>('tbody input[type="checkbox"]')
    );
    checkboxes.forEach((checkbox, index) => {
      if (index === currentCategoryFocusIndex) {
        checkbox.setAttribute('tabindex', '0');
      } else {
        checkbox.setAttribute('tabindex', '-1');
      }
    });
  };

  updateTabindexAttributes();

  container.addEventListener('keydown', (event: Event) => {
    const keyEvent = event as KeyboardEvent;
    const checkboxes = Array.from(
      container.querySelectorAll<HTMLInputElement>('tbody input[type="checkbox"]')
    );

    if (checkboxes.length === 0) {
      return;
    }

    const target = keyEvent.target as HTMLElement | null;
    const row = target?.closest('tr');
    if (!row) {
      return;
    }

    let newIndex = currentCategoryFocusIndex;
    let shouldMove = false;

    switch (keyEvent.key) {
      case 'ArrowDown':
      case 'ArrowRight':
        keyEvent.preventDefault();
        newIndex = Math.min(currentCategoryFocusIndex + 1, checkboxes.length - 1);
        shouldMove = true;
        break;
      case 'ArrowUp':
      case 'ArrowLeft':
        keyEvent.preventDefault();
        newIndex = Math.max(currentCategoryFocusIndex - 1, 0);
        shouldMove = true;
        break;
      case 'Home':
        keyEvent.preventDefault();
        newIndex = 0;
        shouldMove = true;
        break;
      case 'End':
        keyEvent.preventDefault();
        newIndex = checkboxes.length - 1;
        shouldMove = true;
        break;
    }

    if (shouldMove && newIndex !== currentCategoryFocusIndex) {
      currentCategoryFocusIndex = newIndex;
      updateTabindexAttributes();
      checkboxes[newIndex]?.focus();
      const row = checkboxes[newIndex]?.closest('tr');
      const nameInput = row?.querySelector<HTMLInputElement>('input[data-field="name"]');
      announceKeyboardNavigation(
        t('accessibility.navigateTo', { item: nameInput?.value || `Item ${newIndex + 1}` })
      );
    }
  });

  container.addEventListener('click', (event: Event) => {
    const target = event.target as HTMLElement | null;
    const checkbox = target?.closest('input[type="checkbox"]') as HTMLInputElement | null;
    if (checkbox) {
      const checkboxes = Array.from(
        container.querySelectorAll<HTMLInputElement>('tbody input[type="checkbox"]')
      );
      const index = checkboxes.indexOf(checkbox);
      if (index !== -1) {
        currentCategoryFocusIndex = index;
        updateTabindexAttributes();
      }
    }
  });

  container.addEventListener(
    'focus',
    (event: Event) => {
      const target = event.target as HTMLElement | null;
      const checkbox = target?.closest('input[type="checkbox"]') as HTMLInputElement | null;
      if (checkbox) {
        const checkboxes = Array.from(
          container.querySelectorAll<HTMLInputElement>('tbody input[type="checkbox"]')
        );
        const index = checkboxes.indexOf(checkbox);
        if (index !== -1) {
          currentCategoryFocusIndex = index;
          updateTabindexAttributes();
        }
      }
    },
    true
  );
}

export function initializeTableFirstCharNavigation(
  tableBody: HTMLTableSectionElement | null
): void {
  if (tableKeyboardNavInitialized) {
    return;
  }
  tableKeyboardNavInitialized = true;

  const typeahead = createTypeahead();

  const container = document.getElementById('categories-table-container');
  const body = tableBody;
  if (!container || !body) {
    return;
  }

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
    if (event.key.length !== 1) {
      return;
    }

    const rows = Array.from(body.querySelectorAll<HTMLTableRowElement>('tr'));
    if (rows.length === 0) {
      return;
    }

    const target = event.target as HTMLElement | null;
    const currentRow = target?.closest('tr');
    const currentIndex = currentRow ? rows.indexOf(currentRow) : -1;

    const query = typeahead.pushKey(event.key);
    if (!query) {
      return;
    }

    for (let offset = 1; offset <= rows.length; offset++) {
      const index = (currentIndex + offset + rows.length) % rows.length;
      const row = rows[index];
      if (!row) continue;
      const nameInput = row.querySelector<HTMLInputElement>('input[data-field="name"]');
      const label = (nameInput?.value ?? '').trim();
      if (!label.toLocaleLowerCase().startsWith(query)) {
        continue;
      }

      const checkbox = row.querySelector<HTMLInputElement>(
        'input[type="checkbox"][data-select-id]'
      );
      if (!checkbox) {
        return;
      }

      event.preventDefault();
      checkbox.focus();
      announceKeyboardNavigation(t('accessibility.navigateTo', { item: label }));
      return;
    }
  });

  container.addEventListener('compositionend', (event) => {
    const composed = (event as CompositionEvent).data ?? '';
    const query = typeahead.pushText(composed);
    if (!query) {
      return;
    }

    const rows = Array.from(body.querySelectorAll<HTMLTableRowElement>('tr'));
    if (rows.length === 0) {
      return;
    }
    const active = document.activeElement as HTMLElement | null;
    const currentRow = active?.closest?.('tr') as HTMLTableRowElement | null;
    const currentIndex = currentRow ? rows.indexOf(currentRow) : -1;

    for (let offset = 1; offset <= rows.length; offset++) {
      const index = (currentIndex + offset + rows.length) % rows.length;
      const row = rows[index];
      if (!row) continue;
      const nameInput = row.querySelector<HTMLInputElement>('input[data-field="name"]');
      const label = (nameInput?.value ?? '').trim();
      if (!label.toLocaleLowerCase().startsWith(query)) {
        continue;
      }
      const checkbox = row.querySelector<HTMLInputElement>(
        'input[type="checkbox"][data-select-id]'
      );
      if (!checkbox) return;
      checkbox.focus();
      announceKeyboardNavigation(t('accessibility.navigateTo', { item: label }));
      return;
    }
  });
}

export function resetFieldError(inputId: string, errorId: string): void {
  const input = document.getElementById(inputId) as HTMLElement | null;
  const error = document.getElementById(errorId);
  input?.setAttribute('aria-invalid', 'false');
  if (error) {
    error.textContent = '';
  }
}

export function setLiveFieldError(inputId: string, errorId: string, message: string): void {
  const input = document.getElementById(inputId) as HTMLElement | null;
  const error = document.getElementById(errorId) as HTMLElement | null;
  const hadError = liveValidationState.get(inputId) === true;

  input?.setAttribute('aria-invalid', 'true');
  if (error) {
    error.textContent = message;
  }
  liveValidationState.set(inputId, true);

  if (!hadError) {
    announce(message, { id: 'validation-announcer', politeness: 'polite' });
  }
}

export function clearLiveFieldError(inputId: string, errorId: string): void {
  const input = document.getElementById(inputId) as HTMLElement | null;
  const error = document.getElementById(errorId) as HTMLElement | null;
  const hadError = liveValidationState.get(inputId) === true;

  input?.setAttribute('aria-invalid', 'false');
  if (error) {
    error.textContent = '';
  }
  liveValidationState.set(inputId, false);

  if (hadError) {
    announce(t('validation.fieldValid') || 'Field is valid.', {
      id: 'validation-announcer',
      politeness: 'polite',
    });
  }
}

export function attachRequiredLiveValidation(
  input: HTMLInputElement | null,
  inputId: string,
  errorId: string,
  message: string
): void {
  if (!input) return;

  input.addEventListener('blur', () => {
    if (!input.value.trim()) {
      setLiveFieldError(inputId, errorId, message);
    } else {
      clearLiveFieldError(inputId, errorId);
    }
  });

  input.addEventListener('input', () => {
    if (liveValidationState.get(inputId) !== true) {
      return;
    }
    if (input.value.trim()) {
      clearLiveFieldError(inputId, errorId);
    }
  });
}

export function attachFileRequiredLiveValidation(
  input: HTMLInputElement | null,
  inputId: string,
  errorId: string,
  message: string
): void {
  if (!input) return;
  input.addEventListener('change', () => {
    const file = input.files?.[0];
    if (!file) {
      setLiveFieldError(inputId, errorId, message);
    } else {
      clearLiveFieldError(inputId, errorId);
    }
  });
}

export function addFieldError(
  errors: FormValidationError[],
  inputId: string,
  errorId: string,
  message: string
): void {
  const input = document.getElementById(inputId) as HTMLElement | null;
  const error = document.getElementById(errorId);
  if (input) {
    const existing =
      input
        .getAttribute('aria-describedby')
        ?.split(/\s+/)
        .map((s) => s.trim())
        .filter(Boolean) ?? [];
    const next = Array.from(new Set([...existing, errorId]));
    input.setAttribute('aria-describedby', next.join(' '));
  }
  input?.setAttribute('aria-invalid', 'true');
  if (error) {
    error.textContent = message;
  }
  errors.push({ inputId, errorId, message });
}

export function resetErrorSummary(summaryId: string): void {
  const summary = document.getElementById(summaryId);
  if (!summary) return;
  summary.textContent = '';
  summary.style.display = 'none';
}

export function renderErrorSummary(summaryId: string, errors: FormValidationError[]): void {
  if (errors.length === 0) {
    return;
  }

  const summary = document.getElementById(summaryId);
  if (!summary) {
    const firstInput = document.getElementById(errors[0]?.inputId ?? '') as HTMLElement | null;
    firstInput?.focus();
    return;
  }

  summary.textContent = '';
  const header = document.createElement('p');
  header.className = 'error-banner-header';
  header.textContent =
    tUnsafe('validation.errorSummaryHeader') || 'Please correct the following errors:';
  summary.appendChild(header);

  const list = document.createElement('ul');
  list.className = 'error-banner-list';
  errors.forEach((error) => {
    const item = document.createElement('li');
    const link = document.createElement('a');
    link.href = `#${error.inputId}`;
    link.className = 'underline';
    link.textContent = error.message;
    link.addEventListener('click', (event) => {
      event.preventDefault();
      const target = document.getElementById(error.inputId) as HTMLElement | null;
      target?.focus();
    });
    item.appendChild(link);
    list.appendChild(item);
  });
  summary.appendChild(list);
  summary.style.display = 'block';

  // Per plan T-ACC023: focus the first invalid field after rendering the summary.
  const firstInput = document.getElementById(errors[0]?.inputId ?? '') as HTMLElement | null;
  if (firstInput) {
    firstInput.focus();
  } else {
    summary.focus();
  }
}
