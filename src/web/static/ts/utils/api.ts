/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * API request utilities with type safety
 */

import i18next from 'i18next';

import type { APIError, TokenResponse } from '@/types';

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

  constructor(status: number, error: APIError) {
    const message =
      typeof error.detail === 'string'
        ? error.detail
        : (error.detail?.[0]?.msg ?? 'Request failed');
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
 * Clear all stored tokens and redirect to login
 */
function clearTokensAndRedirect(): void {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  sessionStorage.removeItem('access_token');
  sessionStorage.removeItem('refresh_token');

  // Only redirect if not already on auth page
  if (!window.location.pathname.includes('/auth/')) {
    window.location.href = '/auth/login';
  }
}

/**
 * Refresh access token using the stored refresh token
 * @returns Promise<boolean> - true if refresh succeeded, false otherwise
 */
async function refreshTokens(): Promise<boolean> {
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
