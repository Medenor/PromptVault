// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

import { test as base } from '@playwright/test';

/**
 * Authentication fixtures for accessibility testing
 * Provides authenticated browser contexts for user and admin roles
 */

/**
 * Login helper function
 * Handles authentication with retry logic for rate-limited endpoints
 *
 * @param {import('@playwright/test').Page} page - Playwright page
 * @param {string} username - Username or email
 * @param {string} password - Password
 * @param {number} attempt - Current attempt number
 * @returns {Promise<void>}
 */
export async function login(page, username, password, attempt = 1) {
  const baseURL = process.env.ACCESSIBILITY_BASE_URL ?? 'http://127.0.0.1:8003';
  const maxAttempts = 7;
  let currentAttempt = attempt;

  while (true) {
    await page.goto(`${baseURL}/auth/login`, { waitUntil: 'networkidle' });

    const usernameInput = page.locator('#username-or-email').first();
    const passwordInput = page.locator('#password').first();
    const loginButton = page.locator('button[type="submit"]').first();

    await usernameInput.fill(username);
    await passwordInput.fill(password);

    const [loginResponse] = await Promise.all([
      page.waitForResponse(
        (response) =>
          response.url().includes('/api/auth/login') && response.request().method() === 'POST',
        { timeout: 30000 }
      ),
      loginButton.click(),
    ]);

    // Handle rate limiting
    if (loginResponse.status() === 429 && currentAttempt < maxAttempts) {
      const rawRetryAfter = loginResponse.headers()['retry-after'];
      const retryAfter = rawRetryAfter ? Number(rawRetryAfter) : NaN;
      const backoffSeconds = Number.isFinite(retryAfter)
        ? Math.max(1, retryAfter)
        : Math.min(180, Math.pow(2, currentAttempt - 1) * 15);

      // Add cushion to avoid retrying at the edge of the window
      await page.waitForTimeout(backoffSeconds * 1000 + 1250);
      currentAttempt += 1;
      continue;
    }

    if (!loginResponse.ok()) {
      const extra =
        loginResponse.status() === 429
          ? ' (rate limited; try reusing ACCESSIBILITY_AUTH_STATE_DIR or using a single admin account for both user/admin scans)'
          : '';
      throw new Error(
        `Login failed for "${username}": received status ${loginResponse.status()} from /api/auth/login.${extra}`
      );
    }

    // Wait for redirect after successful login
    await page.waitForURL((url) => !url.pathname.includes('/auth/login'), { timeout: 20000 });
    return;
  }
}

/**
 * Logout helper function
 * Signs out the current user
 *
 * @param {import('@playwright/test').Page} page - Playwright page
 * @returns {Promise<void>}
 */
export async function logout(page) {
  try {
    // Try to find and click logout button
    const logoutButton = page.locator('button:has-text("Logout"), a:has-text("Logout"), [aria-label*="Logout"]').first();
    await logoutButton.click();
    await page.waitForURL(/\/auth\/login|\/$/);
  } catch (error) {
    console.warn('Could not find logout button:', error.message);
    // Fallback: clear cookies and local storage
    await page.context().clearCookies();
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
  }
}

/**
 * Create storage state for authentication
 * Saves cookies and local storage for reuse across tests
 *
 * @param {import('@playwright/test').BrowserContext} context - Browser context
 * @param {string} username - Username for login
 * @param {string} password - Password for login
 * @param {string} outputPath - Path to save auth state
 * @returns {Promise<void>}
 */
export async function createAuthState(context, username, password, outputPath) {
  const page = await context.newPage();
  try {
    await login(page, username, password);
    await context.storageState({ path: outputPath });
  } finally {
    await page.close();
  }
}

/**
 * Authenticated user fixture
 * Provides a logged-in page for user-level tests
 */
export const authenticatedUserTest = base.extend({
  /**
   * @param {any} _use - Playwright parameter
   * @param {import('@playwright/test').TestInfo} testInfo - Test context
   */
  authenticatedPage: async ({ browser }, use, testInfo) => {
    const username = process.env.ACCESSIBILITY_USER_USERNAME;
    const password = process.env.ACCESSIBILITY_USER_PASSWORD;
    const stateDir = process.env.ACCESSIBILITY_AUTH_STATE_DIR;

    if (!username || !password) {
      testInfo.skip(true, 'ACCESSIBILITY_USER_USERNAME and ACCESSIBILITY_USER_PASSWORD not set');
      return;
    }

    const storageStatePath = stateDir
      ? `${stateDir}/user-state.json`
      : undefined;

    const context = await browser.newContext(
      storageStatePath ? { storageState: storageStatePath } : undefined
    );
    const page = await context.newPage();

    try {
      // If we don't have pre-saved state, login now
      if (!storageStatePath) {
        await login(page, username, password);
      }
      await use(page);
    } finally {
      await context.close();
    }
  },
});

/**
 * Authenticated admin fixture
 * Provides a logged-in page with admin privileges
 */
export const authenticatedAdminTest = base.extend({
  /**
   * @param {any} _use - Playwright parameter
   * @param {import('@playwright/test').TestInfo} testInfo - Test context
   */
  authenticatedPage: async ({ browser }, use, testInfo) => {
    const username = process.env.ACCESSIBILITY_ADMIN_USERNAME;
    const password = process.env.ACCESSIBILITY_ADMIN_PASSWORD;
    const stateDir = process.env.ACCESSIBILITY_AUTH_STATE_DIR;

    if (!username || !password) {
      testInfo.skip(true, 'ACCESSIBILITY_ADMIN_USERNAME and ACCESSIBILITY_ADMIN_PASSWORD not set');
      return;
    }

    const storageStatePath = stateDir
      ? `${stateDir}/admin-state.json`
      : undefined;

    const context = await browser.newContext(
      storageStatePath ? { storageState: storageStatePath } : undefined
    );
    const page = await context.newPage();

    try {
      // If we don't have pre-saved state, login now
      if (!storageStatePath) {
        await login(page, username, password);
      }
      await use(page);
    } finally {
      await context.close();
    }
  },
});

/**
 * Dual-role fixture for testing both user and admin paths
 * Provides both authenticated user and admin pages
 */
export const dualAuthTest = base.extend({
  /**
   * @type {[import('@playwright/test').Page, import('@playwright/test').Page]}
   */
  authenticatedPages: async ({ browser }, use) => {
    const userUsername = process.env.ACCESSIBILITY_USER_USERNAME;
    const userPassword = process.env.ACCESSIBILITY_USER_PASSWORD;
    const adminUsername = process.env.ACCESSIBILITY_ADMIN_USERNAME;
    const adminPassword = process.env.ACCESSIBILITY_ADMIN_PASSWORD;
    const stateDir = process.env.ACCESSIBILITY_AUTH_STATE_DIR;

    const pages = [];

    // Create user context
    if (userUsername && userPassword) {
      const userStateFile = stateDir ? `${stateDir}/user-state.json` : undefined;
      const userContext = await browser.newContext(
        userStateFile ? { storageState: userStateFile } : undefined
      );
      const userPage = await userContext.newPage();

      if (!userStateFile) {
        await login(userPage, userUsername, userPassword);
      }
      pages.push({ role: 'user', page: userPage, context: userContext });
    }

    // Create admin context
    if (adminUsername && adminPassword) {
      const adminStateFile = stateDir ? `${stateDir}/admin-state.json` : undefined;
      const adminContext = await browser.newContext(
        adminStateFile ? { storageState: adminStateFile } : undefined
      );
      const adminPage = await adminContext.newPage();

      if (!adminStateFile) {
        await login(adminPage, adminUsername, adminPassword);
      }
      pages.push({ role: 'admin', page: adminPage, context: adminContext });
    }

    await use(pages);

    // Cleanup
    for (const { context } of pages) {
      await context.close();
    }
  },
});

/**
 * Get the base URL for tests
 *
 * @returns {string} Base URL
 */
export function getBaseURL() {
  return process.env.ACCESSIBILITY_BASE_URL ?? 'http://127.0.0.1:8003';
}

/**
 * Helper to navigate to a protected route
 * Assumes user is already authenticated
 *
 * @param {import('@playwright/test').Page} page - Playwright page
 * @param {string} route - Route to navigate to
 * @returns {Promise<void>}
 */
export async function navigateToProtectedRoute(page, route) {
  const baseURL = getBaseURL();
  const url = new URL(route, baseURL).toString();
  await page.goto(url, { waitUntil: 'networkidle' });
}

/**
 * Check if user is currently authenticated
 *
 * @param {import('@playwright/test').Page} page - Playwright page
 * @returns {Promise<boolean>}
 */
export async function isAuthenticated(page) {
  try {
    const cookies = await page.context().cookies();
    const hasCookie = cookies.some(
      (cookie) =>
        cookie.name === 'access_token' ||
        cookie.name === 'session' ||
        cookie.name === 'Authorization'
    );

    if (!hasCookie) return false;

    // Try to navigate to a protected route
    const baseURL = getBaseURL();
    const response = await page.goto(`${baseURL}/auth/profile`, { waitUntil: 'networkidle' });
    return !response?.url().includes('/auth/login');
  } catch (error) {
    return false;
  }
}

/**
 * Clear authentication state
 *
 * @param {import('@playwright/test').Page} page - Playwright page
 * @returns {Promise<void>}
 */
export async function clearAuthState(page) {
  await page.context().clearCookies();
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
}
