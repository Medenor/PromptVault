/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/utils/i18n', () => ({
  initI18n: (callback: () => void) => callback(),
  t: vi.fn((key: string) => key),
  updateStaticTranslations: vi.fn(),
}));

vi.mock('@/telemetry', () => ({
  reportError: vi.fn(),
}));

vi.mock('@/utils/notifications', () => ({
  showNotification: vi.fn(),
}));

vi.mock('@/utils/a11y', () => ({
  announce: vi.fn(),
}));

vi.mock('@/utils/secondary-nav', () => ({
  initSecondaryNav: vi.fn(),
}));

vi.mock('@/utils/api', () => ({
  clearStoredTokens: vi.fn(),
  refreshTokens: vi.fn().mockResolvedValue(false),
}));

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

function setupLoginPageDom(): void {
  document.body.innerHTML = `
    <form id="login-form">
      <input id="username-or-email" />
      <input id="password" type="password" />
      <input id="remember-me" type="checkbox" />
      <button type="submit">Login</button>
    </form>
    <div id="account-locked-message" class="hidden"></div>
    <form id="totp-challenge-form" class="hidden">
      <div id="totp-challenge-error-summary"></div>
      <input id="totp-challenge-code" />
      <p id="totp-challenge-code-error" class="hidden"></p>
      <button type="submit">Verify</button>
      <button type="button" id="totp-challenge-back">Back</button>
    </form>
  `;
}

describe('auth.ts login challenge step', () => {
  beforeEach(() => {
    setupLoginPageDom();
    vi.stubGlobal('localStorage', createStorage());
    vi.stubGlobal('sessionStorage', createStorage());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  it('shows the challenge step and hides the login form when login returns a challenge_token', async () => {
    const { __internal } = await import('../auth');
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ challenge_token: 'challenge-abc', expires_in: 120 }),
    });

    (document.getElementById('username-or-email') as HTMLInputElement).value = 'alice';
    (document.getElementById('password') as HTMLInputElement).value = 'Sup3rSecret!23';

    const event = { preventDefault: vi.fn() } as unknown as Event;
    await __internal.handleLoginSubmit(event);

    expect(document.getElementById('login-form')?.classList.contains('hidden')).toBe(true);
    expect(document.getElementById('totp-challenge-form')?.classList.contains('hidden')).toBe(
      false
    );
    expect(__internal.getPendingChallengeToken()).toBe('challenge-abc');
  });

  it('does not treat a normal (non-2FA) login response as a challenge', async () => {
    const { __internal } = await import('../auth');
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ access_token: 'a', refresh_token: 'r' }),
    });

    (document.getElementById('username-or-email') as HTMLInputElement).value = 'alice';
    (document.getElementById('password') as HTMLInputElement).value = 'Sup3rSecret!23';

    const event = { preventDefault: vi.fn() } as unknown as Event;
    await __internal.handleLoginSubmit(event);

    expect(document.getElementById('totp-challenge-form')?.classList.contains('hidden')).toBe(true);
    expect(sessionStorage.getItem('access_token')).toBe('a');
  });

  it('submitting a valid code exchanges the challenge and stores tokens', async () => {
    const { __internal } = await import('../auth');

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ access_token: 'access-1', refresh_token: 'refresh-1' }),
    });

    __internal.showTwoFactorChallengeStep('challenge-abc', false);
    (document.getElementById('totp-challenge-code') as HTMLInputElement).value = '123456';

    const event = { preventDefault: vi.fn() } as unknown as Event;
    await __internal.handleTwoFactorChallengeSubmit(event);

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/auth/login/2fa',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ challenge_token: 'challenge-abc', code: '123456' }),
      })
    );
    expect(sessionStorage.getItem('access_token')).toBe('access-1');
    expect(sessionStorage.getItem('refresh_token')).toBe('refresh-1');
  });

  it('shows an inline error on a wrong code (401) without leaving the challenge step', async () => {
    const { __internal } = await import('../auth');

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ detail: 'Invalid or expired authentication code.' }),
    });

    __internal.showTwoFactorChallengeStep('challenge-abc', false);
    (document.getElementById('totp-challenge-code') as HTMLInputElement).value = '000000';

    const event = { preventDefault: vi.fn() } as unknown as Event;
    await __internal.handleTwoFactorChallengeSubmit(event);

    expect(document.getElementById('totp-challenge-code-error')?.textContent).toContain(
      'Invalid or expired authentication code.'
    );
    expect(document.getElementById('totp-challenge-form')?.classList.contains('hidden')).toBe(
      false
    );
  });

  it('resets to the password step on an expired/consumed challenge (410)', async () => {
    const { __internal } = await import('../auth');

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 410,
      json: async () => ({ detail: 'Your two-factor authentication challenge has expired.' }),
    });

    __internal.showTwoFactorChallengeStep('challenge-abc', false);
    (document.getElementById('totp-challenge-code') as HTMLInputElement).value = '123456';

    const event = { preventDefault: vi.fn() } as unknown as Event;
    await __internal.handleTwoFactorChallengeSubmit(event);

    expect(document.getElementById('login-form')?.classList.contains('hidden')).toBe(false);
    expect(document.getElementById('totp-challenge-form')?.classList.contains('hidden')).toBe(true);
    expect(__internal.getPendingChallengeToken()).toBeNull();
  });

  it('the back button resets to the password step without calling fetch', async () => {
    const { __internal } = await import('../auth');
    __internal.setupLoginForm();
    __internal.showTwoFactorChallengeStep('challenge-abc', false);

    globalThis.fetch = vi.fn();
    document.getElementById('totp-challenge-back')?.dispatchEvent(new Event('click'));

    expect(globalThis.fetch).not.toHaveBeenCalled();
    expect(document.getElementById('login-form')?.classList.contains('hidden')).toBe(false);
    expect(__internal.getPendingChallengeToken()).toBeNull();
  });
});
