// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

import { test, expect } from '@playwright/test';

test.describe('Mobile navigation drawer', () => {
  test('hamburger opens the unified drawer with nav actions and filters', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    const toggle = page.locator('#mobile-menu-toggle');
    await expect(toggle).toBeVisible();
    await toggle.click();

    const drawer = page.locator('#mobile-sidebar');
    await expect(drawer).toBeVisible();
    await expect(drawer.getByRole('button', { name: 'New Prompt' })).toBeVisible();
    await expect(drawer.getByRole('heading', { name: 'Filters' })).toBeVisible();
    expect(await toggle.getAttribute('aria-expanded')).toBe('true');
  });

  test('outside-tap closes the drawer', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    await page.locator('#mobile-menu-toggle').click();

    const drawer = page.locator('#mobile-sidebar');
    await expect(drawer).toBeVisible();
    await expect(drawer).not.toHaveClass(/-translate-x-full/);

    await page.locator('#sidebar-backdrop').click({ position: { x: 300, y: 400 } });

    await expect(drawer).toHaveClass(/-translate-x-full/);
  });

  test('Escape key closes the drawer', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    await page.locator('#mobile-menu-toggle').click();

    const drawer = page.locator('#mobile-sidebar');
    await expect(drawer).toBeVisible();
    await expect(drawer).not.toHaveClass(/-translate-x-full/);

    await page.keyboard.press('Escape');

    await expect(drawer).toHaveClass(/-translate-x-full/);
  });

  test('close button closes the drawer', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    await page.locator('#mobile-menu-toggle').click();

    const drawer = page.locator('#mobile-sidebar');
    await expect(drawer).toBeVisible();
    await expect(drawer).not.toHaveClass(/-translate-x-full/);

    await page.locator('#sidebar-close').click();

    await expect(drawer).toHaveClass(/-translate-x-full/);
  });

  for (const width of [320, 375, 425, 768]) {
    test(`no horizontal scroll on main content at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 800 });
      await page.goto('/', { waitUntil: 'networkidle' });

      const hasHorizontalScroll = await page.evaluate(() => {
        return document.documentElement.scrollWidth > document.documentElement.clientWidth;
      });

      expect(hasHorizontalScroll).toBe(false);
    });
  }
});
