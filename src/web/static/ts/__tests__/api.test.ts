import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

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
} from '@/utils/api';

describe('api utils', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
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

    (globalThis.fetch as unknown as vi.Mock).mockResolvedValue(response);

    const result = await apiFetch<{ value: number }>('/api/test');
    expect(result.value).toBe(42);
  });

  it('supports helper methods and error predicates', async () => {
    const response = {
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: vi.fn().mockResolvedValue({ status: 'ok' }),
    };

    const fetchMock = globalThis.fetch as unknown as vi.Mock;
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

    (globalThis.fetch as unknown as vi.Mock).mockResolvedValue(response);

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

    (globalThis.fetch as unknown as vi.Mock).mockResolvedValue(response);

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

    (globalThis.fetch as unknown as vi.Mock).mockResolvedValue(response);

    await expect(apiFetch('/api/test')).rejects.toThrow('HTTP 500: Server Error');
  });

  it('times out when fetch aborts', async () => {
    vi.useFakeTimers();

    (globalThis.fetch as unknown as vi.Mock).mockImplementation(
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

    (globalThis.fetch as unknown as vi.Mock).mockResolvedValue(response);

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

    (globalThis.fetch as unknown as vi.Mock).mockResolvedValue(response);

    const formData = new FormData();
    await expect(apiPostForm('/api/upload', formData)).rejects.toBeInstanceOf(APIRequestError);
  });
});
