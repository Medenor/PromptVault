// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

import { test, expect } from '@playwright/test';

test.describe('PWA installability (FR-013, SC-006)', () => {
  test('manifest link is present and resolves with the required fields', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    const manifestHref = await page.locator('link[rel="manifest"]').getAttribute('href');
    expect(manifestHref).toBeTruthy();

    const response = await page.request.get(manifestHref!);
    expect(response.ok()).toBe(true);

    const manifest = await response.json();
    expect(manifest.name).toBeTruthy();
    expect(manifest.start_url).toBeTruthy();
    expect(manifest.display).toBe('standalone');
    expect(Array.isArray(manifest.icons)).toBe(true);
    expect(manifest.icons.some((icon: { sizes: string }) => icon.sizes === '512x512')).toBe(true);
  });

  test('theme-color meta tag is present', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    const themeColor = await page.locator('meta[name="theme-color"]').getAttribute('content');
    expect(themeColor).toBeTruthy();
  });

  test('icon assets referenced by the manifest are reachable', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    const manifestHref = await page.locator('link[rel="manifest"]').getAttribute('href');
    const manifest = await (await page.request.get(manifestHref!)).json();

    for (const icon of manifest.icons) {
      const response = await page.request.get(icon.src);
      expect(response.ok(), `icon ${icon.src} should be reachable`).toBe(true);
    }
  });
});
