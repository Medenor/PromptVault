/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Client-side validation functions for PromptVault.
 *
 * These validators mirror the server-side validation logic defined in
 * src/web/validators/sanitizers.py to ensure client/server validation parity.
 */

import {
  ALLOWED_IMPORT_EXTENSIONS,
  ALLOWED_MIME_TYPES,
  CONTROL_CHARACTERS_REGEX,
  MAX_BACKUP_NAME_LENGTH,
  MAX_CATEGORY_LENGTH,
  MAX_COMMIT_MESSAGE_LENGTH,
  MAX_FILENAME_LENGTH,
  MAX_FILE_SIZE_BYTES,
  MAX_NOTE_LENGTH,
  MAX_PROMPT_LENGTH,
  MAX_TAG_COUNT,
  MAX_TAG_LENGTH,
  MAX_TITLE_LENGTH,
  MAX_RETENTION_DAYS,
  MAX_COMPRESSION_THRESHOLD_DAYS,
  MIN_RETENTION_DAYS,
  MIN_COMPRESSION_THRESHOLD_DAYS,
  SAFE_BACKUP_NAME_PATTERN,
  SAFE_FILENAME_PATTERN,
} from './constants';

import type { FileValidationResult, ValidationResult } from '@/types/validation';

/**
 * Strip control characters from text (except newlines if allowed).
 */
export function stripControlCharacters(text: string, allowNewlines = true): string {
  if (!text) return text;

  if (allowNewlines) {
    return text.replace(CONTROL_CHARACTERS_REGEX, '');
  }

  return text.replace(/[\x00-\x1F\x7F]/g, '');
}

/**
 * Normalize whitespace in text.
 */
export function normalizeWhitespace(text: string, allowNewlines = true): string {
  if (!text) return text;

  if (allowNewlines) {
    const lines = text.split('\n');
    return lines.map((line) => line.replace(/\s+/g, ' ').trim()).join('\n');
  }

  return text.replace(/\s+/g, ' ').trim();
}

/**
 * Sanitize a text field.
 */
export function sanitizeTextField(
  text: string,
  maxLength: number | null = null,
  allowNewlines = true
): string {
  if (!text) return '';

  let sanitized = stripControlCharacters(text, allowNewlines);
  sanitized = normalizeWhitespace(sanitized, allowNewlines);

  if (maxLength !== null && sanitized.length > maxLength) {
    sanitized = sanitized.substring(0, maxLength);
  }

  return sanitized.trim();
}

/**
 * Deduplicate tags (case-insensitive).
 */
export function deduplicateTags(tags: string[]): string[] {
  if (!Array.isArray(tags) || tags.length === 0) {
    return [];
  }

  const seen = new Set<string>();
  const uniqueTags: string[] = [];

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
 */
export function sanitizeTags(
  tags: string[],
  maxCount = MAX_TAG_COUNT,
  maxLengthPerTag = MAX_TAG_LENGTH
): string[] {
  if (!Array.isArray(tags) || tags.length === 0) {
    return [];
  }

  let uniqueTags = deduplicateTags(tags);
  uniqueTags = uniqueTags.slice(0, maxCount);

  const sanitized: string[] = [];
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
 */
export function validateTitle(title: string, required = true): ValidationResult<string> {
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
 */
export function validatePrompt(prompt: string, required = true): ValidationResult<string> {
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
 */
export function validateCategory(category: string, required = false): ValidationResult<string> {
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
 */
export function validateTags(
  tags: string[] | string,
  required = false
): ValidationResult<string[]> {
  let tagArray: string[];
  if (typeof tags === 'string') {
    tagArray = tags
      .split(',')
      .map((tag) => tag.trim())
      .filter(Boolean);
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
 */
export function validateNote(note: string, required = false): ValidationResult<string> {
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
 */
export function validateCommitMessage(
  commitMessage: string,
  required = true
): ValidationResult<string> {
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
 */
export function validateFilename(filename: string, required = true): ValidationResult<string> {
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
 */
export function validateBackupName(backupName: string, required = false): ValidationResult<string> {
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
 */
export function validateFileUpload(file: File | null | undefined): FileValidationResult {
  if (!file) {
    return {
      valid: false,
      error: 'validation.fileRequired',
    };
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    return {
      valid: false,
      error: 'validation.fileTooLarge',
    };
  }

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
 */
export function validateRetentionDays(days: number | string): ValidationResult<number> {
  const numDays = Number.parseInt(String(days), 10);

  if (Number.isNaN(numDays)) {
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
 */
export function validateCompressionDays(days: number | string): ValidationResult<number> {
  const numDays = Number.parseInt(String(days), 10);

  if (Number.isNaN(numDays)) {
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
 */
export function getDuplicateTags(tags: string[]): string[] {
  if (!Array.isArray(tags) || tags.length === 0) {
    return [];
  }

  const seen = new Map<string, string>();
  const duplicates: string[] = [];

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

interface PromptFormInput {
  title: string;
  prompt: string;
  category?: string;
  tags?: string[] | string;
  note?: string;
  commit_message?: string;
}

interface PromptFormValidationResult {
  valid: boolean;
  errors: Record<string, string>;
  sanitized: Record<string, string | string[]>;
}

/**
 * Validate entire prompt form data.
 */
export function validatePromptForm(
  formData: PromptFormInput,
  isUpdate = false
): PromptFormValidationResult {
  const errors: Record<string, string> = {};
  const sanitized: Record<string, string | string[]> = {};

  const titleResult = validateTitle(formData.title, true);
  if (!titleResult.valid && titleResult.error) {
    errors.title = titleResult.error;
  }
  sanitized.title = titleResult.sanitized;

  const promptResult = validatePrompt(formData.prompt, true);
  if (!promptResult.valid && promptResult.error) {
    errors.prompt = promptResult.error;
  }
  sanitized.prompt = promptResult.sanitized;

  const categoryResult = validateCategory(formData.category ?? '', false);
  if (!categoryResult.valid && categoryResult.error) {
    errors.category = categoryResult.error;
  }
  sanitized.category = categoryResult.sanitized;

  const tagsResult = validateTags(formData.tags ?? [], false);
  if (!tagsResult.valid && tagsResult.error) {
    errors.tags = tagsResult.error;
  }
  sanitized.tags = tagsResult.sanitized;

  if (formData.note !== undefined) {
    const noteResult = validateNote(formData.note ?? '', false);
    if (!noteResult.valid && noteResult.error) {
      errors.note = noteResult.error;
    }
    sanitized.note = noteResult.sanitized;
  }

  if (formData.commit_message !== undefined) {
    const commitResult = validateCommitMessage(formData.commit_message ?? '', isUpdate);
    if (!commitResult.valid && commitResult.error) {
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
