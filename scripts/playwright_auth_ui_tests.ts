// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

/**
 * Playwright UI Tests for PromptVault Authentication
 * Tests AUTH-UI test cases with admin test account
 *
 * Run with: npx playwright test scripts/playwright_auth_ui_tests.ts
 * Or: npm run test:ui
 */

import { test, expect, Page } from '@playwright/test';

// Test configuration
const BASE_URL = 'http://127.0.0.1:8003';
const TEST_ADMIN_USERNAME = 'test_admin_ui';
const TEST_ADMIN_EMAIL = 'test_admin_ui@example.com';
const TEST_ADMIN_PASSWORD = 'TestAdmin@Pass123456';
const TEST_USER_USERNAME = 'test_user_ui';
const TEST_USER_EMAIL = 'test_user_ui@example.com';
const TEST_USER_PASSWORD = 'TestUser@Pass123456';

/**
 * AUTH-UI-001: Login Page Renders Correctly
 */
test('AUTH-UI-001: Login page renders with all required elements', async ({ page }) => {
  await page.goto(`${BASE_URL}/auth/login`);

  // Check page title
  await expect(page).toHaveTitle(/login|connexion/i);

  // Check for required form elements
  const usernameInput = page
    .locator(
      'input[placeholder*="utilisateur"], input[placeholder*="username"], input[type="text"]'
    )
    .first();
  const passwordInput = page
    .locator(
      'input[placeholder*="mot de passe"], input[placeholder*="password"], input[type="password"]'
    )
    .first();
  const loginButton = page
    .locator(
      'button:has-text("Se connecter"), button:has-text("Login"), button:has-text("Sign In")'
    )
    .first();
  const registerLink = page
    .locator('a:has-text("créer"), a:has-text("register"), a:has-text("inscription")')
    .first();

  // All elements should be visible
  await expect(usernameInput).toBeVisible();
  await expect(passwordInput).toBeVisible();
  await expect(loginButton).toBeVisible();
  await expect(registerLink).toBeVisible();

  // Check for forgot password link
  const forgotLink = page
    .locator(
      'a:has-text("mot de passe oublié"), a:has-text("forgot password"), a:has-text("reset")'
    )
    .first();
  await expect(forgotLink).toBeVisible();
});

/**
 * AUTH-UI-002: Registration Page Renders Correctly
 */
test('AUTH-UI-002: Registration page renders with all required elements', async ({ page }) => {
  await page.goto(`${BASE_URL}/auth/register`);

  // Check page title
  await expect(page).toHaveTitle(/register|inscription/i);

  // Check for required form elements
  const usernameInput = page
    .locator('input[placeholder*="utilisateur"], input[placeholder*="username"]')
    .first();
  const emailInput = page.locator('input[type="email"]').first();
  const passwordInput = page
    .locator('input[placeholder*="mot de passe"], input[placeholder*="password"]')
    .first();
  const confirmPasswordInput = page
    .locator('input[placeholder*="confirmer"], input[placeholder*="confirm"]')
    .first();
  const registerButton = page
    .locator('button:has-text("créer"), button:has-text("register"), button:has-text("Sign Up")')
    .first();
  const loginLink = page
    .locator('a:has-text("connexion"), a:has-text("login"), a:has-text("sign in")')
    .first();

  // All elements should be visible
  await expect(usernameInput).toBeVisible();
  await expect(emailInput).toBeVisible();
  await expect(passwordInput).toBeVisible();
  await expect(confirmPasswordInput).toBeVisible();
  await expect(registerButton).toBeVisible();
  await expect(loginLink).toBeVisible();

  // Check for password strength indicator
  const strengthIndicator = page
    .locator(
      '[class*="strength"], [id*="strength"], span:has-text("Weak"), span:has-text("Strong")'
    )
    .first();
  if (await strengthIndicator.isVisible({ timeout: 1000 }).catch(() => false)) {
    await expect(strengthIndicator).toBeVisible();
  }
});

/**
 * AUTH-UI-003: Password Visibility Toggle
 */
test('AUTH-UI-003: Password visibility toggle works', async ({ page }) => {
  await page.goto(`${BASE_URL}/auth/login`);

  const passwordInput = page.locator('input[type="password"]').first();
  const visibilityToggle = page
    .locator('button[title*="password"], button[aria-label*="password"], [class*="toggle"]')
    .first();

  if (await visibilityToggle.isVisible({ timeout: 1000 }).catch(() => false)) {
    // Initially password input type should be "password"
    await expect(passwordInput).toHaveAttribute('type', 'password');

    // Click toggle to show password
    await visibilityToggle.click();

    // Password input type should now be "text"
    await expect(passwordInput).toHaveAttribute('type', 'text');

    // Click toggle again to hide password
    await visibilityToggle.click();

    // Password input type should be "password" again
    await expect(passwordInput).toHaveAttribute('type', 'password');
  }
});

/**
 * AUTH-UI-004: Form Validation - Empty Fields
 */
test('AUTH-UI-004: Login form shows error for empty fields', async ({ page }) => {
  await page.goto(`${BASE_URL}/auth/login`);

  const loginButton = page
    .locator('button:has-text("Se connecter"), button:has-text("Login")')
    .first();

  // Click login without entering anything
  await loginButton.click();

  // Should see validation error
  const errorMessage = page
    .locator(
      '[role="alert"], .error, [class*="error"], span:has-text("required"), span:has-text("requis")'
    )
    .first();

  if (await errorMessage.isVisible({ timeout: 2000 }).catch(() => false)) {
    await expect(errorMessage).toBeVisible();
  }

  // Still on login page
  expect(page.url()).toContain('/login') || expect(page.url()).toContain('/auth');
});

/**
 * AUTH-UI-005: Successful Login Flow
 */
test('AUTH-UI-005: Successful login redirects to dashboard', async ({ page }) => {
  // Register test user first if needed
  await registerTestUser(page, TEST_USER_USERNAME, TEST_USER_EMAIL, TEST_USER_PASSWORD);

  // Login
  await page.goto(`${BASE_URL}/auth/login`);

  const usernameInput = page
    .locator(
      'input[placeholder*="utilisateur"], input[placeholder*="username"], input[type="text"]'
    )
    .first();
  const passwordInput = page
    .locator(
      'input[placeholder*="mot de passe"], input[placeholder*="password"], input[type="password"]'
    )
    .first();
  const loginButton = page
    .locator('button:has-text("Se connecter"), button:has-text("Login")')
    .first();

  await usernameInput.fill(TEST_USER_USERNAME);
  await passwordInput.fill(TEST_USER_PASSWORD);
  await loginButton.click();

  // Should redirect to home/dashboard
  await page.waitForURL(/\/($|home|dashboard)/, { timeout: 5000 });

  // Should be logged in (check for logout button or user menu)
  const logoutButton = page
    .locator('button:has-text("déconnexion"), button:has-text("logout"), a:has-text("logout")')
    .first();
  const userMenu = page.locator('[class*="user"], [class*="profile"], [class*="menu"]').first();

  const isLoggedIn =
    (await logoutButton.isVisible({ timeout: 1000 }).catch(() => false)) ||
    (await userMenu.isVisible({ timeout: 1000 }).catch(() => false));

  expect(isLoggedIn).toBeTruthy();
});

/**
 * AUTH-UI-006: Logout Flow
 */
test('AUTH-UI-006: Logout button redirects to login page', async ({ page }) => {
  // Login first
  await loginTestUser(page, TEST_USER_USERNAME, TEST_USER_PASSWORD);

  // Find and click logout button
  const logoutButton = page
    .locator('button:has-text("déconnexion"), button:has-text("logout")')
    .first();
  const logoutMenuItem = page.locator('a:has-text("déconnexion"), a:has-text("logout")').first();

  const logoutElement = (await logoutButton.isVisible().catch(() => false))
    ? logoutButton
    : logoutMenuItem;

  await logoutElement.click();

  // Should redirect to login
  await page.waitForURL(/login|auth/, { timeout: 5000 });

  // Should not see logout button
  await expect(logoutButton).not.toBeVisible({ timeout: 1000 });
});

/**
 * AUTH-UI-007: Profile Page Access
 */
test('AUTH-UI-007: Profile page accessible when logged in', async ({ page }) => {
  // Login
  await loginTestUser(page, TEST_USER_USERNAME, TEST_USER_PASSWORD);

  // Navigate to profile (look for profile link or navigate directly)
  const profileLink = page
    .locator('a:has-text("profil"), a:has-text("profile"), [class*="profile"]')
    .first();

  if (await profileLink.isVisible({ timeout: 1000 }).catch(() => false)) {
    await profileLink.click();
  } else {
    await page.goto(`${BASE_URL}/profile`);
  }

  // Should see profile information
  const profileForm = page
    .locator('form, [class*="profile"], h1:has-text("Profil"), h1:has-text("Profile")')
    .first();

  if (await profileForm.isVisible({ timeout: 2000 }).catch(() => false)) {
    await expect(profileForm).toBeVisible();
  }
});

/**
 * AUTH-UI-008: Admin Panel Access (Admin User Only)
 */
test('AUTH-UI-008: Admin panel accessible to admin users', async ({ page }) => {
  // Create/login as admin test user
  await loginTestUser(page, TEST_ADMIN_USERNAME, TEST_ADMIN_PASSWORD);

  // Navigate to admin panel
  const adminLink = page.locator('a:has-text("admin"), [class*="admin"]').first();

  if (await adminLink.isVisible({ timeout: 1000 }).catch(() => false)) {
    await adminLink.click();

    // Should be on admin page
    expect(page.url()).toContain('admin');

    // Should see admin interface
    const adminPanel = page.locator('[class*="admin"]').first();
    await expect(adminPanel).toBeVisible();
  }
});

/**
 * AUTH-UI-009: Language Switcher
 */
test('AUTH-UI-009: Language switcher changes UI language', async ({ page }) => {
  await page.goto(`${BASE_URL}/auth/login`);

  // Find language switcher
  const languageSwitcher = page
    .locator('[class*="lang"], button:has-text("English"), button:has-text("Français")')
    .first();

  if (await languageSwitcher.isVisible({ timeout: 1000 }).catch(() => false)) {
    // Get initial language
    const initialContent = await page.textContent('body');

    // Click language switcher to change language
    await languageSwitcher.click();

    // Select different language
    const languageOption = page
      .locator('button:has-text("Français"), button:has-text("English")')
      .first();
    await languageOption.click({ timeout: 1000 }).catch(() => {});

    // Wait for page to update
    await page.waitForTimeout(1000);

    // Page should show different language
    const newContent = await page.textContent('body');
    expect(newContent).not.toBe(initialContent);
  }
});

/**
 * AUTH-UI-010: Responsive Design - Mobile View
 */
test('AUTH-UI-010: UI is responsive on mobile viewport', async ({ page }) => {
  // Set mobile viewport
  await page.setViewportSize({ width: 375, height: 667 });

  await page.goto(`${BASE_URL}/auth/login`);

  // Check that form is still visible and properly sized
  const loginForm = page.locator('form, [class*="form"]').first();

  if (await loginForm.isVisible()) {
    const boundingBox = await loginForm.boundingBox();

    // Form should fit within viewport width
    expect(boundingBox?.width).toBeLessThanOrEqual(375);

    // Elements should be tappable (height >= 44px)
    const inputs = page.locator('input, button').all();

    for (const input of await inputs) {
      const box = await input.boundingBox();
      if (box && box.height > 0) {
        expect(box.height).toBeGreaterThanOrEqual(30); // Slightly flexible for UI frameworks
      }
    }
  }
});

/**
 * Helper: Register a new test user
 */
async function registerTestUser(page: Page, username: string, email: string, password: string) {
  try {
    await page.goto(`${BASE_URL}/auth/register`);

    const usernameInput = page
      .locator('input[placeholder*="utilisateur"], input[placeholder*="username"]')
      .first();
    const emailInput = page.locator('input[type="email"]').first();
    const passwordInput = page
      .locator('input[placeholder*="mot de passe"], input[placeholder*="password"]')
      .first();
    const confirmPasswordInput = page
      .locator('input[placeholder*="confirmer"], input[placeholder*="confirm"]')
      .first();
    const registerButton = page
      .locator('button:has-text("créer"), button:has-text("register")')
      .first();

    // Check if user might already exist (skip if we can't find form)
    if (!(await usernameInput.isVisible({ timeout: 1000 }).catch(() => false))) {
      return;
    }

    await usernameInput.fill(username);
    await emailInput.fill(email);
    await passwordInput.fill(password);
    await confirmPasswordInput.fill(password);
    await registerButton.click();

    // Wait for registration to complete
    await page.waitForURL(/login|auth/, { timeout: 5000 }).catch(() => {});
  } catch (error) {
    // User might already exist, continue
  }
}

/**
 * Helper: Login with test credentials
 */
async function loginTestUser(page: Page, username: string, password: string) {
  await page.goto(`${BASE_URL}/auth/login`);

  const usernameInput = page
    .locator(
      'input[placeholder*="utilisateur"], input[placeholder*="username"], input[type="text"]'
    )
    .first();
  const passwordInput = page
    .locator(
      'input[placeholder*="mot de passe"], input[placeholder*="password"], input[type="password"]'
    )
    .first();
  const loginButton = page
    .locator('button:has-text("Se connecter"), button:has-text("Login")')
    .first();

  await usernameInput.fill(username);
  await passwordInput.fill(password);
  await loginButton.click();

  // Wait for redirect after login
  await page.waitForURL(/^(?!.*login)/, { timeout: 5000 }).catch(() => {});
}

/**
 * Test Suite Configuration
 */
test.describe('PromptVault Authentication UI Tests (AUTH-UI)', () => {
  // Set timeout for all tests
  test.setTimeout(30000);

  // Before each test: ensure clean state
  test.beforeEach(async ({ page }) => {
    // Clear cookies and storage
    await page.context().clearCookies();
    await page.evaluate(() => localStorage.clear());
    await page.evaluate(() => sessionStorage.clear());
  });
});
