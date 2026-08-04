/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { reportError } from '@/telemetry';
import { t, updateStaticTranslations } from '@/utils/i18n';
import { showNotification } from '@/utils/notifications';
import { APIRequestError, handleApiError } from '@/utils/api';
import { announceToScreenReader } from '@/utils/focus-management';
import { html, raw } from '@/utils/safe-html';
import { deleteUserRequest, fetchUser, fetchUsers, updateUser } from './api';
import {
  addFieldError,
  initializeUsersTableFirstCharNavigation,
  renderErrorSummary,
  resetFormAccessibilityState,
  showFieldError,
} from './a11y';
import {
  formatDate,
  getStatusClass,
  getStatusText,
  getTranslatedRole,
  renderUsersTable,
  updatePagination,
  updateStats,
} from './list';
import { hideModal, showModal } from './modals';
import type { FormValidationError, UsersResponse } from './types';

export interface UserListState {
  currentPage: number;
  totalPages: number;
  filters: { search: string; role: string; status: string };
}

let userDetailModalTrigger: HTMLElement | null = null;
let editUserModalTrigger: HTMLElement | null = null;
let confirmDeleteModalTrigger: HTMLElement | null = null;

export async function loadUsers(state: UserListState): Promise<void> {
  const tableBody = document.getElementById('users-table-body');
  if (!tableBody) return;

  // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
  tableBody.innerHTML =
    '<tr><td colspan="7" class="px-6 py-4 text-center text-gray-500 dark:text-gray-400"><div>Loading...</div></td></tr>';

  try {
    const data: UsersResponse = await fetchUsers({
      page: state.currentPage,
      search: state.filters.search,
      role: state.filters.role,
      status: state.filters.status,
    });
    const users = data.users || [];
    state.totalPages = data.pages || 1;

    updateStats(data);

    renderUsersTable(tableBody, users, {
      onView: (userId, trigger) => {
        userDetailModalTrigger = trigger;
        void viewUser(userId);
      },
      onEdit: (userId, trigger) => {
        editUserModalTrigger = trigger;
        void editUser(userId);
      },
      onDelete: (userId, username, trigger) => {
        confirmDeleteModalTrigger = trigger;
        void deleteUser(userId, username, state);
      },
    });

    updatePagination(state.currentPage, state.totalPages);
    updateStaticTranslations();
    initializeUsersTableFirstCharNavigation();
  } catch (error) {
    reportError('admin-users', 'loadUsers', error);
    // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
    tableBody.innerHTML =
      '<tr><td colspan="7" class="px-6 py-4 text-center text-red-600">Error loading users</td></tr>';
  }
}

export async function viewUser(userId: string): Promise<void> {
  const content = document.getElementById('user-detail-content');
  if (content) {
    // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
    content.innerHTML = '<div class="text-gray-500 dark:text-gray-400">Loading...</div>';
  }
  showModal('user-detail-modal');

  try {
    const user = await fetchUser(userId);
    if (content) {
      const roleBadgeClass =
        user.role === 'admin'
          ? 'bg-red-100 text-red-800'
          : user.role === 'editor'
            ? 'bg-amber-100 text-amber-800'
            : 'bg-blue-100 text-blue-800';
      const statusClass = getStatusClass(user);
      const statusBadgeClass =
        statusClass === 'active'
          ? 'bg-green-100 text-green-800'
          : statusClass === 'locked'
            ? 'bg-red-100 text-red-800'
            : 'bg-gray-100 text-gray-800';
      // eslint-disable-next-line no-restricted-properties -- structurally escaped via html`` tagged template (utils/safe-html.ts)
      content.innerHTML = html`
        <div class="space-y-4">
          <div class="flex justify-between py-3 border-b border-gray-200 dark:border-gray-700">
            <div class="text-sm font-medium text-gray-500 dark:text-gray-400">Username:</div>
            <div class="text-sm text-gray-900 dark:text-gray-100">${user.username}</div>
          </div>
          <div class="flex justify-between py-3 border-b border-gray-200 dark:border-gray-700">
            <div class="text-sm font-medium text-gray-500 dark:text-gray-400">Email:</div>
            <div class="text-sm text-gray-900 dark:text-gray-100">${user.email}</div>
          </div>
          <div class="flex justify-between py-3 border-b border-gray-200 dark:border-gray-700">
            <div class="text-sm font-medium text-gray-500 dark:text-gray-400">Role:</div>
            <div class="text-sm">
              <span
                class="inline-block px-3 py-1 rounded-full text-xs font-medium ${raw(
                  roleBadgeClass
                )}"
                >${getTranslatedRole(user.role)}</span
              >
            </div>
          </div>
          <div class="flex justify-between py-3 border-b border-gray-200 dark:border-gray-700">
            <div class="text-sm font-medium text-gray-500 dark:text-gray-400">Status:</div>
            <div class="text-sm">
              <span
                class="inline-block px-3 py-1 rounded-full text-xs font-medium ${raw(
                  statusBadgeClass
                )}"
                >${getStatusText(user)}</span
              >
            </div>
          </div>
          <div class="flex justify-between py-3 border-b border-gray-200 dark:border-gray-700">
            <div class="text-sm font-medium text-gray-500 dark:text-gray-400">Email Verified:</div>
            <div class="text-sm text-gray-900 dark:text-gray-100">
              ${user.email_verified ? 'Yes' : 'No'}
            </div>
          </div>
          <div class="flex justify-between py-3 border-b border-gray-200 dark:border-gray-700">
            <div class="text-sm font-medium text-gray-500 dark:text-gray-400">Created:</div>
            <div class="text-sm text-gray-900 dark:text-gray-100">
              ${formatDate(user.created_at)}
            </div>
          </div>
          <div class="flex justify-between py-3 border-b border-gray-200 dark:border-gray-700">
            <div class="text-sm font-medium text-gray-500 dark:text-gray-400">Last Login:</div>
            <div class="text-sm text-gray-900 dark:text-gray-100">
              ${formatDate(user.last_login)}
            </div>
          </div>
          <div class="flex justify-between py-3 border-b border-gray-200 dark:border-gray-700">
            <div class="text-sm font-medium text-gray-500 dark:text-gray-400">
              Failed Login Attempts:
            </div>
            <div class="text-sm text-gray-900 dark:text-gray-100">
              ${user.failed_login_attempts || 0}
            </div>
          </div>
          <div class="flex justify-between py-3">
            <div class="text-sm font-medium text-gray-500 dark:text-gray-400">Active Sessions:</div>
            <div class="text-sm text-gray-900 dark:text-gray-100">${user.session_count || 0}</div>
          </div>
        </div>
      `;
    }
  } catch (error) {
    reportError('admin-users', 'viewUser', error);
    if (content) {
      // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
      content.innerHTML = '<p class="text-red-600">Failed to load user details</p>';
    }
  }
}

export async function editUser(userId: string): Promise<void> {
  try {
    const user = await fetchUser(userId);
    // Reset validation state for the edit modal each time it opens.
    const editSummary = document.getElementById('edit-user-error-summary') as HTMLElement | null;
    if (editSummary) {
      editSummary.textContent = '';
      editSummary.style.display = 'none';
      editSummary.classList.add('hidden');
    }
    showFieldError('edit-form-error', '');
    const editRole = document.getElementById('edit-role') as HTMLElement | null;
    editRole?.setAttribute('aria-invalid', 'false');

    (document.getElementById('edit-user-id') as HTMLInputElement | null)!.value = user.id;
    (document.getElementById('edit-role') as HTMLSelectElement | null)!.value = user.role;
    (document.getElementById('edit-is-active') as HTMLInputElement | null)!.checked =
      user.is_active;
    (document.getElementById('edit-email-verified') as HTMLInputElement | null)!.checked =
      !!user.email_verified;

    showModal('edit-user-modal');
  } catch (error) {
    if (!(error instanceof APIRequestError)) {
      reportError('admin-users', 'editUser', error);
    }
    showNotification(handleApiError(error, 'Failed to load user'), 'error');
  }
}

export async function saveUser(state: UserListState): Promise<void> {
  const userId = (document.getElementById('edit-user-id') as HTMLInputElement | null)?.value || '';
  const role = (document.getElementById('edit-role') as HTMLSelectElement | null)?.value || '';
  const isActive =
    (document.getElementById('edit-is-active') as HTMLInputElement | null)?.checked || false;
  const emailVerified =
    (document.getElementById('edit-email-verified') as HTMLInputElement | null)?.checked || false;

  // Minimal client-side validation to support the error summary pattern (T-ACC023).
  const validationErrors: FormValidationError[] = [];
  const editForm = document.getElementById('edit-user-form') as HTMLFormElement | null;
  resetFormAccessibilityState(
    editForm,
    ['edit-role', 'edit-is-active', 'edit-email-verified'],
    'edit-user-error-summary'
  );
  showFieldError('edit-form-error', '');
  if (!role.trim()) {
    addFieldError(
      validationErrors,
      'edit-role',
      'edit-form-error',
      t('validation.required') || 'Role is required'
    );
    renderErrorSummary('edit-user-error-summary', validationErrors);
    return;
  }

  try {
    await updateUser(userId, {
      role,
      is_active: isActive,
      email_verified: emailVerified,
    });

    showNotification('User updated successfully', 'success');
    hideModal('edit-user-modal', editUserModalTrigger);
    await loadUsers(state);
  } catch (error) {
    if (error instanceof APIRequestError) {
      if (error.status === 422 && Array.isArray(error.error.detail)) {
        const apiErrors: FormValidationError[] = [];
        error.error.detail.forEach((err) => {
          const errorMsg = err.msg || 'Validation error';
          const field = String(err.loc?.[1] ?? '');
          // Edit modal has few fields, so keep mapping small and predictable.
          if (field === 'role') {
            addFieldError(apiErrors, 'edit-role', 'edit-form-error', errorMsg);
          } else if (field === 'is_active') {
            addFieldError(apiErrors, 'edit-is-active', 'edit-form-error', errorMsg);
          } else if (field === 'email_verified') {
            addFieldError(apiErrors, 'edit-email-verified', 'edit-form-error', errorMsg);
          } else {
            showFieldError('edit-form-error', errorMsg);
          }
        });
        renderErrorSummary('edit-user-error-summary', apiErrors);
      } else {
        showNotification(error.message || 'Failed to update user', 'error');
      }
    } else {
      reportError('admin-users', 'saveUser', error);
      showNotification('Failed to update user', 'error');
    }
  }
}

export async function deleteUser(
  userId: string,
  username: string,
  state: UserListState
): Promise<void> {
  const deleteUsername = document.getElementById('delete-username');
  if (deleteUsername) {
    deleteUsername.textContent = username;
  }
  showModal('confirm-delete-modal');

  const confirmBtn = document.getElementById('confirm-delete-btn') as HTMLButtonElement | null;
  if (confirmBtn) {
    confirmBtn.onclick = async () => {
      try {
        await deleteUserRequest(userId);
        showNotification('User permanently deleted from database', 'success');
        hideModal('confirm-delete-modal', confirmDeleteModalTrigger);
        await loadUsers(state);
        // Announce to screen reader that user was deleted
        announceToScreenReader(
          `User ${username} has been deleted. Focus returned to delete button.`,
          'polite'
        );
      } catch (error) {
        if (!(error instanceof APIRequestError)) {
          reportError('admin-users', 'deleteUser', error);
        }
        showNotification(handleApiError(error, 'Failed to delete user'), 'error');
      }
    };
  }
}

export function closeUserDetailModal(): void {
  hideModal('user-detail-modal', userDetailModalTrigger);
}

export function closeEditUserModal(): void {
  hideModal('edit-user-modal', editUserModalTrigger);
}

export function closeConfirmDeleteModal(): void {
  hideModal('confirm-delete-modal', confirmDeleteModalTrigger);
}
