/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Password reset logic (forgot/reset)
 */

import { reportError } from '@/telemetry';
import { changeLanguage, initI18n, t, updateStaticTranslations } from '@/utils/i18n';
import { clearAllErrors, hideElement, showElement, showError } from '@/utils/dom';

const API_BASE = '/api/auth';

interface PasswordChecks {
  length: boolean;
  uppercase: boolean;
  lowercase: boolean;
  digit: boolean;
  special: boolean;
}

function getInputValue(id: string): string {
  const input = document.getElementById(id) as HTMLInputElement | null;
  return input?.value ?? '';
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

async function handleForgotPasswordSubmit(event: Event): Promise<void> {
  event.preventDefault();
  clearAllErrors();

  const email = getInputValue('email').trim();

  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    showError(
      document.getElementById('email-error'),
      t('auth.forgotPassword.emailInvalid') || 'Invalid email address'
    );
    return;
  }

  const form = document.getElementById('forgot-password-form') as HTMLFormElement | null;
  const submitButton = form?.querySelector('button[type="submit"]') as HTMLButtonElement | null;
  if (submitButton) {
    submitButton.disabled = true;
    submitButton.textContent = t('messages.loading') || 'Loading...';
  }

  try {
    const response = await fetch(`${API_BASE}/password-reset/request`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email }),
    });

    const data = (await response.json()) as Record<string, string>;

    if (response.ok) {
      hideElement(form);
      showElement(document.getElementById('success-message'));
    } else if (response.status === 429) {
      showElement(document.getElementById('rate-limit-message'));
    } else {
      showError(
        document.getElementById('email-error'),
        data.detail || t('messages.error') || 'An error occurred'
      );
    }
  } catch (error) {
    reportError('password-reset', 'forgot', error);
    showError(document.getElementById('email-error'), t('messages.error') || 'An error occurred');
  } finally {
    if (submitButton) {
      submitButton.disabled = false;
      submitButton.textContent = t('auth.forgotPassword.sendButton') || 'Send Reset Link';
    }
  }
}

async function handleResetPasswordSubmit(event: Event, token: string): Promise<void> {
  event.preventDefault();
  clearAllErrors();

  const password = getInputValue('password');
  const confirmPassword = getInputValue('confirm-password');

  let hasErrors = false;

  const { checks } = checkPasswordStrength(password);
  if (!Object.values(checks).every((value) => value)) {
    showError(
      document.getElementById('password-error'),
      t('auth.register.passwordPolicy') || 'Password does not meet requirements'
    );
    hasErrors = true;
  }

  if (password !== confirmPassword) {
    showError(
      document.getElementById('confirm-password-error'),
      t('auth.register.passwordMismatch') || 'Passwords do not match'
    );
    hasErrors = true;
  }

  if (hasErrors) return;

  const form = document.getElementById('reset-password-form') as HTMLFormElement | null;
  const submitButton = form?.querySelector('button[type="submit"]') as HTMLButtonElement | null;
  if (submitButton) {
    submitButton.disabled = true;
    submitButton.textContent = t('messages.loading') || 'Loading...';
  }

  try {
    const response = await fetch(`${API_BASE}/password-reset/confirm`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        token,
        new_password: password,
        confirm_new_password: confirmPassword,
      }),
    });

    const data = (await response.json()) as Record<string, string>;

    if (response.ok) {
      hideElement(form?.parentElement ?? null);
      showElement(document.getElementById('success-message'));
    } else if (response.status === 400 || response.status === 404) {
      hideElement(form?.parentElement ?? null);
      showElement(document.getElementById('token-error-message'));
    } else {
      showError(
        document.getElementById('password-error'),
        data.detail || t('messages.error') || 'An error occurred'
      );
    }
  } catch (error) {
    reportError('password-reset', 'reset', error);
    showError(
      document.getElementById('password-error'),
      t('messages.error') || 'An error occurred'
    );
  } finally {
    if (submitButton) {
      submitButton.disabled = false;
      submitButton.textContent = t('auth.resetPassword.resetButton') || 'Reset Password';
    }
  }
}

function setupForgotPasswordForm(): void {
  const form = document.getElementById('forgot-password-form');
  if (!form) return;

  form.addEventListener('submit', handleForgotPasswordSubmit);
}

function setupResetPasswordForm(): void {
  const form = document.getElementById('reset-password-form') as HTMLFormElement | null;
  if (!form) return;

  const urlParams = new URLSearchParams(window.location.search);
  const token = urlParams.get('token');

  if (!token) {
    hideElement(form);
    showElement(document.getElementById('token-error-message'));
    return;
  }

  const tokenInput = document.getElementById('reset-token') as HTMLInputElement | null;
  if (tokenInput) {
    tokenInput.value = token;
  }

  setupPasswordToggle('toggle-password', 'password');
  setupPasswordToggle('toggle-confirm-password', 'confirm-password');

  const passwordInput = document.getElementById('password') as HTMLInputElement | null;
  if (passwordInput) {
    passwordInput.addEventListener('input', () => {
      updatePasswordStrength(passwordInput.value);
    });
  }

  form.addEventListener('submit', (event) => {
    void handleResetPasswordSubmit(event, token);
  });
}

function initializePasswordResetPage(): void {
  updateStaticTranslations();

  const languageSelector = document.getElementById('language-selector') as HTMLSelectElement | null;
  if (languageSelector) {
    languageSelector.addEventListener('change', (event) => {
      const target = event.target as HTMLSelectElement;
      changeLanguage(target.value).catch((error) => {
        reportError('password-reset', 'changeLanguage', error);
      });
    });
  }

  if (document.getElementById('forgot-password-form')) {
    setupForgotPasswordForm();
  } else if (document.getElementById('reset-password-form')) {
    setupResetPasswordForm();
  }
}

initI18n(() => {
  try {
    initializePasswordResetPage();
  } catch (error) {
    reportError('password-reset', 'initialize', error);
  }
});
