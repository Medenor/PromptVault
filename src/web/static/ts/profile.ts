/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Profile management logic
 */

import '../css/tailwind-globals.css';
import { reportError } from '@/telemetry';
import { changeLanguage, initI18n, t, updateStaticTranslations } from '@/utils/i18n';
import { clearAllErrors, showError } from '@/utils/dom';
import { showNotification } from '@/utils/notifications';
import { apiGet, apiPost, apiDelete, APIRequestError } from '@/utils/api';

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
      message: `(Expires in ${Math.round(hoursUntilExpiry)}h)`,
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
    special: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password),
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
    special: 'policy-special',
  };

  (Object.entries(checks) as Array<[keyof PasswordChecks, boolean]>).forEach(([check, met]) => {
    const element = document.getElementById(policyMap[check]);
    if (element) {
      const icon = element.querySelector('.policy-icon');
      if (icon) {
        icon.textContent = met ? '✓' : '○';
      }
      if (met) {
        element.classList.add('text-green-600');
        element.classList.remove('text-gray-600');
      } else {
        element.classList.add('text-gray-600');
        element.classList.remove('text-green-600');
      }
    }
  });
}

function updatePasswordStrength(password: string): void {
  const { strength, checks } = checkPasswordStrength(password);
  const strengthBar = document.getElementById('strength-bar-fill');
  const strengthText = document.getElementById('strength-text');

  if (!strengthBar || !strengthText) return;

  // Reset classes and set base Tailwind classes
  strengthBar.className = 'h-full transition-all duration-200';

  if (strength >= 5) {
    strengthBar.classList.add('bg-green-500', 'w-full');
    strengthText.textContent = t('auth.register.strengthStrong') || 'Strong password';
    strengthText.className = 'text-xs text-green-600 mt-1';
  } else if (strength >= 3) {
    strengthBar.classList.add('bg-yellow-500', 'w-3/5');
    strengthText.textContent = t('auth.register.strengthMedium') || 'Medium password';
    strengthText.className = 'text-xs text-yellow-600 mt-1';
  } else if (password.length > 0) {
    strengthBar.classList.add('bg-red-500', 'w-2/5');
    strengthText.textContent = t('auth.register.strengthWeak') || 'Weak password';
    strengthText.className = 'text-xs text-red-600 mt-1';
  } else {
    strengthBar.classList.add('bg-gray-300', 'w-0');
    strengthText.textContent = '';
    strengthText.className = 'text-xs text-gray-600 mt-1';
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

  sessionsList.innerHTML =
    '<div class="text-gray-600 text-sm" data-i18n="messages.loading">Loading...</div>';

  try {
    const data = await apiGet<{ sessions?: SessionItem[] }>(`${API_BASE}/sessions`);
    const sessions = data.sessions ?? [];

    const sessionCount = document.getElementById('session-count');
    if (sessionCount) {
      sessionCount.textContent = String(sessions.length);
    }

    if (sessions.length === 0) {
      sessionsList.innerHTML = '<p class="text-gray-600 text-sm">No active sessions</p>';
      return;
    }

    sessionsList.innerHTML = sessions
      .map((session) => {
        const expirationStatus = getExpirationStatus(session.expires_at ?? null);
        const deviceDisplay = session.device || 'Unknown Device';
        const browserDisplay = session.browser ? `${session.browser}` : 'Unknown Browser';
        const osDisplay = session.os ? `${session.os}` : 'Unknown OS';
        const sessionId = session.id || session.session_id || '';

        // Determine badge color based on expiration status
        let badgeClass = 'bg-gray-100 text-gray-700';
        if (expirationStatus.status === 'expired') {
          badgeClass = 'bg-red-100 text-red-700';
        } else if (expirationStatus.status === 'expiring-soon') {
          badgeClass = 'bg-amber-100 text-amber-700';
        }

        return `
            <div class="border border-gray-200 rounded-lg p-4 ${session.is_current ? 'bg-blue-50 border-blue-300' : 'bg-white'}" data-session-id="${sessionId}">
              <div class="flex justify-between items-start">
                <div class="flex-1">
                  <div class="flex items-center gap-2 mb-2">
                    <div class="font-medium text-gray-900">${deviceDisplay}</div>
                    ${session.is_current ? '<span class="px-2 py-1 text-xs bg-blue-500 text-white rounded">Current Session</span>' : ''}
                  </div>
                  <div class="text-sm text-gray-600 mb-1">${browserDisplay} on ${osDisplay}</div>
                  <div class="text-xs text-gray-500">
                    IP: ${session.ip_address || 'Unknown'} |
                    Last used: ${formatDate(session.last_used_at)} |
                    Expires: ${formatDate(session.expires_at)}
                    ${expirationStatus.message ? `<span class="${badgeClass} px-2 py-0.5 rounded text-xs ml-1">${expirationStatus.message}</span>` : ''}
                  </div>
                </div>
                <div class="ml-4">
                  <button
                    onclick="window.revokeSession('${sessionId}')"
                    ${session.is_current ? 'disabled' : ''}
                    class="px-3 py-1 text-sm ${session.is_current ? 'bg-gray-200 text-gray-400 cursor-not-allowed' : 'bg-red-500 hover:bg-red-600 text-white'} rounded-md font-medium"
                  >
                    ${t('auth.profile.revokeSession') || 'Revoke'}
                  </button>
                </div>
              </div>
            </div>
          `;
      })
      .join('');
  } catch (error) {
    reportError('profile', 'loadSessions', error);
    sessionsList.innerHTML = '<p class="text-red-500 text-sm">Failed to load sessions</p>';
  }
}

async function loadUserInfo(): Promise<void> {
  try {
    const user = await apiGet<UserInfo>(`${API_BASE}/me`);

    const usernameEl = document.getElementById('user-username') as HTMLInputElement | null;
    const emailEl = document.getElementById('user-email') as HTMLInputElement | null;

    if (usernameEl) usernameEl.value = user.username;
    if (emailEl) emailEl.value = user.email;

    const createdEl = document.getElementById('user-created');
    const lastLoginEl = document.getElementById('user-last-login');
    if (createdEl) createdEl.textContent = formatDate(user.created_at);
    if (lastLoginEl) lastLoginEl.textContent = formatDate(user.last_login);

    await loadSessions();
  } catch (error) {
    reportError('profile', 'loadUserInfo', error);
    showNotification(t('messages.error') || 'Failed to load user info', 'error');
  }
}

async function revokeSession(sessionId: string): Promise<void> {
  if (!sessionId) return;
  if (
    !window.confirm(
      t('auth.profile.confirmRevokeSession') || 'Are you sure you want to revoke this session?'
    )
  ) {
    return;
  }

  try {
    await apiDelete(`${API_BASE}/sessions/${sessionId}`);
    showNotification(t('auth.profile.sessionRevoked') || 'Session revoked successfully', 'success');
    await loadSessions();
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

    const currentPassword =
      (document.getElementById('current-password') as HTMLInputElement | null)?.value ?? '';
    const newPassword =
      (document.getElementById('new-password') as HTMLInputElement | null)?.value ?? '';
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
      await apiPost(`${API_BASE}/change-password`, {
        old_password: currentPassword,
        new_password: newPassword,
        confirm_new_password: confirmNewPassword,
      });

      showNotification(
        t('auth.profile.passwordChanged') || 'Password changed successfully',
        'success'
      );
      form.reset();
      clearAllErrors();
    } catch (error) {
      if (error instanceof APIRequestError) {
        if (error.status === 401) {
          showError(
            document.getElementById('current-password-error'),
            error.message || t('auth.profile.incorrectPassword') || 'Incorrect current password'
          );
        } else {
          showNotification(
            error.message || t('messages.error') || 'Failed to change password',
            'error'
          );
        }
      } else {
        reportError('profile', 'changePassword', error);
        showNotification(t('messages.error') || 'Failed to change password', 'error');
      }
    } finally {
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = t('auth.profile.updatePassword') || 'Update Password';
      }
    }
  });
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

  void loadUserInfo();
  setupChangePasswordForm();
}

(window as Window & { revokeSession?: (sessionId: string) => Promise<void> }).revokeSession =
  revokeSession;

initI18n(() => {
  try {
    initializeProfilePage();
  } catch (error) {
    reportError('profile', 'initialize', error);
  }
});
