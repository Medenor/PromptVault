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
import { initI18n, updateStaticTranslations } from '@/utils/i18n';
import { initMobileNav } from '@/mobile-nav';
import { debounce } from '@/utils/debounce';
import { initAdminTotpPolicy } from '../admin-2fa-policy';
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
} from './user-actions';
import {
  closeCreateUserModal,
  setCreateUserFormCallbacks,
  setupCreateUserForm,
} from './create-user-form';

const state: UserListState = {
  currentPage: 1,
  totalPages: 1,
  filters: {
    search: '',
    role: 'all',
    status: 'all',
  },
};

function refreshUsers(): Promise<void> {
  return loadUsers(state);
}

function setupFilters(): void {
  const searchInput = document.getElementById('search-input') as HTMLInputElement | null;
  const roleFilter = document.getElementById('role-filter') as HTMLSelectElement | null;
  const statusFilter = document.getElementById('status-filter') as HTMLSelectElement | null;

  if (searchInput) {
    const debouncedSearch = debounce((target: HTMLInputElement) => {
      state.filters.search = target.value;
      state.currentPage = 1;
      void refreshUsers();
    }, 500);
    searchInput.addEventListener('input', (event) => {
      debouncedSearch(event.target as HTMLInputElement);
    });
  }

  if (roleFilter) {
    roleFilter.addEventListener('change', (event) => {
      const target = event.target as HTMLSelectElement;
      state.filters.role = target.value;
      state.currentPage = 1;
      void refreshUsers();
    });
  }

  if (statusFilter) {
    statusFilter.addEventListener('change', (event) => {
      const target = event.target as HTMLSelectElement;
      state.filters.status = target.value;
      state.currentPage = 1;
      void refreshUsers();
    });
  }
}

function setupPagination(): void {
  const prevBtn = document.getElementById('prev-page');
  const nextBtn = document.getElementById('next-page');

  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      if (state.currentPage > 1) {
        state.currentPage -= 1;
        void refreshUsers();
      }
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      if (state.currentPage < state.totalPages) {
        state.currentPage += 1;
        void refreshUsers();
      }
    });
  }
}

function initializeAdminUsersPage(): void {
  updateStaticTranslations();

  initMobileNav();

  const refreshBtn = document.getElementById('refresh-users-btn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      void refreshUsers();
    });
  }

  const closeBtn = document.getElementById('close-user-detail-btn');
  if (closeBtn) {
    closeBtn.addEventListener('click', closeUserDetailModal);
  }

  const cancelDeleteBtn = document.getElementById('cancel-delete-btn');
  if (cancelDeleteBtn) {
    cancelDeleteBtn.addEventListener('click', closeConfirmDeleteModal);
  }

  const cancelEditBtn = document.getElementById('cancel-edit-btn');
  if (cancelEditBtn) {
    cancelEditBtn.addEventListener('click', closeEditUserModal);
  }

  const saveBtn = document.getElementById('save-user-btn');
  if (saveBtn) {
    saveBtn.addEventListener('click', () => {
      void saveUser(state);
    });
  }

  setCreateUserFormCallbacks({
    onUserCreated: () => {
      state.currentPage = 1;
      return refreshUsers();
    },
  });

  setupFilters();
  setupPagination();
  setupCreateUserForm();
  void refreshUsers();
  void initAdminTotpPolicy();
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
).deleteUser = (userId: string, username: string) => deleteUser(userId, username, state);

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
).closeUserDetailModal = closeUserDetailModal;

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
).closeEditUserModal = closeEditUserModal;

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
).closeConfirmDeleteModal = closeConfirmDeleteModal;

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
).closeCreateUserModal = closeCreateUserModal;

initI18n(() => {
  try {
    initializeAdminUsersPage();
  } catch (error) {
    reportError('admin-users', 'initialize', error);
  }
});
