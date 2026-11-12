/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * API request utilities with type safety
 */

import i18next from 'i18next';

import type {
  APIError,
  PromptResponse,
  ShareListResponse,
  ShareResponse,
  TokenResponse,
  UserSearchResponse,
} from '@/types';
import { t } from '@/utils/i18n';
import { showNotification } from '@/utils/notifications';

/** Cap on how long a single automatic backoff-retry will wait, in seconds. */
const MAX_RETRY_AFTER_SECONDS = 30;

/**
 * Extended fetch options with timeout
 */
export interface FetchOptions extends RequestInit {
  timeout?: number;
  /** Internal flag to prevent infinite retry loops */
  _isRetry?: boolean;
}

/**
 * Custom error class for API request failures
 */
export class APIRequestError extends Error {
  public readonly status: number;
  public readonly error: APIError;
  /** Seconds to wait before retrying, parsed from the Retry-After header (429 only). */
  public readonly retryAfter?: number;

  constructor(status: number, error: APIError, retryAfter?: number) {
    const message =
      typeof error.detail === 'string'
        ? error.detail
        : (error.detail?.[0]?.msg ?? error.error ?? 'Request failed');
    super(message);
    this.name = 'APIRequestError';
    this.status = status;
    this.error = error;
    if (retryAfter !== undefined) {
      this.retryAfter = retryAfter;
    }
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
 * Get stored refresh token from localStorage or sessionStorage
 */
function getRefreshToken(): string | null {
  return localStorage.getItem('refresh_token') || sessionStorage.getItem('refresh_token');
}

/**
 * Update stored tokens (access and refresh) in the appropriate storage
 */
function updateStoredTokens(accessToken: string, refreshToken: string): void {
  // Store in the same location as the current refresh token
  if (localStorage.getItem('refresh_token')) {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
  } else if (sessionStorage.getItem('refresh_token')) {
    sessionStorage.setItem('access_token', accessToken);
    sessionStorage.setItem('refresh_token', refreshToken);
  } else {
    // Default to sessionStorage if no existing tokens
    sessionStorage.setItem('access_token', accessToken);
    sessionStorage.setItem('refresh_token', refreshToken);
  }
}

/**
 * Clear all stored access/refresh tokens (localStorage and sessionStorage).
 */
export function clearStoredTokens(): void {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  sessionStorage.removeItem('access_token');
  sessionStorage.removeItem('refresh_token');
}

/**
 * Clear all stored tokens and redirect to login
 */
function clearTokensAndRedirect(): void {
  clearStoredTokens();

  // Only redirect if not already on auth page
  if (!window.location.pathname.includes('/auth/')) {
    window.location.href = '/auth/login';
  }
}

/**
 * Parse the Retry-After header (delta-seconds form) into a number of seconds.
 * Returns undefined when the header is absent or not a non-negative integer.
 */
function parseRetryAfter(response: Response): number | undefined {
  const raw = response.headers.get('Retry-After');
  if (!raw) {
    return undefined;
  }
  const seconds = Number.parseInt(raw, 10);
  return Number.isFinite(seconds) && seconds >= 0 ? seconds : undefined;
}

/**
 * Surface a rate-limit (429) to the user via a warning toast, including the
 * wait time when known. Kept i18n-ready so callers don't duplicate the string.
 */
function notifyRateLimited(retryAfter?: number): void {
  const message =
    retryAfter && retryAfter > 0
      ? t('messages.rateLimit', { seconds: retryAfter })
      : t('messages.rateLimitGeneric');
  showNotification(message, 'warning');
}

/**
 * Sleep for the given number of milliseconds.
 */
function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Refresh access token using the stored refresh token
 * @returns Promise<boolean> - true if refresh succeeded, false otherwise
 */
export async function refreshTokens(): Promise<boolean> {
  const refreshToken = getRefreshToken();

  if (!refreshToken) {
    return false;
  }

  try {
    const response = await fetch('/api/auth/refresh', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      return false;
    }

    const data = (await response.json()) as TokenResponse;

    if (!data.access_token || !data.refresh_token) {
      return false;
    }

    updateStoredTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

/**
 * Response header set by the server when admin policy requires the user to
 * enroll in 2FA before using the app (see enforce_totp_enrollment_policy).
 */
const TOTP_ENROLLMENT_REQUIRED_HEADER = 'X-TOTP-Enrollment-Required';
const TOTP_ENROLLMENT_PATH = '/auth/profile';

/**
 * Send a user whose role requires 2FA (but who has not enrolled) to the
 * profile page, where the enrollment card is reachable, instead of leaving
 * them on a page whose data requests all fail with 403 (FR-015).
 */
function redirectIfEnrollmentRequired(response: Response): void {
  if (
    response.status === 403 &&
    response.headers.get(TOTP_ENROLLMENT_REQUIRED_HEADER) === 'true' &&
    !window.location.pathname.startsWith(TOTP_ENROLLMENT_PATH)
  ) {
    window.location.assign(TOTP_ENROLLMENT_PATH);
  }
}

/**
 * Type-safe fetch wrapper for JSON API calls with automatic token refresh
 */
export async function apiFetch<T>(url: string, options: FetchOptions = {}): Promise<T> {
  const { timeout = 30000, _isRetry = false, ...fetchOptions } = options;

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
        error = (await response.json()) as APIError;
      } catch {
        error = { detail: `HTTP ${response.status}: ${response.statusText}` };
      }

      // Handle 401 with automatic token refresh
      if (response.status === 401 && !_isRetry && !url.includes('/api/auth/refresh')) {
        // Try to refresh the token
        const refreshSuccess = await refreshTokens();

        if (refreshSuccess) {
          // Retry the original request with new token
          return apiFetch<T>(url, { ...options, _isRetry: true });
        } else {
          // Refresh failed - clear tokens and redirect to login
          clearTokensAndRedirect();
          throw new APIRequestError(response.status, error);
        }
      }

      redirectIfEnrollmentRequired(response);

      // Handle 429 rate limiting: for idempotent GETs, back off once and retry;
      // for mutations, surface a toast and let the caller handle the failure
      // (never auto-retry a write — it could duplicate the mutation).
      if (response.status === 429) {
        const retryAfter = parseRetryAfter(response);
        const isGet = (fetchOptions.method ?? 'GET').toUpperCase() === 'GET';

        if (
          isGet &&
          !_isRetry &&
          retryAfter !== undefined &&
          retryAfter <= MAX_RETRY_AFTER_SECONDS
        ) {
          await delay(retryAfter * 1000);
          return apiFetch<T>(url, { ...options, _isRetry: true });
        }

        notifyRateLimited(retryAfter);
        throw new APIRequestError(response.status, error, retryAfter);
      }

      throw new APIRequestError(response.status, error);
    }

    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
      return {} as T;
    }

    return (await response.json()) as T;
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
    body: body ? JSON.stringify(body) : null,
  });
}

/**
 * PUT request helper
 */
export function apiPut<T>(url: string, body?: unknown, options?: FetchOptions): Promise<T> {
  return apiFetch<T>(url, {
    ...options,
    method: 'PUT',
    body: body ? JSON.stringify(body) : null,
  });
}

/**
 * DELETE request helper
 */
export function apiDelete<T>(url: string, body?: unknown, options?: FetchOptions): Promise<T> {
  return apiFetch<T>(url, {
    ...options,
    method: 'DELETE',
    body: body ? JSON.stringify(body) : null,
  });
}

/**
 * PATCH request helper
 */
export function apiPatch<T>(url: string, body?: unknown, options?: FetchOptions): Promise<T> {
  return apiFetch<T>(url, {
    ...options,
    method: 'PATCH',
    body: body ? JSON.stringify(body) : null,
  });
}

/**
 * POST with FormData (for file uploads) with automatic token refresh
 */
export async function apiPostForm<T>(
  url: string,
  formData: FormData,
  _isRetry = false
): Promise<T> {
  const response = await fetch(url, {
    method: 'POST',
    credentials: 'include',
    body: formData,
  });

  if (!response.ok) {
    let error: APIError;
    try {
      error = (await response.json()) as APIError;
    } catch {
      error = { detail: `HTTP ${response.status}: ${response.statusText}` };
    }

    // Handle 401 with automatic token refresh
    if (response.status === 401 && !_isRetry && !url.includes('/api/auth/refresh')) {
      const refreshSuccess = await refreshTokens();

      if (refreshSuccess) {
        // Retry the original request with new token
        return apiPostForm<T>(url, formData, true);
      } else {
        // Refresh failed - clear tokens and redirect to login
        clearTokensAndRedirect();
        throw new APIRequestError(response.status, error);
      }
    }

    redirectIfEnrollmentRequired(response);

    // Handle 429 rate limiting: form posts are always mutations (imports,
    // uploads), so never auto-retry — toast and throw with the wait time.
    if (response.status === 429) {
      const retryAfter = parseRetryAfter(response);
      notifyRateLimited(retryAfter);
      throw new APIRequestError(response.status, error, retryAfter);
    }

    throw new APIRequestError(response.status, error);
  }

  return (await response.json()) as T;
}

/**
 * Build URL with query parameters
 */
export function buildUrl(
  base: string,
  params: Record<string, string | number | boolean | undefined>
): string {
  const url = new URL(base, window.location.origin);

  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') {
      url.searchParams.append(key, String(value));
    }
  }

  return url.toString();
}

/**
 * Grant (or update) a share on a prompt.
 * POST /api/prompts/{promptId}/shares
 *
 * Resolves to a 201 (new grant) or 200 (existing grant updated) body — both
 * share the same `ShareResponse` shape. Callers should show a generic
 * failure message on error (no user enumeration, contracts §1).
 */
export function grantShare(
  promptId: number,
  identifier: string,
  permission: 'read' | 'edit'
): Promise<ShareResponse> {
  return apiPost<ShareResponse>(`/api/prompts/${promptId}/shares`, { identifier, permission });
}

/**
 * Typeahead search for active users by username or email prefix.
 * GET /api/users/search?q=<prefix>
 *
 * `query` must be at least 2 characters (enforced server-side, 400 otherwise).
 */
export function searchUsers(query: string): Promise<UserSearchResponse> {
  return apiGet<UserSearchResponse>(`/api/users/search?q=${encodeURIComponent(query)}`);
}

/**
 * List a prompt's share grants (grant review, US3).
 * GET /api/prompts/{promptId}/shares
 *
 * Owner/admin only — a grantee gets 403, a stranger gets 404.
 */
export function listShares(promptId: number): Promise<ShareListResponse> {
  return apiGet<ShareListResponse>(`/api/prompts/${promptId}/shares`);
}

/**
 * Revoke a grantee's access to a prompt (US3).
 * DELETE /api/prompts/{promptId}/shares/{userId}
 *
 * Access ends immediately.
 */
export function revokeShare(promptId: number, userId: string): Promise<{ message: string }> {
  return apiDelete<{ message: string }>(`/api/prompts/${promptId}/shares/${userId}`);
}

/**
 * Un-grandfather a legacy-public prompt (US3).
 * PATCH /api/prompts/{promptId} { legacy_public: false }
 *
 * One-way — there is no path back to `legacy_public: true`. Creates no
 * share rows; a user who could previously view the prompt only via
 * `legacy_public` loses that access immediately.
 */
export function unGrandfatherPrompt(promptId: number): Promise<PromptResponse> {
  return apiPatch<PromptResponse>(`/api/prompts/${promptId}`, { legacy_public: false });
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
      return error.retryAfter && error.retryAfter > 0
        ? t('messages.rateLimit', { seconds: error.retryAfter })
        : t('messages.rateLimitGeneric');
    }
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return defaultMessage;
}
