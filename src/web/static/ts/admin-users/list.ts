/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { tUnsafe } from '@/utils/i18n';
import { escapeHtml } from '@/utils/dom';
import type { AdminUser, UsersResponse } from './types';

export function formatDate(dateString?: string | null): string {
  if (!dateString) return 'Never';
  const date = new Date(dateString);
  return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
}

export function getTranslatedRole(role: string): string {
  const roleTranslations: Record<string, string> = {
    viewer: 'roleViewer',
    editor: 'roleEditor',
    admin: 'roleAdmin',
    user: 'roleUser',
  };
  const translationKey = roleTranslations[role] || role;
  return tUnsafe(`admin.users.${translationKey}`) || role;
}

export function getStatusClass(user: AdminUser): string {
  if (user.locked_until && new Date(user.locked_until) > new Date()) {
    return 'locked';
  }
  return user.is_active ? 'active' : 'inactive';
}

export function getStatusText(user: AdminUser): string {
  if (user.locked_until && new Date(user.locked_until) > new Date()) {
    return 'Locked';
  }
  return user.is_active ? 'Active' : 'Inactive';
}

export function updateStats(data: UsersResponse): void {
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

export function updatePagination(currentPage: number, totalPages: number): void {
  const pageInfo = document.getElementById('page-info');
  const prevBtn = document.getElementById('prev-page') as HTMLButtonElement | null;
  const nextBtn = document.getElementById('next-page') as HTMLButtonElement | null;

  if (pageInfo) pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
  if (prevBtn) prevBtn.disabled = currentPage === 1;
  if (nextBtn) nextBtn.disabled = currentPage === totalPages;
}

export interface RenderUsersTableCallbacks {
  onView: (userId: string, trigger: HTMLElement) => void;
  onEdit: (userId: string, trigger: HTMLElement) => void;
  onDelete: (userId: string, username: string, trigger: HTMLElement) => void;
}

export function renderUsersTable(
  tableBody: HTMLElement,
  users: AdminUser[],
  callbacks: RenderUsersTableCallbacks
): void {
  if (users.length === 0) {
    tableBody.innerHTML =
      '<tr><td colspan="7" class="px-6 py-4 text-center text-gray-500 dark:text-gray-400">No users found</td></tr>';
    return;
  }

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
          <tr class="hover:bg-gray-50 dark:hover:bg-gray-800">
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100">${escapeHtml(user.username)}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">${escapeHtml(user.email)}</td>
            <td class="px-6 py-4 whitespace-nowrap"><span class="inline-block px-3 py-1 rounded-full text-xs font-medium ${roleBadgeClass}">${getTranslatedRole(user.role)}</span></td>
            <td class="px-6 py-4 whitespace-nowrap"><span class="inline-block px-3 py-1 rounded-full text-xs font-medium ${statusBadgeClass}">${getStatusText(user)}</span></td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">${formatDate(user.last_login)}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">${user.session_count || 0}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm">
              <div class="flex space-x-2">
                <button class="px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 text-xs font-medium focus:outline-2 focus:outline-blue-500 focus:outline-offset-1" data-action="view-user" data-user-id="${escapeHtml(user.id)}" aria-label="View user ${escapeHtml(user.username)}" data-i18n="actions.view">View</button>
                <button class="px-3 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 text-xs font-medium focus:outline-2 focus:outline-gray-500 focus:outline-offset-1 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600" data-action="edit-user" data-user-id="${escapeHtml(user.id)}" aria-label="Edit user ${escapeHtml(user.username)}" data-i18n="actions.edit">Edit</button>
                <button class="px-3 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200 text-xs font-medium focus:outline-2 focus:outline-red-500 focus:outline-offset-1" data-action="delete-user" data-user-id="${escapeHtml(user.id)}" data-user-name="${escapeHtml(user.username)}" aria-label="Delete user ${escapeHtml(user.username)}" data-i18n="actions.delete">Delete</button>
              </div>
            </td>
          </tr>
        `;
    })
    .join('');

  tableBody.querySelectorAll<HTMLButtonElement>('button[data-action="view-user"]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const userId = btn.getAttribute('data-user-id');
      if (userId) {
        callbacks.onView(userId, btn);
      }
    });
  });

  tableBody.querySelectorAll<HTMLButtonElement>('button[data-action="edit-user"]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const userId = btn.getAttribute('data-user-id');
      if (userId) {
        callbacks.onEdit(userId, btn);
      }
    });
  });

  tableBody.querySelectorAll<HTMLButtonElement>('button[data-action="delete-user"]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const userId = btn.getAttribute('data-user-id');
      const username = btn.getAttribute('data-user-name');
      if (userId && username) {
        callbacks.onDelete(userId, username, btn);
      }
    });
  });
}
