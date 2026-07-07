// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

import { test, expect, Page } from '@playwright/test';

test.describe('Modal ARIA Attributes and Dialog Roles', () => {
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage();
  });

  test.afterAll(async () => {
    await page?.close();
  });

  test('1. Admin Users Page - Create User Modal ARIA attributes', async () => {
    // Navigate to login
    await page.goto('http://localhost:8003');

    // Login with admin credentials
    await page.fill('input[name="email"]', 'test_admin_ui@example.com');
    await page.fill('input[name="password"]', 'TestAdmin@Pass123456');
    await page.click('button:has-text("Login")');

    // Wait for navigation to complete
    await page.waitForURL('**/');
    await page.waitForTimeout(500);

    // Navigate to admin users page
    await page.goto('http://localhost:8003/admin/users');
    await page.waitForLoadState('networkidle');

    // Click the add user button (blue button)
    await page.click(
      'button[aria-label*="Create" i], button:has-text("Create"), button:has-text("Add")'
    );

    // Wait for modal to appear
    await page.waitForSelector('[role="dialog"]', { timeout: 5000 });

    // Get the modal element
    const modal = await page.locator('[role="dialog"]').first();

    // Check ARIA attributes
    const ariaModal = await modal.getAttribute('aria-modal');
    const ariaLabelledBy = await modal.getAttribute('aria-labelledby');
    const role = await modal.getAttribute('role');

    console.log('Create User Modal ARIA attributes:');
    console.log(`  aria-modal: ${ariaModal}`);
    console.log(`  aria-labelledby: ${ariaLabelledBy}`);
    console.log(`  role: ${role}`);

    // Verify attributes
    expect(ariaModal).toBe('true');
    expect(ariaLabelledBy).toBeTruthy();
    expect(role).toBe('dialog');

    // Verify the modal title element has matching ID
    if (ariaLabelledBy) {
      const titleElement = await page.locator(`#${ariaLabelledBy}`);
      await expect(titleElement).toBeVisible();
    }

    // Take screenshot
    await page.screenshot({ path: '/tmp/modal-create-user.png', fullPage: true });
    console.log('Screenshot: /tmp/modal-create-user.png');
  });

  test('2. Admin Users Page - Delete Confirmation Modal', async () => {
    // Already on admin users page from previous test
    // Find first user row and click delete button
    const deleteButtons = page.locator('button[aria-label*="Delete" i], button:has-text("Delete")');
    const firstDeleteButton = deleteButtons.first();

    if (await firstDeleteButton.isVisible()) {
      await firstDeleteButton.click();

      // Wait for delete confirmation modal
      await page.waitForSelector('[role="dialog"]', { timeout: 5000 });

      const modal = await page.locator('[role="dialog"]').last();

      const ariaModal = await modal.getAttribute('aria-modal');
      const ariaLabelledBy = await modal.getAttribute('aria-labelledby');
      const role = await modal.getAttribute('role');

      console.log('Delete Confirmation Modal ARIA attributes:');
      console.log(`  aria-modal: ${ariaModal}`);
      console.log(`  aria-labelledby: ${ariaLabelledBy}`);
      console.log(`  role: ${role}`);

      expect(ariaModal).toBe('true');
      expect(ariaLabelledBy).toBeTruthy();
      expect(role).toBe('dialog');

      // Take screenshot
      await page.screenshot({ path: '/tmp/modal-delete-confirmation.png', fullPage: true });
      console.log('Screenshot: /tmp/modal-delete-confirmation.png');

      // Close the modal (press Escape)
      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);
    }
  });

  test('3. Admin Sessions Page Modal ARIA attributes', async () => {
    // Navigate to admin sessions page
    await page.goto('http://localhost:8003/admin/sessions');
    await page.waitForLoadState('networkidle');

    // Look for a session detail button/link
    const sessionButtons = page.locator(
      'button:has-text("Detail"), button:has-text("View"), a:has-text("View")'
    );

    if (await sessionButtons.first().isVisible()) {
      await sessionButtons.first().click();

      // Wait for modal
      await page.waitForSelector('[role="dialog"]', { timeout: 5000 });

      const modal = await page.locator('[role="dialog"]').first();

      const ariaModal = await modal.getAttribute('aria-modal');
      const ariaLabelledBy = await modal.getAttribute('aria-labelledby');
      const role = await modal.getAttribute('role');

      console.log('Session Detail Modal ARIA attributes:');
      console.log(`  aria-modal: ${ariaModal}`);
      console.log(`  aria-labelledby: ${ariaLabelledBy}`);
      console.log(`  role: ${role}`);

      expect(ariaModal).toBe('true');
      expect(ariaLabelledBy).toBeTruthy();
      expect(role).toBe('dialog');

      // Take screenshot
      await page.screenshot({ path: '/tmp/modal-session-detail.png', fullPage: true });
      console.log('Screenshot: /tmp/modal-session-detail.png');

      // Close modal
      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);
    }
  });

  test('4. Main Page - Version History Modal', async () => {
    // Navigate to main page
    await page.goto('http://localhost:8003');
    await page.waitForLoadState('networkidle');

    // Look for version history button
    const versionButtons = page.locator(
      'button:has-text("Version"), button:has-text("History"), button[title*="Version" i]'
    );

    if (await versionButtons.first().isVisible()) {
      await versionButtons.first().click();

      // Wait for modal
      await page.waitForSelector('[role="dialog"]', { timeout: 5000 });

      const modal = await page.locator('[role="dialog"]').first();

      const ariaModal = await modal.getAttribute('aria-modal');
      const ariaLabelledBy = await modal.getAttribute('aria-labelledby');
      const role = await modal.getAttribute('role');

      console.log('Version History Modal ARIA attributes:');
      console.log(`  aria-modal: ${ariaModal}`);
      console.log(`  aria-labelledby: ${ariaLabelledBy}`);
      console.log(`  role: ${role}`);

      expect(ariaModal).toBe('true');
      expect(ariaLabelledBy).toBeTruthy();
      expect(role).toBe('dialog');

      // Take screenshot
      await page.screenshot({ path: '/tmp/modal-version-history.png', fullPage: true });
      console.log('Screenshot: /tmp/modal-version-history.png');

      // Close modal
      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);
    } else {
      console.log('Version History button not found on main page');
    }
  });

  test('5. Modal Keyboard Navigation', async () => {
    // Go back to admin users
    await page.goto('http://localhost:8003/admin/users');
    await page.waitForLoadState('networkidle');

    // Open create user modal
    await page.click(
      'button[aria-label*="Create" i], button:has-text("Create"), button:has-text("Add")'
    );

    // Wait for modal
    await page.waitForSelector('[role="dialog"]', { timeout: 5000 });

    // Get all focusable elements in modal
    const focusableElements = page.locator(
      '[role="dialog"] input, [role="dialog"] button, [role="dialog"] select, [role="dialog"] textarea, [role="dialog"] [tabindex="0"]'
    );
    const count = await focusableElements.count();

    console.log(`Found ${count} focusable elements in modal`);

    // Tab through elements
    for (let i = 0; i < Math.min(count, 3); i++) {
      await page.keyboard.press('Tab');
      await page.waitForTimeout(100);

      const focusedElement = await page.evaluate(() => {
        const el = document.activeElement as HTMLElement;
        return {
          tag: el?.tagName,
          type: el?.getAttribute('type'),
          class: el?.className,
        };
      });

      console.log(`  Tab ${i + 1}: Focused element:`, focusedElement);
    }

    // Take screenshot showing focus
    await page.screenshot({ path: '/tmp/modal-focus-navigation.png', fullPage: true });
    console.log('Screenshot: /tmp/modal-focus-navigation.png');

    // Test Escape key closes modal
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);

    const modalStillOpen = await page
      .locator('[role="dialog"]')
      .isVisible()
      .catch(() => false);
    expect(modalStillOpen).toBeFalsy();
    console.log('Modal closed with Escape key: PASS');
  });

  test('6. Verify Modal Structure and IDs', async () => {
    // Navigate to admin/users again
    await page.goto('http://localhost:8003/admin/users');
    await page.waitForLoadState('networkidle');

    // Open create user modal
    await page.click(
      'button[aria-label*="Create" i], button:has-text("Create"), button:has-text("Add")'
    );

    // Wait for modal
    await page.waitForSelector('[role="dialog"]', { timeout: 5000 });

    // Get all modals on page
    const modals = await page.locator('[role="dialog"]').all();

    console.log(`Found ${modals.length} modal(s) on page`);

    for (let i = 0; i < modals.length; i++) {
      const modal = modals[i];
      const id = await modal.getAttribute('id');
      const ariaLabelledBy = await modal.getAttribute('aria-labelledby');
      const ariaModal = await modal.getAttribute('aria-modal');
      const role = await modal.getAttribute('role');

      console.log(`\nModal ${i + 1}:`);
      console.log(`  id: ${id}`);
      console.log(`  aria-modal: ${ariaModal}`);
      console.log(`  aria-labelledby: ${ariaLabelledBy}`);
      console.log(`  role: ${role}`);

      // Verify attributes
      expect(role).toBe('dialog');
      expect(ariaModal).toBe('true');

      if (ariaLabelledBy) {
        // Check if title element exists with matching ID
        const titleElement = await page.locator(`#${ariaLabelledBy}`).first();
        const titleVisible = await titleElement.isVisible().catch(() => false);
        console.log(`  Title element #${ariaLabelledBy} exists: ${titleVisible}`);

        if (titleVisible) {
          const titleText = await titleElement.textContent();
          console.log(`  Title text: ${titleText}`);
        }
      }
    }
  });
});
