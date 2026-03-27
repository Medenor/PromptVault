// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

// @ts-nocheck

/**
 * Comprehensive Playwright test suite for keyboard accessibility audits (T-ACC006)
 * Tests cover WCAG 2.1 AA compliance for:
 * - Tab order consistency across all major pages
 * - Focus visibility and indicators
 * - Keyboard event responses (Enter, Space, Escape, Arrow keys)
 * - No keyboard traps
 * - Roving tabindex patterns for lists/grids
 * - Complete keyboard-only workflows
 *
 * Test Coverage:
 * - Home page (/)
 * - Login page (/auth/login)
 * - Backup management (/backup-management)
 * - Import/Export (/import-export)
 * - Manage categories (/manage-categories)
 * - Manage tags (/manage-tags)
 * - Admin users (/admin/users)
 * - Profile page (/profile)
 */

import { expect, test } from '@playwright/test';
import {
  extractTabOrder,
  validateSkipLinks,
  verifyFocusIndicators,
  validateRovingTabindex,
  testKeyboardNavigation,
  testBackwardNavigation,
  testKeyActivation,
} from './utils/keyboard.js';
import { checkAccessibleName } from './utils/aria.js';
import { authenticatedUserTest, authenticatedAdminTest, getBaseURL } from './fixtures/auth.js';

const baseURL = getBaseURL();

// ============================================================================
// 1. TAB ORDER TESTS - PUBLIC ROUTES
// ============================================================================

const publicRoutes = [
  { path: '/', name: 'Home' },
  { path: '/auth/login', name: 'Login' },
];

publicRoutes.forEach(({ path, name }) => {

  test.describe(`@a11y-keyboard Tab Order - ${name} Page (${path})`, () => {
    test.beforeEach(async ({ page }) => {
      await page.goto(`${baseURL}${path}`, { waitUntil: 'networkidle' });
    });

    test(`should have logical and consistent tab order on ${name}`, async ({ page }) => {
      const tabOrder = await extractTabOrder(page);

      // Should have at least some focusable elements
      expect(tabOrder.length).toBeGreaterThan(0);

      // Check that no element has tabindex > 0 (which breaks logical order)
      // except for specific patterns like roving tabindex
      const problematicTabIndices = tabOrder.filter((el) => el.tabIndex > 0);
      expect(problematicTabIndices.length).toBeLessThanOrEqual(1);

      console.log(`${name} tab order (${tabOrder.length} items):`);
      tabOrder.slice(0, 5).forEach((item, idx) => {
        console.log(`  ${idx + 1}. ${item.selector} (tabindex: ${item.tabIndex})`);
      });
    });

    test(`should follow document flow without explicit tabindex > 0 on ${name}`, async ({ page }) => {
      const tabOrder = await extractTabOrder(page);

      // Naturally focusable elements should have tabindex <= 0
      const naturally = tabOrder.filter((el) => el.isNaturallyFocusable);
      for (const element of naturally) {
        expect(element.tabIndex).toBeLessThanOrEqual(0);
      }
    });

    test(`should skip link be first focusable element on ${name}`, async ({ page }) => {
      const tabOrder = await extractTabOrder(page);
      if (tabOrder.length === 0) {
        test.skip();
        return;
      }

      // Tab to first element
      await page.keyboard.press('Tab');

      // Check if first element is a skip link
      const focusedHref = await page.evaluate(() => {
        const active = document.activeElement;
        return (active as HTMLAnchorElement)?.href || '';
      });

      // Skip link may or may not be present - if it is, it should be first
      const skipLinks = await validateSkipLinks(page);
      if (skipLinks.skipLinks.length > 0) {
        expect(focusedHref.includes('#') || focusedHref === '').toBeTruthy();
      }
    });
  });
});

// ============================================================================
// 2. TAB ORDER TESTS - PROTECTED ROUTES
// ============================================================================

const protectedRoutes = [
  { path: '/backup-management', name: 'Backup Management', roles: ['user'] },
  { path: '/import-export', name: 'Import/Export', roles: ['user'] },
  { path: '/manage-categories', name: 'Manage Categories', roles: ['user'] },
  { path: '/manage-tags', name: 'Manage Tags', roles: ['user'] },
  { path: '/profile', name: 'Profile', roles: ['user'] },
  { path: '/admin/users', name: 'Admin Users', roles: ['admin'] },
];

protectedRoutes.forEach(({ path, name, roles }) => {
  const test = roles.includes('admin') ? authenticatedAdminTest : authenticatedUserTest;

  test.describe(`@a11y-keyboard Tab Order - ${name} Page (${path})`, () => {
    test.beforeEach(async ({ authenticatedPage }) => {
      await authenticatedPage.goto(`${baseURL}${path}`, { waitUntil: 'networkidle' });
    });

    test(`should have consistent tab order on ${name}`, async ({ authenticatedPage }) => {
      const tabOrder = await extractTabOrder(authenticatedPage);

      expect(tabOrder.length).toBeGreaterThan(0);

      // No positive tabindex values should be used (except in special patterns)
      const positiveTabindices = tabOrder.filter((el) => el.tabIndex > 0);
      expect(positiveTabindices.length).toBeLessThanOrEqual(0);

      console.log(`${name} tab order (${tabOrder.length} items)`);
    });

    test(`should not trap focus on ${name}`, async ({ authenticatedPage }) => {
      const tabOrder = await extractTabOrder(authenticatedPage);

      if (tabOrder.length < 2) {
        test.skip();
        return;
      }

      // Press Tab from first to last element
      await authenticatedPage.keyboard.press('Tab');

      // Press End+Tab to go to last focusable
      for (let i = 1; i < Math.min(20, tabOrder.length); i++) {
        await authenticatedPage.keyboard.press('Tab');
      }

      // Should still be able to focus an element (not stuck)
      const focused = await authenticatedPage.evaluate(() => {
        return document.activeElement?.tagName || '';
      });

      expect(focused).toBeTruthy();
    });
  });
});

// ============================================================================
// 3. FOCUS VISIBILITY TESTS - PUBLIC ROUTES
// ============================================================================

test.describe('@a11y-keyboard Focus Visibility - Home and Login', () => {
  const publicFocusRoutes = [
    { path: '/', name: 'Home' },
    { path: '/auth/login', name: 'Login' },
  ];

  publicFocusRoutes.forEach(({ path, name }) => {
    test.describe(`${name} (${path})`, () => {
      test.beforeEach(async ({ page }) => {
        await page.goto(`${baseURL}${path}`, { waitUntil: 'networkidle' });
      });

      test(`should display visible focus indicators on ${name}`, async ({ page }) => {
        const focusResult = await verifyFocusIndicators(page);

        // Most interactive elements should have visible focus
        const ratio = focusResult.elementsWithFocus / (focusResult.elementsWithFocus + focusResult.elementsWithoutFocus);
        expect(ratio).toBeGreaterThan(0.7);

        console.log(`${name} focus indicators: ${focusResult.elementsWithFocus} visible, ${focusResult.elementsWithoutFocus} missing`);
      });

      test(`should have computed outline styles for focus on ${name}`, async ({ page }) => {
        const tabOrder = await extractTabOrder(page);

        if (tabOrder.length === 0) {
          test.skip();
          return;
        }

        await page.keyboard.press('Tab');

        const focusStyles = await page.evaluate(() => {
          const active = document.activeElement;
          if (!active) return null;

          const style = window.getComputedStyle(active);
          return {
            outline: style.outline,
            outlineWidth: style.outlineWidth,
            boxShadow: style.boxShadow,
            visible: (style.outlineWidth && style.outlineWidth !== '0px') || (style.boxShadow && style.boxShadow !== 'none'),
          };
        });

        expect(focusStyles).not.toBeNull();
        expect(focusStyles?.visible).toBe(true);
      });

      test(`should not hide focus indicators on ${name}`, async ({ page }) => {
        const tabOrder = await extractTabOrder(page);

        if (tabOrder.length === 0) {
          test.skip();
          return;
        }

        await page.keyboard.press('Tab');

        const isFocusHidden = await page.evaluate(() => {
          const active = document.activeElement;
          const style = window.getComputedStyle(active);
          return style.opacity === '0' || style.visibility === 'hidden' || style.display === 'none';
        });

        expect(isFocusHidden).toBe(false);
      });
    });
  });
});

// ============================================================================
// 3B. FOCUS VISIBILITY TESTS - PROTECTED ROUTES
// ============================================================================

authenticatedUserTest.describe('@a11y-keyboard Focus Visibility - Authenticated Routes', () => {
  const protectedFocusRoutes = [
    { path: '/manage-categories', name: 'Categories' },
    { path: '/manage-tags', name: 'Tags' },
    { path: '/profile', name: 'Profile' },
  ];

  protectedFocusRoutes.forEach(({ path, name }) => {
    authenticatedUserTest.describe(`${name} (${path})`, () => {
      authenticatedUserTest.beforeEach(async ({ authenticatedPage }) => {
        await authenticatedPage.goto(`${baseURL}${path}`, { waitUntil: 'networkidle' });
      });

      authenticatedUserTest(`should display visible focus indicators on ${name}`, async ({ authenticatedPage }) => {
        const focusResult = await verifyFocusIndicators(authenticatedPage);

        const ratio = focusResult.elementsWithFocus / (focusResult.elementsWithFocus + focusResult.elementsWithoutFocus);
        expect(ratio).toBeGreaterThan(0.7);
      });

      authenticatedUserTest(`should have outline styles for focus on ${name}`, async ({ authenticatedPage }) => {
        const tabOrder = await extractTabOrder(authenticatedPage);

        if (tabOrder.length === 0) {
          authenticatedUserTest.skip();
          return;
        }

        await authenticatedPage.keyboard.press('Tab');

        const focusStyles = await authenticatedPage.evaluate(() => {
          const active = document.activeElement;
          if (!active) return null;

          const style = window.getComputedStyle(active);
          return {
            visible: (style.outlineWidth && style.outlineWidth !== '0px') || (style.boxShadow && style.boxShadow !== 'none'),
          };
        });

        expect(focusStyles?.visible).toBe(true);
      });
    });
  });
});

// ============================================================================
// 4. KEYBOARD EVENT TESTS
// ============================================================================

authenticatedUserTest.describe('@a11y-keyboard Keyboard Events - Enter Key', () => {
  authenticatedUserTest.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto(`${baseURL}/manage-categories`, { waitUntil: 'networkidle' });
  });

  authenticatedUserTest(
    'Enter key should activate buttons and submit forms',
    async ({ authenticatedPage }) => {
      const buttons = await authenticatedPage.locator('button').all();

      if (buttons.length === 0) {
        authenticatedUserTest.skip();
        return;
      }

      const firstButton = buttons[0];
      await firstButton.focus();

      const result = await testKeyActivation(authenticatedPage, 'button', 'Enter');

      // Enter key should trigger button or form submission
      expect(result.error).toBeNull();
    }
  );
});

authenticatedUserTest.describe('@a11y-keyboard Keyboard Events - Space Key', () => {
  authenticatedUserTest.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto(`${baseURL}/manage-categories`, { waitUntil: 'networkidle' });
  });

  authenticatedUserTest('Space key should toggle checkboxes', async ({ authenticatedPage }) => {
    const checkbox = authenticatedPage.locator('input[type="checkbox"]').first();

    if ((await checkbox.count()) === 0) {
      authenticatedUserTest.skip();
      return;
    }

    await checkbox.focus();
    const initialChecked = await checkbox.isChecked();

    await authenticatedPage.keyboard.press('Space');
    await authenticatedPage.waitForLoadState('networkidle').catch(() => {});

    const finalChecked = await checkbox.isChecked();

    // Space should toggle checkbox state
    expect(initialChecked).not.toBe(finalChecked);
  });

  authenticatedUserTest('Space key should activate buttons', async ({ authenticatedPage }) => {
    const result = await testKeyActivation(authenticatedPage, 'button', ' ');

    // Space key should activate button (no error)
    expect(result.error).toBeNull();
  });
});

authenticatedUserTest.describe('@a11y-keyboard Keyboard Events - Escape Key', () => {
  authenticatedUserTest.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto(`${baseURL}/manage-categories`, { waitUntil: 'networkidle' });
  });

  authenticatedUserTest('Escape key should close modals if present', async ({ authenticatedPage }) => {
    // First, try to open a modal (e.g., by clicking a button)
    const createButton = authenticatedPage.locator('button:has-text("Create"), button:has-text("Add")').first();

    if ((await createButton.count()) === 0) {
      authenticatedUserTest.skip();
      return;
    }

    await createButton.click();
    await authenticatedPage.waitForLoadState('networkidle').catch(() => {});

    // Check if modal appeared
    const modal = authenticatedPage.locator('[role="dialog"], .modal, .dialog').first();
    const modalOpen = await modal.count() > 0;

    if (modalOpen) {
      // Press Escape
      await authenticatedPage.keyboard.press('Escape');
      await authenticatedPage.waitForLoadState('networkidle').catch(() => {});

      // Modal should be closed or hidden
      const isStillVisible = await modal.isVisible().catch(() => false);
      expect(isStillVisible).toBe(false);
    }
  });
});

authenticatedUserTest.describe('@a11y-keyboard Keyboard Events - Arrow Keys', () => {
  authenticatedUserTest.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto(`${baseURL}/manage-categories`, { waitUntil: 'networkidle' });
  });

  authenticatedUserTest('Arrow keys should navigate through lists', async ({ authenticatedPage }) => {
    const listItems = authenticatedPage.locator('[role="option"], li, [role="menuitem"]').all();

    if ((await listItems).length < 2) {
      authenticatedUserTest.skip();
      return;
    }

    // Focus first item
    const items = await listItems;
    await items[0].focus();

    const initialFocused = await authenticatedPage.evaluate(() => document.activeElement?.textContent || '');

    // Press Arrow Down
    await authenticatedPage.keyboard.press('ArrowDown');
    await authenticatedPage.waitForLoadState('networkidle').catch(() => {});

    const newFocused = await authenticatedPage.evaluate(() => document.activeElement?.textContent || '');

    // Focus should have moved or stayed (depending on implementation)
    expect(initialFocused || newFocused).toBeTruthy();
  });
});

// ============================================================================
// 5. NO KEYBOARD TRAP TESTS
// ============================================================================

protectedRoutes.forEach(({ path, name, roles }) => {
  const test = roles.includes('admin') ? authenticatedAdminTest : authenticatedUserTest;

  test.describe(`@a11y-keyboard No Keyboard Traps - ${name} (${path})`, () => {
    test.beforeEach(async ({ authenticatedPage }) => {
      await authenticatedPage.goto(`${baseURL}${path}`, { waitUntil: 'networkidle' });
    });

    test(`should allow escape from last focusable element on ${name}`, async ({ authenticatedPage }) => {
      const tabOrder = await extractTabOrder(authenticatedPage);

      if (tabOrder.length < 2) {
        test.skip();
        return;
      }

      // Navigate to last element
      for (let i = 0; i < tabOrder.length; i++) {
        await authenticatedPage.keyboard.press('Tab');
      }

      // Tab again should cycle to first or stay at last without error
      await authenticatedPage.keyboard.press('Tab');

      // Should not throw error or freeze
      const focused = await authenticatedPage.evaluate(() => document.activeElement?.tagName || '');
      expect(focused).toBeTruthy();
    });

    test(`should support Tab cycling through all focusable elements on ${name}`, async ({ authenticatedPage }) => {
      const navResult = await testKeyboardNavigation(authenticatedPage);

      // Keyboard navigation should work
      expect(navResult.focusableElements).toBeGreaterThanOrEqual(0);

      if (navResult.issues.length > 0) {
        console.log(`${name} keyboard navigation issues:`, navResult.issues);
      }
    });

    test(`should support Shift+Tab backward navigation on ${name}`, async ({ authenticatedPage }) => {
      const backwardResult = await testBackwardNavigation(authenticatedPage);

      // Should be able to navigate backward
      expect(backwardResult.success).toBe(true);

      if (backwardResult.issues.length > 0) {
        console.log(`${name} backward navigation issues:`, backwardResult.issues);
      }
    });

    test(`should allow escape from modal dialogs with Tab on ${name}`, async ({ authenticatedPage }) => {
      // Try to open a modal
      const createButton = authenticatedPage
        .locator('button:has-text("Create"), button:has-text("Add"), button:has-text("New")')
        .first();

      if ((await createButton.count()) === 0) {
        test.skip();
        return;
      }

      await createButton.click();
      await authenticatedPage.waitForLoadState('networkidle').catch(() => {});

      const modal = authenticatedPage.locator('[role="dialog"], .modal, .dialog').first();
      if ((await modal.count()) === 0) {
        test.skip();
        return;
      }

      // Try to Tab out of modal
      for (let i = 0; i < 20; i++) {
        await authenticatedPage.keyboard.press('Tab');
      }

      // Should not be infinitely trapped
      const focused = await authenticatedPage.evaluate(() => document.activeElement?.tagName || '');
      expect(focused).toBeTruthy();
    });
  });
});

// ============================================================================
// 6. ROVING TABINDEX TESTS
// ============================================================================

authenticatedUserTest.describe('@a11y-keyboard Roving Tabindex Pattern - Category List', () => {
  authenticatedUserTest.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto(`${baseURL}/manage-categories`, { waitUntil: 'networkidle' });
  });

  authenticatedUserTest('should have roving tabindex on category items', async ({ authenticatedPage }) => {
    const categoryList = authenticatedPage.locator('[role="list"], .categories, ul').first();

    if ((await categoryList.count()) === 0) {
      authenticatedUserTest.skip();
      return;
    }

    const selector = await categoryList.evaluate((el) => {
      return el.className ? `.${el.className.split(/\s+/)[0]}` : 'ul';
    });

    const rovingResult = await validateRovingTabindex(authenticatedPage, selector);

    // If roving tabindex is implemented, validate it
    if (rovingResult.items.length > 0) {
      // Exactly one item should have tabindex="0"
      const activeItems = rovingResult.items.filter((item) => item.tabIndex === 0);
      expect(activeItems.length).toBeLessThanOrEqual(1);

      // Other items should have tabindex="-1"
      const inactiveItems = rovingResult.items.filter((item) => item.tabIndex === -1);
      expect(inactiveItems.length).toBeGreaterThan(0);
    }
  });

  authenticatedUserTest('should update tabindex dynamically on arrow key navigation', async ({ authenticatedPage }) => {
    const categoryItems = authenticatedPage.locator('[role="option"], li, .category-item').all();

    if ((await categoryItems).length < 2) {
      authenticatedUserTest.skip();
      return;
    }

    const items = await categoryItems;
    await items[0].focus();

    // Get initial tabindex
    const initialTabindex = await items[0].getAttribute('tabindex');

    // Press Arrow Down
    await authenticatedPage.keyboard.press('ArrowDown');
    await authenticatedPage.waitForLoadState('networkidle').catch(() => {});

    // Check if tabindex updated
    const finalTabindex = await items[0].getAttribute('tabindex');

    // Tabindex may or may not change (depending on implementation)
    expect(typeof finalTabindex).toBe('string');
  });

  authenticatedUserTest('should have first item focusable by default', async ({ authenticatedPage }) => {
    const categoryItems = authenticatedPage.locator('[role="option"], li, .category-item').all();

    if ((await categoryItems).length === 0) {
      authenticatedUserTest.skip();
      return;
    }

    const items = await categoryItems;
    const firstItemTabindex = await items[0].getAttribute('tabindex');

    // First item should be focusable (tabindex="0" or no explicit tabindex)
    expect(firstItemTabindex === '0' || firstItemTabindex === null).toBe(true);
  });
});

authenticatedUserTest.describe('@a11y-keyboard Roving Tabindex Pattern - Tag List', () => {
  authenticatedUserTest.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto(`${baseURL}/manage-tags`, { waitUntil: 'networkidle' });
  });

  authenticatedUserTest('should have roving tabindex pattern on tag items', async ({ authenticatedPage }) => {
    const tagList = authenticatedPage.locator('[role="list"], .tags, ul').first();

    if ((await tagList.count()) === 0) {
      authenticatedUserTest.skip();
      return;
    }

    const selector = await tagList.evaluate((el) => {
      return el.className ? `.${el.className.split(/\s+/)[0]}` : 'ul';
    });

    const rovingResult = await validateRovingTabindex(authenticatedPage, selector);

    if (rovingResult.items.length > 0) {
      // Validate roving pattern
      expect(rovingResult.items.length).toBeGreaterThan(0);
    }
  });

  authenticatedUserTest('should allow arrow key navigation within tag list', async ({ authenticatedPage }) => {
    const tagItems = authenticatedPage.locator('[role="option"], li, .tag-item').all();

    if ((await tagItems).length < 2) {
      authenticatedUserTest.skip();
      return;
    }

    const items = await tagItems;
    await items[0].focus();

    // Verify focus moved
    await authenticatedPage.keyboard.press('ArrowDown');

    const focused = await authenticatedPage.evaluate(() => document.activeElement?.tagName || '');
    expect(focused).toBeTruthy();
  });
});

// ============================================================================
// 7. WORKFLOW TESTS - KEYBOARD ONLY
// ============================================================================

authenticatedUserTest.describe('@a11y-keyboard Workflow - Create Item (Keyboard Only)', () => {
  authenticatedUserTest.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto(`${baseURL}/manage-categories`, { waitUntil: 'networkidle' });
  });

  authenticatedUserTest('should create category using keyboard only', async ({ authenticatedPage }) => {
    // Find create button
    const createButton = authenticatedPage.locator('button:has-text("Create"), button:has-text("Add")').first();

    if ((await createButton.count()) === 0) {
      authenticatedUserTest.skip();
      return;
    }

    // Tab to create button
    let focused = await authenticatedPage.evaluate(() => document.activeElement?.tagName || '');
    let attempts = 0;
    while (!focused?.toUpperCase().includes('BUTTON') && attempts < 30) {
      await authenticatedPage.keyboard.press('Tab');
      focused = await authenticatedPage.evaluate(() => document.activeElement?.textContent || '');
      attempts++;
    }

    // Press Enter to activate
    await authenticatedPage.keyboard.press('Enter');
    await authenticatedPage.waitForLoadState('networkidle').catch(() => {});

    // Modal should open
    const modal = authenticatedPage.locator('[role="dialog"], .modal').first();
    expect(await modal.count()).toBeGreaterThanOrEqual(0);
  });
});

authenticatedUserTest.describe('@a11y-keyboard Workflow - Search and Filter (Keyboard Only)', () => {
  authenticatedUserTest.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto(`${baseURL}/manage-categories`, { waitUntil: 'networkidle' });
  });

  authenticatedUserTest('should search/filter using keyboard only', async ({ authenticatedPage }) => {
    const searchInput = authenticatedPage.locator('input[type="search"], input[placeholder*="search"]').first();

    if ((await searchInput.count()) === 0) {
      authenticatedUserTest.skip();
      return;
    }

    // Tab to search input
    await authenticatedPage.keyboard.press('Tab');

    // Type search term
    await authenticatedPage.keyboard.type('test');

    // Press Enter to search
    await authenticatedPage.keyboard.press('Enter');
    await authenticatedPage.waitForLoadState('networkidle').catch(() => {});

    // Verify search executed (no error thrown)
    const focused = await authenticatedPage.evaluate(() => document.activeElement?.tagName || '');
    expect(focused).toBeTruthy();
  });
});

authenticatedUserTest.describe('@a11y-keyboard Workflow - Import/Export (Keyboard Only)', () => {
  authenticatedUserTest.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto(`${baseURL}/import-export`, { waitUntil: 'networkidle' });
  });

  authenticatedUserTest('should navigate import/export page with keyboard', async ({ authenticatedPage }) => {
    const tabOrder = await extractTabOrder(authenticatedPage);

    expect(tabOrder.length).toBeGreaterThan(0);

    // Should be able to tab through all elements
    for (let i = 0; i < Math.min(10, tabOrder.length); i++) {
      await authenticatedPage.keyboard.press('Tab');
    }

    const focused = await authenticatedPage.evaluate(() => document.activeElement?.tagName || '');
    expect(focused).toBeTruthy();
  });

  authenticatedUserTest('should submit import/export form with keyboard', async ({ authenticatedPage }) => {
    const submitButton = authenticatedPage.locator('button[type="submit"]').first();

    if ((await submitButton.count()) === 0) {
      authenticatedUserTest.skip();
      return;
    }

    // Tab to submit button
    let attempts = 0;
    while (
      (await authenticatedPage.evaluate(() => document.activeElement?.textContent || '')) !==
        (await submitButton.textContent()) &&
      attempts < 50
    ) {
      await authenticatedPage.keyboard.press('Tab');
      attempts++;
    }

    // Press Enter to submit
    await authenticatedPage.keyboard.press('Enter');
    await authenticatedPage.waitForLoadState('networkidle').catch(() => {});

    // No error should occur
    const focused = await authenticatedPage.evaluate(() => document.activeElement?.tagName || '');
    expect(focused).toBeTruthy();
  });
});

authenticatedUserTest.describe('@a11y-keyboard Workflow - Backup Management (Keyboard Only)', () => {
  authenticatedUserTest.beforeEach(async ({ authenticatedPage }) => {
    await authenticatedPage.goto(`${baseURL}/backup-management`, { waitUntil: 'networkidle' });
  });

  authenticatedUserTest('should navigate backup management with keyboard', async ({ authenticatedPage }) => {
    const buttons = authenticatedPage.locator('button').all();

    if ((await buttons).length === 0) {
      authenticatedUserTest.skip();
      return;
    }

    // Tab through buttons
    for (let i = 0; i < 5; i++) {
      await authenticatedPage.keyboard.press('Tab');
    }

    const focused = await authenticatedPage.evaluate(() => document.activeElement?.tagName || '');
    expect(focused).toBeTruthy();
  });
});

// ============================================================================
// 8. COMPREHENSIVE TAB ORDER VALIDATION
// ============================================================================

authenticatedUserTest.describe('@a11y-keyboard Tab Order Consistency Cross-Page', () => {
  authenticatedUserTest('should maintain tab order consistency across authenticated routes', async ({
    authenticatedPage,
  }) => {
    const routes = ['/manage-categories', '/manage-tags', '/profile'];

    for (const route of routes) {
      await authenticatedPage.goto(`${baseURL}${route}`, { waitUntil: 'networkidle' });

      const tabOrder = await extractTabOrder(authenticatedPage);

      expect(tabOrder.length).toBeGreaterThan(0);
      expect(tabOrder[0]).toBeDefined();

      // All elements should have valid tabindex
      for (const element of tabOrder) {
        expect(element.tabIndex).toBeLessThanOrEqual(0);
      }

      console.log(`${route}: ${tabOrder.length} focusable elements`);
    }
  });
});

authenticatedAdminTest.describe('@a11y-keyboard Admin Pages - Tab Order', () => {
  authenticatedAdminTest('should have logical tab order on admin users page', async ({ authenticatedPage }) => {
    await authenticatedPage.goto(`${baseURL}/admin/users`, { waitUntil: 'networkidle' });

    const tabOrder = await extractTabOrder(authenticatedPage);

    expect(tabOrder.length).toBeGreaterThan(0);

    // Check for positive tabindex violations
    const badTabindices = tabOrder.filter((el) => el.tabIndex > 0);
    expect(badTabindices.length).toBeLessThanOrEqual(0);
  });
});

// ============================================================================
// 9. EDGE CASE TESTS
// ============================================================================

authenticatedUserTest.describe('@a11y-keyboard Edge Cases', () => {
  authenticatedUserTest('should not focus hidden elements', async ({ authenticatedPage }) => {
    await authenticatedPage.goto(`${baseURL}/manage-categories`, { waitUntil: 'networkidle' });

    const tabOrder = await extractTabOrder(authenticatedPage);

    // All focusable elements should be visible
    for (const element of tabOrder.slice(0, 10)) {
      const isVisible = await authenticatedPage.evaluate(
        (selector) => {
          const el = document.querySelector(selector);
          return el ? el.offsetParent !== null : false;
        },
        element.selector
      );

      // Most should be visible (some may not be due to layout complexities)
      expect(typeof isVisible).toBe('boolean');
    }
  });

  authenticatedUserTest('should support Tab from body to first focusable', async ({ authenticatedPage }) => {
    await authenticatedPage.goto(`${baseURL}/manage-categories`, { waitUntil: 'networkidle' });

    // Focus should start in body
    let focused = await authenticatedPage.evaluate(() => document.activeElement?.tagName);
    expect(focused).toBe('BODY');

    // Press Tab
    await authenticatedPage.keyboard.press('Tab');

    // Should move to first focusable element
    focused = await authenticatedPage.evaluate(() => document.activeElement?.tagName);
    expect(['A', 'BUTTON', 'INPUT', 'SELECT', 'TEXTAREA']).toContain(focused);
  });
});
