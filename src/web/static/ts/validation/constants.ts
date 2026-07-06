/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Validation constants for PromptVault client-side validation.
 *
 * These constants mirror the server-side validation constraints defined in
 * src/web/validators/constraints.py to ensure client/server validation parity.
 */

// Text field length constraints
export const MAX_TITLE_LENGTH = 200;
export const MAX_PROMPT_LENGTH = 50000;
export const MAX_CATEGORY_LENGTH = 100;
export const MAX_TAG_LENGTH = 50;
export const MAX_TAG_COUNT = 50;
export const MAX_NOTE_LENGTH = 10000;
export const MAX_COMMIT_MESSAGE_LENGTH = 500;

// Filename constraints
export const MAX_FILENAME_LENGTH = 255;
export const MAX_BACKUP_NAME_LENGTH = 64;

// File upload constraints
export const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB
export const MAX_FILE_SIZE_MB = 10;

// Allowed file extensions for import
export const ALLOWED_IMPORT_EXTENSIONS = new Set(['.csv', '.json', '.md', '.markdown']);

// Allowed MIME types for import
export const ALLOWED_MIME_TYPES = new Set([
  'text/csv',
  'application/json',
  'text/markdown',
  'text/plain', // Some systems report .md as text/plain
]);

// Backup retention constraints
export const MIN_RETENTION_DAYS = 1;
export const MAX_RETENTION_DAYS = 3650; // 10 years

export const MIN_COMPRESSION_THRESHOLD_DAYS = 1;
export const MAX_COMPRESSION_THRESHOLD_DAYS = 365; // 1 year

// Regular expressions for validation
export const SAFE_FILENAME_PATTERN = /^[A-Za-z0-9_-]+$/;
export const SAFE_BACKUP_NAME_PATTERN = /^[A-Za-z0-9_-]+$/;

// Control characters (ASCII 0-31 except newline, carriage return, tab)
// Used for stripping control characters from input
// eslint-disable-next-line no-control-regex
export const CONTROL_CHARACTERS_REGEX = /[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g;

// Character count warning thresholds (show warning when approaching limit)
export const WARNING_THRESHOLD_PERCENTAGE = 0.9; // Show warning at 90% of max length

/**
 * Validation state constants
 */
export const ValidationState = {
  VALID: 'valid',
  WARNING: 'warning',
  ERROR: 'error',
  PRISTINE: 'pristine',
} as const;

export type ValidationStateKey = (typeof ValidationState)[keyof typeof ValidationState];

/**
 * Get warning threshold for a given maximum length.
 */
export function getWarningThreshold(maxLength: number): number {
  return Math.floor(maxLength * WARNING_THRESHOLD_PERCENTAGE);
}

/**
 * Check if current length is approaching the limit.
 */
export function isApproachingLimit(currentLength: number, maxLength: number): boolean {
  return currentLength >= getWarningThreshold(maxLength);
}

/**
 * Check if current length exceeds the limit.
 */
export function exceedsLimit(currentLength: number, maxLength: number): boolean {
  return currentLength > maxLength;
}

/**
 * Get remaining characters for a field.
 */
export function getRemainingChars(currentLength: number, maxLength: number): number {
  return Math.max(0, maxLength - currentLength);
}

/**
 * Format bytes to human-readable format.
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

/**
 * Get validation state for a field based on its length.
 */
export function getValidationState(
  currentLength: number,
  maxLength: number,
  required = false,
  touched = false
): ValidationStateKey {
  if (!touched) {
    return ValidationState.PRISTINE;
  }

  if (required && currentLength === 0) {
    return ValidationState.ERROR;
  }

  if (exceedsLimit(currentLength, maxLength)) {
    return ValidationState.ERROR;
  }

  if (isApproachingLimit(currentLength, maxLength)) {
    return ValidationState.WARNING;
  }

  return ValidationState.VALID;
}
