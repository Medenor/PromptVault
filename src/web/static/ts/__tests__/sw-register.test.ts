/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('i18next', () => ({
  default: {
    t: vi.fn((key: string) => `tr:${key}`),
  },
}));

import {
  initOfflineIndicator,
  isOffline,
  registerServiceWorker,
  updateOfflineIndicator,
} from '../sw-register';

function setNavigatorOnLine(value: boolean): void {
  Object.defineProperty(window.navigator, 'onLine', {
    configurable: true,
    value,
  });
}

describe('registerServiceWorker', () => {
  it('registers /sw.js (root scope) when serviceWorker is supported', () => {
    const register = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(window.navigator, 'serviceWorker', {
      configurable: true,
      value: { register },
    });

    registerServiceWorker();

    expect(register).toHaveBeenCalledWith('/sw.js');
  });

  it('does nothing when serviceWorker is unsupported', () => {
    Object.defineProperty(window.navigator, 'serviceWorker', {
      configurable: true,
      value: undefined,
    });

    expect(() => registerServiceWorker()).not.toThrow();
  });

  it('does not throw when registration rejects', async () => {
    const register = vi.fn().mockRejectedValue(new Error('quota exceeded'));
    Object.defineProperty(window.navigator, 'serviceWorker', {
      configurable: true,
      value: { register },
    });
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => undefined);

    registerServiceWorker();
    await Promise.resolve();
    await Promise.resolve();

    expect(warnSpy).toHaveBeenCalled();
    warnSpy.mockRestore();
  });
});

describe('offline indicator', () => {
  beforeEach(() => {
    document.body.innerHTML = '<div id="offline-indicator" class="hidden"></div>';
  });

  afterEach(() => {
    setNavigatorOnLine(true);
  });

  it('isOffline reflects navigator.onLine', () => {
    setNavigatorOnLine(true);
    expect(isOffline()).toBe(false);

    setNavigatorOnLine(false);
    expect(isOffline()).toBe(true);
  });

  it('updateOfflineIndicator shows the indicator when offline', () => {
    updateOfflineIndicator(true);
    const indicator = document.getElementById('offline-indicator')!;
    expect(indicator.classList.contains('hidden')).toBe(false);
    expect(indicator.textContent).toBeTruthy();
  });

  it('updateOfflineIndicator hides the indicator when online', () => {
    updateOfflineIndicator(true);
    updateOfflineIndicator(false);
    const indicator = document.getElementById('offline-indicator')!;
    expect(indicator.classList.contains('hidden')).toBe(true);
  });

  it('does nothing when the indicator element is missing', () => {
    document.body.innerHTML = '';
    expect(() => updateOfflineIndicator(true)).not.toThrow();
  });

  it('initOfflineIndicator sets the initial state from navigator.onLine', () => {
    setNavigatorOnLine(false);
    initOfflineIndicator();

    const indicator = document.getElementById('offline-indicator')!;
    expect(indicator.classList.contains('hidden')).toBe(false);
  });

  it('initOfflineIndicator reacts to online/offline events', () => {
    setNavigatorOnLine(true);
    const onOnline = vi.fn();
    initOfflineIndicator(onOnline);

    window.dispatchEvent(new Event('offline'));
    const indicator = document.getElementById('offline-indicator')!;
    expect(indicator.classList.contains('hidden')).toBe(false);

    window.dispatchEvent(new Event('online'));
    expect(indicator.classList.contains('hidden')).toBe(true);
    expect(onOnline).toHaveBeenCalled();
  });
});
