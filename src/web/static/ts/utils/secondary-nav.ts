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
import { apiGet, APIRequestError } from '@/utils/api';
import { reportError } from '@/telemetry';
import { clearOfflineDataOnLogout } from '@/sw-register';

export interface SecondaryNavOptions {
  /** Component name passed to reportError for telemetry. */
  component: string;
  /** Wire #logout-btn/#logout-btn-mobile and admin-link visibility. Default false. */
  requireAuth?: boolean;
}

async function logout(component: string): Promise<void> {
  if (window.__AUTH_ENABLED__ === false) {
    window.location.href = '/';
    return;
  }

  try {
    const refreshToken =
      localStorage.getItem('refresh_token') || sessionStorage.getItem('refresh_token');

    await fetch('/api/auth/logout', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
      body: refreshToken ? JSON.stringify({ refresh_token: refreshToken }) : '{}',
    });
  } catch (error) {
    reportError(component, 'logout-error', error, {}, 'warning');
  } finally {
    // Clear cached prompt API responses and any queued offline writes so a
    // different user signing in on this device afterward can't see or replay
    // this user's data.
    await clearOfflineDataOnLogout();

    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    sessionStorage.clear();

    window.location.href = '/auth/login';
  }
}

function hideAuthOnlyElements(): void {
  const idsToHide = ['profile-btn', 'logout-btn', 'mobile-drawer-account-section'];
  idsToHide.forEach((id) => {
    document.getElementById(id)?.style.setProperty('display', 'none');
  });
  document.querySelectorAll<HTMLElement>('[onclick*="/auth/profile"]').forEach((el) => {
    el.style.display = 'none';
  });
}

async function checkAdminAccess(component: string): Promise<void> {
  if (window.__AUTH_ENABLED__ === false) {
    hideAuthOnlyElements();
    return;
  }

  try {
    const data = await apiGet<{ role?: string }>('/api/auth/me');
    if (data.role === 'admin') {
      document.getElementById('admin-btn')?.style.setProperty('display', '');
      document.getElementById('admin-btn-mobile')?.style.setProperty('display', '');
    }
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
