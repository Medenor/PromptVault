// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

import { test, expect, type Page } from '@playwright/test';

const TEST_ADMIN_USERNAME = process.env.TEST_ADMIN_USERNAME ?? 'test_admin_ui';
const TEST_ADMIN_PASSWORD = process.env.TEST_ADMIN_PASSWORD ?? 'TestAdmin@Pass123456';

/**
 * Logs in via the real login form. Prompt mutation endpoints require an
 * authenticated user even when AUTH_ENABLED=false only bypasses the login
 * page display, not write authorization — see scripts/init_test_admin.py.
 */
async function login(page: Page): Promise<void> {
  await page.goto('/auth/login', { waitUntil: 'networkidle' });
  await page.locator('#username-or-email').fill(TEST_ADMIN_USERNAME);
  await page.locator('#password').fill(TEST_ADMIN_PASSWORD);
  await Promise.all([
    page.waitForResponse(
      (response) =>
        response.url().includes('/api/auth/login') && response.request().method() === 'POST'
    ),
    page.locator('button[type="submit"]').click(),
  ]);
}

test.describe('Offline edit queue and auto-sync (FR-011)', () => {
  test('an offline edit queues, then auto-syncs within 10s of reconnect', async ({
    page,
    context,
  }) => {
    await login(page);
    await page.goto('/', { waitUntil: 'networkidle' });
    await page.waitForFunction(async () => {
      const reg = await navigator.serviceWorker.getRegistration();
      return !!reg?.active;
    });

    const firstCard = page.locator('.prompt-item').first();
    await expect(firstCard).toBeVisible();
    await firstCard.locator('.edit-btn').first().click();

    await context.setOffline(true);

    const uniqueTitle = `Offline Edit ${Date.now()}`;
    await page.fill('#prompt-title', uniqueTitle);
    await page.locator('#prompt-form button[type="submit"]').click();

    // The app should tell the user the change was queued, not show a generic error.
    await expect(page.locator('.notification')).toContainText(/queue|offline/i, {
      timeout: 5000,
    });

    await context.setOffline(false);
    // Playwright's context.setOffline(false) does not reliably dispatch the
    // DOM `online` event that the app listens on to trigger sync; nudge it
    // directly, matching what a real browser regaining connectivity would fire.
    await page.evaluate(() => window.dispatchEvent(new Event('online')));

    // Sync happens automatically on the `online` event — poll the prompt list
    // for the synced title within the SC-005 10s budget.
    await expect(async () => {
      const response = await page.request.get('/api/prompts');
      const body = (await response.json()) as { prompts: Record<string, { title: string }> };
      const titles = Object.values(body.prompts).map((p) => p.title);
      expect(titles).toContain(uniqueTitle);
    }).toPass({ timeout: 10_000 });
  });
});
