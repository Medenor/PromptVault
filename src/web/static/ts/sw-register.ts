/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Service Worker registration and offline/online state wiring (FR-009, FR-010).
 * Registration failures (unsupported browser, storage quota, etc.) are caught and
 * logged — the app must keep working online-only without the offline features.
 */

import { t } from '@/utils/i18n';

export function registerServiceWorker(): void {
  if (!navigator.serviceWorker) {
    return;
  }

  navigator.serviceWorker.register('/sw.js').catch((error: unknown) => {
    console.warn(
      '[sw-register] Service Worker registration failed; continuing online-only.',
      error
    );
  });
}

function getOfflineIndicator(): HTMLElement | null {
  return document.getElementById('offline-indicator');
}

export function updateOfflineIndicator(isOffline: boolean): void {
  const indicator = getOfflineIndicator();
  if (!indicator) return;

  if (isOffline) {
    indicator.classList.remove('hidden');
    indicator.textContent = t('offline.indicator');
  } else {
    indicator.classList.add('hidden');
  }
}

export function isOffline(): boolean {
  return !navigator.onLine;
}

/** How long to wait for the service worker's cache-cleared ack before giving up. */
const CLEAR_CACHE_ACK_TIMEOUT_MS = 500;

/**
 * Clears data cached for offline use so it can't leak across users on a shared
 * device: tells the active service worker to drop its cached prompt API
 * responses (API_CACHE in sw.ts), and waits for it to confirm before
 * resolving. Call this as part of logout, and await it before navigating
 * away, so a second user signing in on the same device can't race the
 * cache-clear and see stale cached data.
 *
 * Resolves after the service worker acknowledges (event.data ===
 * 'cache-cleared') or after a short timeout, whichever comes first — logout
 * must never hang if the service worker is unavailable or unregistered.
 */
export function clearOfflineDataOnLogout(): Promise<void> {
  const controller = navigator.serviceWorker?.controller;
  if (!controller) {
    return Promise.resolve();
  }

  const ack = new Promise<void>((resolve) => {
    const onMessage = (event: MessageEvent): void => {
      if (event.data === 'cache-cleared') {
        navigator.serviceWorker.removeEventListener('message', onMessage);
        resolve();
      }
    };
    navigator.serviceWorker.addEventListener('message', onMessage);
  });

  const timeout = new Promise<void>((resolve) => {
    setTimeout(resolve, CLEAR_CACHE_ACK_TIMEOUT_MS);
  });

  controller.postMessage('clear-api-cache');

  return Promise.race([ack, timeout]);
}

let onlineHandler: (() => void) | null = null;
let offlineHandler: (() => void) | null = null;

/**
 * Wires the persistent offline indicator to the browser's online/offline events
 * and sets its initial state. Call once at app startup.
 */
export function initOfflineIndicator(onOnline?: () => void): void {
  updateOfflineIndicator(isOffline());

  offlineHandler = () => updateOfflineIndicator(true);
  onlineHandler = () => {
    updateOfflineIndicator(false);
    onOnline?.();
  };

  window.addEventListener('offline', offlineHandler);
  window.addEventListener('online', onlineHandler);
}
