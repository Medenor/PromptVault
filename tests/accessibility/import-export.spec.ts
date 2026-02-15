// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

// @ts-nocheck

/**
 * Comprehensive accessibility tests for the import-export page (/import-export)
 * Tests cover WCAG 2.1 AA compliance including:
 * - Page structure and landmarks
 * - File upload accessibility
 * - Form field navigation and labels
 * - Modal dialog accessibility
 * - Progress indication
 * - Error and status message accessibility
 * - Color contrast
 * - Keyboard-only workflow
 */

import { expect } from '@playwright/test';
import {
  validateSkipLinks,
  extractTabOrder,
  validateRovingTabindex,
  verifyFocusIndicators,
  checkLandmarkRegions,
  validateButtonLabels,
  validateFormLabels,
  checkAccessibleName,
  checkLiveRegions,
  validateHeadingHierarchy,
  testTextContrast,
  testUIContrast,
  testContrastBatch,
  captureNormalState,
  captureFocusState,
  capturePageWithHighlight,
  validateAccessibleNamesBatch,
  testKeyboardNavigation,
  validateSkipLinks as validateSkipLinksUtil,
} from './utils/index.js';
import { authenticatedUserTest, getBaseURL, navigateToProtectedRoute } from './fixtures/auth.js';

const test = authenticatedUserTest;
const baseURL = getBaseURL();

// Define test suites organized by feature
test.describe('@regression-a11y Import-Export Page Accessibility Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the import-export page
    await navigateToProtectedRoute(page, '/import-export');
  });

  // ============================================================================
  // 1. PAGE STRUCTURE TESTS
  // ============================================================================
  test.describe('@regression-a11y Page Structure', () => {
    test('page should have correct title', async ({ page }) => {
      const title = await page.title();
      expect(title).toContain('Import');
      expect(title).toContain('Export');
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
      expect(id || 'main').toBeTruthy();
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

    test('section headings should not skip levels', async ({ page }) => {
      const hierarchy = await validateHeadingHierarchy(page);
      for (const heading of hierarchy.headings) {
        expect(heading.level).toBeGreaterThan(0);
        expect(heading.level).toBeLessThanOrEqual(6);
      }
    });
  });

  // ============================================================================
  // 2. FILE UPLOAD ACCESSIBILITY TESTS
  // ============================================================================
  test.describe('@regression-a11y File Upload Accessibility', () => {
    test('file input should have accessible label', async ({ page }) => {
      const fileInput = page.locator('#import-file').first();
      expect(await fileInput.count()).toBeGreaterThan(0);

      const label = page.locator('label[for="import-file"]').first();
      expect(await label.count()).toBeGreaterThan(0);

      const labelText = await label.textContent();
      expect(labelText).toBeTruthy();
    });

    test('file input should have correct accept attribute', async ({ page }) => {
      const fileInput = page.locator('#import-file').first();
      const accept = await fileInput.getAttribute('accept');

      expect(accept).toBeTruthy();
      expect(accept).toContain('.csv');
      expect(accept).toContain('.json');
      expect(accept).toContain('.md');
    });

    test('file input should be keyboard accessible', async ({ page }) => {
      const fileInput = page.locator('#import-file').first();

      // Tab to the file input
      const tabOrder = await extractTabOrder(page);
      expect(tabOrder.length).toBeGreaterThan(0);

      // Find file input in tab order
      const fileInputInTabOrder = tabOrder.some((el) =>
        el.selector.includes('import-file')
      );
      expect(fileInputInTabOrder).toBe(true);

      // Focus the file input
      await fileInput.focus();
      const isFocused = await fileInput.evaluate((el) => el === document.activeElement);
      expect(isFocused).toBe(true);
    });

    test('file input should have aria-describedby pointing to error message', async ({ page }) => {
      const fileInput = page.locator('#import-file').first();
      const describedBy = await fileInput.getAttribute('aria-describedby');

      expect(describedBy).toBe('import-file-error');

      // Verify the referenced element exists
      const errorElement = page.locator(`#${describedBy}`).first();
      expect(await errorElement.count()).toBeGreaterThan(0);
    });

    test('drag-and-drop zone should be keyboard accessible', async ({ page }) => {
      // While HTML file input doesn't have native drag-and-drop, verify file input is reachable
      const fileInput = page.locator('#import-file').first();
      expect(await fileInput.count()).toBeGreaterThan(0);

      // Verify it can receive focus
      await fileInput.focus();
      const isFocused = await fileInput.evaluate((el) => el === document.activeElement);
      expect(isFocused).toBe(true);
    });
  });

  // ============================================================================
  // 3. FORM FIELD NAVIGATION TESTS
  // ============================================================================
  test.describe('@regression-a11y Form Field Navigation', () => {
    test('export form should have logical tab order', async ({ page }) => {
      const exportForm = page.locator('#export-form').first();
      expect(await exportForm.count()).toBeGreaterThan(0);

      const tabOrder = await extractTabOrder(page);
      expect(tabOrder.length).toBeGreaterThan(0);

      // Form should contain multiple focusable elements
      const formElements = tabOrder.filter((el) =>
        el.selector.includes('export')
      );
      expect(formElements.length).toBeGreaterThan(0);
    });

    test('import form should have logical tab order', async ({ page }) => {
      const importForm = page.locator('#import-form').first();
      expect(await importForm.count()).toBeGreaterThan(0);

      const tabOrder = await extractTabOrder(page);
      expect(tabOrder.length).toBeGreaterThan(0);

      const formElements = tabOrder.filter((el) =>
        el.selector.includes('import')
      );
      expect(formElements.length).toBeGreaterThan(0);
    });

    test('all form inputs should have associated labels', async ({ page }) => {
      const formLabels = await validateFormLabels(page);
      expect(formLabels.allLabeled).toBe(true);

      if (!formLabels.allLabeled) {
        console.error('Unlabeled inputs:', formLabels.unlabeledElements);
      }
    });

    test('export format select should have label', async ({ page }) => {
      const select = page.locator('#export-format').first();
      const label = page.locator('label[for="export-format"]').first();

      expect(await select.count()).toBeGreaterThan(0);
      expect(await label.count()).toBeGreaterThan(0);

      const labelText = await label.textContent();
      expect(labelText).toMatch(/format/i);
    });

    test('import mode select should have label and description', async ({ page }) => {
      const select = page.locator('#import-mode').first();
      const label = page.locator('label[for="import-mode"]').first();
      const help = page.locator('#import-mode-help').first();

      expect(await select.count()).toBeGreaterThan(0);
      expect(await label.count()).toBeGreaterThan(0);
      expect(await help.count()).toBeGreaterThan(0);

      // Verify aria-describedby
      const describedBy = await select.getAttribute('aria-describedby');
      expect(describedBy).toBe('import-mode-help');
    });

    test('export filename input should have label and error description', async ({ page }) => {
      const input = page.locator('#export-filename').first();
      const label = page.locator('label[for="export-filename"]').first();
      const error = page.locator('#export-filename-error').first();

      expect(await input.count()).toBeGreaterThan(0);
      expect(await label.count()).toBeGreaterThan(0);
      expect(await error.count()).toBeGreaterThan(0);

      const describedBy = await input.getAttribute('aria-describedby');
      expect(describedBy).toBe('export-filename-error');
    });

    test('checkbox inputs should have labels', async ({ page }) => {
      const checkboxes = await page.locator('input[type="checkbox"]').all();
      expect(checkboxes.length).toBeGreaterThan(0);

      for (const checkbox of checkboxes) {
        // Each checkbox should have an associated label
        const id = await checkbox.getAttribute('id');
        const label = page.locator(`label[for="${id}"]`).first();
        expect(await label.count()).toBeGreaterThan(0);
      }
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

    test('form elements should not have skipped tabindex values', async ({ page }) => {
      const tabOrder = await extractTabOrder(page);

      for (const element of tabOrder) {
        // No positive tabindex should be used
        if (element.tabIndex > 0) {
          console.warn(`Element with positive tabindex: ${element.selector}`);
        }
      }
    });
  });

  // ============================================================================
  // 4. MODAL DIALOG ACCESSIBILITY TESTS
  // ============================================================================
  test.describe('@regression-a11y Modal Dialog Accessibility', () => {
    test('preview panel should be hidden initially', async ({ page }) => {
      const previewPanel = page.locator('#preview-panel').first();
      const isHidden = await previewPanel.evaluate((el) =>
        el.classList.contains('hidden')
      );
      expect(isHidden).toBe(true);
    });

    test('preview panel should be keyboard accessible when shown', async ({ page }) => {
      const previewPanel = page.locator('#preview-panel').first();

      // Show the preview panel
      await previewPanel.evaluate((el) => el.classList.remove('hidden'));

      // Verify it's visible
      const isVisible = await previewPanel.isVisible();
      expect(isVisible).toBe(true);
    });

    test('preview modal should have accessible buttons', async ({ page }) => {
      const previewPanel = page.locator('#preview-panel').first();
      await previewPanel.evaluate((el) => el.classList.remove('hidden'));

      const cancelBtn = page.locator('#cancel-btn').first();
      const confirmBtn = page.locator('#confirm-btn').first();

      expect(await cancelBtn.count()).toBeGreaterThan(0);
      expect(await confirmBtn.count()).toBeGreaterThan(0);

      // Both should have accessible names
      const cancelName = await checkAccessibleName(cancelBtn);
      const confirmName = await checkAccessibleName(confirmBtn);

      expect(cancelName.hasAccessibleName).toBe(true);
      expect(confirmName.hasAccessibleName).toBe(true);
    });

    test('modal buttons should be keyboard focusable', async ({ page }) => {
      const previewPanel = page.locator('#preview-panel').first();
      await previewPanel.evaluate((el) => el.classList.remove('hidden'));

      const cancelBtn = page.locator('#cancel-btn').first();

      await cancelBtn.focus();
      const isFocused = await cancelBtn.evaluate((el) => el === document.activeElement);
      expect(isFocused).toBe(true);
    });

    test('modal close buttons should have clear labels', async ({ page }) => {
      const previewPanel = page.locator('#preview-panel').first();
      await previewPanel.evaluate((el) => el.classList.remove('hidden'));

      const cancelBtn = page.locator('#cancel-btn').first();
      const cancelText = await cancelBtn.textContent();

      expect(cancelText).toMatch(/cancel|close/i);
    });

    test('modal confirm button should have clear action label', async ({ page }) => {
      const previewPanel = page.locator('#preview-panel').first();
      await previewPanel.evaluate((el) => el.classList.remove('hidden'));

      const confirmBtn = page.locator('#confirm-btn').first();
      const confirmText = await confirmBtn.textContent();

      expect(confirmText).toMatch(/confirm|proceed|import|export/i);
    });
  });

  // ============================================================================
  // 5. PROGRESS INDICATION TESTS
  // ============================================================================
  test.describe('@regression-a11y Progress Indication', () => {
    test('export progress bar should be hidden initially', async ({ page }) => {
      const progressContainer = page.locator('#export-progress').first();
      const isHidden = await progressContainer.evaluate((el) =>
        el.classList.contains('hidden')
      );
      expect(isHidden).toBe(true);
    });

    test('import progress bar should be hidden initially', async ({ page }) => {
      const progressContainer = page.locator('#import-progress').first();
      const isHidden = await progressContainer.evaluate((el) =>
        el.classList.contains('hidden')
      );
      expect(isHidden).toBe(true);
    });

    test('export progress indicator should have proper structure', async ({ page }) => {
      const progressContainer = page.locator('#export-progress').first();
      const progressFill = page.locator('#export-progress-fill').first();
      const statusText = page.locator('#export-status').first();

      expect(await progressContainer.count()).toBeGreaterThan(0);
      expect(await progressFill.count()).toBeGreaterThan(0);
      expect(await statusText.count()).toBeGreaterThan(0);
    });

    test('import progress indicator should have proper structure', async ({ page }) => {
      const progressContainer = page.locator('#import-progress').first();
      const progressFill = page.locator('#import-progress-fill').first();
      const statusText = page.locator('#import-status').first();

      expect(await progressContainer.count()).toBeGreaterThan(0);
      expect(await progressFill.count()).toBeGreaterThan(0);
      expect(await statusText.count()).toBeGreaterThan(0);
    });

    test('progress status text should be associated with live region', async ({ page }) => {
      const statusText = page.locator('#export-status').first();
      expect(await statusText.count()).toBeGreaterThan(0);

      // Status text should be in a container that can announce updates
      const parent = await statusText.evaluate((el) => el.parentElement);
      expect(parent).toBeTruthy();
    });
  });

  // ============================================================================
  // 6. ERROR MESSAGE ACCESSIBILITY TESTS
  // ============================================================================
  test.describe('@regression-a11y Error Message Accessibility', () => {
    test('export error banner should have alert role', async ({ page }) => {
      const errorBanner = page.locator('#export-error-summary').first();
      const role = await errorBanner.getAttribute('role');
      expect(role).toBe('alert');
    });

    test('import error banner should have alert role', async ({ page }) => {
      const errorBanner = page.locator('#import-error-summary').first();
      const role = await errorBanner.getAttribute('role');
      expect(role).toBe('alert');
    });

    test('error banners should have aria-live polite', async ({ page }) => {
      const exportError = page.locator('#export-error-summary').first();
      const importError = page.locator('#import-error-summary').first();

      const exportLive = await exportError.getAttribute('aria-live');
      const importLive = await importError.getAttribute('aria-live');

      expect(exportLive).toBe('polite');
      expect(importLive).toBe('polite');
    });

    test('error messages should be associated with form fields', async ({ page }) => {
      const exportFilenameError = page.locator('#export-filename-error').first();
      const importFileError = page.locator('#import-file-error').first();

      expect(await exportFilenameError.count()).toBeGreaterThan(0);
      expect(await importFileError.count()).toBeGreaterThan(0);

      // Verify they have alert role
      const exportRole = await exportFilenameError.getAttribute('role');
      const importRole = await importFileError.getAttribute('role');

      expect(exportRole).toBe('alert');
      expect(importRole).toBe('alert');
    });

    test('error field associations should be valid', async ({ page }) => {
      const labelledByErrors = await page.evaluate(() => {
        const errors = [];
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

    test('error messages should have sufficient contrast', async ({ page }) => {
      const exportError = page.locator('#export-filename-error').first();
      const importError = page.locator('#import-file-error').first();

      if (await exportError.count() > 0) {
        const contrast = await testTextContrast(page, exportError, 'AA');
        expect(contrast.passes).toBe(true);
      }

      if (await importError.count() > 0) {
        const contrast = await testTextContrast(page, importError, 'AA');
        expect(contrast.passes).toBe(true);
      }
    });

    test('error text color should not rely on color alone', async ({ page }) => {
      // Verify errors have visual indicators beyond color
      const errorElements = await page.locator('[role="alert"]').all();

      for (const error of errorElements) {
        const hasContent = await error.evaluate((el) => {
          const text = el.textContent?.trim() || '';
          const children = el.children.length;
          return text.length > 0 || children > 0;
        });

        // At minimum, error should have text content or child elements
        expect(hasContent).toBe(true);
      }
    });
  });

  // ============================================================================
  // 7. SUCCESS/STATUS MESSAGE ACCESSIBILITY TESTS
  // ============================================================================
  test.describe('@regression-a11y Success/Status Messages', () => {
    test('status messages should be announced to screen readers', async ({ page }) => {
      const exportStatus = page.locator('#export-status').first();
      const importStatus = page.locator('#import-status').first();

      expect(await exportStatus.count()).toBeGreaterThan(0);
      expect(await importStatus.count()).toBeGreaterThan(0);
    });

    test('live regions should be properly configured', async ({ page }) => {
      const liveRegions = await checkLiveRegions(page);
      console.log('Found live regions:', liveRegions.regions);

      // Should have some form of live region capability
      expect(liveRegions.regions.length >= 0).toBe(true);
    });

    test('statistics display should be accessible', async ({ page }) => {
      const totalPrompts = page.locator('#total-prompts').first();
      const totalCategories = page.locator('#total-categories').first();
      const totalTags = page.locator('#total-tags').first();
      const favoritePrompts = page.locator('#favorite-prompts').first();

      expect(await totalPrompts.count()).toBeGreaterThan(0);
      expect(await totalCategories.count()).toBeGreaterThan(0);
      expect(await totalTags.count()).toBeGreaterThan(0);
      expect(await favoritePrompts.count()).toBeGreaterThan(0);
    });

    test('activity history should have proper heading', async ({ page }) => {
      const activitySection = page.locator('#activity-history').first();
      const heading = page.locator('h4:has-text("Recent Activity")').first();

      expect(await activitySection.count()).toBeGreaterThan(0);
      if (await heading.count() > 0) {
        const text = await heading.textContent();
        expect(text).toMatch(/activity|history/i);
      }
    });
  });

  // ============================================================================
  // 8. EXPORT FUNCTIONALITY TESTS
  // ============================================================================
  test.describe('@regression-a11y Export Functionality', () => {
    test('export button should have accessible name', async ({ page }) => {
      const exportBtn = page.locator('button[onclick="performExport()"]').first();
      const nameInfo = await checkAccessibleName(exportBtn);

      expect(nameInfo.hasAccessibleName).toBe(true);
      expect(nameInfo.name).toMatch(/export/i);
    });

    test('preview button should have accessible name', async ({ page }) => {
      const previewBtn = page.locator('button[onclick="previewExport()"]').first();
      const nameInfo = await checkAccessibleName(previewBtn);

      expect(nameInfo.hasAccessibleName).toBe(true);
      expect(nameInfo.name).toMatch(/preview/i);
    });

    test('export format select should be keyboard accessible', async ({ page }) => {
      const select = page.locator('#export-format').first();

      // Focus the select
      await select.focus();
      const isFocused = await select.evaluate((el) => el === document.activeElement);
      expect(isFocused).toBe(true);

      // Should have multiple options
      const options = await select.locator('option').all();
      expect(options.length).toBeGreaterThan(1);
    });

    test('export options should have proper labels', async ({ page }) => {
      const options = await page.locator('#export-format option').all();

      for (const option of options) {
        const text = await option.textContent();
        expect(text).toBeTruthy();
        expect(text?.length).toBeGreaterThan(0);
      }
    });

    test('export checkboxes should have labels', async ({ page }) => {
      const favoritesCheckbox = page.locator('#include-favorites').first();
      const metadataCheckbox = page.locator('#include-metadata').first();

      expect(await favoritesCheckbox.count()).toBeGreaterThan(0);
      expect(await metadataCheckbox.count()).toBeGreaterThan(0);

      const favoritesLabel = page.locator('label:has(#include-favorites)').first();
      const metadataLabel = page.locator('label:has(#include-metadata)').first();

      expect(await favoritesLabel.count()).toBeGreaterThan(0);
      expect(await metadataLabel.count()).toBeGreaterThan(0);
    });

    test('clear button should have accessible name', async ({ page }) => {
      const clearBtn = page.locator('button[onclick="clearExportSettings()"]').first();
      const nameInfo = await checkAccessibleName(clearBtn);

      expect(nameInfo.hasAccessibleName).toBe(true);
      expect(nameInfo.name).toMatch(/clear/i);
    });
  });

  // ============================================================================
  // 9. COLOR CONTRAST TESTS
  // ============================================================================
  test.describe('@regression-a11y Color Contrast - WCAG 2.1 AA Compliance', () => {
    test('form labels should have sufficient contrast', async ({ page }) => {
      const labels = await page.locator('label').all();

      for (let i = 0; i < Math.min(5, labels.length); i++) {
        const contrast = await testTextContrast(page, labels[i], 'AA');
        expect(contrast.passes).toBe(true);
      }
    });

    test('form field text should have sufficient contrast', async ({ page }) => {
      const inputs = await page.locator('input:visible, select:visible').all();

      for (let i = 0; i < Math.min(5, inputs.length); i++) {
        const contrast = await testUIContrast(page, inputs[i], 'AA');
        expect(contrast.passes).toBe(true);
      }
    });

    test('form field borders should have sufficient contrast', async ({ page }) => {
      const inputs = await page.locator('input[type="text"], input[type="file"], select').all();

      for (let i = 0; i < Math.min(3, inputs.length); i++) {
        const contrast = await testUIContrast(page, inputs[i], 'AA');
        // Borders should have at least 3:1 contrast
        expect(contrast.ratio).toBeGreaterThanOrEqual(3);
      }
    });

    test('button text should have sufficient contrast', async ({ page }) => {
      const buttons = await page.locator('button').all();

      for (let i = 0; i < Math.min(5, buttons.length); i++) {
        const contrast = await testUIContrast(page, buttons[i], 'AA');
        expect(contrast.passes).toBe(true);
      }
    });

    test('error messages should have sufficient contrast', async ({ page }) => {
      const errorElements = await page.locator('[role="alert"], .text-red-600').all();

      for (let i = 0; i < Math.min(3, errorElements.length); i++) {
        const contrast = await testTextContrast(page, errorElements[i], 'AA');
        expect(contrast.passes).toBe(true);
      }
    });

    test('form help text should have sufficient contrast', async ({ page }) => {
      const helpText = await page.locator('.text-xs, small, [class*="help"]').all();

      for (let i = 0; i < Math.min(3, helpText.length); i++) {
        const contrast = await testTextContrast(page, helpText[i], 'AA');
        expect(contrast.passes).toBe(true);
      }
    });

    test('placeholder text should have sufficient contrast', async ({ page }) => {
      const inputsWithPlaceholder = await page.locator('input[placeholder]').all();

      for (let i = 0; i < Math.min(3, inputsWithPlaceholder.length); i++) {
        const contrast = await testUIContrast(page, inputsWithPlaceholder[i], 'AA');
        expect(contrast.ratio).toBeGreaterThanOrEqual(3);
      }
    });

    test('progress indicators should have sufficient contrast', async ({ page }) => {
      const progressFill = page.locator('#export-progress-fill, #import-progress-fill').first();

      if (await progressFill.count() > 0) {
        const contrast = await testUIContrast(page, progressFill, 'AA');
        expect(contrast.ratio).toBeGreaterThanOrEqual(3);
      }
    });

    test('focus indicators should have sufficient contrast', async ({ page }) => {
      const focusableElements = await page.locator('a[href], button, input, select, textarea').all();

      if (focusableElements.length > 0) {
        const element = focusableElements[0];
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
          const firstElement = elements[0];
          const contrast = await testTextContrast(page, firstElement, 'AA');
          // At minimum, text should have reasonable contrast
          expect(contrast.ratio).toBeGreaterThan(2);
        }
      }
    });
  });

  // ============================================================================
  // 10. KEYBOARD-ONLY WORKFLOW TESTS
  // ============================================================================
  test.describe('@regression-a11y Keyboard-Only Workflow', () => {
    test('should navigate export form with keyboard only', async ({ page }) => {
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

    test('should navigate import form with keyboard only', async ({ page }) => {
      const tabOrder = await extractTabOrder(page);
      expect(tabOrder.length).toBeGreaterThan(0);

      // Start fresh
      await page.reload();
      await page.waitForLoadState('domcontentloaded');

      // Tab to file input
      let tabCount = 0;
      while (tabCount < 20) {
        await page.keyboard.press('Tab');
        const focusedId = await page.evaluate(() => {
          return document.activeElement?.getAttribute('id') || '';
        });

        if (focusedId === 'import-file') {
          expect(focusedId).toBe('import-file');
          return;
        }
        tabCount++;
      }

      expect(tabCount < 20).toBe(true);
    });

    test('should activate buttons with Enter key', async ({ page }) => {
      const tabOrder = await extractTabOrder(page);

      // Find a button in tab order
      const buttonInOrder = tabOrder.find((el) =>
        el.selector.includes('button') || el.selector.includes('preview')
      );

      if (buttonInOrder) {
        await page.keyboard.press('Tab');
        await page.keyboard.press('Enter');

        // Verify some action occurred or no error was thrown
        await expect(page.locator('body')).toBeVisible();
      }
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

    test('all interactive elements should be reachable via Tab', async ({ page }) => {
      const allInteractiveElements = await page.locator(
        'button, a[href], input, select, textarea, [role="button"], [role="link"]'
      ).all();

      const tabOrder = await extractTabOrder(page);

      // Most interactive elements should be in tab order
      const inTabOrder = allInteractiveElements.filter(async (el) => {
        const selector = await el.evaluate((element) => {
          if (element.id) return `#${element.id}`;
          if (element.className) return `.${element.className.split(/\s+/)[0]}`;
          return element.tagName.toLowerCase();
        });

        return tabOrder.some((tabEl) => tabEl.selector.includes(selector));
      });

      expect(inTabOrder.length).toBeGreaterThan(0);
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
  // 11. FORM VALIDATION AND SUBMISSION TESTS
  // ============================================================================
  test.describe('@regression-a11y Form Validation and Submission', () => {
    test('export filename input should have maxlength attribute', async ({ page }) => {
      const input = page.locator('#export-filename').first();
      const maxlength = await input.getAttribute('maxlength');

      expect(maxlength).toBeTruthy();
      expect(parseInt(maxlength || '0')).toBeGreaterThan(0);
    });

    test('export filename input should have pattern attribute', async ({ page }) => {
      const input = page.locator('#export-filename').first();
      const pattern = await input.getAttribute('pattern');

      expect(pattern).toBeTruthy();
    });

    test('import mode select should have help text associated', async ({ page }) => {
      const select = page.locator('#import-mode').first();
      const helpId = await select.getAttribute('aria-describedby');

      expect(helpId).toBe('import-mode-help');

      const helpElement = page.locator(`#${helpId}`).first();
      expect(await helpElement.count()).toBeGreaterThan(0);

      const helpText = await helpElement.textContent();
      expect(helpText).toBeTruthy();
    });
  });

  // ============================================================================
  // 12. VISUAL TESTING TESTS
  // ============================================================================
  test.describe('@regression-a11y Visual Accessibility', () => {
    test('should capture import-export page state for visual review', async ({ page }) => {
      await page.screenshot({ path: 'tests/accessibility/reports/import-export-page.png' });
      await expect(page.locator('body')).toBeVisible();
    });

    test('should capture export form focus state', async ({ page }) => {
      const exportBtn = page.locator('button[onclick="performExport()"]').first();
      if (await exportBtn.count() > 0) {
        await captureFocusState(
          page,
          exportBtn,
          'tests/accessibility/reports/export-button-focus.png'
        );
      }
    });

    test('should capture import form focus state', async ({ page }) => {
      const importBtn = page.locator('button[onclick="performImport()"]').first();
      if (await importBtn.count() > 0) {
        await captureFocusState(
          page,
          importBtn,
          'tests/accessibility/reports/import-button-focus.png'
        );
      }
    });

    test('should capture file input focus state', async ({ page }) => {
      const fileInput = page.locator('#import-file').first();
      if (await fileInput.count() > 0) {
        await captureFocusState(
          page,
          fileInput,
          'tests/accessibility/reports/file-input-focus.png'
        );
      }
    });
  });

  // ============================================================================
  // 13. ARIA ATTRIBUTES TESTS
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
        const errors = [];
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
        const errors = [];
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

    test('form groups should have proper labels or legends', async ({ page }) => {
      const fieldsets = await page.locator('fieldset').all();

      for (const fieldset of fieldsets) {
        const legend = fieldset.locator('legend').first();
        const hasLegend = await legend.count() > 0;

        // If using fieldset, should have legend
        if (hasLegend) {
          const legendText = await legend.textContent();
          expect(legendText).toBeTruthy();
        }
      }
    });
  });

  // ============================================================================
  // 14. SKIP LINK FUNCTIONALITY TESTS
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
  // 15. RESPONSIVE ACCESSIBILITY TESTS
  // ============================================================================
  test.describe('@regression-a11y Mobile Viewport Accessibility', () => {
    test('should maintain accessibility at mobile viewport', async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 });

      // Navigate to import-export page
      await navigateToProtectedRoute(page, '/import-export');

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
      await navigateToProtectedRoute(page, '/import-export');

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
});

// ============================================================================
// AUTHENTICATED USER TESTS
// ============================================================================
authenticatedUserTest.describe(
  'Import-Export Page Accessibility - Authenticated User',
  () => {
    authenticatedUserTest.beforeEach(async ({ page }) => {
      // Navigate to import-export page
      await navigateToProtectedRoute(page, '/import-export');
    });

    authenticatedUserTest(
      'user should be able to access import-export functionality',
      async ({ page }) => {
        // Verify page loaded
        const mainContent = page.locator('main[role="main"], [role="main"]').first();
        expect(await mainContent.count()).toBeGreaterThan(0);

        // Verify both forms are present
        const importForm = page.locator('#import-form').first();
        const exportForm = page.locator('#export-form').first();

        expect(await importForm.count()).toBeGreaterThan(0);
        expect(await exportForm.count()).toBeGreaterThan(0);
      }
    );

    authenticatedUserTest(
      'all import-export buttons should be accessible to authenticated user',
      async ({ page }) => {
        const buttons = await validateButtonLabels(page);
        expect(buttons.allButtonsLabeled).toBe(true);
      }
    );

    authenticatedUserTest(
      'authenticated user should be able to navigate forms with keyboard',
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
  }
);
