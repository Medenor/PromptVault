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

let currentPage = 1;
let totalPages = 1;
let currentFilters = {
  search: '',
  role: 'all',
  status: 'all',
};

function getAuthHeaders(): HeadersInit {
  return {
    'Content-Type': 'application/json',
  };
}

function getFetchOptions(method = 'GET', body?: Record<string, unknown>): RequestInit {
  const options: RequestInit = {
    method,
    credentials: 'include',
    headers: getAuthHeaders(),
  };
  if (body) {
    options.body = JSON.stringify(body);
  }
  return options;
}

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
  detail:
    | string
    | Array<{ loc?: Array<string | number>; msg?: string; detail?: string }>
    | undefined
): string | undefined {
  if (typeof detail === 'string') {
    return detail;
  }
  if (Array.isArray(detail)) {
    const first = detail[0];
    return first?.msg || first?.detail;
  }
  return undefined;
}

function showModal(modalId: string): void {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove(HIDDEN_CLASS);
}

function hideModal(modalId: string): void {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add(HIDDEN_CLASS);
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

    const response = await fetch(`${API_BASE}/users?${params.toString()}`, {
      credentials: 'include',
      headers: getAuthHeaders(),
    });

    if (response.ok) {
      const data = (await response.json()) as UsersResponse;
      const users = data.users || [];
      totalPages = data.pages || 1;

      updateStats(data);

      if (users.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="7" class="px-6 py-4 text-center text-gray-500">No users found</td></tr>';
      } else {
        tableBody.innerHTML = users
          .map((user) => {
            const roleBadgeClass = user.role === 'admin' ? 'bg-red-100 text-red-800' : user.role === 'editor' ? 'bg-amber-100 text-amber-800' : 'bg-blue-100 text-blue-800';
            const statusClass = getStatusClass(user);
            const statusBadgeClass = statusClass === 'active' ? 'bg-green-100 text-green-800' : statusClass === 'locked' ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800';
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
    } else if (response.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/auth/login';
    }
  } catch (error) {
    reportError('admin-users', 'loadUsers', error);
    tableBody.innerHTML = '<tr><td colspan="7" class="px-6 py-4 text-center text-red-600">Error loading users</td></tr>';
  }
}

async function viewUser(userId: string): Promise<void> {
  const content = document.getElementById('user-detail-content');
  if (content) {
    content.innerHTML = '<div class="text-gray-500">Loading...</div>';
  }
  showModal('user-detail-modal');

  try {
    const response = await fetch(`${API_BASE}/users/${userId}`, {
      credentials: 'include',
      headers: getAuthHeaders(),
    });

    if (response.ok) {
      const user = (await response.json()) as AdminUser;
      if (content) {
        const roleBadgeClass = user.role === 'admin' ? 'bg-red-100 text-red-800' : user.role === 'editor' ? 'bg-amber-100 text-amber-800' : 'bg-blue-100 text-blue-800';
        const statusClass = getStatusClass(user);
        const statusBadgeClass = statusClass === 'active' ? 'bg-green-100 text-green-800' : statusClass === 'locked' ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800';
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
    const response = await fetch(`${API_BASE}/users/${userId}`, {
      credentials: 'include',
      headers: getAuthHeaders(),
    });

    if (response.ok) {
      const user = (await response.json()) as AdminUser;
      (document.getElementById('edit-user-id') as HTMLInputElement | null)!.value = user.id;
      (document.getElementById('edit-role') as HTMLSelectElement | null)!.value = user.role;
      (document.getElementById('edit-is-active') as HTMLInputElement | null)!.checked =
        user.is_active;
      (document.getElementById('edit-email-verified') as HTMLInputElement | null)!.checked =
        !!user.email_verified;

      showModal('edit-user-modal');
    }
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

  try {
    const response = await fetch(`${API_BASE}/users/${userId}`, {
      method: 'PUT',
      credentials: 'include',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        role,
        is_active: isActive,
        email_verified: emailVerified,
      }),
    });

    if (response.ok) {
      showNotification('User updated successfully', 'success');
      hideModal('edit-user-modal');
      await loadUsers();
    } else {
      const data = (await response.json()) as Record<string, string>;
      showNotification(data.detail || 'Failed to update user', 'error');
    }
  } catch (error) {
    reportError('admin-users', 'saveUser', error);
    showNotification('Failed to update user', 'error');
  }
}

async function deleteUser(userId: string, username: string): Promise<void> {
  const deleteUsername = document.getElementById('delete-username');
  if (deleteUsername) {
    deleteUsername.textContent = username;
  }
  showModal('confirm-delete-modal');

  const confirmBtn = document.getElementById('confirm-delete-btn') as HTMLButtonElement | null;
  if (confirmBtn) {
    confirmBtn.onclick = async () => {
      try {
        const response = await fetch(`${API_BASE}/users/${userId}?hard_delete=true`, {
          method: 'DELETE',
          credentials: 'include',
          headers: getAuthHeaders(),
        });

        if (response.ok) {
          showNotification('User permanently deleted from database', 'success');
          hideModal('confirm-delete-modal');
          await loadUsers();
        } else {
          const data = (await response.json()) as Record<string, string>;
          showNotification(data.detail || 'Failed to delete user', 'error');
        }
      } catch (error) {
        reportError('admin-users', 'deleteUser', error);
        showNotification('Failed to delete user', 'error');
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
    'create-username-error',
    'create-email-error',
    'create-password-error',
    'create-confirm-password-error',
    'create-form-error',
  ];
  errorIds.forEach((id) => {
    const element = document.getElementById(id);
    if (element) element.textContent = '';
  });
}

function showFieldError(elementId: string, message: string): void {
  const element = document.getElementById(elementId);
  if (element) {
    element.textContent = message;
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
  clearAllCreateUserErrors();

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
    showFieldError('create-username-error', t('validation.required') || 'Username is required');
    hasErrors = true;
  }

  if (!email) {
    showFieldError('create-email-error', t('validation.required') || 'Email is required');
    hasErrors = true;
  }

  if (!password) {
    showFieldError('create-password-error', t('validation.required') || 'Password is required');
    hasErrors = true;
  }

  if (!confirmPassword) {
    showFieldError(
      'create-confirm-password-error',
      t('validation.required') || 'Confirm password is required'
    );
    hasErrors = true;
  }

  if (password && confirmPassword && password !== confirmPassword) {
    showFieldError(
      'create-confirm-password-error',
      t('auth.register.passwordMismatch') || 'Passwords do not match'
    );
    hasErrors = true;
  }

  if (hasErrors) return;

  const submitBtn = document.getElementById('create-user-submit-btn') as HTMLButtonElement | null;
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = t('messages.loading') || 'Creating...';
  }

  try {
    const response = await fetch(`${API_BASE}/users`, {
      ...getFetchOptions('POST', {
        username,
        email,
        password,
        confirm_password: confirmPassword,
        role,
        email_verified: emailVerified,
      }),
    });

    const data = (await response.json()) as {
      detail?: string | Array<{ loc?: Array<string | number>; msg?: string; detail?: string }>;
    };

    if (response.ok) {
      showNotification(t('admin.users.userCreated') || 'User created successfully', 'success');
      closeCreateUserModal();
      currentPage = 1;
      await loadUsers();
    } else {
      if (response.status === 422 && Array.isArray(data.detail)) {
        data.detail.forEach((error) => {
          if (error.loc && error.loc.length > 1) {
            const field = error.loc[1];
            const errorMsg = error.msg || error.detail || 'Validation error';
            showFieldError(`create-${String(field)}-error`, errorMsg);
          }
        });
      } else if (response.status === 409) {
        const detailMessage = normalizeErrorDetail(data.detail);
        showFieldError(
          'create-form-error',
          detailMessage || t('admin.users.userExists') || 'User already exists'
        );
      } else {
        const detailMessage = normalizeErrorDetail(data.detail);
        showFieldError(
          'create-form-error',
          detailMessage || t('messages.error') || 'Failed to create user'
        );
      }
    }
  } catch (error) {
    reportError('admin-users', 'createUser', error);
    showFieldError('create-form-error', t('messages.error') || 'Failed to create user');
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = t('actions.create') || 'Create User';
    }
  }
}

function initializeAdminUsersPage(): void {
  updateStaticTranslations();

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
