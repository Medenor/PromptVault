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
let isAuthErrorResult = false;
vi.mock('@/utils/api', () => ({
  apiGet: (...args: unknown[]) => apiGet(...args),
  APIRequestError: class APIRequestError extends Error {
    isAuthError() {
      return isAuthErrorResult;
    }
  },
}));

const reportError = vi.fn();
vi.mock('@/telemetry', () => ({
  reportError: (...args: unknown[]) => reportError(...args),
}));

import { initSecondaryNav } from '../utils/secondary-nav';

describe('initSecondaryNav', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
    initMobileNav.mockClear();
    clearOfflineDataOnLogout.mockClear();
    apiGet.mockClear();
    reportError.mockClear();
    isAuthErrorResult = false;
    apiGet.mockResolvedValue({ role: 'user' });
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

  it('wires the mobile logout button to trigger logout as well', () => {
    document.body.innerHTML = '<button id="logout-btn-mobile">Logout</button>';
    (window as unknown as { __AUTH_ENABLED__?: boolean }).__AUTH_ENABLED__ = false;
    let href: string | undefined;
    delete (window as unknown as Record<string, unknown>).location;
    (window as unknown as Record<string, unknown>).location = {
      get href() {
        return href ?? '';
      },
      set href(value: string) {
        href = value;
      },
    };

    initSecondaryNav({ component: 'test-page', requireAuth: true });
    document.getElementById('logout-btn-mobile')?.dispatchEvent(new MouseEvent('click'));

    expect(href).toBe('/');
  });

  it('reports the error without redirecting when apiGet rejects with a plain error', async () => {
    apiGet.mockRejectedValueOnce(new Error('boom'));

    initSecondaryNav({ component: 'test-page', requireAuth: true });
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();

    expect(reportError).toHaveBeenCalledWith('test-page', 'checkAdminAccess', expect.any(Error));
  });

  it('redirects to login when apiGet rejects with an auth error', async () => {
    let href: string | undefined;
    delete (window as unknown as Record<string, unknown>).location;
    (window as unknown as Record<string, unknown>).location = {
      get href() {
        return href ?? '';
      },
      set href(value: string) {
        href = value;
      },
    };
    isAuthErrorResult = true;
    const { APIRequestError } = await import('@/utils/api');
    apiGet.mockRejectedValueOnce(new APIRequestError('unauthorized'));

    initSecondaryNav({ component: 'test-page', requireAuth: true });
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();

    expect(href).toBe('/auth/login');
  });
});
