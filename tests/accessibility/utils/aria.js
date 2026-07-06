// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

/**
 * ARIA attribute validation utilities for accessibility testing
 * Implements checks for ARIA labels, landmarks, form labels, and live regions
 */

/**
 * Check if element has accessible name
 * Accessible name can come from:
 * - aria-label
 * - aria-labelledby
 * - Explicit <label> element
 * - Text content for certain elements
 * - title attribute
 *
 * @param {import('@playwright/test').Locator} element - Element to check
 * @returns {Promise<{hasAccessibleName: boolean, name: string, sources: string[]}>} Accessible name info
 */
export async function checkAccessibleName(element) {
  return await element.evaluate((el) => {
    const sources = [];
    let name = '';

    // Check aria-label
    const ariaLabel = el.getAttribute('aria-label');
    if (ariaLabel?.trim()) {
      sources.push('aria-label');
      name = ariaLabel;
      return { hasAccessibleName: true, name, sources };
    }

    // Check aria-labelledby
    const ariaLabelledBy = el.getAttribute('aria-labelledby');
    if (ariaLabelledBy) {
      const ids = ariaLabelledBy.split(/\s+/);
      const labelTexts = ids
        .map((id) => document.getElementById(id)?.textContent?.trim())
        .filter(Boolean);
      if (labelTexts.length > 0) {
        sources.push('aria-labelledby');
        name = labelTexts.join(' ');
        return { hasAccessibleName: true, name, sources };
      }
    }

    // Check associated label for form elements
    if (el.tagName === 'INPUT' || el.tagName === 'SELECT' || el.tagName === 'TEXTAREA') {
      if (el.id) {
        const label = document.querySelector(`label[for="${el.id}"]`);
        if (label?.textContent?.trim()) {
          sources.push('associated label');
          name = label.textContent.trim();
          return { hasAccessibleName: true, name, sources };
        }
      }
    }

    // Check text content for buttons, links, headings
    if (['BUTTON', 'A', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6'].includes(el.tagName)) {
      const text = el.textContent?.trim();
      if (text) {
        sources.push('text content');
        name = text;
        return { hasAccessibleName: true, name, sources };
      }
    }

    // Check title attribute as last resort
    const title = el.getAttribute('title');
    if (title?.trim()) {
      sources.push('title attribute');
      name = title;
      return { hasAccessibleName: true, name, sources };
    }

    return { hasAccessibleName: false, name: '', sources };
  });
}

/**
 * Validate that an element has required ARIA attributes
 *
 * @param {import('@playwright/test').Locator} element - Element to validate
 * @param {string[]} requiredAttrs - ARIA attributes that must be present
 * @returns {Promise<{valid: boolean, missing: string[], present: string[]}>} Validation results
 */
export async function validateAriaAttributes(element, requiredAttrs) {
  return await element.evaluate((el, attrs) => {
    const present = [];
    const missing = [];

    for (const attr of attrs) {
      if (el.hasAttribute(attr)) {
        present.push(attr);
      } else {
        missing.push(attr);
      }
    }

    return {
      valid: missing.length === 0,
      missing,
      present,
    };
  }, requiredAttrs);
}

/**
 * Check for WCAG 2.1 landmark regions on the page
 * Required landmarks: banner, main, navigation (if multiple sections)
 *
 * @param {import('@playwright/test').Page} page - Page to check
 * @returns {Promise<{hasLandmarks: boolean, landmarks: {role: string, count: number}[]}>} Landmark info
 */
export async function checkLandmarkRegions(page) {
  return await page.evaluate(() => {
    const landmarks = {};

    // Check for banner (typically header)
    const banner = document.querySelector('[role="banner"], header:not(header *)')?.outerHTML;
    if (banner) landmarks.banner = (landmarks.banner || 0) + 1;

    // Check for main content
    const main = document.querySelector('[role="main"], main')?.outerHTML;
    if (main) landmarks.main = (landmarks.main || 0) + 1;

    // Check for navigation
    const nav = document.querySelectorAll('[role="navigation"], nav');
    if (nav.length > 0) landmarks.navigation = nav.length;

    // Check for contentinfo (footer)
    const footer = document.querySelector('[role="contentinfo"], footer:not(footer *)')?.outerHTML;
    if (footer) landmarks.contentinfo = (landmarks.contentinfo || 0) + 1;

    const hasLandmarks = Object.keys(landmarks).length > 0;

    return {
      hasLandmarks,
      landmarks: Object.entries(landmarks).map(([role, count]) => ({ role, count })),
    };
  });
}

/**
 * Validate form label associations
 * Checks that all form inputs have associated labels
 *
 * @param {import('@playwright/test').Page} page - Page to check
 * @returns {Promise<{
 *   allLabeled: boolean,
 *   labeled: number,
 *   unlabeled: number,
 *   unlabeledElements: Array<{id: string, type: string}>
 * }>} Form labeling validation
 */
export async function validateFormLabels(page) {
  return await page.evaluate(() => {
    const inputs = document.querySelectorAll('input, select, textarea');
    const unlabeledElements = [];
    let labeled = 0;

    for (const input of inputs) {
      // Skip hidden inputs
      if (input.type === 'hidden') continue;

      // Check for aria-label
      if (input.hasAttribute('aria-label')) {
        labeled++;
        continue;
      }

      // Check for aria-labelledby
      if (input.hasAttribute('aria-labelledby')) {
        labeled++;
        continue;
      }

      // Check for associated label
      if (input.id) {
        const label = document.querySelector(`label[for="${input.id}"]`);
        if (label) {
          labeled++;
          continue;
        }
      }

      // Check if inside a label
      if (input.closest('label')) {
        labeled++;
        continue;
      }

      // Unlabeled
      unlabeledElements.push({
        id: input.id || 'no-id',
        type: input.tagName.toLowerCase(),
      });
    }

    const total = inputs.length;
    const unlabeled = unlabeledElements.length;

    return {
      allLabeled: unlabeled === 0,
      labeled,
      unlabeled,
      unlabeledElements,
    };
  });
}

/**
 * Check for ARIA live regions (notifications, alerts, status updates)
 *
 * @param {import('@playwright/test').Page} page - Page to check
 * @returns {Promise<{hasLiveRegions: boolean, regions: Array<{role: string, ariaLive: string}>}>} Live region info
 */
export async function checkLiveRegions(page) {
  return await page.evaluate(() => {
    const regions = [];

    // Check for explicit live regions
    const liveElements = document.querySelectorAll('[aria-live], [role="alert"], [role="status"]');

    for (const element of liveElements) {
      regions.push({
        role: element.getAttribute('role') || 'generic',
        ariaLive: element.getAttribute('aria-live') || 'off',
        ariaAtomic: element.getAttribute('aria-atomic') || 'false',
        ariaRelevant: element.getAttribute('aria-relevant') || 'additions text',
      });
    }

    return {
      hasLiveRegions: regions.length > 0,
      regions,
    };
  });
}

/**
 * Validate that buttons have accessible names
 * Buttons must have text content, aria-label, or aria-labelledby
 *
 * @param {import('@playwright/test').Page} page - Page to check
 * @returns {Promise<{
 *   allButtonsLabeled: boolean,
 *   labeled: number,
 *   unlabeled: number,
 *   unlabeledSelectors: string[]
 * }>} Button labeling validation
 */
export async function validateButtonLabels(page) {
  return await page.evaluate(() => {
    const buttons = document.querySelectorAll('button, [role="button"]');
    const unlabeledSelectors = [];
    let labeled = 0;

    for (const button of buttons) {
      // Check aria-label
      if (button.hasAttribute('aria-label') && button.getAttribute('aria-label')?.trim()) {
        labeled++;
        continue;
      }

      // Check aria-labelledby
      if (button.hasAttribute('aria-labelledby')) {
        labeled++;
        continue;
      }

      // Check text content
      if (button.textContent?.trim()) {
        labeled++;
        continue;
      }

      // Check title attribute
      if (button.hasAttribute('title') && button.getAttribute('title')?.trim()) {
        labeled++;
        continue;
      }

      // Unlabeled - generate selector for identification
      const selector = button.id
        ? `#${button.id}`
        : button.className
          ? `.${button.className.split(/\s+/)[0]}`
          : 'button';
      unlabeledSelectors.push(selector);
    }

    const total = buttons.length;
    const unlabeled = unlabeledSelectors.length;

    return {
      allButtonsLabeled: unlabeled === 0,
      labeled,
      unlabeled,
      unlabeledSelectors,
    };
  });
}

/**
 * Check for proper heading hierarchy
 * Headings should not skip levels (e.g., H1 to H3 is bad)
 *
 * @param {import('@playwright/test').Page} page - Page to check
 * @returns {Promise<{
 *   validHierarchy: boolean,
 *   headings: Array<{level: number, text: string}>,
 *   issues: string[]
 * }>} Heading hierarchy validation
 */
export async function validateHeadingHierarchy(page) {
  return await page.evaluate(() => {
    const headings = [];
    const issues = [];

    document.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach((heading) => {
      const level = parseInt(heading.tagName[1]);
      headings.push({
        level,
        text: heading.textContent?.trim() || '',
      });
    });

    // Check hierarchy
    let previousLevel = 0;
    for (const heading of headings) {
      if (heading.level > previousLevel + 1) {
        issues.push(
          `Heading hierarchy skip: H${previousLevel || 'start'} to H${heading.level} at "${heading.text}"`
        );
      }
      previousLevel = heading.level;
    }

    return {
      validHierarchy: issues.length === 0,
      headings,
      issues,
    };
  });
}

/**
 * Get all ARIA attribute values on an element
 *
 * @param {import('@playwright/test').Locator} element - Element to inspect
 * @returns {Promise<Record<string, string>>} All aria-* attributes and values
 */
export async function getAriaAttributes(element) {
  return await element.evaluate((el) => {
    const ariaAttrs = {};
    for (const attr of el.attributes) {
      if (attr.name.startsWith('aria-')) {
        ariaAttrs[attr.name] = attr.value;
      }
    }
    return ariaAttrs;
  });
}

/**
 * Batch validate accessible names for multiple elements
 *
 * @param {import('@playwright/test').Page} page - Page context
 * @param {string} selector - CSS selector for elements
 * @returns {Promise<Array>} Array of results for each element
 */
export async function validateAccessibleNamesBatch(page, selector) {
  const elements = await page.locator(selector).all();
  const results = [];

  for (const element of elements) {
    const nameInfo = await checkAccessibleName(element);
    results.push({
      ...nameInfo,
      selector,
    });
  }

  return results;
}
