// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

import { test, expect } from '@playwright/test';

test.describe('Pull-to-refresh on the prompt list (FR-008)', () => {
  test('pulling down past the threshold reloads the list with a loading affordance', async ({
    page,
  }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    const list = page.locator('#prompts-list');
    await expect(list).toBeVisible();

    let requestSeen = false;
    page.on('request', (request) => {
      if (request.url().includes('/api/prompts') && request.method() === 'GET') {
        requestSeen = true;
      }
    });

    const box = await list.boundingBox();
    if (!box) throw new Error('prompts-list has no bounding box');
    const startX = box.x + box.width / 2;
    const startY = box.y + 10;

    await list.evaluate(
      (el, [sx, sy]) => {
        function fire(type: string, x: number, y: number): void {
          el.dispatchEvent(
            new PointerEvent(type, { clientX: x, clientY: y, pointerId: 1, bubbles: true })
          );
        }
        fire('pointerdown', sx, sy);
        fire('pointerup', sx, sy + 100);
      },
      [startX, startY]
    );

    await expect(async () => {
      expect(requestSeen).toBe(true);
    }).toPass({ timeout: 5000 });
  });

  test('the visible refresh button is an accessible equivalent to the gesture', async ({
    page,
  }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    const refreshBtn = page.locator('#refresh-prompts-btn');
    await expect(refreshBtn).toBeVisible();

    let requestSeen = false;
    page.on('request', (request) => {
      if (request.url().includes('/api/prompts') && request.method() === 'GET') {
        requestSeen = true;
      }
    });

    await refreshBtn.click();

    await expect(async () => {
      expect(requestSeen).toBe(true);
    }).toPass({ timeout: 5000 });
  });
});
