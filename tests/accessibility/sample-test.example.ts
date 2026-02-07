// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

/**
 * Sample accessibility tests demonstrating utility usage
 * These are EXAMPLE tests showing how to use the accessibility testing utilities
 * Copy and adapt these patterns for your own tests
 */

import { test, expect } from '@playwright/test';
import {
  testTextContrast,
  testUIContrast,
  validateFormLabels,
  validateButtonLabels,
  checkLandmarkRegions,
  validateHeadingHierarchy,
  extractTabOrder,
  testKeyboardNavigation,
  verifyFocusIndicators,
  validateSkipLinks,
  captureElementStates,
} from './utils/index.js';
import { authenticatedUserTest } from './fixtures/auth.js';

/**
 * Example 1: Basic contrast and semantic validation
 */
test('EXAMPLE: Login page has proper contrast and semantic structure', async ({ page }) => {
  await page.goto('/auth/login');

  // Test heading hierarchy is correct
  const hierarchy = await validateHeadingHierarchy(page);
  expect(hierarchy.validHierarchy).toBe(true);
  if (!hierarchy.validHierarchy) {
    console.log('Heading issues:', hierarchy.issues);
  }

  // Test all form inputs are labeled
  const labels = await validateFormLabels(page);
  expect(labels.allLabeled).toBe(true);
  if (!labels.allLabeled) {
    console.log('Unlabeled inputs:', labels.unlabeledElements);
  }

  // Test text contrast on labels
  const labelElements = await page.locator('label').all();
  for (const label of labelElements) {
    const contrast = await testTextContrast(page, label, 'AA');
    expect(contrast.passes).toBe(true);
  }

  // Test button contrast (UI component level)
  const submitButton = page.locator('button[type="submit"]');
  const buttonContrast = await testUIContrast(page, submitButton, 'AA');
  expect(buttonContrast.passes).toBe(true);
});

/**
 * Example 2: Keyboard navigation testing
 */
test('EXAMPLE: Form is fully keyboard navigable', async ({ page }) => {
  await page.goto('/auth/login');

  // Get all focusable elements
  const tabOrder = await extractTabOrder(page);
  console.log(`Found ${tabOrder.length} focusable elements`);
  expect(tabOrder.length).toBeGreaterThan(0);

  // Test Tab key navigation works
  const navResult = await testKeyboardNavigation(page);
  expect(navResult.success).toBe(true);
  if (!navResult.success) {
    console.log('Navigation issues:', navResult.issues);
  }

  // Verify all focusable elements have visible focus indicators
  const focusResult = await verifyFocusIndicators(page);
  expect(focusResult.elementsWithoutFocus).toBe(0);
  if (focusResult.elementsWithoutFocus > 0) {
    console.log('Elements without focus indicators:', focusResult.details);
  }
});

/**
 * Example 3: Button and form accessibility
 */
test('EXAMPLE: All interactive elements are properly labeled', async ({ page }) => {
  await page.goto('/');

  // Validate all buttons have accessible names
  const buttonLabels = await validateButtonLabels(page);
  expect(buttonLabels.allButtonsLabeled).toBe(true);
  if (!buttonLabels.allButtonsLabeled) {
    console.log('Unlabeled buttons:', buttonLabels.unlabeledSelectors);
  }

  // Validate all form inputs have labels
  const formLabels = await validateFormLabels(page);
  expect(formLabels.allLabeled).toBe(true);

  // Test contrast on all buttons
  const buttons = await page.locator('button').all();
  for (const button of buttons) {
    const contrast = await testUIContrast(page, button, 'AA');
    expect(contrast.passes).toBe(true);
  }
});

/**
 * Example 4: Page structure and landmarks
 */
test('EXAMPLE: Page has proper semantic structure and landmarks', async ({ page }) => {
  await page.goto('/');

  // Check for landmark regions (header, main, footer, nav)
  const landmarks = await checkLandmarkRegions(page);
  expect(landmarks.hasLandmarks).toBe(true);

  // Check heading hierarchy
  const hierarchy = await validateHeadingHierarchy(page);
  expect(hierarchy.validHierarchy).toBe(true);

  // Check for skip links to main content
  const skipLinks = await validateSkipLinks(page);
  console.log('Skip links:', skipLinks.skipLinks);
});

/**
 * Example 5: Testing authenticated pages
 */
authenticatedUserTest('EXAMPLE: Profile page is accessible to authenticated users', async ({
  authenticatedPage,
}) => {
  await authenticatedPage.goto('/auth/profile');

  // Test form labeling
  const labels = await validateFormLabels(authenticatedPage);
  expect(labels.allLabeled).toBe(true);

  // Test button labels
  const buttons = await validateButtonLabels(authenticatedPage);
  expect(buttons.allButtonsLabeled).toBe(true);

  // Test keyboard navigation
  const navResult = await testKeyboardNavigation(authenticatedPage);
  expect(navResult.success).toBe(true);
});

/**
 * Example 6: Capturing element states for visual review
 */
test('EXAMPLE: Capture element states for visual comparison', async ({ page }) => {
  await page.goto('/');

  // Capture button in different states
  const button = page.locator('button:visible').first();
  const states = await captureElementStates(page, button, '/tmp/example-button');

  // States captured: normal, hover, focus, active
  console.log('Screenshots saved:', states);
  expect(states.normal).toBeTruthy();
  expect(states.focus).toBeTruthy();
});

/**
 * Example 7: Batch testing multiple elements
 */
test('EXAMPLE: Test contrast on all text and buttons', async ({ page }) => {
  await page.goto('/');

  // Test all paragraphs
  const paragraphs = await page.locator('p').all();
  let failedContrasts = 0;

  for (const paragraph of paragraphs) {
    const result = await testTextContrast(page, paragraph, 'AA');
    if (!result.passes) {
      failedContrasts++;
      console.log(`Low contrast paragraph:`, result);
    }
  }

  expect(failedContrasts).toBe(0);

  // Test all buttons
  const buttons = await page.locator('button').all();
  let failedButtons = 0;

  for (const btn of buttons) {
    const result = await testUIContrast(page, btn, 'AA');
    if (!result.passes) {
      failedButtons++;
      console.log(`Low contrast button:`, result);
    }
  }

  expect(failedButtons).toBe(0);
});

/**
 * Example 8: Focus-specific testing
 * Tests that focus indicators are visible when using keyboard navigation
 */
test('EXAMPLE: Focus indicators are visible for keyboard navigation', async ({ page }) => {
  await page.goto('/');

  // Tab to first element
  await page.keyboard.press('Tab');

  // Get currently focused element
  const activeElement = page.locator(':focus');

  // Verify it has a visible focus indicator
  const focusIndicator = await activeElement.evaluate((el) => {
    const style = window.getComputedStyle(el, ':focus');
    const outline = style.outline || style.outlineWidth;
    const boxShadow = style.boxShadow;
    return (outline && outline !== 'none') || (boxShadow && boxShadow !== 'none');
  });

  expect(focusIndicator).toBe(true);
});

/**
 * Example 9: Contrast level validation (AA vs AAA)
 */
test('EXAMPLE: Validate different WCAG conformance levels', async ({ page }) => {
  await page.goto('/');

  const heading = page.locator('h1').first();

  // Test AA compliance (4.5:1)
  const aaResult = await testTextContrast(page, heading, 'AA');
  console.log(`AA Contrast: ${aaResult.ratio}:1 (required: ${aaResult.required}:1)`);
  expect(aaResult.passes).toBe(true);

  // Test AAA compliance (7:1) - might not pass
  const aaaResult = await testTextContrast(page, heading, 'AAA');
  console.log(`AAA Contrast: ${aaaResult.ratio}:1 (required: ${aaaResult.required}:1)`);
  // AAA is stricter, so it's okay if this fails
});

/**
 * Example 10: Real-world workflow test
 * Tests a complete user interaction while ensuring accessibility
 */
test('EXAMPLE: Complete login workflow is accessible', async ({ page }) => {
  // 1. Navigate to login page
  await page.goto('/auth/login');

  // 2. Verify page structure
  const structure = await checkLandmarkRegions(page);
  expect(structure.hasLandmarks).toBe(true);

  // 3. Verify form is accessible
  const labels = await validateFormLabels(page);
  expect(labels.allLabeled).toBe(true);

  // 4. Verify keyboard navigation works
  const navResult = await testKeyboardNavigation(page);
  expect(navResult.success).toBe(true);

  // 5. Perform login (assuming test credentials are set up)
  const username = page.locator('#username-or-email');
  const password = page.locator('#password');
  const submit = page.locator('button[type="submit"]');

  // Use keyboard navigation to fill form
  await username.fill('test@example.com');
  await password.fill('testpassword');
  await submit.click();

  // 6. Verify we logged in successfully
  await page.waitForURL('/', { timeout: 10000 });
});
