import { test, expect } from '@playwright/test';

test('Visual verification - Skip link and focus indicators', async ({ page, context }) => {
  await page.goto('http://localhost:8003/');
  await page.waitForLoadState('networkidle');

  // Screenshot 1: Initial page load
  await page.screenshot({ path: '/tmp/1-initial-load.png', fullPage: true });

  // Screenshot 2: Tab once - should focus skip link
  await page.keyboard.press('Tab');
  await page.waitForTimeout(500);
  await page.screenshot({ path: '/tmp/2-skip-link-focused.png', fullPage: true });

  // Verify skip link is focused
  const skipLinkFocused = await page.evaluate(() => {
    return document.activeElement?.classList.contains('skip-link');
  });
  console.log('Skip link is focused:', skipLinkFocused);
  expect(skipLinkFocused).toBe(true);

  // Screenshot 3: Tab again to next element
  await page.keyboard.press('Tab');
  await page.waitForTimeout(500);
  await page.screenshot({ path: '/tmp/3-logo-focused.png', fullPage: true });

  // Screenshot 4: Tab to form fields
  for (let i = 0; i < 3; i++) {
    await page.keyboard.press('Tab');
  }
  await page.waitForTimeout(500);
  await page.screenshot({ path: '/tmp/4-form-element-focused.png', fullPage: true });

  // Check focus indicator is visible
  const focusIndicator = await page.evaluate(() => {
    const el = document.activeElement as HTMLElement;
    const style = window.getComputedStyle(el);
    return {
      element: el?.tagName,
      hasFocusVisible: el?.matches(':focus-visible') || false,
      outline: style.outline,
      ring: style.boxShadow
    };
  });
  console.log('Focus indicator:', JSON.stringify(focusIndicator));
  expect(focusIndicator.hasFocusVisible || focusIndicator.outline !== 'none').toBeTruthy();

  // Screenshot 5: Shift+Tab to go back
  await page.keyboard.press('Shift+Tab');
  await page.waitForTimeout(500);
  await page.screenshot({ path: '/tmp/5-shift-tab-back.png', fullPage: true });

  console.log('All visual verification tests passed');
});
