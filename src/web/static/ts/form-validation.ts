/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Form validation and real-time feedback for PromptVault.
 *
 * This module provides:
 * - Real-time character count feedback
 * - Tag deduplication warnings
 * - Control character prevention
 * - Inline validation with ARIA support
 * - Non-dismissable error states
 */

import i18next from 'i18next';

import { html, raw } from './utils/safe-html';

import {
  MAX_TITLE_LENGTH,
  MAX_PROMPT_LENGTH,
  MAX_CATEGORY_LENGTH,
  MAX_TAG_COUNT,
  MAX_COMMIT_MESSAGE_LENGTH,
  MAX_FILENAME_LENGTH,
  MAX_BACKUP_NAME_LENGTH,
  getValidationState,
  getRemainingChars,
  ValidationState,
} from './validation/constants';

import {
  validateTitle,
  validatePrompt,
  validateCategory,
  validateTags,
  validateCommitMessage,
  validateFilename,
  validateBackupName,
  validateFileUpload,
  validateRetentionDays,
  validateCompressionDays,
  stripControlCharacters,
  getDuplicateTags,
} from './validation/validators';

import type { ValidationResult } from '@/types/validation';

type FieldValidator = (value: string, required: boolean) => ValidationResult<string>;

/**
 * Safely translate a key with i18next, returning null if not available.
 */
function safeTranslate(key: string, options: Record<string, unknown> = {}): string | null {
  if (i18next.isInitialized) {
    const translated = i18next.t(key, options);
    // i18next.t() returns the key itself if translation fails
    if (translated && translated !== key) {
      return translated;
    }
  }
  return null;
}

function translateCharCounter(
  counterId: string,
  length: number,
  maxLength: number,
  required = false
): void {
  const counter = document.getElementById(counterId);
  if (!counter) return;

  const remaining = getRemainingChars(length, maxLength);
  const translationKey = remaining === 1 ? 'validation.charRemaining' : 'validation.charsRemaining';
  const state = getValidationState(length, maxLength, required, true);

  counter.textContent = i18next.t(translationKey, { count: remaining });
  counter.className = `char-counter char-counter-${state}`;
}

/**
 * Initialize validation for a text field with character counter.
 */
export function initFieldValidation(
  fieldId: string,
  counterId: string | null,
  errorId: string,
  maxLength: number,
  required = false,
  validator: FieldValidator | null = null,
  allowNewlines = true
): void {
  const field = document.getElementById(fieldId) as HTMLInputElement | HTMLTextAreaElement | null;
  const counter = counterId ? document.getElementById(counterId) : null;
  const errorEl = document.getElementById(errorId);

  if (!field) return;

  let touched = false;

  function updateField(): void {
    if (!field) return;
    const value = field.value || '';
    const length = value.length;
    const remaining = getRemainingChars(length, maxLength);
    const state = getValidationState(length, maxLength, required, touched);

    if (counter) {
      const translationKey =
        remaining === 1 ? 'validation.charRemaining' : 'validation.charsRemaining';
      counter.textContent = i18next.t(translationKey, { count: remaining });
      counter.className = `char-counter char-counter-${state}`;
    }

    if (validator && touched) {
      const result = validator(value, required);

      if (errorEl) {
        if (result.valid) {
          errorEl.textContent = '';
          delete errorEl.dataset.errorKey;
          errorEl.className = 'validation-error';
          field.setAttribute('aria-invalid', 'false');
        } else {
          errorEl.textContent = i18next.t(result.error ?? '');
          if (result.error) {
            errorEl.dataset.errorKey = result.error;
          }
          errorEl.className = 'validation-error validation-error-visible';
          field.setAttribute('aria-invalid', 'true');
        }
      }

      field.classList.remove('field-valid', 'field-warning', 'field-error');
      if (!result.valid) {
        field.classList.add('field-error');
      } else if (state === ValidationState.WARNING) {
        field.classList.add('field-warning');
      } else if (touched) {
        field.classList.add('field-valid');
      }
    } else {
      field.classList.remove('field-valid', 'field-warning', 'field-error');
      if (state === ValidationState.ERROR) {
        field.classList.add('field-error');
      } else if (state === ValidationState.WARNING) {
        field.classList.add('field-warning');
      } else if (touched && state === ValidationState.VALID) {
        field.classList.add('field-valid');
      }
    }
  }

  field.addEventListener('paste', () => {
    setTimeout(() => {
      if (!field) return;
      const cleaned = stripControlCharacters(field.value, allowNewlines);
      if (cleaned !== field.value) {
        field.value = cleaned;
        updateField();
      }
    }, 0);
  });

  field.addEventListener('input', () => {
    touched = true;
    updateField();
  });

  field.addEventListener('blur', () => {
    touched = true;
    updateField();
  });

  field.addEventListener('focus', () => {
    if (counter) {
      counter.style.display = 'block';
    }
  });

  updateField();
}

/**
 * Refresh counters and warnings when language changes or after i18n loads.
 */
export function refreshValidationText(): void {
  const titleField = document.getElementById('prompt-title') as HTMLInputElement | null;
  const contentField = document.getElementById('prompt-content') as HTMLTextAreaElement | null;
  const commitField = document.getElementById('commit-message') as HTMLInputElement | null;
  const tagsField = document.getElementById('prompt-tags') as HTMLInputElement | null;
  const errorEls = document.querySelectorAll<HTMLElement>('.validation-error[data-error-key]');

  if (titleField) {
    translateCharCounter(
      'prompt-title-counter',
      (titleField.value || '').length,
      MAX_TITLE_LENGTH,
      true
    );
  }

  if (contentField) {
    translateCharCounter(
      'prompt-content-counter',
      (contentField.value || '').length,
      MAX_PROMPT_LENGTH,
      true
    );
  }

  if (commitField) {
    translateCharCounter(
      'commit-message-counter',
      (commitField.value || '').length,
      MAX_COMMIT_MESSAGE_LENGTH,
      false
    );
  }

  if (tagsField) {
    const counter = document.getElementById('prompt-tags-counter');
    const duplicatesEl = document.getElementById('prompt-tags-duplicates');
    const tags = (tagsField.value || '')
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);
    const tagCount = tags.length;
    const remaining = MAX_TAG_COUNT - tagCount;
    const translationKey = tagCount === 1 ? 'validation.tagCount' : 'validation.tagsCount';
    const warningKey = remaining === 1 ? 'validation.tagRemaining' : 'validation.tagsRemaining';

    if (counter) {
      const countText = safeTranslate(translationKey, { count: tagCount });
      const remainingText = safeTranslate(warningKey, { count: remaining });

      if (countText) {
        let counterText = countText;
        if (tagCount > 0 && remainingText) {
          counterText += ' • ' + remainingText;
        }
        counter.textContent = counterText;
      }
    }

    if (duplicatesEl) {
      const duplicates = getDuplicateTags(tags);
      if (duplicates.length > 0) {
        duplicatesEl.textContent = i18next.t('validation.duplicateTags', {
          tags: duplicates.join(', '),
        });
        duplicatesEl.className = 'validation-warning validation-warning-visible';
      } else {
        duplicatesEl.textContent = '';
        duplicatesEl.className = 'validation-warning';
      }
    }
  }

  errorEls.forEach((el) => {
    const key = el.dataset.errorKey;
    if (key) {
      el.textContent = i18next.t(key);
    }
  });
}

/**
 * Initialize tag field validation with deduplication warnings.
 */
export function initTagFieldValidation(
  fieldId: string,
  counterId: string,
  errorId: string,
  duplicatesId: string
): void {
  const field = document.getElementById(fieldId) as HTMLInputElement | null;
  const counter = document.getElementById(counterId);
  const errorEl = document.getElementById(errorId);
  const duplicatesEl = document.getElementById(duplicatesId);

  if (!field) return;

  let touched = false;

  function updateTagField(): void {
    if (!field) return;
    const value = field.value || '';
    const tags = value
      .split(',')
      .map((t) => t.trim())
      .filter((t) => t);
    const tagCount = tags.length;

    touched = true;

    if (counter) {
      const translationKey = tagCount === 1 ? 'validation.tagCount' : 'validation.tagsCount';
      const remaining = MAX_TAG_COUNT - tagCount;
      const warningKey = remaining === 1 ? 'validation.tagRemaining' : 'validation.tagsRemaining';

      const countText = safeTranslate(translationKey, { count: tagCount });
      const remainingText = safeTranslate(warningKey, { count: remaining });

      if (countText) {
        let counterText = countText;
        if (tagCount > 0 && remainingText) {
          counterText += ' • ' + remainingText;
        }
        counter.textContent = counterText;
      }

      if (tagCount > MAX_TAG_COUNT) {
        counter.className = 'char-counter char-counter-error';
      } else if (tagCount >= MAX_TAG_COUNT * 0.9) {
        counter.className = 'char-counter char-counter-warning';
      } else {
        counter.className = 'char-counter char-counter-valid';
      }
    }

    const duplicates = getDuplicateTags(tags);
    if (duplicatesEl) {
      if (duplicates.length > 0) {
        duplicatesEl.textContent = i18next.t('validation.duplicateTags', {
          tags: duplicates.join(', '),
        });
        duplicatesEl.className = 'validation-warning validation-warning-visible';
      } else {
        duplicatesEl.textContent = '';
        duplicatesEl.className = 'validation-warning';
      }
    }

    const result = validateTags(tags, false);

    if (errorEl) {
      if (result.valid) {
        errorEl.textContent = '';
        delete errorEl.dataset.errorKey;
        errorEl.className = 'validation-error';
        field.setAttribute('aria-invalid', 'false');
      } else {
        errorEl.textContent = i18next.t(result.error ?? '');
        if (result.error) {
          errorEl.dataset.errorKey = result.error;
        }
        errorEl.className = 'validation-error validation-error-visible';
        field.setAttribute('aria-invalid', 'true');
      }
    }

    field.classList.remove('field-valid', 'field-warning', 'field-error');
    if (!result.valid) {
      field.classList.add('field-error');
    } else if (duplicates.length > 0) {
      field.classList.add('field-warning');
    } else if (touched && tags.length > 0) {
      field.classList.add('field-valid');
    }
  }

  field.addEventListener('paste', () => {
    setTimeout(() => {
      if (!field) return;
      const cleaned = stripControlCharacters(field.value, false);
      if (cleaned !== field.value) {
        field.value = cleaned;
        updateTagField();
      }
    }, 0);
  });

  field.addEventListener('input', updateTagField);
  field.addEventListener('blur', updateTagField);

  updateTagField();
}

/**
 * Initialize file upload validation.
 */
export function initFileUploadValidation(fieldId: string, errorId: string): void {
  const field = document.getElementById(fieldId) as HTMLInputElement | null;
  const errorEl = document.getElementById(errorId);

  if (!field) return;

  function updateFileField(): void {
    if (!field) return;
    const file = field.files?.[0];

    if (!file) {
      if (errorEl) {
        errorEl.textContent = '';
        errorEl.className = 'validation-error';
      }
      field.classList.remove('field-valid', 'field-error');
      return;
    }

    const result = validateFileUpload(file);

    if (errorEl) {
      if (result.valid) {
        errorEl.textContent = '';
        errorEl.className = 'validation-error';
        field.setAttribute('aria-invalid', 'false');
        field.classList.remove('field-error');
        field.classList.add('field-valid');
      } else {
        errorEl.textContent = i18next.t(result.error ?? '');
        errorEl.className = 'validation-error validation-error-visible';
        field.setAttribute('aria-invalid', 'true');
        field.classList.remove('field-valid');
        field.classList.add('field-error');
      }
    }
  }

  field.addEventListener('change', updateFileField);
}

/**
 * Initialize number field validation.
 */
export function initNumberFieldValidation(
  fieldId: string,
  errorId: string,
  validator: (value: string) => ValidationResult<number>
): void {
  const field = document.getElementById(fieldId) as HTMLInputElement | null;
  const errorEl = document.getElementById(errorId);

  if (!field) return;

  function updateNumberField(): void {
    if (!field) return;
    const value = field.value;
    const result = validator(value);

    if (errorEl) {
      if (result.valid) {
        errorEl.textContent = '';
        errorEl.className = 'validation-error';
        field.setAttribute('aria-invalid', 'false');
        field.classList.remove('field-error');
        field.classList.add('field-valid');
      } else {
        errorEl.textContent = i18next.t(result.error ?? '');
        errorEl.className = 'validation-error validation-error-visible';
        field.setAttribute('aria-invalid', 'true');
        field.classList.remove('field-valid');
        field.classList.add('field-error');
      }
    }
  }

  field.addEventListener('input', updateNumberField);
  field.addEventListener('blur', updateNumberField);
}

/**
 * Initialize all form validations on the page.
 */
export function initAllValidations(): void {
  initFieldValidation(
    'prompt-title',
    'prompt-title-counter',
    'prompt-title-error',
    MAX_TITLE_LENGTH,
    true,
    validateTitle,
    false
  );

  initFieldValidation(
    'prompt-content',
    'prompt-content-counter',
    'prompt-content-error',
    MAX_PROMPT_LENGTH,
    true,
    validatePrompt,
    true
  );

  initFieldValidation(
    'prompt-category',
    null,
    'prompt-category-error',
    MAX_CATEGORY_LENGTH,
    false,
    validateCategory,
    false
  );

  initTagFieldValidation(
    'prompt-tags',
    'prompt-tags-counter',
    'prompt-tags-error',
    'prompt-tags-duplicates'
  );

  initFieldValidation(
    'commit-message',
    'commit-message-counter',
    'commit-message-error',
    MAX_COMMIT_MESSAGE_LENGTH,
    false,
    validateCommitMessage,
    false
  );

  initFieldValidation(
    'revert-commit-message',
    'revert-commit-counter',
    'revert-commit-error',
    MAX_COMMIT_MESSAGE_LENGTH,
    true,
    validateCommitMessage,
    false
  );

  initFieldValidation(
    'export-filename',
    null,
    'export-filename-error',
    MAX_FILENAME_LENGTH,
    true,
    validateFilename,
    false
  );

  initFileUploadValidation('import-file', 'import-file-error');

  initFieldValidation(
    'backup-name',
    null,
    'backup-name-error',
    MAX_BACKUP_NAME_LENGTH,
    false,
    validateBackupName,
    false
  );

  initNumberFieldValidation('retention-days', 'retention-days-error', validateRetentionDays);

  initNumberFieldValidation('compress-days', 'compress-days-error', validateCompressionDays);
}

/**
 * Show non-dismissable error summary.
 */
function showErrorSummary(errors: Record<string, string>): void {
  const errorCount = Object.keys(errors).length;
  const translationKey = errorCount === 1 ? 'validation.errorCount' : 'validation.errorsCount';

  let banner = document.getElementById('validation-error-banner');
  if (!banner) {
    banner = document.createElement('div');
    banner.id = 'validation-error-banner';
    banner.className = 'validation-error-banner';
    banner.setAttribute('role', 'alert');
    banner.setAttribute('aria-live', 'assertive');

    const form = document.querySelector('#prompt-form');
    if (form) {
      form.insertBefore(banner, form.firstChild);
    }
  }

  const errorItems = Object.keys(errors).map(
    (field) => html`<li>${i18next.t(errors[field] ?? '')}</li>`
  );

  // eslint-disable-next-line no-restricted-properties -- structurally escaped via html`` tagged template (utils/safe-html.ts)
  banner.innerHTML = html`
    <div class="error-banner-header">
      <strong>${i18next.t(translationKey, { count: errorCount })}</strong>
    </div>
    <ul class="error-banner-list">
      ${raw(errorItems.join(''))}
    </ul>
    <p class="error-banner-message">${i18next.t('validation.fixErrorsMessage')}</p>
  `;

  banner.style.display = 'block';
  banner.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

interface PromptFormData {
  title: string;
  prompt: string;
  category: string;
  tags: string;
  commit_message: string;
}

/**
 * Validate entire prompt form before submission.
 */
export function validateFormBeforeSubmit(form: HTMLFormElement): boolean {
  const formData: PromptFormData = {
    title: (form.querySelector('#prompt-title') as HTMLInputElement | null)?.value || '',
    prompt: (form.querySelector('#prompt-content') as HTMLTextAreaElement | null)?.value || '',
    category: (form.querySelector('#prompt-category') as HTMLInputElement | null)?.value || '',
    tags: (form.querySelector('#prompt-tags') as HTMLInputElement | null)?.value || '',
    commit_message: (form.querySelector('#commit-message') as HTMLInputElement | null)?.value || '',
  };

  const errors: Record<string, string> = {};

  const titleResult = validateTitle(formData.title, true);
  if (!titleResult.valid && titleResult.error) errors.title = titleResult.error;

  const promptResult = validatePrompt(formData.prompt, true);
  if (!promptResult.valid && promptResult.error) errors.prompt = promptResult.error;

  const categoryResult = validateCategory(formData.category, false);
  if (!categoryResult.valid && categoryResult.error) errors.category = categoryResult.error;

  const tagsResult = validateTags(formData.tags, false);
  if (!tagsResult.valid && tagsResult.error) errors.tags = tagsResult.error;

  const commitResult = validateCommitMessage(formData.commit_message, false);
  if (!commitResult.valid && commitResult.error) errors.commit_message = commitResult.error;

  Object.keys(errors).forEach((fieldName) => {
    const errorId = `prompt-${fieldName === 'prompt' ? 'content' : fieldName}-error`;
    const errorEl = document.getElementById(errorId);
    const errorMessage = errors[fieldName];
    if (errorEl && errorMessage) {
      errorEl.textContent = i18next.t(errorMessage);
      errorEl.dataset.errorKey = errorMessage;
      errorEl.className = 'validation-error validation-error-visible';
    }

    const fieldId = fieldName === 'prompt' ? 'prompt-content' : `prompt-${fieldName}`;
    const field = document.getElementById(fieldId);
    if (field) {
      field.setAttribute('aria-invalid', 'true');
      field.classList.add('field-error');
      field.focus();
    }
  });

  const valid = Object.keys(errors).length === 0;
  if (!valid) {
    showErrorSummary(errors);
  }

  return valid;
}

/**
 * Hide error summary banner.
 */
export function hideErrorSummary(): void {
  const banner = document.getElementById('validation-error-banner');
  if (banner) {
    banner.style.display = 'none';
  }
}

// Initialize validations when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAllValidations);
} else {
  initAllValidations();
}

// Refresh counters and error text when i18n initializes or language changes
if (i18next.isInitialized) {
  refreshValidationText();
  i18next.on('languageChanged', refreshValidationText);
} else {
  i18next.on('initialized', () => {
    refreshValidationText();
    i18next.on('languageChanged', refreshValidationText);
  });
}
