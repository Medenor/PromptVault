/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Password reset logic (forgot/reset)
 */

import '../css/tailwind-globals.css';
import { reportError } from '@/telemetry';
import { changeLanguage, initI18n, t, updateStaticTranslations } from '@/utils/i18n';
import { clearAllErrors, hideElement, showElement, showError } from '@/utils/dom';
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

async function handleForgotPasswordSubmit(event: Event): Promise<void> {
  event.preventDefault();
  clearAllErrors();
  const form = document.getElementById('forgot-password-form') as HTMLFormElement | null;
  resetFormAccessibilityState(form, ['email'], 'forgot-password-error-summary');
  const validationErrors: FormValidationError[] = [];

  const email = getInputValue('email').trim();

  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    addFieldError(
      validationErrors,
      'email',
      'email-error',
      t('auth.forgotPassword.emailInvalid') || 'Invalid email address'
    );
    renderErrorSummary('forgot-password-error-summary', validationErrors);
    return;
  }

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
      addFieldError(
        validationErrors,
        'email',
        'email-error',
        data.detail || t('messages.error') || 'An error occurred'
      );
      renderErrorSummary('forgot-password-error-summary', validationErrors);
    }
  } catch (error) {
    reportError('password-reset', 'forgot', error);
    addFieldError(
      validationErrors,
      'email',
      'email-error',
      t('messages.error') || 'An error occurred'
    );
    renderErrorSummary('forgot-password-error-summary', validationErrors);
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
  const form = document.getElementById('reset-password-form') as HTMLFormElement | null;
  resetFormAccessibilityState(
    form,
    ['password', 'confirm-password'],
    'reset-password-error-summary'
  );
  const validationErrors: FormValidationError[] = [];

  const password = getInputValue('password');
  const confirmPassword = getInputValue('confirm-password');

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
    renderErrorSummary('reset-password-error-summary', validationErrors);
    return;
  }

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
      addFieldError(
        validationErrors,
        'password',
        'password-error',
        data.detail || t('messages.error') || 'An error occurred'
      );
      renderErrorSummary('reset-password-error-summary', validationErrors);
    }
  } catch (error) {
    reportError('password-reset', 'reset', error);
    addFieldError(
      validationErrors,
      'password',
      'password-error',
      t('messages.error') || 'An error occurred'
    );
    renderErrorSummary('reset-password-error-summary', validationErrors);
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

  // Live validation (T-ACC025): required email.
  attachRequiredLiveValidation(
    'email',
    'email-error',
    t('validation.required') || 'This field is required.'
  );
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

  // Live validation (T-ACC025): required fields + confirmation match.
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
