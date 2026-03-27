// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

/**
 * Accessibility test fixtures index
 * Central export point for test fixtures and helpers
 */

export {
  login,
  logout,
  createAuthState,
  authenticatedUserTest,
  authenticatedAdminTest,
  dualAuthTest,
  getBaseURL,
  navigateToProtectedRoute,
  isAuthenticated,
  clearAuthState,
} from './auth.js';
