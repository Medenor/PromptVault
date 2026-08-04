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

const announceToScreenReaderMock = vi.fn();
vi.mock('@/utils/focus-management', () => ({
  announceToScreenReader: (...args: unknown[]) => announceToScreenReaderMock(...args),
}));

const fetchUsersMock = vi.fn();
const fetchUserMock = vi.fn();
const updateUserMock = vi.fn();
const deleteUserRequestMock = vi.fn();
vi.mock('../api', () => ({
  fetchUsers: (...args: unknown[]) => fetchUsersMock(...args),
  fetchUser: (...args: unknown[]) => fetchUserMock(...args),
  updateUser: (...args: unknown[]) => updateUserMock(...args),
  deleteUserRequest: (...args: unknown[]) => deleteUserRequestMock(...args),
}));

import { APIRequestError } from '@/utils/api';
import {
  closeConfirmDeleteModal,
  closeEditUserModal,
  closeUserDetailModal,
  deleteUser,
  editUser,
  loadUsers,
  saveUser,
  viewUser,
  type UserListState,
} from '../user-actions';

function makeState(): UserListState {
  return {
    currentPage: 1,
    totalPages: 1,
    filters: { search: '', role: 'all', status: 'all' },
  };
}

beforeEach(() => {
  document.body.innerHTML = '';
  fetchUsersMock.mockReset();
  fetchUserMock.mockReset();
  updateUserMock.mockReset();
  deleteUserRequestMock.mockReset();
  reportErrorMock.mockClear();
  showNotificationMock.mockClear();
  announceToScreenReaderMock.mockClear();
});

describe('loadUsers', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <table><tbody id="users-table-body"></tbody></table>
      <span id="total-users"></span>
      <span id="active-users"></span>
      <span id="locked-users"></span>
      <span id="admin-users"></span>
      <span id="page-info"></span>
      <button id="prev-page"></button>
      <button id="next-page"></button>
    `;
  });

  it('renders returned users and updates pagination state', async () => {
    fetchUsersMock.mockResolvedValue({
      users: [{ id: '1', username: 'alice', email: 'a@x.com', role: 'admin', is_active: true }],
      pages: 3,
      total: 1,
    });

    const state = makeState();
    await loadUsers(state);

    expect(state.totalPages).toBe(3);
    expect(document.getElementById('users-table-body')?.textContent).toContain('alice');
  });

  it('shows an error row when the fetch fails', async () => {
    fetchUsersMock.mockRejectedValue(new Error('network down'));
    await loadUsers(makeState());
    expect(document.getElementById('users-table-body')?.textContent).toContain(
      'Error loading users'
    );
    expect(reportErrorMock).toHaveBeenCalledWith('admin-users', 'loadUsers', expect.any(Error));
  });
});

describe('viewUser', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div id="user-detail-modal" class="hidden"></div>
      <div id="user-detail-content"></div>
    `;
  });

  it('renders user details on success', async () => {
    fetchUserMock.mockResolvedValue({
      id: '1',
      username: 'bob',
      email: 'bob@x.com',
      role: 'viewer',
      is_active: true,
    });

    await viewUser('1');

    expect(document.getElementById('user-detail-content')?.textContent).toContain('bob');
  });

  it('shows a failure message when the fetch fails', async () => {
    fetchUserMock.mockRejectedValue(new Error('boom'));
    await viewUser('1');
    expect(document.getElementById('user-detail-content')?.textContent).toContain(
      'Failed to load user details'
    );
  });
});

describe('editUser', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div id="edit-user-modal" class="hidden"></div>
      <input id="edit-user-id" />
      <select id="edit-role"><option value="admin">admin</option><option value="viewer">viewer</option></select>
      <input id="edit-is-active" type="checkbox" />
      <input id="edit-email-verified" type="checkbox" />
      <div id="edit-user-error-summary"></div>
      <span id="edit-form-error"></span>
    `;
  });

  it('populates the edit form from the fetched user', async () => {
    fetchUserMock.mockResolvedValue({
      id: '42',
      username: 'carol',
      email: 'carol@x.com',
      role: 'viewer',
      is_active: false,
      email_verified: true,
    });

    await editUser('42');

    expect((document.getElementById('edit-user-id') as HTMLInputElement).value).toBe('42');
    expect((document.getElementById('edit-role') as HTMLSelectElement).value).toBe('viewer');
    expect((document.getElementById('edit-is-active') as HTMLInputElement).checked).toBe(false);
    expect((document.getElementById('edit-email-verified') as HTMLInputElement).checked).toBe(true);
  });

  it('shows a notification when the fetch fails with a generic error', async () => {
    fetchUserMock.mockRejectedValue(new Error('boom'));
    await editUser('42');
    expect(showNotificationMock).toHaveBeenCalled();
  });
});

describe('saveUser', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div id="edit-user-modal" class="hidden"></div>
      <form id="edit-user-form">
        <input id="edit-user-id" value="7" />
        <select id="edit-role"><option value="admin" selected>admin</option></select>
        <input id="edit-is-active" type="checkbox" checked />
        <input id="edit-email-verified" type="checkbox" />
      </form>
      <div id="edit-user-error-summary"></div>
      <span id="edit-form-error"></span>
      <table><tbody id="users-table-body"></tbody></table>
      <span id="total-users"></span><span id="active-users"></span>
      <span id="locked-users"></span><span id="admin-users"></span>
      <span id="page-info"></span><button id="prev-page"></button><button id="next-page"></button>
    `;
  });

  it('rejects an empty role without calling the API', async () => {
    (document.getElementById('edit-role') as HTMLSelectElement).value = '';
    await saveUser(makeState());
    expect(updateUserMock).not.toHaveBeenCalled();
  });

  it('updates the user and reloads the list on success', async () => {
    updateUserMock.mockResolvedValue({});
    fetchUsersMock.mockResolvedValue({ users: [], pages: 1, total: 0 });

    await saveUser(makeState());

    expect(updateUserMock).toHaveBeenCalledWith('7', {
      role: 'admin',
      is_active: true,
      email_verified: false,
    });
    expect(showNotificationMock).toHaveBeenCalledWith('User updated successfully', 'success');
  });

  it('surfaces field-level 422 errors from the API', async () => {
    const apiError = new APIRequestError(422, {
      detail: [{ loc: ['body', 'role'], msg: 'Invalid role', type: 'value_error' }],
    });
    updateUserMock.mockRejectedValue(apiError);

    await saveUser(makeState());

    expect(document.getElementById('edit-user-error-summary')?.querySelectorAll('li')).toHaveLength(
      1
    );
  });
});

describe('deleteUser', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div id="confirm-delete-modal" class="hidden"></div>
      <span id="delete-username"></span>
      <button id="confirm-delete-btn"></button>
      <table><tbody id="users-table-body"></tbody></table>
      <span id="total-users"></span><span id="active-users"></span>
      <span id="locked-users"></span><span id="admin-users"></span>
      <span id="page-info"></span><button id="prev-page"></button><button id="next-page"></button>
    `;
  });

  it('wires the confirm button to delete and refresh the list', async () => {
    deleteUserRequestMock.mockResolvedValue({});
    fetchUsersMock.mockResolvedValue({ users: [], pages: 1, total: 0 });

    await deleteUser('9', 'dave', makeState());
    expect(document.getElementById('delete-username')?.textContent).toBe('dave');

    const confirmBtn = document.getElementById('confirm-delete-btn') as HTMLButtonElement;
    confirmBtn.click();

    await vi.waitFor(() => {
      expect(announceToScreenReaderMock).toHaveBeenCalled();
    });

    expect(deleteUserRequestMock).toHaveBeenCalledWith('9');
  });
});

describe('modal close helpers', () => {
  it('hide their respective modals', () => {
    document.body.innerHTML = `
      <div id="user-detail-modal"></div>
      <div id="edit-user-modal"></div>
      <div id="confirm-delete-modal"></div>
    `;
    closeUserDetailModal();
    closeEditUserModal();
    closeConfirmDeleteModal();
    expect(document.getElementById('user-detail-modal')?.classList.contains('hidden')).toBe(true);
    expect(document.getElementById('edit-user-modal')?.classList.contains('hidden')).toBe(true);
    expect(document.getElementById('confirm-delete-modal')?.classList.contains('hidden')).toBe(
      true
    );
  });
});
