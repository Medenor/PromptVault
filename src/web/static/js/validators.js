// -----------------------------------------------------------------------------
// LEGACY JAVASCRIPT (HISTORICAL REFERENCE ONLY)
// This file remains only for historical reference and should not be edited for
// new work. Make changes in the TypeScript sources under src/web/static/ts.
// -----------------------------------------------------------------------------
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/. */

/**
 * Client-side validation functions for PromptVault.
 *
 * These validators mirror the server-side validation logic defined in
 * src/web/validators/sanitizers.py to ensure client/server validation parity.
 *
 * All validation functions return an object with:
 * - valid: boolean indicating if validation passed
 * - error: string with error message key (for i18n) if validation failed
 * - sanitized: sanitized value (if applicable)
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
  MAX_FILE_SIZE_BYTES,
  ALLOWED_IMPORT_EXTENSIONS,
  ALLOWED_MIME_TYPES,
  SAFE_FILENAME_PATTERN,
  SAFE_BACKUP_NAME_PATTERN,
  CONTROL_CHARACTERS_REGEX,
  MIN_RETENTION_DAYS,
  MAX_RETENTION_DAYS,
  MIN_COMPRESSION_THRESHOLD_DAYS,
  MAX_COMPRESSION_THRESHOLD_DAYS,
} from './validation_constants.js';

/**
 * Strip control characters from text (except newlines if allowed).
 * Mirrors strip_control_characters() from src/web/validators/sanitizers.py
 *
 * @param {string} text - Text to sanitize
 * @param {boolean} allowNewlines - Whether to preserve newlines
 * @returns {string} - Sanitized text
 */
export function stripControlCharacters(text, allowNewlines = true) {
  if (!text) return text;

  if (allowNewlines) {
    // Remove control chars except \n (0x0A), \r (0x0D), \t (0x09)
    return text.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '');
  } else {
    // Remove all control chars including newlines
    return text.replace(/[\x00-\x1F\x7F]/g, '');
  }
}

/**
 * Normalize whitespace in text.
 * Mirrors normalize_whitespace() behavior from sanitizers.py
 *
 * @param {string} text - Text to normalize
 * @param {boolean} allowNewlines - Whether to preserve newlines
 * @returns {string} - Normalized text
 */
export function normalizeWhitespace(text, allowNewlines = true) {
  if (!text) return text;

  if (allowNewlines) {
    // Preserve newlines, but normalize other whitespace
    const lines = text.split('\n');
    return lines.map((line) => line.replace(/\s+/g, ' ').trim()).join('\n');
  } else {
    // Collapse all whitespace to single spaces
    return text.replace(/\s+/g, ' ').trim();
  }
}

/**
 * Sanitize a text field.
 * Mirrors sanitize_text_field() from src/web/validators/sanitizers.py
 *
 * @param {string} text - Text to sanitize
 * @param {number|null} maxLength - Maximum allowed length (null for no limit)
 * @param {boolean} allowNewlines - Whether to preserve newlines
 * @returns {string} - Sanitized text
 */
export function sanitizeTextField(text, maxLength = null, allowNewlines = true) {
  if (!text) return '';

  // Step 1: Strip control characters
  text = stripControlCharacters(text, allowNewlines);

  // Step 2: Normalize whitespace
  text = normalizeWhitespace(text, allowNewlines);

  // Step 3: Trim to max length if specified
  if (maxLength !== null && text.length > maxLength) {
    text = text.substring(0, maxLength);
  }

  return text.trim();
}

/**
 * Deduplicate tags (case-insensitive).
 * Mirrors deduplicate_tags() from src/web/validators/sanitizers.py
 *
 * @param {Array<string>} tags - Array of tags
 * @returns {Array<string>} - Deduplicated tags
 */
export function deduplicateTags(tags) {
  if (!Array.isArray(tags) || tags.length === 0) {
    return [];
  }

  const seen = new Set();
  const uniqueTags = [];

  for (const tag of tags) {
    const normalized = String(tag).trim().toLowerCase();

    if (normalized && !seen.has(normalized)) {
      seen.add(normalized);
      uniqueTags.push(String(tag).trim());
    }
  }

  return uniqueTags;
}

/**
 * Sanitize tags array.
 * Mirrors sanitize_tags() from src/web/validators/sanitizers.py
 *
 * @param {Array<string>} tags - Array of tags
 * @param {number} maxCount - Maximum number of tags
 * @param {number} maxLengthPerTag - Maximum length per tag
 * @returns {Array<string>} - Sanitized tags
 */
export function sanitizeTags(tags, maxCount = MAX_TAG_COUNT, maxLengthPerTag = MAX_TAG_LENGTH) {
  if (!Array.isArray(tags) || tags.length === 0) {
    return [];
  }

  // Step 1: Deduplicate
  let uniqueTags = deduplicateTags(tags);

  // Step 2: Limit count
  uniqueTags = uniqueTags.slice(0, maxCount);

  // Step 3: Sanitize each tag
  const sanitized = [];
  for (const tag of uniqueTags) {
    const cleanTag = sanitizeTextField(String(tag), maxLengthPerTag, false);
    if (cleanTag) {
      sanitized.push(cleanTag);
    }
  }

  return sanitized;
}

/**
 * Validate title field.
 *
 * @param {string} title - Title to validate
 * @param {boolean} required - Whether field is required
 * @returns {object} - Validation result {valid, error, sanitized}
 */
export function validateTitle(title, required = true) {
  const sanitized = sanitizeTextField(title, MAX_TITLE_LENGTH, false);

  if (required && !sanitized) {
    return {
      valid: false,
      error: 'validation.titleRequired',
      sanitized: '',
    };
  }

  if (sanitized.length > MAX_TITLE_LENGTH) {
    return {
      valid: false,
      error: 'validation.titleTooLong',
      sanitized,
    };
  }

  return {
    valid: true,
    error: null,
    sanitized,
  };
}

/**
 * Validate prompt content field.
 *
 * @param {string} prompt - Prompt content to validate
 * @param {boolean} required - Whether field is required
 * @returns {object} - Validation result {valid, error, sanitized}
 */
export function validatePrompt(prompt, required = true) {
  const sanitized = sanitizeTextField(prompt, MAX_PROMPT_LENGTH, true);

  if (required && !sanitized) {
    return {
      valid: false,
      error: 'validation.contentRequired',
      sanitized: '',
    };
  }

  if (sanitized.length > MAX_PROMPT_LENGTH) {
    return {
      valid: false,
      error: 'validation.contentTooLong',
      sanitized,
    };
  }

  return {
    valid: true,
    error: null,
    sanitized,
  };
}

/**
 * Validate category field.
 *
 * @param {string} category - Category to validate
 * @param {boolean} required - Whether field is required
 * @returns {object} - Validation result {valid, error, sanitized}
 */
export function validateCategory(category, required = false) {
  const sanitized = sanitizeTextField(category, MAX_CATEGORY_LENGTH, false);

  if (required && !sanitized) {
    return {
      valid: false,
      error: 'validation.categoryRequired',
      sanitized: '',
    };
  }

  if (sanitized.length > MAX_CATEGORY_LENGTH) {
    return {
      valid: false,
      error: 'validation.categoryTooLong',
      sanitized,
    };
  }

  return {
    valid: true,
    error: null,
    sanitized,
  };
}

/**
 * Validate tags field.
 *
 * @param {Array<string>|string} tags - Tags to validate (array or comma-separated string)
 * @param {boolean} required - Whether field is required
 * @returns {object} - Validation result {valid, error, sanitized}
 */
export function validateTags(tags, required = false) {
  // Convert comma-separated string to array if needed
  let tagArray;
  if (typeof tags === 'string') {
    tagArray = tags
      .split(',')
      .map((t) => t.trim())
      .filter((t) => t);
  } else if (Array.isArray(tags)) {
    tagArray = tags;
  } else {
    tagArray = [];
  }

  const sanitized = sanitizeTags(tagArray);

  if (required && sanitized.length === 0) {
    return {
      valid: false,
      error: 'validation.tagsRequired',
      sanitized: [],
    };
  }

  if (sanitized.length > MAX_TAG_COUNT) {
    return {
      valid: false,
      error: 'validation.tooManyTags',
      sanitized: sanitized.slice(0, MAX_TAG_COUNT),
    };
  }

  // Check individual tag lengths
  const tooLongTags = sanitized.filter((tag) => tag.length > MAX_TAG_LENGTH);
  if (tooLongTags.length > 0) {
    return {
      valid: false,
      error: 'validation.tagTooLong',
      sanitized,
    };
  }

  return {
    valid: true,
    error: null,
    sanitized,
  };
}

/**
 * Validate note field.
 *
 * @param {string} note - Note to validate
 * @param {boolean} required - Whether field is required
 * @returns {object} - Validation result {valid, error, sanitized}
 */
export function validateNote(note, required = false) {
  const sanitized = sanitizeTextField(note, MAX_NOTE_LENGTH, true);

  if (required && !sanitized) {
    return {
      valid: false,
      error: 'validation.noteRequired',
      sanitized: '',
    };
  }

  if (sanitized.length > MAX_NOTE_LENGTH) {
    return {
      valid: false,
      error: 'validation.noteTooLong',
      sanitized,
    };
  }

  return {
    valid: true,
    error: null,
    sanitized,
  };
}

/**
 * Validate commit message field.
 *
 * @param {string} commitMessage - Commit message to validate
 * @param {boolean} required - Whether field is required
 * @returns {object} - Validation result {valid, error, sanitized}
 */
export function validateCommitMessage(commitMessage, required = true) {
  const sanitized = sanitizeTextField(commitMessage, MAX_COMMIT_MESSAGE_LENGTH, false);

  if (required && !sanitized) {
    return {
      valid: false,
      error: 'validation.commitRequired',
      sanitized: '',
    };
  }

  if (sanitized.length > MAX_COMMIT_MESSAGE_LENGTH) {
    return {
      valid: false,
      error: 'validation.commitTooLong',
      sanitized,
    };
  }

  return {
    valid: true,
    error: null,
    sanitized,
  };
}

/**
 * Validate filename.
 *
 * @param {string} filename - Filename to validate
 * @param {boolean} required - Whether field is required
 * @returns {object} - Validation result {valid, error, sanitized}
 */
export function validateFilename(filename, required = true) {
  const sanitized = sanitizeTextField(filename, MAX_FILENAME_LENGTH, false);

  if (required && !sanitized) {
    return {
      valid: false,
      error: 'validation.filenameRequired',
      sanitized: '',
    };
  }

  if (!SAFE_FILENAME_PATTERN.test(sanitized)) {
    return {
      valid: false,
      error: 'validation.filenameInvalid',
      sanitized,
    };
  }

  if (sanitized.length > MAX_FILENAME_LENGTH) {
    return {
      valid: false,
      error: 'validation.filenameTooLong',
      sanitized,
    };
  }

  return {
    valid: true,
    error: null,
    sanitized,
  };
}

/**
 * Validate backup name.
 *
 * @param {string} backupName - Backup name to validate
 * @param {boolean} required - Whether field is required
 * @returns {object} - Validation result {valid, error, sanitized}
 */
export function validateBackupName(backupName, required = false) {
  const sanitized = sanitizeTextField(backupName, MAX_BACKUP_NAME_LENGTH, false);

  if (required && !sanitized) {
    return {
      valid: false,
      error: 'validation.backupNameRequired',
      sanitized: '',
    };
  }

  if (sanitized && !SAFE_BACKUP_NAME_PATTERN.test(sanitized)) {
    return {
      valid: false,
      error: 'validation.backupNameInvalid',
      sanitized,
    };
  }

  if (sanitized.length > MAX_BACKUP_NAME_LENGTH) {
    return {
      valid: false,
      error: 'validation.backupNameTooLong',
      sanitized,
    };
  }

  return {
    valid: true,
    error: null,
    sanitized,
  };
}

/**
 * Validate file upload.
 *
 * @param {File} file - File object to validate
 * @returns {object} - Validation result {valid, error}
 */
export function validateFileUpload(file) {
  if (!file) {
    return {
      valid: false,
      error: 'validation.fileRequired',
    };
  }

  // Check file size
  if (file.size > MAX_FILE_SIZE_BYTES) {
    return {
      valid: false,
      error: 'validation.fileTooLarge',
    };
  }

  // Check file extension
  const fileName = file.name.toLowerCase();
  const hasValidExtension = Array.from(ALLOWED_IMPORT_EXTENSIONS).some((ext) =>
    fileName.endsWith(ext)
  );

  if (!hasValidExtension) {
    return {
      valid: false,
      error: 'validation.fileInvalidExtension',
    };
  }

  // Check MIME type
  if (file.type && !ALLOWED_MIME_TYPES.has(file.type)) {
    return {
      valid: false,
      error: 'validation.fileInvalidMimeType',
    };
  }

  return {
    valid: true,
    error: null,
  };
}

/**
 * Validate retention days.
 *
 * @param {number|string} days - Number of days
 * @returns {object} - Validation result {valid, error, sanitized}
 */
export function validateRetentionDays(days) {
  const numDays = parseInt(days, 10);

  if (isNaN(numDays)) {
    return {
      valid: false,
      error: 'validation.retentionDaysInvalid',
      sanitized: MIN_RETENTION_DAYS,
    };
  }

  if (numDays < MIN_RETENTION_DAYS) {
    return {
      valid: false,
      error: 'validation.retentionDaysTooLow',
      sanitized: MIN_RETENTION_DAYS,
    };
  }

  if (numDays > MAX_RETENTION_DAYS) {
    return {
      valid: false,
      error: 'validation.retentionDaysTooHigh',
      sanitized: MAX_RETENTION_DAYS,
    };
  }

  return {
    valid: true,
    error: null,
    sanitized: numDays,
  };
}

/**
 * Validate compression threshold days.
 *
 * @param {number|string} days - Number of days
 * @returns {object} - Validation result {valid, error, sanitized}
 */
export function validateCompressionDays(days) {
  const numDays = parseInt(days, 10);

  if (isNaN(numDays)) {
    return {
      valid: false,
      error: 'validation.compressionDaysInvalid',
      sanitized: MIN_COMPRESSION_THRESHOLD_DAYS,
    };
  }

  if (numDays < MIN_COMPRESSION_THRESHOLD_DAYS) {
    return {
      valid: false,
      error: 'validation.compressionDaysTooLow',
      sanitized: MIN_COMPRESSION_THRESHOLD_DAYS,
    };
  }

  if (numDays > MAX_COMPRESSION_THRESHOLD_DAYS) {
    return {
      valid: false,
      error: 'validation.compressionDaysTooHigh',
      sanitized: MAX_COMPRESSION_THRESHOLD_DAYS,
    };
  }

  return {
    valid: true,
    error: null,
    sanitized: numDays,
  };
}

/**
 * Get duplicate tags in an array (case-insensitive).
 *
 * @param {Array<string>} tags - Array of tags
 * @returns {Array<string>} - Array of duplicate tags (original casing)
 */
export function getDuplicateTags(tags) {
  if (!Array.isArray(tags) || tags.length === 0) {
    return [];
  }

  const seen = new Map(); // Maps lowercase tag -> first occurrence
  const duplicates = [];

  for (const tag of tags) {
    const normalized = String(tag).trim().toLowerCase();
    if (!normalized) continue;

    if (seen.has(normalized)) {
      duplicates.push(tag);
    } else {
      seen.set(normalized, tag);
    }
  }

  return duplicates;
}

/**
 * Validate entire prompt form data.
 *
 * @param {object} formData - Form data object with title, prompt, category, tags, etc.
 * @param {boolean} isUpdate - Whether this is an update (affects required fields)
 * @returns {object} - Validation result {valid, errors, sanitized}
 */
export function validatePromptForm(formData, isUpdate = false) {
  const errors = {};
  const sanitized = {};

  // Validate title
  const titleResult = validateTitle(formData.title, true);
  if (!titleResult.valid) {
    errors.title = titleResult.error;
  }
  sanitized.title = titleResult.sanitized;

  // Validate prompt content
  const promptResult = validatePrompt(formData.prompt, true);
  if (!promptResult.valid) {
    errors.prompt = promptResult.error;
  }
  sanitized.prompt = promptResult.sanitized;

  // Validate category (optional)
  const categoryResult = validateCategory(formData.category, false);
  if (!categoryResult.valid) {
    errors.category = categoryResult.error;
  }
  sanitized.category = categoryResult.sanitized;

  // Validate tags (optional)
  const tagsResult = validateTags(formData.tags, false);
  if (!tagsResult.valid) {
    errors.tags = tagsResult.error;
  }
  sanitized.tags = tagsResult.sanitized;

  // Validate note (optional)
  if (formData.note !== undefined) {
    const noteResult = validateNote(formData.note, false);
    if (!noteResult.valid) {
      errors.note = noteResult.error;
    }
    sanitized.note = noteResult.sanitized;
  }

  // Validate commit message (required for updates)
  if (formData.commit_message !== undefined) {
    const commitResult = validateCommitMessage(formData.commit_message, isUpdate);
    if (!commitResult.valid) {
      errors.commit_message = commitResult.error;
    }
    sanitized.commit_message = commitResult.sanitized;
  }

  return {
    valid: Object.keys(errors).length === 0,
    errors,
    sanitized,
  };
}
