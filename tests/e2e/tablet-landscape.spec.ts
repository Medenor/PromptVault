// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

import { test, expect } from '@playwright/test';

/**
 * Tablet-landscape layout check (FR-021): at or above 768px width, the
 * existing desktop-style layout is used instead of the mobile patterns,
 * regardless of touch capability. Below 768px (e.g. tablet portrait),
 * the mobile layout applies.
 */
test.describe('Tablet layout adapts by width, not device type (FR-021)', () => {
  test('landscape tablet (1024x768) shows the desktop sidebar and hides mobile nav controls', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1024, height: 768 });
    await page.goto('/', { waitUntil: 'networkidle' });

    await expect(page.locator('aside').first()).toBeVisible();
    await expect(page.locator('#mobile-menu-toggle')).toBeHidden();
    await expect(page.locator('#new-prompt-fab')).toBeHidden();
    await expect(page.locator('#mobile-search-toggle')).toBeHidden();
  });

  test('exactly 768px width (the FR-021 boundary) shows the desktop layout', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/', { waitUntil: 'networkidle' });

    await expect(page.locator('aside').first()).toBeVisible();
    await expect(page.locator('#mobile-menu-toggle')).toBeHidden();
    await expect(page.locator('#new-prompt-fab')).toBeHidden();
  });

  test('narrower tablet portrait (767px) uses the mobile layout', async ({ page }) => {
    await page.setViewportSize({ width: 767, height: 1024 });
    await page.goto('/', { waitUntil: 'networkidle' });

    await expect(page.locator('#mobile-menu-toggle')).toBeVisible();
    await expect(page.locator('#new-prompt-fab')).toBeVisible();

    const desktopSidebar = page.locator('aside').first();
    await expect(desktopSidebar).toBeHidden();
  });

  test('no horizontal scroll at the tablet-landscape breakpoint', async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 768 });
    await page.goto('/', { waitUntil: 'networkidle' });

    const hasHorizontalScroll = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });

    expect(hasHorizontalScroll).toBe(false);
  });
});
