// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

import { test, expect } from '@playwright/test';

test.describe('Keyboard-safe prompt editor input (FR-005)', () => {
  test('viewport meta tag opts into interactive-widget=resizes-content', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    const content = await page.locator('meta[name="viewport"]').getAttribute('content');
    expect(content).toContain('interactive-widget=resizes-content');
  });

  test('focused prompt title field stays within the viewport bounds', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    const firstCard = page.locator('.prompt-item').first();
    await expect(firstCard).toBeVisible();
    await firstCard.locator('.edit-btn').first().click();

    const titleField = page.locator('#prompt-title');
    await expect(titleField).toBeVisible();
    await titleField.focus();

    // Allow the scrollIntoView fallback's delay to elapse.
    await page.waitForTimeout(400);

    const box = await titleField.boundingBox();
    const viewport = page.viewportSize();
    expect(box).not.toBeNull();
    expect(viewport).not.toBeNull();
    expect(box!.y).toBeGreaterThanOrEqual(0);
    expect(box!.y + box!.height).toBeLessThanOrEqual(viewport!.height);
  });

  test('focused prompt content field stays within the viewport bounds', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    const firstCard = page.locator('.prompt-item').first();
    await expect(firstCard).toBeVisible();
    await firstCard.locator('.edit-btn').first().click();

    const contentField = page.locator('#prompt-content');
    await expect(contentField).toBeVisible();
    await contentField.focus();

    await page.waitForTimeout(400);

    const box = await contentField.boundingBox();
    const viewport = page.viewportSize();
    expect(box).not.toBeNull();
    expect(viewport).not.toBeNull();
    expect(box!.y).toBeGreaterThanOrEqual(0);
    expect(box!.y + box!.height).toBeLessThanOrEqual(viewport!.height + 5);
  });
});
