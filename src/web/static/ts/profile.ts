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
import { initI18n, t, updateStaticTranslations } from '@/utils/i18n';
import { clearAllErrors, showError } from '@/utils/dom';
import { showNotification } from '@/utils/notifications';
import { apiGet, apiPost, apiDelete, APIRequestError } from '@/utils/api';
import { announce } from '@/utils/a11y';
import { initSecondaryNav } from '@/utils/secondary-nav';
import { html, raw } from '@/utils/safe-html';

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

interface FormValidationError {
  inputId: string;
  message: string;
}

const liveValidationState = new Map<string, boolean>();

function setLiveError(inputId: string, errorId: string, message: string): void {
  showError(document.getElementById(errorId), message);
  const input = document.getElementById(inputId);
  const hadError = liveValidationState.get(inputId) === true;
  input?.setAttribute('aria-invalid', 'true');
  liveValidationState.set(inputId, true);
  if (!hadError) {
    announce(message, { id: 'validation-announcer', politeness: 'polite' });
  }
}

function clearLiveError(inputId: string, errorId: string): void {
  showError(document.getElementById(errorId), '');
  const input = document.getElementById(inputId);
  const hadError = liveValidationState.get(inputId) === true;
  input?.setAttribute('aria-invalid', 'false');
  liveValidationState.set(inputId, false);
  if (hadError) {
    announce(t('validation.fieldValid') || 'Field is valid.', {
      id: 'validation-announcer',
      politeness: 'polite',
    });
  }
}

function attachRequiredLiveValidation(inputId: string, errorId: string, message: string): void {
  const input = document.getElementById(inputId) as HTMLInputElement | null;
  if (!input) return;

  input.addEventListener('blur', () => {
    if (!input.value.trim()) {
      setLiveError(inputId, errorId, message);
    } else {
      clearLiveError(inputId, errorId);
    }
  });

  input.addEventListener('input', () => {
    if (liveValidationState.get(inputId) !== true) return;
    if (input.value.trim()) {
      clearLiveError(inputId, errorId);
    }
  });
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
    special: /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(password),
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
    summary.style.display = 'none';
  }
}

function addFieldError(
  errors: FormValidationError[],
  inputId: string,
  errorId: string,
  message: string
): void {
  showError(document.getElementById(errorId), message);
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
  if (errors.length === 0) {
    return;
  }

  const summary = document.getElementById(summaryId);
  if (!summary) {
    const firstInput = document.getElementById(errors[0]?.inputId ?? '');
    firstInput?.focus();
    return;
  }

  summary.textContent = '';

  const header = document.createElement('p');
  header.className = 'error-banner-header';
  header.textContent = t('validation.errorSummaryHeader') || 'Please correct the following errors:';
  summary.appendChild(header);

  const list = document.createElement('ul');
  list.className = 'error-banner-list';
  errors.forEach((error) => {
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
  });
  summary.appendChild(list);

  summary.style.display = 'block';

  // Per plan T-ACC023: focus the first invalid field after rendering the summary.
  const firstInput = document.getElementById(errors[0]?.inputId ?? '') as HTMLElement | null;
  if (firstInput) {
    firstInput.focus();
  } else {
    summary.focus();
  }
}

async function loadSessions(): Promise<void> {
  const sessionsList = document.getElementById('sessions-list');
  if (!sessionsList) return;

  // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
  sessionsList.innerHTML =
    '<div class="text-gray-600 text-sm dark:text-gray-400" data-i18n="messages.loading">Loading...</div>';

  try {
    const data = await apiGet<{ sessions?: SessionItem[] }>(`${API_BASE}/sessions`);
    const sessions = data.sessions ?? [];

    const sessionCount = document.getElementById('session-count');
    if (sessionCount) {
      sessionCount.textContent = String(sessions.length);
    }

    if (sessions.length === 0) {
      // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
      sessionsList.innerHTML =
        '<p class="text-gray-600 text-sm dark:text-gray-400">No active sessions</p>';
      return;
    }

    // eslint-disable-next-line no-restricted-properties -- structurally escaped via html`` tagged template (utils/safe-html.ts)
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

        return html`
          <div
            class="border border-gray-200 dark:border-gray-700 rounded-lg p-4 ${raw(
              session.is_current
                ? 'bg-blue-50 border-blue-300 dark:bg-blue-950 dark:border-blue-800'
                : 'bg-white dark:bg-gray-800'
            )}"
            data-session-id="${sessionId}"
          >
            <div class="flex justify-between items-start">
              <div class="flex-1">
                <div class="flex items-center gap-2 mb-2">
                  <div class="font-medium text-gray-900 dark:text-gray-100">${deviceDisplay}</div>
                  ${raw(
                    session.is_current
                      ? '<span class="px-2 py-1 text-xs bg-blue-700 text-white rounded">Current Session</span>'
                      : ''
                  )}
                </div>
                <div class="text-sm text-gray-600 mb-1 dark:text-gray-400">
                  ${browserDisplay} on ${osDisplay}
                </div>
                <div class="text-xs text-gray-500 dark:text-gray-400">
                  IP: ${session.ip_address || 'Unknown'} | Last used:
                  ${formatDate(session.last_used_at)} | Expires: ${formatDate(session.expires_at)}
                  ${raw(
                    expirationStatus.message
                      ? html`<span class="${raw(badgeClass)} px-2 py-0.5 rounded text-xs ml-1"
                          >${expirationStatus.message}</span
                        >`
                      : ''
                  )}
                </div>
              </div>
              <div class="ml-4">
                <button
                  data-revoke-session-id="${sessionId}"
                  ${raw(session.is_current ? 'disabled' : '')}
                  class="px-3 py-1 text-sm ${raw(
                    session.is_current
                      ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                      : 'bg-red-700 hover:bg-red-800 text-white'
                  )} rounded-md font-medium"
                >
                  ${t('auth.profile.revokeSession') || 'Revoke'}
                </button>
              </div>
            </div>
          </div>
        `;
      })
      .join('');

    sessionsList
      .querySelectorAll<HTMLButtonElement>('[data-revoke-session-id]')
      .forEach((button) => {
        button.addEventListener('click', () => {
          const id = button.dataset.revokeSessionId;
          if (id) {
            void (
              window as Window & { revokeSession?: (sessionId: string) => Promise<void> }
            ).revokeSession?.(id);
          }
        });
      });
  } catch (error) {
    reportError('profile', 'loadSessions', error);
    // eslint-disable-next-line no-restricted-properties -- static markup, no interpolation
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

  // Live validation (T-ACC025): required fields + confirmation match.
  attachRequiredLiveValidation(
    'current-password',
    'current-password-error',
    t('auth.profile.currentPasswordRequired') ||
      t('validation.required') ||
      'This field is required.'
  );
  attachRequiredLiveValidation(
    'new-password',
    'new-password-error',
    t('validation.required') || 'This field is required.'
  );
  attachRequiredLiveValidation(
    'confirm-new-password',
    'confirm-new-password-error',
    t('validation.required') || 'This field is required.'
  );

  const confirmPasswordInput = document.getElementById(
    'confirm-new-password'
  ) as HTMLInputElement | null;
  const passwordConfirmCheck = () => {
    const password =
      (document.getElementById('new-password') as HTMLInputElement | null)?.value ?? '';
    const confirm = confirmPasswordInput?.value ?? '';
    if (!confirm.trim()) {
      return;
    }
    if (password && confirm && password !== confirm) {
      setLiveError(
        'confirm-new-password',
        'confirm-new-password-error',
        t('auth.register.passwordMismatch') || 'Passwords do not match'
      );
    } else if (password && confirm) {
      clearLiveError('confirm-new-password', 'confirm-new-password-error');
    }
  };
  confirmPasswordInput?.addEventListener('input', passwordConfirmCheck);
  newPasswordInput?.addEventListener('input', passwordConfirmCheck);

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    clearAllErrors();
    resetFormAccessibilityState(
      form,
      ['current-password', 'new-password', 'confirm-new-password'],
      'change-password-error-summary'
    );
    const validationErrors: FormValidationError[] = [];

    const currentPassword =
      (document.getElementById('current-password') as HTMLInputElement | null)?.value ?? '';
    const newPassword =
      (document.getElementById('new-password') as HTMLInputElement | null)?.value ?? '';
    const confirmNewPassword =
      (document.getElementById('confirm-new-password') as HTMLInputElement | null)?.value ?? '';

    if (!currentPassword) {
      addFieldError(
        validationErrors,
        'current-password',
        'current-password-error',
        t('auth.profile.currentPasswordRequired') || 'Current password is required'
      );
    }

    const { checks } = checkPasswordStrength(newPassword);
    if (!Object.values(checks).every((value) => value)) {
      addFieldError(
        validationErrors,
        'new-password',
        'new-password-error',
        t('auth.register.passwordPolicy') || 'Password does not meet requirements'
      );
    }

    if (newPassword !== confirmNewPassword) {
      addFieldError(
        validationErrors,
        'confirm-new-password',
        'confirm-new-password-error',
        t('auth.register.passwordMismatch') || 'Passwords do not match'
      );
    }

    if (validationErrors.length > 0) {
      renderErrorSummary('change-password-error-summary', validationErrors);
      return;
    }

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
          addFieldError(
            validationErrors,
            'current-password',
            'current-password-error',
            error.message || t('auth.profile.incorrectPassword') || 'Incorrect current password'
          );
          renderErrorSummary('change-password-error-summary', validationErrors);
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
  initSecondaryNav({ component: 'profile', requireAuth: true });

  // Button keyboard activation (Enter and Space keys)
  // Enables keyboard accessibility for all buttons
  document.addEventListener('keydown', (e) => {
    if (document.activeElement instanceof HTMLButtonElement) {
      const button = document.activeElement;
      // Enter and Space keys should activate buttons (standard keyboard behavior)
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        button.click();
      }
    }
  });

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
