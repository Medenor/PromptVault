/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/. */

// Password Reset JavaScript

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
        document.addEventListener('DOMContentLoaded', initPasswordResetPage);
      } else {
        initPasswordResetPage();
      }
    }
  );

// Constants
const API_BASE = '/api/auth';
const HIDDEN_CLASS = 'is-hidden';

// Utility Functions
function showElement(element) {
  if (element) element.classList.remove(HIDDEN_CLASS);
}

function hideElement(element) {
  if (element) element.classList.add(HIDDEN_CLASS);
}

function showError(element, message) {
  if (element) {
    element.textContent = message;
    element.classList.add('validation-error-visible');
  }
}

function clearError(element) {
  if (element) {
    element.textContent = '';
    element.classList.remove('validation-error-visible');
  }
}

function clearAllErrors() {
  document.querySelectorAll('.validation-error').forEach((el) => clearError(el));
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

// Password Strength Checker
function checkPasswordStrength(password) {
  const checks = {
    length: password.length >= 12,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    digit: /[0-9]/.test(password),
    special: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password),
  };

  let strength = Object.values(checks).filter((v) => v).length;
  return { strength, checks };
}

function updatePasswordStrength(password) {
  const { strength, checks } = checkPasswordStrength(password);
  const strengthBar = document.getElementById('strength-bar-fill');
  const strengthText = document.getElementById('strength-text');

  if (!strengthBar || !strengthText) return;

  // Update bar
  strengthBar.className = 'strength-bar-fill';
  if (strength >= 5) {
    strengthBar.classList.add('strength-strong');
    strengthText.textContent = i18next.t('auth.register.strengthStrong') || 'Strong password';
    strengthText.className = 'strength-text strength-strong';
  } else if (strength >= 3) {
    strengthBar.classList.add('strength-medium');
    strengthText.textContent = i18next.t('auth.register.strengthMedium') || 'Medium password';
    strengthText.className = 'strength-text strength-medium';
  } else if (password.length > 0) {
    strengthBar.classList.add('strength-weak');
    strengthText.textContent = i18next.t('auth.register.strengthWeak') || 'Weak password';
    strengthText.className = 'strength-text strength-weak';
  } else {
    strengthText.textContent = '';
  }

  // Update policy requirements
  updatePolicyRequirements(checks);
}

function updatePolicyRequirements(checks) {
  const policyMap = {
    length: 'policy-length',
    uppercase: 'policy-uppercase',
    lowercase: 'policy-lowercase',
    digit: 'policy-digit',
    special: 'policy-special',
  };

  Object.entries(checks).forEach(([check, met]) => {
    const element = document.getElementById(policyMap[check]);
    if (element) {
      if (met) {
        element.classList.add('met');
      } else {
        element.classList.remove('met');
      }
    }
  });
}

// Password Toggle
function setupPasswordToggle(toggleButtonId, passwordInputId) {
  const toggleButton = document.getElementById(toggleButtonId);
  const passwordInput = document.getElementById(passwordInputId);

  if (toggleButton && passwordInput) {
    toggleButton.addEventListener('click', () => {
      const type = passwordInput.type === 'password' ? 'text' : 'password';
      passwordInput.type = type;
    });
  }
}

// Forgot Password Form Handler
function setupForgotPasswordForm() {
  const form = document.getElementById('forgot-password-form');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearAllErrors();

    const email = document.getElementById('email').value.trim();

    // Validation
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      showError(
        document.getElementById('email-error'),
        i18next.t('auth.forgotPassword.emailInvalid') || 'Invalid email address'
      );
      return;
    }

    // Disable form
    const submitButton = form.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.textContent = i18next.t('messages.loading') || 'Loading...';

    try {
      const response = await fetch(`${API_BASE}/password-reset/request`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: email }),
      });

      const data = await response.json();

      if (response.ok) {
        // Show success message
        hideElement(form);
        showElement(document.getElementById('success-message'));
      } else if (response.status === 429) {
        // Rate limited
        showElement(document.getElementById('rate-limit-message'));
      } else {
        showError(
          document.getElementById('email-error'),
          data.detail || i18next.t('messages.error') || 'An error occurred'
        );
      }
    } catch (error) {
      console.error('Forgot password error:', error);
      showError(
        document.getElementById('email-error'),
        i18next.t('messages.error') || 'An error occurred'
      );
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = i18next.t('auth.forgotPassword.sendButton') || 'Send Reset Link';
    }
  });
}

// Reset Password Form Handler
function setupResetPasswordForm() {
  const form = document.getElementById('reset-password-form');
  if (!form) return;

  // Get token from URL
  const urlParams = new URLSearchParams(window.location.search);
  const token = urlParams.get('token');

  if (!token) {
    hideElement(form);
    showElement(document.getElementById('token-error-message'));
    return;
  }

  document.getElementById('reset-token').value = token;

  setupPasswordToggle('toggle-password', 'password');
  setupPasswordToggle('toggle-confirm-password', 'confirm-password');

  const passwordInput = document.getElementById('password');
  if (passwordInput) {
    passwordInput.addEventListener('input', () => {
      updatePasswordStrength(passwordInput.value);
    });
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearAllErrors();

    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirm-password').value;

    // Validation
    let hasErrors = false;

    const { checks } = checkPasswordStrength(password);
    if (!Object.values(checks).every((v) => v)) {
      showError(
        document.getElementById('password-error'),
        i18next.t('auth.register.passwordPolicy') || 'Password does not meet requirements'
      );
      hasErrors = true;
    }

    if (password !== confirmPassword) {
      showError(
        document.getElementById('confirm-password-error'),
        i18next.t('auth.register.passwordMismatch') || 'Passwords do not match'
      );
      hasErrors = true;
    }

    if (hasErrors) return;

    // Disable form
    const submitButton = form.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.textContent = i18next.t('messages.loading') || 'Loading...';

    try {
      const response = await fetch(`${API_BASE}/password-reset/confirm`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token: token,
          new_password: password,
          confirm_password: confirmPassword,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // Show success message
        hideElement(form.parentElement);
        showElement(document.getElementById('success-message'));
      } else {
        if (response.status === 400 || response.status === 404) {
          // Invalid or expired token
          hideElement(form.parentElement);
          showElement(document.getElementById('token-error-message'));
        } else {
          showError(
            document.getElementById('password-error'),
            data.detail || i18next.t('messages.error') || 'An error occurred'
          );
        }
      }
    } catch (error) {
      console.error('Reset password error:', error);
      showError(
        document.getElementById('password-error'),
        i18next.t('messages.error') || 'An error occurred'
      );
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = i18next.t('auth.resetPassword.resetButton') || 'Reset Password';
    }
  });
}

// Initialize Page
function initPasswordResetPage() {
  updateTranslations();

  // Setup language selector
  const languageSelector = document.getElementById('language-selector');
  if (languageSelector) {
    languageSelector.addEventListener('change', (e) => {
      i18next.changeLanguage(e.target.value, () => {
        updateTranslations();
      });
    });
  }

  // Setup form based on current page
  if (document.getElementById('forgot-password-form')) {
    setupForgotPasswordForm();
  } else if (document.getElementById('reset-password-form')) {
    setupResetPasswordForm();
  }
}
