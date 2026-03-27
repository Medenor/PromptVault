// -----------------------------------------------------------------------------
// LEGACY JAVASCRIPT (HISTORICAL REFERENCE ONLY)
// This file remains only for historical reference and should not be edited for
// new work. Make changes in the TypeScript sources under src/web/static/ts.
// -----------------------------------------------------------------------------
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/. */

// Admin User Management JavaScript

// Initialize i18next
i18next
  .use(i18nextHttpBackend)
  .use(i18nextBrowserLanguageDetector)
  .init(
    {
      fallbackLng: 'en',
      debug: false,
      backend: {
        loadPath: '/static/locales/{{lng}}.json',
      },
    },
    function (err, t) {
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAdminUsersPage);
      } else {
        initAdminUsersPage();
      }
    }
  );

// Constants
const API_BASE = '/api/admin';
const HIDDEN_CLASS = 'is-hidden';

// State
let currentPage = 1;
let totalPages = 1;
let currentFilters = {
  search: '',
  role: 'all',
  status: 'all',
};

// Utility Functions
function getAuthHeaders() {
  // Return headers for fetch - cookies are sent automatically with credentials: 'include'
  return {
    'Content-Type': 'application/json',
  };
}

function getFetchOptions(method = 'GET', body = null) {
  const options = {
    method,
    credentials: 'include', // Send cookies automatically
    headers: getAuthHeaders(),
  };
  if (body) {
    options.body = JSON.stringify(body);
  }
  return options;
}

function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.textContent = message;
  document.body.appendChild(notification);

  setTimeout(() => {
    notification.remove();
  }, 5000);
}

function updateTranslations() {
  document.querySelectorAll('[data-i18n]').forEach((element) => {
    const key = element.getAttribute('data-i18n');
    if (key) {
      if (key.includes('[') && key.includes(']')) {
        const match = key.match(/\[(\w+)\](.+)/);
        if (match) {
          const attribute = match[1];
          const translationKey = match[2];
          const translation = i18next.t(translationKey);
          if (translation) {
            element.setAttribute(attribute, translation);
          }
        }
      } else {
        element.textContent = i18next.t(key);
      }
    }
  });

  const languageSelector = document.getElementById('language-selector');
  if (languageSelector) {
    languageSelector.value = i18next.language;
  }
}

function formatDate(dateString) {
  if (!dateString) return 'Never';
  const date = new Date(dateString);
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

function getTranslatedRole(role) {
  const roleTranslations = {
    viewer: 'roleViewer',
    editor: 'roleEditor',
    admin: 'roleAdmin',
    user: 'roleUser',
  };
  const translationKey = roleTranslations[role] || role;
  return i18next.t(`admin.users.${translationKey}`) || role;
}

function showModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove(HIDDEN_CLASS);
}

function hideModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add(HIDDEN_CLASS);
}

// Close Modal Functions (called from HTML)
window.closeUserDetailModal = () => hideModal('user-detail-modal');
window.closeEditUserModal = () => hideModal('edit-user-modal');
window.closeConfirmDeleteModal = () => hideModal('confirm-delete-modal');
window.closeCreateUserModal = () => {
  hideModal('create-user-modal');
  clearCreateUserForm();
};

// Load Users
async function loadUsers() {
  const tableBody = document.getElementById('users-table-body');
  tableBody.innerHTML =
    '<tr><td colspan="7" class="loading-cell"><div class="loading">Loading...</div></td></tr>';

  try {
    const params = new URLSearchParams({
      page: currentPage,
      limit: 20,
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
      const data = await response.json();
      const users = data.users || [];
      totalPages = data.pages || 1;

      // Update stats
      updateStats(data);

      // Render users
      if (users.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="7" class="loading-cell">No users found</td></tr>';
      } else {
        tableBody.innerHTML = users
          .map(
            (user) => `
                    <tr>
                        <td>${user.username}</td>
                        <td>${user.email}</td>
                        <td><span class="role-badge ${user.role}">${getTranslatedRole(user.role)}</span></td>
                        <td><span class="status-badge ${getStatusClass(user)}">${getStatusText(user)}</span></td>
                        <td>${formatDate(user.last_login)}</td>
                        <td>${user.session_count || 0}</td>
                        <td>
                            <div class="action-buttons">
                                <button class="action-btn view" onclick="viewUser('${user.id}')" data-i18n="actions.view">View</button>
                                <button class="action-btn edit" onclick="editUser('${user.id}')" data-i18n="actions.edit">Edit</button>
                                <button class="action-btn delete" onclick="deleteUser('${user.id}', '${user.username}')" data-i18n="actions.delete">Delete</button>
                            </div>
                        </td>
                    </tr>
                `
          )
          .join('');
      }

      // Update pagination and translations
      updatePagination();
      updateTranslations();
    } else if (response.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/auth/login';
    }
  } catch (error) {
    console.error('Error loading users:', error);
    tableBody.innerHTML = '<tr><td colspan="7" class="loading-cell">Error loading users</td></tr>';
  }
}

function getStatusClass(user) {
  if (user.locked_until && new Date(user.locked_until) > new Date()) {
    return 'locked';
  }
  return user.is_active ? 'active' : 'inactive';
}

function getStatusText(user) {
  if (user.locked_until && new Date(user.locked_until) > new Date()) {
    return 'Locked';
  }
  return user.is_active ? 'Active' : 'Inactive';
}

function updateStats(data) {
  document.getElementById('total-users').textContent = data.total || 0;

  // Calculate stats from current data
  let activeUsers = 0;
  let lockedUsers = 0;
  let adminUsers = 0;

  if (data.users) {
    data.users.forEach((user) => {
      if (user.is_active) activeUsers++;
      if (user.locked_until && new Date(user.locked_until) > new Date()) lockedUsers++;
      if (user.role === 'admin') adminUsers++;
    });
  }

  document.getElementById('active-users').textContent = activeUsers;
  document.getElementById('locked-users').textContent = lockedUsers;
  document.getElementById('admin-users').textContent = adminUsers;
}

function updatePagination() {
  document.getElementById('page-info').textContent = `Page ${currentPage} of ${totalPages}`;
  document.getElementById('prev-page').disabled = currentPage === 1;
  document.getElementById('next-page').disabled = currentPage === totalPages;
}

// View User
window.viewUser = async function (userId) {
  const modal = document.getElementById('user-detail-modal');
  const content = document.getElementById('user-detail-content');
  content.innerHTML = '<div class="loading">Loading...</div>';
  showModal('user-detail-modal');

  try {
    const response = await fetch(`${API_BASE}/users/${userId}`, {
      credentials: 'include',
      headers: getAuthHeaders(),
    });

    if (response.ok) {
      const user = await response.json();
      content.innerHTML = `
                <div class="detail-row">
                    <div class="detail-label">Username:</div>
                    <div class="detail-value">${user.username}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Email:</div>
                    <div class="detail-value">${user.email}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Role:</div>
                    <div class="detail-value"><span class="role-badge ${user.role}">${getTranslatedRole(user.role)}</span></div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Status:</div>
                    <div class="detail-value"><span class="status-badge ${getStatusClass(user)}">${getStatusText(user)}</span></div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Email Verified:</div>
                    <div class="detail-value">${user.email_verified ? 'Yes' : 'No'}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Created:</div>
                    <div class="detail-value">${formatDate(user.created_at)}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Last Login:</div>
                    <div class="detail-value">${formatDate(user.last_login)}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Failed Login Attempts:</div>
                    <div class="detail-value">${user.failed_login_attempts || 0}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Active Sessions:</div>
                    <div class="detail-value">${user.session_count || 0}</div>
                </div>
            `;
    }
  } catch (error) {
    console.error('Error loading user:', error);
    content.innerHTML = '<p class="error">Failed to load user details</p>';
  }
};

// Edit User
window.editUser = async function (userId) {
  try {
    const response = await fetch(`${API_BASE}/users/${userId}`, {
      credentials: 'include',
      headers: getAuthHeaders(),
    });

    if (response.ok) {
      const user = await response.json();

      document.getElementById('edit-user-id').value = user.id;
      document.getElementById('edit-role').value = user.role;
      document.getElementById('edit-is-active').checked = user.is_active;
      document.getElementById('edit-email-verified').checked = user.email_verified;

      showModal('edit-user-modal');
    }
  } catch (error) {
    console.error('Error loading user:', error);
    showNotification('Failed to load user', 'error');
  }
};

// Save User
document.addEventListener('DOMContentLoaded', () => {
  const saveBtn = document.getElementById('save-user-btn');
  if (saveBtn) {
    saveBtn.addEventListener('click', async () => {
      const userId = document.getElementById('edit-user-id').value;
      const role = document.getElementById('edit-role').value;
      const isActive = document.getElementById('edit-is-active').checked;
      const emailVerified = document.getElementById('edit-email-verified').checked;

      try {
        const response = await fetch(`${API_BASE}/users/${userId}`, {
          method: 'PUT',
          credentials: 'include',
          headers: getAuthHeaders(),
          body: JSON.stringify({
            role: role,
            is_active: isActive,
            email_verified: emailVerified,
          }),
        });

        if (response.ok) {
          showNotification('User updated successfully', 'success');
          hideModal('edit-user-modal');
          loadUsers();
        } else {
          const data = await response.json();
          showNotification(data.detail || 'Failed to update user', 'error');
        }
      } catch (error) {
        console.error('Error updating user:', error);
        showNotification('Failed to update user', 'error');
      }
    });
  }

  const cancelBtn = document.getElementById('cancel-edit-btn');
  if (cancelBtn) {
    cancelBtn.addEventListener('click', () => {
      hideModal('edit-user-modal');
    });
  }
});

// Delete User
window.deleteUser = function (userId, username) {
  document.getElementById('delete-username').textContent = username;
  showModal('confirm-delete-modal');

  const confirmBtn = document.getElementById('confirm-delete-btn');
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
        loadUsers();
      } else {
        const data = await response.json();
        showNotification(data.detail || 'Failed to delete user', 'error');
      }
    } catch (error) {
      console.error('Error deleting user:', error);
      showNotification('Failed to delete user', 'error');
    }
  };
};

// Setup Filters
function setupFilters() {
  const searchInput = document.getElementById('search-input');
  const roleFilter = document.getElementById('role-filter');
  const statusFilter = document.getElementById('status-filter');

  if (searchInput) {
    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        currentFilters.search = e.target.value;
        currentPage = 1;
        loadUsers();
      }, 500);
    });
  }

  if (roleFilter) {
    roleFilter.addEventListener('change', (e) => {
      currentFilters.role = e.target.value;
      currentPage = 1;
      loadUsers();
    });
  }

  if (statusFilter) {
    statusFilter.addEventListener('change', (e) => {
      currentFilters.status = e.target.value;
      currentPage = 1;
      loadUsers();
    });
  }
}

// Setup Pagination
function setupPagination() {
  const prevBtn = document.getElementById('prev-page');
  const nextBtn = document.getElementById('next-page');

  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      if (currentPage > 1) {
        currentPage--;
        loadUsers();
      }
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      if (currentPage < totalPages) {
        currentPage++;
        loadUsers();
      }
    });
  }
}

// Initialize Page
function initAdminUsersPage() {
  updateTranslations();

  const languageSelector = document.getElementById('language-selector');
  if (languageSelector) {
    languageSelector.addEventListener('change', (e) => {
      i18next.changeLanguage(e.target.value, () => {
        updateTranslations();
      });
    });
  }

  const refreshBtn = document.getElementById('refresh-users-btn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', loadUsers);
  }

  const closeBtn = document.getElementById('close-user-detail-btn');
  if (closeBtn) {
    closeBtn.addEventListener('click', () => hideModal('user-detail-modal'));
  }

  const cancelDeleteBtn = document.getElementById('cancel-delete-btn');
  if (cancelDeleteBtn) {
    cancelDeleteBtn.addEventListener('click', () => hideModal('confirm-delete-modal'));
  }

  setupFilters();
  setupPagination();
  setupCreateUserForm();
  loadUsers();
}

// ============================================================================
// Create User Modal Functions
// ============================================================================

function setupCreateUserForm() {
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

  const passwordInput = document.getElementById('create-password');
  if (passwordInput) {
    passwordInput.addEventListener('input', updatePasswordRequirements);
  }

  // Setup password toggle buttons
  setupPasswordToggle('toggle-password-create', 'create-password');
  setupPasswordToggle('toggle-confirm-password-create', 'create-confirm-password');
}

function setupPasswordToggle(toggleButtonId, passwordInputId) {
  const toggleButton = document.getElementById(toggleButtonId);
  const passwordInput = document.getElementById(passwordInputId);

  if (toggleButton && passwordInput) {
    toggleButton.addEventListener('click', (e) => {
      e.preventDefault();
      const type = passwordInput.type === 'password' ? 'text' : 'password';
      passwordInput.type = type;
    });
  }
}

function openCreateUserModal() {
  showModal('create-user-modal');
  clearCreateUserForm();
  updateTranslations();
}

function closeCreateUserModal() {
  hideModal('create-user-modal');
  clearCreateUserForm();
}

function clearCreateUserForm() {
  const form = document.getElementById('create-user-form');
  if (form) {
    form.reset();
  }
  clearAllCreateUserErrors();
  resetPasswordRequirements();
}

function clearAllCreateUserErrors() {
  document.getElementById('create-username-error').textContent = '';
  document.getElementById('create-email-error').textContent = '';
  document.getElementById('create-password-error').textContent = '';
  document.getElementById('create-confirm-password-error').textContent = '';
  document.getElementById('create-form-error').textContent = '';
}

function showError(elementId, message) {
  const element = document.getElementById(elementId);
  if (element) {
    element.textContent = message;
  }
}

function checkPasswordStrength(password) {
  let strength = 0;
  const checks = {
    length: password.length >= 12,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    digit: /[0-9]/.test(password),
    special: /[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]/.test(password),
  };

  Object.values(checks).forEach((check) => {
    if (check) strength++;
  });

  return { strength, checks };
}

function updatePasswordRequirements() {
  const password = document.getElementById('create-password').value;
  const { strength, checks } = checkPasswordStrength(password);

  const requirements = {
    'req-length': checks.length,
    'req-uppercase': checks.uppercase,
    'req-lowercase': checks.lowercase,
    'req-digit': checks.digit,
    'req-special': checks.special,
  };

  Object.entries(requirements).forEach(([id, met]) => {
    const el = document.getElementById(id);
    if (el) {
      if (met) {
        el.classList.add('met');
      } else {
        el.classList.remove('met');
      }
    }
  });

  // Update password strength bar
  updatePasswordStrengthDisplay(strength);
}

function updatePasswordStrengthDisplay(strength) {
  const strengthBar = document.getElementById('create-strength-bar-fill');
  const strengthText = document.getElementById('create-strength-text');

  if (!strengthBar || !strengthText) return;

  strengthBar.className = 'strength-bar-fill';
  if (strength >= 5) {
    strengthBar.classList.add('strength-strong');
    strengthText.textContent = i18next.t('auth.register.strengthStrong') || 'Strong password';
    strengthText.className = 'strength-text strength-strong';
  } else if (strength >= 3) {
    strengthBar.classList.add('strength-medium');
    strengthText.textContent = i18next.t('auth.register.strengthMedium') || 'Medium password';
    strengthText.className = 'strength-text strength-medium';
  } else if (strength > 0) {
    strengthBar.classList.add('strength-weak');
    strengthText.textContent = i18next.t('auth.register.strengthWeak') || 'Weak password';
    strengthText.className = 'strength-text strength-weak';
  } else {
    strengthText.textContent = '';
  }
}

function resetPasswordRequirements() {
  ['req-length', 'req-uppercase', 'req-lowercase', 'req-digit', 'req-special'].forEach((id) => {
    const el = document.getElementById(id);
    if (el) {
      el.classList.remove('met');
    }
  });
}

async function submitCreateUserForm() {
  clearAllCreateUserErrors();

  const username = document.getElementById('create-username').value.trim();
  const email = document.getElementById('create-email').value.trim();
  const password = document.getElementById('create-password').value;
  const confirmPassword = document.getElementById('create-confirm-password').value;
  const role = document.getElementById('create-role').value;
  const emailVerified = document.getElementById('create-email-verified').checked;

  // Validation
  let hasErrors = false;

  if (!username) {
    showError('create-username-error', i18next.t('validation.required') || 'Username is required');
    hasErrors = true;
  }

  if (!email) {
    showError('create-email-error', i18next.t('validation.required') || 'Email is required');
    hasErrors = true;
  }

  if (!password) {
    showError('create-password-error', i18next.t('validation.required') || 'Password is required');
    hasErrors = true;
  }

  if (!confirmPassword) {
    showError(
      'create-confirm-password-error',
      i18next.t('validation.required') || 'Confirm password is required'
    );
    hasErrors = true;
  }

  if (password && confirmPassword && password !== confirmPassword) {
    showError(
      'create-confirm-password-error',
      i18next.t('auth.register.passwordMismatch') || 'Passwords do not match'
    );
    hasErrors = true;
  }

  if (hasErrors) {
    return;
  }

  const submitBtn = document.getElementById('create-user-submit-btn');
  submitBtn.disabled = true;
  submitBtn.textContent = i18next.t('messages.loading') || 'Creating...';

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

    const data = await response.json();

    if (response.ok) {
      showNotification(
        i18next.t('admin.users.userCreated') || 'User created successfully',
        'success'
      );
      closeCreateUserModal();
      currentPage = 1; // Reset to first page
      loadUsers(); // Reload user list
    } else {
      // Handle validation errors from backend
      if (response.status === 422) {
        if (data.detail && Array.isArray(data.detail)) {
          data.detail.forEach((error) => {
            if (error.loc && error.loc.length > 1) {
              const field = error.loc[1];
              const errorMsg = error.msg || error.detail || 'Validation error';
              showError(`create-${field}-error`, errorMsg);
            }
          });
        } else {
          showError(
            'create-form-error',
            data.detail || i18next.t('messages.error') || 'Validation failed'
          );
        }
      } else if (response.status === 409) {
        showError(
          'create-form-error',
          data.detail || i18next.t('admin.users.userExists') || 'User already exists'
        );
      } else {
        showError(
          'create-form-error',
          data.detail || i18next.t('messages.error') || 'Failed to create user'
        );
      }
    }
  } catch (error) {
    console.error('Error creating user:', error);
    showError('create-form-error', i18next.t('messages.error') || 'Failed to create user');
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = i18next.t('actions.create') || 'Create User';
  }
}
