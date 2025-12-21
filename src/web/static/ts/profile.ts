/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Profile management logic
 */

import { reportError } from '@/telemetry';
import { changeLanguage, initI18n, t, updateStaticTranslations } from '@/utils/i18n';
import { clearAllErrors, hideElement, showElement, showError } from '@/utils/dom';
import { showNotification } from '@/utils/notifications';

const API_BASE = '/api/auth';

interface PasswordChecks {
  length: boolean;
  uppercase: boolean;
  lowercase: boolean;
  digit: boolean;
  special: boolean;
}

interface SessionItem {
  id?: string;
  session_id?: string;
  device?: string;
  browser?: string;
  os?: string;
  is_current?: boolean;
  ip_address?: string | null;
  last_used_at?: string | null;
  expires_at?: string | null;
}

interface UserInfo {
  username: string;
  email: string;
  role: string;
  created_at?: string | null;
  last_login?: string | null;
}

function getAuthHeaders(): HeadersInit {
  return {
    'Content-Type': 'application/json'
  };
}

function formatDate(dateString?: string | null): string {
  if (!dateString) return 'Never';
  const date = new Date(dateString);
  return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
}

function getExpirationStatus(expiresAtString?: string | null): {
  status: string;
  className: string;
  message: string;
} {
  if (!expiresAtString) return { status: 'unknown', className: '', message: '' };

  const now = new Date();
  const expiresAt = new Date(expiresAtString);
  const hoursUntilExpiry = (expiresAt.getTime() - now.getTime()) / (1000 * 60 * 60);

  if (expiresAt <= now) {
    return { status: 'expired', className: 'expired', message: '(Expired)' };
  }
  if (hoursUntilExpiry < 24) {
    return {
      status: 'expiring-soon',
      className: 'expires-soon',
      message: `(Expires in ${Math.round(hoursUntilExpiry)}h)`
    };
  }

  return { status: 'active', className: 'active', message: '' };
}

function checkPasswordStrength(password: string): { strength: number; checks: PasswordChecks } {
  const checks: PasswordChecks = {
    length: password.length >= 12,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    digit: /[0-9]/.test(password),
    special: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)
  };

  const strength = Object.values(checks).filter(Boolean).length;
  return { strength, checks };
}

function updatePolicyRequirements(checks: PasswordChecks): void {
  const policyMap: Record<keyof PasswordChecks, string> = {
    length: 'policy-length',
    uppercase: 'policy-uppercase',
    lowercase: 'policy-lowercase',
    digit: 'policy-digit',
    special: 'policy-special'
  };

  (Object.entries(checks) as Array<[keyof PasswordChecks, boolean]>).forEach(([check, met]) => {
    const element = document.getElementById(policyMap[check]);
    if (element) {
      element.classList.toggle('met', met);
    }
  });
}

function updatePasswordStrength(password: string): void {
  const { strength, checks } = checkPasswordStrength(password);
  const strengthBar = document.getElementById('strength-bar-fill');
  const strengthText = document.getElementById('strength-text');

  if (!strengthBar || !strengthText) return;

  strengthBar.className = 'strength-bar-fill';
  if (strength >= 5) {
    strengthBar.classList.add('strength-strong');
    strengthText.textContent = t('auth.register.strengthStrong') || 'Strong password';
    strengthText.className = 'strength-text strength-strong';
  } else if (strength >= 3) {
    strengthBar.classList.add('strength-medium');
    strengthText.textContent = t('auth.register.strengthMedium') || 'Medium password';
    strengthText.className = 'strength-text strength-medium';
  } else if (password.length > 0) {
    strengthBar.classList.add('strength-weak');
    strengthText.textContent = t('auth.register.strengthWeak') || 'Weak password';
    strengthText.className = 'strength-text strength-weak';
  } else {
    strengthText.textContent = '';
  }

  updatePolicyRequirements(checks);
}

function setupPasswordToggle(toggleButtonId: string, passwordInputId: string): void {
  const toggleButton = document.getElementById(toggleButtonId);
  const passwordInput = document.getElementById(passwordInputId) as HTMLInputElement | null;

  if (toggleButton && passwordInput) {
    toggleButton.addEventListener('click', () => {
      passwordInput.type = passwordInput.type === 'password' ? 'text' : 'password';
    });
  }
}

async function loadSessions(): Promise<void> {
  const sessionsList = document.getElementById('sessions-list');
  if (!sessionsList) return;

  sessionsList.innerHTML = '<div class="loading" data-i18n="messages.loading">Loading...</div>';

  try {
    const response = await fetch(`${API_BASE}/sessions`, {
      credentials: 'include',
      headers: getAuthHeaders()
    });

    if (response.ok) {
      const data = (await response.json()) as { sessions?: SessionItem[] };
      const sessions = data.sessions ?? [];

      const sessionCount = document.getElementById('session-count');
      if (sessionCount) {
        sessionCount.textContent = String(sessions.length);
      }

      if (sessions.length === 0) {
        sessionsList.innerHTML = '<p>No active sessions</p>';
        return;
      }

      sessionsList.innerHTML = sessions
        .map((session) => {
          const expirationStatus = getExpirationStatus(session.expires_at ?? null);
          const deviceDisplay = session.device || 'Unknown Device';
          const browserDisplay = session.browser ? `${session.browser}` : 'Unknown Browser';
          const osDisplay = session.os ? `${session.os}` : 'Unknown OS';
          const sessionId = session.id || session.session_id || '';

          return `
            <div class="session-item ${session.is_current ? 'current-session' : ''} ${expirationStatus.className}" data-session-id="${sessionId}">
              <div class="session-info">
                <div class="session-header">
                  <div class="session-device">${deviceDisplay}</div>
                  ${session.is_current ? '<span class="badge current-badge">Current Session</span>' : ''}
                </div>
                <div class="session-metadata">
                  <div class="device-details">${browserDisplay} on ${osDisplay}</div>
                  <div class="session-details">
                    IP: ${session.ip_address || 'Unknown'} |
                    Last used: ${formatDate(session.last_used_at)} |
                    Expires: ${formatDate(session.expires_at)} <span class="expiration-badge">${expirationStatus.message}</span>
                  </div>
                </div>
              </div>
              <div class="session-actions">
                <button onclick="window.revokeSession('${sessionId}')" ${session.is_current ? 'disabled' : ''}>
                  ${t('auth.profile.revokeSession') || 'Revoke'}
                </button>
              </div>
            </div>
          `;
        })
        .join('');
    }
  } catch (error) {
    reportError('profile', 'loadSessions', error);
    sessionsList.innerHTML = '<p class="error">Failed to load sessions</p>';
  }
}

async function loadUserInfo(): Promise<void> {
  try {
    const response = await fetch(`${API_BASE}/me`, {
      credentials: 'include',
      headers: getAuthHeaders()
    });

    if (response.ok) {
      const user = (await response.json()) as UserInfo;

      const usernameEl = document.getElementById('user-username');
      const emailEl = document.getElementById('user-email');
      const roleEl = document.getElementById('user-role');
      const avatarEl = document.getElementById('user-avatar');

      if (usernameEl) usernameEl.textContent = user.username;
      if (emailEl) emailEl.textContent = user.email;
      if (roleEl) roleEl.textContent = user.role.toUpperCase();
      if (avatarEl) avatarEl.textContent = user.username.charAt(0).toUpperCase();

      const createdEl = document.getElementById('user-created');
      const lastLoginEl = document.getElementById('user-last-login');
      if (createdEl) createdEl.textContent = formatDate(user.created_at);
      if (lastLoginEl) lastLoginEl.textContent = formatDate(user.last_login);

      if (user.role === 'admin') {
        const adminBtn = document.getElementById('admin-btn');
        if (adminBtn) {
          (adminBtn as HTMLElement).style.display = '';
        }
      }

      await loadSessions();
    } else if (response.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/auth/login';
    }
  } catch (error) {
    reportError('profile', 'loadUserInfo', error);
    showNotification(t('messages.error') || 'Failed to load user info', 'error');
  }
}

async function revokeSession(sessionId: string): Promise<void> {
  if (!sessionId) return;
  if (!window.confirm(t('auth.profile.confirmRevokeSession') || 'Are you sure you want to revoke this session?')) {
    return;
  }

  try {
    const response = await fetch(`${API_BASE}/sessions/${sessionId}`, {
      credentials: 'include',
      method: 'DELETE',
      headers: getAuthHeaders()
    });

    if (response.ok) {
      showNotification(t('auth.profile.sessionRevoked') || 'Session revoked successfully', 'success');
      await loadSessions();
    } else {
      showNotification(t('messages.error') || 'Failed to revoke session', 'error');
    }
  } catch (error) {
    reportError('profile', 'revokeSession', error);
    showNotification(t('messages.error') || 'Failed to revoke session', 'error');
  }
}

function setupChangePasswordForm(): void {
  const form = document.getElementById('change-password-form') as HTMLFormElement | null;
  if (!form) return;

  setupPasswordToggle('toggle-current-password', 'current-password');
  setupPasswordToggle('toggle-new-password', 'new-password');
  setupPasswordToggle('toggle-confirm-new-password', 'confirm-new-password');

  const newPasswordInput = document.getElementById('new-password') as HTMLInputElement | null;
  if (newPasswordInput) {
    newPasswordInput.addEventListener('input', () => {
      updatePasswordStrength(newPasswordInput.value);
    });
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    clearAllErrors();

    const currentPassword = (document.getElementById('current-password') as HTMLInputElement | null)?.value ?? '';
    const newPassword = (document.getElementById('new-password') as HTMLInputElement | null)?.value ?? '';
    const confirmNewPassword =
      (document.getElementById('confirm-new-password') as HTMLInputElement | null)?.value ?? '';

    let hasErrors = false;

    if (!currentPassword) {
      showError(
        document.getElementById('current-password-error'),
        t('auth.profile.currentPasswordRequired') || 'Current password is required'
      );
      hasErrors = true;
    }

    const { checks } = checkPasswordStrength(newPassword);
    if (!Object.values(checks).every((value) => value)) {
      showError(
        document.getElementById('new-password-error'),
        t('auth.register.passwordPolicy') || 'Password does not meet requirements'
      );
      hasErrors = true;
    }

    if (newPassword !== confirmNewPassword) {
      showError(
        document.getElementById('confirm-new-password-error'),
        t('auth.register.passwordMismatch') || 'Passwords do not match'
      );
      hasErrors = true;
    }

    if (hasErrors) return;

    const submitButton = form.querySelector('button[type="submit"]') as HTMLButtonElement | null;
    if (submitButton) {
      submitButton.disabled = true;
      submitButton.textContent = t('messages.loading') || 'Loading...';
    }

    try {
      const response = await fetch(`${API_BASE}/change-password`, {
        credentials: 'include',
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          old_password: currentPassword,
          new_password: newPassword,
          confirm_new_password: confirmNewPassword
        })
      });

      const data = (await response.json()) as Record<string, string>;

      if (response.ok) {
        showNotification(t('auth.profile.passwordChanged') || 'Password changed successfully', 'success');
        form.reset();
        clearAllErrors();
      } else if (response.status === 401) {
        showError(
          document.getElementById('current-password-error'),
          data.detail || t('auth.profile.incorrectPassword') || 'Incorrect current password'
        );
      } else {
        showNotification(data.detail || t('messages.error') || 'Failed to change password', 'error');
      }
    } catch (error) {
      reportError('profile', 'changePassword', error);
      showNotification(t('messages.error') || 'Failed to change password', 'error');
    } finally {
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = t('auth.profile.updatePassword') || 'Update Password';
      }
    }
  });
}

function setupLogout(): void {
  const logoutBtn = document.getElementById('logout-btn');
  if (!logoutBtn) return;

  logoutBtn.addEventListener('click', async () => {
    try {
      const refreshToken = localStorage.getItem('refresh_token') || sessionStorage.getItem('refresh_token');
      if (refreshToken) {
        await fetch(`${API_BASE}/logout`, {
          credentials: 'include',
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ refresh_token: refreshToken })
        });
      }
    } catch (error) {
      reportError('profile', 'logout', error);
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      sessionStorage.removeItem('access_token');
      sessionStorage.removeItem('refresh_token');
      window.location.href = '/auth/login';
    }
  });
}

async function checkAdminAccess(): Promise<void> {
  try {
    const response = await fetch('/api/auth/me', {
      credentials: 'include'
    });

    if (response.ok) {
      const data = (await response.json()) as UserInfo;

      if (data.role === 'admin') {
        const adminBtn = document.getElementById('admin-btn');
        if (adminBtn) {
          (adminBtn as HTMLElement).style.display = '';
        }
      }
    } else if (response.status === 401) {
      window.location.href = '/auth/login';
    } else {
      window.location.href = '/auth/login';
    }
  } catch (error) {
    reportError('profile', 'checkAdminAccess', error);
    window.location.href = '/auth/login';
  }
}

function initializeProfilePage(): void {
  updateStaticTranslations();

  const languageSelector = document.getElementById('language-selector') as HTMLSelectElement | null;
  if (languageSelector) {
    languageSelector.addEventListener('change', (event) => {
      const target = event.target as HTMLSelectElement;
      changeLanguage(target.value).catch((error) => {
        reportError('profile', 'changeLanguage', error);
      });
    });
  }

  checkAdminAccess();
  void loadUserInfo();
  setupChangePasswordForm();
  setupLogout();
}

(window as Window & { revokeSession?: (sessionId: string) => Promise<void> }).revokeSession = revokeSession;

initI18n(() => {
  try {
    initializeProfilePage();
  } catch (error) {
    reportError('profile', 'initialize', error);
  }
});
