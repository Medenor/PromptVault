/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('i18next', () => ({
  default: {
    t: vi.fn((key: string) => key),
    language: 'en',
  },
}));

const reportErrorMock = vi.fn();
vi.mock('@/telemetry', () => ({
  reportError: (...args: unknown[]) => reportErrorMock(...args),
}));

const showNotificationMock = vi.fn();
vi.mock('@/utils/notifications', () => ({
  showNotification: (...args: unknown[]) => showNotificationMock(...args),
}));

const createUserMock = vi.fn();
vi.mock('../api', () => ({
  createUser: (...args: unknown[]) => createUserMock(...args),
}));

import { APIRequestError } from '@/utils/api';
import {
  setCreateUserFormCallbacks,
  setupCreateUserForm,
  submitCreateUserForm,
} from '../create-user-form';

function renderCreateUserForm(): void {
  document.body.innerHTML = `
    <div id="create-user-modal" class="hidden"></div>
    <button id="add-user-btn"></button>
    <button id="create-user-cancel-btn"></button>
    <button id="create-user-submit-btn"></button>
    <form id="create-user-form">
      <input id="create-username" />
      <span id="create-username-error" class="hidden"></span>
      <input id="create-email" />
      <span id="create-email-error" class="hidden"></span>
      <input id="create-password" />
      <span id="create-password-error" class="hidden"></span>
      <input id="create-confirm-password" />
      <span id="create-confirm-password-error" class="hidden"></span>
      <select id="create-role"><option value="viewer" selected>viewer</option></select>
      <input id="create-email-verified" type="checkbox" />
      <span id="create-form-error" class="hidden"></span>
    </form>
    <div id="create-user-error-summary" class="hidden"></div>
  `;
}

beforeEach(() => {
  renderCreateUserForm();
  createUserMock.mockReset();
  reportErrorMock.mockClear();
  showNotificationMock.mockClear();
});

function fill(id: string, value: string): void {
  (document.getElementById(id) as HTMLInputElement).value = value;
}

describe('submitCreateUserForm', () => {
  it('blocks submission when required fields are empty', async () => {
    await submitCreateUserForm();
    expect(createUserMock).not.toHaveBeenCalled();
    expect(
      document.getElementById('create-user-error-summary')?.querySelectorAll('li').length
    ).toBeGreaterThan(0);
  });

  it('blocks submission when passwords do not match', async () => {
    fill('create-username', 'newuser');
    fill('create-email', 'new@example.com');
    fill('create-password', 'Password123!');
    fill('create-confirm-password', 'Different123!');

    await submitCreateUserForm();

    expect(createUserMock).not.toHaveBeenCalled();
  });

  it('creates the user and invokes the refresh callback on success', async () => {
    createUserMock.mockResolvedValue({});
    const onUserCreated = vi.fn().mockResolvedValue(undefined);
    setCreateUserFormCallbacks({ onUserCreated });

    fill('create-username', 'newuser');
    fill('create-email', 'new@example.com');
    fill('create-password', 'Password123!');
    fill('create-confirm-password', 'Password123!');

    await submitCreateUserForm();

    expect(createUserMock).toHaveBeenCalledWith({
      username: 'newuser',
      email: 'new@example.com',
      password: 'Password123!',
      confirm_password: 'Password123!',
      role: 'viewer',
      email_verified: false,
    });
    expect(showNotificationMock).toHaveBeenCalled();
    expect(onUserCreated).toHaveBeenCalled();
  });

  it('maps a 409 conflict to the form-level error message', async () => {
    createUserMock.mockRejectedValue(
      new APIRequestError(409, { detail: 'Username already exists' })
    );

    fill('create-username', 'dup');
    fill('create-email', 'dup@example.com');
    fill('create-password', 'Password123!');
    fill('create-confirm-password', 'Password123!');

    await submitCreateUserForm();

    expect(document.getElementById('create-form-error')?.textContent).toBe(
      'Username already exists'
    );
  });

  it('maps 422 field errors onto the matching inputs', async () => {
    createUserMock.mockRejectedValue(
      new APIRequestError(422, {
        detail: [{ loc: ['body', 'email'], msg: 'Invalid email', type: 'value_error' }],
      })
    );

    fill('create-username', 'newuser');
    fill('create-email', 'bad-email');
    fill('create-password', 'Password123!');
    fill('create-confirm-password', 'Password123!');

    await submitCreateUserForm();

    expect(document.getElementById('create-email-error')?.textContent).toBe('Invalid email');
  });

  it('reports unexpected errors via telemetry', async () => {
    createUserMock.mockRejectedValue(new Error('network down'));

    fill('create-username', 'newuser');
    fill('create-email', 'new@example.com');
    fill('create-password', 'Password123!');
    fill('create-confirm-password', 'Password123!');

    await submitCreateUserForm();

    expect(reportErrorMock).toHaveBeenCalledWith('admin-users', 'createUser', expect.any(Error));
  });
});

describe('setupCreateUserForm', () => {
  it('wires the add-user button to open the modal', () => {
    setupCreateUserForm();
    document.getElementById('add-user-btn')?.dispatchEvent(new MouseEvent('click'));
    expect(document.getElementById('create-user-modal')?.classList.contains('hidden')).toBe(false);
  });

  it('wires the cancel button to close and reset the form', () => {
    setupCreateUserForm();
    fill('create-username', 'leftover');
    document.getElementById('create-user-cancel-btn')?.dispatchEvent(new MouseEvent('click'));
    expect((document.getElementById('create-username') as HTMLInputElement).value).toBe('');
  });
});
