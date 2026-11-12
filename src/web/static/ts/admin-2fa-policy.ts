/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Admin 2FA-required role policy screen (User Story 4).
 *
 * Renders a role-by-role "required" toggle on the admin users page, backed
 * by GET/PUT /api/admin/2fa/policy.
 */

import { reportError } from '@/telemetry';
import { t, tUnsafe } from '@/utils/i18n';
import { apiGet, apiPut } from '@/utils/api';
import { showNotification } from '@/utils/notifications';
import { html, raw } from '@/utils/safe-html';

const API_BASE = '/api/admin/2fa/policy';

interface TotpRolePolicyItem {
  role: string;
  required: boolean;
}

interface TotpPolicyResponse {
  roles: TotpRolePolicyItem[];
}

function getContainer(): HTMLElement | null {
  return document.getElementById('totp-2fa-policy-card');
}

function roleLabel(role: string): string {
  const key = `admin.users.role${role.charAt(0).toUpperCase()}${role.slice(1)}`;
  return tUnsafe(key) || role.charAt(0).toUpperCase() + role.slice(1);
}

function render(roles: TotpRolePolicyItem[]): void {
  const container = getContainer();
  if (!container) return;

  // eslint-disable-next-line no-restricted-properties -- structurally escaped via html`` tagged template (utils/safe-html.ts)
  container.innerHTML = html`
    <div class="space-y-3">
      ${raw(
        roles
          .map(
            (entry) => html`
              <label
                class="flex items-center justify-between gap-4 p-3 border border-gray-200 rounded-md dark:border-gray-700"
              >
                <span class="text-sm font-medium text-gray-900 dark:text-gray-100">
                  ${roleLabel(entry.role)}
                </span>
                <input
                  type="checkbox"
                  data-role="${entry.role}"
                  class="totp-policy-toggle w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 dark:border-gray-600"
                  ${entry.required ? 'checked' : ''}
                />
              </label>
            `
          )
          .join('')
      )}
    </div>
  `;

  container.querySelectorAll<HTMLInputElement>('.totp-policy-toggle').forEach((toggle) => {
    toggle.addEventListener('change', () => {
      void handleToggle(toggle);
    });
  });
}

async function handleToggle(toggle: HTMLInputElement): Promise<void> {
  const role = toggle.dataset.role;
  if (!role) return;

  const required = toggle.checked;
  // A disabled control drops keyboard focus to <body>; remember it so focus
  // can be put back once the request settles (FR-019).
  const hadFocus = document.activeElement === toggle;
  toggle.disabled = true;

  try {
    await apiPut<TotpRolePolicyItem>(API_BASE, { role, required });
    showNotification(
      t('admin.users.twoFactorPolicy.updateSuccess') || 'Two-factor authentication policy updated.',
      'success'
    );
  } catch (error) {
    toggle.checked = !required;
    reportError('admin-2fa-policy', 'handleToggle', error);
    showNotification(
      t('admin.users.twoFactorPolicy.updateError') ||
        'Failed to update two-factor authentication policy.',
      'error'
    );
  } finally {
    toggle.disabled = false;
    if (hadFocus) toggle.focus();
  }
}

export async function initAdminTotpPolicy(): Promise<void> {
  const container = getContainer();
  if (!container) return;

  try {
    const data = await apiGet<TotpPolicyResponse>(API_BASE);
    render(data.roles);
  } catch (error) {
    reportError('admin-2fa-policy', 'initAdminTotpPolicy', error);
    showNotification(
      t('admin.users.twoFactorPolicy.loadError') ||
        'Failed to load two-factor authentication policy.',
      'error'
    );
  }
}

// Exposed for tests.
export const __internal = { handleToggle, render };
