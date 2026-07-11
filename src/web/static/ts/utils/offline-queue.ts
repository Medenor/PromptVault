/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * IndexedDB-backed offline write queue (FR-011), per data-model.md's
 * OfflineQueueEntry: persists queued create/edit operations made while offline
 * so they survive reloads until synced.
 */

const DB_NAME = 'promptvault-offline-queue';
const DB_VERSION = 1;
const STORE_NAME = 'queue';

export type QueueOperation = 'create' | 'update';
export type QueueStatus = 'pending' | 'syncing' | 'synced' | 'conflict';

export interface OfflineQueueEntry {
  id: string;
  promptId: string | null;
  operation: QueueOperation;
  payload: Record<string, unknown>;
  baseVersion: number | null;
  timestamp: number;
  status: QueueStatus;
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'id' });
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

function runTransaction<T>(
  mode: IDBTransactionMode,
  action: (store: IDBObjectStore) => IDBRequest<T>
): Promise<T> {
  return openDb().then(
    (db) =>
      new Promise<T>((resolve, reject) => {
        const tx = db.transaction(STORE_NAME, mode);
        const store = tx.objectStore(STORE_NAME);
        const request = action(store);

        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      })
  );
}

function generateEntryId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

/**
 * Adds a new queued operation. `operation: 'update'` requires promptId; baseVersion
 * is the version the client last saw, or null when unknown (e.g. the editor
 * couldn't fetch it) — a null baseVersion means the sync replay omits
 * `expected_version` and no conflict check is requested, matching the backend
 * contract's backward-compatible behavior for non-offline clients.
 */
export async function addQueueEntry(
  entry:
    | { operation: 'create'; promptId?: null; payload: Record<string, unknown> }
    | {
        operation: 'update';
        promptId: string;
        baseVersion: number | null;
        payload: Record<string, unknown>;
      }
): Promise<OfflineQueueEntry> {
  const fullEntry: OfflineQueueEntry = {
    id: generateEntryId(),
    promptId: entry.operation === 'update' ? entry.promptId : null,
    operation: entry.operation,
    payload: entry.payload,
    baseVersion: entry.operation === 'update' ? entry.baseVersion : null,
    timestamp: Date.now(),
    status: 'pending',
  };

  await runTransaction('readwrite', (store) => store.add(fullEntry));
  return fullEntry;
}

export async function listQueueEntries(): Promise<OfflineQueueEntry[]> {
  const entries = await runTransaction<OfflineQueueEntry[]>('readonly', (store) => store.getAll());
  return entries.sort((a, b) => a.timestamp - b.timestamp);
}

export async function listPendingQueueEntries(): Promise<OfflineQueueEntry[]> {
  const entries = await listQueueEntries();
  return entries.filter((entry) => entry.status === 'pending');
}

/**
 * Updates a queue entry's status. Enforces the forward-only transition rule
 * from data-model.md: pending -> syncing -> (synced | conflict). A conflict
 * entry may be retried by resetting it to 'pending' with an updated baseVersion.
 */
export async function updateQueueEntryStatus(
  id: string,
  status: QueueStatus,
  updates?: Partial<Pick<OfflineQueueEntry, 'baseVersion'>>
): Promise<void> {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const getRequest = store.get(id);

    getRequest.onsuccess = () => {
      const entry = getRequest.result as OfflineQueueEntry | undefined;
      if (!entry) {
        resolve();
        return;
      }
      entry.status = status;
      if (updates?.baseVersion !== undefined) {
        entry.baseVersion = updates.baseVersion;
      }
      const putRequest = store.put(entry);
      putRequest.onsuccess = () => resolve();
      putRequest.onerror = () => reject(putRequest.error);
    };
    getRequest.onerror = () => reject(getRequest.error);
  });
}

export async function removeQueueEntry(id: string): Promise<void> {
  await runTransaction('readwrite', (store) => store.delete(id));
}

export async function getQueueEntryCount(): Promise<number> {
  const entries = await listQueueEntries();
  return entries.length;
}
