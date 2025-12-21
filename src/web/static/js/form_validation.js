/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/. */

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

import {
  MAX_TITLE_LENGTH,
  MAX_PROMPT_LENGTH,
  MAX_CATEGORY_LENGTH,
  MAX_TAG_LENGTH,
  MAX_TAG_COUNT,
  MAX_NOTE_LENGTH,
  MAX_COMMIT_MESSAGE_LENGTH,
  MAX_FILENAME_LENGTH,
  MAX_BACKUP_NAME_LENGTH,
  getValidationState,
  getRemainingChars,
  ValidationState,
} from './validation_constants.js';

import {
  validateTitle,
  validatePrompt,
  validateCategory,
  validateTags,
  validateNote,
  validateCommitMessage,
  validateFilename,
  validateBackupName,
  validateFileUpload,
  validateRetentionDays,
  validateCompressionDays,
  validatePromptForm,
  stripControlCharacters,
  getDuplicateTags,
} from './validators.js';

function translateCharCounter(counterId, length, maxLength, required = false) {
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
 *
 * @param {string} fieldId - ID of the input/textarea field
 * @param {string} counterId - ID of the character counter element
 * @param {string} errorId - ID of the error message element
 * @param {number} maxLength - Maximum allowed length
 * @param {boolean} required - Whether field is required
 * @param {Function} validator - Validation function
 * @param {boolean} allowNewlines - Whether to preserve newlines
 */
export function initFieldValidation(
  fieldId,
  counterId,
  errorId,
  maxLength,
  required = false,
  validator = null,
  allowNewlines = true
) {
  const field = document.getElementById(fieldId);
  const counter = document.getElementById(counterId);
  const errorEl = document.getElementById(errorId);

  if (!field) return;

  let touched = false;

  // Update character counter and validation state
  function updateField() {
    const value = field.value || '';
    const length = value.length;
    const remaining = getRemainingChars(length, maxLength);
    const state = getValidationState(length, maxLength, required, touched);

    // Update counter
    if (counter) {
      const translationKey =
        remaining === 1 ? 'validation.charRemaining' : 'validation.charsRemaining';
      counter.textContent = i18next.t(translationKey, { count: remaining });
      counter.className = `char-counter char-counter-${state}`;
    }

    // Run validator if provided
    if (validator && touched) {
      const result = validator(value, required);

      if (errorEl) {
        if (result.valid) {
          errorEl.textContent = '';
          delete errorEl.dataset.errorKey;
          errorEl.className = 'validation-error';
          field.setAttribute('aria-invalid', 'false');
        } else {
          errorEl.textContent = i18next.t(result.error);
          errorEl.dataset.errorKey = result.error;
          errorEl.className = 'validation-error validation-error-visible';
          field.setAttribute('aria-invalid', 'true');
        }
      }

      // Update field visual state
      field.classList.remove('field-valid', 'field-warning', 'field-error');
      if (!result.valid) {
        field.classList.add('field-error');
      } else if (state === ValidationState.WARNING) {
        field.classList.add('field-warning');
      } else if (touched) {
        field.classList.add('field-valid');
      }
    } else {
      // Just update visual state based on length
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

  // Handle paste events - strip control characters
  field.addEventListener('paste', (e) => {
    setTimeout(() => {
      const cleaned = stripControlCharacters(field.value, allowNewlines);
      if (cleaned !== field.value) {
        field.value = cleaned;
        updateField();
      }
    }, 0);
  });

  // Handle input events
  field.addEventListener('input', () => {
    touched = true;
    updateField();
  });

  // Handle blur events
  field.addEventListener('blur', () => {
    touched = true;
    updateField();
  });

  // Handle focus events
  field.addEventListener('focus', () => {
    if (counter) {
      counter.style.display = 'block';
    }
  });

  // Initial update
  updateField();
}

/**
 * Refresh counters and warnings when language changes or after i18n loads.
 */
export function refreshValidationText() {
  const titleField = document.getElementById('prompt-title');
  const contentField = document.getElementById('prompt-content');
  const commitField = document.getElementById('commit-message');
  const tagsField = document.getElementById('prompt-tags');
  const errorEls = document.querySelectorAll('.validation-error[data-error-key]');

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
      let counterText = i18next.t(translationKey, { count: tagCount });
      if (tagCount > 0) {
        counterText += ' • ' + i18next.t(warningKey, { count: remaining });
      }
      counter.textContent = counterText;
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

  // Retranslate any existing field errors
  if (errorEls && errorEls.length) {
    errorEls.forEach((el) => {
      const key = el.dataset.errorKey;
      if (key) {
        el.textContent = i18next.t(key);
      }
    });
  }
}

/**
 * Initialize tag field validation with deduplication warnings.
 *
 * @param {string} fieldId - ID of the tags input field
 * @param {string} counterId - ID of the character counter element
 * @param {string} errorId - ID of the error message element
 * @param {string} duplicatesId - ID of the duplicates warning element
 */
export function initTagFieldValidation(fieldId, counterId, errorId, duplicatesId) {
  const field = document.getElementById(fieldId);
  const counter = document.getElementById(counterId);
  const errorEl = document.getElementById(errorId);
  const duplicatesEl = document.getElementById(duplicatesId);

  if (!field) return;

  let touched = false;

  function updateTagField() {
    const value = field.value || '';
    const tags = value
      .split(',')
      .map((t) => t.trim())
      .filter((t) => t);
    const tagCount = tags.length;

    touched = true;

    // Update counter
    if (counter) {
      const translationKey = tagCount === 1 ? 'validation.tagCount' : 'validation.tagsCount';
      const remaining = MAX_TAG_COUNT - tagCount;
      const warningKey = remaining === 1 ? 'validation.tagRemaining' : 'validation.tagsRemaining';

      let counterText = i18next.t(translationKey, { count: tagCount });
      if (tagCount > 0) {
        counterText += ' • ' + i18next.t(warningKey, { count: remaining });
      }

      counter.textContent = counterText;

      if (tagCount > MAX_TAG_COUNT) {
        counter.className = 'char-counter char-counter-error';
      } else if (tagCount >= MAX_TAG_COUNT * 0.9) {
        counter.className = 'char-counter char-counter-warning';
      } else {
        counter.className = 'char-counter char-counter-valid';
      }
    }

    // Check for duplicates
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

    // Validate tags
    const result = validateTags(tags, false);

    if (errorEl) {
      if (result.valid) {
        errorEl.textContent = '';
        delete errorEl.dataset.errorKey;
        errorEl.className = 'validation-error';
        field.setAttribute('aria-invalid', 'false');
      } else {
        errorEl.textContent = i18next.t(result.error);
        errorEl.dataset.errorKey = result.error;
        errorEl.className = 'validation-error validation-error-visible';
        field.setAttribute('aria-invalid', 'true');
      }
    }

    // Update field visual state
    field.classList.remove('field-valid', 'field-warning', 'field-error');
    if (!result.valid) {
      field.classList.add('field-error');
    } else if (duplicates.length > 0) {
      field.classList.add('field-warning');
    } else if (touched && tags.length > 0) {
      field.classList.add('field-valid');
    }
  }

  // Handle paste events - strip control characters
  field.addEventListener('paste', (e) => {
    setTimeout(() => {
      const cleaned = stripControlCharacters(field.value, false);
      if (cleaned !== field.value) {
        field.value = cleaned;
        updateTagField();
      }
    }, 0);
  });

  field.addEventListener('input', updateTagField);
  field.addEventListener('blur', updateTagField);

  // Initial update
  updateTagField();
}

/**
 * Initialize file upload validation.
 *
 * @param {string} fieldId - ID of the file input field
 * @param {string} errorId - ID of the error message element
 */
export function initFileUploadValidation(fieldId, errorId) {
  const field = document.getElementById(fieldId);
  const errorEl = document.getElementById(errorId);

  if (!field) return;

  function updateFileField() {
    const file = field.files[0];

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
        errorEl.textContent = i18next.t(result.error);
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
 *
 * @param {string} fieldId - ID of the number input field
 * @param {string} errorId - ID of the error message element
 * @param {Function} validator - Validation function
 */
export function initNumberFieldValidation(fieldId, errorId, validator) {
  const field = document.getElementById(fieldId);
  const errorEl = document.getElementById(errorId);

  if (!field) return;

  function updateNumberField() {
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
        errorEl.textContent = i18next.t(result.error);
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
export function initAllValidations() {
  // Main prompt form fields
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

  // Revert commit message
  initFieldValidation(
    'revert-commit-message',
    'revert-commit-counter',
    'revert-commit-error',
    MAX_COMMIT_MESSAGE_LENGTH,
    true,
    validateCommitMessage,
    false
  );

  // Export filename
  initFieldValidation(
    'export-filename',
    null,
    'export-filename-error',
    MAX_FILENAME_LENGTH,
    true,
    validateFilename,
    false
  );

  // Import file
  initFileUploadValidation('import-file', 'import-file-error');

  // Backup name
  initFieldValidation(
    'backup-name',
    null,
    'backup-name-error',
    MAX_BACKUP_NAME_LENGTH,
    false,
    validateBackupName,
    false
  );

  // Retention days
  initNumberFieldValidation('retention-days', 'retention-days-error', validateRetentionDays);

  // Compression days
  initNumberFieldValidation('compress-days', 'compress-days-error', validateCompressionDays);
}

/**
 * Validate entire prompt form before submission.
 *
 * @param {HTMLFormElement} form - Form element to validate
 * @param {boolean} isUpdate - Whether this is an update operation
 * @returns {boolean} - True if form is valid
 */
export function validateFormBeforeSubmit(form, isUpdate = false) {
  const formData = {
    title: form.querySelector('#prompt-title')?.value || '',
    prompt: form.querySelector('#prompt-content')?.value || '',
    category: form.querySelector('#prompt-category')?.value || '',
    tags: form.querySelector('#prompt-tags')?.value || '',
    commit_message: form.querySelector('#commit-message')?.value || '',
  };

  const result = validatePromptForm(formData, isUpdate);

  // Display errors for each field
  Object.keys(result.errors).forEach((fieldName) => {
    const errorId = `prompt-${fieldName === 'prompt' ? 'content' : fieldName}-error`;
    const errorEl = document.getElementById(errorId);
    if (errorEl) {
      errorEl.textContent = i18next.t(result.errors[fieldName]);
      errorEl.dataset.errorKey = result.errors[fieldName];
      errorEl.className = 'validation-error validation-error-visible';
    }

    const fieldId = fieldName === 'prompt' ? 'prompt-content' : `prompt-${fieldName}`;
    const field = document.getElementById(fieldId);
    if (field) {
      field.setAttribute('aria-invalid', 'true');
      field.classList.add('field-error');
      field.focus(); // Focus first error field
    }
  });

  if (!result.valid) {
    // Show non-dismissable error summary
    showErrorSummary(result.errors);
  }

  return result.valid;
}

/**
 * Show non-dismissable error summary.
 *
 * @param {object} errors - Object containing field errors
 */
function showErrorSummary(errors) {
  const errorCount = Object.keys(errors).length;
  const translationKey = errorCount === 1 ? 'validation.errorCount' : 'validation.errorsCount';

  // Create error summary banner if it doesn't exist
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

  // Build error list
  const errorList = Object.keys(errors)
    .map((field) => `<li>${i18next.t(errors[field])}</li>`)
    .join('');

  banner.innerHTML = `
        <div class="error-banner-header">
            <strong>${i18next.t(translationKey, { count: errorCount })}</strong>
        </div>
        <ul class="error-banner-list">
            ${errorList}
        </ul>
        <p class="error-banner-message">${i18next.t('validation.fixErrorsMessage')}</p>
    `;

  banner.style.display = 'block';

  // Scroll to error banner
  banner.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/**
 * Hide error summary banner.
 */
export function hideErrorSummary() {
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
if (window.i18next) {
  const attachListeners = () => {
    refreshValidationText();
    i18next.on('languageChanged', refreshValidationText);
  };

  if (i18next.isInitialized) {
    attachListeners();
  } else {
    i18next.on('initialized', attachListeners);
  }
}
