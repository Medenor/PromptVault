/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const apiGet = vi.fn().mockResolvedValue({ role: 'user' });
vi.mock('@/utils/api', () => ({
  apiGet: (...args: unknown[]) => apiGet(...args),
}));

const clearOfflineDataOnLogout = vi.fn().mockResolvedValue(undefined);
vi.mock('@/sw-register', () => ({
  clearOfflineDataOnLogout: (...args: unknown[]) => clearOfflineDataOnLogout(...args),
}));

const reportError = vi.fn();
vi.mock('@/telemetry', () => ({
  reportError: (...args: unknown[]) => reportError(...args),
}));

import {
  fetchRoleAndRevealAdmin,
  hideAuthOnlyElements,
  logout,
  revealAdminButtons,
} from '../utils/auth-nav';

function createStorage() {
  const store = new Map<string, string>();
  return {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => {
      store.set(key, value);
    },
    removeItem: (key: string) => {
      store.delete(key);
    },
    clear: () => {
      store.clear();
    },
  };
}

describe('logout', () => {
  beforeEach(() => {
    apiGet.mockClear();
    clearOfflineDataOnLogout.mockClear();
    reportError.mockClear();
    delete (window as unknown as { __AUTH_ENABLED__?: boolean }).__AUTH_ENABLED__;
    delete (window as unknown as Record<string, unknown>).location;
    (window as unknown as Record<string, unknown>).location = { href: '' };
    vi.stubGlobal('localStorage', createStorage());
    vi.stubGlobal('sessionStorage', createStorage());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    delete (window as unknown as { __AUTH_ENABLED__?: boolean }).__AUTH_ENABLED__;
  });

  it('redirects immediately without calling fetch when auth is disabled (anonymous mode)', async () => {
    (window as unknown as { __AUTH_ENABLED__?: boolean }).__AUTH_ENABLED__ = false;
    globalThis.fetch = vi.fn();

    await logout('test-page');

    expect(globalThis.fetch).not.toHaveBeenCalled();
    expect(window.location.href).toBe('/');
  });

  it('clears storage, clears offline cache, and redirects to login on success', async () => {
    localStorage.setItem('access_token', 'a');
    localStorage.setItem('refresh_token', 'r');
    localStorage.setItem('user', 'u');
    sessionStorage.setItem('other', 'value');
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true });

    await logout('test-page');

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/auth/logout',
      expect.objectContaining({ method: 'POST' })
    );
    expect(clearOfflineDataOnLogout).toHaveBeenCalledTimes(1);
    expect(localStorage.getItem('access_token')).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
    expect(localStorage.getItem('user')).toBeNull();
    expect(sessionStorage.getItem('other')).toBeNull();
    expect(window.location.href).toBe('/auth/login');
  });

  it('sends the refresh token from localStorage in the request body when present', async () => {
    localStorage.setItem('refresh_token', 'stored-refresh-token');
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true });

    await logout('test-page');

    const [, init] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [
      string,
      { body: string },
    ];
    expect(JSON.parse(init.body)).toEqual({ refresh_token: 'stored-refresh-token' });
  });

  it('still clears storage, reports the error, and redirects when fetch rejects', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('network error'));

    await logout('test-page');

    expect(reportError).toHaveBeenCalledWith(
      'test-page',
      'logout-error',
      expect.any(Error),
      {},
      'warning'
    );
    expect(clearOfflineDataOnLogout).toHaveBeenCalledTimes(1);
    expect(window.location.href).toBe('/auth/login');
  });
});

describe('hideAuthOnlyElements', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
  });

  it('hides known auth-only elements when present', () => {
    document.body.innerHTML = `
      <div id="profile-btn"></div>
      <div id="logout-btn"></div>
      <div id="mobile-drawer-account-section"></div>
      <div id="shared-with-me-filter-label"></div>
      <div id="shared-with-me-filter-label-mobile"></div>
    `;

    hideAuthOnlyElements();

    expect(document.getElementById('profile-btn')?.style.display).toBe('none');
    expect(document.getElementById('logout-btn')?.style.display).toBe('none');
    expect(document.getElementById('mobile-drawer-account-section')?.style.display).toBe('none');
    expect(document.getElementById('shared-with-me-filter-label')?.style.display).toBe('none');
    expect(document.getElementById('shared-with-me-filter-label-mobile')?.style.display).toBe(
      'none'
    );
  });

  it('does not throw when known elements are absent', () => {
    expect(() => hideAuthOnlyElements()).not.toThrow();
  });

  it('hides profile navigation links matched by onclick selector', () => {
    document.body.innerHTML = `
      <button onclick="location.href='/auth/profile'">Profile</button>
      <a onclick="window.location='/auth/profile'">Mobile Profile</a>
      <button onclick="doSomethingElse()">Other</button>
    `;

    hideAuthOnlyElements();

    const [profileBtn, mobileProfile, other] = Array.from(document.querySelectorAll('button, a'));
    expect((profileBtn as HTMLElement).style.display).toBe('none');
    expect((mobileProfile as HTMLElement).style.display).toBe('none');
    expect((other as HTMLElement).style.display).toBe('');
  });
});

describe('revealAdminButtons', () => {
  beforeEach(() => {
    document.body.innerHTML =
      '<div id="admin-btn" style="display:none"></div><div id="admin-btn-mobile" style="display:none"></div>';
  });

  it('does nothing when role is not admin', () => {
    revealAdminButtons('user');

    expect(document.getElementById('admin-btn')?.style.display).toBe('none');
    expect(document.getElementById('admin-btn-mobile')?.style.display).toBe('none');
  });

  it('does nothing when role is undefined', () => {
    revealAdminButtons(undefined);

    expect(document.getElementById('admin-btn')?.style.display).toBe('none');
  });

  it('reveals both desktop and mobile admin buttons when role is admin', () => {
    revealAdminButtons('admin');

    expect(document.getElementById('admin-btn')?.style.display).toBe('');
    expect(document.getElementById('admin-btn-mobile')?.style.display).toBe('');
  });

  it('reveals only the mobile admin button when the desktop button is absent', () => {
    document.body.innerHTML = '<div id="admin-btn-mobile" style="display:none"></div>';

    expect(() => revealAdminButtons('admin')).not.toThrow();
    expect(document.getElementById('admin-btn-mobile')?.style.display).toBe('');
  });
});

describe('fetchRoleAndRevealAdmin', () => {
  beforeEach(() => {
    document.body.innerHTML = '<div id="admin-btn" style="display:none"></div>';
    apiGet.mockClear();
  });

  it('fetches the current role and reveals admin buttons when admin', async () => {
    apiGet.mockResolvedValueOnce({ role: 'admin' });

    const result = await fetchRoleAndRevealAdmin();

    expect(apiGet).toHaveBeenCalledWith('/api/auth/me');
    expect(result).toEqual({ role: 'admin' });
    expect(document.getElementById('admin-btn')?.style.display).toBe('');
  });

  it('leaves admin buttons hidden for a non-admin role', async () => {
    apiGet.mockResolvedValueOnce({ role: 'user' });

    await fetchRoleAndRevealAdmin();

    expect(document.getElementById('admin-btn')?.style.display).toBe('none');
  });
});
