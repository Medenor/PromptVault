// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

import { test, expect } from '@playwright/test';

test.describe('Accessible equivalents for gesture-driven actions (FR-020)', () => {
  test('the prompt card has Edit visible and Delete reachable from the More menu without swiping', async ({
    page,
  }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    const firstCard = page.locator('.prompt-item').first();
    await expect(firstCard).toBeVisible();

    const editBtn = firstCard.locator('.edit-btn').first();
    const deleteBtn = firstCard.locator('.delete-btn').first();
    await expect(editBtn).toBeVisible();
    await firstCard.locator('.card-menu-btn').click();
    await expect(deleteBtn).toBeVisible();

    // Both must be real, keyboard-focusable buttons (not gesture-only divs).
    expect(await editBtn.evaluate((el) => el.tagName)).toBe('BUTTON');
    expect(await deleteBtn.evaluate((el) => el.tagName)).toBe('BUTTON');
  });

  test('the FAB and refresh button are keyboard-focusable with accessible names', async ({
    page,
  }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    const fab = page.locator('#new-prompt-fab');
    await expect(fab).toBeVisible();
    expect(await fab.getAttribute('aria-label')).toBeTruthy();

    const refreshBtn = page.locator('#refresh-prompts-btn');
    await expect(refreshBtn).toBeVisible();
    expect(await refreshBtn.getAttribute('aria-label')).toBeTruthy();
  });

  test('Edit button opens the editor without performing a swipe', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    const firstCard = page.locator('.prompt-item').first();
    await firstCard.locator('.edit-btn').first().click();
    await expect(page.locator('#prompt-editor')).toBeVisible();
  });
});
