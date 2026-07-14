/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const initMobileNav = vi.fn();
vi.mock('@/mobile-nav', () => ({
  initMobileNav: (...args: unknown[]) => initMobileNav(...args),
}));

const clearOfflineDataOnLogout = vi.fn();
vi.mock('@/sw-register', () => ({
  clearOfflineDataOnLogout: (...args: unknown[]) => clearOfflineDataOnLogout(...args),
}));

const apiGet = vi.fn().mockResolvedValue({ role: 'user' });
vi.mock('@/utils/api', () => ({
  apiGet: (...args: unknown[]) => apiGet(...args),
  APIRequestError: class APIRequestError extends Error {
    isAuthError() {
      return false;
    }
  },
}));

vi.mock('@/telemetry', () => ({
  reportError: vi.fn(),
}));

import { initSecondaryNav } from '../utils/secondary-nav';

describe('initSecondaryNav', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
    initMobileNav.mockClear();
    clearOfflineDataOnLogout.mockClear();
    apiGet.mockClear();
    delete (window as unknown as { __AUTH_ENABLED__?: boolean }).__AUTH_ENABLED__;
  });

  afterEach(() => {
    delete (window as unknown as { __AUTH_ENABLED__?: boolean }).__AUTH_ENABLED__;
  });

  it('wires the shared mobile nav drawer on every secondary page', () => {
    initSecondaryNav({ component: 'test-page' });

    expect(initMobileNav).toHaveBeenCalledTimes(1);
  });

  it('does not wire logout/admin-access checks when requireAuth is false', () => {
    initSecondaryNav({ component: 'test-page' });

    expect(apiGet).not.toHaveBeenCalled();
  });

  it('checks admin access when requireAuth is true', async () => {
    initSecondaryNav({ component: 'test-page', requireAuth: true });
    await Promise.resolve();
    await Promise.resolve();

    expect(apiGet).toHaveBeenCalledWith('/api/auth/me');
  });

  it('clears offline cache data on logout click', () => {
    document.body.innerHTML = '<button id="logout-btn">Logout</button>';
    (window as unknown as { __AUTH_ENABLED__?: boolean }).__AUTH_ENABLED__ = false;

    initSecondaryNav({ component: 'test-page', requireAuth: true });
    document.getElementById('logout-btn')?.dispatchEvent(new MouseEvent('click'));

    expect(clearOfflineDataOnLogout).not.toHaveBeenCalled();
  });
});
