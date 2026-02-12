/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Admin user management logic
 */

import '../css/tailwind-globals.css';
import { reportError } from '@/telemetry';
import { changeLanguage, initI18n, t, tUnsafe, updateStaticTranslations } from '@/utils/i18n';
import { showNotification } from '@/utils/notifications';
import { apiGet, apiPost, apiPut, apiDelete, APIRequestError } from '@/utils/api';
import { createTypeahead } from '@/utils/typeahead';
import { announce } from '@/utils/a11y';

const API_BASE = '/api/admin';
const HIDDEN_CLASS = 'hidden';

interface AdminUser {
  id: string;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  email_verified?: boolean;
  last_login?: string | null;
  created_at?: string | null;
  locked_until?: string | null;
  session_count?: number;
  failed_login_attempts?: number;
}

interface UsersResponse {
  users?: AdminUser[];
  pages?: number;
  total?: number;
}

interface PasswordChecks {
  length: boolean;
  uppercase: boolean;
  lowercase: boolean;
  digit: boolean;
  special: boolean;
}

interface FormValidationError {
  inputId: string;
  message: string;
}

const liveValidationState = new Map<string, boolean>();

let currentPage = 1;
let totalPages = 1;
let currentFilters = {
  search: '',
  role: 'all',
  status: 'all',
};

// Focus management for modals
let userDetailModalTrigger: HTMLElement | null = null;
let editUserModalTrigger: HTMLElement | null = null;
let confirmDeleteModalTrigger: HTMLElement | null = null;
let createUserModalTrigger: HTMLElement | null = null;

function formatDate(dateString?: string | null): string {
  if (!dateString) return 'Never';
  const date = new Date(dateString);
  return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
}

function getTranslatedRole(role: string): string {
  const roleTranslations: Record<string, string> = {
    viewer: 'roleViewer',
    editor: 'roleEditor',
    admin: 'roleAdmin',
    user: 'roleUser',
  };
  const translationKey = roleTranslations[role] || role;
  return tUnsafe(`admin.users.${translationKey}`) || role;
}

function normalizeErrorDetail(
  detail: string | Array<{ loc?: Array<string | number>; msg?: string }> | undefined
): string | undefined {
  if (typeof detail === 'string') {
    return detail;
  }
  if (Array.isArray(detail)) {
    const first = detail[0];
    return first?.msg;
  }
  return undefined;
}

function showModal(modalId: string): void {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove(HIDDEN_CLASS);
    // Move focus to first focusable element in modal
    const firstFocusable = modal.querySelector('h2, button, input, [tabindex="0"]') as HTMLElement;
    if (firstFocusable) {
      firstFocusable.focus();
    }
  }
}

function hideModal(modalId: string): void {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add(HIDDEN_CLASS);
  // Return focus to trigger element
  if (modalId === 'user-detail-modal' && userDetailModalTrigger) {
    userDetailModalTrigger.focus();
  } else if (modalId === 'edit-user-modal' && editUserModalTrigger) {
    editUserModalTrigger.focus();
  } else if (modalId === 'confirm-delete-modal' && confirmDeleteModalTrigger) {
    confirmDeleteModalTrigger.focus();
  } else if (modalId === 'create-user-modal' && createUserModalTrigger) {
    createUserModalTrigger.focus();
  }
}

function getStatusClass(user: AdminUser): string {
  if (user.locked_until && new Date(user.locked_until) > new Date()) {
    return 'locked';
  }
  return user.is_active ? 'active' : 'inactive';
}

function getStatusText(user: AdminUser): string {
  if (user.locked_until && new Date(user.locked_until) > new Date()) {
    return 'Locked';
  }
  return user.is_active ? 'Active' : 'Inactive';
}

function updateStats(data: UsersResponse): void {
  const totalUsersEl = document.getElementById('total-users');
  if (totalUsersEl) {
    totalUsersEl.textContent = String(data.total || 0);
  }

  let activeUsers = 0;
  let lockedUsers = 0;
  let adminUsers = 0;

  if (data.users) {
    data.users.forEach((user) => {
      if (user.is_active) activeUsers += 1;
      if (user.locked_until && new Date(user.locked_until) > new Date()) lockedUsers += 1;
      if (user.role === 'admin') adminUsers += 1;
    });
  }

  const activeUsersEl = document.getElementById('active-users');
  const lockedUsersEl = document.getElementById('locked-users');
  const adminUsersEl = document.getElementById('admin-users');

  if (activeUsersEl) activeUsersEl.textContent = String(activeUsers);
  if (lockedUsersEl) lockedUsersEl.textContent = String(lockedUsers);
  if (adminUsersEl) adminUsersEl.textContent = String(adminUsers);
}

function updatePagination(): void {
  const pageInfo = document.getElementById('page-info');
  const prevBtn = document.getElementById('prev-page') as HTMLButtonElement | null;
  const nextBtn = document.getElementById('next-page') as HTMLButtonElement | null;

  if (pageInfo) pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
  if (prevBtn) prevBtn.disabled = currentPage === 1;
  if (nextBtn) nextBtn.disabled = currentPage === totalPages;
}

let usersTableKeyboardNavInitialized = false;

function announceKeyboardNavigation(message: string): void {
  const announcer = document.getElementById('keyboard-navigation-announcer');
  if (!announcer) {
    return;
  }
  announcer.textContent = '';
  requestAnimationFrame(() => {
    announcer.textContent = message;
  });
}

function isTextEditingTarget(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  if (!el) return false;
  return el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT' || el.isContentEditable;
}

function initializeUsersTableFirstCharNavigation(): void {
  if (usersTableKeyboardNavInitialized) {
    return;
  }
  usersTableKeyboardNavInitialized = true;

  const typeahead = createTypeahead();

  const body = document.getElementById('users-table-body');
  if (!body) {
    return;
  }

  body.addEventListener('keydown', (event) => {
    if (event.metaKey || event.ctrlKey || event.altKey) {
      return;
    }
    if (isTextEditingTarget(event.target)) {
      return;
    }
    if ((event as KeyboardEvent).isComposing || event.key === 'Process') {
      return;
    }
    if (event.key.length !== 1) {
      return;
    }

    const rows = Array.from(body.querySelectorAll<HTMLTableRowElement>('tr'));
    if (rows.length === 0) {
      return;
    }

    const target = event.target as HTMLElement | null;
    const currentRow = target?.closest('tr');
    const currentIndex = currentRow ? rows.indexOf(currentRow) : -1;

    const query = typeahead.pushKey(event.key);
    if (!query) {
      return;
    }

    for (let offset = 1; offset <= rows.length; offset++) {
      const index = (currentIndex + offset + rows.length) % rows.length;
      const row = rows[index];
      if (!row) continue;
      const usernameCell = row.querySelector('td');
      const username = usernameCell?.textContent?.trim() ?? '';
      if (!username.toLocaleLowerCase().startsWith(query)) {
        continue;
      }

      const viewButton = row.querySelector<HTMLButtonElement>('button[onclick^="window.viewUser"]');
      if (!viewButton) {
        return;
      }

      event.preventDefault();
      viewButton.focus();
      announceKeyboardNavigation(t('accessibility.navigateTo', { item: username }));
      return;
    }
  });

  body.addEventListener('compositionend', (event) => {
    const composed = (event as CompositionEvent).data ?? '';
    const query = typeahead.pushText(composed);
    if (!query) {
      return;
    }

    const rows = Array.from(body.querySelectorAll<HTMLTableRowElement>('tr'));
    if (rows.length === 0) {
      return;
    }
    const active = document.activeElement as HTMLElement | null;
    const currentRow = active?.closest?.('tr') as HTMLTableRowElement | null;
    const currentIndex = currentRow ? rows.indexOf(currentRow) : -1;

    for (let offset = 1; offset <= rows.length; offset++) {
      const index = (currentIndex + offset + rows.length) % rows.length;
      const row = rows[index];
      if (!row) continue;
      const usernameCell = row.querySelector('td');
      const username = usernameCell?.textContent?.trim() ?? '';
      if (!username.toLocaleLowerCase().startsWith(query)) {
        continue;
      }
      const viewButton = row.querySelector<HTMLButtonElement>('button[onclick^="window.viewUser"]');
      if (!viewButton) return;
      viewButton.focus();
      announceKeyboardNavigation(t('accessibility.navigateTo', { item: username }));
      return;
    }
  });
}

async function loadUsers(): Promise<void> {
  const tableBody = document.getElementById('users-table-body');
  if (!tableBody) return;

  tableBody.innerHTML =
    '<tr><td colspan="7" class="px-6 py-4 text-center text-gray-500"><div>Loading...</div></td></tr>';

  try {
    const params = new URLSearchParams({
      page: String(currentPage),
      limit: '20',
      search: currentFilters.search,
    });

    if (currentFilters.role !== 'all') {
      params.append('role', currentFilters.role);
    }

    if (currentFilters.status !== 'all') {
      if (currentFilters.status === 'active') {
        params.append('is_active', 'true');
      } else if (currentFilters.status === 'inactive') {
        params.append('is_active', 'false');
      } else if (currentFilters.status === 'locked') {
        params.append('is_locked', 'true');
      }
    }

    const data = await apiGet<UsersResponse>(`${API_BASE}/users?${params.toString()}`);
    const users = data.users || [];
    totalPages = data.pages || 1;

    updateStats(data);

    if (users.length === 0) {
      tableBody.innerHTML =
        '<tr><td colspan="7" class="px-6 py-4 text-center text-gray-500">No users found</td></tr>';
    } else {
      tableBody.innerHTML = users
        .map((user) => {
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
          return `
              <tr class="hover:bg-gray-50">
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${user.username}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${user.email}</td>
                <td class="px-6 py-4 whitespace-nowrap"><span class="inline-block px-3 py-1 rounded-full text-xs font-medium ${roleBadgeClass}">${getTranslatedRole(user.role)}</span></td>
                <td class="px-6 py-4 whitespace-nowrap"><span class="inline-block px-3 py-1 rounded-full text-xs font-medium ${statusBadgeClass}">${getStatusText(user)}</span></td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${formatDate(user.last_login)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${user.session_count || 0}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm">
                  <div class="flex space-x-2">
                    <button class="px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 text-xs font-medium" onclick="window.viewUser('${user.id}')" data-i18n="actions.view">View</button>
                    <button class="px-3 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 text-xs font-medium" onclick="window.editUser('${user.id}')" data-i18n="actions.edit">Edit</button>
                    <button class="px-3 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200 text-xs font-medium" onclick="window.deleteUser('${user.id}', '${user.username}')" data-i18n="actions.delete">Delete</button>
                  </div>
                </td>
              </tr>
            `;
        })
        .join('');
    }

    updatePagination();
    updateStaticTranslations();
    initializeUsersTableFirstCharNavigation();
  } catch (error) {
    reportError('admin-users', 'loadUsers', error);
    tableBody.innerHTML =
      '<tr><td colspan="7" class="px-6 py-4 text-center text-red-600">Error loading users</td></tr>';
  }
}

async function viewUser(userId: string): Promise<void> {
  const content = document.getElementById('user-detail-content');
  if (content) {
    content.innerHTML = '<div class="text-gray-500">Loading...</div>';
  }
  // Store trigger element for focus return
  userDetailModalTrigger = (event as unknown as { target: HTMLElement }).target || null;
  showModal('user-detail-modal');

  try {
    const user = await apiGet<AdminUser>(`${API_BASE}/users/${userId}`);
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
      content.innerHTML = `
          <div class="space-y-4">
            <div class="flex justify-between py-3 border-b border-gray-200">
              <div class="text-sm font-medium text-gray-500">Username:</div>
              <div class="text-sm text-gray-900">${user.username}</div>
            </div>
            <div class="flex justify-between py-3 border-b border-gray-200">
              <div class="text-sm font-medium text-gray-500">Email:</div>
              <div class="text-sm text-gray-900">${user.email}</div>
            </div>
            <div class="flex justify-between py-3 border-b border-gray-200">
              <div class="text-sm font-medium text-gray-500">Role:</div>
              <div class="text-sm"><span class="inline-block px-3 py-1 rounded-full text-xs font-medium ${roleBadgeClass}">${getTranslatedRole(user.role)}</span></div>
            </div>
            <div class="flex justify-between py-3 border-b border-gray-200">
              <div class="text-sm font-medium text-gray-500">Status:</div>
              <div class="text-sm"><span class="inline-block px-3 py-1 rounded-full text-xs font-medium ${statusBadgeClass}">${getStatusText(user)}</span></div>
            </div>
            <div class="flex justify-between py-3 border-b border-gray-200">
              <div class="text-sm font-medium text-gray-500">Email Verified:</div>
              <div class="text-sm text-gray-900">${user.email_verified ? 'Yes' : 'No'}</div>
            </div>
            <div class="flex justify-between py-3 border-b border-gray-200">
              <div class="text-sm font-medium text-gray-500">Created:</div>
              <div class="text-sm text-gray-900">${formatDate(user.created_at)}</div>
            </div>
            <div class="flex justify-between py-3 border-b border-gray-200">
              <div class="text-sm font-medium text-gray-500">Last Login:</div>
              <div class="text-sm text-gray-900">${formatDate(user.last_login)}</div>
            </div>
            <div class="flex justify-between py-3 border-b border-gray-200">
              <div class="text-sm font-medium text-gray-500">Failed Login Attempts:</div>
              <div class="text-sm text-gray-900">${user.failed_login_attempts || 0}</div>
            </div>
            <div class="flex justify-between py-3">
              <div class="text-sm font-medium text-gray-500">Active Sessions:</div>
              <div class="text-sm text-gray-900">${user.session_count || 0}</div>
            </div>
          </div>
        `;
    }
  } catch (error) {
    reportError('admin-users', 'viewUser', error);
    if (content) {
      content.innerHTML = '<p class="text-red-600">Failed to load user details</p>';
    }
  }
}

async function editUser(userId: string): Promise<void> {
  try {
    const user = await apiGet<AdminUser>(`${API_BASE}/users/${userId}`);
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

    // Store trigger element for focus return
    editUserModalTrigger = (event as unknown as { target: HTMLElement }).target || null;
    showModal('edit-user-modal');
  } catch (error) {
    reportError('admin-users', 'editUser', error);
    showNotification('Failed to load user', 'error');
  }
}

async function saveUser(): Promise<void> {
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
    await apiPut(`${API_BASE}/users/${userId}`, {
      role,
      is_active: isActive,
      email_verified: emailVerified,
    });

    showNotification('User updated successfully', 'success');
    hideModal('edit-user-modal');
    await loadUsers();
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

async function deleteUser(userId: string, username: string): Promise<void> {
  const deleteUsername = document.getElementById('delete-username');
  if (deleteUsername) {
    deleteUsername.textContent = username;
  }
  // Store trigger element for focus return
  confirmDeleteModalTrigger = (event as unknown as { target: HTMLElement }).target || null;
  showModal('confirm-delete-modal');

  const confirmBtn = document.getElementById('confirm-delete-btn') as HTMLButtonElement | null;
  if (confirmBtn) {
    confirmBtn.onclick = async () => {
      try {
        await apiDelete(`${API_BASE}/users/${userId}?hard_delete=true`);
        showNotification('User permanently deleted from database', 'success');
        hideModal('confirm-delete-modal');
        await loadUsers();
      } catch (error) {
        if (error instanceof APIRequestError) {
          showNotification(error.message || 'Failed to delete user', 'error');
        } else {
          reportError('admin-users', 'deleteUser', error);
          showNotification('Failed to delete user', 'error');
        }
      }
    };
  }
}

function setupFilters(): void {
  const searchInput = document.getElementById('search-input') as HTMLInputElement | null;
  const roleFilter = document.getElementById('role-filter') as HTMLSelectElement | null;
  const statusFilter = document.getElementById('status-filter') as HTMLSelectElement | null;

  if (searchInput) {
    let searchTimeout: number | null = null;
    searchInput.addEventListener('input', (event) => {
      const target = event.target as HTMLInputElement;
      if (searchTimeout) {
        window.clearTimeout(searchTimeout);
      }
      searchTimeout = window.setTimeout(() => {
        currentFilters.search = target.value;
        currentPage = 1;
        void loadUsers();
      }, 500);
    });
  }

  if (roleFilter) {
    roleFilter.addEventListener('change', (event) => {
      const target = event.target as HTMLSelectElement;
      currentFilters.role = target.value;
      currentPage = 1;
      void loadUsers();
    });
  }

  if (statusFilter) {
    statusFilter.addEventListener('change', (event) => {
      const target = event.target as HTMLSelectElement;
      currentFilters.status = target.value;
      currentPage = 1;
      void loadUsers();
    });
  }
}

function setupPagination(): void {
  const prevBtn = document.getElementById('prev-page');
  const nextBtn = document.getElementById('next-page');

  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      if (currentPage > 1) {
        currentPage -= 1;
        void loadUsers();
      }
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      if (currentPage < totalPages) {
        currentPage += 1;
        void loadUsers();
      }
    });
  }
}

function setupCreateUserForm(): void {
  const addUserBtn = document.getElementById('add-user-btn');
  if (addUserBtn) {
    addUserBtn.addEventListener('click', openCreateUserModal);
  }

  const cancelBtn = document.getElementById('create-user-cancel-btn');
  if (cancelBtn) {
    cancelBtn.addEventListener('click', closeCreateUserModal);
  }

  const submitBtn = document.getElementById('create-user-submit-btn');
  if (submitBtn) {
    submitBtn.addEventListener('click', submitCreateUserForm);
  }

  const passwordInput = document.getElementById('create-password') as HTMLInputElement | null;
  if (passwordInput) {
    passwordInput.addEventListener('input', updatePasswordRequirements);
  }

  setupPasswordToggle('toggle-password-create', 'create-password');
  setupPasswordToggle('toggle-confirm-password-create', 'create-confirm-password');

  // Live validation (T-ACC025) for create modal fields.
  const usernameInput = document.getElementById('create-username') as HTMLInputElement | null;
  const emailInput = document.getElementById('create-email') as HTMLInputElement | null;
  const createPasswordInput = document.getElementById('create-password') as HTMLInputElement | null;
  const confirmInput = document.getElementById('create-confirm-password') as HTMLInputElement | null;

  const requiredMessage = t('validation.required') || 'This field is required.';

  const attachRequired = (
    input: HTMLInputElement | null,
    inputId: string,
    errorId: string,
    message: string
  ) => {
    if (!input) return;
    input.addEventListener('blur', () => {
      if (!input.value.trim()) {
        setLiveFieldError(inputId, errorId, message);
      } else {
        clearLiveFieldError(inputId, errorId);
      }
    });
    input.addEventListener('input', () => {
      if (liveValidationState.get(inputId) !== true) return;
      if (input.value.trim()) {
        clearLiveFieldError(inputId, errorId);
      }
    });
  };

  attachRequired(usernameInput, 'create-username', 'create-username-error', requiredMessage);
  attachRequired(emailInput, 'create-email', 'create-email-error', requiredMessage);
  attachRequired(createPasswordInput, 'create-password', 'create-password-error', requiredMessage);
  attachRequired(
    confirmInput,
    'create-confirm-password',
    'create-confirm-password-error',
    requiredMessage
  );

  emailInput?.addEventListener('blur', () => {
    if (!emailInput.value.trim()) return;
    if (!emailInput.checkValidity()) {
      setLiveFieldError(
        'create-email',
        'create-email-error',
        t('auth.register.emailInvalid') || 'Invalid email address'
      );
    }
  });

  const passwordConfirmCheck = () => {
    const password = createPasswordInput?.value ?? '';
    const confirm = confirmInput?.value ?? '';
    if (!confirm.trim()) return;
    if (password && confirm && password !== confirm) {
      setLiveFieldError(
        'create-confirm-password',
        'create-confirm-password-error',
        t('auth.register.passwordMismatch') || 'Passwords do not match'
      );
    } else if (password && confirm) {
      clearLiveFieldError('create-confirm-password', 'create-confirm-password-error');
    }
  };
  createPasswordInput?.addEventListener('input', passwordConfirmCheck);
  confirmInput?.addEventListener('input', passwordConfirmCheck);
}

function setupPasswordToggle(toggleButtonId: string, passwordInputId: string): void {
  const toggleButton = document.getElementById(toggleButtonId);
  const passwordInput = document.getElementById(passwordInputId) as HTMLInputElement | null;

  if (toggleButton && passwordInput) {
    toggleButton.addEventListener('click', (event) => {
      event.preventDefault();
      passwordInput.type = passwordInput.type === 'password' ? 'text' : 'password';
    });
  }
}

function openCreateUserModal(): void {
  // Store trigger element for focus return
  createUserModalTrigger = (event as unknown as { target: HTMLElement }).target || null;
  showModal('create-user-modal');
  clearCreateUserForm();
  updateStaticTranslations();
}

function closeCreateUserModal(): void {
  hideModal('create-user-modal');
  clearCreateUserForm();
}

function clearCreateUserForm(): void {
  const form = document.getElementById('create-user-form') as HTMLFormElement | null;
  if (form) {
    form.reset();
  }
  clearAllCreateUserErrors();
  resetPasswordRequirements();
}

function clearAllCreateUserErrors(): void {
  const errorIds = [
    'create-user-error-summary',
    'create-username-error',
    'create-email-error',
    'create-password-error',
    'create-confirm-password-error',
    'create-form-error',
  ];
  errorIds.forEach((id) => {
    const element = document.getElementById(id);
    if (element) {
      element.textContent = '';
      // Inline field errors are toggled via `.hidden`; the summary uses inline style (CSS default is `display:none`).
      if (id === 'create-user-error-summary') {
        (element as HTMLElement).style.display = 'none';
      }
      element.classList.add('hidden');
    }
  });
}

function showFieldError(elementId: string, message: string): void {
  const element = document.getElementById(elementId);
  if (element) {
    element.textContent = message;
    element.classList.toggle('hidden', message.trim().length === 0);
  }
}

function setLiveFieldError(inputId: string, errorId: string, message: string): void {
  const input = document.getElementById(inputId) as HTMLElement | null;
  const hadError = liveValidationState.get(inputId) === true;
  input?.setAttribute('aria-invalid', 'true');
  showFieldError(errorId, message);
  liveValidationState.set(inputId, true);
  if (!hadError) {
    announce(message, { id: 'validation-announcer', politeness: 'polite' });
  }
}

function clearLiveFieldError(inputId: string, errorId: string): void {
  const input = document.getElementById(inputId) as HTMLElement | null;
  const hadError = liveValidationState.get(inputId) === true;
  input?.setAttribute('aria-invalid', 'false');
  showFieldError(errorId, '');
  liveValidationState.set(inputId, false);
  if (hadError) {
    announce(t('validation.fieldValid') || 'Field is valid.', {
      id: 'validation-announcer',
      politeness: 'polite',
    });
  }
}

function resetFormAccessibilityState(
  form: HTMLFormElement | null,
  inputIds: string[],
  summaryId: string
): void {
  if (form) {
    inputIds.forEach((inputId) => {
      const input = form.querySelector<HTMLElement>(`#${inputId}`);
      if (input) {
        input.setAttribute('aria-invalid', 'false');
      }
    });
  }

  const summary = document.getElementById(summaryId);
  if (summary) {
    summary.textContent = '';
    (summary as HTMLElement).style.display = 'none';
    summary.classList.add('hidden');
  }
}

function addFieldError(
  errors: FormValidationError[],
  inputId: string,
  errorId: string,
  message: string
): void {
  showFieldError(errorId, message);
  const input = document.getElementById(inputId);
  if (input) {
    const existing =
      input
        .getAttribute('aria-describedby')
        ?.split(/\s+/)
        .map((s) => s.trim())
        .filter(Boolean) ?? [];
    const next = Array.from(new Set([...existing, errorId]));
    input.setAttribute('aria-describedby', next.join(' '));
  }
  input?.setAttribute('aria-invalid', 'true');
  errors.push({ inputId, message });
}

function renderErrorSummary(summaryId: string, errors: FormValidationError[]): void {
  if (errors.length === 0) return;

  const summary = document.getElementById(summaryId);
  if (!summary) {
    document.getElementById(errors[0]?.inputId ?? '')?.focus();
    return;
  }

  summary.textContent = '';
  summary.classList.remove('hidden');
  (summary as HTMLElement).style.display = 'block';

  const header = document.createElement('p');
  header.className = 'error-banner-header';
  header.textContent = t('validation.errorSummaryHeader') || 'Please correct the following errors:';
  summary.appendChild(header);

  const list = document.createElement('ul');
  list.className = 'error-banner-list';
  for (const error of errors) {
    const item = document.createElement('li');
    const link = document.createElement('a');
    link.href = `#${error.inputId}`;
    link.className = 'underline';
    link.textContent = error.message;
    link.addEventListener('click', (event) => {
      event.preventDefault();
      const target = document.getElementById(error.inputId) as HTMLElement | null;
      target?.focus();
    });
    item.appendChild(link);
    list.appendChild(item);
  }
  summary.appendChild(list);

  // Per plan T-ACC023: focus the first invalid field after rendering the summary.
  const firstInput = document.getElementById(errors[0]?.inputId ?? '') as HTMLElement | null;
  if (firstInput) {
    firstInput.focus();
  } else {
    summary.focus();
  }
}

function mapCreateUserField(field: string): { inputId: string; errorId: string } | null {
  switch (field) {
    case 'username':
      return { inputId: 'create-username', errorId: 'create-username-error' };
    case 'email':
      return { inputId: 'create-email', errorId: 'create-email-error' };
    case 'password':
      return { inputId: 'create-password', errorId: 'create-password-error' };
    case 'confirm_password':
      return { inputId: 'create-confirm-password', errorId: 'create-confirm-password-error' };
    default:
      return null;
  }
}

function checkPasswordStrength(password: string): { strength: number; checks: PasswordChecks } {
  let strength = 0;
  const checks: PasswordChecks = {
    length: password.length >= 12,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    digit: /[0-9]/.test(password),
    special: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password),
  };

  Object.values(checks).forEach((check) => {
    if (check) strength += 1;
  });

  return { strength, checks };
}

function updatePasswordStrengthDisplay(strength: number): void {
  const strengthBar = document.getElementById('create-strength-bar-fill');
  const strengthText = document.getElementById('create-strength-text');

  if (!strengthBar || !strengthText) return;

  strengthBar.className = 'h-full transition-all duration-300';
  if (strength >= 5) {
    strengthBar.classList.add('bg-green-500');
    strengthBar.style.width = '100%';
    strengthText.textContent = t('auth.register.strengthStrong') || 'Strong password';
    strengthText.className = 'text-sm mt-1 text-green-600 font-medium';
  } else if (strength >= 3) {
    strengthBar.classList.add('bg-yellow-500');
    strengthBar.style.width = '66%';
    strengthText.textContent = t('auth.register.strengthMedium') || 'Medium password';
    strengthText.className = 'text-sm mt-1 text-yellow-600 font-medium';
  } else if (strength > 0) {
    strengthBar.classList.add('bg-red-500');
    strengthBar.style.width = '33%';
    strengthText.textContent = t('auth.register.strengthWeak') || 'Weak password';
    strengthText.className = 'text-sm mt-1 text-red-600 font-medium';
  } else {
    strengthBar.style.width = '0%';
    strengthText.textContent = '';
  }
}

function resetPasswordRequirements(): void {
  ['req-length', 'req-uppercase', 'req-lowercase', 'req-digit', 'req-special'].forEach((id) => {
    const element = document.getElementById(id);
    if (element) {
      element.classList.remove('text-green-600');
      element.classList.add('text-gray-600');
      const icon = element.querySelector('span:first-child');
      if (icon) icon.textContent = '○';
    }
  });
}

function updatePasswordRequirements(): void {
  const password =
    (document.getElementById('create-password') as HTMLInputElement | null)?.value ?? '';
  const { strength, checks } = checkPasswordStrength(password);

  const requirements: Record<string, boolean> = {
    'req-length': checks.length,
    'req-uppercase': checks.uppercase,
    'req-lowercase': checks.lowercase,
    'req-digit': checks.digit,
    'req-special': checks.special,
  };

  Object.entries(requirements).forEach(([id, met]) => {
    const element = document.getElementById(id);
    if (element) {
      if (met) {
        element.classList.remove('text-gray-600');
        element.classList.add('text-green-600');
        const icon = element.querySelector('span:first-child');
        if (icon) icon.textContent = '●';
      } else {
        element.classList.remove('text-green-600');
        element.classList.add('text-gray-600');
        const icon = element.querySelector('span:first-child');
        if (icon) icon.textContent = '○';
      }
    }
  });

  updatePasswordStrengthDisplay(strength);
}

async function submitCreateUserForm(): Promise<void> {
  const form = document.getElementById('create-user-form') as HTMLFormElement | null;
  resetFormAccessibilityState(
    form,
    ['create-username', 'create-email', 'create-password', 'create-confirm-password'],
    'create-user-error-summary'
  );
  clearAllCreateUserErrors();
  const validationErrors: FormValidationError[] = [];

  const username =
    (document.getElementById('create-username') as HTMLInputElement | null)?.value.trim() ?? '';
  const email =
    (document.getElementById('create-email') as HTMLInputElement | null)?.value.trim() ?? '';
  const password =
    (document.getElementById('create-password') as HTMLInputElement | null)?.value ?? '';
  const confirmPassword =
    (document.getElementById('create-confirm-password') as HTMLInputElement | null)?.value ?? '';
  const role = (document.getElementById('create-role') as HTMLSelectElement | null)?.value ?? '';
  const emailVerified =
    (document.getElementById('create-email-verified') as HTMLInputElement | null)?.checked ?? false;

  let hasErrors = false;

  if (!username) {
    addFieldError(
      validationErrors,
      'create-username',
      'create-username-error',
      t('validation.required') || 'Username is required'
    );
    hasErrors = true;
  }

  if (!email) {
    addFieldError(
      validationErrors,
      'create-email',
      'create-email-error',
      t('validation.required') || 'Email is required'
    );
    hasErrors = true;
  }

  if (!password) {
    addFieldError(
      validationErrors,
      'create-password',
      'create-password-error',
      t('validation.required') || 'Password is required'
    );
    hasErrors = true;
  }

  if (!confirmPassword) {
    addFieldError(
      validationErrors,
      'create-confirm-password',
      'create-confirm-password-error',
      t('validation.required') || 'Confirm password is required'
    );
    hasErrors = true;
  }

  if (password && confirmPassword && password !== confirmPassword) {
    addFieldError(
      validationErrors,
      'create-confirm-password',
      'create-confirm-password-error',
      t('auth.register.passwordMismatch') || 'Passwords do not match'
    );
    hasErrors = true;
  }

  if (hasErrors) {
    renderErrorSummary('create-user-error-summary', validationErrors);
    return;
  }

  const submitBtn = document.getElementById('create-user-submit-btn') as HTMLButtonElement | null;
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = t('messages.loading') || 'Creating...';
  }

  try {
    await apiPost(`${API_BASE}/users`, {
      username,
      email,
      password,
      confirm_password: confirmPassword,
      role,
      email_verified: emailVerified,
    });

    showNotification(t('admin.users.userCreated') || 'User created successfully', 'success');
    closeCreateUserModal();
    currentPage = 1;
    await loadUsers();
  } catch (error) {
    if (error instanceof APIRequestError) {
      if (error.status === 422 && Array.isArray(error.error.detail)) {
        const apiErrors: FormValidationError[] = [];
        error.error.detail.forEach((err) => {
          if (err.loc && err.loc.length > 1) {
            const errorMsg = err.msg || 'Validation error';
            const field = String(err.loc[1]);
            const mapping = mapCreateUserField(field);
            if (mapping) {
              addFieldError(apiErrors, mapping.inputId, mapping.errorId, errorMsg);
            } else {
              showFieldError('create-form-error', errorMsg);
            }
          }
        });
        renderErrorSummary('create-user-error-summary', apiErrors);
      } else if (error.status === 409) {
        const detailMessage = normalizeErrorDetail(error.error.detail);
        showFieldError(
          'create-form-error',
          detailMessage || t('admin.users.userExists') || 'User already exists'
        );
      } else {
        const detailMessage = normalizeErrorDetail(error.error.detail);
        showFieldError(
          'create-form-error',
          detailMessage || t('messages.error') || 'Failed to create user'
        );
      }
    } else {
      reportError('admin-users', 'createUser', error);
      showFieldError('create-form-error', t('messages.error') || 'Failed to create user');
    }
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = t('actions.create') || 'Create User';
    }
  }
}

function initializeAdminUsersPage(): void {
  updateStaticTranslations();

  // Mobile menu toggle
  const adminMenuToggle = document.getElementById('admin-menu-toggle');
  if (adminMenuToggle) {
    adminMenuToggle.addEventListener('click', () => {
      const dropdown = document.getElementById('admin-menu-dropdown');
      if (dropdown) {
        dropdown.classList.toggle('hidden');
      }
    });
  }

  const languageSelector = document.getElementById('language-selector') as HTMLSelectElement | null;
  if (languageSelector) {
    languageSelector.addEventListener('change', (event) => {
      const target = event.target as HTMLSelectElement;
      changeLanguage(target.value).catch((error) => {
        reportError('admin-users', 'changeLanguage', error);
      });
    });
  }

  const refreshBtn = document.getElementById('refresh-users-btn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      void loadUsers();
    });
  }

  const closeBtn = document.getElementById('close-user-detail-btn');
  if (closeBtn) {
    closeBtn.addEventListener('click', () => hideModal('user-detail-modal'));
  }

  const cancelDeleteBtn = document.getElementById('cancel-delete-btn');
  if (cancelDeleteBtn) {
    cancelDeleteBtn.addEventListener('click', () => hideModal('confirm-delete-modal'));
  }

  const cancelEditBtn = document.getElementById('cancel-edit-btn');
  if (cancelEditBtn) {
    cancelEditBtn.addEventListener('click', () => hideModal('edit-user-modal'));
  }

  const saveBtn = document.getElementById('save-user-btn');
  if (saveBtn) {
    saveBtn.addEventListener('click', () => {
      void saveUser();
    });
  }

  setupFilters();
  setupPagination();
  setupCreateUserForm();
  void loadUsers();
}

// Export all window functions
(
  window as Window & {
    viewUser?: (userId: string) => Promise<void>;
    editUser?: (userId: string) => Promise<void>;
    deleteUser?: (userId: string, username: string) => Promise<void>;
    openCreateUserModal?: () => void;
    submitCreateUserForm?: () => Promise<void>;
    closeUserDetailModal?: () => void;
    closeEditUserModal?: () => void;
    closeConfirmDeleteModal?: () => void;
    closeCreateUserModal?: () => void;
  }
).viewUser = viewUser;

(
  window as Window & {
    viewUser?: (userId: string) => Promise<void>;
    editUser?: (userId: string) => Promise<void>;
    deleteUser?: (userId: string, username: string) => Promise<void>;
    openCreateUserModal?: () => void;
    submitCreateUserForm?: () => Promise<void>;
    closeUserDetailModal?: () => void;
    closeEditUserModal?: () => void;
    closeConfirmDeleteModal?: () => void;
    closeCreateUserModal?: () => void;
  }
).editUser = editUser;

(
  window as Window & {
    viewUser?: (userId: string) => Promise<void>;
    editUser?: (userId: string) => Promise<void>;
    deleteUser?: (userId: string, username: string) => Promise<void>;
    openCreateUserModal?: () => void;
    submitCreateUserForm?: () => Promise<void>;
    closeUserDetailModal?: () => void;
    closeEditUserModal?: () => void;
    closeConfirmDeleteModal?: () => void;
    closeCreateUserModal?: () => void;
  }
).deleteUser = deleteUser;

(
  window as Window & {
    viewUser?: (userId: string) => Promise<void>;
    editUser?: (userId: string) => Promise<void>;
    deleteUser?: (userId: string, username: string) => Promise<void>;
    closeUserDetailModal?: () => void;
    closeEditUserModal?: () => void;
    closeConfirmDeleteModal?: () => void;
    closeCreateUserModal?: () => void;
  }
).closeUserDetailModal = () => hideModal('user-detail-modal');

(
  window as Window & {
    viewUser?: (userId: string) => Promise<void>;
    editUser?: (userId: string) => Promise<void>;
    deleteUser?: (userId: string, username: string) => Promise<void>;
    openCreateUserModal?: () => void;
    submitCreateUserForm?: () => Promise<void>;
    closeUserDetailModal?: () => void;
    closeEditUserModal?: () => void;
    closeConfirmDeleteModal?: () => void;
    closeCreateUserModal?: () => void;
  }
).closeEditUserModal = () => hideModal('edit-user-modal');

(
  window as Window & {
    viewUser?: (userId: string) => Promise<void>;
    editUser?: (userId: string) => Promise<void>;
    deleteUser?: (userId: string, username: string) => Promise<void>;
    openCreateUserModal?: () => void;
    submitCreateUserForm?: () => Promise<void>;
    closeUserDetailModal?: () => void;
    closeEditUserModal?: () => void;
    closeConfirmDeleteModal?: () => void;
    closeCreateUserModal?: () => void;
  }
).closeConfirmDeleteModal = () => hideModal('confirm-delete-modal');

(
  window as Window & {
    viewUser?: (userId: string) => Promise<void>;
    editUser?: (userId: string) => Promise<void>;
    deleteUser?: (userId: string, username: string) => Promise<void>;
    openCreateUserModal?: () => void;
    submitCreateUserForm?: () => Promise<void>;
    closeUserDetailModal?: () => void;
    closeEditUserModal?: () => void;
    closeConfirmDeleteModal?: () => void;
    closeCreateUserModal?: () => void;
  }
).closeCreateUserModal = () => {
  hideModal('create-user-modal');
  clearCreateUserForm();
};

initI18n(() => {
  try {
    initializeAdminUsersPage();
  } catch (error) {
    reportError('admin-users', 'initialize', error);
  }
});
