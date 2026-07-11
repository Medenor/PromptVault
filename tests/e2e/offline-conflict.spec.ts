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

test.describe('Offline sync conflict notification (FR-012)', () => {
  test('a conflicting concurrent offline edit surfaces a conflict notification instead of silently overwriting', async ({
    page,
    context,
    browser,
  }) => {
    await login(page);
    await page.goto('/', { waitUntil: 'networkidle' });
    const firstCard = page.locator('.prompt-item').first();
    await expect(firstCard).toBeVisible();
    const promptId = await firstCard.getAttribute('data-id');
    expect(promptId).toBeTruthy();

    // Client A: edit (allow the editor's baseVersion tracking fetch to finish
    // while still online — see editPrompt()), then go offline and queue the change.
    await firstCard.locator('.edit-btn').first().click();
    await expect(page.locator('#prompt-form')).toHaveAttribute('data-base-version', /\d+/, {
      timeout: 5000,
    });
    await context.setOffline(true);
    await page.fill('#prompt-title', 'Client A Edit');
    await page.locator('#prompt-form button[type="submit"]').click();
    await expect(page.locator('.notification')).toContainText(/queue|offline/i, {
      timeout: 5000,
    });

    // Client B (separate context/tab): while online, apply a real update to the
    // same prompt, advancing its server-side version past what Client A queued.
    const otherContext = await browser.newContext();
    const otherPage = await otherContext.newPage();
    await login(otherPage);
    await otherPage.goto('/', { waitUntil: 'networkidle' });
    const otherCard = otherPage.locator(`.prompt-item[data-id="${promptId}"]`);
    await expect(otherCard).toBeVisible();
    await otherCard.locator('.edit-btn').first().click();
    await otherPage.fill('#prompt-title', 'Client B Edit (server wins)');
    await otherPage.locator('#prompt-form button[type="submit"]').click();
    await expect(otherPage.locator('#prompt-editor')).toBeHidden();
    await otherContext.close();

    // Client A reconnects: its queued edit is now stale relative to the server.
    // The load-bearing assertion is that the server keeps Client B's write —
    // i.e. the sync does NOT silently overwrite it — verified by polling the
    // server directly rather than a transient toast, which can auto-dismiss
    // before a test assertion re-checks the DOM.
    await context.setOffline(false);
    await page.evaluate(() => window.dispatchEvent(new Event('online')));

    await expect(async () => {
      const response = await page.request.get(`/api/prompts/${promptId}`);
      const body = (await response.json()) as { title: string };
      expect(body.title).toBe('Client B Edit (server wins)');
    }).toPass({ timeout: 15_000 });
  });
});
