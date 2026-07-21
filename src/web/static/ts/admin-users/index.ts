/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Admin user management logic
 */

import '../../css/tailwind-globals.css';
import { reportError } from '@/telemetry';
import { initI18n, t, updateStaticTranslations } from '@/utils/i18n';
import { showNotification } from '@/utils/notifications';
import { APIRequestError, handleApiError } from '@/utils/api';
import { announceToScreenReader } from '@/utils/focus-management';
import { initMobileNav } from '@/mobile-nav';
import { escapeHtml } from '@/utils/dom';
import { debounce } from '@/utils/debounce';
import { fetchUser, fetchUsers, createUser, deleteUserRequest, updateUser } from './api';
import {
  addFieldError,
  clearLiveFieldError,
  getLiveValidationState,
  initializeUsersTableFirstCharNavigation,
  renderErrorSummary,
  resetFormAccessibilityState,
  setLiveFieldError,
  showFieldError,
} from './a11y';
import { getStatusClass, getStatusText, getTranslatedRole, updatePagination, updateStats, renderUsersTable, formatDate } from './list';
import {
  hideModal,
  mapCreateUserField,
  normalizeErrorDetail,
  resetPasswordRequirements,
  setupPasswordToggle,
  showModal,
  updatePasswordRequirements,
} from './modals';
import type { FormValidationError } from './types';

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

async function loadUsers(): Promise<void> {
  const tableBody = document.getElementById('users-table-body');
  if (!tableBody) return;

  tableBody.innerHTML =
    '<tr><td colspan="7" class="px-6 py-4 text-center text-gray-500 dark:text-gray-400"><div>Loading...</div></td></tr>';

  try {
    const data = await fetchUsers({
      page: currentPage,
      search: currentFilters.search,
      role: currentFilters.role,
      status: currentFilters.status,
    });
    const users = data.users || [];
    totalPages = data.pages || 1;

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
        void deleteUser(userId, username);
      },
    });

    updatePagination(currentPage, totalPages);
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
      content.innerHTML = `
          <div class="space-y-4">
            <div class="flex justify-between py-3 border-b border-gray-200 dark:border-gray-700">
              <div class="text-sm font-medium text-gray-500 dark:text-gray-400">Username:</div>
              <div class="text-sm text-gray-900 dark:text-gray-100">${escapeHtml(user.username)}</div>
            </div>
            <div class="flex justify-between py-3 border-b border-gray-200 dark:border-gray-700">
              <div class="text-sm font-medium text-gray-500 dark:text-gray-400">Email:</div>
              <div class="text-sm text-gray-900 dark:text-gray-100">${escapeHtml(user.email)}</div>
            </div>
            <div class="flex justify-between py-3 border-b border-gray-200 dark:border-gray-700">
              <div class="text-sm font-medium text-gray-500 dark:text-gray-400">Role:</div>
              <div class="text-sm"><span class="inline-block px-3 py-1 rounded-full text-xs font-medium ${roleBadgeClass}">${getTranslatedRole(user.role)}</span></div>
            </div>
            <div class="flex justify-between py-3 border-b border-gray-200 dark:border-gray-700">
              <div class="text-sm font-medium text-gray-500 dark:text-gray-400">Status:</div>
              <div class="text-sm"><span class="inline-block px-3 py-1 rounded-full text-xs font-medium ${statusBadgeClass}">${getStatusText(user)}</span></div>
            </div>
            <div class="flex justify-between py-3 border-b border-gray-200 dark:border-gray-700">
              <div class="text-sm font-medium text-gray-500 dark:text-gray-400">Email Verified:</div>
              <div class="text-sm text-gray-900 dark:text-gray-100">${user.email_verified ? 'Yes' : 'No'}</div>
            </div>
            <div class="flex justify-between py-3 border-b border-gray-200 dark:border-gray-700">
              <div class="text-sm font-medium text-gray-500 dark:text-gray-400">Created:</div>
              <div class="text-sm text-gray-900 dark:text-gray-100">${formatDate(user.created_at)}</div>
            </div>
            <div class="flex justify-between py-3 border-b border-gray-200 dark:border-gray-700">
              <div class="text-sm font-medium text-gray-500 dark:text-gray-400">Last Login:</div>
              <div class="text-sm text-gray-900 dark:text-gray-100">${formatDate(user.last_login)}</div>
            </div>
            <div class="flex justify-between py-3 border-b border-gray-200 dark:border-gray-700">
              <div class="text-sm font-medium text-gray-500 dark:text-gray-400">Failed Login Attempts:</div>
              <div class="text-sm text-gray-900 dark:text-gray-100">${user.failed_login_attempts || 0}</div>
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
      content.innerHTML = '<p class="text-red-600">Failed to load user details</p>';
    }
  }
}

async function editUser(userId: string): Promise<void> {
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
    await updateUser(userId, {
      role,
      is_active: isActive,
      email_verified: emailVerified,
    });

    showNotification('User updated successfully', 'success');
    hideModal('edit-user-modal', editUserModalTrigger);
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
  showModal('confirm-delete-modal');

  const confirmBtn = document.getElementById('confirm-delete-btn') as HTMLButtonElement | null;
  if (confirmBtn) {
    confirmBtn.onclick = async () => {
      try {
        await deleteUserRequest(userId);
        showNotification('User permanently deleted from database', 'success');
        hideModal('confirm-delete-modal', confirmDeleteModalTrigger);
        await loadUsers();
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

function setupFilters(): void {
  const searchInput = document.getElementById('search-input') as HTMLInputElement | null;
  const roleFilter = document.getElementById('role-filter') as HTMLSelectElement | null;
  const statusFilter = document.getElementById('status-filter') as HTMLSelectElement | null;

  if (searchInput) {
    const debouncedSearch = debounce((target: HTMLInputElement) => {
      currentFilters.search = target.value;
      currentPage = 1;
      void loadUsers();
    }, 500);
    searchInput.addEventListener('input', (event) => {
      debouncedSearch(event.target as HTMLInputElement);
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
  const confirmInput = document.getElementById(
    'create-confirm-password'
  ) as HTMLInputElement | null;

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
      if (!getLiveValidationState(inputId)) return;
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

function openCreateUserModal(): void {
  // Store trigger element for focus return
  createUserModalTrigger = (event as unknown as { target: HTMLElement }).target || null;
  showModal('create-user-modal');
  clearCreateUserForm();
  updateStaticTranslations();
}

function closeCreateUserModal(): void {
  hideModal('create-user-modal', createUserModalTrigger);
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
    await createUser({
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

  initMobileNav();

  const refreshBtn = document.getElementById('refresh-users-btn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      void loadUsers();
    });
  }

  const closeBtn = document.getElementById('close-user-detail-btn');
  if (closeBtn) {
    closeBtn.addEventListener('click', () => hideModal('user-detail-modal', userDetailModalTrigger));
  }

  const cancelDeleteBtn = document.getElementById('cancel-delete-btn');
  if (cancelDeleteBtn) {
    cancelDeleteBtn.addEventListener('click', () =>
      hideModal('confirm-delete-modal', confirmDeleteModalTrigger)
    );
  }

  const cancelEditBtn = document.getElementById('cancel-edit-btn');
  if (cancelEditBtn) {
    cancelEditBtn.addEventListener('click', () => hideModal('edit-user-modal', editUserModalTrigger));
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
).closeUserDetailModal = () => hideModal('user-detail-modal', userDetailModalTrigger);

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
).closeEditUserModal = () => hideModal('edit-user-modal', editUserModalTrigger);

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
).closeConfirmDeleteModal = () => hideModal('confirm-delete-modal', confirmDeleteModalTrigger);

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
  hideModal('create-user-modal', createUserModalTrigger);
  clearCreateUserForm();
};

initI18n(() => {
  try {
    initializeAdminUsersPage();
  } catch (error) {
    reportError('admin-users', 'initialize', error);
  }
});
