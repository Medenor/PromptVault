// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

/**
 * Mobile-specific ARIA audit (FR-020): drawer, FAB, swipe actions, search overlay.
 * Runs axe-core against each mobile-only surface plus targeted manual checks
 * for attributes axe cannot verify (aria-expanded state changes, focus return).
 */
test.describe('Mobile ARIA audit (FR-020)', () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test('nav drawer has no automatically-detectable a11y violations when open', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    await page.locator('#mobile-menu-toggle').click();
    await expect(page.locator('#mobile-sidebar')).toBeVisible();

    const results = await new AxeBuilder({ page })
      .include('#mobile-sidebar')
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();

    expect(results.violations).toEqual([]);
  });

  test('drawer toggle exposes aria-expanded and aria-controls correctly', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    const toggle = page.locator('#mobile-menu-toggle');

    expect(await toggle.getAttribute('aria-controls')).toBe('mobile-sidebar');
    expect(await toggle.getAttribute('aria-expanded')).toBe('false');

    await toggle.click();
    expect(await toggle.getAttribute('aria-expanded')).toBe('true');

    await page.keyboard.press('Escape');
    expect(await toggle.getAttribute('aria-expanded')).toBe('false');
  });

  test('drawer is a labeled dialog with focus trapped inside while open', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    await page.locator('#mobile-menu-toggle').click();

    const drawer = page.locator('#mobile-sidebar');
    expect(await drawer.getAttribute('role')).toBe('dialog');

    const hasAccessibleName = await drawer.evaluate((el) => {
      return Boolean(
        el.getAttribute('aria-label') ||
        (el.getAttribute('aria-labelledby') &&
          document.getElementById(el.getAttribute('aria-labelledby')!))
      );
    });
    expect(hasAccessibleName).toBe(true);

    // Tab past the last focusable element inside the drawer; focus should wrap, not escape.
    for (let i = 0; i < 15; i++) {
      await page.keyboard.press('Tab');
    }
    const focusStayedInDrawer = await drawer.evaluate((el) => el.contains(document.activeElement));
    expect(focusStayedInDrawer).toBe(true);
  });

  test('search overlay has no automatically-detectable a11y violations when open', async ({
    page,
  }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    await page.locator('#mobile-search-toggle').click();
    await expect(page.locator('#mobile-search-overlay')).toBeVisible();

    const results = await new AxeBuilder({ page })
      .include('#mobile-search-overlay')
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();

    expect(results.violations).toEqual([]);
  });

  test('search overlay moves focus to the search input and returns focus on close', async ({
    page,
  }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    const searchToggle = page.locator('#mobile-search-toggle');
    await searchToggle.click();

    await expect(page.locator('#search-input-overlay')).toBeFocused();

    await page.keyboard.press('Escape');
    await expect(page.locator('#mobile-search-overlay')).toBeHidden();
    await expect(searchToggle).toBeFocused();
  });

  test('floating action button has an accessible name and meets touch-target size', async ({
    page,
  }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    const fab = page.locator('#new-prompt-fab');
    await expect(fab).toBeVisible();

    const accessibleName = await fab.getAttribute('aria-label');
    expect(accessibleName).toBeTruthy();

    const box = await fab.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.width).toBeGreaterThanOrEqual(44);
    expect(box!.height).toBeGreaterThanOrEqual(44);

    const results = await new AxeBuilder({ page }).include('#new-prompt-fab').analyze();
    expect(results.violations).toEqual([]);
  });

  test('swipe-revealed delete confirmation is an accessible, labeled dialog', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    const firstCard = page.locator('.prompt-item').first();
    await expect(firstCard).toBeVisible();

    const box = await firstCard.boundingBox();
    if (!box) throw new Error('card has no bounding box');
    await firstCard.evaluate(
      (el, [sx, sy]) => {
        function fire(type: string, x: number, y: number): void {
          el.dispatchEvent(
            new PointerEvent(type, { clientX: x, clientY: y, pointerId: 1, bubbles: true })
          );
        }
        fire('pointerdown', sx, sy);
        fire('pointermove', sx - 100, sy);
        fire('pointerup', sx - 100, sy);
      },
      [box.x + box.width / 2, box.y + 20]
    );

    const confirmModal = page.getByRole('dialog', { name: /confirm delete/i });
    await expect(confirmModal).toBeVisible({ timeout: 5000 });

    const modalId = await confirmModal.getAttribute('id');
    const results = await new AxeBuilder({ page }).include(`#${modalId}`).analyze();
    expect(results.violations).toEqual([]);

    await confirmModal.getByRole('button', { name: /cancel/i }).click();
  });

  test('full page at mobile viewport has no automatically-detectable a11y violations', async ({
    page,
  }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();

    expect(results.violations).toEqual([]);
  });
});
