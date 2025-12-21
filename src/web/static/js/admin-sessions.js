/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/. */

// Admin Session Management JavaScript

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
        document.addEventListener('DOMContentLoaded', initAdminSessionsPage);
      } else {
        initAdminSessionsPage();
      }
    }
  );

// Constants
const API_BASE = '/api/admin';
const HIDDEN_CLASS = 'is-hidden';

// State
let allSessions = [];
let currentFilters = {
  search: '',
  user: 'all',
};
let currentSessionId = null;

// Utility Functions
function getAuthHeaders() {
  // With HTTP-only cookies, credentials are sent automatically
  return {
    'Content-Type': 'application/json',
  };
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

function showModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove(HIDDEN_CLASS);
}

function hideModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add(HIDDEN_CLASS);
}

// Close Modal Functions
window.closeSessionDetailModal = () => hideModal('session-detail-modal');
window.closeConfirmRevokeModal = () => hideModal('confirm-revoke-modal');

// Load All Sessions from All Users
async function loadAllSessions() {
  const tableBody = document.getElementById('sessions-table-body');
  tableBody.innerHTML =
    '<tr><td colspan="7" class="loading-cell"><div class="loading">Loading...</div></td></tr>';

  try {
    // First, get all users
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

    const usersData = await usersResponse.json();
    const users = usersData.users || [];

    // Populate user filter dropdown
    populateUserFilter(users);

    // Load sessions for each user
    allSessions = [];
    for (const user of users) {
      try {
        const sessionsResponse = await fetch(`${API_BASE}/users/${user.id}/sessions`, {
          credentials: 'include',
          headers: getAuthHeaders(),
        });

        if (sessionsResponse.ok) {
          const sessionsData = await sessionsResponse.json();
          const sessions = sessionsData.sessions || [];
          sessions.forEach((session) => {
            session.username = user.username;
            session.userId = user.id;
            allSessions.push(session);
          });
        }
      } catch (error) {
        console.error(`Error loading sessions for user ${user.username}:`, error);
      }
    }

    // Update stats
    updateStats();

    // Filter and display sessions
    displaySessions();

    // Update translations for action buttons
    updateTranslations();
  } catch (error) {
    console.error('Error loading sessions:', error);
    tableBody.innerHTML =
      '<tr><td colspan="7" class="loading-cell">Error loading sessions</td></tr>';
  }
}

function populateUserFilter(users) {
  const userFilter = document.getElementById('user-filter');
  if (!userFilter) return;

  // Keep "All Users" option and add users
  const currentValue = userFilter.value;
  userFilter.innerHTML =
    '<option value="all" data-i18n="admin.sessions.allUsers">All Users</option>';

  users.forEach((user) => {
    const option = document.createElement('option');
    option.value = user.id; // Use user ID, not username
    option.textContent = user.username;
    option.dataset.username = user.username; // Store username for display
    userFilter.appendChild(option);
  });

  // Restore previous selection if it still exists
  if (currentValue !== 'all') {
    userFilter.value = currentValue;
  }
}

function displaySessions() {
  const tableBody = document.getElementById('sessions-table-body');

  // Apply filters
  let filteredSessions = allSessions;

  // Filter out revoked sessions by default (only show active ones)
  filteredSessions = filteredSessions.filter((session) => !session.is_revoked);

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

  // Render sessions
  if (filteredSessions.length === 0) {
    tableBody.innerHTML =
      '<tr><td colspan="7" class="loading-cell">No active sessions found</td></tr>';
  } else {
    tableBody.innerHTML = filteredSessions
      .map(
        (session) => `
            <tr>
                <td>${session.username || 'Unknown'}</td>
                <td>${session.ip_address || 'Unknown'}</td>
                <td title="${session.user_agent || 'Unknown'}">${truncateText(session.user_agent || 'Unknown', 50)}</td>
                <td>${formatDate(session.created_at)}</td>
                <td>${formatDate(session.last_used_at)}</td>
                <td>${formatDate(session.expires_at)}</td>
                <td>
                    <div class="action-buttons">
                        <button class="action-btn revoke" onclick="showRevokeConfirmation('${session.userId}', '${session.id}', '${session.username}')" data-i18n="actions.revoke">Revoke</button>
                    </div>
                </td>
            </tr>
        `
      )
      .join('');
    // Update translations for newly rendered buttons
    updateTranslations();
  }
}

function truncateText(text, maxLength) {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
}

function updateStats() {
  // Count only non-revoked sessions for "Total Sessions"
  const nonRevokedSessions = allSessions.filter((session) => !session.is_revoked).length;
  document.getElementById('total-sessions').textContent = nonRevokedSessions;

  // Count active sessions (not revoked AND not expired)
  const now = new Date();
  const activeSessions = allSessions.filter((session) => {
    const expiresAt = new Date(session.expires_at);
    return !session.is_revoked && expiresAt > now;
  }).length;
  document.getElementById('active-sessions').textContent = activeSessions;

  // Count unique users with active sessions
  const usersWithActiveSessions = new Set(
    allSessions.filter((session) => !session.is_revoked).map((s) => s.username)
  );
  document.getElementById('unique-users').textContent = usersWithActiveSessions.size;
}

// Revoke Session
window.showRevokeConfirmation = function (userId, sessionId, username) {
  currentSessionId = { userId, sessionId, username };
  showModal('confirm-revoke-modal');
};

document.addEventListener('DOMContentLoaded', () => {
  const confirmBtn = document.getElementById('confirm-revoke-btn');
  if (confirmBtn) {
    confirmBtn.addEventListener('click', async () => {
      if (!currentSessionId) return;

      const { userId, sessionId, username } = currentSessionId;

      try {
        const response = await fetch(`${API_BASE}/users/${userId}/sessions/${sessionId}`, {
          credentials: 'include',
          method: 'DELETE',
          headers: getAuthHeaders(),
        });

        if (response.ok) {
          showNotification(`Session for ${username} revoked successfully`, 'success');
          hideModal('confirm-revoke-modal');
          loadAllSessions();
        } else {
          const data = await response.json();
          showNotification(data.detail || 'Failed to revoke session', 'error');
        }
      } catch (error) {
        console.error('Error revoking session:', error);
        showNotification('Failed to revoke session', 'error');
      }
    });
  }

  const cancelBtn = document.getElementById('cancel-revoke-btn');
  if (cancelBtn) {
    cancelBtn.addEventListener('click', () => {
      hideModal('confirm-revoke-modal');
      currentSessionId = null;
    });
  }
});

// Setup Filters
function setupFilters() {
  const searchInput = document.getElementById('search-input');
  const userFilter = document.getElementById('user-filter');

  if (searchInput) {
    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        currentFilters.search = e.target.value;
        displaySessions();
      }, 500);
    });
  }

  if (userFilter) {
    userFilter.addEventListener('change', (e) => {
      currentFilters.user = e.target.value;
      displaySessions();
    });
  }
}

// Initialize Page
function initAdminSessionsPage() {
  updateTranslations();

  const languageSelector = document.getElementById('language-selector');
  if (languageSelector) {
    languageSelector.addEventListener('change', (e) => {
      i18next.changeLanguage(e.target.value, () => {
        updateTranslations();
      });
    });
  }

  const refreshBtn = document.getElementById('refresh-sessions-btn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', loadAllSessions);
  }

  const revokeAllBtn = document.getElementById('revoke-all-sessions-btn');
  if (revokeAllBtn) {
    revokeAllBtn.addEventListener('click', revokeAllSessions);
  }

  setupFilters();
  loadAllSessions();
}

// Revoke All Sessions Function
async function revokeAllSessions() {
  const userFilter = document.getElementById('user-filter');
  const selectedUserId = userFilter.value;

  if (selectedUserId === 'all') {
    showNotification('Please select a specific user to revoke all their sessions', 'error');
    return;
  }

  const selectedUserText = userFilter.options[userFilter.selectedIndex].text;

  if (
    !confirm(
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
      const data = await response.json();
      showNotification(
        `${data.revoked_count} session(s) revoked for ${selectedUserText}`,
        'success'
      );
      await loadAllSessions();
    } else {
      const data = await response.json();
      showNotification(data.detail || 'Failed to revoke sessions', 'error');
    }
  } catch (error) {
    console.error('Error revoking sessions:', error);
    showNotification('Failed to revoke sessions', 'error');
  }
}
