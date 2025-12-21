/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { ExportFormat, ImportMode, UserRole } from './enums';

// ============================================
// PROMPT ENDPOINTS
// ============================================

/**
 * Request body for creating a new prompt
 * POST /api/prompts
 */
export interface PromptCreateRequest {
  /** Prompt title (1-200 characters) */
  title: string;
  /** Prompt content (1-50,000 characters) */
  prompt: string;
  /** Optional category (0-100 characters) */
  category?: string;
  /** Comma-separated tags (max 50 tags, each max 50 chars) */
  tags?: string;
  /** Optional note (0-2,000 characters) */
  note?: string;
}

/**
 * Request body for updating a prompt
 * PUT /api/prompts/{id}
 */
export interface PromptUpdateRequest extends PromptCreateRequest {
  /** Commit message describing the change (1-500 characters) */
  commit_message: string;
}

/**
 * Request body for bulk deleting prompts
 * DELETE /api/prompts/bulk
 */
export interface BulkDeleteRequest {
  /** Array of prompt IDs to delete (1-1000 IDs, all unique) */
  prompt_ids: number[];
}

// ============================================
// AUTHENTICATION ENDPOINTS
// ============================================

/**
 * Request body for user login
 * POST /api/auth/login
 */
export interface LoginRequest {
  /** Username or email address */
  username_or_email: string;
  /** User's password */
  password: string;
  /** Keep user logged in with extended refresh token */
  remember_me?: boolean;
}

/**
 * Request body for user registration
 * POST /api/auth/register
 */
export interface RegisterRequest {
  /** Username (3-32 chars, alphanumeric + underscore) */
  username: string;
  /** Valid email address */
  email: string;
  /** Password (must meet security policy) */
  password: string;
  /** Must match password exactly */
  confirm_password: string;
}

/**
 * Request body for changing password
 * POST /api/auth/me/change-password
 */
export interface ChangePasswordRequest {
  /** Current password for verification */
  current_password: string;
  /** New password (must meet security policy) */
  new_password: string;
  /** Must match new_password exactly */
  confirm_password: string;
}

/**
 * Request body for password reset request
 * POST /api/auth/password-reset/request
 */
export interface PasswordResetRequestRequest {
  /** Email address to send reset link */
  email: string;
}

/**
 * Request body for confirming password reset
 * POST /api/auth/password-reset/confirm
 */
export interface PasswordResetConfirmRequest {
  /** Reset token from email link */
  token: string;
  /** New password (must meet security policy) */
  new_password: string;
  /** Must match new_password exactly */
  confirm_password: string;
}

/**
 * Request body for updating user profile
 * PUT /api/auth/me
 */
export interface UpdateProfileRequest {
  /** Display name (optional) */
  display_name?: string;
  /** New email address (optional) */
  email?: string;
}

// ============================================
// EXPORT/IMPORT ENDPOINTS
// ============================================

/**
 * Request body for exporting prompts
 * POST /api/export
 */
export interface ExportRequest {
  /** Export format */
  format: ExportFormat;
  /** Suggested filename (1-255 chars, alphanumeric + underscore/hyphen) */
  filename?: string;
  /** Only export favorites */
  include_favorites?: boolean;
  /** Include metadata (created_at, updated_at, etc.) */
  include_metadata?: boolean;
}

/**
 * Form data for importing prompts
 * POST /api/import (multipart/form-data)
 */
export interface ImportRequest {
  /** How to handle existing prompts */
  mode: ImportMode;
  /** Validate data before importing */
  validate_data?: boolean;
}

// ============================================
// BACKUP ENDPOINTS
// ============================================

/**
 * Request body for creating a backup
 * POST /api/backups
 */
export interface BackupCreateRequest {
  /** Backup name (1-64 chars, alphanumeric + underscore/hyphen) */
  name?: string;
}

/**
 * Request body for backup cleanup
 * POST /api/backups/cleanup
 */
export interface BackupCleanupRequest {
  /** Delete backups older than this many days (1-3650) */
  retention_days: number;
}

/**
 * Request body for backup compression
 * POST /api/backups/compress
 */
export interface BackupCompressRequest {
  /** Compress backups older than this many days (1-365) */
  days_threshold: number;
}

// ============================================
// VERSION CONTROL ENDPOINTS
// ============================================

/**
 * Request body for reverting to a version
 * POST /api/prompts/{id}/versions/{version_id}/revert
 */
export interface VersionRevertRequest {
  /** Commit message for the revert (1-500 characters) */
  commit_message: string;
}

// ============================================
// ADMIN ENDPOINTS
// ============================================

/**
 * Request body for creating a user (admin only)
 * POST /api/admin/users
 */
export interface CreateUserRequest {
  /** Username (3-32 chars, alphanumeric + underscore) */
  username: string;
  /** Valid email address */
  email: string;
  /** Password (must meet security policy) */
  password: string;
  /** Must match password exactly */
  confirm_password: string;
  /** User role (defaults to editor) */
  role?: UserRole;
}

/**
 * Request body for updating a user (admin only)
 * PUT /api/admin/users/{id}
 */
export interface UpdateUserRequest {
  /** Display name (optional) */
  display_name?: string;
  /** Email address (optional) */
  email?: string;
  /** User role (optional) */
  role?: UserRole;
  /** Active status (optional) */
  is_active?: boolean;
}

// ============================================
// TELEMETRY ENDPOINTS
// ============================================

/**
 * Frontend error log entry
 * POST /api/logs/frontend
 */
export interface FrontendLogEntry {
  /** Component where error occurred (1-100 chars) */
  component: string;
  /** Action being performed (1-100 chars) */
  action: string;
  /** Error message (1-500 chars) */
  message: string;
  /** Severity level */
  severity: 'error' | 'warning' | 'info';
  /** Error stack trace (max 2000 chars) */
  stack?: string;
  /** Current page URL (max 500 chars) */
  url?: string;
  /** Additional context */
  context?: Record<string, unknown>;
}
