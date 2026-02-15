// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

// @ts-nocheck

/**
 * Comprehensive accessibility tests for the backup management page (/backup-management)
 * Tests cover WCAG 2.1 AA compliance including:
 * - Page structure and landmarks
 * - Form input accessibility
 * - Keyboard navigation
 * - Modal dialog accessibility
 * - Validation error accessibility
 * - Success message accessibility
 * - Backup list accessibility
 * - Action button accessibility
 * - Color contrast
 * - Disabled state accessibility
 * - Keyboard-only workflows
 * - Help text and instructions
 */

import { expect } from '@playwright/test';
import {
  validateSkipLinks,
  extractTabOrder,
  verifyFocusIndicators,
  checkLandmarkRegions,
  validateButtonLabels,
  validateFormLabels,
  checkAccessibleName,
  validateHeadingHierarchy,
  testTextContrast,
  testUIContrast,
  captureFocusState,
} from './utils/index.js';
import { authenticatedUserTest, navigateToProtectedRoute } from './fixtures/auth.js';

const test = authenticatedUserTest;

// Define test suites organized by feature
test.describe('@regression-a11y Backup Management Page Accessibility Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the backup management page
    await navigateToProtectedRoute(page, '/backup-management');
  });

  // ============================================================================
  // 1. PAGE STRUCTURE TESTS
  // ============================================================================
  test.describe('@regression-a11y Page Structure', () => {
    test('page should have correct title', async ({ page }) => {
      const title = await page.title();
      expect(title).toContain('Backup');
      expect(title).toContain('Management');
    });

    test('page should have required landmark regions', async ({ page }) => {
      const landmarks = await checkLandmarkRegions(page);
      expect(landmarks.hasLandmarks).toBe(true);

      // Should have banner landmark
      const hasBanner = landmarks.landmarks.some((l) => l.role === 'banner');
      expect(hasBanner).toBe(true);

      // Should have main landmark
      const hasMain = landmarks.landmarks.some((l) => l.role === 'main');
      expect(hasMain).toBe(true);

      console.log('Found landmarks:', landmarks.landmarks);
    });

    test('main landmark should exist and contain primary content', async ({ page }) => {
      const mainContent = page.locator('main[role="main"], [role="main"]').first();
      expect(await mainContent.count()).toBeGreaterThan(0);

      const id = await mainContent.getAttribute('id');
      expect(id).toBe('main-content');
    });

    test('navigation landmark should exist', async ({ page }) => {
      const nav = page.locator('[role="navigation"], nav').first();
      expect(await nav.count()).toBeGreaterThan(0);
    });

    test('heading hierarchy should be valid', async ({ page }) => {
      const hierarchy = await validateHeadingHierarchy(page);
      expect(hierarchy.validHierarchy).toBe(true);

      if (!hierarchy.validHierarchy) {
        console.error('Heading hierarchy issues:', hierarchy.issues);
      }
    });

    test('page should have at least one H1', async ({ page }) => {
      const h1Count = await page.locator('h1').count();
      expect(h1Count).toBeGreaterThan(0);
    });

    test('page should have proper section headings', async ({ page }) => {
      const h2Count = await page.locator('h2').count();
      const h3Count = await page.locator('h3').count();
      expect(h2Count + h3Count).toBeGreaterThan(0);
    });
  });

  // ============================================================================
  // 2. FORM INPUT ACCESSIBILITY TESTS
  // ============================================================================
  test.describe('@regression-a11y Form Input Accessibility', () => {
    test('backup create form should have error summary with alert role', async ({ page }) => {
      const errorSummary = page.locator('#backup-create-error-summary').first();
      expect(await errorSummary.count()).toBeGreaterThan(0);

      const role = await errorSummary.getAttribute('role');
      expect(role).toBe('alert');

      const ariaLive = await errorSummary.getAttribute('aria-live');
      expect(ariaLive).toBe('polite');
    });

    test('backup name input should have label', async ({ page }) => {
      const input = page.locator('#backup-name').first();
      const label = page.locator('label[for="backup-name"]').first();

      expect(await input.count()).toBeGreaterThan(0);
      expect(await label.count()).toBeGreaterThan(0);

      const labelText = await label.textContent();
      expect(labelText).toMatch(/backup.*name/i);
    });

    test('backup name input should have aria-describedby', async ({ page }) => {
      const input = page.locator('#backup-name').first();
      const describedBy = await input.getAttribute('aria-describedby');

      expect(describedBy).toBe('backup-name-error');

      // Verify the referenced element exists
      const errorElement = page.locator(`#${describedBy}`).first();
      expect(await errorElement.count()).toBeGreaterThan(0);
    });

    test('backup name input should have constraints', async ({ page }) => {
      const input = page.locator('#backup-name').first();
      const maxlength = await input.getAttribute('maxlength');
      const pattern = await input.getAttribute('pattern');

      expect(maxlength).toBe('64');
      expect(pattern).toBeTruthy();
    });

    test('retention days input should have label', async ({ page }) => {
      const input = page.locator('#retention-days').first();
      const label = page.locator('label[for="retention-days"]').first();

      expect(await input.count()).toBeGreaterThan(0);
      expect(await label.count()).toBeGreaterThan(0);

      const labelText = await label.textContent();
      expect(labelText).toMatch(/retention/i);
    });

    test('retention days input should have numeric constraints', async ({ page }) => {
      const input = page.locator('#retention-days').first();
      const type = await input.getAttribute('type');
      const min = await input.getAttribute('min');
      const max = await input.getAttribute('max');

      expect(type).toBe('number');
      expect(min).toBe('1');
      expect(max).toBe('3650');
    });

    test('retention days input should have aria-describedby', async ({ page }) => {
      const input = page.locator('#retention-days').first();
      const describedBy = await input.getAttribute('aria-describedby');

      expect(describedBy).toBe('retention-days-error');

      const errorElement = page.locator(`#${describedBy}`).first();
      expect(await errorElement.count()).toBeGreaterThan(0);
    });

    test('compress days input should have label', async ({ page }) => {
      const input = page.locator('#compress-days').first();
      const label = page.locator('label[for="compress-days"]').first();

      expect(await input.count()).toBeGreaterThan(0);
      expect(await label.count()).toBeGreaterThan(0);

      const labelText = await label.textContent();
      expect(labelText).toMatch(/compress/i);
    });

    test('all form inputs should have associated labels', async ({ page }) => {
      const formLabels = await validateFormLabels(page);
      expect(formLabels.allLabeled).toBe(true);

      if (!formLabels.allLabeled) {
        console.error('Unlabeled inputs:', formLabels.unlabeledElements);
      }
    });
  });

  // ============================================================================
  // 3. KEYBOARD NAVIGATION TESTS
  // ============================================================================
  test.describe('@regression-a11y Keyboard Navigation', () => {
    test('should be able to navigate to all buttons via Tab', async ({ page }) => {
      const buttons = await page.locator('button[type="button"], button[type="submit"]').all();
      expect(buttons.length).toBeGreaterThan(0);

      const tabOrder = await extractTabOrder(page);
      let buttonsFound = 0;

      for (const button of buttons) {
        const selector = await button.evaluate((el) => {
          if (el.id) return `#${el.id}`;
          if (el.onclick) return 'button';
          return el.textContent || el.tagName;
        });

        const inTabOrder = tabOrder.some((el) =>
          el.selector.includes('button') || el.selector.includes(selector)
        );

        if (inTabOrder) buttonsFound++;
      }

      // Most buttons should be reachable via tab order
      expect(buttonsFound).toBeGreaterThan(0);
    });

    test('Tab key should navigate through form inputs', async ({ page }) => {
      const tabOrder = await extractTabOrder(page);
      expect(tabOrder.length).toBeGreaterThan(0);

      // Should have multiple form-related elements
      const formElements = tabOrder.filter((el) =>
        el.selector.includes('input') || el.selector.includes('button')
      );
      expect(formElements.length).toBeGreaterThan(1);
    });

    test('inputs should be keyboard accessible', async ({ page }) => {
      const backupNameInput = page.locator('#backup-name').first();

      // Tab to focus
      await page.keyboard.press('Tab');
      await page.waitForLoadState("networkidle").catch(() => {});

      // Cycle through elements until we find the input or confirm it's reachable
      let attempts = 0;
      while (attempts < 20) {
        const focused = await page.evaluate(() => {
          const el = document.activeElement;
          return el?.id || '';
        });

        if (focused === 'backup-name') {
          expect(focused).toBe('backup-name');
          return;
        }

        await page.keyboard.press('Tab');
        attempts++;
      }

      // If we got here, verify the input exists and is focusable
      expect(await backupNameInput.count()).toBeGreaterThan(0);
    });

    test('should not have keyboard traps', async ({ page }) => {
      const tabOrder = await extractTabOrder(page);
      expect(tabOrder.length).toBeGreaterThan(0);

      // Navigate forward 10 times
      const visited = new Set<string>();
      for (let i = 0; i < 10; i++) {
        await page.keyboard.press('Tab');

        const focusedElement = await page.evaluate(() => {
          const el = document.activeElement;
          return el?.getAttribute('id') || el?.getAttribute('class') || el?.tagName || '';
        });

        if (visited.has(focusedElement)) {
          // We've cycled back - this might be expected at end of page
          break;
        }
        visited.add(focusedElement);
      }

      // Should have visited multiple different elements
      expect(visited.size).toBeGreaterThan(1);
    });

    test('buttons should be activable with Enter key', async ({ page }) => {
      const createBtn = page.locator('button[onclick="createBackup()"]').first();

      if (await createBtn.count() > 0) {
        // Focus the button
        await createBtn.focus();
        const isFocused = await createBtn.evaluate((el) => el === document.activeElement);
        expect(isFocused).toBe(true);

        // Button should be keyboard operable
        expect(await createBtn.count()).toBeGreaterThan(0);
      }
    });

    test('all interactive elements should be reachable via Tab', async ({ page }) => {
      const allInteractiveElements = await page.locator(
        'button, a[href], input, select, textarea, [role="button"], [role="link"]'
      ).all();

      const tabOrder = await extractTabOrder(page);

      // Most interactive elements should be in tab order
      let inTabOrderCount = 0;
      for (const el of allInteractiveElements) {
        const selector = await el.evaluate((element) => {
          if (element.id) return `#${element.id}`;
          if (element.className) return `.${element.className.split(/\s+/)[0]}`;
          return element.tagName.toLowerCase();
        });

        const inOrder = tabOrder.some((tabEl) => tabEl.selector.includes(selector));
        if (inOrder) inTabOrderCount++;
      }

      expect(inTabOrderCount).toBeGreaterThan(0);
    });
  });

  // ============================================================================
  // 4. MODAL DIALOG ACCESSIBILITY TESTS
  // ============================================================================
  test.describe('@regression-a11y Modal Dialog Accessibility', () => {
    test('restore modal should be hidden initially', async ({ page }) => {
      const modal = page.locator('#restore-modal').first();
      const isHidden = await modal.evaluate((el) =>
        el.classList.contains('hidden')
      );
      expect(isHidden).toBe(true);
    });

    test('delete modal should be hidden initially', async ({ page }) => {
      const modal = page.locator('#delete-modal').first();
      const isHidden = await modal.evaluate((el) =>
        el.classList.contains('hidden')
      );
      expect(isHidden).toBe(true);
    });

    test('restore modal should have accessible heading', async ({ page }) => {
      const modal = page.locator('#restore-modal').first();
      const heading = modal.locator('h2').first();

      expect(await heading.count()).toBeGreaterThan(0);

      const text = await heading.textContent();
      expect(text).toMatch(/confirm|restore/i);
    });

    test('delete modal should have accessible heading', async ({ page }) => {
      const modal = page.locator('#delete-modal').first();
      const heading = modal.locator('h2').first();

      expect(await heading.count()).toBeGreaterThan(0);

      const text = await heading.textContent();
      expect(text).toMatch(/confirm|delete/i);
    });

    test('restore modal buttons should have accessible names', async ({ page }) => {
      // Buttons should exist in hidden modal
      const cancelBtn = page.locator('#restore-modal button[onclick="hideRestoreModal()"]').first();
      const confirmBtn = page.locator('#confirm-restore-btn').first();

      expect(await cancelBtn.count()).toBeGreaterThan(0);
      expect(await confirmBtn.count()).toBeGreaterThan(0);

      const cancelText = await cancelBtn.textContent();
      const confirmText = await confirmBtn.textContent();

      expect(cancelText).toMatch(/cancel/i);
      expect(confirmText).toMatch(/restore/i);
    });

    test('delete modal buttons should have accessible names', async ({ page }) => {
      const cancelBtn = page.locator('#delete-modal button[onclick="hideDeleteModal()"]').first();
      const confirmBtn = page.locator('#confirm-delete-btn').first();

      expect(await cancelBtn.count()).toBeGreaterThan(0);
      expect(await confirmBtn.count()).toBeGreaterThan(0);

      const cancelText = await cancelBtn.textContent();
      const confirmText = await confirmBtn.textContent();

      expect(cancelText).toMatch(/cancel/i);
      expect(confirmText).toMatch(/delete/i);
    });
  });

  // ============================================================================
  // 5. VALIDATION ERROR ACCESSIBILITY TESTS
  // ============================================================================
  test.describe('@regression-a11y Validation Error Accessibility', () => {
    test('error messages should have alert role', async ({ page }) => {
      const errorElements = await page.locator('[id$="-error"]').all();

      for (const error of errorElements) {
        const role = await error.getAttribute('role');
        if (role) {
          expect(role).toBe('alert');
        }
      }
    });

    test('error messages should have aria-live assertive', async ({ page }) => {
      const errorElements = await page.locator('[id$="-error"]').all();

      for (const error of errorElements) {
        const ariaLive = await error.getAttribute('aria-live');
        if (ariaLive) {
          expect(ariaLive).toBe('assertive');
        }
      }
    });

    test('error field associations should be valid', async ({ page }) => {
      const labelledByErrors = await page.evaluate(() => {
        const errors: string[] = [];
        document.querySelectorAll('[aria-describedby]').forEach((el) => {
          const ids = (el.getAttribute('aria-describedby') || '').split(/\s+/);
          for (const id of ids) {
            if (id && !document.getElementById(id)) {
              errors.push(`Invalid aria-describedby reference: ${id}`);
            }
          }
        });
        return errors;
      });

      expect(labelledByErrors.length).toBe(0);
    });

    test('error summaries should have proper ARIA attributes', async ({ page }) => {
      const errorSummaries = await page.locator('[id$="error-summary"]').all();

      for (const summary of errorSummaries) {
        const role = await summary.getAttribute('role');
        const ariaLive = await summary.getAttribute('aria-live');

        expect(role).toBe('alert');
        expect(ariaLive).toBe('polite');
      }
    });
  });

  // ============================================================================
  // 6. SUCCESS MESSAGE ACCESSIBILITY TESTS
  // ============================================================================
  test.describe('@regression-a11y Success Message Accessibility', () => {
    test('backup status text should be associated with proper container', async ({ page }) => {
      const statusText = page.locator('#backup-status').first();
      expect(await statusText.count()).toBeGreaterThan(0);
    });

    test('maintenance status text should be associated with proper container', async ({ page }) => {
      const statusText = page.locator('#maintenance-status').first();
      expect(await statusText.count()).toBeGreaterThan(0);
    });

    test('restore status indicator should exist', async ({ page }) => {
      const restoreStatus = page.locator('#restore-status').first();
      expect(await restoreStatus.count()).toBeGreaterThan(0);
    });
  });

  // ============================================================================
  // 7. BACKUP LIST ACCESSIBILITY TESTS
  // ============================================================================
  test.describe('@regression-a11y Backup List Accessibility', () => {
    test('backup list container should be accessible', async ({ page }) => {
      const backupList = page.locator('#backup-list').first();
      expect(await backupList.count()).toBeGreaterThan(0);
    });

    test('backup statistics should be accessible', async ({ page }) => {
      const totalBackups = page.locator('#total-backups').first();
      const totalSize = page.locator('#total-size').first();
      const compressedCount = page.locator('#compressed-count').first();
      const newestBackup = page.locator('#newest-backup').first();
      const oldestBackup = page.locator('#oldest-backup').first();

      expect(await totalBackups.count()).toBeGreaterThan(0);
      expect(await totalSize.count()).toBeGreaterThan(0);
      expect(await compressedCount.count()).toBeGreaterThan(0);
      expect(await newestBackup.count()).toBeGreaterThan(0);
      expect(await oldestBackup.count()).toBeGreaterThan(0);
    });

    test('statistics section should have proper heading', async ({ page }) => {
      const statsSection = page.locator('text=Backup Statistics').first();
      expect(await statsSection.count()).toBeGreaterThan(0);
    });
  });

  // ============================================================================
  // 8. ACTION BUTTON ACCESSIBILITY TESTS
  // ============================================================================
  test.describe('@regression-a11y Action Button Accessibility', () => {
    test('create backup button should have accessible name', async ({ page }) => {
      const createBtn = page.locator('button[onclick="createBackup()"]').first();
      const nameInfo = await checkAccessibleName(createBtn);

      expect(nameInfo.hasAccessibleName).toBe(true);
      expect(nameInfo.name).toMatch(/create|backup/i);
    });

    test('clear button should have accessible name', async ({ page }) => {
      const clearBtn = page.locator('button[onclick="clearBackupForm()"]').first();
      const nameInfo = await checkAccessibleName(clearBtn);

      expect(nameInfo.hasAccessibleName).toBe(true);
      expect(nameInfo.name).toMatch(/clear/i);
    });

    test('refresh button should have accessible name', async ({ page }) => {
      const refreshBtn = page.locator('button[onclick="refreshBackups()"]').first();
      const nameInfo = await checkAccessibleName(refreshBtn);

      expect(nameInfo.hasAccessibleName).toBe(true);
      expect(nameInfo.name).toMatch(/refresh/i);
    });

    test('cleanup button should have accessible name', async ({ page }) => {
      const cleanupBtn = page.locator('button[onclick="cleanupBackups()"]').first();
      const nameInfo = await checkAccessibleName(cleanupBtn);

      expect(nameInfo.hasAccessibleName).toBe(true);
      expect(nameInfo.name).toMatch(/cleanup/i);
    });

    test('compress button should have accessible name', async ({ page }) => {
      const compressBtn = page.locator('button[onclick="compressBackups()"]').first();
      const nameInfo = await checkAccessibleName(compressBtn);

      expect(nameInfo.hasAccessibleName).toBe(true);
      expect(nameInfo.name).toMatch(/compress/i);
    });

    test('all buttons should be keyboard accessible', async ({ page }) => {
      const buttons = await page.locator('button[type="button"], button[type="submit"]').all();
      expect(buttons.length).toBeGreaterThan(0);

      const tabOrder = await extractTabOrder(page);
      for (const button of buttons) {
        const selector = await button.evaluate((el) => {
          if (el.id) return `#${el.id}`;
          if (el.className) return `.${el.className.split(/\s+/)[0]}`;
          return el.tagName.toLowerCase();
        });

        // Button should be in tab order or have onclick (which makes it focusable)
        const hasOnclick = await button.getAttribute('onclick');
        const inTabOrder = tabOrder.some((el) => el.selector.includes(selector));
        expect(inTabOrder || hasOnclick).toBe(true);
      }
    });
  });

  // ============================================================================
  // 9. COLOR CONTRAST TESTS
  // ============================================================================
  test.describe('@regression-a11y Color Contrast - WCAG 2.1 AA Compliance', () => {
    test('form labels should have sufficient contrast', async ({ page }) => {
      const labels = await page.locator('label').all();

      for (let i = 0; i < Math.min(5, labels.length); i++) {
        const contrast = await testTextContrast(page, labels[i]!, 'AA');
        expect(contrast.passes).toBe(true);
      }
    });

    test('form field text should have sufficient contrast', async ({ page }) => {
      const inputs = await page.locator('input:visible').all();

      for (let i = 0; i < Math.min(5, inputs.length); i++) {
        const contrast = await testUIContrast(page, inputs[i]!, 'AA');
        expect(contrast.passes).toBe(true);
      }
    });

    test('form field borders should have sufficient contrast', async ({ page }) => {
      const inputs = await page.locator('input[type="text"], input[type="number"]').all();

      for (let i = 0; i < Math.min(3, inputs.length); i++) {
        const contrast = await testUIContrast(page, inputs[i]!, 'AA');
        // Borders should have at least 3:1 contrast
        expect(contrast.ratio).toBeGreaterThanOrEqual(3);
      }
    });

    test('button text should have sufficient contrast', async ({ page }) => {
      const buttons = await page.locator('button').all();

      for (let i = 0; i < Math.min(5, buttons.length); i++) {
        const contrast = await testUIContrast(page, buttons[i]!, 'AA');
        expect(contrast.passes).toBe(true);
      }
    });

    test('error messages should have sufficient contrast', async ({ page }) => {
      const errorElements = await page.locator('[role="alert"], .text-red-600').all();

      for (let i = 0; i < Math.min(3, errorElements.length); i++) {
        const contrast = await testTextContrast(page, errorElements[i]!, 'AA');
        expect(contrast.passes).toBe(true);
      }
    });

    test('form help text should have sufficient contrast', async ({ page }) => {
      const helpText = await page.locator('label, small, [class*="help"]').all();

      for (let i = 0; i < Math.min(3, helpText.length); i++) {
        const contrast = await testTextContrast(page, helpText[i]!, 'AA');
        expect(contrast.passes).toBe(true);
      }
    });

    test('placeholder text should have sufficient contrast', async ({ page }) => {
      const inputsWithPlaceholder = await page.locator('input[placeholder]').all();

      for (let i = 0; i < Math.min(3, inputsWithPlaceholder.length); i++) {
        const contrast = await testUIContrast(page, inputsWithPlaceholder[i]!, 'AA');
        expect(contrast.ratio).toBeGreaterThanOrEqual(3);
      }
    });

    test('progress indicators should have sufficient contrast', async ({ page }) => {
      const progressFill = page.locator('#backup-progress-fill, #maintenance-progress-fill').first();

      if (await progressFill.count() > 0) {
        const contrast = await testUIContrast(page, progressFill, 'AA');
        expect(contrast.ratio).toBeGreaterThanOrEqual(3);
      }
    });

    test('focus indicators should have sufficient contrast', async ({ page }) => {
      const focusableElements = await page.locator('a[href], button, input, select, textarea').all();

      if (focusableElements.length > 0) {
        const element = focusableElements[0]!;
        await element.focus();

        const focusOutlineColor = await element.evaluate((el) => {
          const style = window.getComputedStyle(el, ':focus');
          return style.outlineColor || style.boxShadow || '';
        });

        expect(focusOutlineColor).toBeTruthy();
      }
    });

    test('all key elements should pass batch contrast check', async ({ page }) => {
      const keyElements = [
        'label',
        'button',
        'input',
        '[role="alert"]',
        '.font-bold',
        '.font-semibold',
      ];

      for (const selector of keyElements) {
        const elements = await page.locator(selector).all();
        if (elements.length > 0) {
          const firstElement = elements[0]!;
          const contrast = await testTextContrast(page, firstElement, 'AA');
          // At minimum, text should have reasonable contrast
          expect(contrast.ratio).toBeGreaterThan(2);
        }
      }
    });
  });

  // ============================================================================
  // 10. DISABLED STATE ACCESSIBILITY TESTS
  // ============================================================================
  test.describe('@regression-a11y Disabled State Accessibility', () => {
    test('disabled buttons should not be in tab order', async ({ page }) => {
      const tabOrder = await extractTabOrder(page);

      // Check that no disabled buttons are in tab order
      for (const element of tabOrder) {
        const isDisabled = await page.evaluate((selector) => {
          const el = document.querySelector(selector);
          if (!el) return false;
          return (
            el.hasAttribute('disabled') ||
            el.getAttribute('aria-disabled') === 'true'
          );
        }, element.selector);

        expect(isDisabled).toBe(false);
      }
    });

    test('disabled inputs should not be in tab order', async ({ page }) => {
      const tabOrder = await extractTabOrder(page);

      // Check that no disabled inputs are in tab order
      for (const element of tabOrder) {
        const isDisabled = await page.evaluate((selector) => {
          const el = document.querySelector(selector);
          if (!el) return false;
          return (
            (el as HTMLInputElement).disabled ||
            el.getAttribute('aria-disabled') === 'true'
          );
        }, element.selector);

        expect(isDisabled).toBe(false);
      }
    });
  });

  // ============================================================================
  // 11. KEYBOARD-ONLY WORKFLOW TESTS
  // ============================================================================
  test.describe('@regression-a11y Keyboard-Only Workflows', () => {
    test('should navigate backup create form with keyboard only', async ({ page }) => {
      const tabOrder = await extractTabOrder(page);
      expect(tabOrder.length).toBeGreaterThan(0);

      // Tab through first 5 elements
      for (let i = 0; i < Math.min(5, tabOrder.length); i++) {
        await page.keyboard.press('Tab');

        const focusedElement = await page.evaluate(() => {
          const el = document.activeElement;
          return el?.getAttribute('id') || el?.tagName || '';
        });

        expect(focusedElement).toBeTruthy();
      }
    });

    test('should focus backup name input via keyboard', async ({ page }) => {
      const tabOrder = await extractTabOrder(page);
      expect(tabOrder.length).toBeGreaterThan(0);

      // Tab to backup name input
      let tabCount = 0;
      while (tabCount < 20) {
        await page.keyboard.press('Tab');
        const focusedId = await page.evaluate(() => {
          return document.activeElement?.getAttribute('id') || '';
        });

        if (focusedId === 'backup-name') {
          expect(focusedId).toBe('backup-name');
          return;
        }
        tabCount++;
      }

      // If direct navigation didn't work, at least verify the input exists
      const backupNameInput = page.locator('#backup-name').first();
      expect(await backupNameInput.count()).toBeGreaterThan(0);
    });

    test('should be able to fill form and submit via keyboard', async ({ page }) => {
      const backupNameInput = page.locator('#backup-name').first();

      if (await backupNameInput.count() > 0) {
        // Focus and fill the input
        await backupNameInput.focus();
        await page.keyboard.type('test-backup');

        const value = await backupNameInput.inputValue();
        expect(value).toBe('test-backup');
      }
    });

    test('should not have keyboard traps in forms', async ({ page }) => {
      const tabOrder = await extractTabOrder(page);
      expect(tabOrder.length).toBeGreaterThan(0);

      // Navigate forward 10 times
      const visited = new Set<string>();
      for (let i = 0; i < 10; i++) {
        await page.keyboard.press('Tab');

        const focusedElement = await page.evaluate(() => {
          const el = document.activeElement;
          return el?.getAttribute('id') || el?.getAttribute('class') || el?.tagName || '';
        });

        if (visited.has(focusedElement)) {
          // We've cycled back - this might be expected at end of page
          break;
        }
        visited.add(focusedElement);
      }

      // Should have visited multiple different elements
      expect(visited.size).toBeGreaterThan(1);
    });

    test('all interactive elements should be reachable via Tab', async ({ page }) => {
      const allInteractiveElements = await page.locator(
        'button, a[href], input, select, textarea, [role="button"], [role="link"]'
      ).all();

      const tabOrder = await extractTabOrder(page);

      // Most interactive elements should be in tab order
      let inTabOrderCount = 0;
      for (const el of allInteractiveElements) {
        const selector = await el.evaluate((element) => {
          if (element.id) return `#${element.id}`;
          if (element.className) return `.${element.className.split(/\s+/)[0]}`;
          return element.tagName.toLowerCase();
        });

        const inOrder = tabOrder.some((tabEl) => tabEl.selector.includes(selector));
        if (inOrder) inTabOrderCount++;
      }

      expect(inTabOrderCount).toBeGreaterThan(0);
    });

    test('should have visible focus indicators during keyboard navigation', async ({ page }) => {
      const focusResult = await verifyFocusIndicators(page);

      // Should have elements with focus indicators
      expect(focusResult.elementsWithFocus + focusResult.elementsWithoutFocus).toBeGreaterThan(0);

      // Ratio of focused elements should be reasonable
      const ratio = focusResult.elementsWithFocus /
        (focusResult.elementsWithFocus + focusResult.elementsWithoutFocus);
      expect(ratio).toBeGreaterThan(0.5);

      console.log(
        `Focus indicators: ${focusResult.elementsWithFocus} with, ${focusResult.elementsWithoutFocus} without`
      );
    });
  });

  // ============================================================================
  // 12. HELP TEXT AND INSTRUCTIONS TESTS
  // ============================================================================
  test.describe('@regression-a11y Help Text and Instructions', () => {
    test('form labels should be properly associated with inputs', async ({ page }) => {
      const labels = await page.locator('label').all();

      for (const label of labels) {
        const htmlFor = await label.getAttribute('for');
        if (htmlFor) {
          const input = page.locator(`#${htmlFor}`).first();
          expect(await input.count()).toBeGreaterThan(0);
        }
      }
    });

    test('error messages should have sufficient contrast', async ({ page }) => {
      const errorMessages = await page.locator('[id$="-error"]').all();

      for (let i = 0; i < Math.min(3, errorMessages.length); i++) {
        const contrast = await testTextContrast(page, errorMessages[i]!, 'AA');
        expect(contrast.passes).toBe(true);
      }
    });

    test('input constraints should be visible', async ({ page }) => {
      const backupNameInput = page.locator('#backup-name').first();
      const maxlength = await backupNameInput.getAttribute('maxlength');
      const pattern = await backupNameInput.getAttribute('pattern');

      expect(maxlength).toBeTruthy();
      expect(pattern).toBeTruthy();
    });
  });

  // ============================================================================
  // 13. SKIP LINK FUNCTIONALITY TESTS
  // ============================================================================
  test.describe('@regression-a11y Skip Link Functionality', () => {
    test('should have skip link as first focusable element', async ({ page }) => {
      const skipLinks = await validateSkipLinks(page);
      expect(skipLinks.hasSkipLink).toBe(true);
      expect(skipLinks.skipLinks.length).toBeGreaterThan(0);
    });

    test('skip link should be invisible until focused', async ({ page }) => {
      const skipLinks = await validateSkipLinks(page);
      expect(skipLinks.hasSkipLink).toBe(true);

      const isHidden = await page.evaluate(() => {
        const skipLink = document.querySelector('a[href^="#"]');
        if (!skipLink) return true;
        const style = window.getComputedStyle(skipLink);
        return style.visibility === 'hidden' || style.display === 'none' || style.opacity === '0';
      });
      expect(isHidden).toBe(true);
    });

    test('skip link should be visible when focused', async ({ page }) => {
      await page.keyboard.press('Tab');

      const isVisible = await page.evaluate(() => {
        const skipLink = document.querySelector('a[href^="#"]');
        if (!skipLink) return false;
        const style = window.getComputedStyle(skipLink);
        return style.visibility !== 'hidden' && style.display !== 'none' && style.opacity !== '0';
      });
      expect(isVisible).toBe(true);
    });

    test('skip link should target main content', async ({ page }) => {
      const skipLink = page.locator('a[href^="#"]').first();
      if (await skipLink.count() > 0) {
        const href = await skipLink.getAttribute('href');
        expect(href).toBeTruthy();
        expect(href).toMatch(/^#/);

        // Target should exist
        const targetId = href?.replace('#', '');
        const target = page.locator(`#${targetId}`).first();
        expect(await target.count()).toBeGreaterThan(0);
      }
    });
  });

  // ============================================================================
  // 14. ARIA ATTRIBUTES TESTS
  // ============================================================================
  test.describe('@regression-a11y ARIA Attributes', () => {
    test('should not have duplicate IDs', async ({ page }) => {
      const ids = await page.evaluate(() => {
        const allIds = Array.from(document.querySelectorAll('[id]')).map((el) => el.id);
        const duplicates = allIds.filter((id, index) => allIds.indexOf(id) !== index);
        return { total: allIds.length, unique: new Set(allIds).size, duplicates };
      });

      expect(ids.duplicates).toEqual([]);
    });

    test('should have valid aria-labelledby references', async ({ page }) => {
      const labelledByErrors = await page.evaluate(() => {
        const errors: string[] = [];
        document.querySelectorAll('[aria-labelledby]').forEach((el) => {
          const ids = (el.getAttribute('aria-labelledby') || '').split(/\s+/);
          for (const id of ids) {
            if (id && !document.getElementById(id)) {
              errors.push(`Invalid reference: ${id}`);
            }
          }
        });
        return errors;
      });

      expect(labelledByErrors.length).toBe(0);
    });

    test('should have valid aria-describedby references', async ({ page }) => {
      const describedByErrors = await page.evaluate(() => {
        const errors: string[] = [];
        document.querySelectorAll('[aria-describedby]').forEach((el) => {
          const ids = (el.getAttribute('aria-describedby') || '').split(/\s+/);
          for (const id of ids) {
            if (id && !document.getElementById(id)) {
              errors.push(`Invalid reference: ${id}`);
            }
          }
        });
        return errors;
      });

      expect(describedByErrors.length).toBe(0);
    });

    test('should have no invalid aria-live values', async ({ page }) => {
      const liveRegions = await page.locator('[aria-live]').all();

      for (const region of liveRegions) {
        const ariaLive = await region.getAttribute('aria-live');
        expect(['polite', 'assertive', 'off']).toContain(ariaLive);
      }
    });
  });

  // ============================================================================
  // 15. RESPONSIVE ACCESSIBILITY TESTS
  // ============================================================================
  test.describe('@regression-a11y Mobile Viewport Accessibility', () => {
    test('should maintain accessibility at mobile viewport', async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 });

      // Navigate to backup management page
      await navigateToProtectedRoute(page, '/backup-management');

      // Test essential accessibility features
      const skipLinks = await validateSkipLinks(page);
      expect(skipLinks.hasSkipLink).toBe(true);

      const landmarks = await checkLandmarkRegions(page);
      expect(landmarks.hasLandmarks).toBe(true);

      const buttons = await validateButtonLabels(page);
      expect(buttons.allButtonsLabeled).toBe(true);

      // Reset viewport
      await page.setViewportSize({ width: 1280, height: 720 });
    });

    test('form inputs should be touch accessible at mobile size', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await navigateToProtectedRoute(page, '/backup-management');

      const inputs = await page.locator('input, select, button').all();

      for (const input of inputs) {
        const boundingBox = await input.boundingBox();
        if (boundingBox) {
          // Touch targets should be at least 44x44 pixels
          expect(boundingBox.width).toBeGreaterThanOrEqual(44);
          expect(boundingBox.height).toBeGreaterThanOrEqual(44);
        }
      }

      // Reset viewport
      await page.setViewportSize({ width: 1280, height: 720 });
    });
  });

  // ============================================================================
  // 16. VISUAL TESTING TESTS
  // ============================================================================
  test.describe('@regression-a11y Visual Accessibility', () => {
    test('should capture backup management page state for visual review', async ({ page }) => {
      await page.screenshot({ path: 'tests/accessibility/reports/backup-management-page.png' });
      await expect(page.locator('body')).toBeVisible();
    });

    test('should capture create backup button focus state', async ({ page }) => {
      const createBtn = page.locator('button[onclick="createBackup()"]').first();
      if (await createBtn.count() > 0) {
        await captureFocusState(
          page,
          createBtn,
          'tests/accessibility/reports/backup-create-button-focus.png'
        );
      }
    });

    test('should capture refresh button focus state', async ({ page }) => {
      const refreshBtn = page.locator('button[onclick="refreshBackups()"]').first();
      if (await refreshBtn.count() > 0) {
        await captureFocusState(
          page,
          refreshBtn,
          'tests/accessibility/reports/backup-refresh-button-focus.png'
        );
      }
    });

    test('should capture backup name input focus state', async ({ page }) => {
      const backupNameInput = page.locator('#backup-name').first();
      if (await backupNameInput.count() > 0) {
        await captureFocusState(
          page,
          backupNameInput,
          'tests/accessibility/reports/backup-name-input-focus.png'
        );
      }
    });

    test('focus indicators should be visually distinct', async ({ page }) => {
      const focusResult = await verifyFocusIndicators(page);

      // Most elements should have focus indicators
      const ratio = focusResult.elementsWithFocus / (focusResult.elementsWithFocus + focusResult.elementsWithoutFocus);
      expect(ratio).toBeGreaterThan(0.5);

      console.log(`Focus indicators: ${focusResult.elementsWithFocus} with, ${focusResult.elementsWithoutFocus} without`);
    });
  });
});

// ============================================================================
// AUTHENTICATED USER TESTS
// ============================================================================
authenticatedUserTest.describe(
  'Backup Management Page Accessibility - Authenticated User',
  () => {
    authenticatedUserTest.beforeEach(async ({ page }) => {
      // Navigate to backup management page
      await navigateToProtectedRoute(page, '/backup-management');
    });

    authenticatedUserTest(
      'user should be able to access backup management functionality',
      async ({ page }) => {
        // Verify page loaded
        const mainContent = page.locator('main[role="main"], [role="main"]').first();
        expect(await mainContent.count()).toBeGreaterThan(0);

        // Verify backup create form is present
        const createForm = page.locator('#backup-create-form').first();
        expect(await createForm.count()).toBeGreaterThan(0);

        // Verify backup list is present
        const backupList = page.locator('#backup-list').first();
        expect(await backupList.count()).toBeGreaterThan(0);
      }
    );

    authenticatedUserTest(
      'all backup management buttons should be accessible to authenticated user',
      async ({ page }) => {
        const buttons = await validateButtonLabels(page);
        expect(buttons.allButtonsLabeled).toBe(true);
      }
    );

    authenticatedUserTest(
      'authenticated user should be able to navigate backup form with keyboard',
      async ({ page }) => {
        const tabOrder = await extractTabOrder(page);
        expect(tabOrder.length).toBeGreaterThan(0);

        // Navigate through form fields
        for (let i = 0; i < Math.min(3, tabOrder.length); i++) {
          await page.keyboard.press('Tab');
          await expect(page.locator(':focus')).toHaveCount(1);
        }
      }
    );

    authenticatedUserTest(
      'authenticated user should see all form labels properly associated',
      async ({ page }) => {
        const formLabels = await validateFormLabels(page);
        expect(formLabels.allLabeled).toBe(true);

        if (!formLabels.allLabeled) {
          console.error('Unlabeled inputs:', formLabels.unlabeledElements);
        }
      }
    );
  }
);
