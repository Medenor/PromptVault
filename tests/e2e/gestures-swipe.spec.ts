// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

import { test, expect, type Locator, type Page } from '@playwright/test';

/**
 * Simulates a horizontal swipe on a card via synthetic PointerEvents, matching
 * the Vitest unit tests for gestures.ts (Playwright's mouse API does not
 * dispatch PointerEvents in all browser engines the way real touch does).
 */
async function swipe(page: Page, card: Locator, deltaX: number): Promise<void> {
  const box = await card.boundingBox();
  if (!box) throw new Error('card has no bounding box');
  const startX = box.x + box.width / 2;
  const startY = box.y + 20;

  await card.evaluate(
    (el, [sx, sy, dx]) => {
      function fire(type: string, x: number, y: number): void {
        el.dispatchEvent(
          new PointerEvent(type, { clientX: x, clientY: y, pointerId: 1, bubbles: true })
        );
      }
      fire('pointerdown', sx, sy);
      fire('pointermove', sx + dx, sy);
      fire('pointerup', sx + dx, sy);
    },
    [startX, startY, deltaX]
  );
}

test.describe('Swipe gestures on prompt cards (FR-007)', () => {
  test('swipe-left reveals delete action requiring confirmation', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    const firstCard = page.locator('.prompt-item').first();
    await expect(firstCard).toBeVisible();

    await swipe(page, firstCard, -100);

    const confirmModal = page.locator('[role="dialog"]:visible', { hasText: /delete/i });
    await expect(confirmModal).toBeVisible({ timeout: 5000 });

    // Cancel to avoid mutating test data.
    await confirmModal.getByRole('button', { name: /cancel/i }).click();
  });

  test('swipe-right opens the prompt editor', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    const firstCard = page.locator('.prompt-item').first();
    await expect(firstCard).toBeVisible();

    await swipe(page, firstCard, 100);

    await expect(page.locator('#prompt-editor')).toBeVisible({ timeout: 5000 });
  });
});

test.describe('Version-history swipeable carousel on mobile (FR-018)', () => {
  test('prev/next buttons page through versions one at a time', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    await page.locator('.card-menu-btn').first().click();
    await page.locator('.history-btn').first().click();

    const nav = page.locator('#version-carousel-nav');
    await expect(nav).toBeVisible();
    await expect(page.locator('#version-carousel-position')).toContainText('1 / ', {
      timeout: 5000,
    });

    await page.locator('#version-carousel-next').click();
    await expect(page.locator('#version-carousel-position')).toContainText('2 / ');
    await expect(page.locator('#version-carousel-prev')).toBeEnabled();
  });

  test('swiping left on the version list pages to the next version', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    await page.locator('.card-menu-btn').first().click();
    await page.locator('.history-btn').first().click();

    const versionList = page.locator('#version-list');
    await expect(versionList).toBeVisible();
    await swipe(page, versionList, -100);

    await expect(page.locator('#version-carousel-position')).toContainText('2 / ');
  });
});
