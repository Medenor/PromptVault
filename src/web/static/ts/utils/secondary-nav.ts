/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Shared mobile-drawer nav chrome for secondary pages (auth, backup,
 * import/export, manage tags/categories, profile). Wires the hamburger
 * drawer, logout, and admin-link visibility so this isn't reimplemented
 * per page. Homepage (index.html/app.ts) has its own richer nav and does
 * not use this module.
 */

import { initMobileNav } from '@/mobile-nav';
import { APIRequestError } from '@/utils/api';
import { reportError } from '@/telemetry';
import { logout, hideAuthOnlyElements, fetchRoleAndRevealAdmin } from '@/utils/auth-nav';

export interface SecondaryNavOptions {
  /** Component name passed to reportError for telemetry. */
  component: string;
  /** Wire #logout-btn/#logout-btn-mobile and admin-link visibility. Default false. */
  requireAuth?: boolean;
}

async function checkAdminAccess(component: string): Promise<void> {
  if (window.__AUTH_ENABLED__ === false) {
    hideAuthOnlyElements();
    return;
  }

  try {
    await fetchRoleAndRevealAdmin();
  } catch (error) {
    reportError(component, 'checkAdminAccess', error);
    if (error instanceof APIRequestError && error.isAuthError()) {
      window.location.href = '/auth/login';
    }
  }
}

/**
 * Wires up the shared hamburger drawer for a secondary page: mobile-nav
 * drawer open/close, and (when requireAuth) logout + admin-link visibility.
 */
export function initSecondaryNav(options: SecondaryNavOptions): void {
  const { component, requireAuth = false } = options;

  initMobileNav();

  if (!requireAuth) {
    return;
  }

  document.getElementById('logout-btn')?.addEventListener('click', () => {
    void logout(component);
  });
  document.getElementById('logout-btn-mobile')?.addEventListener('click', () => {
    void logout(component);
  });

  void checkAdminAccess(component);
}
