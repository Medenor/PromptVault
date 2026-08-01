/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import type { TranslationKey } from '@/types/i18n';
import { t } from '@/utils/i18n';
import { announce } from '@/utils/a11y';
import { html, raw } from '@/utils/safe-html';
import { ERROR_VISIBLE_CLASS } from './shared';
import { getTagInputElement } from './tag-autocomplete';
import type { PromptFieldError } from './types';

const promptLiveValidationState = new Map<string, boolean>();

export function clearPromptFormErrors(): void {
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

export function showPromptFieldError(
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

export function showPromptErrorSummary(
  errors: PromptFieldError[],
  _escapeHtml: (text: string) => string
): void {
  const banner = document.getElementById('validation-error-banner');
  if (!banner) {
    return;
  }
  if (errors.length === 0) {
    banner.textContent = '';
    banner.style.display = 'none';
    return;
  }

  const itemsHtml = errors.map(
    (err) => html`<li><a href="#${err.fieldId}" class="underline">${t(err.messageKey)}</a></li>`
  );

  // eslint-disable-next-line no-restricted-properties -- structurally escaped via html`` tagged template (utils/safe-html.ts)
  banner.innerHTML = html`
    <p class="font-semibold">${t('validation.errorSummaryHeader')}</p>
    <ul class="list-disc list-inside mt-2 space-y-1">
      ${raw(itemsHtml.join(''))}
    </ul>
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

export function clearPromptFieldError(
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

export function getPromptLiveValidationState(fieldId: string): boolean {
  return promptLiveValidationState.get(fieldId) === true;
}
