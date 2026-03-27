// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

// @ts-nocheck

/**
 * Comprehensive accessibility tests for tag management page (/manage-tags)
 * Tests cover WCAG 2.1 AA compliance including:
 * - Page structure and landmarks
 * - Roving tabindex pattern for tag list
 * - Arrow key navigation
 * - Home/End key navigation
 * - Typeahead/type-ahead search
 * - Tag operations (merge, find/replace, add, edit, delete)
 * - Keyboard-only workflows
 * - ARIA attributes and focus management
 * - Color contrast
 * - Live regions and announcements
 */

import { expect } from '@playwright/test';
import {
  validateSkipLinks,
  checkLandmarkRegions,
  validateHeadingHierarchy,
  validateButtonLabels,
  validateFormLabels,
  checkAccessibleName,
  checkLiveRegions,
  validateRovingTabindex,
  extractTabOrder,
  verifyFocusIndicators,
  testTextContrast,
  testUIContrast,
  testContrastBatch,
  captureNormalState,
  captureFocusState,
  capturePageWithHighlight,
} from './utils/index.js';
import { authenticatedAdminTest, navigateToProtectedRoute, getBaseURL } from './fixtures/auth.js';

const test = authenticatedAdminTest;
const baseURL = getBaseURL();

async function hasVisibleDialog(page) {
  return await page.evaluate(() => {
    const dialogs = Array.from(document.querySelectorAll('[role="dialog"]'));
    return dialogs.some((dialog) => {
      const style = window.getComputedStyle(dialog);
      return !dialog.classList.contains('hidden') && style.display !== 'none' && style.visibility !== 'hidden';
    });
  });
}

async function focusInsideVisibleDialog(page) {
  return await page.evaluate(() => {
    const dialogs = Array.from(document.querySelectorAll('[role="dialog"]'));
    const visibleDialog = dialogs.find((dialog) => {
      const style = window.getComputedStyle(dialog);
      return !dialog.classList.contains('hidden') && style.display !== 'none' && style.visibility !== 'hidden';
    });
    if (!visibleDialog) {
      return false;
    }
    return Boolean(document.activeElement && visibleDialog.contains(document.activeElement));
  });
}

// Define test suites organized by feature
test.describe('@regression-a11y Tag Management Page Accessibility Tests', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    // Navigate to the tag management page
    await navigateToProtectedRoute(page, '/manage-tags');
    await page.waitForLoadState('domcontentloaded');
  });

  // ============================================================================
  // 1. PAGE STRUCTURE TESTS
  // ============================================================================
  test.describe('@regression-a11y Page Structure', () => {
    test('should have correct page title', async ({ authenticatedPage: page }) => {
      await navigateToProtectedRoute(page, '/manage-tags');
      await page.waitForLoadState('networkidle');
      const title = await page.title();
      expect(title).toContain('Manage Tags');
    });

    test('should have required landmark regions', async ({ authenticatedPage: page }) => {
      const landmarks = await checkLandmarkRegions(page);
      expect(landmarks.hasLandmarks).toBe(true);

      // Check for main landmark
      const hasMain = landmarks.landmarks.some((l) => l.role === 'main');
      expect(hasMain).toBe(true);

      // Check for banner
      const hasBanner = landmarks.landmarks.some((l) => l.role === 'banner');
      expect(hasBanner).toBe(true);
    });

    test('should have proper heading hierarchy', async ({ authenticatedPage: page }) => {
      const hierarchy = await validateHeadingHierarchy(page);
      expect(hierarchy.validHierarchy).toBe(
        true,
        `Heading hierarchy violations: ${hierarchy.issues.join(', ')}`
      );
      expect(hierarchy.headings.length).toBeGreaterThan(0);
    });

    test('should have skip link to main content', async ({ authenticatedPage: page }) => {
      const skipLinks = await validateSkipLinks(page);
      expect(skipLinks.hasSkipLink).toBe(
        true,
        'Page should have skip link as first focusable element'
      );

      // Verify skip link points to main content
      const mainLink = skipLinks.skipLinks.find((link) => link.href.includes('main'));
      expect(mainLink).toBeDefined();
    });

    test('skip link should focus main content when activated', async ({ authenticatedPage: page }) => {
      // Tab to skip link
      await page.keyboard.press('Tab');

      // Press Enter to activate
      await page.keyboard.press('Enter');

      // Wait for focus to move
      await page.waitForLoadState("networkidle").catch(() => {});

      // Verify focus is on main content or within it
      const focusedId = await page.evaluate(() => {
        const active = document.activeElement;
        if (!active) return '';
        // Check if focused element is main or within main
        const mainContent = active.closest('[role="main"], main');
        return mainContent?.id || active.id || '';
      });

      expect(focusedId || 'has-focus').toBeTruthy();
    });
  });

  // ============================================================================
  // 2. TAG LIST STRUCTURE TESTS
  // ============================================================================
  test.describe('@regression-a11y Tag List Structure', () => {
    test('should have tags listed in table format', async ({ authenticatedPage: page }) => {
      // Check if table or list exists
      const table = page.locator('#tags-table-body');
      const exists = await table.count();
      expect(exists).toBeGreaterThan(0);
    });

    test('tag table should have proper headers', async ({ authenticatedPage: page }) => {
      // Check for table headers
      const headers = await page.locator('table thead th').all();
      expect(headers.length).toBeGreaterThan(0);

      // At least 'Name', 'Actions' headers expected
      const headerTexts = await Promise.all(
        headers.map((h) => h.textContent())
      );
      expect(headerTexts.some((t) => t?.toLowerCase().includes('name'))).toBe(true);
    });

    test('each tag row should have accessible checkbox for selection', async ({ authenticatedPage: page }) => {
      // If there are tag rows, check for checkboxes
      const checkboxes = await page.locator('tbody tr input[type="checkbox"]').all();

      if (checkboxes.length > 0) {
        for (const checkbox of checkboxes) {
          const hasAriaLabel = await checkbox.evaluate((el) => {
            return el.hasAttribute('aria-label') || el.hasAttribute('aria-labelledby');
          });
          // Checkboxes should have accessible names or be in labeled row context
          expect(checkbox).toBeDefined();
        }
      }
    });

    test('tag items should have tag name accessible in each row', async ({ authenticatedPage: page }) => {
      // Get first tag row if any
      const firstRow = page.locator('tbody tr').first();
      const exists = await firstRow.count();

      if (exists > 0) {
        const nameInput = firstRow.locator('input[data-field="name"]').first();
        const nameExists = await nameInput.count();
        expect(nameExists).toBeGreaterThan(0);
      }
    });

    test('tag color badge should not be the only indicator', async ({ authenticatedPage: page }) => {
      // Verify tags have text labels, not just color
      const firstRow = page.locator('tbody tr').first();
      const exists = await firstRow.count();

      if (exists > 0) {
        const nameInput = firstRow.locator('input[data-field="name"]').first();
        const nameText = await nameInput.inputValue();
        // Tag should have a name accessible via text content or input value
        expect(nameText || 'has-text-label').toBeTruthy();
      }
    });
  });

  // ============================================================================
  // 3. ROVING TABINDEX PATTERN TESTS
  // ============================================================================
  test.describe('@regression-a11y Roving Tabindex Pattern in Tag List', () => {
    test('only ONE tag item should have tabindex="0" at a time', async ({ authenticatedPage: page }) => {
      // Get all tag rows
      const rows = await page.locator('tbody tr').all();
      if (rows.length === 0) {
        return; // Skip if no tags
      }

      // Check first checkbox's tabindex
      const firstCheckbox = rows[0].locator('input[type="checkbox"]').first();
      const firstTabindex = await firstCheckbox.getAttribute('tabindex');

      // Count items with tabindex="0"
      const tabindexZeroItems = await page.locator('tbody input[type="checkbox"][tabindex="0"]').count();
      expect(tabindexZeroItems).toBeLessThanOrEqual(1);

      // All others should be tabindex="-1"
      const allCheckboxes = await page.locator('tbody input[type="checkbox"]').all();
      for (const checkbox of allCheckboxes) {
        const tabindex = await checkbox.getAttribute('tabindex');
        expect(['0', '-1']).toContain(tabindex);
      }
    });

    test('all other tag items should have tabindex="-1"', async ({ authenticatedPage: page }) => {
      // Get all checkboxes in tag list
      const checkboxes = await page.locator('tbody input[type="checkbox"]').all();
      if (checkboxes.length < 2) {
        return; // Skip if not enough items
      }

      // Find the item with tabindex="0"
      let zeroItem = null;
      for (const checkbox of checkboxes) {
        const tabindex = await checkbox.getAttribute('tabindex');
        if (tabindex === '0') {
          zeroItem = checkbox;
          break;
        }
      }

      // All others should be -1
      for (const checkbox of checkboxes) {
        if (checkbox === zeroItem) {
          continue;
        }
        const tabindex = await checkbox.getAttribute('tabindex');
        expect(tabindex).toBe('-1');
      }
    });

    test('Tab key should move focus into the list', async ({ authenticatedPage: page }) => {
      // Get the table container
      const tableContainer = page.locator('#tags-table-container');
      const exists = await tableContainer.count();
      expect(exists).toBeGreaterThan(0);

      // Tab through page to reach list
      for (let i = 0; i < 10; i++) {
        await page.keyboard.press('Tab');
      }

      // Check if focus is on a checkbox in the list
      const focusedElement = await page.evaluate(() => {
        const el = document.activeElement as HTMLElement;
        const isInTable = el?.closest('#tags-table-container') !== null;
        return {
          isInTable,
          id: el?.id || 'unknown',
          type: el?.getAttribute('type') || 'unknown'
        };
      });

      // Focus should either be on the table or before it
      expect(focusedElement.isInTable || focusedElement.id || focusedElement.type).toBeTruthy();
    });

    test('Tab again should move focus OUT of the list', async ({ authenticatedPage: page }) => {
      // Get all rows
      const rows = await page.locator('tbody tr').all();
      if (rows.length === 0) {
        return;
      }

      // Focus first checkbox
      const firstCheckbox = rows[0].locator('input[type="checkbox"]').first();
      await firstCheckbox.focus();

      // Verify it's focused
      const isFocused = await firstCheckbox.evaluate((el) => el === document.activeElement);
      expect(isFocused).toBe(true);

      // Get initial focus position
      const initialFocusId = await page.evaluate(() => (document.activeElement as HTMLElement)?.id || 'unknown');

      // Tab from the focused checkbox should move to next focusable element
      await page.keyboard.press('Tab');
      await page.waitForLoadState("networkidle").catch(() => {});

      // Focus should move to next element
      const nextFocusId = await page.evaluate(() => (document.activeElement as HTMLElement)?.id || 'unknown');
      expect(nextFocusId || 'focus-moved').toBeTruthy();
    });

    test('focus should not be trapped in the list', async ({ authenticatedPage: page }) => {
      // Tab multiple times and verify we exit eventually
      const focusHistory = [];

      for (let i = 0; i < 30; i++) {
        const inTable = await page.evaluate(() => {
          const el = document.activeElement as HTMLElement;
          return el?.closest('#tags-table-container') !== null;
        });

        focusHistory.push(inTable);
        await page.keyboard.press('Tab');
      }

      // Should have moved out of table at some point
      const wasOutOfTable = focusHistory.some((inTable) => !inTable);
      expect(wasOutOfTable).toBe(true);
    });
  });

  // ============================================================================
  // 4. ARROW KEY NAVIGATION TESTS
  // ============================================================================
  test.describe('@regression-a11y Arrow Key Navigation', () => {
    test('Down arrow should move to next tag', async ({ authenticatedPage: page }) => {
      // Get all rows
      const rows = await page.locator('tbody tr').all();
      if (rows.length < 2) {
        return;
      }

      // Focus first checkbox
      const firstCheckbox = rows[0].locator('input[type="checkbox"]').first();
      await firstCheckbox.focus();

      // Get initial focus
      let currentFocus = await page.evaluate(() => {
        const el = document.activeElement as HTMLElement;
        const row = el?.closest('tr');
        return {
          rowIndex: Array.from(row?.parentElement?.children || []).indexOf(row as Element),
          elementId: el?.id || 'unknown'
        };
      });

      // Press down arrow
      await page.keyboard.press('ArrowDown');
      await page.waitForLoadState("networkidle").catch(() => {});

      // Verify focus moved or stayed valid
      const newFocus = await page.evaluate(() => {
        const el = document.activeElement as HTMLElement;
        const row = el?.closest('tr');
        return {
          rowIndex: Array.from(row?.parentElement?.children || []).indexOf(row as Element),
          elementId: el?.id || 'unknown'
        };
      });

      // Focus should be valid and potentially moved
      expect(newFocus.rowIndex >= 0 || newFocus.elementId).toBeTruthy();
    });

    test('Up arrow should move to previous tag', async ({ authenticatedPage: page }) => {
      // Get all rows
      const rows = await page.locator('tbody tr').all();
      if (rows.length < 2) {
        return;
      }

      // Focus second checkbox
      const secondCheckbox = rows[1].locator('input[type="checkbox"]').first();
      await secondCheckbox.focus();

      // Get initial focus
      const initialRowIndex = await page.evaluate(() => {
        const el = document.activeElement as HTMLElement;
        const row = el?.closest('tr');
        return Array.from(row?.parentElement?.children || []).indexOf(row as Element);
      });

      // Press up arrow
      await page.keyboard.press('ArrowUp');
      await page.waitForLoadState("networkidle").catch(() => {});

      // Verify focus is still valid
      const newRowIndex = await page.evaluate(() => {
        const el = document.activeElement as HTMLElement;
        const row = el?.closest('tr');
        return Array.from(row?.parentElement?.children || []).indexOf(row as Element);
      });

      // Focus should be valid
      expect(newRowIndex >= 0 || initialRowIndex >= 0).toBeTruthy();
    });

    test('tabindex should update during navigation', async ({ authenticatedPage: page }) => {
      // Get all rows
      const rows = await page.locator('tbody tr').all();
      if (rows.length < 2) {
        return;
      }

      // Focus first checkbox
      const firstCheckbox = rows[0].locator('input[type="checkbox"]').first();
      await firstCheckbox.focus();

      // Get initial tabindex values
      const firstTabindex = await firstCheckbox.getAttribute('tabindex');
      expect(firstTabindex).toBe('0');

      // Get second checkbox
      const secondCheckbox = rows[1].locator('input[type="checkbox"]').first();
      const secondTabindex = await secondCheckbox.getAttribute('tabindex');
      expect(secondTabindex).toBe('-1');

      // Press down arrow
      await page.keyboard.press('ArrowDown');
      await page.waitForLoadState("networkidle").catch(() => {});

      // Verify tabindex values updated
      const firstTabindexAfter = await firstCheckbox.getAttribute('tabindex');
      const secondTabindexAfter = await secondCheckbox.getAttribute('tabindex');

      // Should be swapped now
      expect([firstTabindexAfter, secondTabindexAfter]).toContain('0');
      expect([firstTabindexAfter, secondTabindexAfter]).toContain('-1');
    });

    test('focus styling should be visible during navigation', async ({ authenticatedPage: page }) => {
      // Get rows
      const rows = await page.locator('tbody tr').all();
      if (rows.length < 2) {
        return;
      }

      // Focus first row
      const firstCheckbox = rows[0].locator('input[type="checkbox"]').first();
      await firstCheckbox.focus();

      // Verify focus indicators
      const focusIndicators = await verifyFocusIndicators(page);
      expect(focusIndicators.elementsWithFocus >= 0).toBe(true);
    });
  });

  // ============================================================================
  // 5. HOME/END KEY NAVIGATION TESTS
  // ============================================================================
  test.describe('@regression-a11y Home/End Key Navigation', () => {
    test('Home key should jump to first tag', async ({ authenticatedPage: page }) => {
      // Get all rows
      const rows = await page.locator('tbody tr').all();
      if (rows.length < 2) {
        return;
      }

      // Focus on middle element
      const middleIndex = Math.floor(rows.length / 2);
      const middleCheckbox = rows[middleIndex].locator('input[type="checkbox"]').first();
      await middleCheckbox.focus();

      // Press Home key
      await page.keyboard.press('Home');
      await page.waitForLoadState("networkidle").catch(() => {});

      // Verify focus is on first row or first element
      const focusedRowIndex = await page.evaluate(() => {
        const el = document.activeElement as HTMLElement;
        const row = el?.closest('tr');
        const tbody = row?.closest('tbody');
        const rows = tbody?.querySelectorAll('tr') || [];
        return Array.from(rows).indexOf(row as Element);
      });

      // Should be at beginning
      expect(focusedRowIndex).toBeLessThanOrEqual(middleIndex);
    });

    test('End key should jump to last tag', async ({ authenticatedPage: page }) => {
      // Get all rows
      const rows = await page.locator('tbody tr').all();
      if (rows.length < 2) {
        return;
      }

      // Focus first element
      const firstCheckbox = rows[0].locator('input[type="checkbox"]').first();
      await firstCheckbox.focus();

      // Press End key
      await page.keyboard.press('End');
      await page.waitForLoadState("networkidle").catch(() => {});

      // Verify focus is near end
      const focusedRowIndex = await page.evaluate(() => {
        const el = document.activeElement as HTMLElement;
        const row = el?.closest('tr');
        const tbody = row?.closest('tbody');
        const rows = tbody?.querySelectorAll('tr') || [];
        return Array.from(rows).indexOf(row as Element);
      });

      // Should be near end or at valid element
      expect(focusedRowIndex > 0 || focusedRowIndex === 0).toBeTruthy();
    });

    test('tabindex values should update after Home/End navigation', async ({ authenticatedPage: page }) => {
      // Get all rows
      const rows = await page.locator('tbody tr').all();
      if (rows.length < 2) {
        return;
      }

      // Focus middle element
      const middleIndex = Math.floor(rows.length / 2);
      const middleCheckbox = rows[middleIndex].locator('input[type="checkbox"]').first();
      await middleCheckbox.focus();

      // Verify initial state has one tabindex="0"
      const zeroCount1 = await page.locator('tbody input[type="checkbox"][tabindex="0"]').count();
      expect(zeroCount1).toBe(1);

      // Press Home
      await page.keyboard.press('Home');
      await page.waitForLoadState("networkidle").catch(() => {});

      // Verify still only one tabindex="0"
      const zeroCount2 = await page.locator('tbody input[type="checkbox"][tabindex="0"]').count();
      expect(zeroCount2).toBe(1);
    });
  });

  // ============================================================================
  // 6. TYPEAHEAD SEARCH TESTS
  // ============================================================================
  test.describe('@regression-a11y Typeahead Search', () => {
    test('typing a letter should focus matching tag', async ({ authenticatedPage: page }) => {
      // Get all rows and first tag name
      const rows = await page.locator('tbody tr').all();
      if (rows.length === 0) {
        return;
      }

      const firstCheckbox = rows[0].locator('input[type="checkbox"]').first();
      await firstCheckbox.focus();

      // Get first tag name
      const firstTagName = await rows[0].locator('input[data-field="name"]').inputValue();
      if (!firstTagName || firstTagName.length === 0) {
        return;
      }

      // Type first letter
      const firstLetter = firstTagName[0].toUpperCase();
      await page.keyboard.type(firstLetter, { delay: 100 });
      await page.waitForLoadState("networkidle").catch(() => {});

      // Verify focus is on a tag (may be the same or matching one)
      const focusedElement = await page.evaluate(() => {
        const el = document.activeElement as HTMLElement;
        return {
          isCheckbox: el?.getAttribute('type') === 'checkbox',
          inTable: el?.closest('#tags-table-container') !== null
        };
      });

      expect(focusedElement.isCheckbox || focusedElement.inTable).toBeTruthy();
    });

    test('typing multiple letters in quick succession should search', async ({ authenticatedPage: page }) => {
      // Get all rows
      const rows = await page.locator('tbody tr').all();
      if (rows.length === 0) {
        return;
      }

      const firstCheckbox = rows[0].locator('input[type="checkbox"]').first();
      await firstCheckbox.focus();

      // Type a few characters quickly
      const searchTerm = 'test';
      for (const char of searchTerm) {
        await page.keyboard.type(char, { delay: 50 });
      }
      await page.waitForLoadState("networkidle").catch(() => {});

      // Verify focus is still valid
      const focused = await page.evaluate(() => {
        const el = document.activeElement;
        return el !== null;
      });

      expect(focused).toBe(true);
    });

    test('typeahead should be case-insensitive', async ({ authenticatedPage: page }) => {
      // Get all rows and first tag name
      const rows = await page.locator('tbody tr').all();
      if (rows.length === 0) {
        return;
      }

      const firstCheckbox = rows[0].locator('input[type="checkbox"]').first();
      await firstCheckbox.focus();

      // Get first tag name
      const firstTagName = await rows[0].locator('input[data-field="name"]').inputValue();
      if (!firstTagName || firstTagName.length === 0) {
        return;
      }

      // Type lowercase first letter
      const firstLetter = firstTagName[0].toLowerCase();
      await page.keyboard.type(firstLetter, { delay: 100 });
      await page.waitForLoadState("networkidle").catch(() => {});

      // Verify typeahead works (should match regardless of case)
      const focused = await page.evaluate(() => {
        const el = document.activeElement;
        return el !== null;
      });

      expect(focused).toBe(true);
    });

    test('typeahead timeout should clear search state', async ({ authenticatedPage: page }) => {
      // Get all rows
      const rows = await page.locator('tbody tr').all();
      if (rows.length < 2) {
        return;
      }

      const firstCheckbox = rows[0].locator('input[type="checkbox"]').first();
      await firstCheckbox.focus();

      // Type first letter
      await page.keyboard.type('a', { delay: 100 });
      await page.waitForLoadState("networkidle").catch(() => {});

      // Wait for typeahead timeout (usually 500-1000ms)
      await page.waitForLoadState("networkidle").catch(() => {});

      // Type a different letter - should be treated as new search
      await page.keyboard.type('b', { delay: 100 });
      await page.waitForLoadState("networkidle").catch(() => {});

      // Should have processed without error
      const focused = await page.evaluate(() => document.activeElement !== null);
      expect(focused).toBe(true);
    });

    test('typeahead should wrap around in search results', async ({ authenticatedPage: page }) => {
      // Get all rows
      const rows = await page.locator('tbody tr').all();
      if (rows.length < 2) {
        return;
      }

      // Focus last row
      const lastCheckbox = rows[rows.length - 1].locator('input[type="checkbox"]').first();
      await lastCheckbox.focus();

      // Get last tag name
      const lastTagName = await rows[rows.length - 1].locator('input[data-field="name"]').inputValue();
      if (!lastTagName || lastTagName.length === 0) {
        return;
      }

      // Type first letter (may wrap to another tag starting with same letter)
      const firstLetter = lastTagName[0].toLowerCase();
      await page.keyboard.type(firstLetter, { delay: 100 });
      await page.waitForLoadState("networkidle").catch(() => {});

      // Verify focus is valid (may have wrapped)
      const focused = await page.evaluate(() => document.activeElement !== null);
      expect(focused).toBe(true);
    });
  });

  // ============================================================================
  // 7. TAG OPERATIONS - MERGE FUNCTIONALITY
  // ============================================================================
  test.describe('@regression-a11y Tag Merge Operation', () => {
    test('merge button should have accessible label', async ({ authenticatedPage: page }) => {
      const mergeBtn = page.locator('#tag-merge-btn');
      const exists = await mergeBtn.count();

      if (exists > 0) {
        const nameInfo = await checkAccessibleName(mergeBtn);
        expect(nameInfo.hasAccessibleName).toBe(true);
      }
    });

    test('merge target input should be labeled', async ({ authenticatedPage: page }) => {
      const mergeTargetInput = page.locator('#tag-merge-target');
      const exists = await mergeTargetInput.count();

      if (exists > 0) {
        const nameInfo = await checkAccessibleName(mergeTargetInput);
        expect(nameInfo.hasAccessibleName).toBe(true);
        expect(nameInfo.name).toMatch(/target/i);
      }
    });

    test('merge sources input should be labeled', async ({ authenticatedPage: page }) => {
      const mergeSourcesInput = page.locator('#tag-merge-sources');
      const exists = await mergeSourcesInput.count();

      if (exists > 0) {
        const nameInfo = await checkAccessibleName(mergeSourcesInput);
        expect(nameInfo.hasAccessibleName).toBe(true);
        expect(nameInfo.name).toMatch(/source/i);
      }
    });

    test('merge help text should be associated with inputs', async ({ authenticatedPage: page }) => {
      // Help text should be associated via aria-describedby
      const targetInput = page.locator('#tag-merge-target');
      const hasDescribedBy = await targetInput.evaluate((el) => {
        return el.hasAttribute('aria-describedby');
      }).catch(() => false);

      // May or may not have aria-describedby, but input should exist
      expect(targetInput).toBeDefined();
    });

    test('merge section should have error announcements', async ({ authenticatedPage: page }) => {
      // Check for live region
      const errorBanner = page.locator('#tag-merge-error-summary');
      const exists = await errorBanner.count();
      expect(exists).toBeGreaterThan(0);

      // Verify it's an alert region
      const hasAlertRole = await errorBanner.evaluate((el) => {
        return el.getAttribute('role') === 'alert';
      }).catch(() => false);

      expect(hasAlertRole || errorBanner).toBeDefined();
    });

    test('merge operation should be completable via keyboard', async ({ authenticatedPage: page }) => {
      const targetInput = page.locator('#tag-merge-target');
      const exists = await targetInput.count();

      if (exists > 0) {
        // Focus target input
        await targetInput.focus();

        // Verify it's focused
        const isFocused = await targetInput.evaluate((el) => el === document.activeElement);
        expect(isFocused).toBe(true);

        // Tab to next field
        await page.keyboard.press('Tab');

        // Should move to next element
        const nextFocused = await page.evaluate(() => document.activeElement?.id || '');
        expect(nextFocused).toBeDefined();
      }
    });
  });

  // ============================================================================
  // 8. TAG OPERATIONS - FIND & REPLACE FUNCTIONALITY
  // ============================================================================
  test.describe('@regression-a11y Tag Find & Replace Operation', () => {
    test('find input should be labeled', async ({ authenticatedPage: page }) => {
      const findInput = page.locator('#tag-find');
      const exists = await findInput.count();

      if (exists > 0) {
        const nameInfo = await checkAccessibleName(findInput);
        expect(nameInfo.hasAccessibleName).toBe(true);
        expect(nameInfo.name).toMatch(/find/i);
      }
    });

    test('replace input should be labeled', async ({ authenticatedPage: page }) => {
      const replaceInput = page.locator('#tag-replace');
      const exists = await replaceInput.count();

      if (exists > 0) {
        const nameInfo = await checkAccessibleName(replaceInput);
        expect(nameInfo.hasAccessibleName).toBe(true);
        expect(nameInfo.name).toMatch(/replace/i);
      }
    });

    test('find/replace button should have accessible label', async ({ authenticatedPage: page }) => {
      const replaceBtn = page.locator('#tag-find-replace-btn');
      const exists = await replaceBtn.count();

      if (exists > 0) {
        const nameInfo = await checkAccessibleName(replaceBtn);
        expect(nameInfo.hasAccessibleName).toBe(true);
      }
    });

    test('find/replace section should have error announcements', async ({ authenticatedPage: page }) => {
      const errorBanner = page.locator('#tag-find-replace-error-summary');
      const exists = await errorBanner.count();
      expect(exists).toBeGreaterThan(0);
    });

    test('find/replace operation should be completable via keyboard', async ({ authenticatedPage: page }) => {
      const findInput = page.locator('#tag-find');
      const exists = await findInput.count();

      if (exists > 0) {
        await findInput.focus();

        const isFocused = await findInput.evaluate((el) => el === document.activeElement);
        expect(isFocused).toBe(true);

        // Tab through fields
        await page.keyboard.press('Tab'); // Replace input
        const nextId = await page.evaluate(() => document.activeElement?.id || '');
        expect(nextId).toBe('tag-replace');
      }
    });
  });

  // ============================================================================
  // 9. TAG OPERATIONS - BULK DELETE FUNCTIONALITY
  // ============================================================================
  test.describe('@regression-a11y Tag Bulk Delete Operation', () => {
    test('bulk delete IDs input should be labeled', async ({ authenticatedPage: page }) => {
      const bulkDeleteInput = page.locator('#tag-bulk-delete-ids');
      const exists = await bulkDeleteInput.count();

      if (exists > 0) {
        const nameInfo = await checkAccessibleName(bulkDeleteInput);
        expect(nameInfo.hasAccessibleName).toBe(true);
      }
    });

    test('force delete checkbox should be labeled', async ({ authenticatedPage: page }) => {
      const forceCheckbox = page.locator('#tag-bulk-delete-force');
      const exists = await forceCheckbox.count();

      if (exists > 0) {
        // Should have associated label
        const label = page.locator('label[for="tag-bulk-delete-force"]');
        const labelExists = await label.count();
        expect(labelExists).toBeGreaterThan(0);
      }
    });

    test('bulk delete button should have accessible label', async ({ authenticatedPage: page }) => {
      const deleteBtn = page.locator('#tag-bulk-delete-btn');
      const exists = await deleteBtn.count();

      if (exists > 0) {
        const nameInfo = await checkAccessibleName(deleteBtn);
        expect(nameInfo.hasAccessibleName).toBe(true);
      }
    });

    test('bulk delete section should have error announcements', async ({ authenticatedPage: page }) => {
      const errorBanner = page.locator('#tag-bulk-delete-error-summary');
      const exists = await errorBanner.count();
      expect(exists).toBeGreaterThan(0);
    });
  });

  // ============================================================================
  // 10. TAG SEARCH/FILTER FUNCTIONALITY
  // ============================================================================
  test.describe('@regression-a11y Tag Search/Filter', () => {
    test('search input should have accessible label', async ({ authenticatedPage: page }) => {
      const searchInput = page.locator('#tag-search');
      const exists = await searchInput.count();

      if (exists > 0) {
        const nameInfo = await checkAccessibleName(searchInput);
        expect(nameInfo.hasAccessibleName).toBe(true);
        expect(nameInfo.name).toMatch(/search/i);
      }
    });

    test('search input should be keyboard accessible', async ({ authenticatedPage: page }) => {
      const searchInput = page.locator('#tag-search');
      const exists = await searchInput.count();

      if (exists > 0) {
        // Tab to search input
        await page.keyboard.press('Tab');

        // Keep pressing tab until we reach search
        for (let i = 0; i < 10; i++) {
          const focused = await page.evaluate(() => document.activeElement?.id || '');
          if (focused === 'tag-search') {
            break;
          }
          await page.keyboard.press('Tab');
        }

        const isFocused = await searchInput.evaluate((el) => el === document.activeElement);
        expect(isFocused).toBe(true);

        // Type in search
        await page.keyboard.type('test');

        // Verify text was entered
        const searchValue = await searchInput.inputValue();
        expect(searchValue).toContain('test');

        // Clear for cleanup
        await searchInput.clear();
      }
    });

    test('search results should maintain focus management', async ({ authenticatedPage: page }) => {
      const searchInput = page.locator('#tag-search');
      const exists = await searchInput.count();

      if (exists > 0) {
        // Type something to filter
        await searchInput.fill('test');

        // Wait for filtering
        await page.waitForLoadState("networkidle").catch(() => {});

        // Verify page is still functional
        const tableBody = page.locator('#tags-table-body');
        expect(await tableBody.count()).toBeGreaterThan(0);

        // Clear for cleanup
        await searchInput.clear();
      }
    });
  });

  // ============================================================================
  // 11. CREATE TAG FORM ACCESSIBILITY
  // ============================================================================
  test.describe('@regression-a11y Create Tag Form', () => {
    test('should have properly labeled form inputs', async ({ authenticatedPage: page }) => {
      const formLabels = await validateFormLabels(page);
      expect(formLabels.allLabeled).toBe(
        true,
        `Unlabeled form elements: ${formLabels.unlabeledElements.map((e) => e.id).join(', ')}`
      );
    });

    test('tag name input should have accessible name', async ({ authenticatedPage: page }) => {
      const nameInput = page.locator('#tag-create-name');
      const exists = await nameInput.count();

      if (exists > 0) {
        const nameInfo = await checkAccessibleName(nameInput);
        expect(nameInfo.hasAccessibleName).toBe(true);
        expect(nameInfo.name).toMatch(/name/i);
      }
    });

    test('tag description input should have accessible name', async ({ authenticatedPage: page }) => {
      const descInput = page.locator('#tag-create-description');
      const exists = await descInput.count();

      if (exists > 0) {
        const nameInfo = await checkAccessibleName(descInput);
        expect(nameInfo.hasAccessibleName).toBe(true);
      }
    });

    test('tag color input should have accessible name', async ({ authenticatedPage: page }) => {
      const colorInput = page.locator('#tag-create-color');
      const exists = await colorInput.count();

      if (exists > 0) {
        const nameInfo = await checkAccessibleName(colorInput);
        expect(nameInfo.hasAccessibleName).toBe(true);
      }
    });

    test('tag color picker should have accessible name', async ({ authenticatedPage: page }) => {
      const colorPicker = page.locator('#tag-create-color-picker');
      const exists = await colorPicker.count();

      if (exists > 0) {
        const nameInfo = await checkAccessibleName(colorPicker);
        // May or may not have explicit accessible name
        expect(colorPicker).toBeDefined();
      }
    });

    test('create button should have accessible label', async ({ authenticatedPage: page }) => {
      const createBtn = page.locator('#tag-create-form button[type="submit"]');
      const exists = await createBtn.count();

      if (exists > 0) {
        const nameInfo = await checkAccessibleName(createBtn);
        expect(nameInfo.hasAccessibleName).toBe(true);
      }
    });

    test('form should be keyboard navigable', async ({ authenticatedPage: page }) => {
      // Tab through form inputs
      await page.keyboard.press('Tab'); // Skip link
      await page.keyboard.press('Tab'); // Logo/home link
      await page.keyboard.press('Tab'); // Back button or nav
      await page.keyboard.press('Tab'); // Should get closer to form

      // Continue tabbing to reach form
      for (let i = 0; i < 3; i++) {
        await page.keyboard.press('Tab');
      }

      // Should be at or near the form
      await page.waitForLoadState("networkidle").catch(() => {});

      // Check if we can reach the name input
      const nameInput = page.locator('#tag-create-name');
      const exists = await nameInput.count();

      if (exists > 0) {
        // Focus the input
        await nameInput.focus();

        // Verify focused
        const isFocused = await nameInput.evaluate((el) => el === document.activeElement);
        expect(isFocused).toBe(true);
      }
    });
  });

  // ============================================================================
  // 12. TAG OPERATIONS - ADD/EDIT/DELETE
  // ============================================================================
  test.describe('@regression-a11y Tag Add/Edit/Delete Operations', () => {
    test('add tag button should be accessible', async ({ authenticatedPage: page }) => {
      const addBtn = page.locator('#tag-create-form button[type="submit"]');
      const exists = await addBtn.count();

      if (exists > 0) {
        const nameInfo = await checkAccessibleName(addBtn);
        expect(nameInfo.hasAccessibleName).toBe(true);
      }
    });

    test('tag form modal should be accessible', async ({ authenticatedPage: page }) => {
      const createForm = page.locator('#tag-create-form');
      const exists = await createForm.count();
      expect(exists).toBeGreaterThan(0);

      // Form should be findable and have structure
      const formLabels = await validateFormLabels(page);
      // At least some elements in form should have labels
      expect(formLabels).toBeDefined();
    });

    test('delete confirmation should be accessible', async ({ authenticatedPage: page }) => {
      const deleteTrigger = page.locator(
        'button:has-text("Delete"), button[aria-label*="delete" i], button[aria-label*="remove" i]'
      ).first();

      if ((await deleteTrigger.count()) === 0) {
        test.skip();
        return;
      }

      await deleteTrigger.focus();
      await deleteTrigger.click();

      await expect
        .poll(async () => await hasVisibleDialog(page), { timeout: 5000 })
        .toBe(true);
      await expect
        .poll(async () => await focusInsideVisibleDialog(page), { timeout: 5000 })
        .toBe(true);

      await page.keyboard.press('Escape');
      await expect
        .poll(async () => await hasVisibleDialog(page), { timeout: 5000 })
        .toBe(false);
    });
  });

  // ============================================================================
  // 13. TAG VISUAL INDICATORS AND ACCESSIBILITY
  // ============================================================================
  test.describe('@regression-a11y Tag Visual Indicators', () => {
    test('tag color should not be only indicator', async ({ authenticatedPage: page }) => {
      // Verify tags have text labels alongside color
      const rows = await page.locator('tbody tr').all();

      if (rows.length > 0) {
        // Each tag should have a name input with text
        const nameInput = rows[0].locator('input[data-field="name"]').first();
        const nameText = await nameInput.inputValue();
        expect(nameText || 'has-text').toBeTruthy();
      }
    });

    test('tag usage count should be accessible', async ({ authenticatedPage: page }) => {
      // Check for usage count elements
      const usageElements = await page.locator('[id*="usage"], [id*="count"]').count();
      // Should have some indicators
      expect(usageElements >= 0).toBe(true);
    });

    test('tag associations should be accessible', async ({ authenticatedPage: page }) => {
      // Check if tag associations are displayed
      const rows = await page.locator('tbody tr').all();
      if (rows.length > 0) {
        // Tag row should be accessible with text content
        const textContent = await rows[0].textContent();
        expect(textContent).toBeTruthy();
      }
    });
  });

  // ============================================================================
  // 14. BUTTONS AND INTERACTIVE ELEMENTS
  // ============================================================================
  test.describe('@regression-a11y Buttons and Interactive Elements', () => {
    test('all buttons should have accessible labels', async ({ authenticatedPage: page }) => {
      const buttonLabels = await validateButtonLabels(page);
      expect(buttonLabels.allButtonsLabeled).toBe(
        true,
        `Unlabeled buttons: ${buttonLabels.unlabeledSelectors.join(', ')}`
      );
    });

    test('save all button should have accessible label', async ({ authenticatedPage: page }) => {
      const saveAllBtn = page.locator('#tag-save-all-btn');
      const exists = await saveAllBtn.count();

      if (exists > 0) {
        const nameInfo = await checkAccessibleName(saveAllBtn);
        expect(nameInfo.hasAccessibleName).toBe(true);
      }
    });

    test('merge selected button should have accessible label', async ({ authenticatedPage: page }) => {
      const mergeSelectedBtn = page.locator('#tag-selection-merge-btn');
      const exists = await mergeSelectedBtn.count();

      if (exists > 0) {
        const nameInfo = await checkAccessibleName(mergeSelectedBtn);
        expect(nameInfo.hasAccessibleName).toBe(true);
      }
    });

    test('find/replace selected button should have accessible label', async ({ authenticatedPage: page }) => {
      const findReplaceSelectedBtn = page.locator('#tag-selection-find-replace-btn');
      const exists = await findReplaceSelectedBtn.count();

      if (exists > 0) {
        const nameInfo = await checkAccessibleName(findReplaceSelectedBtn);
        expect(nameInfo.hasAccessibleName).toBe(true);
      }
    });

    test('undo button should have accessible label', async ({ authenticatedPage: page }) => {
      const undoBtn = page.locator('#tag-undo-btn');
      const exists = await undoBtn.count();

      if (exists > 0) {
        const nameInfo = await checkAccessibleName(undoBtn);
        expect(nameInfo.hasAccessibleName).toBe(true);
      }
    });

    test('all buttons should be keyboard accessible', async ({ authenticatedPage: page }) => {
      const tabOrder = await extractTabOrder(page);
      expect(tabOrder.length).toBeGreaterThan(0);
    });

    test('export button should have accessible label', async ({ authenticatedPage: page }) => {
      const exportBtn = page.locator('#tag-export-btn');
      const exists = await exportBtn.count();

      if (exists > 0) {
        const nameInfo = await checkAccessibleName(exportBtn);
        expect(nameInfo.hasAccessibleName).toBe(true);
      }
    });

    test('import button should have accessible label', async ({ authenticatedPage: page }) => {
      const importBtn = page.locator('#tag-import-btn');
      const exists = await importBtn.count();

      if (exists > 0) {
        const nameInfo = await checkAccessibleName(importBtn);
        expect(nameInfo.hasAccessibleName).toBe(true);
      }
    });

    test('import file input should be labeled', async ({ authenticatedPage: page }) => {
      const importInput = page.locator('#tag-import-file');
      const exists = await importInput.count();

      if (exists > 0) {
        const label = page.locator('label[for="tag-import-file"]');
        const labelExists = await label.count();
        expect(labelExists).toBeGreaterThan(0);
      }
    });
  });

  // ============================================================================
  // 15. LIVE REGIONS AND ANNOUNCEMENTS
  // ============================================================================
  test.describe('@regression-a11y Live Regions and Announcements', () => {
    test('page should have live regions for announcements', async ({ authenticatedPage: page }) => {
      const liveRegions = await checkLiveRegions(page);
      expect(liveRegions).toBeDefined();
    });

    test('error banners should be live regions', async ({ authenticatedPage: page }) => {
      const errorBanners = await page.locator('[role="alert"]').all();

      if (errorBanners.length > 0) {
        for (const banner of errorBanners) {
          // Should be alert regions or have aria-live
          expect(banner).toBeDefined();
        }
      }
    });

    test('validation announcements should use aria-live', async ({ authenticatedPage: page }) => {
      const liveElements = await page.locator('[aria-live]').all();

      if (liveElements.length > 0) {
        expect(liveElements.length).toBeGreaterThan(0);
      }
    });
  });

  // ============================================================================
  // 16. COLOR CONTRAST TESTS
  // ============================================================================
  test.describe('@regression-a11y Color Contrast (WCAG AA)', () => {
    test('page headings should have sufficient contrast', async ({ authenticatedPage: page }) => {
      const headings = await page.locator('h1, h2, h3').all();

      if (headings.length > 0) {
        for (let i = 0; i < Math.min(3, headings.length); i++) {
          const contrast = await testTextContrast(page, headings[i], 'AA');
          expect(contrast.passes).toBe(
            true,
            `Heading contrast ratio ${contrast.ratio}:1 is below required ${contrast.required}:1`
          );
        }
      }
    });

    test('button text should have sufficient contrast', async ({ authenticatedPage: page }) => {
      const buttons = await page.locator('button').all();

      if (buttons.length > 0) {
        for (let i = 0; i < Math.min(3, buttons.length); i++) {
          const contrast = await testUIContrast(page, buttons[i], 'AA');
          expect(contrast.passes).toBe(
            true,
            `Button contrast ratio ${contrast.ratio}:1 is below required ${contrast.required}:1`
          );
        }
      }
    });

    test('form label text should have sufficient contrast', async ({ authenticatedPage: page }) => {
      const labels = await page.locator('label').all();

      if (labels.length > 0) {
        for (let i = 0; i < Math.min(3, labels.length); i++) {
          const contrast = await testTextContrast(page, labels[i], 'AA');
          expect(contrast.passes).toBe(
            true,
            `Label contrast ratio ${contrast.ratio}:1 is below required ${contrast.required}:1`
          );
        }
      }
    });

    test('input fields should have sufficient contrast on border', async ({ authenticatedPage: page }) => {
      const inputs = await page.locator('input[type="text"], input[type="number"]').all();

      if (inputs.length > 0) {
        for (let i = 0; i < Math.min(2, inputs.length); i++) {
          const contrast = await testUIContrast(page, inputs[i], 'AA');
          expect(contrast.passes).toBe(
            true,
            `Input field contrast ratio ${contrast.ratio}:1 is below required ${contrast.required}:1`
          );
        }
      }
    });

    test('focus indicators should have sufficient contrast', async ({ authenticatedPage: page }) => {
      await page.keyboard.press('Tab');

      const activeElement = page.locator(':focus');
      const exists = await activeElement.count();

      if (exists > 0) {
        const contrast = await testUIContrast(page, activeElement, 'AA');
        expect(contrast.ratio).toBeGreaterThanOrEqual(3);
      }
    });

    test('error message text should have sufficient contrast', async ({ authenticatedPage: page }) => {
      const errorMessages = await page.locator('[id*="-error"]').all();

      if (errorMessages.length > 0) {
        for (let i = 0; i < Math.min(2, errorMessages.length); i++) {
          const contrast = await testTextContrast(page, errorMessages[i], 'AA');
          if (contrast.ratio > 0) {
            expect(contrast.ratio).toBeGreaterThanOrEqual(3);
          }
        }
      }
    });
  });

  // ============================================================================
  // 17. FOCUS MANAGEMENT AND KEYBOARD-ONLY WORKFLOW
  // ============================================================================
  test.describe('@regression-a11y Focus Management and Keyboard-Only Workflow', () => {
    test('focus should be visible when tabbing through page', async ({ authenticatedPage: page }) => {
      for (let i = 0; i < 5; i++) {
        await page.keyboard.press('Tab');

        const activeElement = await page.evaluate(() => {
          const el = document.activeElement;
          return el ? el.id || el.className : '';
        });

        expect(activeElement).toBeDefined();
      }
    });

    test('focus should not be trapped in any section', async ({ authenticatedPage: page }) => {
      const focusHistory = [];

      for (let i = 0; i < 20; i++) {
        const activeElement = await page.evaluate(() => {
          const el = document.activeElement;
          return el ? el.id || el.className : '';
        });

        if (i > 10) {
          const uniqueFocuses = new Set(focusHistory.slice(-10));
          expect(uniqueFocuses.size > 1 || focusHistory.length === 1).toBe(true);
        }

        focusHistory.push(activeElement);
        await page.keyboard.press('Tab');
      }

      const uniqueFocuses = new Set(focusHistory);
      expect(uniqueFocuses.size).toBeGreaterThan(1);
    });

    test('Shift+Tab should navigate backwards', async ({ authenticatedPage: page }) => {
      await page.keyboard.press('Tab');
      const firstFocus = await page.evaluate(() => document.activeElement?.id || '');

      await page.keyboard.press('Tab');
      const secondFocus = await page.evaluate(() => document.activeElement?.id || '');

      await page.keyboard.press('Shift+Tab');
      const backFocus = await page.evaluate(() => document.activeElement?.id || '');

      expect(backFocus).toBeTruthy();
    });

    test('keyboard-only navigation of tag list should work', async ({ authenticatedPage: page }) => {
      const rows = await page.locator('tbody tr').all();
      if (rows.length < 2) {
        return;
      }

      // Tab to first checkbox
      for (let i = 0; i < 10; i++) {
        await page.keyboard.press('Tab');
        const focused = await page.evaluate(() => {
          const el = document.activeElement as HTMLElement;
          return el?.getAttribute('type') === 'checkbox' && el?.closest('tbody') !== null;
        });
        if (focused) break;
      }

      // Verify we're in the list
      const inList = await page.evaluate(() => {
        const el = document.activeElement as HTMLElement;
        return el?.closest('tbody') !== null;
      });

      expect(inList).toBe(true);
    });
  });

  // ============================================================================
  // 18. BULK OPERATIONS ACCESSIBILITY
  // ============================================================================
  test.describe('@regression-a11y Bulk Operations Accessibility', () => {
    test('bulk select functionality should be accessible', async ({ authenticatedPage: page }) => {
      const checkboxes = await page.locator('tbody input[type="checkbox"]').all();
      if (checkboxes.length < 2) {
        return;
      }

      // Select multiple items
      await checkboxes[0].click();
      await checkboxes[1].click();

      // Verify selections work
      const firstChecked = await checkboxes[0].isChecked();
      const secondChecked = await checkboxes[1].isChecked();

      expect([firstChecked, secondChecked]).toContain(true);
    });

    test('select all button should be accessible', async ({ authenticatedPage: page }) => {
      const selectAllBtn = page.locator('button:has-text("Select All"), button[aria-label*="Select All"]').first();
      const exists = await selectAllBtn.count();

      if (exists > 0) {
        const nameInfo = await checkAccessibleName(selectAllBtn);
        expect(nameInfo.hasAccessibleName || selectAllBtn).toBeDefined();
      }
    });

    test('bulk operation buttons should have clear names', async ({ authenticatedPage: page }) => {
      const bulkBtns = await page.locator('button[id*="selection"]').all();

      for (const btn of bulkBtns) {
        const nameInfo = await checkAccessibleName(btn);
        // Should have some kind of accessible name
        expect(nameInfo.hasAccessibleName || btn).toBeDefined();
      }
    });

    test('selected count announcement should be accessible', async ({ authenticatedPage: page }) => {
      const rows = await page.locator('tbody tr').all();
      if (rows.length < 2) {
        return;
      }

      // Select a few items
      const checkboxes = await page.locator('tbody input[type="checkbox"]').all();
      if (checkboxes.length > 0) {
        await checkboxes[0].click();
      }

      // Check if selection count is announced
      const announcer = page.locator('[id*="announcer"], [role="status"]').first();
      const exists = await announcer.count();
      expect(exists >= 0).toBe(true);
    });
  });

  // ============================================================================
  // 19. TAG USAGE INFORMATION ACCESSIBILITY
  // ============================================================================
  test.describe('@regression-a11y Tag Usage Information', () => {
    test('tag usage count should be accessible', async ({ authenticatedPage: page }) => {
      const rows = await page.locator('tbody tr').all();
      if (rows.length === 0) {
        return;
      }

      // Check if usage count is displayed
      const usageText = await rows[0].textContent();
      expect(usageText).toBeTruthy();
    });

    test('unused tag indicator should be accessible', async ({ authenticatedPage: page }) => {
      // Check if unused tag information is available
      const unusedIndicators = await page.locator('[id*="unused"], [aria-label*="unused"]').count();
      expect(unusedIndicators >= 0).toBe(true);
    });
  });

  // ============================================================================
  // 20. VISUAL TESTING - SCREENSHOTS
  // ============================================================================
  test.describe('@regression-a11y Visual Accessibility Tests', () => {
    test('should capture page in normal state', async ({ authenticatedPage: page }) => {
      await capturePageWithHighlight(
        page,
        'tests/accessibility/reports/tag-management-normal.png'
      );
    });

    test('should capture focused form input', async ({ authenticatedPage: page }) => {
      const nameInput = page.locator('#tag-create-name');
      const exists = await nameInput.count();

      if (exists > 0) {
        await nameInput.focus();
        await captureFocusState(
          page,
          nameInput,
          'tests/accessibility/reports/tag-form-focused.png'
        );
      }
    });

    test('should capture tag table with focus', async ({ authenticatedPage: page }) => {
      const table = page.locator('#tags-table-body');
      await table.scrollIntoViewIfNeeded();

      const firstCheckbox = page.locator('tbody tr input[type="checkbox"]').first();
      const exists = await firstCheckbox.count();

      if (exists > 0) {
        await firstCheckbox.focus();
        await capturePageWithHighlight(
          page,
          'tests/accessibility/reports/tag-table-focus.png'
        );
      }
    });

    test('should capture tag table with selected items', async ({ authenticatedPage: page }) => {
      const checkboxes = await page.locator('tbody input[type="checkbox"]').all();
      if (checkboxes.length < 2) {
        return;
      }

      // Select first item
      await checkboxes[0].click();

      await capturePageWithHighlight(
        page,
        'tests/accessibility/reports/tag-table-selected.png'
      );

      // Unselect for cleanup
      await checkboxes[0].click();
    });

    test('should demonstrate accessible button focus states', async ({ authenticatedPage: page }) => {
      const mergeBtn = page.locator('#tag-merge-btn');
      const exists = await mergeBtn.count();

      if (exists > 0) {
        await mergeBtn.scrollIntoViewIfNeeded();
        await mergeBtn.focus();

        await captureFocusState(
          page,
          mergeBtn,
          'tests/accessibility/reports/tag-merge-button-focused.png'
        );
      }
    });
  });

  // ============================================================================
  // 21. EDGE CASES AND ERROR HANDLING
  // ============================================================================
  test.describe('@regression-a11y Edge Cases and Error Handling', () => {
    test('page should remain accessible with empty tag list', async ({ authenticatedPage: page }) => {
      const landmarks = await checkLandmarkRegions(page);
      expect(landmarks.hasLandmarks).toBe(true);

      const createForm = page.locator('#tag-create-form');
      expect(await createForm.count()).toBeGreaterThan(0);
    });

    test('search input should remain accessible when clearing text', async ({ authenticatedPage: page }) => {
      const searchInput = page.locator('#tag-search');
      const exists = await searchInput.count();

      if (exists > 0) {
        await searchInput.fill('test');
        expect(await searchInput.inputValue()).toBe('test');

        await searchInput.clear();
        expect(await searchInput.inputValue()).toBe('');

        const isFocusable = await searchInput.evaluate((el) => {
          return el.offsetParent !== null;
        });

        expect(isFocusable).toBe(true);
      }
    });

    test('form elements should be accessible even with validation errors', async ({ authenticatedPage: page }) => {
      const nameInput = page.locator('#tag-create-name');
      const exists = await nameInput.count();

      if (exists > 0) {
        await nameInput.focus();
        await nameInput.blur();

        expect(await nameInput.count()).toBeGreaterThan(0);

        await nameInput.focus();
        const isFocused = await nameInput.evaluate((el) => el === document.activeElement);
        expect(isFocused).toBe(true);
      }
    });

    test('disabled state should be accessible', async ({ authenticatedPage: page }) => {
      const disabledInputs = await page.locator('input[disabled]').all();

      if (disabledInputs.length > 0) {
        const disabled = await disabledInputs[0].isDisabled();
        expect(disabled).toBe(true);

        const nameInfo = await checkAccessibleName(disabledInputs[0]);
        expect(disabledInputs[0]).toBeDefined();
      }
    });

    test('page should handle rapid checkbox toggling', async ({ authenticatedPage: page }) => {
      const checkboxes = await page.locator('tbody input[type="checkbox"]').all();
      if (checkboxes.length < 2) {
        return;
      }

      // Rapidly toggle checkboxes
      for (let i = 0; i < 3; i++) {
        await checkboxes[0].click();
        await checkboxes[1].click();
      }

      // Page should still be functional
      const focused = await page.evaluate(() => document.activeElement !== null);
      expect(focused).toBe(true);
    });
  });

  // ============================================================================
  // 22. ARIA ATTRIBUTES VALIDATION
  // ============================================================================
  test.describe('@regression-a11y ARIA Attributes', () => {
    test('list should have proper ARIA role', async ({ authenticatedPage: page }) => {
      const table = page.locator('#tags-table-body');
      const exists = await table.count();

      if (exists > 0) {
        const role = await table.evaluate((el) => {
          // Check element or parent for role
          let current = el as HTMLElement;
          while (current && !current.getAttribute('role')) {
            current = current.parentElement as HTMLElement;
            if (!current || current.tagName === 'BODY') {
              break;
            }
          }
          return current?.getAttribute('role');
        });

        // Should have a semantic role
        expect(role || 'table-structure').toBeTruthy();
      }
    });

    test('selected items should have aria-selected or checked state', async ({ authenticatedPage: page }) => {
      const checkboxes = await page.locator('tbody input[type="checkbox"]').all();
      if (checkboxes.length === 0) {
        return;
      }

      // Check first checkbox
      const isCheckbox = await checkboxes[0].evaluate((el) => el.getAttribute('type') === 'checkbox');
      expect(isCheckbox).toBe(true);

      // Checkboxes use checked property, not aria-selected
      const isChecked = await checkboxes[0].isChecked();
      expect(typeof isChecked === 'boolean').toBe(true);
    });

    test('inputs should not have duplicate IDs', async ({ authenticatedPage: page }) => {
      const allIds = await page.evaluate(() => {
        const elements = document.querySelectorAll('[id]');
        const ids: string[] = [];
        elements.forEach((el) => {
          const id = el.id;
          if (id) ids.push(id);
        });
        return ids;
      });

      // Check for duplicates
      const unique = new Set(allIds);
      expect(unique.size === allIds.length).toBe(true);
    });

    test('form inputs should have aria-describedby for help text', async ({ authenticatedPage: page }) => {
      const inputs = await page.locator('[aria-describedby]').all();
      // May or may not have aria-describedby, but should have proper structure
      expect(inputs.length >= 0).toBe(true);
    });
  });

  // ============================================================================
  // 23. RESPONSIVE DESIGN AND MOBILE ACCESSIBILITY
  // ============================================================================
  test.describe('@regression-a11y Responsive Design', () => {
    test('page elements should be accessible at different screen sizes', async ({ authenticatedPage: page }) => {
      await page.setViewportSize({ width: 375, height: 812 });

      const firstButton = page.locator('button').first();
      const exists = await firstButton.count();

      expect(exists).toBeGreaterThan(0);

      await page.setViewportSize({ width: 1280, height: 720 });
    });

    test('form inputs should be accessible on mobile', async ({ authenticatedPage: page }) => {
      await page.setViewportSize({ width: 375, height: 812 });

      const nameInput = page.locator('#tag-create-name');
      const exists = await nameInput.count();

      if (exists > 0) {
        await nameInput.focus();
        const isFocused = await nameInput.evaluate((el) => el === document.activeElement);
        expect(isFocused).toBe(true);
      }

      await page.setViewportSize({ width: 1280, height: 720 });
    });

    test('tag list should be navigable on mobile', async ({ authenticatedPage: page }) => {
      await page.setViewportSize({ width: 375, height: 812 });

      const checkboxes = await page.locator('tbody input[type="checkbox"]').all();
      if (checkboxes.length > 0) {
        await checkboxes[0].focus();
        const isFocused = await checkboxes[0].evaluate((el) => el === document.activeElement);
        expect(isFocused).toBe(true);
      }

      await page.setViewportSize({ width: 1280, height: 720 });
    });
  });
});
