/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Offline queue sync replay (FR-011, FR-012), per
 * specs/004-mobile-responsive-ui/contracts/offline-sync.md:
 *
 * On reconnect, replays each pending OfflineQueueEntry in timestamp order against
 * the existing prompt create/update endpoints. Update replays send `expected_version`
 * so the server can detect a conflicting concurrent edit (409) instead of silently
 * overwriting it.
 */

import { t } from '@/utils/i18n';
import { showNotification } from '@/utils/notifications';
import {
  listPendingQueueEntries,
  removeQueueEntry,
  updateQueueEntryStatus,
  type OfflineQueueEntry,
} from '@/utils/offline-queue';

function toFormData(payload: Record<string, unknown>): FormData {
  const formData = new FormData();
  for (const [key, value] of Object.entries(payload)) {
    if (value !== undefined && value !== null) {
      formData.append(key, String(value));
    }
  }
  return formData;
}

async function replayCreate(entry: OfflineQueueEntry): Promise<Response> {
  return fetch('/api/prompts', {
    method: 'POST',
    credentials: 'include',
    body: toFormData(entry.payload),
  });
}

async function replayUpdate(entry: OfflineQueueEntry): Promise<Response> {
  const formData = toFormData(entry.payload);
  if (entry.baseVersion !== null) {
    formData.append('expected_version', String(entry.baseVersion));
  }
  return fetch(`/api/prompts/${entry.promptId}`, {
    method: 'PUT',
    credentials: 'include',
    body: formData,
  });
}

let isSyncing = false;

/**
 * Replays all pending queue entries in timestamp order. Safe to call repeatedly
 * (e.g. on every `online` event) — a concurrent call is a no-op while one is in flight.
 */
export async function syncOfflineQueue(): Promise<void> {
  if (isSyncing) return;
  isSyncing = true;

  try {
    const pending = await listPendingQueueEntries();
    if (pending.length === 0) return;

    let syncedCount = 0;

    for (const entry of pending) {
      await updateQueueEntryStatus(entry.id, 'syncing');

      try {
        const response =
          entry.operation === 'create' ? await replayCreate(entry) : await replayUpdate(entry);

        if (response.status === 409) {
          await updateQueueEntryStatus(entry.id, 'conflict');
          showNotification(t('offline.syncConflict'), 'warning', 8000);
          continue;
        }

        if (!response.ok) {
          // Non-network failure (validation, auth, etc.) — leave pending for a
          // later retry rather than silently dropping the queued change.
          await updateQueueEntryStatus(entry.id, 'pending');
          continue;
        }

        await updateQueueEntryStatus(entry.id, 'synced');
        await removeQueueEntry(entry.id);
        syncedCount += 1;
      } catch {
        // Network failure mid-replay: leave pending, retry on the next online event.
        await updateQueueEntryStatus(entry.id, 'pending');
      }
    }

    if (syncedCount > 0) {
      showNotification(t('offline.synced'), 'success');
    }
  } finally {
    isSyncing = false;
  }
}
