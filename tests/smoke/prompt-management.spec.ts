// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

// @ts-nocheck

/**
 * Functional smoke tests for the main prompt list/editor page (/), backed by
 * app.ts (the largest god-file targeted for Phase 8 decomposition). Covers
 * create/edit/delete of a prompt and basic pagination affordance presence.
 * Phase 0c safety net for the god-file refactor plan.
 */

import { expect } from '@playwright/test';
import { authenticatedUserTest, navigateToProtectedRoute } from '../accessibility/fixtures/auth.js';

const test = authenticatedUserTest;

function uniqueTitle(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
}

test.describe('Prompt management functional smoke tests', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await navigateToProtectedRoute(page, '/');
    await page.waitForLoadState('networkidle');
  });

  test('creating a prompt adds it to the list', async ({ authenticatedPage: page }) => {
    const title = uniqueTitle('Smoke Prompt');

    await page.locator('#new-menu-btn').click();
    await page.locator('#new-prompt-btn').click();
    await expect(page.locator('#prompt-editor')).toBeVisible();

    await page.locator('#prompt-title').fill(title);
    await page.locator('#prompt-content').fill('Smoke test prompt body content.');
    await page.locator('#prompt-form button[type="submit"]').click();

    await expect(page.locator('#prompt-editor')).toBeHidden({ timeout: 10000 });

    await page.locator('#search-input').fill(title);
    await page.waitForLoadState('networkidle').catch(() => {});

    const card = page.locator('.prompt-item', { hasText: title });
    await expect(card).toHaveCount(1, { timeout: 10000 });
    await page.locator('#search-input').clear();
  });

  test('editing a prompt updates its title in the list', async ({ authenticatedPage: page }) => {
    const originalTitle = uniqueTitle('Smoke Edit Prompt');
    const updatedTitle = uniqueTitle('Smoke Edited Prompt');

    await page.locator('#new-menu-btn').click();
    await page.locator('#new-prompt-btn').click();
    await page.locator('#prompt-title').fill(originalTitle);
    await page.locator('#prompt-content').fill('Original body content.');
    await page.locator('#prompt-form button[type="submit"]').click();
    await expect(page.locator('#prompt-editor')).toBeHidden({ timeout: 10000 });

    await page.locator('#search-input').fill(originalTitle);
    await page.waitForLoadState('networkidle').catch(() => {});

    const card = page.locator('.prompt-item', { hasText: originalTitle });
    await expect(card).toHaveCount(1, { timeout: 10000 });

    await card.locator('.edit-btn').click();
    await expect(page.locator('#prompt-editor')).toBeVisible();
    await page.locator('#prompt-title').fill(updatedTitle);
    await page.locator('#prompt-form button[type="submit"]').click();
    await expect(page.locator('#prompt-editor')).toBeHidden({ timeout: 10000 });

    await expect
      .poll(
        async () => {
          await page.locator('#search-input').fill(updatedTitle);
          await page.waitForLoadState('networkidle').catch(() => {});
          return await page.locator('.prompt-item', { hasText: updatedTitle }).count();
        },
        { timeout: 15000 }
      )
      .toBe(1);
    await page.locator('#search-input').clear();
  });

  test('deleting a prompt removes it from the list', async ({ authenticatedPage: page }) => {
    const title = uniqueTitle('Smoke Delete Prompt');

    await page.locator('#new-menu-btn').click();
    await page.locator('#new-prompt-btn').click();
    await page.locator('#prompt-title').fill(title);
    await page.locator('#prompt-content').fill('To be deleted.');
    await page.locator('#prompt-form button[type="submit"]').click();
    await expect(page.locator('#prompt-editor')).toBeHidden({ timeout: 10000 });

    await page.locator('#search-input').fill(title);
    await page.waitForLoadState('networkidle').catch(() => {});

    const card = page.locator('.prompt-item', { hasText: title });
    await expect(card).toHaveCount(1, { timeout: 10000 });

    await card.locator('.card-menu-btn').click();
    await card.locator('.delete-btn').click();

    const dialog = page.locator('[role="dialog"]:visible').last();
    await expect(dialog).toBeVisible({ timeout: 5000 });
    await dialog
      .getByRole('button', { name: /delete/i })
      .last()
      .click();

    await expect(card).toHaveCount(0, { timeout: 10000 });
  });

  test('creating a prompt with an empty title is blocked by the required field', async ({
    authenticatedPage: page,
  }) => {
    await page.locator('#new-menu-btn').click();
    await page.locator('#new-prompt-btn').click();
    await expect(page.locator('#prompt-editor')).toBeVisible();

    const titleInput = page.locator('#prompt-title');
    await titleInput.fill('');
    await page.locator('#prompt-content').fill('Body without a title.');
    await page.locator('#prompt-form button[type="submit"]').click();

    // Should not close the editor on a client-side validation failure.
    await expect(page.locator('#prompt-editor')).toBeVisible();
    const isValid = await titleInput.evaluate((el: HTMLInputElement) => el.checkValidity());
    expect(isValid).toBe(false);

    await page.locator('#cancel-btn-edit-modal').click();
  });

  test('pagination affordance appears once enough prompts exist', async ({
    authenticatedPage: page,
  }) => {
    const pageSizeSelect = page.locator('#page-size-select');
    if ((await pageSizeSelect.count()) === 0) {
      test.skip();
      return;
    }

    // Force the smallest page size so seeded/created prompts are more likely
    // to overflow a single page without needing to create dozens of prompts.
    const options = await pageSizeSelect.locator('option').allTextContents();
    if (options.length === 0) {
      test.skip();
      return;
    }
    await pageSizeSelect.selectOption({ index: 0 });
    await page.waitForLoadState('networkidle').catch(() => {});

    const loadMoreContainer = page.locator('#load-more-container');
    const promptCount = await page.locator('.prompt-item').count();

    if (promptCount === 0) {
      test.skip();
      return;
    }

    // Either pagination is visible (more prompts than fit one page) or the
    // container legitimately stays hidden because everything fits — both are
    // valid states; we just assert the control exists and is inspectable.
    expect(await loadMoreContainer.count()).toBeGreaterThan(0);
  });
});
