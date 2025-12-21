/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/. */

// Authentication JavaScript

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
        document.addEventListener('DOMContentLoaded', initAuthPage);
      } else {
        initAuthPage();
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

function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.textContent = message;
  document.body.appendChild(notification);

  setTimeout(() => {
    notification.remove();
  }, 5000);
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
  let strength = 0;
  const checks = {
    length: password.length >= 12,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    digit: /[0-9]/.test(password),
    special: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password),
  };

  // Count met requirements
  Object.values(checks).forEach((met) => {
    if (met) strength++;
  });

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

// Login Form Handler
function setupLoginForm() {
  const form = document.getElementById('login-form');
  if (!form) return;

  setupPasswordToggle('toggle-password', 'password');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearAllErrors();

    const usernameOrEmail = document.getElementById('username-or-email').value.trim();
    const password = document.getElementById('password').value;
    const rememberMeInput = document.getElementById('remember-me');
    const rememberMe = rememberMeInput ? rememberMeInput.checked : false;

    // Validation
    if (!usernameOrEmail) {
      showError(
        document.getElementById('username-error'),
        i18next.t('auth.login.usernameRequired') || 'Username or email is required'
      );
      return;
    }

    if (!password) {
      showError(
        document.getElementById('password-error'),
        i18next.t('auth.login.passwordRequired') || 'Password is required'
      );
      return;
    }

    // Disable form
    const submitButton = form.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.textContent = i18next.t('messages.loading') || 'Loading...';

    try {
      const response = await fetch(`${API_BASE}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username_or_email: usernameOrEmail,
          password: password,
          remember_me: rememberMe,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // Store tokens based on preference
        const preferredStorage = rememberMe ? localStorage : sessionStorage;
        const secondaryStorage = rememberMe ? sessionStorage : localStorage;

        preferredStorage.setItem('access_token', data.access_token);
        preferredStorage.setItem('refresh_token', data.refresh_token);

        secondaryStorage.removeItem('access_token');
        secondaryStorage.removeItem('refresh_token');

        showNotification(i18next.t('auth.login.success') || 'Login successful!', 'success');

        // Redirect to main page
        setTimeout(() => {
          window.location.href = '/';
        }, 1000);
      } else {
        // Handle errors
        if (response.status === 401) {
          showError(
            document.getElementById('password-error'),
            data.detail || i18next.t('auth.login.invalidCredentials') || 'Invalid credentials'
          );
        } else if (response.status === 403) {
          if (data.detail && data.detail.includes('locked')) {
            showElement(document.getElementById('account-locked-message'));
          } else {
            showError(
              document.getElementById('password-error'),
              data.detail || i18next.t('auth.login.accountInactive') || 'Account inactive'
            );
          }
        } else {
          showError(
            document.getElementById('password-error'),
            data.detail || i18next.t('messages.error') || 'An error occurred'
          );
        }
      }
    } catch (error) {
      console.error('Login error:', error);
      showError(
        document.getElementById('password-error'),
        i18next.t('messages.error') || 'An error occurred'
      );
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = i18next.t('auth.login.loginButton') || 'Login';
    }
  });
}

// Register Form Handler
function setupRegisterForm() {
  const form = document.getElementById('register-form');
  if (!form) return;

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

    const username = document.getElementById('username').value.trim();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirm-password').value;

    // Validation
    let hasErrors = false;

    if (!username || username.length < 3 || username.length > 50) {
      showError(
        document.getElementById('username-error'),
        i18next.t('auth.register.usernameInvalid') || 'Username must be 3-50 characters'
      );
      hasErrors = true;
    }

    if (!/^[a-zA-Z0-9_-]+$/.test(username)) {
      showError(
        document.getElementById('username-error'),
        i18next.t('auth.register.usernamePattern') ||
          'Username can only contain letters, numbers, underscore, and hyphen'
      );
      hasErrors = true;
    }

    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      showError(
        document.getElementById('email-error'),
        i18next.t('auth.register.emailInvalid') || 'Invalid email address'
      );
      hasErrors = true;
    }

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
      const response = await fetch(`${API_BASE}/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: username,
          email: email,
          password: password,
          confirm_password: confirmPassword,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // Store tokens
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);

        showNotification(
          i18next.t('auth.register.success') || 'Registration successful!',
          'success'
        );

        // Redirect to main page
        setTimeout(() => {
          window.location.href = '/';
        }, 1000);
      } else {
        // Handle errors
        if (data.detail) {
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
      }
    } catch (error) {
      console.error('Register error:', error);
      showNotification(i18next.t('messages.error') || 'An error occurred', 'error');
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = i18next.t('auth.register.registerButton') || 'Register';
    }
  });
}

// Initialize Page
function initAuthPage() {
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
  if (document.getElementById('login-form')) {
    setupLoginForm();
  } else if (document.getElementById('register-form')) {
    setupRegisterForm();
  }
}
