// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

// @ts-nocheck

/**
 * Functional smoke tests for the category management page
 * (/manage-categories), backed by manage-categories.ts. Complements
 * tests/accessibility/category-management.spec.ts (structure-only a11y
 * checks) with actual create/edit/delete behavior. Phase 0c safety net for
 * the god-file refactor plan.
 */

import { expect } from '@playwright/test';
import { authenticatedAdminTest, navigateToProtectedRoute } from '../accessibility/fixtures/auth.js';

const test = authenticatedAdminTest;

function uniqueName(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
}

test.describe('Category management functional smoke tests', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await navigateToProtectedRoute(page, '/manage-categories');
    await page.waitForLoadState('networkidle');
  });

  test('creating a category adds it to the table', async ({ authenticatedPage: page }) => {
    const categoryName = uniqueName('smoke-category');

    await page.locator('#category-create-name').fill(categoryName);
    await page.locator('#category-create-form button[type="submit"]').click();

    const row = page.locator('tbody tr', {
      has: page.locator(`input[data-field="name"][value="${categoryName}"]`),
    });
    await expect(row).toHaveCount(1, { timeout: 10000 });
  });

  test('editing a category name persists after reload', async ({ authenticatedPage: page }) => {
    const originalName = uniqueName('smoke-cat-edit');
    const updatedName = uniqueName('smoke-cat-edited');

    await page.locator('#category-create-name').fill(originalName);
    await page.locator('#category-create-form button[type="submit"]').click();

    const nameInput = page.locator(`input[data-field="name"][value="${originalName}"]`);
    await expect(nameInput).toHaveCount(1, { timeout: 10000 });

    await nameInput.fill(updatedName);

    const row = nameInput.locator('xpath=ancestor::tr[1]');
    await row.locator('[data-action="save"]').click();
    await page.waitForLoadState('networkidle').catch(() => {});
    await navigateToProtectedRoute(page, '/manage-categories');
    await page.waitForLoadState('networkidle');

    await expect(
      page.locator(`input[data-field="name"][value="${updatedName}"]`)
    ).toHaveCount(1, { timeout: 10000 });
  });

  test('deleting a category removes it from the table', async ({ authenticatedPage: page }) => {
    const categoryName = uniqueName('smoke-cat-delete');

    await page.locator('#category-create-name').fill(categoryName);
    await page.locator('#category-create-form button[type="submit"]').click();

    const row = page.locator('tbody tr', {
      has: page.locator(`input[data-field="name"][value="${categoryName}"]`),
    });
    await expect(row).toHaveCount(1, { timeout: 10000 });

    const deleteBtn = row
      .locator('button[aria-label*="delete" i], button:has-text("Delete")')
      .first();
    await deleteBtn.click();

    const dialog = page.locator('[role="dialog"]:visible').last();
    const confirmBtn = dialog.getByRole('button', { name: /delete|confirm/i }).last();
    if (await confirmBtn.count()) {
      await confirmBtn.click();
    }

    await expect(row).toHaveCount(0, { timeout: 10000 });
  });

  test('creating a category with an empty name is blocked by the required field', async ({
    authenticatedPage: page,
  }) => {
    const nameInput = page.locator('#category-create-name');
    await nameInput.fill('');
    await page.locator('#category-create-form button[type="submit"]').click();

    const isValid = await nameInput.evaluate((el: HTMLInputElement) => el.checkValidity());
    expect(isValid).toBe(false);
  });
});
