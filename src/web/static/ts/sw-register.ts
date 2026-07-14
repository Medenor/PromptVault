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

/**
 * Clears data cached for offline use so it can't leak across users on a shared
 * device: tells the active service worker to drop its cached prompt API
 * responses (API_CACHE in sw.ts). Call this as part of logout, before
 * navigating away.
 */
export function clearOfflineDataOnLogout(): void {
  navigator.serviceWorker?.controller?.postMessage('clear-api-cache');
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
