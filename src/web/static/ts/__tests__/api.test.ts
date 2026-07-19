import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from 'vitest';

vi.mock('i18next', () => ({
  default: {
    t: vi.fn((key: string) => key),
  },
}));

import {
  apiDelete,
  apiFetch,
  apiGet,
  apiPost,
  apiPostForm,
  apiPut,
  APIRequestError,
  buildUrl,
  handleApiError,
} from '@/utils/api';

describe('api utils', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
    // Mock window.location
    delete (window as unknown as Record<string, unknown>).location;
    (window as unknown as Record<string, unknown>).location = {
      href: '',
      pathname: '/app',
      origin: 'http://localhost',
    };

    const createStorage = () => {
      const store = new Map<string, string>();
      return {
        getItem: (key: string) => store.get(key) ?? null,
        setItem: (key: string, value: string) => {
          store.set(key, value);
        },
        removeItem: (key: string) => {
          store.delete(key);
        },
        clear: () => {
          store.clear();
        },
      };
    };

    vi.stubGlobal('localStorage', createStorage());
    vi.stubGlobal('sessionStorage', createStorage());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('returns JSON payload for ok responses', async () => {
    const response = {
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: vi.fn().mockResolvedValue({ value: 42 }),
    };

    (globalThis.fetch as unknown as Mock).mockResolvedValue(response);

    const result = await apiFetch<{ value: number }>('/api/test');
    expect(result.value).toBe(42);
  });

  it('supports helper methods and error predicates', async () => {
    const response = {
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: vi.fn().mockResolvedValue({ status: 'ok' }),
    };

    const fetchMock = globalThis.fetch as unknown as Mock;
    fetchMock.mockResolvedValue(response);

    const getResult = await apiGet<{ status: string }>('/api/test');
    const postResult = await apiPost<{ status: string }>('/api/test', { a: 1 });
    const putResult = await apiPut<{ status: string }>('/api/test', { a: 2 });
    const deleteResult = await apiDelete<{ status: string }>('/api/test', { a: 3 });

    expect(getResult.status).toBe('ok');
    expect(postResult.status).toBe('ok');
    expect(putResult.status).toBe('ok');
    expect(deleteResult.status).toBe('ok');

    const apiError = new APIRequestError(401, { detail: 'Unauthorized' });
    expect(apiError.isAuthError()).toBe(true);
    expect(apiError.isValidationError()).toBe(false);
    expect(apiError.isNotFoundError()).toBe(false);
    expect(apiError.isRateLimitError()).toBe(false);
    expect(new APIRequestError(404, { detail: 'Missing' }).isNotFoundError()).toBe(true);
    expect(new APIRequestError(429, { detail: 'Too many' }).isRateLimitError()).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith('/api/test', expect.objectContaining({ method: 'GET' }));
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/test',
      expect.objectContaining({ method: 'POST' })
    );
    expect(fetchMock).toHaveBeenCalledWith('/api/test', expect.objectContaining({ method: 'PUT' }));
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/test',
      expect.objectContaining({ method: 'DELETE' })
    );
  });

  it('returns empty object for non-json responses', async () => {
    const response = {
      ok: true,
      headers: new Headers({ 'content-type': 'text/plain' }),
      json: vi.fn(),
    };

    (globalThis.fetch as unknown as Mock).mockResolvedValue(response);

    const result = await apiFetch<Record<string, never>>('/api/test');
    expect(result).toEqual({});
    expect(response.json).not.toHaveBeenCalled();
  });

  it('throws APIRequestError for bad responses', async () => {
    const response = {
      ok: false,
      status: 422,
      statusText: 'Unprocessable Entity',
      headers: new Headers({ 'content-type': 'application/json' }),
      json: vi.fn().mockResolvedValue({ detail: [{ msg: 'Validation failed' }] }),
    };

    (globalThis.fetch as unknown as Mock).mockResolvedValue(response);

    await expect(apiFetch('/api/test')).rejects.toBeInstanceOf(APIRequestError);
    await expect(apiFetch('/api/test')).rejects.toMatchObject({ status: 422 });

    try {
      await apiFetch('/api/test');
    } catch (error) {
      expect(error).toBeInstanceOf(APIRequestError);
      const apiError = error as APIRequestError;
      expect(apiError.isValidationError()).toBe(true);
    }
  });

  it('uses status text when error payload is not JSON', async () => {
    const response = {
      ok: false,
      status: 500,
      statusText: 'Server Error',
      headers: new Headers({ 'content-type': 'application/json' }),
      json: vi.fn().mockRejectedValue(new Error('bad json')),
    };

    (globalThis.fetch as unknown as Mock).mockResolvedValue(response);

    await expect(apiFetch('/api/test')).rejects.toThrow('HTTP 500: Server Error');
  });

  it('times out when fetch aborts', async () => {
    vi.useFakeTimers();

    (globalThis.fetch as unknown as Mock).mockImplementation(
      (_url: string, init?: RequestInit) =>
        new Promise((_resolve, reject) => {
          init?.signal?.addEventListener('abort', () => {
            const abortError = new Error('Aborted');
            abortError.name = 'AbortError';
            reject(abortError);
          });
        })
    );

    const promise = apiFetch('/api/test', { timeout: 5 });
    const expectation = expect(promise).rejects.toThrow('Request timeout');

    await vi.advanceTimersByTimeAsync(5);
    await expectation;

    vi.useRealTimers();
  });

  it('posts form data and parses JSON', async () => {
    const response = {
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: vi.fn().mockResolvedValue({ uploaded: true }),
    };

    (globalThis.fetch as unknown as Mock).mockResolvedValue(response);

    const formData = new FormData();
    formData.append('file', new Blob(['data']), 'file.txt');

    const result = await apiPostForm<{ uploaded: boolean }>('/api/upload', formData);
    expect(result.uploaded).toBe(true);
  });

  it('throws APIRequestError for form data failures', async () => {
    const response = {
      ok: false,
      status: 400,
      statusText: 'Bad Request',
      headers: new Headers({ 'content-type': 'application/json' }),
      json: vi.fn().mockResolvedValue({ detail: 'Invalid form' }),
    };

    (globalThis.fetch as unknown as Mock).mockResolvedValue(response);

    const formData = new FormData();
    await expect(apiPostForm('/api/upload', formData)).rejects.toBeInstanceOf(APIRequestError);
  });

  it('uses status text for form data failures when error payload is not JSON', async () => {
    const response = {
      ok: false,
      status: 500,
      statusText: 'Server Error',
      headers: new Headers({ 'content-type': 'application/json' }),
      json: vi.fn().mockRejectedValue(new Error('bad json')),
    };

    (globalThis.fetch as unknown as Mock).mockResolvedValue(response);

    const formData = new FormData();
    await expect(apiPostForm('/api/upload', formData)).rejects.toThrow('HTTP 500: Server Error');
  });

  it('redirects to login when refresh fails for apiPostForm on 401', async () => {
    localStorage.setItem('refresh_token', 'invalid_refresh_token');

    const fetchMock = globalThis.fetch as unknown as Mock;

    const unauthorizedResponse = {
      ok: false,
      status: 401,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: vi.fn().mockResolvedValue({ detail: 'Unauthorized' }),
    };

    const refreshFailedResponse = {
      ok: false,
      status: 401,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: vi.fn().mockResolvedValue({ detail: 'Invalid refresh token' }),
    };

    fetchMock
      .mockResolvedValueOnce(unauthorizedResponse)
      .mockResolvedValueOnce(refreshFailedResponse);

    const formData = new FormData();
    await expect(apiPostForm('/api/upload', formData)).rejects.toBeInstanceOf(APIRequestError);

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(window.location.href).toBe('/auth/login');
  });

  describe('automatic token refresh', () => {
    it('automatically refreshes token on 401 and retries request', async () => {
      localStorage.setItem('refresh_token', 'old_refresh_token');

      const fetchMock = globalThis.fetch as unknown as Mock;

      // First call returns 401
      const unauthorizedResponse = {
        ok: false,
        status: 401,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: vi.fn().mockResolvedValue({ detail: 'Unauthorized' }),
      };

      // Second call is refresh token request - returns new tokens
      const refreshResponse = {
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: vi.fn().mockResolvedValue({
          access_token: 'new_access_token',
          refresh_token: 'new_refresh_token',
          token_type: 'Bearer',
          expires_in: 900,
        }),
      };

      // Third call is retry of original request - returns success
      const successResponse = {
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: vi.fn().mockResolvedValue({ data: 'success' }),
      };

      fetchMock
        .mockResolvedValueOnce(unauthorizedResponse)
        .mockResolvedValueOnce(refreshResponse)
        .mockResolvedValueOnce(successResponse);

      const result = await apiFetch<{ data: string }>('/api/test');

      expect(result.data).toBe('success');
      expect(fetchMock).toHaveBeenCalledTimes(3);
      expect(fetchMock).toHaveBeenNthCalledWith(
        2,
        '/api/auth/refresh',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ refresh_token: 'old_refresh_token' }),
        })
      );
      expect(localStorage.getItem('access_token')).toBe('new_access_token');
      expect(localStorage.getItem('refresh_token')).toBe('new_refresh_token');
    });

    it('redirects to login when refresh token is invalid', async () => {
      localStorage.setItem('refresh_token', 'invalid_refresh_token');

      const fetchMock = globalThis.fetch as unknown as Mock;

      // First call returns 401
      const unauthorizedResponse = {
        ok: false,
        status: 401,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: vi.fn().mockResolvedValue({ detail: 'Unauthorized' }),
      };

      // Refresh token request fails
      const refreshFailedResponse = {
        ok: false,
        status: 401,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: vi.fn().mockResolvedValue({ detail: 'Invalid refresh token' }),
      };

      fetchMock
        .mockResolvedValueOnce(unauthorizedResponse)
        .mockResolvedValueOnce(refreshFailedResponse);

      await expect(apiFetch('/api/test')).rejects.toBeInstanceOf(APIRequestError);

      expect(fetchMock).toHaveBeenCalledTimes(2);
      expect(localStorage.getItem('access_token')).toBeNull();
      expect(localStorage.getItem('refresh_token')).toBeNull();
      expect(window.location.href).toBe('/auth/login');
    });

    it('does not refresh when already on auth page', async () => {
      window.location.pathname = '/auth/login';
      localStorage.setItem('refresh_token', 'refresh_token');

      const fetchMock = globalThis.fetch as unknown as Mock;

      const unauthorizedResponse = {
        ok: false,
        status: 401,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: vi.fn().mockResolvedValue({ detail: 'Unauthorized' }),
      };

      const refreshFailedResponse = {
        ok: false,
        status: 401,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: vi.fn().mockResolvedValue({ detail: 'Invalid refresh token' }),
      };

      fetchMock
        .mockResolvedValueOnce(unauthorizedResponse)
        .mockResolvedValueOnce(refreshFailedResponse);

      await expect(apiFetch('/api/test')).rejects.toBeInstanceOf(APIRequestError);

      // Should clear tokens but not redirect
      expect(localStorage.getItem('refresh_token')).toBeNull();
      expect(window.location.href).toBe(''); // unchanged
    });

    it('does not attempt refresh for /api/auth/refresh endpoint', async () => {
      localStorage.setItem('refresh_token', 'refresh_token');

      const fetchMock = globalThis.fetch as unknown as Mock;

      const unauthorizedResponse = {
        ok: false,
        status: 401,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: vi.fn().mockResolvedValue({ detail: 'Invalid refresh token' }),
      };

      fetchMock.mockResolvedValueOnce(unauthorizedResponse);

      await expect(apiFetch('/api/auth/refresh')).rejects.toBeInstanceOf(APIRequestError);

      // Should only call fetch once, no retry
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });

    it('does not retry more than once', async () => {
      localStorage.setItem('refresh_token', 'refresh_token');

      const fetchMock = globalThis.fetch as unknown as Mock;

      const unauthorizedResponse = {
        ok: false,
        status: 401,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: vi.fn().mockResolvedValue({ detail: 'Unauthorized' }),
      };

      const refreshResponse = {
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: vi.fn().mockResolvedValue({
          access_token: 'new_access_token',
          refresh_token: 'new_refresh_token',
          token_type: 'Bearer',
          expires_in: 900,
        }),
      };

      // Mock: original request fails, refresh succeeds, retry fails
      fetchMock
        .mockResolvedValueOnce(unauthorizedResponse)
        .mockResolvedValueOnce(refreshResponse)
        .mockResolvedValueOnce(unauthorizedResponse);

      await expect(apiFetch('/api/test')).rejects.toBeInstanceOf(APIRequestError);

      // Should only try 3 times: original + refresh + retry
      expect(fetchMock).toHaveBeenCalledTimes(3);
    });

    it('handles token refresh in sessionStorage', async () => {
      sessionStorage.setItem('refresh_token', 'session_refresh_token');

      const fetchMock = globalThis.fetch as unknown as Mock;

      const unauthorizedResponse = {
        ok: false,
        status: 401,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: vi.fn().mockResolvedValue({ detail: 'Unauthorized' }),
      };

      const refreshResponse = {
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: vi.fn().mockResolvedValue({
          access_token: 'new_access_token',
          refresh_token: 'new_refresh_token',
          token_type: 'Bearer',
          expires_in: 900,
        }),
      };

      const successResponse = {
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: vi.fn().mockResolvedValue({ data: 'success' }),
      };

      fetchMock
        .mockResolvedValueOnce(unauthorizedResponse)
        .mockResolvedValueOnce(refreshResponse)
        .mockResolvedValueOnce(successResponse);

      const result = await apiFetch<{ data: string }>('/api/test');

      expect(result.data).toBe('success');
      expect(sessionStorage.getItem('access_token')).toBe('new_access_token');
      expect(sessionStorage.getItem('refresh_token')).toBe('new_refresh_token');
      expect(localStorage.getItem('access_token')).toBeNull();
      expect(localStorage.getItem('refresh_token')).toBeNull();
    });

    it('refreshes tokens for apiPostForm on 401', async () => {
      localStorage.setItem('refresh_token', 'refresh_token');

      const fetchMock = globalThis.fetch as unknown as Mock;

      const unauthorizedResponse = {
        ok: false,
        status: 401,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: vi.fn().mockResolvedValue({ detail: 'Unauthorized' }),
      };

      const refreshResponse = {
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: vi.fn().mockResolvedValue({
          access_token: 'new_access_token',
          refresh_token: 'new_refresh_token',
          token_type: 'Bearer',
          expires_in: 900,
        }),
      };

      const successResponse = {
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: vi.fn().mockResolvedValue({ uploaded: true }),
      };

      fetchMock
        .mockResolvedValueOnce(unauthorizedResponse)
        .mockResolvedValueOnce(refreshResponse)
        .mockResolvedValueOnce(successResponse);

      const formData = new FormData();
      formData.append('file', new Blob(['data']), 'file.txt');

      const result = await apiPostForm<{ uploaded: boolean }>('/api/upload', formData);

      expect(result.uploaded).toBe(true);
      expect(fetchMock).toHaveBeenCalledTimes(3);
    });
  });

  describe('buildUrl', () => {
    it('appends only defined, non-empty params', () => {
      const url = buildUrl('/api/prompts', {
        page: 2,
        search: '',
        active: true,
        missing: undefined,
      });

      expect(url).toContain('page=2');
      expect(url).toContain('active=true');
      expect(url).not.toContain('search=');
      expect(url).not.toContain('missing');
    });
  });

  describe('handleApiError', () => {
    it('returns the session-expired message for auth errors', () => {
      const error = new APIRequestError(401, { detail: 'Unauthorized' });
      expect(handleApiError(error, 'default')).toBe('auth.sessionExpired');
    });

    it('returns the rate-limit message for rate limit errors', () => {
      const error = new APIRequestError(429, { detail: 'Too many' });
      expect(handleApiError(error, 'default')).toBe('errors.rateLimit');
    });

    it('returns the error message for other APIRequestError statuses', () => {
      const error = new APIRequestError(422, { detail: 'Invalid' });
      expect(handleApiError(error, 'default')).toBe('Invalid');
    });

    it('returns the message for a plain Error', () => {
      expect(handleApiError(new Error('boom'), 'default')).toBe('boom');
    });

    it('returns the default message for unknown error shapes', () => {
      expect(handleApiError('not an error', 'default')).toBe('default');
    });
  });
});
