/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Admin session management logic
 */

import '../css/tailwind-globals.css';
import { reportError } from '@/telemetry';
import { changeLanguage, initI18n, updateStaticTranslations } from '@/utils/i18n';
import { showNotification } from '@/utils/notifications';

const API_BASE = '/api/admin';
const HIDDEN_CLASS = 'is-hidden';

interface AdminUser {
  id: string;
  username: string;
}

interface SessionItem {
  id: string;
  userId?: string;
  username?: string;
  ip_address?: string | null;
  user_agent?: string | null;
  created_at?: string | null;
  last_used_at?: string | null;
  expires_at?: string | null;
  is_revoked?: boolean;
}

let allSessions: SessionItem[] = [];
let currentFilters = {
  search: '',
  user: 'all',
};
let currentSession: { userId: string; sessionId: string; username: string } | null = null;

function getAuthHeaders(): HeadersInit {
  return {
    'Content-Type': 'application/json',
  };
}

function formatDate(dateString?: string | null): string {
  if (!dateString) return 'Never';
  const date = new Date(dateString);
  return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
}

function showModal(modalId: string): void {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove(HIDDEN_CLASS);
}

function hideModal(modalId: string): void {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add(HIDDEN_CLASS);
}

function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return `${text.substring(0, maxLength)}...`;
}

function updateStats(): void {
  const totalSessionsEl = document.getElementById('total-sessions');
  const activeSessionsEl = document.getElementById('active-sessions');
  const uniqueUsersEl = document.getElementById('unique-users');

  const nonRevokedSessions = allSessions.filter((session) => !session.is_revoked).length;
  if (totalSessionsEl) totalSessionsEl.textContent = String(nonRevokedSessions);

  const now = new Date();
  const activeSessions = allSessions.filter((session) => {
    const expiresAt = session.expires_at ? new Date(session.expires_at) : null;
    return !session.is_revoked && expiresAt !== null && expiresAt > now;
  }).length;
  if (activeSessionsEl) activeSessionsEl.textContent = String(activeSessions);

  const usersWithActiveSessions = new Set(
    allSessions.filter((session) => !session.is_revoked).map((session) => session.username)
  );
  if (uniqueUsersEl) uniqueUsersEl.textContent = String(usersWithActiveSessions.size);
}

function populateUserFilter(users: AdminUser[]): void {
  const userFilter = document.getElementById('user-filter') as HTMLSelectElement | null;
  if (!userFilter) return;

  const currentValue = userFilter.value;
  userFilter.innerHTML =
    '<option value="all" data-i18n="admin.sessions.allUsers">All Users</option>';

  users.forEach((user) => {
    const option = document.createElement('option');
    option.value = user.id;
    option.textContent = user.username;
    option.dataset.username = user.username;
    userFilter.appendChild(option);
  });

  if (currentValue !== 'all') {
    userFilter.value = currentValue;
  }
}

function displaySessions(): void {
  const tableBody = document.getElementById('sessions-table-body');
  if (!tableBody) return;

  let filteredSessions = allSessions.filter((session) => !session.is_revoked);

  if (currentFilters.search) {
    const searchLower = currentFilters.search.toLowerCase();
    filteredSessions = filteredSessions.filter(
      (session) =>
        (session.username && session.username.toLowerCase().includes(searchLower)) ||
        (session.ip_address && session.ip_address.includes(searchLower)) ||
        (session.user_agent && session.user_agent.toLowerCase().includes(searchLower))
    );
  }

  if (currentFilters.user !== 'all') {
    filteredSessions = filteredSessions.filter((session) => session.userId === currentFilters.user);
  }

  if (filteredSessions.length === 0) {
    tableBody.innerHTML =
      '<tr><td colspan="7" class="loading-cell">No active sessions found</td></tr>';
    return;
  }

  tableBody.innerHTML = filteredSessions
    .map((session) => {
      const username = session.username || 'Unknown';
      const userAgent = session.user_agent || 'Unknown';
      const ipAddress = session.ip_address || 'Unknown';
      const userId = session.userId || '';
      const sessionId = session.id;

      return `
        <tr>
          <td>${username}</td>
          <td>${ipAddress}</td>
          <td title="${userAgent}">${truncateText(userAgent, 50)}</td>
          <td>${formatDate(session.created_at)}</td>
          <td>${formatDate(session.last_used_at)}</td>
          <td>${formatDate(session.expires_at)}</td>
          <td>
            <div class="action-buttons">
              <button class="action-btn revoke" onclick="window.showRevokeConfirmation('${userId}', '${sessionId}', '${username}')" data-i18n="actions.revoke">Revoke</button>
            </div>
          </td>
        </tr>
      `;
    })
    .join('');

  updateStaticTranslations();
}

async function loadAllSessions(): Promise<void> {
  const tableBody = document.getElementById('sessions-table-body');
  if (tableBody) {
    tableBody.innerHTML =
      '<tr><td colspan="7" class="loading-cell"><div class="loading">Loading...</div></td></tr>';
  }

  try {
    const usersResponse = await fetch(`${API_BASE}/users?limit=1000`, {
      credentials: 'include',
      headers: getAuthHeaders(),
    });

    if (!usersResponse.ok) {
      if (usersResponse.status === 401) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/auth/login';
        return;
      }
      throw new Error('Failed to load users');
    }

    const usersData = (await usersResponse.json()) as { users?: AdminUser[] };
    const users = usersData.users || [];

    populateUserFilter(users);

    allSessions = [];
    for (const user of users) {
      try {
        const sessionsResponse = await fetch(`${API_BASE}/users/${user.id}/sessions`, {
          credentials: 'include',
          headers: getAuthHeaders(),
        });

        if (sessionsResponse.ok) {
          const sessionsData = (await sessionsResponse.json()) as { sessions?: SessionItem[] };
          const sessions = sessionsData.sessions || [];
          sessions.forEach((session) => {
            session.username = user.username;
            session.userId = user.id;
            allSessions.push(session);
          });
        }
      } catch (error) {
        reportError('admin-sessions', 'loadUserSessions', error, { userId: user.id });
      }
    }

    updateStats();
    displaySessions();
  } catch (error) {
    reportError('admin-sessions', 'loadAllSessions', error);
    if (tableBody) {
      tableBody.innerHTML =
        '<tr><td colspan="7" class="loading-cell">Error loading sessions</td></tr>';
    }
  }
}

async function revokeSession(userId: string, sessionId: string, username: string): Promise<void> {
  try {
    const response = await fetch(`${API_BASE}/users/${userId}/sessions/${sessionId}`, {
      credentials: 'include',
      method: 'DELETE',
      headers: getAuthHeaders(),
    });

    if (response.ok) {
      showNotification(`Session for ${username} revoked successfully`, 'success');
      hideModal('confirm-revoke-modal');
      await loadAllSessions();
    } else {
      const data = (await response.json()) as Record<string, string>;
      showNotification(data.detail || 'Failed to revoke session', 'error');
    }
  } catch (error) {
    reportError('admin-sessions', 'revokeSession', error, { userId, sessionId });
    showNotification('Failed to revoke session', 'error');
  }
}

function setupFilters(): void {
  const searchInput = document.getElementById('search-input') as HTMLInputElement | null;
  const userFilter = document.getElementById('user-filter') as HTMLSelectElement | null;

  if (searchInput) {
    let searchTimeout: number | null = null;
    searchInput.addEventListener('input', (event) => {
      const target = event.target as HTMLInputElement;
      if (searchTimeout) {
        window.clearTimeout(searchTimeout);
      }
      searchTimeout = window.setTimeout(() => {
        currentFilters.search = target.value;
        displaySessions();
      }, 500);
    });
  }

  if (userFilter) {
    userFilter.addEventListener('change', (event) => {
      const target = event.target as HTMLSelectElement;
      currentFilters.user = target.value;
      displaySessions();
    });
  }
}

async function revokeAllSessions(): Promise<void> {
  const userFilter = document.getElementById('user-filter') as HTMLSelectElement | null;
  if (!userFilter) return;

  const selectedUserId = userFilter.value;
  if (selectedUserId === 'all') {
    showNotification('Please select a specific user to revoke all their sessions', 'error');
    return;
  }

  const selectedOption =
    userFilter.selectedOptions[0] ||
    (userFilter.selectedIndex >= 0 ? userFilter.options[userFilter.selectedIndex] : null);
  const selectedUserText = selectedOption?.text ?? '';
  if (
    !window.confirm(
      `Are you sure you want to revoke ALL sessions for user "${selectedUserText}"? They will be logged out of all devices.`
    )
  ) {
    return;
  }

  try {
    const response = await fetch(`${API_BASE}/users/${selectedUserId}/sessions`, {
      method: 'DELETE',
      credentials: 'include',
      headers: getAuthHeaders(),
    });

    if (response.ok) {
      const data = (await response.json()) as { revoked_count?: number };
      showNotification(
        `${data.revoked_count || 0} session(s) revoked for ${selectedUserText}`,
        'success'
      );
      await loadAllSessions();
    } else {
      const data = (await response.json()) as Record<string, string>;
      showNotification(data.detail || 'Failed to revoke sessions', 'error');
    }
  } catch (error) {
    reportError('admin-sessions', 'revokeAll', error, { userId: selectedUserId });
    showNotification('Failed to revoke sessions', 'error');
  }
}

function setupConfirmRevokeModal(): void {
  const confirmBtn = document.getElementById('confirm-revoke-btn');
  if (confirmBtn) {
    confirmBtn.addEventListener('click', () => {
      if (!currentSession) return;
      void revokeSession(currentSession.userId, currentSession.sessionId, currentSession.username);
    });
  }

  const cancelBtn = document.getElementById('cancel-revoke-btn');
  if (cancelBtn) {
    cancelBtn.addEventListener('click', () => {
      hideModal('confirm-revoke-modal');
      currentSession = null;
    });
  }
}

function initializeAdminSessionsPage(): void {
  updateStaticTranslations();

  const languageSelector = document.getElementById('language-selector') as HTMLSelectElement | null;
  if (languageSelector) {
    languageSelector.addEventListener('change', (event) => {
      const target = event.target as HTMLSelectElement;
      changeLanguage(target.value).catch((error) => {
        reportError('admin-sessions', 'changeLanguage', error);
      });
    });
  }

  const refreshBtn = document.getElementById('refresh-sessions-btn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      void loadAllSessions();
    });
  }

  const revokeAllBtn = document.getElementById('revoke-all-sessions-btn');
  if (revokeAllBtn) {
    revokeAllBtn.addEventListener('click', () => {
      void revokeAllSessions();
    });
  }

  setupFilters();
  setupConfirmRevokeModal();
  void loadAllSessions();
}

(
  window as Window & {
    showRevokeConfirmation?: (userId: string, sessionId: string, username: string) => void;
    closeSessionDetailModal?: () => void;
    closeConfirmRevokeModal?: () => void;
  }
).showRevokeConfirmation = (userId: string, sessionId: string, username: string) => {
  currentSession = { userId, sessionId, username };
  showModal('confirm-revoke-modal');
};

(
  window as Window & {
    showRevokeConfirmation?: (userId: string, sessionId: string, username: string) => void;
    closeSessionDetailModal?: () => void;
    closeConfirmRevokeModal?: () => void;
  }
).closeSessionDetailModal = () => hideModal('session-detail-modal');

(
  window as Window & {
    showRevokeConfirmation?: (userId: string, sessionId: string, username: string) => void;
    closeSessionDetailModal?: () => void;
    closeConfirmRevokeModal?: () => void;
  }
).closeConfirmRevokeModal = () => hideModal('confirm-revoke-modal');

initI18n(() => {
  try {
    initializeAdminSessionsPage();
  } catch (error) {
    reportError('admin-sessions', 'initialize', error);
  }
});
