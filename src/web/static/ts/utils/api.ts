/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * API request utilities with type safety
 */

import i18next from 'i18next';

import type { APIError } from '@/types';

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
 * Type-safe fetch wrapper for JSON API calls
 */
export async function apiFetch<T>(url: string, options: FetchOptions = {}): Promise<T> {
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
        error = (await response.json()) as APIError;
      } catch {
        error = { detail: `HTTP ${response.status}: ${response.statusText}` };
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
 * POST with FormData (for file uploads)
 */
export async function apiPostForm<T>(url: string, formData: FormData): Promise<T> {
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
