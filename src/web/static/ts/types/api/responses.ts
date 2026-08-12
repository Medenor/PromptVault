/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { UserRole } from './enums';

// ============================================
// COMMON RESPONSES
// ============================================

/**
 * Generic message response
 */
export interface MessageResponse {
  message: string;
  success?: boolean;
}

/**
 * API error response format
 */
export interface APIError {
  detail: string | ValidationErrorDetail[];
  error?: string;
}

/**
 * Validation error detail from Pydantic
 */
export interface ValidationErrorDetail {
  loc: Array<string | number>;
  msg: string;
  type: string;
}

// ============================================
// USER/AUTH RESPONSES
// ============================================

/**
 * User information response
 */
export interface UserResponse {
  id: string;
  username: string;
  email: string;
  display_name: string | null;
  role: UserRole;
  is_active: boolean;
  email_verified: boolean;
  created_at: string;
  updated_at: string;
  last_login: string | null;
}

/**
 * Login/refresh token response
 */
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'Bearer';
  expires_in: number;
  user: UserResponse;
}

/**
 * User session information
 */
export interface SessionResponse {
  session_id: string;
  user_id: string;
  created_at: string;
  expires_at: string;
  ip_address: string | null;
  user_agent: string | null;
  is_current: boolean;
}

/**
 * List of user sessions
 */
export interface SessionListResponse {
  sessions: SessionResponse[];
  total_count: number;
}

// ============================================
// PROMPT RESPONSES
// ============================================

/**
 * Single prompt response
 */
export interface PromptResponse {
  id: number;
  title: string;
  prompt: string;
  category: string;
  category_color?: string | null;
  tags: string[];
  tag_colors?: Record<string, string | null>;
  note: string;
  favorite: boolean;
  user_id: string;
  created_at: string | null;
  updated_at: string | null;
  semantic_version?: string | null;
  /**
   * Per-viewer sharing fields (007-prompt-sharing). Present only when
   * AUTH_ENABLED and the request is attributed to a viewer; omitted
   * otherwise (e.g. anonymous mode).
   */
  shared?: boolean;
  legacy_public?: boolean;
  permission?: 'owner' | 'edit' | 'read' | null;
  /**
   * Ranked-search snippet with [[MATCH]]/[[/MATCH]] sentinels around hits
   * (008-full-text-search, US2). Present only on search results with a body
   * match; absent otherwise.
   */
  match_context?: string;
}

// ============================================
// SHARING RESPONSES
// ============================================

/**
 * Minimal user info surfaced in sharing contexts (grant results, typeahead).
 */
export interface UserSuggestion {
  id: string;
  username: string;
}

/**
 * Response for POST /api/prompts/{id}/shares (grant/update a share).
 */
export interface ShareResponse {
  prompt_id: number;
  grantee: UserSuggestion;
  permission: 'read' | 'edit';
  granted_by: string | null;
  created_at: string;
  updated_at: string;
}

/**
 * Response for GET /api/users/search (typeahead).
 */
export interface UserSearchResponse {
  users: UserSuggestion[];
}

/**
 * Response for GET /api/prompts/{id}/shares (grant review, US3).
 */
export interface ShareListResponse {
  prompt_id: number;
  shares: ShareResponse[];
}

/**
 * List of prompts (as object with ID keys)
 */
export interface PromptListResponse {
  prompts: Record<string, PromptResponse>;
  page: number;
  limit: number;
  total_pages: number;
  total_count: number;
  has_next: boolean;
  has_previous: boolean;
}

/**
 * Create prompt success response
 */
export interface PromptCreateResponse {
  success: boolean;
  prompt_id: number;
}

/**
 * Update prompt success response
 */
export interface PromptUpdateResponse {
  success: boolean;
}

/**
 * Delete prompt success response
 */
export interface PromptDeleteResponse {
  success: boolean;
}

/**
 * Toggle favorite response
 */
export interface PromptFavoriteResponse {
  success: boolean;
  favorite: boolean;
}

/**
 * Bulk delete response
 */
export interface BulkDeleteResponse {
  success: boolean;
  deleted_count: number;
  failed_count: number;
  failed_ids: number[];
}

// ============================================
// CATEGORY/TAG RESPONSES
// ============================================

/**
 * List of categories
 */
export interface CategoriesResponse {
  categories: string[];
}

/**
 * Tag with usage count
 */
export interface TagInfo {
  name: string;
  count: number;
  color?: string | null;
}

/**
 * List of tags (can be string or TagInfo)
 */
export interface TagsResponse {
  tags: Array<string | TagInfo>;
}

// ============================================
// VERSION RESPONSES
// ============================================

/**
 * Version summary for list display
 */
export interface VersionInfo {
  version: number;
  version_id: string;
  commit_message: string;
  created_at: string;
  author: string;
  title: string;
  prompt_preview: string;
}

/**
 * Full version details
 */
export interface VersionDetail extends VersionInfo {
  prompt: string;
  category: string;
  tags: string[];
  note: string;
}

/**
 * Version history list
 */
export interface VersionHistoryResponse {
  versions: VersionInfo[];
  total_count: number;
}

/**
 * Diff operation for character-level changes
 */
export interface DiffOperation {
  op: 'equal' | 'delete' | 'insert';
  text: string;
}

/**
 * Field change with optional character-level diff
 */
export interface FieldChange {
  old: string | string[] | null;
  new: string | string[] | null;
  diff?: DiffOperation[];
}

/**
 * Version comparison diff
 */
export interface VersionDiffResponse {
  v1_id: string;
  v2_id: string;
  changes: Record<string, FieldChange>;
}

// ============================================
// BACKUP RESPONSES
// ============================================

/**
 * Backup information
 */
export interface BackupInfo {
  id: string;
  name: string;
  created_at: string;
  size: number;
  compressed: boolean;
  prompt_count: number;
}

/**
 * List of backups
 */
export interface BackupListResponse {
  backups: BackupInfo[];
}

/**
 * Backup statistics
 */
export interface BackupStatsResponse {
  total_count: number;
  total_size: number;
  compressed_count: number;
  oldest_backup: string | null;
  newest_backup: string | null;
}

/**
 * Backup operation result
 */
export interface BackupOperationResponse {
  success: boolean;
  backup_id?: string;
  message?: string;
}

// ============================================
// ADMIN RESPONSES
// ============================================

/**
 * Detailed user info for admin
 */
export interface UserDetailResponse extends UserResponse {
  prompt_count: number;
  session_count: number;
}

/**
 * Paginated user list for admin
 */
export interface UserListResponse {
  users: UserDetailResponse[];
  total_count: number;
  page: number;
  per_page: number;
  pages: number;
}

/**
 * Admin dashboard statistics
 */
export interface AdminStatsResponse {
  total_users: number;
  active_users: number;
  total_sessions: number;
  total_prompts: number;
}

// ============================================
// IMPORT/EXPORT RESPONSES
// ============================================

/**
 * Import preview result
 */
export interface ImportPreviewResponse {
  valid: boolean;
  prompt_count: number;
  errors: string[];
  warnings: string[];
  preview: PromptResponse[];
}

/**
 * Import result
 */
export interface ImportResultResponse {
  success: boolean;
  imported_count: number;
  skipped_count: number;
  errors: string[];
}

/**
 * Import/export statistics
 */
export interface ImportExportStatsResponse {
  total_imports: number;
  total_exports: number;
  last_import: string | null;
  last_export: string | null;
}
