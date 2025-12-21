/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Export format options for prompts
 */
export enum ExportFormat {
  CSV = 'csv',
  JSON = 'json',
  MARKDOWN = 'markdown',
}

/**
 * Import mode - how to handle existing prompts
 */
export enum ImportMode {
  APPEND = 'append',
  REPLACE = 'replace',
}

/**
 * User roles for RBAC
 */
export enum UserRole {
  VIEWER = 'viewer',
  EDITOR = 'editor',
  ADMIN = 'admin',
}

/**
 * Validation field state
 */
export enum ValidationState {
  VALID = 'valid',
  WARNING = 'warning',
  ERROR = 'error',
  PRISTINE = 'pristine',
}
