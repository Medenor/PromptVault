// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

import { test, expect, type Page } from '@playwright/test';

/**
 * SC-007: on a mid-tier mobile device, the prompt list view becomes
 * interactive within 3 seconds on a simulated 4G connection.
 *
 * Uses Chromium's CDP Network/Emulation domains to simulate "Regular 4G"
 * (per Chrome DevTools' own throttling presets: ~4Mb/s down, ~3Mb/s up,
 * 20ms latency) plus 4x CPU slowdown to approximate a mid-tier device,
 * since Playwright's WebKit/Firefox drivers expose no CDP equivalent.
 */
const REGULAR_4G = {
  offline: false,
  downloadThroughput: (4 * 1024 * 1024) / 8, // 4 Mb/s
  uploadThroughput: (3 * 1024 * 1024) / 8, // 3 Mb/s
  latency: 20,
};

async function throttleToRegular4G(page: Page): Promise<void> {
  const client = await page.context().newCDPSession(page);
  await client.send('Network.enable');
  await client.send('Network.emulateNetworkConditions', REGULAR_4G);
  await client.send('Emulation.setCPUThrottlingRate', { rate: 4 });
}

test.describe('Mobile performance (SC-007)', () => {
  test.skip(
    ({ browserName }) => browserName !== 'chromium',
    'CDP network/CPU throttling is Chromium-only'
  );
  test.use({ viewport: { width: 390, height: 844 } });

  test('prompt list is interactive within 3s on simulated Regular 4G', async ({ page }) => {
    await throttleToRegular4G(page);

    const start = Date.now();
    await page.goto('/', { waitUntil: 'domcontentloaded' });

    const firstCard = page.locator('.prompt-item').first();
    await expect(firstCard).toBeVisible({ timeout: 3000 });

    // "Interactive" means a real control on the card responds to a click,
    // not just that markup painted.
    const editButton = firstCard.getByRole('button', { name: /edit/i });
    await editButton.click();
    await expect(page.locator('#prompt-editor')).toBeVisible();

    const elapsedMs = Date.now() - start;
    expect(elapsedMs).toBeLessThanOrEqual(3000);
  });
});
