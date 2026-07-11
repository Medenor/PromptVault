/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import 'fake-indexeddb/auto';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('i18next', () => ({
  default: {
    t: vi.fn((key: string) => `tr:${key}`),
  },
}));

import { addQueueEntry, listQueueEntries, removeQueueEntry } from '@/utils/offline-queue';
import { syncOfflineQueue } from '../offline-sync';

async function clearAllEntries(): Promise<void> {
  const entries = await listQueueEntries();
  await Promise.all(entries.map((entry) => removeQueueEntry(entry.id)));
}

function mockFetchResponse(status: number, body: unknown = {}): void {
  globalThis.fetch = vi.fn().mockResolvedValue({
    status,
    ok: status >= 200 && status < 300,
    json: () => Promise.resolve(body),
  }) as unknown as typeof fetch;
}

describe('syncOfflineQueue', () => {
  beforeEach(async () => {
    await clearAllEntries();
    document.body.innerHTML = '';
  });

  afterEach(async () => {
    await clearAllEntries();
    vi.restoreAllMocks();
  });

  it('does nothing when the queue is empty', async () => {
    mockFetchResponse(200, { success: true });
    await syncOfflineQueue();
    expect(fetch).not.toHaveBeenCalled();
  });

  it('replays a pending create entry and removes it on success', async () => {
    await addQueueEntry({ operation: 'create', payload: { title: 'New', prompt: 'Body' } });
    mockFetchResponse(201, { success: true, prompt_id: 5 });

    await syncOfflineQueue();

    expect(fetch).toHaveBeenCalledWith('/api/prompts', expect.objectContaining({ method: 'POST' }));
    const remaining = await listQueueEntries();
    expect(remaining).toHaveLength(0);
  });

  it('replays a pending update entry with expected_version and removes it on success', async () => {
    await addQueueEntry({
      operation: 'update',
      promptId: '9',
      baseVersion: 2,
      payload: { title: 'Edited' },
    });
    mockFetchResponse(200, { success: true });

    await syncOfflineQueue();

    expect(fetch).toHaveBeenCalledWith(
      '/api/prompts/9',
      expect.objectContaining({ method: 'PUT' })
    );
    const [, options] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit];
    const formData = options.body as FormData;
    expect(formData.get('expected_version')).toBe('2');

    const remaining = await listQueueEntries();
    expect(remaining).toHaveLength(0);
  });

  it('marks an entry as conflict on 409 and does not remove it', async () => {
    await addQueueEntry({
      operation: 'update',
      promptId: '9',
      baseVersion: 1,
      payload: { title: 'Stale' },
    });
    mockFetchResponse(409, {
      error: 'version_conflict',
      current_version: 3,
      current_prompt: {},
    });

    await syncOfflineQueue();

    const remaining = await listQueueEntries();
    expect(remaining).toHaveLength(1);
    expect(remaining[0]?.status).toBe('conflict');
  });

  it('leaves an entry pending on a non-network failure (e.g. validation error)', async () => {
    await addQueueEntry({ operation: 'create', payload: { title: '' } });
    mockFetchResponse(422, { detail: 'Validation failed' });

    await syncOfflineQueue();

    const remaining = await listQueueEntries();
    expect(remaining).toHaveLength(1);
    expect(remaining[0]?.status).toBe('pending');
  });

  it('leaves an entry pending on a network failure', async () => {
    await addQueueEntry({ operation: 'create', payload: { title: 'Retry me' } });
    globalThis.fetch = vi
      .fn()
      .mockRejectedValue(new Error('network down')) as unknown as typeof fetch;

    await syncOfflineQueue();

    const remaining = await listQueueEntries();
    expect(remaining).toHaveLength(1);
    expect(remaining[0]?.status).toBe('pending');
  });

  it('replays multiple pending entries in order', async () => {
    await addQueueEntry({ operation: 'create', payload: { title: 'First' } });
    await new Promise((resolve) => setTimeout(resolve, 5));
    await addQueueEntry({ operation: 'create', payload: { title: 'Second' } });
    mockFetchResponse(201, { success: true });

    await syncOfflineQueue();

    expect(fetch).toHaveBeenCalledTimes(2);
    const remaining = await listQueueEntries();
    expect(remaining).toHaveLength(0);
  });
});
