/**
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Shared auth/nav-chrome logic used by both the homepage (app.ts) and the
 * secondary-page nav helper (utils/secondary-nav.ts): logging out, hiding
 * auth-only UI elements, and revealing the admin link for admin users.
 * Extracted so the logout contract, auth-only element list, and
 * admin-visibility check can't silently diverge between the two call sites.
 */

import { apiGet } from '@/utils/api';
import { clearOfflineDataOnLogout } from '@/sw-register';
import { reportError } from '@/telemetry';

/**
 * Log the current user out: revokes the refresh token server-side (best
 * effort), clears local/session storage and cached offline data, then
 * redirects to the login page. In anonymous mode (AUTH_ENABLED=false) there
 * is no session to revoke, so this just navigates home.
 */
export async function logout(component: string): Promise<void> {
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
    // Clear cached prompt API responses so a different user signing in on
    // this device afterward can't see this user's data. Awaited (with an
    // internal timeout fallback) so navigation doesn't race the cache clear.
    await clearOfflineDataOnLogout();

    // Always clear storage and redirect
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    sessionStorage.clear();

    window.location.href = '/auth/login';
  }
}

/**
 * Hide elements that only make sense when authentication is enabled
 * (profile/logout buttons, mobile drawer account section, profile links).
 */
export function hideAuthOnlyElements(): void {
  const idsToHide = ['profile-btn', 'logout-btn', 'mobile-drawer-account-section'];
  idsToHide.forEach((id) => {
    const el = document.getElementById(id);
    if (el) {
      el.style.display = 'none';
    }
  });
  // Hide profile navigation links (desktop button + mobile dropdown entries).
  document.querySelectorAll<HTMLElement>('[onclick*="/auth/profile"]').forEach((el) => {
    el.style.display = 'none';
  });
}

/**
 * Reveal the admin-only nav buttons (desktop + mobile) when the given role
 * is 'admin'. Secondary pages may not render the desktop `#admin-btn` at
 * all, only `#admin-btn-mobile` — both lookups tolerate a missing element.
 */
export function revealAdminButtons(role: string | undefined): void {
  if (role !== 'admin') {
    return;
  }
  const adminBtn = document.getElementById('admin-btn');
  const adminBtnMobile = document.getElementById('admin-btn-mobile');
  if (adminBtn) {
    adminBtn.style.display = '';
  }
  if (adminBtnMobile) {
    adminBtnMobile.style.display = '';
  }
}

/**
 * Fetch the current user's role and reveal admin-only nav buttons if they
 * are an admin. Callers handle fetch failures (e.g. reporting them and
 * deciding how to react to auth errors, such as redirecting to login).
 */
export async function fetchRoleAndRevealAdmin(): Promise<{ role?: string }> {
  const data = await apiGet<{ role?: string }>('/api/auth/me');
  revealAdminButtons(data.role);
  return data;
}
