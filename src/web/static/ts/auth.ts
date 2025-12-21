/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Authentication page logic (login/register)
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

function getInputValue(id: string): string {
  const input = document.getElementById(id) as HTMLInputElement | null;
  return input?.value ?? '';
}

function getCheckboxValue(id: string): boolean {
  const input = document.getElementById(id) as HTMLInputElement | null;
  return input?.checked ?? false;
}

function checkPasswordStrength(password: string): { strength: number; checks: PasswordChecks } {
  let strength = 0;
  const checks: PasswordChecks = {
    length: password.length >= 12,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    digit: /[0-9]/.test(password),
    special: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password),
  };

  Object.values(checks).forEach((met) => {
    if (met) strength += 1;
  });

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

async function handleLoginSubmit(event: Event): Promise<void> {
  event.preventDefault();
  clearAllErrors();

  const usernameOrEmail = getInputValue('username-or-email').trim();
  const password = getInputValue('password');
  const rememberMe = getCheckboxValue('remember-me');

  if (!usernameOrEmail) {
    showError(
      document.getElementById('username-error'),
      t('auth.login.usernameRequired') || 'Username or email is required'
    );
    return;
  }

  if (!password) {
    showError(
      document.getElementById('password-error'),
      t('auth.login.passwordRequired') || 'Password is required'
    );
    return;
  }

  const form = document.getElementById('login-form') as HTMLFormElement | null;
  const submitButton = form?.querySelector('button[type="submit"]') as HTMLButtonElement | null;
  if (submitButton) {
    submitButton.disabled = true;
    submitButton.textContent = t('messages.loading') || 'Loading...';
  }

  try {
    const response = await fetch(`${API_BASE}/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username_or_email: usernameOrEmail,
        password,
        remember_me: rememberMe,
      }),
    });

    const data = (await response.json()) as {
      access_token?: string;
      refresh_token?: string;
      detail?: string;
    };

    if (response.ok) {
      const preferredStorage = rememberMe ? localStorage : sessionStorage;
      const secondaryStorage = rememberMe ? sessionStorage : localStorage;

      if (!data.access_token || !data.refresh_token) {
        showNotification(t('messages.error') || 'An error occurred', 'error');
        return;
      }
      preferredStorage.setItem('access_token', data.access_token);
      preferredStorage.setItem('refresh_token', data.refresh_token);

      secondaryStorage.removeItem('access_token');
      secondaryStorage.removeItem('refresh_token');

      showNotification(t('auth.login.success') || 'Login successful!', 'success');

      setTimeout(() => {
        window.location.href = '/';
      }, 1000);
    } else if (response.status === 401) {
      showError(
        document.getElementById('password-error'),
        data.detail || t('auth.login.invalidCredentials') || 'Invalid credentials'
      );
    } else if (response.status === 403) {
      if (data.detail && data.detail.includes('locked')) {
        showElement(document.getElementById('account-locked-message'));
      } else {
        showError(
          document.getElementById('password-error'),
          data.detail || t('auth.login.accountInactive') || 'Account inactive'
        );
      }
    } else {
      showError(
        document.getElementById('password-error'),
        data.detail || t('messages.error') || 'An error occurred'
      );
    }
  } catch (error) {
    reportError('auth', 'login', error);
    showError(
      document.getElementById('password-error'),
      t('messages.error') || 'An error occurred'
    );
  } finally {
    if (submitButton) {
      submitButton.disabled = false;
      submitButton.textContent = t('auth.login.loginButton') || 'Login';
    }
  }
}

async function handleRegisterSubmit(event: Event): Promise<void> {
  event.preventDefault();
  clearAllErrors();

  const username = getInputValue('username').trim();
  const email = getInputValue('email').trim();
  const password = getInputValue('password');
  const confirmPassword = getInputValue('confirm-password');

  let hasErrors = false;

  if (!username || username.length < 3 || username.length > 50) {
    showError(
      document.getElementById('username-error'),
      t('auth.register.usernameInvalid') || 'Username must be 3-50 characters'
    );
    hasErrors = true;
  }

  if (!/^[a-zA-Z0-9_-]+$/.test(username)) {
    showError(
      document.getElementById('username-error'),
      t('auth.register.usernamePattern') ||
        'Username can only contain letters, numbers, underscore, and hyphen'
    );
    hasErrors = true;
  }

  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    showError(
      document.getElementById('email-error'),
      t('auth.register.emailInvalid') || 'Invalid email address'
    );
    hasErrors = true;
  }

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

  const form = document.getElementById('register-form') as HTMLFormElement | null;
  const submitButton = form?.querySelector('button[type="submit"]') as HTMLButtonElement | null;
  if (submitButton) {
    submitButton.disabled = true;
    submitButton.textContent = t('messages.loading') || 'Loading...';
  }

  try {
    const response = await fetch(`${API_BASE}/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username,
        email,
        password,
        confirm_password: confirmPassword,
      }),
    });

    const data = (await response.json()) as {
      access_token?: string;
      refresh_token?: string;
      detail?: string;
    };

    if (response.ok) {
      if (!data.access_token || !data.refresh_token) {
        showNotification(t('messages.error') || 'An error occurred', 'error');
        return;
      }
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);

      showNotification(t('auth.register.success') || 'Registration successful!', 'success');

      setTimeout(() => {
        window.location.href = '/';
      }, 1000);
    } else if (data.detail) {
      if (data.detail.includes('username')) {
        showError(document.getElementById('username-error'), data.detail);
      } else if (data.detail.includes('email')) {
        showError(document.getElementById('email-error'), data.detail);
      } else if (data.detail.includes('password')) {
        showError(document.getElementById('password-error'), data.detail);
      } else {
        showNotification(data.detail, 'error');
      }
    }
  } catch (error) {
    reportError('auth', 'register', error);
    showNotification(t('messages.error') || 'An error occurred', 'error');
  } finally {
    if (submitButton) {
      submitButton.disabled = false;
      submitButton.textContent = t('auth.register.registerButton') || 'Register';
    }
  }
}

function setupLoginForm(): void {
  const form = document.getElementById('login-form');
  if (!form) return;

  setupPasswordToggle('toggle-password', 'password');
  form.addEventListener('submit', handleLoginSubmit);
}

function setupRegisterForm(): void {
  const form = document.getElementById('register-form');
  if (!form) return;

  setupPasswordToggle('toggle-password', 'password');
  setupPasswordToggle('toggle-confirm-password', 'confirm-password');

  const passwordInput = document.getElementById('password') as HTMLInputElement | null;
  if (passwordInput) {
    passwordInput.addEventListener('input', () => {
      updatePasswordStrength(passwordInput.value);
    });
  }

  form.addEventListener('submit', handleRegisterSubmit);
}

function initializeAuthPage(): void {
  updateStaticTranslations();

  const languageSelector = document.getElementById('language-selector') as HTMLSelectElement | null;
  if (languageSelector) {
    languageSelector.addEventListener('change', (event) => {
      const target = event.target as HTMLSelectElement;
      changeLanguage(target.value).catch((error) => {
        reportError('auth', 'changeLanguage', error);
      });
    });
  }

  if (document.getElementById('login-form')) {
    setupLoginForm();
  } else if (document.getElementById('register-form')) {
    setupRegisterForm();
  }

  hideElement(document.getElementById('account-locked-message'));
}

initI18n(() => {
  try {
    initializeAuthPage();
  } catch (error) {
    reportError('auth', 'initialize', error);
  }
});
