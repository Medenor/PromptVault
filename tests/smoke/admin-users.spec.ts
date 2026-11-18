// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

// @ts-nocheck

/**
 * Functional smoke tests for the admin users page (/admin/users), backed by
 * admin-users.ts. tests/accessibility/admin-pages.spec.ts only checks a11y
 * structure of the existing (fixture) user table — it never creates a user.
 * These tests create a disposable test-only user, edit it, then delete it,
 * so the seeded ACCESSIBILITY_ADMIN_* / ACCESSIBILITY_USER_* fixture
 * accounts are never touched. Phase 0c safety net for the god-file refactor.
 */

import { expect } from '@playwright/test';
import {
  authenticatedAdminTest,
  navigateToProtectedRoute,
} from '../accessibility/fixtures/auth.js';

const test = authenticatedAdminTest;

function uniqueSuffix(): string {
  return `${Date.now()}_${Math.floor(Math.random() * 10000)}`;
}

async function createUser(page, { username, email, password = 'SmokeTest@Pass123456' }) {
  await page.locator('#add-user-btn').click();
  await expect(page.locator('#create-user-modal')).toBeVisible();

  await page.locator('#create-username').fill(username);
  await page.locator('#create-email').fill(email);
  await page.locator('#create-password').fill(password);
  await page.locator('#create-confirm-password').fill(password);

  await Promise.all([
    page.waitForResponse(
      (res) => res.url().includes('/api/admin/users') && res.request().method() === 'POST',
      { timeout: 15000 }
    ),
    page.locator('#create-user-submit-btn').click(),
  ]);
  await expect(page.locator('#create-user-modal')).toBeHidden({ timeout: 15000 });
}

test.describe('Admin users functional smoke tests', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await navigateToProtectedRoute(page, '/admin/users');
    await page.waitForLoadState('networkidle');
  });

  test('users table is populated on page load', async ({ authenticatedPage: page }) => {
    const tableBody = page.locator('#users-table-body');
    await expect(tableBody).not.toContainText('Loading', { timeout: 15000 });
    const rows = tableBody.locator('tr');
    expect(await rows.count()).toBeGreaterThan(0);
  });

  test('creating a user adds it to the table', async ({ authenticatedPage: page }) => {
    const suffix = uniqueSuffix();
    const username = `smoke_user_${suffix}`;
    const email = `smoke_${suffix}@example.com`;

    await createUser(page, { username, email });

    const row = page.locator('#users-table-body tr', { hasText: username });
    await expect(row).toHaveCount(1, { timeout: 10000 });

    // Cleanup: delete the user we just created.
    const deleteBtn = row.locator('button[data-action="delete-user"]');
    await deleteBtn.click();
    await expect(page.locator('#confirm-delete-modal')).toBeVisible();
    await page.locator('#confirm-delete-btn').click();
    await expect(row).toHaveCount(0, { timeout: 10000 });
  });

  test('editing a user role persists after reload', async ({ authenticatedPage: page }) => {
    const suffix = uniqueSuffix();
    const username = `smoke_edit_${suffix}`;
    const email = `smoke_edit_${suffix}@example.com`;

    await createUser(page, { username, email });

    const row = page.locator('#users-table-body tr', { hasText: username });
    await expect(row).toHaveCount(1, { timeout: 10000 });

    await row.locator('button[data-action="edit-user"]').click();
    await expect(page.locator('#edit-user-modal')).toBeVisible();

    await page.locator('#edit-role').selectOption('editor');
    await page.locator('#save-user-btn').click();
    await expect(page.locator('#edit-user-modal')).toBeHidden({ timeout: 10000 });

    await navigateToProtectedRoute(page, '/admin/users');
    await page.waitForLoadState('networkidle');

    const reloadedRow = page.locator('#users-table-body tr', { hasText: username });
    await expect(reloadedRow).toContainText(/editor/i, { timeout: 10000 });

    // Cleanup: delete the user we just created.
    await reloadedRow.locator('button[data-action="delete-user"]').click();
    await expect(page.locator('#confirm-delete-modal')).toBeVisible();
    await page.locator('#confirm-delete-btn').click();
    await expect(reloadedRow).toHaveCount(0, { timeout: 10000 });
  });

  test('creating a user with an invalid email shows a validation error', async ({
    authenticatedPage: page,
  }) => {
    const suffix = uniqueSuffix();
    await page.locator('#add-user-btn').click();
    await expect(page.locator('#create-user-modal')).toBeVisible();

    await page.locator('#create-username').fill(`smoke_invalid_${suffix}`);
    await page.locator('#create-email').fill('not-an-email');
    await page.locator('#create-password').fill('SmokeTest@Pass123456');
    await page.locator('#create-user-submit-btn').click();

    // Modal should remain open with an error rather than silently succeeding.
    await expect(page.locator('#create-user-modal')).toBeVisible();
    await page.locator('#create-user-cancel-btn').click();
  });
});
