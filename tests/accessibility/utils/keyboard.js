// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

/**
 * Keyboard navigation utilities for accessibility testing
 * Tests tab order, focus indicators, keyboard shortcuts, and roving tabindex patterns
 */

/**
 * Extract tab order from a page
 * Returns all focusable elements in tab order
 *
 * @param {import('@playwright/test').Page} page - Page to analyze
 * @returns {Promise<Array<{
 *   selector: string,
 *   text: string,
 *   tabIndex: number,
 *   isNaturallyFocusable: boolean
 * }>} Elements in tab order
 */
export async function extractTabOrder(page) {
  return await page.evaluate(() => {
    const focusableSelectors = [
      'a[href]',
      'button:not([disabled])',
      'input:not([disabled])',
      'select:not([disabled])',
      'textarea:not([disabled])',
      '[tabindex]:not([tabindex="-1"])',
    ];

    const focusableElements = [];

    for (const selector of focusableSelectors) {
      document.querySelectorAll(selector).forEach((el) => {
        // Skip if already added
        if (focusableElements.find((item) => item.element === el)) return;

        // Skip if hidden
        if (!el.offsetParent && el.style.display !== 'none') return;

        const tabIndex = parseInt(el.getAttribute('tabindex') || '0');
        const isNaturallyFocusable = ['A', 'BUTTON', 'INPUT', 'SELECT', 'TEXTAREA'].includes(
          el.tagName
        );

        focusableElements.push({
          element: el,
          selector: el.id ? `#${el.id}` : el.className ? `.${el.className.split(/\s+/)[0]}` : el.tagName,
          text: el.textContent?.trim().substring(0, 50) || '',
          tabIndex,
          isNaturallyFocusable,
        });
      });
    }

    // Sort by tab order: positive tabindex first (in order), then 0 (document order)
    focusableElements.sort((a, b) => {
      if (a.tabIndex > 0 && b.tabIndex > 0) return a.tabIndex - b.tabIndex;
      if (a.tabIndex > 0) return -1;
      if (b.tabIndex > 0) return 1;
      return 0;
    });

    return focusableElements.map((item) => ({
      selector: item.selector,
      text: item.text,
      tabIndex: item.tabIndex,
      isNaturallyFocusable: item.isNaturallyFocusable,
    }));
  });
}

/**
 * Test keyboard navigation through focusable elements
 * Simulates Tab key presses and checks focus moves correctly
 *
 * @param {import('@playwright/test').Page} page - Page to test
 * @returns {Promise<{
 *   success: boolean,
 *   tabOrder: string[],
 *   focusableElements: number,
 *   issues: string[]
 * }>} Keyboard navigation test results
 */
export async function testKeyboardNavigation(page) {
  const issues = [];
  const tabOrder = [];

  // First, get the initial focusable elements
  const focusableElements = await extractTabOrder(page);
  const focusableSelectors = focusableElements.map((el) => el.selector);

  if (focusableSelectors.length === 0) {
    return {
      success: true,
      tabOrder: [],
      focusableElements: 0,
      issues: [],
    };
  }

  // Try to simulate Tab navigation
  try {
    // First Tab should focus first element
    await page.keyboard.press('Tab');
    const firstFocused = await page.evaluate(() => document.activeElement?.id || '');

    tabOrder.push(firstFocused);

    // Press Tab multiple times and track focus
    for (let i = 1; i < focusableSelectors.length; i++) {
      await page.keyboard.press('Tab');
      const focused = await page.evaluate(() => document.activeElement?.id || '');
      tabOrder.push(focused);

      // Check if focus moved
      if (i > 0 && tabOrder[i] === tabOrder[i - 1]) {
        issues.push(`Focus did not move on Tab #${i}`);
      }
    }
  } catch (error) {
    issues.push(`Error during keyboard navigation test: ${error.message}`);
  }

  return {
    success: issues.length === 0,
    tabOrder: tabOrder.filter(Boolean),
    focusableElements: focusableSelectors.length,
    issues,
  };
}

/**
 * Check if elements have visible focus indicators
 * Tests both CSS outline and custom focus styles
 *
 * @param {import('@playwright/test').Page} page - Page to check
 * @returns {Promise<{
 *   hasFocusIndicators: boolean,
 *   elementsWithFocus: number,
 *   elementsWithoutFocus: number,
 *   details: Array<{selector: string, hasFocus: boolean, outline: string}>
 * }>} Focus indicator validation
 */
export async function verifyFocusIndicators(page) {
  const focusableElements = await extractTabOrder(page);
  const details = [];
  let elementsWithFocus = 0;
  let elementsWithoutFocus = 0;

  for (const element of focusableElements) {
    const hasFocus = await page.evaluate(
      (selector) => {
        const el = document.querySelector(selector);
        if (!el) return false;

        const style = window.getComputedStyle(el, ':focus');
        const outline = style.outline || style.outlineWidth;
        const boxShadow = style.boxShadow;

        // Check for visible focus indicator
        return (
          (outline && outline !== 'none') || (boxShadow && boxShadow !== 'none')
        );
      },
      element.selector
    );

    const outline = await page.evaluate(
      (selector) => {
        const el = document.querySelector(selector);
        if (!el) return '';
        const style = window.getComputedStyle(el, ':focus');
        return style.outline || '';
      },
      element.selector
    );

    details.push({
      selector: element.selector,
      hasFocus,
      outline,
    });

    if (hasFocus) {
      elementsWithFocus++;
    } else {
      elementsWithoutFocus++;
    }
  }

  return {
    hasFocusIndicators: elementsWithoutFocus === 0,
    elementsWithFocus,
    elementsWithoutFocus,
    details,
  };
}

/**
 * Test specific keyboard shortcuts
 *
 * @param {import('@playwright/test').Page} page - Page to test
 * @param {Array<{key: string, expected: string | Function}>} shortcuts - Shortcuts to test
 * @returns {Promise<Array<{key: string, works: boolean, result: any}>>} Test results for each shortcut
 */
export async function testKeyboardShortcuts(page, shortcuts) {
  const results = [];

  for (const shortcut of shortcuts) {
    try {
      const initialFocus = await page.evaluate(() => document.activeElement?.id || '');

      // Press the shortcut
      await page.keyboard.press(shortcut.key);

      // Check expected result
      let works = false;
      let result = null;

      if (typeof shortcut.expected === 'function') {
        result = await shortcut.expected(page);
        works = result === true;
      } else if (typeof shortcut.expected === 'string') {
        const finalFocus = await page.evaluate(() => document.activeElement?.id || '');
        works = finalFocus === shortcut.expected;
        result = finalFocus;
      }

      results.push({
        key: shortcut.key,
        works,
        result,
      });
    } catch (error) {
      results.push({
        key: shortcut.key,
        works: false,
        result: error.message,
      });
    }
  }

  return results;
}

/**
 * Test Shift+Tab backward navigation
 *
 * @param {import('@playwright/test').Page} page - Page to test
 * @returns {Promise<{
 *   success: boolean,
 *   backwardTabOrder: string[],
 *   issues: string[]
 * }>} Backward navigation test results
 */
export async function testBackwardNavigation(page) {
  const issues = [];
  const backwardTabOrder = [];

  try {
    // Focus the last element
    const focusableElements = await extractTabOrder(page);
    if (focusableElements.length === 0) {
      return {
        success: true,
        backwardTabOrder: [],
        issues: [],
      };
    }

    // Go to end of page
    await page.keyboard.press('End');
    await page.keyboard.press('Tab');

    // Now use Shift+Tab to go backward
    for (let i = 0; i < focusableElements.length; i++) {
      await page.keyboard.press('Shift+Tab');
      const focused = await page.evaluate(() => document.activeElement?.id || '');
      backwardTabOrder.push(focused);
    }

    // Check if we cycled properly
    if (backwardTabOrder.length < focusableElements.length / 2) {
      issues.push('Shift+Tab cycling incomplete');
    }
  } catch (error) {
    issues.push(`Error during Shift+Tab test: ${error.message}`);
  }

  return {
    success: issues.length === 0,
    backwardTabOrder: backwardTabOrder.filter(Boolean),
    issues,
  };
}

/**
 * Check for roving tabindex pattern (common in lists, grids, tabs)
 * Only one element in group should have tabindex="0", rest should have tabindex="-1"
 *
 * @param {import('@playwright/test').Page} page - Page to check
 * @param {string} containerSelector - Selector for the container with roving tabindex
 * @returns {Promise<{
 *   isRovingTabindex: boolean,
 *   activeIndex: number,
 *   items: Array<{selector: string, tabIndex: number, ariaSelected: boolean}>,
 *   violations: string[]
 * }>} Roving tabindex pattern validation
 */
export async function validateRovingTabindex(page, containerSelector) {
  return await page.evaluate(
    (selector) => {
      const container = document.querySelector(selector);
      if (!container) {
        return {
          isRovingTabindex: false,
          activeIndex: -1,
          items: [],
          violations: [`Container not found: ${selector}`],
        };
      }

      const items = Array.from(container.querySelectorAll('[role="tab"], [role="menuitem"], li, [role="option"]'))
        .map((item, index) => ({
          selector: item.id || `item-${index}`,
          tabIndex: parseInt(item.getAttribute('tabindex') || '-1'),
          ariaSelected: item.getAttribute('aria-selected') === 'true',
        }))
        .filter((item) => item.tabIndex !== null);

      const violations = [];
      let activeCount = 0;

      for (const item of items) {
        if (item.tabIndex === 0) {
          activeCount++;
        } else if (item.tabIndex !== -1 && item.tabIndex !== 0) {
          violations.push(`Invalid tabIndex ${item.tabIndex} on ${item.selector}`);
        }
      }

      if (activeCount !== 1) {
        violations.push(
          `Expected exactly one item with tabindex="0", found ${activeCount}`
        );
      }

      return {
        isRovingTabindex: violations.length === 0 && items.length > 0,
        activeIndex: items.findIndex((item) => item.tabIndex === 0),
        items,
        violations,
      };
    },
    containerSelector
  );
}

/**
 * Test Enter/Space key activation on custom elements
 *
 * @param {import('@playwright/test').Page} page - Page to test
 * @param {string} selector - Selector for element to test
 * @param {string} key - Key to test ('Enter' or ' ')
 * @returns {Promise<{key: string, triggered: boolean, error: string | null}>} Key activation test
 */
export async function testKeyActivation(page, selector, key = 'Enter') {
  try {
    const element = page.locator(selector);
    await element.focus();

    const initialState = await element.evaluate((el) => ({
      classList: Array.from(el.classList),
      attribute: el.getAttribute('aria-pressed'),
    }));

    await page.keyboard.press(key === ' ' ? 'Space' : 'Enter');

    const finalState = await element.evaluate((el) => ({
      classList: Array.from(el.classList),
      attribute: el.getAttribute('aria-pressed'),
    }));

    const triggered =
      JSON.stringify(initialState) !== JSON.stringify(finalState);

    return {
      key,
      triggered,
      error: null,
    };
  } catch (error) {
    return {
      key,
      triggered: false,
      error: error.message,
    };
  }
}

/**
 * Check that skip links are present and functional
 *
 * @param {import('@playwright/test').Page} page - Page to check
 * @returns {Promise<{
 *   hasSkipLink: boolean,
 *   skipLinks: Array<{text: string, href: string, target: string}>,
 *   issues: string[]
 * }>} Skip link validation
 */
export async function validateSkipLinks(page) {
  return await page.evaluate(() => {
    const skipLinks = [];
    const issues = [];

    // Look for skip links (usually hidden until focused)
    const links = document.querySelectorAll('a[href^="#"]');

    for (const link of links) {
      const href = link.getAttribute('href');
      const target = href ? document.querySelector(href) : null;

      if (href && href.startsWith('#')) {
        skipLinks.push({
          text: link.textContent?.trim() || '',
          href,
          target: target ? target.tagName : 'not-found',
        });

        // Check if target exists
        if (!target) {
          issues.push(`Skip link target not found: ${href}`);
        }
      }
    }

    // Warn if no skip links found
    if (skipLinks.length === 0) {
      issues.push('No skip links found (expected at least one to skip to main content)');
    }

    return {
      hasSkipLink: skipLinks.length > 0 && issues.length === 0,
      skipLinks,
      issues,
    };
  });
}
