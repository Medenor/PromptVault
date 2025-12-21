# TypeScript Migration Plan for PromptVault Frontend

## Executive Summary

This plan migrates PromptVault's vanilla JavaScript frontend to TypeScript with Vite build tooling. The migration is incremental, maintaining backward compatibility throughout.

**Decisions:**

- **Build Tool:** Vite (fast HMR, native ESM, excellent TS support)
- **Strategy:** Incremental file-by-file migration
- **TypeScript:** Strict mode enabled
- **State Management:** No library (type existing patterns)
- **Dev Server:** Vite on 5173 with proxy to FastAPI dev server on 8003
- **Production App Port:** 8001 (FastAPI serves built assets)
- **Docker Entrypoint:** Use `run_web.py` (preferred project entrypoint)
- **Types Strategy:** Pure frontend types initially; consider OpenAPI codegen later

**Current State:**

- 12 JavaScript files totaling ~234KB
- No bundler, no TypeScript, no minification
- Mixed module patterns (ESM + global scripts)
- CDN dependencies (i18next)
- Manual cache-busting with query strings

---

## Phase 0: Infrastructure Setup

### Task 0.1: Update package.json

**File:** `/package.json`

**Merge into existing scripts/deps (do not overwrite). Ensure these scripts and dependencies exist:**

```json
{
  "name": "promptvault",
  "version": "1.3.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "typecheck": "tsc --noEmit",
    "test": "playwright test",
    "test:ui": "playwright test --ui"
  },
  "dependencies": {
    "i18next": "^23.7.6",
    "i18next-browser-languagedetector": "^7.2.0",
    "i18next-http-backend": "^2.4.2"
  },
  "devDependencies": {
    "@playwright/test": "^1.56.1",
    "@types/node": "^20.10.0",
    "playwright": "^1.56.1",
    "typescript": "^5.3.0",
    "vite": "^5.0.0"
  }
}
```

**Commands to run:**

```bash
npm install
```

---

### Task 0.2: Create tsconfig.json

**File:** `/tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "allowJs": true,
    "checkJs": false,
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "strictBindCallApply": true,
    "strictPropertyInitialization": true,
    "noImplicitThis": true,
    "useUnknownInCatchVariables": true,
    "alwaysStrict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "forceConsistentCasingInFileNames": true,
    "isolatedModules": true,
    "noEmit": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/web/static/ts/*"],
      "@types/*": ["src/web/static/ts/types/*"]
    }
  },
  "include": [
    "src/web/static/ts/**/*",
    "vite.config.ts"
  ],
  "exclude": [
    "node_modules",
    "dist",
    "src/web/static/js"
  ]
}
```

---

### Task 0.3: Create vite.config.ts

**File:** `/vite.config.ts`

```typescript
import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: 'src/web/static',
  base: '/static/',
  publicDir: false,

  build: {
    outDir: '../../../dist/static',
    emptyOutDir: true,
    manifest: true,
    sourcemap: true,
    rollupOptions: {
      input: {
        // Main application
        app: resolve(__dirname, 'src/web/static/ts/app.ts'),
        // Authentication pages
        auth: resolve(__dirname, 'src/web/static/ts/auth.ts'),
        profile: resolve(__dirname, 'src/web/static/ts/profile.ts'),
        passwordReset: resolve(__dirname, 'src/web/static/ts/password-reset.ts'),
        // Admin pages
        adminUsers: resolve(__dirname, 'src/web/static/ts/admin-users.ts'),
        adminSessions: resolve(__dirname, 'src/web/static/ts/admin-sessions.ts'),
        // Feature pages
        importExport: resolve(__dirname, 'src/web/static/ts/import-export.ts'),
        backupManagement: resolve(__dirname, 'src/web/static/ts/backup-management.ts'),
        // Shared telemetry (loaded on all pages)
        telemetry: resolve(__dirname, 'src/web/static/ts/telemetry.ts'),
      },
      output: {
        entryFileNames: 'js/[name].[hash].js',
        chunkFileNames: 'js/chunks/[name].[hash].js',
        assetFileNames: 'assets/[name].[hash][extname]',
      },
    },
  },

  resolve: {
    alias: {
      '@': resolve(__dirname, 'src/web/static/ts'),
      '@types': resolve(__dirname, 'src/web/static/ts/types'),
    },
  },

  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/auth': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/static/locales': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
    },
  },
});
```

---

### Task 0.4: Create TypeScript Directory Structure

**Commands:**

```bash
mkdir -p src/web/static/ts/types/api
mkdir -p src/web/static/ts/types/state
mkdir -p src/web/static/ts/utils
mkdir -p src/web/static/ts/validation
```

---

### Task 0.5: Update .gitignore

**File:** `/.gitignore`

**Add these lines:**

```
# Vite build output
dist/
src/web/static/dist/

# TypeScript cache
*.tsbuildinfo
```

---

## Phase 1: Type Definitions

### Task 1.1: Create Enums

**File:** `/src/web/static/ts/types/api/enums.ts`

```typescript
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
```

---

### Task 1.2: Create API Request Types

**File:** `/src/web/static/ts/types/api/requests.ts`

```typescript
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
```

---

### Task 1.3: Create API Response Types

**File:** `/src/web/static/ts/types/api/responses.ts`

```typescript
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
  loc: (string | number)[];
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
  tags: string[];
  note: string;
  favorite: boolean;
  user_id: string;
  created_at: string | null;
  updated_at: string | null;
}

/**
 * List of prompts (as object with ID keys)
 */
export interface PromptListResponse {
  prompts: Record<string, PromptResponse>;
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
}

/**
 * List of tags (can be string or TagInfo)
 */
export interface TagsResponse {
  tags: (string | TagInfo)[];
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
 * Version comparison diff
 */
export interface VersionDiffResponse {
  v1: number;
  v2: number;
  diff: {
    title: { old: string; new: string };
    prompt: { old: string; new: string };
    category: { old: string; new: string };
    tags: { old: string[]; new: string[] };
    note: { old: string; new: string };
  };
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
```

---

### Task 1.4: Create State Types

**File:** `/src/web/static/ts/types/state/app-state.ts`

```typescript
import type { PromptResponse, VersionInfo } from '../api/responses';

/**
 * Search and filter state for prompt list
 */
export interface SearchState {
  searchTerm: string;
  category: string;
  tag: string;
  favorites: boolean;
  caseSensitive: boolean;
  isLoading: boolean;
}

/**
 * Generic cache entry with timestamp for TTL
 */
export interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

/**
 * Tag autocomplete state
 */
export interface TagAutocompleteState {
  isOpen: boolean;
  suggestions: string[];
  selectedIndex: number;
  inputValue: string;
}

/**
 * Main application state (app.ts)
 */
export interface AppState {
  /** Cache of loaded prompts by ID */
  promptCache: Record<string, PromptResponse>;
  /** Last selected prompt ID for details view */
  lastSelectedPromptId: string | null;
  /** Set of selected prompt IDs for bulk operations */
  selectedPromptIds: Set<number>;
  /** Current search/filter state */
  searchState: SearchState;
  /** Cached version histories (TTL: 5 minutes) */
  versionCache: Record<string, CacheEntry<VersionInfo[]>>;
  /** Cached diff results (TTL: 5 minutes) */
  diffCache: Record<string, CacheEntry<unknown>>;
  /** Tag autocomplete state */
  tagAutocompleteState: TagAutocompleteState;
  /** Selected versions for comparison */
  selectedVersions: Set<string>;
}

/**
 * Admin users page state
 */
export interface AdminUsersState {
  currentPage: number;
  totalPages: number;
  currentFilters: {
    search: string;
    role: string;
    status: string;
  };
}

/**
 * Admin sessions page state
 */
export interface AdminSessionsState {
  allSessions: unknown[];
  currentFilters: {
    search: string;
    user: string;
  };
  currentSessionId: string | null;
}

/**
 * Backup management page state
 */
export interface BackupState {
  backups: unknown[];
  selectedBackupId: string | null;
  isLoading: boolean;
}

/**
 * Default search state values
 */
export const DEFAULT_SEARCH_STATE: SearchState = {
  searchTerm: '',
  category: 'all',
  tag: 'all',
  favorites: false,
  caseSensitive: false,
  isLoading: false,
};

/**
 * Cache duration in milliseconds (5 minutes)
 */
export const CACHE_DURATION = 5 * 60 * 1000;
```

---

### Task 1.5: Create Global Type Declarations

**File:** `/src/web/static/ts/types/globals.d.ts`

```typescript
import type { i18n } from 'i18next';

declare global {
  /**
   * FrontendLogger for error telemetry (defined in telemetry.ts)
   */
  interface Window {
    FrontendLogger: {
      reportError: (
        component: string,
        action: string,
        error: unknown,
        metadata?: Record<string, unknown>,
        severity?: 'error' | 'warning' | 'info'
      ) => void;
      enable: () => void;
      disable: () => void;
      isEnabled: () => boolean;
    };
  }

  /**
   * i18next loaded from CDN (until bundled)
   */
  const i18next: i18n;

  /**
   * i18next plugins loaded from CDN
   */
  const i18nextHttpBackend: {
    type: 'backend';
  };

  const i18nextBrowserLanguageDetector: {
    type: 'languageDetector';
  };
}

export {};
```

---

### Task 1.6: Create Validation Types

**File:** `/src/web/static/ts/types/validation.ts`

```typescript
import { ValidationState } from './api/enums';

/**
 * Result of a validation function
 */
export interface ValidationResult<T = string> {
  /** Whether the value is valid */
  valid: boolean;
  /** Error translation key if invalid, null if valid */
  error: string | null;
  /** Sanitized/normalized value */
  sanitized: T;
}

/**
 * Result of file validation
 */
export interface FileValidationResult {
  valid: boolean;
  error: string | null;
}

/**
 * Result of validating an entire form
 */
export interface FormValidationResult {
  valid: boolean;
  errors: Record<string, string>;
  sanitized: Record<string, unknown>;
}

/**
 * Password strength check results
 */
export interface PasswordStrengthCheck {
  length: boolean;
  uppercase: boolean;
  lowercase: boolean;
  digit: boolean;
  special: boolean;
}

/**
 * Password strength evaluation result
 */
export interface PasswordStrengthResult {
  /** Strength score 0-5 */
  strength: number;
  /** Individual check results */
  checks: PasswordStrengthCheck;
}

/**
 * Field validation state for UI
 */
export interface FieldValidationState {
  state: ValidationState;
  message: string | null;
  characterCount?: number;
  maxLength?: number;
}
```

---

### Task 1.7: Create Index File for Types

**File:** `/src/web/static/ts/types/index.ts`

```typescript
// API types
export * from './api/enums';
export * from './api/requests';
export * from './api/responses';

// State types
export * from './state/app-state';

// Validation types
export * from './validation';
```

---

## Phase 2: Utility Modules

### Task 2.1: Create DOM Utilities

**File:** `/src/web/static/ts/utils/dom.ts`

```typescript
/**
 * DOM manipulation utilities with type safety
 */

const HIDDEN_CLASS = 'is-hidden';
const ERROR_VISIBLE_CLASS = 'validation-error-visible';
const FIELD_ERROR_CLASS = 'field-error';
const FIELD_WARNING_CLASS = 'field-warning';
const FIELD_VALID_CLASS = 'field-valid';

/**
 * Show an element by removing the hidden class
 */
export function showElement(element: HTMLElement | null): void {
  element?.classList.remove(HIDDEN_CLASS);
}

/**
 * Hide an element by adding the hidden class
 */
export function hideElement(element: HTMLElement | null): void {
  element?.classList.add(HIDDEN_CLASS);
}

/**
 * Toggle element visibility based on condition
 */
export function toggleElement(element: HTMLElement | null, shouldShow: boolean): void {
  element?.classList.toggle(HIDDEN_CLASS, !shouldShow);
}

/**
 * Get element by ID with type assertion
 */
export function getElementById<T extends HTMLElement>(id: string): T | null {
  return document.getElementById(id) as T | null;
}

/**
 * Get required element by ID, throws if not found
 */
export function getRequiredElement<T extends HTMLElement>(id: string): T {
  const element = document.getElementById(id) as T | null;
  if (!element) {
    throw new Error(`Required element #${id} not found`);
  }
  return element;
}

/**
 * Query selector with type assertion
 */
export function querySelector<T extends Element>(selector: string, parent: ParentNode = document): T | null {
  return parent.querySelector(selector) as T | null;
}

/**
 * Query selector all with type assertion
 */
export function querySelectorAll<T extends Element>(selector: string, parent: ParentNode = document): NodeListOf<T> {
  return parent.querySelectorAll(selector) as NodeListOf<T>;
}

/**
 * Show validation error on an element
 */
export function showError(element: HTMLElement | null, message: string): void {
  if (element) {
    element.textContent = message;
    element.classList.add(ERROR_VISIBLE_CLASS);
  }
}

/**
 * Clear validation error from an element
 */
export function clearError(element: HTMLElement | null): void {
  if (element) {
    element.textContent = '';
    element.classList.remove(ERROR_VISIBLE_CLASS);
  }
}

/**
 * Clear all validation errors on the page
 */
export function clearAllErrors(): void {
  querySelectorAll<HTMLElement>('.validation-error').forEach((el) => {
    clearError(el);
  });
}

/**
 * Set field validation state classes
 */
export function setFieldState(
  field: HTMLElement | null,
  state: 'valid' | 'warning' | 'error' | 'pristine'
): void {
  if (!field) return;

  field.classList.remove(FIELD_ERROR_CLASS, FIELD_WARNING_CLASS, FIELD_VALID_CLASS);

  switch (state) {
    case 'valid':
      field.classList.add(FIELD_VALID_CLASS);
      break;
    case 'warning':
      field.classList.add(FIELD_WARNING_CLASS);
      break;
    case 'error':
      field.classList.add(FIELD_ERROR_CLASS);
      break;
    // 'pristine' - no class added
  }
}

/**
 * Escape HTML to prevent XSS
 */
export function escapeHtml(text: string): string {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Create element with attributes and children
 */
export function createElement<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attributes?: Record<string, string>,
  children?: (Node | string)[]
): HTMLElementTagNameMap[K] {
  const element = document.createElement(tag);

  if (attributes) {
    for (const [key, value] of Object.entries(attributes)) {
      element.setAttribute(key, value);
    }
  }

  if (children) {
    for (const child of children) {
      if (typeof child === 'string') {
        element.appendChild(document.createTextNode(child));
      } else {
        element.appendChild(child);
      }
    }
  }

  return element;
}

/**
 * Debounce function execution
 */
export function debounce<T extends (...args: unknown[]) => void>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  return (...args: Parameters<T>) => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    timeoutId = setTimeout(() => {
      fn(...args);
    }, delay);
  };
}
```

---

### Task 2.2: Create API Utilities

**File:** `/src/web/static/ts/utils/api.ts`

```typescript
/**
 * API request utilities with type safety
 */

import type { APIError } from '@/types/api/responses';

/**
 * Extended fetch options with timeout
 */
export interface FetchOptions extends RequestInit {
  timeout?: number;
}

/**
 * Custom error class for API request failures
 */
export class APIRequestError extends Error {
  public readonly status: number;
  public readonly error: APIError;

  constructor(status: number, error: APIError) {
    const message = typeof error.detail === 'string'
      ? error.detail
      : error.detail?.[0]?.msg ?? 'Request failed';
    super(message);
    this.name = 'APIRequestError';
    this.status = status;
    this.error = error;
  }

  /**
   * Check if error is an authentication error
   */
  isAuthError(): boolean {
    return this.status === 401;
  }

  /**
   * Check if error is a validation error
   */
  isValidationError(): boolean {
    return this.status === 422;
  }

  /**
   * Check if error is a not found error
   */
  isNotFoundError(): boolean {
    return this.status === 404;
  }

  /**
   * Check if error is a rate limit error
   */
  isRateLimitError(): boolean {
    return this.status === 429;
  }
}

/**
 * Type-safe fetch wrapper for JSON API calls
 */
export async function apiFetch<T>(
  url: string,
  options: FetchOptions = {}
): Promise<T> {
  const { timeout = 30000, ...fetchOptions } = options;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      credentials: 'include',
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...fetchOptions.headers,
      },
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let error: APIError;
      try {
        error = await response.json() as APIError;
      } catch {
        error = { detail: `HTTP ${response.status}: ${response.statusText}` };
      }
      throw new APIRequestError(response.status, error);
    }

    // Handle empty responses
    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
      return {} as T;
    }

    return await response.json() as T;
  } catch (error) {
    clearTimeout(timeoutId);

    if (error instanceof APIRequestError) {
      throw error;
    }

    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('Request timeout');
    }

    throw error;
  }
}

/**
 * GET request helper
 */
export function apiGet<T>(url: string, options?: FetchOptions): Promise<T> {
  return apiFetch<T>(url, { ...options, method: 'GET' });
}

/**
 * POST request helper
 */
export function apiPost<T>(url: string, body?: unknown, options?: FetchOptions): Promise<T> {
  return apiFetch<T>(url, {
    ...options,
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
  });
}

/**
 * PUT request helper
 */
export function apiPut<T>(url: string, body?: unknown, options?: FetchOptions): Promise<T> {
  return apiFetch<T>(url, {
    ...options,
    method: 'PUT',
    body: body ? JSON.stringify(body) : undefined,
  });
}

/**
 * DELETE request helper
 */
export function apiDelete<T>(url: string, body?: unknown, options?: FetchOptions): Promise<T> {
  return apiFetch<T>(url, {
    ...options,
    method: 'DELETE',
    body: body ? JSON.stringify(body) : undefined,
  });
}

/**
 * POST with FormData (for file uploads)
 */
export async function apiPostForm<T>(url: string, formData: FormData): Promise<T> {
  const response = await fetch(url, {
    method: 'POST',
    credentials: 'include',
    body: formData,
    // Don't set Content-Type - browser will set it with boundary
  });

  if (!response.ok) {
    let error: APIError;
    try {
      error = await response.json() as APIError;
    } catch {
      error = { detail: `HTTP ${response.status}: ${response.statusText}` };
    }
    throw new APIRequestError(response.status, error);
  }

  return await response.json() as T;
}

/**
 * Build URL with query parameters
 */
export function buildUrl(base: string, params: Record<string, string | number | boolean | undefined>): string {
  const url = new URL(base, window.location.origin);

  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') {
      url.searchParams.append(key, String(value));
    }
  }

  return url.toString();
}

/**
 * Handle API errors with user-friendly messages
 */
export function handleApiError(error: unknown, defaultMessage: string): string {
  if (error instanceof APIRequestError) {
    if (error.isAuthError()) {
      return i18next.t('auth.sessionExpired') || 'Session expired. Please log in again.';
    }
    if (error.isRateLimitError()) {
      return i18next.t('errors.rateLimit') || 'Too many requests. Please try again later.';
    }
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return defaultMessage;
}
```

---

### Task 2.3: Create i18n Utilities

**File:** `/src/web/static/ts/utils/i18n.ts`

```typescript
/**
 * i18next initialization and utilities
 */

type InitCallback = () => void;

/**
 * Update all elements with data-i18n attribute
 */
export function updateStaticTranslations(): void {
  // Handle data-i18n for text content and attributes
  document.querySelectorAll('[data-i18n]').forEach((element) => {
    const key = element.getAttribute('data-i18n');
    if (!key) return;

    // Handle attribute translations like [placeholder]key
    if (key.includes('[') && key.includes(']')) {
      const match = key.match(/\[(\w+)\](.+)/);
      if (match) {
        const [, attribute, translationKey] = match;
        const translation = i18next.t(translationKey);
        if (translation && attribute) {
          element.setAttribute(attribute, translation);
        }
      }
    } else {
      // Regular text content translation
      element.textContent = i18next.t(key);
    }
  });

  // Handle placeholder translations
  document.querySelectorAll('[data-i18n-placeholder]').forEach((element) => {
    const key = element.getAttribute('data-i18n-placeholder');
    if (key && element instanceof HTMLInputElement) {
      element.placeholder = i18next.t(key);
    }
  });

  // Handle title translations
  document.querySelectorAll('[data-i18n-title]').forEach((element) => {
    const key = element.getAttribute('data-i18n-title');
    if (key && element instanceof HTMLElement) {
      element.title = i18next.t(key);
    }
  });

  // Update language selector if present
  const languageSelector = document.getElementById('language-selector');
  if (languageSelector instanceof HTMLSelectElement) {
    languageSelector.value = i18next.language;
  }
}

/**
 * Initialize i18next with standard configuration
 */
export function initI18n(callback: InitCallback): void {
  i18next
    .use(i18nextHttpBackend)
    .use(i18nextBrowserLanguageDetector)
    .init(
      {
        fallbackLng: 'en',
        supportedLngs: ['en', 'fr', 'es', 'de'],
        debug: false,
        backend: {
          loadPath: '/static/locales/{{lng}}.json',
        },
        detection: {
          order: ['localStorage', 'navigator', 'htmlTag'],
          caches: ['localStorage'],
        },
      },
      (err: Error | null) => {
        if (err) {
          console.error('i18next initialization failed:', err);
        }

        if (document.readyState === 'loading') {
          document.addEventListener('DOMContentLoaded', callback);
        } else {
          callback();
        }
      }
    );
}

/**
 * Change the current language
 */
export function changeLanguage(lang: string): Promise<void> {
  return new Promise((resolve, reject) => {
    i18next.changeLanguage(lang, (err) => {
      if (err) {
        reject(err);
      } else {
        updateStaticTranslations();
        resolve();
      }
    });
  });
}

/**
 * Get current language
 */
export function getCurrentLanguage(): string {
  return i18next.language;
}

/**
 * Translate a key with optional interpolation
 */
export function t(key: string, options?: Record<string, unknown>): string {
  return i18next.t(key, options);
}
```

---

### Task 2.4: Create Notification Utilities

**File:** `/src/web/static/ts/utils/notifications.ts`

```typescript
/**
 * Notification and status message utilities
 */

export type NotificationType = 'info' | 'success' | 'warning' | 'error';

/**
 * Show a toast notification
 */
export function showNotification(
  message: string,
  type: NotificationType = 'info',
  duration: number = 5000
): void {
  // Remove any existing notification
  const existing = document.querySelector('.toast-notification');
  if (existing) {
    existing.remove();
  }

  const notification = document.createElement('div');
  notification.className = `toast-notification toast-${type}`;
  notification.textContent = message;
  notification.setAttribute('role', 'alert');
  notification.setAttribute('aria-live', 'polite');

  document.body.appendChild(notification);

  // Trigger animation
  requestAnimationFrame(() => {
    notification.classList.add('toast-visible');
  });

  // Auto-dismiss
  setTimeout(() => {
    notification.classList.remove('toast-visible');
    notification.addEventListener('transitionend', () => {
      notification.remove();
    });
  }, duration);
}

/**
 * Show a status message in a specific element
 */
export function showStatus(
  elementId: string,
  message: string,
  type: NotificationType = 'info'
): void {
  const element = document.getElementById(elementId);
  if (element) {
    element.textContent = message;
    element.className = `status status-${type}`;
    element.classList.remove('is-hidden');
  }
}

/**
 * Hide a status message element
 */
export function hideStatus(elementId: string): void {
  const element = document.getElementById(elementId);
  if (element) {
    element.classList.add('is-hidden');
  }
}

/**
 * Show loading indicator
 */
export function showLoading(elementId: string, message?: string): void {
  const element = document.getElementById(elementId);
  if (element) {
    element.innerHTML = `
      <span class="loading-spinner"></span>
      <span class="loading-text">${message || i18next.t('common.loading')}</span>
    `;
    element.classList.remove('is-hidden');
  }
}

/**
 * Confirm dialog wrapper with translation support
 */
export function confirmAction(messageKey: string, options?: Record<string, unknown>): boolean {
  const message = i18next.t(messageKey, options);
  return window.confirm(message);
}

/**
 * Report error to telemetry
 */
export function reportError(
  component: string,
  action: string,
  error: unknown,
  metadata?: Record<string, unknown>
): void {
  const logger = window.FrontendLogger;
  if (logger && typeof logger.reportError === 'function') {
    logger.reportError(component, action, error, metadata, 'error');
  }
  console.error(`[${component}] ${action}:`, error);
}

/**
 * Report warning to telemetry
 */
export function reportWarning(
  component: string,
  action: string,
  message: string,
  metadata?: Record<string, unknown>
): void {
  const logger = window.FrontendLogger;
  if (logger && typeof logger.reportError === 'function') {
    logger.reportError(component, action, new Error(message), metadata, 'warning');
  }
  console.warn(`[${component}] ${action}:`, message);
}
```

---

### Task 2.5: Create Utils Index

**File:** `/src/web/static/ts/utils/index.ts`

```typescript
export * from './dom';
export * from './api';
export * from './i18n';
export * from './notifications';
```

---

## Phase 3: Migrate Validation Modules

### Task 3.1: Migrate Validation Constants

**File:** `/src/web/static/ts/validation/constants.ts`

**Source:** `src/web/static/js/validation_constants.js`

```typescript
/**
 * Validation constants matching server-side Pydantic constraints
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0.
 */

// ============================================
// PROMPT FIELD CONSTRAINTS
// ============================================

export const MAX_TITLE_LENGTH = 200 as const;
export const MAX_PROMPT_LENGTH = 50000 as const;
export const MAX_CATEGORY_LENGTH = 100 as const;
export const MAX_TAG_LENGTH = 50 as const;
export const MAX_TAGS_COUNT = 50 as const;
export const MAX_NOTE_LENGTH = 2000 as const;
export const MAX_COMMIT_MESSAGE_LENGTH = 500 as const;

// ============================================
// AUTH FIELD CONSTRAINTS
// ============================================

export const MIN_USERNAME_LENGTH = 3 as const;
export const MAX_USERNAME_LENGTH = 32 as const;
export const MIN_PASSWORD_LENGTH = 12 as const;
export const MAX_PASSWORD_LENGTH = 128 as const;
export const MAX_EMAIL_LENGTH = 255 as const;
export const MAX_DISPLAY_NAME_LENGTH = 100 as const;

// ============================================
// BACKUP CONSTRAINTS
// ============================================

export const MAX_BACKUP_NAME_LENGTH = 64 as const;
export const MIN_RETENTION_DAYS = 1 as const;
export const MAX_RETENTION_DAYS = 3650 as const;
export const MIN_COMPRESS_DAYS = 1 as const;
export const MAX_COMPRESS_DAYS = 365 as const;

// ============================================
// BULK OPERATION CONSTRAINTS
// ============================================

export const MAX_BULK_DELETE_IDS = 1000 as const;

// ============================================
// FILE UPLOAD CONSTRAINTS
// ============================================

export const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024 as const; // 10 MB
export const MAX_FILE_SIZE_MB = 10 as const;

export const ALLOWED_IMPORT_MIME_TYPES = [
  'text/csv',
  'application/json',
  'text/markdown',
  'text/plain',
] as const;

export const ALLOWED_IMPORT_EXTENSIONS = [
  '.csv',
  '.json',
  '.md',
  '.txt',
] as const;

// ============================================
// PATTERNS
// ============================================

/** Username pattern: alphanumeric and underscore only */
export const USERNAME_PATTERN = /^[a-zA-Z0-9_]+$/;

/** Safe filename pattern: alphanumeric, underscore, hyphen */
export const SAFE_FILENAME_PATTERN = /^[a-zA-Z0-9_-]+$/;

/** Email pattern (simplified, server does full validation) */
export const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// ============================================
// UI THRESHOLDS
// ============================================

/** Character count warning threshold (percentage of max) */
export const CHAR_COUNT_WARNING_THRESHOLD = 0.9 as const;

/** Debounce delay for input validation (ms) */
export const VALIDATION_DEBOUNCE_MS = 300 as const;

// ============================================
// PASSWORD STRENGTH
// ============================================

export const PASSWORD_MIN_STRENGTH = 3 as const;
export const PASSWORD_SPECIAL_CHARS = '!@#$%^&*()_+-=[]{}|;:\'",.<>?/`~' as const;
```

---

### Task 3.2: Migrate Validators

**File:** `/src/web/static/ts/validation/validators.ts`

**Source:** `src/web/static/js/validators.js`

This is a large file. Key changes:

1. Add TypeScript types to all functions
2. Use `ValidationResult<T>` interface
3. Add proper null checks
4. Type the `File` parameter

```typescript
/**
 * Validation functions matching server-side Pydantic validators
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0.
 */

import type { ValidationResult, FileValidationResult, PasswordStrengthResult } from '@/types/validation';
import {
  MAX_TITLE_LENGTH,
  MAX_PROMPT_LENGTH,
  MAX_CATEGORY_LENGTH,
  MAX_TAG_LENGTH,
  MAX_TAGS_COUNT,
  MAX_NOTE_LENGTH,
  MAX_COMMIT_MESSAGE_LENGTH,
  MAX_BACKUP_NAME_LENGTH,
  MAX_BULK_DELETE_IDS,
  MAX_FILE_SIZE_BYTES,
  ALLOWED_IMPORT_MIME_TYPES,
  ALLOWED_IMPORT_EXTENSIONS,
  MIN_USERNAME_LENGTH,
  MAX_USERNAME_LENGTH,
  MIN_PASSWORD_LENGTH,
  MAX_PASSWORD_LENGTH,
  MAX_EMAIL_LENGTH,
  USERNAME_PATTERN,
  SAFE_FILENAME_PATTERN,
  EMAIL_PATTERN,
  PASSWORD_SPECIAL_CHARS,
} from './constants';

// ============================================
// STRING VALIDATORS
// ============================================

/**
 * Validate prompt title
 */
export function validateTitle(title: string, required = true): ValidationResult<string> {
  const trimmed = title.trim();

  if (!trimmed) {
    if (required) {
      return { valid: false, error: 'validation.titleRequired', sanitized: '' };
    }
    return { valid: true, error: null, sanitized: '' };
  }

  if (trimmed.length > MAX_TITLE_LENGTH) {
    return { valid: false, error: 'validation.titleTooLong', sanitized: trimmed };
  }

  return { valid: true, error: null, sanitized: trimmed };
}

/**
 * Validate prompt content
 */
export function validatePrompt(prompt: string, required = true): ValidationResult<string> {
  const trimmed = prompt.trim();

  if (!trimmed) {
    if (required) {
      return { valid: false, error: 'validation.promptRequired', sanitized: '' };
    }
    return { valid: true, error: null, sanitized: '' };
  }

  if (trimmed.length > MAX_PROMPT_LENGTH) {
    return { valid: false, error: 'validation.promptTooLong', sanitized: trimmed };
  }

  return { valid: true, error: null, sanitized: trimmed };
}

/**
 * Validate category
 */
export function validateCategory(category: string): ValidationResult<string> {
  const trimmed = category.trim();

  if (trimmed.length > MAX_CATEGORY_LENGTH) {
    return { valid: false, error: 'validation.categoryTooLong', sanitized: trimmed };
  }

  return { valid: true, error: null, sanitized: trimmed };
}

/**
 * Validate tags (comma-separated string)
 */
export function validateTags(tags: string): ValidationResult<string[]> {
  if (!tags.trim()) {
    return { valid: true, error: null, sanitized: [] };
  }

  const tagArray = tags
    .split(',')
    .map(t => t.trim())
    .filter(t => t.length > 0);

  // Remove duplicates
  const uniqueTags = [...new Set(tagArray)];

  if (uniqueTags.length > MAX_TAGS_COUNT) {
    return { valid: false, error: 'validation.tooManyTags', sanitized: uniqueTags };
  }

  for (const tag of uniqueTags) {
    if (tag.length > MAX_TAG_LENGTH) {
      return { valid: false, error: 'validation.tagTooLong', sanitized: uniqueTags };
    }
  }

  return { valid: true, error: null, sanitized: uniqueTags };
}

/**
 * Validate note
 */
export function validateNote(note: string): ValidationResult<string> {
  const trimmed = note.trim();

  if (trimmed.length > MAX_NOTE_LENGTH) {
    return { valid: false, error: 'validation.noteTooLong', sanitized: trimmed };
  }

  return { valid: true, error: null, sanitized: trimmed };
}

/**
 * Validate commit message
 */
export function validateCommitMessage(message: string, required = true): ValidationResult<string> {
  const trimmed = message.trim();

  if (!trimmed) {
    if (required) {
      return { valid: false, error: 'validation.commitMessageRequired', sanitized: '' };
    }
    return { valid: true, error: null, sanitized: '' };
  }

  if (trimmed.length > MAX_COMMIT_MESSAGE_LENGTH) {
    return { valid: false, error: 'validation.commitMessageTooLong', sanitized: trimmed };
  }

  return { valid: true, error: null, sanitized: trimmed };
}

/**
 * Validate backup name
 */
export function validateBackupName(name: string): ValidationResult<string> {
  const trimmed = name.trim();

  if (!trimmed) {
    return { valid: true, error: null, sanitized: '' };
  }

  if (trimmed.length > MAX_BACKUP_NAME_LENGTH) {
    return { valid: false, error: 'validation.backupNameTooLong', sanitized: trimmed };
  }

  if (!SAFE_FILENAME_PATTERN.test(trimmed)) {
    return { valid: false, error: 'validation.backupNameInvalidChars', sanitized: trimmed };
  }

  return { valid: true, error: null, sanitized: trimmed };
}

// ============================================
// AUTH VALIDATORS
// ============================================

/**
 * Validate username
 */
export function validateUsername(username: string): ValidationResult<string> {
  const trimmed = username.trim();

  if (!trimmed) {
    return { valid: false, error: 'validation.usernameRequired', sanitized: '' };
  }

  if (trimmed.length < MIN_USERNAME_LENGTH) {
    return { valid: false, error: 'validation.usernameTooShort', sanitized: trimmed };
  }

  if (trimmed.length > MAX_USERNAME_LENGTH) {
    return { valid: false, error: 'validation.usernameTooLong', sanitized: trimmed };
  }

  if (!USERNAME_PATTERN.test(trimmed)) {
    return { valid: false, error: 'validation.usernameInvalidChars', sanitized: trimmed };
  }

  return { valid: true, error: null, sanitized: trimmed };
}

/**
 * Validate email
 */
export function validateEmail(email: string): ValidationResult<string> {
  const trimmed = email.trim().toLowerCase();

  if (!trimmed) {
    return { valid: false, error: 'validation.emailRequired', sanitized: '' };
  }

  if (trimmed.length > MAX_EMAIL_LENGTH) {
    return { valid: false, error: 'validation.emailTooLong', sanitized: trimmed };
  }

  if (!EMAIL_PATTERN.test(trimmed)) {
    return { valid: false, error: 'validation.emailInvalid', sanitized: trimmed };
  }

  return { valid: true, error: null, sanitized: trimmed };
}

/**
 * Validate password
 */
export function validatePassword(password: string): ValidationResult<string> {
  if (!password) {
    return { valid: false, error: 'validation.passwordRequired', sanitized: '' };
  }

  if (password.length < MIN_PASSWORD_LENGTH) {
    return { valid: false, error: 'validation.passwordTooShort', sanitized: password };
  }

  if (password.length > MAX_PASSWORD_LENGTH) {
    return { valid: false, error: 'validation.passwordTooLong', sanitized: password };
  }

  return { valid: true, error: null, sanitized: password };
}

/**
 * Validate password confirmation matches
 */
export function validatePasswordMatch(password: string, confirmPassword: string): ValidationResult<string> {
  if (!confirmPassword) {
    return { valid: false, error: 'validation.confirmPasswordRequired', sanitized: '' };
  }

  if (password !== confirmPassword) {
    return { valid: false, error: 'validation.passwordsDoNotMatch', sanitized: confirmPassword };
  }

  return { valid: true, error: null, sanitized: confirmPassword };
}

/**
 * Calculate password strength
 */
export function calculatePasswordStrength(password: string): PasswordStrengthResult {
  const checks = {
    length: password.length >= MIN_PASSWORD_LENGTH,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    digit: /[0-9]/.test(password),
    special: new RegExp(`[${PASSWORD_SPECIAL_CHARS.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}]`).test(password),
  };

  const strength = Object.values(checks).filter(Boolean).length;

  return { strength, checks };
}

// ============================================
// ARRAY VALIDATORS
// ============================================

/**
 * Validate bulk delete prompt IDs
 */
export function validateBulkDeleteIds(ids: number[]): ValidationResult<number[]> {
  if (!Array.isArray(ids)) {
    return { valid: false, error: 'validation.invalidIdArray', sanitized: [] };
  }

  if (ids.length === 0) {
    return { valid: false, error: 'validation.noIdsSelected', sanitized: [] };
  }

  if (ids.length > MAX_BULK_DELETE_IDS) {
    return { valid: false, error: 'validation.tooManyIds', sanitized: ids };
  }

  // Check for duplicates
  const uniqueIds = [...new Set(ids)];
  if (uniqueIds.length !== ids.length) {
    return { valid: false, error: 'validation.duplicateIds', sanitized: uniqueIds };
  }

  // Check all are positive integers
  for (const id of ids) {
    if (!Number.isInteger(id) || id <= 0) {
      return { valid: false, error: 'validation.invalidId', sanitized: ids };
    }
  }

  return { valid: true, error: null, sanitized: ids };
}

// ============================================
// FILE VALIDATORS
// ============================================

/**
 * Validate file for import
 */
export function validateFileUpload(file: File | null | undefined): FileValidationResult {
  if (!file) {
    return { valid: false, error: 'validation.fileRequired' };
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    return { valid: false, error: 'validation.fileTooLarge' };
  }

  // Check MIME type
  const mimeType = file.type.toLowerCase();
  const mimeValid = ALLOWED_IMPORT_MIME_TYPES.some(allowed => mimeType === allowed || mimeType.startsWith(allowed));

  // Check extension
  const fileName = file.name.toLowerCase();
  const extValid = ALLOWED_IMPORT_EXTENSIONS.some(ext => fileName.endsWith(ext));

  if (!mimeValid && !extValid) {
    return { valid: false, error: 'validation.invalidFileType' };
  }

  return { valid: true, error: null };
}

// ============================================
// NUMERIC VALIDATORS
// ============================================

/**
 * Validate retention days for backup cleanup
 */
export function validateRetentionDays(days: number): ValidationResult<number> {
  if (!Number.isInteger(days)) {
    return { valid: false, error: 'validation.mustBeInteger', sanitized: days };
  }

  if (days < 1 || days > 3650) {
    return { valid: false, error: 'validation.retentionDaysOutOfRange', sanitized: days };
  }

  return { valid: true, error: null, sanitized: days };
}

/**
 * Validate compress threshold days
 */
export function validateCompressDays(days: number): ValidationResult<number> {
  if (!Number.isInteger(days)) {
    return { valid: false, error: 'validation.mustBeInteger', sanitized: days };
  }

  if (days < 1 || days > 365) {
    return { valid: false, error: 'validation.compressDaysOutOfRange', sanitized: days };
  }

  return { valid: true, error: null, sanitized: days };
}
```

---

### Task 3.3: Create Validation Index

**File:** `/src/web/static/ts/validation/index.ts`

```typescript
export * from './constants';
export * from './validators';
```

---

## Phase 4: Page Entry Points (Completed)

All page entry points have been fully migrated to TypeScript and are now live.

### Task 4.1: Create Telemetry Entry Point

**File:** `/src/web/static/ts/telemetry.ts`

```typescript
/**
 * Frontend telemetry and error reporting
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0.
 */

import type { FrontendLogEntry } from '@/types';

const TELEMETRY_ENDPOINT = '/api/logs/frontend';
const MAX_REPORTS_PER_MINUTE = 10;
const REPORT_INTERVAL_MS = 60000;

interface TelemetryState {
  enabled: boolean;
  reportCount: number;
  lastResetTime: number;
}

const state: TelemetryState = {
  enabled: true,
  reportCount: 0,
  lastResetTime: Date.now(),
};

/**
 * Check if telemetry is opted out via localStorage
 */
function isOptedOut(): boolean {
  try {
    return localStorage.getItem('promptvault.telemetry.optOut') === 'true';
  } catch {
    return false;
  }
}

/**
 * Reset rate limit counter if interval has passed
 */
function checkRateLimit(): boolean {
  const now = Date.now();
  if (now - state.lastResetTime >= REPORT_INTERVAL_MS) {
    state.reportCount = 0;
    state.lastResetTime = now;
  }
  return state.reportCount < MAX_REPORTS_PER_MINUTE;
}

/**
 * Serialize error for transmission
 */
function serializeError(error: unknown): { message: string; stack?: string } {
  if (error instanceof Error) {
    return {
      message: error.message.slice(0, 500),
      stack: error.stack?.slice(0, 2000),
    };
  }
  if (typeof error === 'string') {
    return { message: error.slice(0, 500) };
  }
  return { message: String(error).slice(0, 500) };
}

/**
 * Send error report to server
 */
async function sendReport(entry: FrontendLogEntry): Promise<void> {
  try {
    // Use sendBeacon for reliability during page unload
    if (navigator.sendBeacon) {
      navigator.sendBeacon(
        TELEMETRY_ENDPOINT,
        JSON.stringify(entry)
      );
    } else {
      await fetch(TELEMETRY_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(entry),
        credentials: 'include',
      });
    }
  } catch {
    // Silently fail - don't cause more errors
  }
}

/**
 * Report an error to telemetry
 */
function reportError(
  component: string,
  action: string,
  error: unknown,
  metadata: Record<string, unknown> = {},
  severity: 'error' | 'warning' | 'info' = 'error'
): void {
  // Always log to console
  const logFn = severity === 'error' ? console.error : console.warn;
  logFn(`[${component}] ${action}:`, error, metadata);

  // Check if reporting is enabled
  if (!state.enabled || isOptedOut()) {
    return;
  }

  // Check rate limit
  if (!checkRateLimit()) {
    return;
  }

  state.reportCount++;

  const serialized = serializeError(error);
  const entry: FrontendLogEntry = {
    component: component.slice(0, 100),
    action: action.slice(0, 100),
    message: serialized.message,
    severity,
    stack: serialized.stack,
    url: window.location.href.slice(0, 500),
    context: metadata,
  };

  void sendReport(entry);
}

/**
 * Enable telemetry reporting
 */
function enable(): void {
  state.enabled = true;
  try {
    localStorage.removeItem('promptvault.telemetry.optOut');
  } catch {
    // Ignore storage errors
  }
}

/**
 * Disable telemetry reporting
 */
function disable(): void {
  state.enabled = false;
  try {
    localStorage.setItem('promptvault.telemetry.optOut', 'true');
  } catch {
    // Ignore storage errors
  }
}

/**
 * Check if telemetry is enabled
 */
function isEnabled(): boolean {
  return state.enabled && !isOptedOut();
}

// Expose globally
window.FrontendLogger = {
  reportError,
  enable,
  disable,
  isEnabled,
};

// Set up global error handler
window.addEventListener('error', (event) => {
  reportError('window', 'unhandledError', event.error || event.message, {
    filename: event.filename,
    lineno: event.lineno,
    colno: event.colno,
  });
});

// Set up unhandled promise rejection handler
window.addEventListener('unhandledrejection', (event) => {
  reportError('window', 'unhandledRejection', event.reason);
});

export { reportError, enable, disable, isEnabled };
```

---

### Task 4.2-4.9: Migrate Pages

Completed migrations:

- `src/web/static/ts/password-reset.ts`
- `src/web/static/ts/admin-sessions.ts`
- `src/web/static/ts/profile.ts`
- `src/web/static/ts/auth.ts`
- `src/web/static/ts/backup-management.ts`
- `src/web/static/ts/import-export.ts`
- `src/web/static/ts/admin-users.ts`
- `src/web/static/ts/app.ts`

---

## Phase 5: Dockerfile Update

### Task 5.1: Update Dockerfile

**File:** `/Dockerfile`

```dockerfile
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# ============================================
# Stage 1: Build frontend assets
# ============================================
FROM node:20-slim AS frontend-builder

WORKDIR /app

# Copy package files for dependency installation
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts

# Copy TypeScript and Vite configuration
COPY tsconfig.json vite.config.ts ./

# Copy source files
COPY src/web/static/ ./src/web/static/

# Build frontend (TypeScript → JavaScript, bundled with Vite)
RUN npm run build

# ============================================
# Stage 2: Python application
# ============================================
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including PostgreSQL client
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy the application code
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Copy built frontend assets from builder stage
COPY --from=frontend-builder /app/dist/static/ ./src/web/static/dist/

# Copy Vite manifest for template rendering
COPY --from=frontend-builder /app/dist/static/.vite/manifest.json ./src/web/static/manifest.json

# Keep original JS files for backward compatibility during migration
# (Remove this line once migration is complete)
# COPY src/web/static/js/ ./src/web/static/js/

# Create data directory and set permissions
RUN mkdir -p data/logs data/backups && \
    adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run the application
CMD ["python", "run_web.py"]
```

---

## Phase 6: FastAPI Integration

### Task 6.1: Create Manifest Loader

**File:** `/src/web/utils/manifest.py`

```python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Vite manifest loader for production builds."""

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

# Path to Vite manifest file
MANIFEST_PATH = Path(__file__).parent.parent / "static" / "manifest.json"
DIST_PATH = Path(__file__).parent.parent / "static" / "dist"


@lru_cache(maxsize=1)
def load_manifest() -> dict[str, Any]:
    """Load Vite manifest file for production builds.

    Returns:
        Dict mapping entry points to their built file paths.
        Empty dict if manifest doesn't exist (development mode).
    """
    if not MANIFEST_PATH.exists():
        return {}

    try:
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def get_asset_path(entry: str) -> str:
    """Get the hashed asset path for a given entry point.

    Args:
        entry: Entry point name (e.g., 'ts/app.ts')

    Returns:
        Built file path with hash, or original entry if not found.
    """
    manifest = load_manifest()
    if entry in manifest:
        return manifest[entry].get("file", entry)
    return entry


def is_production() -> bool:
    """Check if running in production mode (built assets exist)."""
    return DIST_PATH.exists() and MANIFEST_PATH.exists()


def clear_manifest_cache() -> None:
    """Clear the cached manifest (useful for hot reload)."""
    load_manifest.cache_clear()
```

---

### Task 6.2: Update app.py Template Configuration

**File:** `/src/web/app.py`

Add to the imports and template setup:

```python
# Add import
from src.web.utils.manifest import load_manifest, get_asset_path, is_production

# Update template configuration (find the Jinja2Templates setup)
templates = Jinja2Templates(directory="src/web/templates")

# Add globals for template access
templates.env.globals["load_manifest"] = load_manifest
templates.env.globals["get_asset_path"] = get_asset_path
templates.env.globals["is_production"] = is_production
templates.env.globals["is_dev"] = lambda: os.getenv("ENV", "production") == "development"
```

---

### Task 6.3: Create Base Template Macro

**File:** `/src/web/templates/macros/scripts.html`

```html
{% macro load_scripts(entry_name, include_telemetry=true) %}
{% if is_dev() %}
    {# Development mode - load from Vite dev server #}
    <script type="module" src="http://localhost:5173/@vite/client"></script>
    {% if include_telemetry %}
    <script type="module" src="http://localhost:5173/ts/telemetry.ts"></script>
    {% endif %}
    <script type="module" src="http://localhost:5173/ts/{{ entry_name }}.ts"></script>
{% else %}
    {# Production mode - load built files #}
    {% set manifest = load_manifest() %}
    {% if include_telemetry and 'ts/telemetry.ts' in manifest %}
    <script type="module" src="/static/dist/{{ manifest['ts/telemetry.ts']['file'] }}"></script>
    {% endif %}
    {% if 'ts/' + entry_name + '.ts' in manifest %}
    <script type="module" src="/static/dist/{{ manifest['ts/' + entry_name + '.ts']['file'] }}"></script>
    {% else %}
    {# Fallback to original JS during migration #}
    <script src="/static/js/{{ entry_name }}.js" defer></script>
    {% endif %}
{% endif %}
{% endmacro %}
```

---

## Verification Checklist

After each phase, verify:

- [ ] `npm run typecheck` - No TypeScript errors
- [ ] `npm run build` - Vite build succeeds
- [ ] `npm run dev` - Dev server starts and proxies work
- [ ] `python run_web.py` - FastAPI serves the app
- [ ] Manual testing of affected pages
- [ ] Playwright tests pass (`npm run test:ui`)

---

## Migration Order Summary

1. **Phase 0**: package.json, tsconfig.json, vite.config.ts, directory structure
2. **Phase 1**: Type definitions (enums, requests, responses, state, globals)
3. **Phase 2**: Utility modules (dom, api, i18n, notifications)
4. **Phase 3**: Validation modules (constants, validators)
5. **Phase 4**: Page entry points (telemetry first, then by complexity)
6. **Phase 5**: Dockerfile multi-stage build
7. **Phase 6**: FastAPI manifest integration

---

## Files Modified/Created Summary

### New Files

- `tsconfig.json`
- `vite.config.ts`
- `src/web/static/ts/types/api/enums.ts`
- `src/web/static/ts/types/api/requests.ts`
- `src/web/static/ts/types/api/responses.ts`
- `src/web/static/ts/types/state/app-state.ts`
- `src/web/static/ts/types/validation.ts`
- `src/web/static/ts/types/globals.d.ts`
- `src/web/static/ts/types/index.ts`
- `src/web/static/ts/utils/dom.ts`
- `src/web/static/ts/utils/api.ts`
- `src/web/static/ts/utils/i18n.ts`
- `src/web/static/ts/utils/notifications.ts`
- `src/web/static/ts/utils/index.ts`
- `src/web/static/ts/validation/constants.ts`
- `src/web/static/ts/validation/validators.ts`
- `src/web/static/ts/validation/index.ts`
- `src/web/static/ts/telemetry.ts`
- `src/web/static/ts/app.ts` (stub, then full migration)
- `src/web/static/ts/auth.ts` (stub, then full migration)
- `src/web/static/ts/profile.ts` (stub, then full migration)
- `src/web/static/ts/password-reset.ts` (stub, then full migration)
- `src/web/static/ts/admin-users.ts` (stub, then full migration)
- `src/web/static/ts/admin-sessions.ts` (stub, then full migration)
- `src/web/static/ts/import-export.ts` (stub, then full migration)
- `src/web/static/ts/backup-management.ts` (stub, then full migration)
- `src/web/utils/manifest.py`
- `src/web/templates/macros/scripts.html`

### Modified Files

- `package.json` - Add dependencies and scripts
- `.gitignore` - Add dist/, *.tsbuildinfo
- `Dockerfile` - Add Node.js build stage
- `src/web/app.py` - Add manifest loader to templates
- All HTML templates - Update script loading (Phase 5)
