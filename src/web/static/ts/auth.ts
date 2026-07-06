/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Authentication page logic (login/register)
 */

import '../css/tailwind-globals.css';
import { reportError } from '@/telemetry';
import { changeLanguage, initI18n, t, updateStaticTranslations } from '@/utils/i18n';
import { clearAllErrors, hideElement, showElement, showError } from '@/utils/dom';
import { showNotification } from '@/utils/notifications';
import { announce } from '@/utils/a11y';

const API_BASE = '/api/auth';

interface PasswordChecks {
  length: boolean;
  uppercase: boolean;
  lowercase: boolean;
  digit: boolean;
  special: boolean;
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
    special: /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(password),
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
      const icon = element.querySelector('.policy-icon');
      if (met) {
        element.classList.remove('text-gray-600');
        element.classList.add('text-green-600');
        if (icon) {
          icon.textContent = '✓';
        }
      } else {
        element.classList.remove('text-green-600');
        element.classList.add('text-gray-600');
        if (icon) {
          icon.textContent = '○';
        }
      }
    }
  });
}

function updatePasswordStrength(password: string): void {
  const { strength, checks } = checkPasswordStrength(password);
  const strengthBar = document.getElementById('strength-bar-fill');
  const strengthText = document.getElementById('strength-text');

  if (!strengthBar || !strengthText) return;

  // Reset classes
  strengthBar.className = 'h-full transition-all duration-300';

  if (strength >= 5) {
    strengthBar.classList.add('bg-green-500');
    strengthBar.style.width = '100%';
    strengthText.textContent = t('auth.register.strengthStrong') || 'Strong password';
    strengthText.className = 'text-xs mt-1 text-green-600 font-medium';
  } else if (strength >= 3) {
    strengthBar.classList.add('bg-yellow-500');
    strengthBar.style.width = '66%';
    strengthText.textContent = t('auth.register.strengthMedium') || 'Medium password';
    strengthText.className = 'text-xs mt-1 text-yellow-600 font-medium';
  } else if (password.length > 0) {
    strengthBar.classList.add('bg-red-500');
    strengthBar.style.width = '33%';
    strengthText.textContent = t('auth.register.strengthWeak') || 'Weak password';
    strengthText.className = 'text-xs mt-1 text-red-600 font-medium';
  } else {
    strengthBar.style.width = '0%';
    strengthText.textContent = '';
  }

  updatePolicyRequirements(checks);
}

function setupPasswordToggle(toggleButtonId: string, passwordInputId: string): void {
  const toggleButton = document.getElementById(toggleButtonId);
  const passwordInput = document.getElementById(passwordInputId) as HTMLInputElement | null;

  if (toggleButton && passwordInput) {
    toggleButton.addEventListener('click', (event) => {
      event.preventDefault();
      const isPasswordVisible = passwordInput.type === 'password';
      passwordInput.type = isPasswordVisible ? 'text' : 'password';
      // Update aria-pressed state
      toggleButton.setAttribute('aria-pressed', isPasswordVisible ? 'true' : 'false');
      // CRITICAL: Keep focus on toggle button after state change (WCAG 2.1 AA)
      toggleButton.focus();
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

async function handleLoginSubmit(event: Event): Promise<void> {
  event.preventDefault();
  clearAllErrors();
  const form = document.getElementById('login-form') as HTMLFormElement | null;
  resetFormAccessibilityState(form, ['username-or-email', 'password'], 'login-error-summary');
  const validationErrors: FormValidationError[] = [];

  const usernameOrEmail = getInputValue('username-or-email').trim();
  const password = getInputValue('password');
  const rememberMe = getCheckboxValue('remember-me');

  if (!usernameOrEmail) {
    addFieldError(
      validationErrors,
      'username-or-email',
      'username-error',
      t('auth.login.usernameRequired') || 'Username or email is required'
    );
  }

  if (!password) {
    addFieldError(
      validationErrors,
      'password',
      'password-error',
      t('auth.login.passwordRequired') || 'Password is required'
    );
  }

  if (validationErrors.length > 0) {
    renderErrorSummary('login-error-summary', validationErrors);
    return;
  }

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
      addFieldError(
        validationErrors,
        'password',
        'password-error',
        data.detail || t('auth.login.invalidCredentials') || 'Invalid credentials'
      );
      renderErrorSummary('login-error-summary', validationErrors);
    } else if (response.status === 403) {
      if (data.detail && data.detail.includes('locked')) {
        showElement(document.getElementById('account-locked-message'));
      } else {
        addFieldError(
          validationErrors,
          'password',
          'password-error',
          data.detail || t('auth.login.accountInactive') || 'Account inactive'
        );
        renderErrorSummary('login-error-summary', validationErrors);
      }
    } else {
      addFieldError(
        validationErrors,
        'password',
        'password-error',
        data.detail || t('messages.error') || 'An error occurred'
      );
      renderErrorSummary('login-error-summary', validationErrors);
    }
  } catch (error) {
    reportError('auth', 'login', error);
    addFieldError(
      validationErrors,
      'password',
      'password-error',
      t('messages.error') || 'An error occurred'
    );
    renderErrorSummary('login-error-summary', validationErrors);
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
  const form = document.getElementById('register-form') as HTMLFormElement | null;
  resetFormAccessibilityState(
    form,
    ['username', 'email', 'password', 'confirm-password'],
    'register-error-summary'
  );

  const username = getInputValue('username').trim();
  const email = getInputValue('email').trim();
  const password = getInputValue('password');
  const confirmPassword = getInputValue('confirm-password');

  const validationErrors: FormValidationError[] = [];

  if (!username || username.length < 3 || username.length > 50) {
    addFieldError(
      validationErrors,
      'username',
      'username-error',
      t('auth.register.usernameInvalid') || 'Username must be 3-50 characters'
    );
  }

  if (!/^[a-zA-Z0-9_-]+$/.test(username)) {
    addFieldError(
      validationErrors,
      'username',
      'username-error',
      t('auth.register.usernamePattern') ||
        'Username can only contain letters, numbers, underscore, and hyphen'
    );
  }

  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    addFieldError(
      validationErrors,
      'email',
      'email-error',
      t('auth.register.emailInvalid') || 'Invalid email address'
    );
  }

  const { checks } = checkPasswordStrength(password);
  if (!Object.values(checks).every((value) => value)) {
    addFieldError(
      validationErrors,
      'password',
      'password-error',
      t('auth.register.passwordPolicy') || 'Password does not meet requirements'
    );
  }

  if (password !== confirmPassword) {
    addFieldError(
      validationErrors,
      'confirm-password',
      'confirm-password-error',
      t('auth.register.passwordMismatch') || 'Passwords do not match'
    );
  }

  if (validationErrors.length > 0) {
    renderErrorSummary('register-error-summary', validationErrors);
    return;
  }

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
        addFieldError(validationErrors, 'username', 'username-error', data.detail);
      } else if (data.detail.includes('email')) {
        addFieldError(validationErrors, 'email', 'email-error', data.detail);
      } else if (data.detail.includes('password')) {
        addFieldError(validationErrors, 'password', 'password-error', data.detail);
      } else {
        showNotification(data.detail, 'error');
      }
      renderErrorSummary('register-error-summary', validationErrors);
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

  // Live validation (T-ACC025): required fields.
  attachRequiredLiveValidation(
    'username-or-email',
    'username-error',
    t('auth.login.usernameRequired') || 'Username or email is required'
  );
  attachRequiredLiveValidation(
    'password',
    'password-error',
    t('auth.login.passwordRequired') || 'Password is required'
  );
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

  // Live validation (T-ACC025): required + password confirmation.
  attachRequiredLiveValidation(
    'username',
    'username-error',
    t('validation.required') || 'This field is required.'
  );
  attachRequiredLiveValidation(
    'email',
    'email-error',
    t('validation.required') || 'This field is required.'
  );
  attachRequiredLiveValidation(
    'password',
    'password-error',
    t('validation.required') || 'This field is required.'
  );
  attachRequiredLiveValidation(
    'confirm-password',
    'confirm-password-error',
    t('validation.required') || 'This field is required.'
  );

  const confirmPasswordInput = document.getElementById(
    'confirm-password'
  ) as HTMLInputElement | null;
  const passwordConfirmCheck = () => {
    const password = (document.getElementById('password') as HTMLInputElement | null)?.value ?? '';
    const confirm = confirmPasswordInput?.value ?? '';
    if (!confirm.trim()) {
      return;
    }
    if (password && confirm && password !== confirm) {
      setLiveError(
        'confirm-password',
        'confirm-password-error',
        t('auth.register.passwordMismatch') || 'Passwords do not match'
      );
    } else if (password && confirm) {
      clearLiveError('confirm-password', 'confirm-password-error');
    }
  };

  confirmPasswordInput?.addEventListener('input', passwordConfirmCheck);
  passwordInput?.addEventListener('input', passwordConfirmCheck);
}

/**
 * Check whether the browser has a stored access token indicating an active
 * session. Used to redirect already-authenticated users away from the login
 * page when it is restored from the back/forward cache (bfcache).
 *
 * Tokens are stored in localStorage (remember me) or sessionStorage by the
 * login/register flow.
 */
function hasStoredAccessToken(): boolean {
  return Boolean(localStorage.getItem('access_token') || sessionStorage.getItem('access_token'));
}

/**
 * Redirect already-authenticated users away from auth pages.
 *
 * When a user presses the browser "back" button after logging in, the login
 * page may be restored from the bfcache (or from the HTTP cache) without
 * hitting the server. Without this guard, the user would see the login form
 * again even though their session is still valid. The server-side redirect
 * handles fresh navigations; this complements it for client-side restoration.
 */
function redirectIfAuthenticated(): void {
  if (hasStoredAccessToken()) {
    window.location.replace('/');
  }
}

function initializeAuthPage(): void {
  // Guard against bfcache restoration showing the login page to an
  // already-authenticated user (fixes "previous page" history navigation).
  redirectIfAuthenticated();
  window.addEventListener('pageshow', (event) => {
    // event.persisted is true when the page is restored from the bfcache.
    if (event.persisted) {
      redirectIfAuthenticated();
    }
  });

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
