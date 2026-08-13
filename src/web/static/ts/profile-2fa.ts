/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * TOTP two-factor authentication enrollment card (User Story 1).
 *
 * Renders on the profile page's Security section. Flow:
 *   1. "Start enrollment" -> POST /api/auth/2fa/enroll -> QR + manual secret
 *   2. 6-digit code form -> POST /api/auth/2fa/verify -> recovery codes
 *   3. One-time recovery-codes display (copy / download), shown exactly once
 *
 * Later phases (disable/regenerate, T044-T048) extend this module.
 */

import { reportError } from '@/telemetry';
import { t } from '@/utils/i18n';
import { apiPost, APIRequestError } from '@/utils/api';
import { showNotification } from '@/utils/notifications';
import { announce } from '@/utils/a11y';
import { html, raw } from '@/utils/safe-html';

const API_BASE = '/api/auth/2fa';

interface TotpEnrollResponse {
  secret: string;
  provisioning_uri: string;
  qr_svg: string;
}

interface TotpConfirmResponse {
  enabled: boolean;
  recovery_codes: string[];
}

type EnrollmentStep = 'idle' | 'scanning' | 'recovery-codes';

let currentStep: EnrollmentStep = 'idle';
let pendingSecret: string | null = null;

function getContainer(): HTMLElement | null {
  return document.getElementById('totp-2fa-card');
}

function render(): void {
  const container = getContainer();
  if (!container) return;

  if (currentStep === 'idle') {
    renderIdle(container);
  }
}

function renderIdle(container: HTMLElement): void {
  // eslint-disable-next-line no-restricted-properties -- structurally escaped via html`` tagged template (utils/safe-html.ts)
  container.innerHTML = html`
    <p class="text-sm text-gray-700 dark:text-gray-300 mb-4">
      ${t('auth.profile.twoFactor.description') ||
      'Add an extra layer of security to your account by requiring a code from an authenticator app when you log in.'}
    </p>
    <button
      type="button"
      id="totp-start-enrollment"
      class="px-4 py-2 bg-blue-800 text-white rounded-md hover:bg-blue-900 font-medium"
    >
      ${t('auth.profile.twoFactor.startButton') || 'Set up two-factor authentication'}
    </button>
  `;

  const startButton = document.getElementById('totp-start-enrollment');
  startButton?.addEventListener('click', () => {
    void startEnrollment();
  });
}

function renderScanning(container: HTMLElement, data: TotpEnrollResponse): void {
  pendingSecret = data.secret;

  // The QR SVG comes from our own trusted backend (qrcode package server-side
  // rendering), never from user input — safe to mark as raw HTML.
  // eslint-disable-next-line no-restricted-properties -- structurally escaped via html`` tagged template (utils/safe-html.ts)
  container.innerHTML = html`
    <div class="space-y-4">
      <div>
        <h3 class="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
          ${t('auth.profile.twoFactor.scanTitle') || 'Scan this QR code'}
        </h3>
        <p class="text-sm text-gray-700 dark:text-gray-300 mb-3">
          ${t('auth.profile.twoFactor.scanInstructions') ||
          'Scan the QR code below with your authenticator app (e.g. Google Authenticator, Authy, 1Password).'}
        </p>
        <div
          id="totp-qr-container"
          class="inline-block bg-white p-3 rounded-md border border-gray-200"
          role="img"
          aria-label="${t('auth.profile.twoFactor.scanTitle') ||
          'QR code for two-factor authentication setup'}"
        >
          ${raw(data.qr_svg)}
        </div>
      </div>

      <div>
        <h4 class="text-sm font-medium text-gray-900 dark:text-gray-100 mb-1">
          ${t('auth.profile.twoFactor.manualEntryTitle') || "Can't scan the code?"}
        </h4>
        <p class="text-sm text-gray-700 dark:text-gray-300 mb-2">
          ${t('auth.profile.twoFactor.manualEntryInstructions') ||
          'Enter this setup key manually in your authenticator app:'}
        </p>
        <div class="flex items-center gap-2">
          <code
            id="totp-manual-secret"
            class="px-3 py-2 bg-gray-100 dark:bg-gray-900 rounded-md text-sm font-mono select-all"
            tabindex="0"
            aria-label="${t('auth.profile.twoFactor.manualSecretLabel') ||
            'Manual setup key'}: ${data.secret}"
            >${data.secret}</code
          >
          <button
            type="button"
            id="totp-copy-secret"
            class="px-3 py-2 text-sm bg-gray-200 dark:bg-gray-700 dark:text-gray-100 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600"
          >
            ${t('auth.profile.twoFactor.copySecret') || 'Copy setup key'}
          </button>
        </div>
      </div>

      <form id="totp-confirm-form" class="space-y-3" novalidate>
        <div>
          <label
            for="totp-confirm-code"
            class="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2"
          >
            ${t('auth.profile.twoFactor.codeLabel') || 'Enter the 6-digit code'}
          </label>
          <input
            type="text"
            id="totp-confirm-code"
            name="code"
            inputmode="numeric"
            autocomplete="one-time-code"
            pattern="[0-9]*"
            maxlength="6"
            required
            aria-required="true"
            aria-describedby="totp-confirm-error"
            class="w-full max-w-xs px-3 py-2 text-sm text-gray-900 border border-gray-600 rounded-md dark:text-gray-100 dark:border-gray-500 dark:bg-gray-800"
            placeholder="${t('auth.profile.twoFactor.codePlaceholder') || '123456'}"
          />
          <p
            id="totp-confirm-error"
            class="text-red-700 text-xs mt-1 hidden"
            role="alert"
            aria-live="assertive"
          ></p>
        </div>
        <div class="flex gap-3">
          <button
            type="submit"
            class="px-4 py-2 bg-blue-800 text-white rounded-md hover:bg-blue-900 font-medium"
          >
            ${t('auth.profile.twoFactor.confirmButton') || 'Verify and enable'}
          </button>
          <button
            type="button"
            id="totp-cancel-enrollment"
            class="px-4 py-2 bg-gray-300 text-gray-900 rounded-md hover:bg-gray-400 font-medium dark:text-gray-100"
          >
            ${t('auth.profile.twoFactor.cancelButton') || 'Cancel'}
          </button>
        </div>
      </form>
    </div>
  `;

  document.getElementById('totp-copy-secret')?.addEventListener('click', () => {
    void copySecretToClipboard(data.secret);
  });

  document.getElementById('totp-cancel-enrollment')?.addEventListener('click', () => {
    currentStep = 'idle';
    pendingSecret = null;
    render();
  });

  const form = document.getElementById('totp-confirm-form') as HTMLFormElement | null;
  form?.addEventListener('submit', (event) => {
    event.preventDefault();
    void confirmEnrollment();
  });

  // FR-019: manual-entry secret must be reachable/announced for screen readers.
  announce(
    `${t('auth.profile.twoFactor.manualSecretLabel') || 'Manual setup key'}: ${data.secret}`,
    { id: 'validation-announcer', politeness: 'polite' }
  );
}

function renderRecoveryCodes(container: HTMLElement, codes: string[]): void {
  // eslint-disable-next-line no-restricted-properties -- structurally escaped via html`` tagged template (utils/safe-html.ts)
  container.innerHTML = html`
    <div class="space-y-4">
      <div
        class="p-3 bg-amber-50 border border-amber-300 rounded-md dark:bg-amber-950 dark:border-amber-800"
        role="alert"
      >
        <p class="text-sm font-medium text-amber-900 dark:text-amber-200 mb-1">
          ${t('auth.profile.twoFactor.recoveryCodesTitle') || 'Save your recovery codes'}
        </p>
        <p class="text-sm text-amber-800 dark:text-amber-300">
          ${t('auth.profile.twoFactor.recoveryCodesWarning') ||
          'These codes are shown only once. Store them somewhere safe — each code can be used once if you lose access to your authenticator app.'}
        </p>
      </div>

      <ul
        id="totp-recovery-codes-list"
        class="grid grid-cols-2 gap-2 font-mono text-sm p-3 bg-gray-100 dark:bg-gray-900 rounded-md"
      >
        ${raw(codes.map((code) => `<li>${code}</li>`).join(''))}
      </ul>

      <div class="flex flex-wrap gap-3">
        <button
          type="button"
          id="totp-copy-recovery-codes"
          class="px-4 py-2 text-sm bg-gray-200 dark:bg-gray-700 dark:text-gray-100 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600"
        >
          ${t('auth.profile.twoFactor.copyRecoveryCodes') || 'Copy codes'}
        </button>
        <button
          type="button"
          id="totp-download-recovery-codes"
          class="px-4 py-2 text-sm bg-gray-200 dark:bg-gray-700 dark:text-gray-100 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600"
        >
          ${t('auth.profile.twoFactor.downloadRecoveryCodes') || 'Download as text file'}
        </button>
        <button
          type="button"
          id="totp-recovery-codes-done"
          class="px-4 py-2 bg-blue-800 text-white rounded-md hover:bg-blue-900 font-medium"
        >
          ${t('auth.profile.twoFactor.doneButton') || 'Done'}
        </button>
      </div>
    </div>
  `;

  document.getElementById('totp-copy-recovery-codes')?.addEventListener('click', () => {
    void copyRecoveryCodesToClipboard(codes);
  });
  document.getElementById('totp-download-recovery-codes')?.addEventListener('click', () => {
    downloadRecoveryCodes(codes);
  });
  document.getElementById('totp-recovery-codes-done')?.addEventListener('click', () => {
    currentStep = 'idle';
    pendingSecret = null;
    render();
  });
}

async function startEnrollment(): Promise<void> {
  const container = getContainer();
  if (!container) return;

  try {
    const data = await apiPost<TotpEnrollResponse>(`${API_BASE}/enroll`);
    currentStep = 'scanning';
    renderScanning(container, data);
  } catch (error) {
    if (error instanceof APIRequestError) {
      if (error.status === 409) {
        showNotification(
          t('auth.profile.twoFactor.alreadyEnabled') ||
            'Two-factor authentication is already enabled.',
          'info'
        );
        return;
      }
      showNotification(
        error.message ||
          t('auth.profile.twoFactor.startError') ||
          'Failed to start two-factor authentication setup. Please try again.',
        'error'
      );
    } else {
      reportError('profile-2fa', 'startEnrollment', error);
      showNotification(
        t('auth.profile.twoFactor.startError') ||
          'Failed to start two-factor authentication setup. Please try again.',
        'error'
      );
    }
  }
}

async function confirmEnrollment(): Promise<void> {
  const codeInput = document.getElementById('totp-confirm-code') as HTMLInputElement | null;
  const errorEl = document.getElementById('totp-confirm-error');
  const code = codeInput?.value.trim() ?? '';

  if (errorEl) {
    errorEl.textContent = '';
    errorEl.classList.add('hidden');
  }
  codeInput?.setAttribute('aria-invalid', 'false');

  if (!code) {
    if (errorEl) {
      errorEl.textContent =
        t('auth.profile.twoFactor.codeRequired') ||
        'Please enter the 6-digit code from your authenticator app';
      errorEl.classList.remove('hidden');
    }
    codeInput?.setAttribute('aria-invalid', 'true');
    codeInput?.focus();
    return;
  }

  const submitButton = document
    .getElementById('totp-confirm-form')
    ?.querySelector('button[type="submit"]') as HTMLButtonElement | null;
  if (submitButton) submitButton.disabled = true;

  try {
    const data = await apiPost<TotpConfirmResponse>(`${API_BASE}/verify`, { code });

    currentStep = 'recovery-codes';
    pendingSecret = null;
    const container = getContainer();
    if (container) {
      renderRecoveryCodes(container, data.recovery_codes);
    }
    showNotification(
      t('auth.profile.twoFactor.enabledSuccess') || 'Two-factor authentication is now enabled.',
      'success'
    );
  } catch (error) {
    if (error instanceof APIRequestError) {
      let message =
        error.message ||
        t('auth.profile.twoFactor.confirmError') ||
        'Failed to verify code. Please try again.';
      if (error.status === 401) {
        message =
          t('auth.profile.twoFactor.invalidCode') ||
          'Incorrect code. Please check your authenticator app and try again.';
      } else if (error.status === 400) {
        message =
          t('auth.profile.twoFactor.noPendingEnrollment') ||
          'Enrollment session expired. Please start setup again.';
      }
      if (errorEl) {
        errorEl.textContent = message;
        errorEl.classList.remove('hidden');
      }
      codeInput?.setAttribute('aria-invalid', 'true');
      announce(message, { id: 'validation-announcer', politeness: 'assertive' });
    } else {
      reportError('profile-2fa', 'confirmEnrollment', error);
      showNotification(
        t('auth.profile.twoFactor.confirmError') || 'Failed to verify code. Please try again.',
        'error'
      );
    }
  } finally {
    if (submitButton) submitButton.disabled = false;
  }
}

async function copySecretToClipboard(secret: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(secret);
    showNotification(
      t('auth.profile.twoFactor.secretCopied') || 'Setup key copied to clipboard',
      'success'
    );
  } catch (error) {
    reportError('profile-2fa', 'copySecretToClipboard', error);
  }
}

async function copyRecoveryCodesToClipboard(codes: string[]): Promise<void> {
  try {
    await navigator.clipboard.writeText(codes.join('\n'));
    showNotification(
      t('auth.profile.twoFactor.recoveryCodesCopied') || 'Recovery codes copied to clipboard',
      'success'
    );
  } catch (error) {
    reportError('profile-2fa', 'copyRecoveryCodesToClipboard', error);
  }
}

function downloadRecoveryCodes(codes: string[]): void {
  const blob = new Blob([codes.join('\n') + '\n'], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'promptvault-recovery-codes.txt';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function initProfileTwoFactor(): void {
  const container = getContainer();
  if (!container) return;
  currentStep = 'idle';
  render();
}

// Exposed for tests / debugging in non-module contexts.
export const __internal = {
  startEnrollment,
  confirmEnrollment,
  getPendingSecret: () => pendingSecret,
};
