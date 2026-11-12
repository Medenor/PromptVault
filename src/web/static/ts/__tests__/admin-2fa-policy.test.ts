/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/telemetry', () => ({
  reportError: vi.fn(),
}));

vi.mock('@/utils/i18n', () => ({
  t: vi.fn((key: string) => key),
  tUnsafe: vi.fn((key: string) => key),
}));

vi.mock('@/utils/notifications', () => ({
  showNotification: vi.fn(),
}));

const apiGetMock = vi.fn();
const apiPutMock = vi.fn();
vi.mock('@/utils/api', () => ({
  apiGet: (...args: unknown[]) => apiGetMock(...args),
  apiPut: (...args: unknown[]) => apiPutMock(...args),
}));

import { showNotification } from '@/utils/notifications';
import { initAdminTotpPolicy, __internal } from '../admin-2fa-policy';

const mockedShowNotification = vi.mocked(showNotification);

function setupContainer(): void {
  document.body.innerHTML = '<div id="totp-2fa-policy-card"></div>';
}

describe('admin-2fa-policy', () => {
  beforeEach(() => {
    setupContainer();
    apiGetMock.mockReset();
    apiPutMock.mockReset();
    mockedShowNotification.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.innerHTML = '';
  });

  it('renders a toggle per role from the fetched policy', async () => {
    apiGetMock.mockResolvedValueOnce({
      roles: [
        { role: 'viewer', required: false },
        { role: 'editor', required: false },
        { role: 'admin', required: true },
      ],
    });

    await initAdminTotpPolicy();

    const toggles = document.querySelectorAll<HTMLInputElement>('.totp-policy-toggle');
    expect(toggles).toHaveLength(3);

    const adminToggle = document.querySelector<HTMLInputElement>('[data-role="admin"]');
    expect(adminToggle?.checked).toBe(true);
    const viewerToggle = document.querySelector<HTMLInputElement>('[data-role="viewer"]');
    expect(viewerToggle?.checked).toBe(false);
  });

  it('shows an error notification and does not render toggles when the fetch fails', async () => {
    apiGetMock.mockRejectedValueOnce(new Error('network error'));

    await initAdminTotpPolicy();

    expect(document.querySelectorAll('.totp-policy-toggle')).toHaveLength(0);
    expect(mockedShowNotification).toHaveBeenCalledWith(expect.any(String), 'error');
  });

  it('toggling a role calls apiPut with the new required value', async () => {
    apiGetMock.mockResolvedValueOnce({
      roles: [{ role: 'admin', required: false }],
    });
    apiPutMock.mockResolvedValueOnce({ role: 'admin', required: true });

    await initAdminTotpPolicy();

    const toggle = document.querySelector<HTMLInputElement>('[data-role="admin"]');
    expect(toggle).not.toBeNull();
    toggle!.checked = true;
    toggle!.dispatchEvent(new Event('change'));
    await Promise.resolve();
    await Promise.resolve();

    expect(apiPutMock).toHaveBeenCalledWith('/api/admin/2fa/policy', {
      role: 'admin',
      required: true,
    });
    expect(mockedShowNotification).toHaveBeenCalledWith(expect.any(String), 'success');
  });

  it('keeps keyboard focus on the toggle after the update settles', async () => {
    apiGetMock.mockResolvedValueOnce({
      roles: [{ role: 'admin', required: false }],
    });
    apiPutMock.mockResolvedValueOnce({ role: 'admin', required: true });

    await initAdminTotpPolicy();

    const toggle = document.querySelector<HTMLInputElement>('[data-role="admin"]')!;
    toggle.focus();
    const focusSpy = vi.spyOn(toggle, 'focus');
    toggle.checked = true;
    toggle.dispatchEvent(new Event('change'));
    // While the request is pending the control is disabled (focus is dropped by
    // the browser); once settled it must be re-enabled and refocused.
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(toggle.disabled).toBe(false);
    // jsdom keeps focus on disabled controls (real browsers drop it), so assert
    // the explicit refocus instead of the resulting activeElement.
    expect(focusSpy).toHaveBeenCalledTimes(1);
  });

  it('reverts the toggle and shows an error notification when the update fails', async () => {
    apiGetMock.mockResolvedValueOnce({
      roles: [{ role: 'admin', required: false }],
    });
    apiPutMock.mockRejectedValueOnce(new Error('network error'));

    await initAdminTotpPolicy();

    const toggle = document.querySelector<HTMLInputElement>('[data-role="admin"]');
    toggle!.checked = true;
    toggle!.dispatchEvent(new Event('change'));
    await Promise.resolve();
    await Promise.resolve();

    expect(toggle!.checked).toBe(false);
    expect(mockedShowNotification).toHaveBeenCalledWith(expect.any(String), 'error');
  });

  it('does nothing when the container is absent', async () => {
    document.body.innerHTML = '';

    await initAdminTotpPolicy();

    expect(apiGetMock).not.toHaveBeenCalled();
  });

  it('exposes internal render/handleToggle for advanced test scenarios', () => {
    expect(typeof __internal.render).toBe('function');
    expect(typeof __internal.handleToggle).toBe('function');
  });
});
