// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

import { test, expect } from '@playwright/test';

const MIN_TOUCH_TARGET = 44;

test.describe('Mobile touch target sizing (SC-002)', () => {
  test('header hamburger and search triggers are >= 44x44px', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    for (const selector of ['#mobile-menu-toggle', '#mobile-search-toggle']) {
      const box = await page.locator(selector).boundingBox();
      expect(box, `${selector} should have a bounding box`).not.toBeNull();
      expect(box!.width).toBeGreaterThanOrEqual(MIN_TOUCH_TARGET);
      expect(box!.height).toBeGreaterThanOrEqual(MIN_TOUCH_TARGET);
    }
  });

  test('drawer close button is >= 44x44px', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    await page.locator('#mobile-menu-toggle').click();

    const box = await page.locator('#sidebar-close').boundingBox();
    expect(box).not.toBeNull();
    expect(box!.width).toBeGreaterThanOrEqual(MIN_TOUCH_TARGET);
    expect(box!.height).toBeGreaterThanOrEqual(MIN_TOUCH_TARGET);
  });

  test('drawer nav action buttons meet the minimum height', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    await page.locator('#mobile-menu-toggle').click();

    const drawer = page.locator('#mobile-sidebar');
    for (const label of ['New Prompt', 'Import/Export', 'Backup']) {
      const box = await drawer.getByRole('button', { name: label }).boundingBox();
      expect(box, `${label} should have a bounding box`).not.toBeNull();
      expect(box!.height).toBeGreaterThanOrEqual(MIN_TOUCH_TARGET);
    }
  });

  test('prompt card action buttons meet the minimum height', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    const firstCard = page.locator('.prompt-item').first();
    await expect(firstCard).toBeVisible();

    for (const selector of ['.history-btn', '.copy-btn', '.edit-btn', '.delete-btn']) {
      const box = await firstCard.locator(selector).first().boundingBox();
      expect(box, `${selector} should have a bounding box`).not.toBeNull();
      expect(box!.height).toBeGreaterThanOrEqual(MIN_TOUCH_TARGET);
    }
  });

  test('favorite button is >= 44x44px', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    const firstCard = page.locator('.prompt-item').first();
    await expect(firstCard).toBeVisible();

    const box = await firstCard.locator('.favorite-btn').boundingBox();
    expect(box).not.toBeNull();
    expect(box!.width).toBeGreaterThanOrEqual(MIN_TOUCH_TARGET);
    expect(box!.height).toBeGreaterThanOrEqual(MIN_TOUCH_TARGET);
  });
});
