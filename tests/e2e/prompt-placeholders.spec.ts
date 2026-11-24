// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

import { test, expect, type Page, type Locator } from '@playwright/test';

const TEST_ADMIN_USERNAME =
  process.env.TEST_ADMIN_USERNAME ?? process.env.TEST_ADMIN_EMAIL ?? 'test_admin_ui@example.com';
const TEST_ADMIN_PASSWORD = process.env.TEST_ADMIN_PASSWORD ?? 'TestAdmin@Pass123456';

/** Logs in via the real login form (the prompt list requires an authenticated user). */
async function login(page: Page): Promise<void> {
  await page.goto('/auth/login', { waitUntil: 'networkidle' });
  await page.locator('#username-or-email').fill(TEST_ADMIN_USERNAME);
  await page.locator('#password').fill(TEST_ADMIN_PASSWORD);
  await Promise.all([
    page.waitForResponse(
      (response) =>
        response.url().includes('/api/auth/login') && response.request().method() === 'POST'
    ),
    page.locator('button[type="submit"]').first().click(),
  ]);
}

async function openNewPromptForm(page: Page): Promise<void> {
  const desktopMenu = page.locator('#new-menu-btn');
  if (await desktopMenu.isVisible()) {
    await desktopMenu.click();
    await page.locator('#new-prompt-btn').click();
    return;
  }
  await page.locator('#mobile-menu-toggle').click();
  await page.locator('#new-prompt-btn-mobile').click();
  await expect(page.locator('#prompt-editor')).toBeVisible();
}

async function createPrompt(page: Page, title: string, content: string): Promise<void> {
  await page.goto('/', { waitUntil: 'networkidle' });
  await openNewPromptForm(page);
  await page.locator('#prompt-title').fill(title);
  await page.locator('#prompt-content').fill(content);
  await page.locator('#prompt-form button[type="submit"]').click();
  await expect(page.locator('#prompt-editor')).toBeHidden();
}

/** Finds a prompt card by title, searching for it since the list is paginated
 * and new prompts are not guaranteed to appear on the first page. */
async function findPromptCard(page: Page, title: string): Promise<Locator> {
  const desktopSearch = page.locator('#search-input');
  const searchInput = (await desktopSearch.isVisible())
    ? desktopSearch
    : page.locator('#search-input-mobile');
  await searchInput.fill(title);
  await page.waitForTimeout(500);
  const card = page.locator('.prompt-item', { hasText: title }).first();
  await expect(card).toBeVisible();
  return card;
}

async function readClipboard(page: Page): Promise<string> {
  return page.evaluate(() => navigator.clipboard.readText());
}

// Clipboard read/write permission grants (and reliable navigator.clipboard.readText()
// in a headless automation context) are only supported by Playwright's Chromium-based
// CDP driver — WebKit here (used by the mobile/iPhone 14/Pixel 7 e2e projects) cannot
// grant clipboard-write, so these clipboard-content assertions run on chromium only.
test.describe('Dynamic prompt placeholders', () => {
  test.skip(({ browserName }) => browserName !== 'chromium', 'Requires Chromium clipboard grants');

  test.beforeEach(async ({ context, page }) => {
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
    await login(page);
  });

  test('filling in all placeholder fields produces fully substituted clipboard text', async ({
    page,
  }) => {
    const title = `Placeholder Test ${Date.now()}`;
    const content =
      'Your task is to create a [DURATION] [TYPE OF PRESENTATION] titled "[INSERT PRESENTATION TITLE]".';
    await createPrompt(page, title, content);

    const card = await findPromptCard(page, title);
    await card.locator('.copy-btn').click();

    const modal = page.locator('#placeholder-fill-modal');
    await expect(modal).toBeVisible();
    const labels = modal.locator('label');
    await expect(labels).toHaveCount(3);
    await expect(labels.nth(0)).toHaveText('DURATION');
    await expect(labels.nth(1)).toHaveText('TYPE OF PRESENTATION');
    await expect(labels.nth(2)).toHaveText('INSERT PRESENTATION TITLE');

    await modal.locator('input').nth(0).fill('1 hour');
    await modal.locator('input').nth(1).fill('Sales');
    await modal.locator('input').nth(2).fill('How to build an app');
    await modal.getByRole('button', { name: 'Copy' }).click();

    await expect(modal).toBeHidden();
    const clipboardText = await readClipboard(page);
    expect(clipboardText).toBe(
      'Your task is to create a 1 hour Sales titled "How to build an app".'
    );
  });

  test('prompt with no placeholders copies immediately with no modal', async ({ page }) => {
    const title = `No Placeholder Test ${Date.now()}`;
    const content = 'This prompt has no dynamic tokens at all.';
    await createPrompt(page, title, content);

    const card = await findPromptCard(page, title);
    await card.locator('.copy-btn').click();

    await expect(page.locator('#placeholder-fill-modal')).toHaveCount(0);
    const clipboardText = await readClipboard(page);
    expect(clipboardText).toBe(content);
  });

  test('leaving all fields blank copies the raw unchanged content', async ({ page }) => {
    const title = `Blank Fields Test ${Date.now()}`;
    const content = 'Say hello to [NAME] from {CITY}.';
    await createPrompt(page, title, content);

    const card = await findPromptCard(page, title);
    await card.locator('.copy-btn').click();

    const modal = page.locator('#placeholder-fill-modal');
    await expect(modal).toBeVisible();
    await modal.getByRole('button', { name: 'Copy' }).click();

    await expect(modal).toBeHidden();
    const clipboardText = await readClipboard(page);
    expect(clipboardText).toBe(content);
  });

  test('leaving one field blank among several keeps only that token literal', async ({ page }) => {
    const title = `Partial Fields Test ${Date.now()}`;
    const content = 'Say hello to [NAME] from {CITY}.';
    await createPrompt(page, title, content);

    const card = await findPromptCard(page, title);
    await card.locator('.copy-btn').click();

    const modal = page.locator('#placeholder-fill-modal');
    await expect(modal).toBeVisible();
    await modal.locator('input').nth(0).fill('Alice');
    // Leave the second field (CITY) blank.
    await modal.getByRole('button', { name: 'Copy' }).click();

    await expect(modal).toBeHidden();
    const clipboardText = await readClipboard(page);
    expect(clipboardText).toBe('Say hello to Alice from {CITY}.');
  });

  test('editing a prompt to change its placeholders updates the copy form field set', async ({
    page,
  }) => {
    const title = `Edit Placeholder Test ${Date.now()}`;
    const originalContent = 'Original with [ALPHA] token.';
    await createPrompt(page, title, originalContent);

    const card = await findPromptCard(page, title);
    await card.locator('.edit-btn').click();
    await expect(page.locator('#prompt-editor')).toBeVisible();

    const updatedContent = 'Updated with [BETA] and [GAMMA] tokens.';
    await page.locator('#prompt-content').fill(updatedContent);
    await page.locator('#prompt-form button[type="submit"]').click();
    await expect(page.locator('#prompt-editor')).toBeHidden();

    const updatedCard = await findPromptCard(page, title);
    await updatedCard.locator('.copy-btn').click();

    const modal = page.locator('#placeholder-fill-modal');
    await expect(modal).toBeVisible();
    const labels = modal.locator('label');
    await expect(labels).toHaveCount(2);
    await expect(labels.nth(0)).toHaveText('BETA');
    await expect(labels.nth(1)).toHaveText('GAMMA');
  });

  test('version-history/diff view shows no placeholder form even with placeholder tokens', async ({
    page,
  }) => {
    const title = `Version History Placeholder Test ${Date.now()}`;
    const content = 'Say hello to [NAME].';
    await createPrompt(page, title, content);

    const card = await findPromptCard(page, title);
    await card.locator('.edit-btn').click();
    await expect(page.locator('#prompt-editor')).toBeVisible();
    await page.locator('#prompt-content').fill('Say hello to [OTHER_NAME] now.');
    await page.locator('#prompt-form button[type="submit"]').click();
    await expect(page.locator('#prompt-editor')).toBeHidden();

    const updatedCard = await findPromptCard(page, title);
    await updatedCard.locator('.card-menu-btn').click();
    await updatedCard.locator('.history-btn').click();

    const historyModal = page.locator('#version-history-modal');
    await expect(historyModal).toBeVisible();
    await expect(historyModal.locator('#placeholder-fill-modal')).toHaveCount(0);
    await expect(page.locator('#placeholder-fill-modal')).toHaveCount(0);
  });
});
