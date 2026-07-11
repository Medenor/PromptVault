/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import 'fake-indexeddb/auto';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import {
  addQueueEntry,
  getQueueEntryCount,
  listPendingQueueEntries,
  listQueueEntries,
  removeQueueEntry,
  updateQueueEntryStatus,
} from '../offline-queue';

async function clearAllEntries(): Promise<void> {
  const entries = await listQueueEntries();
  await Promise.all(entries.map((entry) => removeQueueEntry(entry.id)));
}

describe('offline-queue', () => {
  beforeEach(async () => {
    await clearAllEntries();
  });

  afterEach(async () => {
    await clearAllEntries();
  });

  it('adds a create entry with promptId/baseVersion null and status pending', async () => {
    const entry = await addQueueEntry({
      operation: 'create',
      payload: { title: 'New prompt', prompt: 'Body' },
    });

    expect(entry.operation).toBe('create');
    expect(entry.promptId).toBeNull();
    expect(entry.baseVersion).toBeNull();
    expect(entry.status).toBe('pending');
    expect(entry.id).toBeTruthy();
    expect(entry.timestamp).toBeGreaterThan(0);
  });

  it('adds an update entry with promptId and baseVersion set', async () => {
    const entry = await addQueueEntry({
      operation: 'update',
      promptId: '42',
      baseVersion: 3,
      payload: { title: 'Edited' },
    });

    expect(entry.operation).toBe('update');
    expect(entry.promptId).toBe('42');
    expect(entry.baseVersion).toBe(3);
    expect(entry.status).toBe('pending');
  });

  it('lists entries ordered by timestamp ascending', async () => {
    const first = await addQueueEntry({ operation: 'create', payload: { title: 'First' } });
    await new Promise((resolve) => setTimeout(resolve, 5));
    const second = await addQueueEntry({ operation: 'create', payload: { title: 'Second' } });

    const entries = await listQueueEntries();
    const ids = entries.map((e) => e.id);
    expect(ids.indexOf(first.id)).toBeLessThan(ids.indexOf(second.id));
  });

  it('lists only pending entries via listPendingQueueEntries', async () => {
    const pendingEntry = await addQueueEntry({
      operation: 'create',
      payload: { title: 'Pending' },
    });
    const syncedEntry = await addQueueEntry({
      operation: 'create',
      payload: { title: 'Will be synced' },
    });
    await updateQueueEntryStatus(syncedEntry.id, 'synced');

    const pending = await listPendingQueueEntries();
    const ids = pending.map((e) => e.id);
    expect(ids).toContain(pendingEntry.id);
    expect(ids).not.toContain(syncedEntry.id);
  });

  it('transitions status pending -> syncing -> synced', async () => {
    const entry = await addQueueEntry({ operation: 'create', payload: { title: 'X' } });

    await updateQueueEntryStatus(entry.id, 'syncing');
    let [current] = (await listQueueEntries()).filter((e) => e.id === entry.id);
    expect(current?.status).toBe('syncing');

    await updateQueueEntryStatus(entry.id, 'synced');
    [current] = (await listQueueEntries()).filter((e) => e.id === entry.id);
    expect(current?.status).toBe('synced');
  });

  it('transitions status to conflict and allows retry back to pending with updated baseVersion', async () => {
    const entry = await addQueueEntry({
      operation: 'update',
      promptId: '7',
      baseVersion: 1,
      payload: { title: 'Conflicted' },
    });

    await updateQueueEntryStatus(entry.id, 'conflict');
    let [current] = (await listQueueEntries()).filter((e) => e.id === entry.id);
    expect(current?.status).toBe('conflict');

    await updateQueueEntryStatus(entry.id, 'pending', { baseVersion: 2 });
    [current] = (await listQueueEntries()).filter((e) => e.id === entry.id);
    expect(current?.status).toBe('pending');
    expect(current?.baseVersion).toBe(2);
  });

  it('removes an entry', async () => {
    const entry = await addQueueEntry({ operation: 'create', payload: { title: 'Remove me' } });
    expect(await getQueueEntryCount()).toBeGreaterThanOrEqual(1);

    await removeQueueEntry(entry.id);

    const entries = await listQueueEntries();
    expect(entries.find((e) => e.id === entry.id)).toBeUndefined();
  });

  it('updateQueueEntryStatus is a no-op for a non-existent id', async () => {
    await expect(updateQueueEntryStatus('does-not-exist', 'synced')).resolves.toBeUndefined();
  });

  it('reports an accurate entry count', async () => {
    expect(await getQueueEntryCount()).toBe(0);
    await addQueueEntry({ operation: 'create', payload: { title: 'One' } });
    await addQueueEntry({ operation: 'create', payload: { title: 'Two' } });
    expect(await getQueueEntryCount()).toBe(2);
  });
});
