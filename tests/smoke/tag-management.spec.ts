// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

// @ts-nocheck

/**
 * Functional smoke tests for the tag management page (/manage-tags), backed
 * by manage-tags.ts. Unlike tests/accessibility/tag-management.spec.ts (which
 * only checks WCAG structure), these tests exercise the actual create/edit/
 * delete business logic. Safety net for Phase 8 of the god-file refactor —
 * see docs/plans "PromptVault Refactor Plan" Phase 0c.
 */

import { expect } from '@playwright/test';
import {
  authenticatedAdminTest,
  navigateToProtectedRoute,
} from '../accessibility/fixtures/auth.js';

const test = authenticatedAdminTest;

function uniqueName(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
}

test.describe('Tag management functional smoke tests', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await navigateToProtectedRoute(page, '/manage-tags');
    await page.waitForLoadState('networkidle');
  });

  test('creating a tag adds it to the table', async ({ authenticatedPage: page }) => {
    const tagName = uniqueName('smoke-tag');

    await page.locator('#tag-create-name').fill(tagName);
    await page.locator('#tag-create-form button[type="submit"]').click();

    const row = page.locator('tbody tr', {
      has: page.locator(`input[data-field="name"][value="${tagName}"]`),
    });
    await expect(row).toHaveCount(1, { timeout: 10000 });
  });

  test('editing a tag name persists after reload', async ({ authenticatedPage: page }) => {
    const originalName = uniqueName('smoke-edit');
    const updatedName = uniqueName('smoke-edited');

    await page.locator('#tag-create-name').fill(originalName);
    await page.locator('#tag-create-form button[type="submit"]').click();

    const nameInput = page.locator(`input[data-field="name"][value="${originalName}"]`);
    await expect(nameInput).toHaveCount(1, { timeout: 10000 });

    await nameInput.fill(updatedName);

    const row = nameInput.locator('xpath=ancestor::tr[1]');
    await row.locator('[data-action="save"]').click();
    await page.waitForLoadState('networkidle').catch(() => {});
    await navigateToProtectedRoute(page, '/manage-tags');
    await page.waitForLoadState('networkidle');

    await expect(page.locator(`input[data-field="name"][value="${updatedName}"]`)).toHaveCount(1, {
      timeout: 10000,
    });
  });

  test('deleting a tag removes it from the table', async ({ authenticatedPage: page }) => {
    const tagName = uniqueName('smoke-delete');

    await page.locator('#tag-create-name').fill(tagName);
    await page.locator('#tag-create-form button[type="submit"]').click();

    const row = page.locator('tbody tr', {
      has: page.locator(`input[data-field="name"][value="${tagName}"]`),
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

  test('creating a tag with an empty name is blocked by the required field', async ({
    authenticatedPage: page,
  }) => {
    const nameInput = page.locator('#tag-create-name');
    await nameInput.fill('');
    await page.locator('#tag-create-form button[type="submit"]').click();

    // The name input has native `required`; the browser blocks submission
    // client-side rather than round-tripping to the server for a JS error.
    const isValid = await nameInput.evaluate((el: HTMLInputElement) => el.checkValidity());
    expect(isValid).toBe(false);
  });

  test('search filters the tag list to matching names', async ({ authenticatedPage: page }) => {
    const tagName = uniqueName('smoke-search-unique');

    await page.locator('#tag-create-name').fill(tagName);
    await page.locator('#tag-create-form button[type="submit"]').click();
    await expect(page.locator(`input[data-field="name"][value="${tagName}"]`)).toHaveCount(1, {
      timeout: 10000,
    });

    const searchInput = page.locator('#tag-search');
    await searchInput.fill(tagName);
    await page.waitForLoadState('networkidle').catch(() => {});

    const visibleRows = page.locator('tbody tr');
    const count = await visibleRows.count();
    expect(count).toBeGreaterThan(0);
    await expect(page.locator(`input[data-field="name"][value="${tagName}"]`)).toBeVisible();

    await searchInput.clear();
  });
});
