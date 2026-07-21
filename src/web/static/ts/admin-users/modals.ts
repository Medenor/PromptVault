/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { t } from '@/utils/i18n';
import type { PasswordChecks } from './types';

const HIDDEN_CLASS = 'hidden';

export function normalizeErrorDetail(
  detail: string | Array<{ loc?: Array<string | number>; msg?: string }> | undefined
): string | undefined {
  if (typeof detail === 'string') {
    return detail;
  }
  if (Array.isArray(detail)) {
    const first = detail[0];
    return first?.msg;
  }
  return undefined;
}

export function showModal(modalId: string): void {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove(HIDDEN_CLASS);
    // Move focus to first focusable element in modal
    const firstFocusable = modal.querySelector('h2, button, input, [tabindex="0"]') as HTMLElement;
    if (firstFocusable) {
      firstFocusable.focus();
    }
  }
}

export function hideModal(modalId: string, trigger: HTMLElement | null): void {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add(HIDDEN_CLASS);
  trigger?.focus();
}

export function mapCreateUserField(field: string): { inputId: string; errorId: string } | null {
  switch (field) {
    case 'username':
      return { inputId: 'create-username', errorId: 'create-username-error' };
    case 'email':
      return { inputId: 'create-email', errorId: 'create-email-error' };
    case 'password':
      return { inputId: 'create-password', errorId: 'create-password-error' };
    case 'confirm_password':
      return { inputId: 'create-confirm-password', errorId: 'create-confirm-password-error' };
    default:
      return null;
  }
}

export function checkPasswordStrength(password: string): {
  strength: number;
  checks: PasswordChecks;
} {
  let strength = 0;
  const checks: PasswordChecks = {
    length: password.length >= 12,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    digit: /[0-9]/.test(password),
    special: /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(password),
  };

  Object.values(checks).forEach((check) => {
    if (check) strength += 1;
  });

  return { strength, checks };
}

export function updatePasswordStrengthDisplay(strength: number): void {
  const strengthBar = document.getElementById('create-strength-bar-fill');
  const strengthText = document.getElementById('create-strength-text');

  if (!strengthBar || !strengthText) return;

  strengthBar.className = 'h-full transition-all duration-300';
  if (strength >= 5) {
    strengthBar.classList.add('bg-green-500');
    strengthBar.style.width = '100%';
    strengthText.textContent = t('auth.register.strengthStrong') || 'Strong password';
    strengthText.className = 'text-sm mt-1 text-green-600 font-medium';
  } else if (strength >= 3) {
    strengthBar.classList.add('bg-yellow-500');
    strengthBar.style.width = '66%';
    strengthText.textContent = t('auth.register.strengthMedium') || 'Medium password';
    strengthText.className = 'text-sm mt-1 text-yellow-600 font-medium';
  } else if (strength > 0) {
    strengthBar.classList.add('bg-red-500');
    strengthBar.style.width = '33%';
    strengthText.textContent = t('auth.register.strengthWeak') || 'Weak password';
    strengthText.className = 'text-sm mt-1 text-red-600 font-medium';
  } else {
    strengthBar.style.width = '0%';
    strengthText.textContent = '';
  }
}

export function resetPasswordRequirements(): void {
  ['req-length', 'req-uppercase', 'req-lowercase', 'req-digit', 'req-special'].forEach((id) => {
    const element = document.getElementById(id);
    if (element) {
      element.classList.remove('text-green-600');
      element.classList.add('text-gray-600');
      const icon = element.querySelector('span:first-child');
      if (icon) icon.textContent = '○';
    }
  });
}

export function updatePasswordRequirements(): void {
  const password =
    (document.getElementById('create-password') as HTMLInputElement | null)?.value ?? '';
  const { strength, checks } = checkPasswordStrength(password);

  const requirements: Record<string, boolean> = {
    'req-length': checks.length,
    'req-uppercase': checks.uppercase,
    'req-lowercase': checks.lowercase,
    'req-digit': checks.digit,
    'req-special': checks.special,
  };

  Object.entries(requirements).forEach(([id, met]) => {
    const element = document.getElementById(id);
    if (element) {
      if (met) {
        element.classList.remove('text-gray-600');
        element.classList.add('text-green-600');
        const icon = element.querySelector('span:first-child');
        if (icon) icon.textContent = '●';
      } else {
        element.classList.remove('text-green-600');
        element.classList.add('text-gray-600');
        const icon = element.querySelector('span:first-child');
        if (icon) icon.textContent = '○';
      }
    }
  });

  updatePasswordStrengthDisplay(strength);
}

export function setupPasswordToggle(toggleButtonId: string, passwordInputId: string): void {
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
