/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { t } from '@/utils/i18n';
import { announce } from '@/utils/a11y';
import { createTypeahead } from '@/utils/typeahead';
import type { FormValidationError } from './types';

const liveValidationState = new Map<string, boolean>();
let usersTableKeyboardNavInitialized = false;

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

export function initializeUsersTableFirstCharNavigation(): void {
  if (usersTableKeyboardNavInitialized) {
    return;
  }
  usersTableKeyboardNavInitialized = true;

  const typeahead = createTypeahead();

  const body = document.getElementById('users-table-body');
  if (!body) {
    return;
  }

  body.addEventListener('keydown', (event) => {
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
      const usernameCell = row.querySelector('td');
      const username = usernameCell?.textContent?.trim() ?? '';
      if (!username.toLocaleLowerCase().startsWith(query)) {
        continue;
      }

      const viewButton = row.querySelector<HTMLButtonElement>('button[data-action="view-user"]');
      if (!viewButton) {
        return;
      }

      event.preventDefault();
      viewButton.focus();
      announceKeyboardNavigation(t('accessibility.navigateTo', { item: username }));
      return;
    }
  });

  body.addEventListener('compositionend', (event) => {
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
      const usernameCell = row.querySelector('td');
      const username = usernameCell?.textContent?.trim() ?? '';
      if (!username.toLocaleLowerCase().startsWith(query)) {
        continue;
      }
      const viewButton = row.querySelector<HTMLButtonElement>('button[data-action="view-user"]');
      if (!viewButton) return;
      viewButton.focus();
      announceKeyboardNavigation(t('accessibility.navigateTo', { item: username }));
      return;
    }
  });
}

export function showFieldError(elementId: string, message: string): void {
  const element = document.getElementById(elementId);
  if (element) {
    element.textContent = message;
    element.classList.toggle('hidden', message.trim().length === 0);
  }
}

export function setLiveFieldError(inputId: string, errorId: string, message: string): void {
  const input = document.getElementById(inputId) as HTMLElement | null;
  const hadError = liveValidationState.get(inputId) === true;
  input?.setAttribute('aria-invalid', 'true');
  showFieldError(errorId, message);
  liveValidationState.set(inputId, true);
  if (!hadError) {
    announce(message, { id: 'validation-announcer', politeness: 'polite' });
  }
}

export function clearLiveFieldError(inputId: string, errorId: string): void {
  const input = document.getElementById(inputId) as HTMLElement | null;
  const hadError = liveValidationState.get(inputId) === true;
  input?.setAttribute('aria-invalid', 'false');
  showFieldError(errorId, '');
  liveValidationState.set(inputId, false);
  if (hadError) {
    announce(t('validation.fieldValid') || 'Field is valid.', {
      id: 'validation-announcer',
      politeness: 'polite',
    });
  }
}

export function getLiveValidationState(inputId: string): boolean {
  return liveValidationState.get(inputId) === true;
}

export function resetFormAccessibilityState(
  form: HTMLFormElement | null,
  inputIds: string[],
  summaryId: string
): void {
  if (form) {
    inputIds.forEach((inputId) => {
      const input = form.querySelector<HTMLElement>(`#${inputId}`);
      if (input) {
        input.setAttribute('aria-invalid', 'false');
      }
    });
  }

  const summary = document.getElementById(summaryId);
  if (summary) {
    summary.textContent = '';
    (summary as HTMLElement).style.display = 'none';
    summary.classList.add('hidden');
  }
}

export function addFieldError(
  errors: FormValidationError[],
  inputId: string,
  errorId: string,
  message: string
): void {
  showFieldError(errorId, message);
  const input = document.getElementById(inputId);
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
  errors.push({ inputId, message });
}

export function renderErrorSummary(summaryId: string, errors: FormValidationError[]): void {
  if (errors.length === 0) return;

  const summary = document.getElementById(summaryId);
  if (!summary) {
    document.getElementById(errors[0]?.inputId ?? '')?.focus();
    return;
  }

  summary.textContent = '';
  summary.classList.remove('hidden');
  (summary as HTMLElement).style.display = 'block';

  const header = document.createElement('p');
  header.className = 'error-banner-header';
  header.textContent = t('validation.errorSummaryHeader') || 'Please correct the following errors:';
  summary.appendChild(header);

  const list = document.createElement('ul');
  list.className = 'error-banner-list';
  for (const error of errors) {
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
  }
  summary.appendChild(list);

  // Per plan T-ACC023: focus the first invalid field after rendering the summary.
  const firstInput = document.getElementById(errors[0]?.inputId ?? '') as HTMLElement | null;
  if (firstInput) {
    firstInput.focus();
  } else {
    summary.focus();
  }
}
