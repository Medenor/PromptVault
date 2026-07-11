// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

import { test, expect } from '@playwright/test';

test.describe('Modal layout: full-screen on mobile, centered on desktop (FR-003)', () => {
  test('version history modal is full-screen on mobile', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    const firstCard = page.locator('.prompt-item').first();
    await expect(firstCard).toBeVisible();
    await firstCard.locator('.history-btn').first().click();

    const modal = page.locator('#version-history-modal');
    await expect(modal).toBeVisible();

    const panel = modal.locator('> div').first();
    const panelBox = await panel.boundingBox();
    const viewport = page.viewportSize();
    expect(panelBox).not.toBeNull();
    expect(viewport).not.toBeNull();
    expect(panelBox!.width).toBeCloseTo(viewport!.width, 0);
    expect(panelBox!.height).toBeCloseTo(viewport!.height, 0);
  });

  test('version history modal is a centered dialog on desktop', async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const page = await context.newPage();
    await page.goto('/', { waitUntil: 'networkidle' });

    const firstCard = page.locator('.prompt-item').first();
    await expect(firstCard).toBeVisible();
    await firstCard.locator('.history-btn').first().click();

    const modal = page.locator('#version-history-modal');
    await expect(modal).toBeVisible();

    const panel = modal.locator('> div').first();
    const panelBox = await panel.boundingBox();
    expect(panelBox).not.toBeNull();
    // Centered dialog should not span the full 1280px viewport width.
    expect(panelBox!.width).toBeLessThan(1000);

    await context.close();
  });
});
