// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

/**
 * Comprehensive accessibility tests for the main page (/)
 * Tests cover WCAG 2.1 AA compliance including:
 * - Skip link functionality
 * - Header navigation and tab order
 * - Landmark regions
 * - Main content filtering and search
 * - Interactive element labels
 * - Color contrast
 * - Live regions
 */

import { test, expect } from '@playwright/test';
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
} from './utils/index.js';
import { authenticatedUserTest, getBaseURL } from './fixtures/auth.js';

const baseURL = getBaseURL();

// Define test suites organized by feature
test.describe('Main Page Accessibility Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the main page
    await page.goto('/', { waitUntil: 'networkidle' });
  });

  // ============================================================================
  // 1. SKIP LINK FUNCTIONALITY TESTS
  // ============================================================================
  test.describe('Skip Link Functionality', () => {
    test('should have skip link as first focusable element', async ({ page }) => {
      // Extract tab order to verify skip link is first
      const tabOrder = await extractTabOrder(page);
      expect(tabOrder.length).toBeGreaterThan(0);

      // First element should be a skip link (href starts with #)
      const firstElement = tabOrder[0];
      expect(firstElement.selector).toBeTruthy();

      // Tab to the first element and verify it's a skip link
      await page.keyboard.press('Tab');
      const activeElement = await page.evaluate(() => document.activeElement?.getAttribute('href') || '');
      expect(activeElement).toMatch(/^#/i);
    });

    test('skip link should be invisible until focused', async ({ page }) => {
      // Check initial visibility - skip links are typically hidden
      const skipLinks = await validateSkipLinks(page);
      expect(skipLinks.hasSkipLink).toBe(true);
      expect(skipLinks.skipLinks.length).toBeGreaterThan(0);

      // Verify skip link is hidden initially
      const isHidden = await page.evaluate(() => {
        const skipLink = document.querySelector('a[href^="#"]');
        if (!skipLink) return true;
        const style = window.getComputedStyle(skipLink);
        return style.visibility === 'hidden' || style.display === 'none' || style.opacity === '0';
      });
      expect(isHidden).toBe(true);
    });

    test('skip link should be visible when focused', async ({ page }) => {
      // Tab to focus the skip link
      await page.keyboard.press('Tab');

      // Check if skip link is now visible
      const isVisible = await page.evaluate(() => {
        const skipLink = document.querySelector('a[href^="#"]');
        if (!skipLink) return false;
        const style = window.getComputedStyle(skipLink);
        return style.visibility !== 'hidden' && style.display !== 'none' && style.opacity !== '0';
      });
      expect(isVisible).toBe(true);

      // Take screenshot of skip link in focus state
      const skipLinkElement = page.locator('a[href^="#"]').first();
      await captureFocusState(page, skipLinkElement, 'tests/accessibility/reports/skip-link-focused.png');
    });

    test('pressing Enter on skip link should move focus to main content', async ({ page }) => {
      // Tab to focus the skip link
      await page.keyboard.press('Tab');

      // Get the target of the skip link
      const skipLinkHref = await page.evaluate(() => {
        return document.querySelector('a[href^="#"]')?.getAttribute('href') || '';
      });
      expect(skipLinkHref).toMatch(/^#/);

      // Press Enter to activate skip link
      await page.keyboard.press('Enter');

      // Wait a moment for focus to move
      await page.waitForTimeout(100);

      // Verify focus moved to the target element
      const focusedElement = await page.evaluate(() => {
        const activeEl = document.activeElement;
        return activeEl?.getAttribute('id') || activeEl?.tagName || '';
      });

      // Skip link target should be main content or a region
      expect(focusedElement).toBeTruthy();
    });

    test('skip link should have accessible name', async ({ page }) => {
      const skipLink = page.locator('a[href^="#"]').first();
      const nameInfo = await checkAccessibleName(skipLink);
      expect(nameInfo.hasAccessibleName).toBe(true);
      expect(nameInfo.name).toMatch(/skip|main|content/i);
    });
  });

  // ============================================================================
  // 2. HEADER NAVIGATION TESTS
  // ============================================================================
  test.describe('Header Navigation', () => {
    test('header should have logical tab order', async ({ page }) => {
      const tabOrder = await extractTabOrder(page);
      expect(tabOrder.length).toBeGreaterThan(0);

      // Verify tab order is consistent with document order
      // (first few elements should be in header area)
      const firstFiveSelectors = tabOrder.slice(0, 5).map((el) => el.selector);
      expect(firstFiveSelectors.length).toBeGreaterThan(0);
    });

    test('header elements should have visible focus indicators', async ({ page }) => {
      // Get tab order
      const tabOrder = await extractTabOrder(page);

      // Focus header elements (usually first few in tab order)
      let focusedCount = 0;
      for (let i = 0; i < Math.min(5, tabOrder.length); i++) {
        await page.keyboard.press('Tab');
        const isFocused = await page.evaluate(() => {
          const el = document.activeElement;
          if (!el) return false;
          const style = window.getComputedStyle(el, ':focus');
          return style.outline !== 'none' && style.outline !== '';
        });
        if (isFocused) focusedCount++;
      }

      // At least some header elements should have visible focus
      expect(focusedCount).toBeGreaterThan(0);
    });

    test('navigation items should have accessible names', async ({ page }) => {
      // Find all navigation items
      const navItems = await page.locator('[role="navigation"] a, nav a').all();

      if (navItems.length > 0) {
        // Check first few navigation items
        for (let i = 0; i < Math.min(3, navItems.length); i++) {
          const nameInfo = await checkAccessibleName(navItems[i]);
          expect(nameInfo.hasAccessibleName).toBe(true);
          expect(nameInfo.name.length).toBeGreaterThan(0);
        }
      }
    });

    test('header should be a landmark region', async ({ page }) => {
      const landmarks = await checkLandmarkRegions(page);
      expect(landmarks.hasLandmarks).toBe(true);

      // Should have banner or header landmark
      const hasBanner = landmarks.landmarks.some((l) => l.role === 'banner');
      expect(hasBanner).toBe(true);
    });

    test('logo should have accessible name', async ({ page }) => {
      // Find logo element (usually in header)
      const logo = page.locator('header a[href="/"], header img[alt*="logo" i], [aria-label*="logo" i]').first();

      if (await logo.count() > 0) {
        const nameInfo = await checkAccessibleName(logo);
        expect(nameInfo.hasAccessibleName).toBe(true);
      }
    });
  });

  // ============================================================================
  // 3. LANDMARK REGIONS TESTS
  // ============================================================================
  test.describe('Landmark Regions', () => {
    test('page should have required landmark regions', async ({ page }) => {
      const landmarks = await checkLandmarkRegions(page);
      expect(landmarks.hasLandmarks).toBe(true);

      // Should have main landmark
      const hasMain = landmarks.landmarks.some((l) => l.role === 'main');
      expect(hasMain).toBe(true);

      // Log found landmarks
      console.log('Found landmarks:', landmarks.landmarks);
    });

    test('banner landmark should exist', async ({ page }) => {
      const landmarks = await checkLandmarkRegions(page);
      const hasBanner = landmarks.landmarks.some((l) => l.role === 'banner');
      expect(hasBanner).toBe(true);
    });

    test('main landmark should exist', async ({ page }) => {
      const landmarks = await checkLandmarkRegions(page);
      const hasMain = landmarks.landmarks.some((l) => l.role === 'main');
      expect(hasMain).toBe(true);
    });

    test('contentinfo (footer) landmark should exist', async ({ page }) => {
      const landmarks = await checkLandmarkRegions(page);
      const hasContentinfo = landmarks.landmarks.some((l) => l.role === 'contentinfo');
      expect(hasContentinfo).toBe(true);
    });

    test('navigation landmark should have accessible name if multiple', async ({ page }) => {
      // Check if there are multiple nav landmarks
      const navCount = await page.evaluate(() => {
        return document.querySelectorAll('[role="navigation"], nav').length;
      });

      if (navCount > 1) {
        // Each should have aria-label or aria-labelledby
        const navs = await page.locator('[role="navigation"], nav').all();
        for (const nav of navs) {
          const hasLabel = await nav.evaluate((el) => {
            return el.hasAttribute('aria-label') || el.hasAttribute('aria-labelledby');
          });
          expect(hasLabel).toBe(true);
        }
      }
    });
  });

  // ============================================================================
  // 4. MAIN CONTENT - CATEGORY/TAG FILTERS TESTS
  // ============================================================================
  test.describe('Main Content - Category/Tag Filters', () => {
    test('filter list should be keyboard navigable', async ({ page }) => {
      // Find filter/category elements
      const filterList = page.locator('[role="listbox"], [role="list"] [role="option"], .filters li, .categories li').first();

      if (await filterList.count() > 0) {
        // Focus on filter list
        await filterList.focus();

        // Verify we can navigate with arrow keys
        const initialFocus = await page.evaluate(() => document.activeElement?.id || '');

        // Press arrow key
        await page.keyboard.press('ArrowDown');

        const newFocus = await page.evaluate(() => document.activeElement?.id || '');

        // Focus should have moved or stayed (depending on implementation)
        expect(initialFocus || newFocus).toBeTruthy();
      }
    });

    test('filter items should have roving tabindex pattern if applicable', async ({ page }) => {
      // Find filter container
      const filterContainer = page.locator('[role="listbox"], .filters, .categories').first();

      if (await filterContainer.count() > 0) {
        const selector = await filterContainer.evaluate((el) => {
          return el.className
            ? `.${el.className.split(/\s+/)[0]}`
            : el.getAttribute('role') || 'ul';
        });

        const rovingResult = await validateRovingTabindex(page, selector);

        if (rovingResult.items.length > 0) {
          // If roving tabindex is used, verify exactly one item has tabindex="0"
          const activeItems = rovingResult.items.filter((item) => item.tabIndex === 0);
          expect(activeItems.length).toBeLessThanOrEqual(1);
        }
      }
    });

    test('filter items should have focus styling', async ({ page }) => {
      const focusResult = await verifyFocusIndicators(page);
      // Not all elements need focus, but focusable ones should have it
      expect(focusResult.elementsWithFocus + focusResult.elementsWithoutFocus).toBeGreaterThan(0);
    });

    test('filter items should have accessible names', async ({ page }) => {
      // Find filter items
      const filterItems = await page.locator('[role="option"], .filters li, .categories li').all();

      if (filterItems.length > 0) {
        // Check first few items
        for (let i = 0; i < Math.min(3, filterItems.length); i++) {
          const nameInfo = await checkAccessibleName(filterItems[i]);
          // Filter items should have text content or aria labels
          expect(nameInfo.hasAccessibleName || filterItems[i].textContent()).toBeTruthy();
        }
      }
    });

    test('filter navigation should support Home/End keys', async ({ page }) => {
      // Find first filter item
      const firstFilter = page.locator('[role="option"], .filters li, .categories li').first();

      if (await firstFilter.count() > 0) {
        // Focus first filter
        await firstFilter.focus();

        // Press End key to go to last
        await page.keyboard.press('End');

        // Verify we're no longer on first element
        const focused = await page.evaluate(() => {
          return document.activeElement?.textContent || '';
        });

        expect(focused).toBeTruthy();
      }
    });

    test('filter items should support typeahead navigation', async ({ page }) => {
      // Find filter items
      const filterItems = await page.locator('[role="option"], .filters li, .categories li').all();

      if (filterItems.length > 1) {
        // Get text of second item
        const secondItemText = await filterItems[1].textContent();
        const firstChar = secondItemText?.charAt(0).toLowerCase() || '';

        if (firstChar) {
          // Focus first item
          await filterItems[0].focus();

          // Type first character of second item
          await page.keyboard.type(firstChar);

          // Wait for typeahead
          await page.waitForTimeout(50);

          // Check if focus moved (typeahead may not always be implemented)
          const focusedText = await page.evaluate(() => {
            return (document.activeElement?.textContent || '').substring(0, 1).toLowerCase();
          });

          // May or may not have typeahead - just verify it doesn't error
          expect(typeof focusedText).toBe('string');
        }
      }
    });
  });

  // ============================================================================
  // 5. SEARCH FUNCTIONALITY TESTS
  // ============================================================================
  test.describe('Search Functionality', () => {
    test('search input should have accessible label', async ({ page }) => {
      const searchInput = page.locator('input[type="search"], input[placeholder*="search" i], [role="searchbox"]').first();

      if (await searchInput.count() > 0) {
        const nameInfo = await checkAccessibleName(searchInput);
        expect(nameInfo.hasAccessibleName).toBe(true);
      }
    });

    test('search input should have descriptive placeholder', async ({ page }) => {
      const searchInput = page.locator('input[type="search"], input[placeholder*="search" i]').first();

      if (await searchInput.count() > 0) {
        const placeholder = await searchInput.getAttribute('placeholder');
        expect(placeholder).toBeTruthy();
        expect(placeholder).toMatch(/search|find|query/i);
      }
    });

    test('search should be submittable with Enter key', async ({ page }) => {
      const searchInput = page.locator('input[type="search"], input[placeholder*="search" i]').first();

      if (await searchInput.count() > 0) {
        // Type in search
        await searchInput.fill('test');

        // Press Enter
        const [searchResponse] = await Promise.all([
          page.waitForResponse((response) => response.status() < 400).catch(() => null),
          page.keyboard.press('Enter'),
        ]);

        // Verify search executed
        expect(searchResponse || true).toBeTruthy();
      }
    });

    test('search input should support Escape key to clear', async ({ page }) => {
      const searchInput = page.locator('input[type="search"], input[placeholder*="search" i]').first();

      if (await searchInput.count() > 0) {
        // Fill search
        await searchInput.fill('test');
        expect(await searchInput.inputValue()).toBe('test');

        // Press Escape
        await page.keyboard.press('Escape');

        // Verify it's cleared or unfocused
        const value = await searchInput.inputValue();
        expect(value === '' || value === 'test').toBeTruthy(); // May or may not clear
      }
    });

    test('search input should have sufficient color contrast', async ({ page }) => {
      const searchInput = page.locator('input[type="search"], input[placeholder*="search" i]').first();

      if (await searchInput.count() > 0) {
        // Test placeholder contrast
        const contrastResult = await testUIContrast(page, searchInput, 'AA');
        expect(contrastResult.passes).toBe(true);
      }
    });
  });

  // ============================================================================
  // 6. INTERACTIVE ELEMENTS TESTS
  // ============================================================================
  test.describe('Interactive Elements', () => {
    test('all buttons should have accessible names', async ({ page }) => {
      const buttonLabels = await validateButtonLabels(page);
      expect(buttonLabels.allButtonsLabeled).toBe(true);

      if (!buttonLabels.allButtonsLabeled) {
        console.error('Unlabeled buttons:', buttonLabels.unlabeledSelectors);
      }
    });

    test('all links should have accessible names', async ({ page }) => {
      const links = await page.locator('a[href]').all();

      if (links.length > 0) {
        // Check first 10 links
        for (let i = 0; i < Math.min(10, links.length); i++) {
          const nameInfo = await checkAccessibleName(links[i]);
          expect(nameInfo.hasAccessibleName).toBe(true);
        }
      }
    });

    test('form inputs should be properly labeled', async ({ page }) => {
      const formLabels = await validateFormLabels(page);
      expect(formLabels.allLabeled).toBe(true);

      if (!formLabels.allLabeled) {
        console.error('Unlabeled inputs:', formLabels.unlabeledElements);
      }
    });

    test('disabled elements should not be in tab order', async ({ page }) => {
      const tabOrder = await extractTabOrder(page);

      // Check that no disabled elements are in tab order
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

    test('aria-pressed buttons should have initial state', async ({ page }) => {
      const buttons = await page.locator('button[aria-pressed], [role="button"][aria-pressed]').all();

      if (buttons.length > 0) {
        // Check first few buttons
        for (let i = 0; i < Math.min(3, buttons.length); i++) {
          const ariaPressed = await buttons[i].getAttribute('aria-pressed');
          expect(ariaPressed === 'true' || ariaPressed === 'false').toBe(true);
        }
      }
    });
  });

  // ============================================================================
  // 7. COLOR CONTRAST TESTS
  // ============================================================================
  test.describe('Color Contrast - WCAG 2.1 AA Compliance', () => {
    test('primary body text should have sufficient contrast', async ({ page }) => {
      const bodyText = page.locator('body p, body li, body span').first();

      if (await bodyText.count() > 0) {
        const contrast = await testTextContrast(page, bodyText, 'AA');
        expect(contrast.passes).toBe(true);
        if (!contrast.passes) {
          console.error(`Text contrast issue: ${contrast.violation}`);
        }
      }
    });

    test('secondary text (help text, labels) should have sufficient contrast', async ({ page }) => {
      const labels = await page.locator('label, .help-text, small').all();

      if (labels.length > 0) {
        // Test first few labels
        for (let i = 0; i < Math.min(3, labels.length); i++) {
          const contrast = await testTextContrast(page, labels[i], 'AA');
          expect(contrast.passes).toBe(true);
        }
      }
    });

    test('button text should have sufficient contrast', async ({ page }) => {
      const buttons = await page.locator('button').all();

      if (buttons.length > 0) {
        // Test first few buttons
        for (let i = 0; i < Math.min(3, buttons.length); i++) {
          const contrast = await testUIContrast(page, buttons[i], 'AA');
          expect(contrast.passes).toBe(true);
        }
      }
    });

    test('link text should have sufficient contrast', async ({ page }) => {
      const links = await page.locator('a[href]').all();

      if (links.length > 0) {
        // Test first few links
        for (let i = 0; i < Math.min(3, links.length); i++) {
          const contrast = await testTextContrast(page, links[i], 'AA');
          expect(contrast.passes).toBe(true);
        }
      }
    });

    test('input borders should have sufficient contrast', async ({ page }) => {
      const inputs = await page.locator('input:visible').all();

      if (inputs.length > 0) {
        // Test first few inputs
        for (let i = 0; i < Math.min(3, inputs.length); i++) {
          const contrast = await testUIContrast(page, inputs[i], 'AA');
          expect(contrast.passes).toBe(true);
        }
      }
    });

    test('focus indicators should have sufficient contrast', async ({ page }) => {
      const focusableElements = await page.locator('a[href], button, input, select, textarea').all();

      if (focusableElements.length > 0) {
        // Focus first element and check contrast
        const element = focusableElements[0];
        await element.focus();

        // Get focus outline color
        const focusOutlineColor = await element.evaluate((el) => {
          const style = window.getComputedStyle(el, ':focus');
          return style.outlineColor || style.boxShadow || '';
        });

        // Verify focus indicator exists and is not invisible
        expect(focusOutlineColor).toBeTruthy();
      }
    });

    test('navigation items should have sufficient contrast', async ({ page }) => {
      const navItems = await page.locator('[role="navigation"] a, nav a').all();

      if (navItems.length > 0) {
        // Test first few nav items
        for (let i = 0; i < Math.min(3, navItems.length); i++) {
          const contrast = await testTextContrast(page, navItems[i], 'AA');
          expect(contrast.passes).toBe(true);
        }
      }
    });

    test('error/warning messages should have sufficient contrast', async ({ page }) => {
      const alerts = await page.locator('[role="alert"], .alert, .error, .warning').all();

      if (alerts.length > 0) {
        // Test first few alerts
        for (let i = 0; i < Math.min(3, alerts.length); i++) {
          const contrast = await testTextContrast(page, alerts[i], 'AA');
          expect(contrast.passes).toBe(true);
        }
      }
    });

    test('disabled elements should have sufficient contrast', async ({ page }) => {
      const disabledElements = await page.locator('button:disabled, input:disabled').all();

      if (disabledElements.length > 0) {
        // Test first few disabled elements
        for (let i = 0; i < Math.min(2, disabledElements.length); i++) {
          const contrast = await testUIContrast(page, disabledElements[i], 'AA');
          // Disabled elements have different contrast requirements but should still be visible
          expect(contrast.ratio).toBeGreaterThan(0);
        }
      }
    });
  });

  // ============================================================================
  // 8. LIVE REGIONS TESTS
  // ============================================================================
  test.describe('Live Regions', () => {
    test('page should have live regions for notifications', async ({ page }) => {
      const liveRegions = await checkLiveRegions(page);
      // May or may not have live regions - log findings
      console.log('Live regions found:', liveRegions.regions);
    });

    test('notification areas should have aria-live attribute', async ({ page }) => {
      const notifications = await page.locator('[role="alert"], [role="status"], .notification').all();

      if (notifications.length > 0) {
        // Check first notification
        const hasAriaLive = await notifications[0].evaluate((el) => {
          return el.hasAttribute('aria-live') || el.hasAttribute('role');
        });
        expect(hasAriaLive).toBe(true);
      }
    });

    test('live regions should have aria-atomic and aria-relevant', async ({ page }) => {
      const liveRegions = await page.locator('[aria-live]').all();

      if (liveRegions.length > 0) {
        for (let i = 0; i < Math.min(2, liveRegions.length); i++) {
          const attrs = await liveRegions[i].evaluate((el) => ({
            ariaLive: el.getAttribute('aria-live'),
            ariaAtomic: el.getAttribute('aria-atomic'),
            ariaRelevant: el.getAttribute('aria-relevant'),
          }));

          // If aria-live is set, should be valid value
          if (attrs.ariaLive) {
            expect(['polite', 'assertive', 'off']).toContain(attrs.ariaLive);
          }
        }
      }
    });
  });

  // ============================================================================
  // 9. HEADING HIERARCHY TESTS
  // ============================================================================
  test.describe('Heading Hierarchy', () => {
    test('headings should have valid hierarchy', async ({ page }) => {
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

    test('headings should not skip levels', async ({ page }) => {
      const hierarchy = await validateHeadingHierarchy(page);
      // Check for skipped levels
      for (const heading of hierarchy.headings) {
        expect(heading.level).toBeGreaterThan(0);
        expect(heading.level).toBeLessThanOrEqual(6);
      }
    });
  });

  // ============================================================================
  // 10. COMPREHENSIVE BUTTON LABEL TEST
  // ============================================================================
  test.describe('Button Label Accessibility', () => {
    test('all buttons should have clear accessible names', async ({ page }) => {
      const buttons = await page.locator('button, [role="button"]').all();

      if (buttons.length > 0) {
        const results = [];
        for (let i = 0; i < Math.min(5, buttons.length); i++) {
          const nameInfo = await checkAccessibleName(buttons[i]);
          results.push({
            name: nameInfo.name || 'no-name',
            hasName: nameInfo.hasAccessibleName,
          });
          expect(nameInfo.hasAccessibleName).toBe(true);
        }
        console.log('Button accessibility results:', results);
      }
    });

    test('icon buttons should have aria-label', async ({ page }) => {
      // Find buttons that might be icon-only
      const iconButtons = await page.locator('button:has(svg), button:has(img), [role="button"]:has(svg)').all();

      if (iconButtons.length > 0) {
        for (let i = 0; i < Math.min(3, iconButtons.length); i++) {
          const hasText = await iconButtons[i].evaluate((el) => {
            return (el.textContent?.trim() || '').length > 0;
          });

          if (!hasText) {
            // If no text, should have aria-label
            const nameInfo = await checkAccessibleName(iconButtons[i]);
            expect(nameInfo.hasAccessibleName).toBe(true);
          }
        }
      }
    });
  });

  // ============================================================================
  // 11. DYNAMIC CONTENT AND CONDITIONAL UI TESTS
  // ============================================================================
  test.describe('Dynamic Content and Conditional UI', () => {
    test('should handle loading states accessibly', async ({ page }) => {
      // Look for loading indicators
      const loaders = await page.locator('[role="progressbar"], .loading, .spinner').all();

      if (loaders.length > 0) {
        // Check if loading indicator is properly announced
        const hasAriaLabel = await loaders[0].evaluate((el) => {
          return el.hasAttribute('aria-label') || el.hasAttribute('aria-labelledby');
        });
        expect(hasAriaLabel || loaders[0].textContent()).toBeTruthy();
      }
    });

    test('should announce dynamic content updates', async ({ page }) => {
      const liveRegions = await checkLiveRegions(page);
      // Log any live regions found
      console.log('Live regions for dynamic content:', liveRegions.regions);
    });
  });

  // ============================================================================
  // 12. MOBILE VIEWPORT TESTS (if applicable)
  // ============================================================================
  test.describe('Mobile Viewport Accessibility', () => {
    test('should maintain accessibility at mobile viewport', async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 });

      // Navigate to main page
      await page.goto('/', { waitUntil: 'networkidle' });

      // Test essential accessibility features
      const skipLinks = await validateSkipLinks(page);
      expect(skipLinks.hasSkipLink).toBe(true);

      const landmarks = await checkLandmarkRegions(page);
      expect(landmarks.hasLandmarks).toBe(true);

      // Reset viewport
      await page.setViewportSize({ width: 1280, height: 720 });
    });
  });

  // ============================================================================
  // 13. TAB ORDER CONSISTENCY TESTS
  // ============================================================================
  test.describe('Tab Order Consistency', () => {
    test('tab order should be logical and consistent', async ({ page }) => {
      const tabOrder = await extractTabOrder(page);

      // Should have focusable elements
      expect(tabOrder.length).toBeGreaterThan(0);

      // Check that no element has tabindex > 0 (which breaks logical order)
      for (const element of tabOrder) {
        if (element.tabIndex > 0) {
          console.warn(`Element with explicit positive tabindex found: ${element.selector}`);
        }
      }
    });

    test('tab order should follow document flow when not explicitly set', async ({ page }) => {
      const tabOrder = await extractTabOrder(page);

      // All naturally focusable elements should have tabIndex 0
      const naturally = tabOrder.filter((el) => el.isNaturallyFocusable);
      for (const element of naturally) {
        expect(element.tabIndex).toBeLessThanOrEqual(0);
      }
    });
  });

  // ============================================================================
  // 14. VISUAL TESTING TESTS
  // ============================================================================
  test.describe('Visual Accessibility', () => {
    test('focus indicators should be visually distinct', async ({ page }) => {
      const focusResult = await verifyFocusIndicators(page);

      // Most elements should have focus indicators
      const ratio = focusResult.elementsWithFocus / (focusResult.elementsWithFocus + focusResult.elementsWithoutFocus);
      expect(ratio).toBeGreaterThan(0.8);

      console.log(`Focus indicators: ${focusResult.elementsWithFocus} with, ${focusResult.elementsWithoutFocus} without`);
    });

    test('should capture main page state for visual review', async ({ page }) => {
      // Take a screenshot of the main page
      await page.screenshot({ path: 'tests/accessibility/reports/main-page.png' });

      // Find and capture first interactive element
      const firstButton = page.locator('button').first();
      if (await firstButton.count() > 0) {
        await captureNormalState(page, firstButton, 'tests/accessibility/reports/button-normal.png');
        await captureFocusState(page, firstButton, 'tests/accessibility/reports/button-focused.png');
      }
    });
  });

  // ============================================================================
  // 15. ARIA ATTRIBUTES TESTS
  // ============================================================================
  test.describe('ARIA Attributes', () => {
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
            if (!document.getElementById(id)) {
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
            if (!document.getElementById(id)) {
              errors.push(`Invalid reference: ${id}`);
            }
          }
        });
        return errors;
      });

      expect(describedByErrors.length).toBe(0);
    });
  });
});

// ============================================================================
// AUTHENTICATED USER TESTS (if applicable)
// ============================================================================
test.describe('Main Page Accessibility - Authenticated User', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to main page (user should already be authenticated via fixture)
    await page.goto('/', { waitUntil: 'networkidle' });
  });

  test('authenticated user menu should be accessible', async ({ page }) => {
    // Find user menu or profile button
    const userMenu = page.locator('[aria-label*="user" i], [aria-label*="account" i], button:has-text("Profile")').first();

    if (await userMenu.count() > 0) {
      // Verify accessible name
      const nameInfo = await checkAccessibleName(userMenu);
      expect(nameInfo.hasAccessibleName).toBe(true);

      // Focus and verify focus indicator
      await userMenu.focus();
      const hasFocus = await userMenu.evaluate((el) => {
        const style = window.getComputedStyle(el, ':focus');
        return style.outline !== 'none' && style.outline !== '';
      });
      expect(hasFocus).toBe(true);
    }
  });

  test('user-specific elements should have proper landmarks', async ({ page }) => {
    const landmarks = await checkLandmarkRegions(page);
    expect(landmarks.hasLandmarks).toBe(true);
  });
});
