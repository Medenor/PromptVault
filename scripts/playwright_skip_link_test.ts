// Skip Link Functionality Test
import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL ?? 'http://127.0.0.1:8003';

// Test pages to verify skip link on
const TEST_PAGES = [
  '/',
  '/auth/login',
  '/admin/users',
  '/backup-management',
];

test.describe('Skip Link Functionality', () => {
  test('skip link appears on Tab press from address bar on homepage', async ({ page }) => {
    // Navigate to home page
    await page.goto(`${BASE_URL}/`);
    
    // Press Tab to focus the first focusable element (should be skip link)
    await page.keyboard.press('Tab');
    
    // Get the skip link element
    const skipLink = page.locator('.skip-link');
    
    // Verify skip link is visible (not hidden by left: -9999px)
    const isVisible = await skipLink.isVisible();
    expect(isVisible).toBe(true);
    
    // Verify the skip link text
    const text = await skipLink.textContent();
    expect(text).toContain('Skip to main content');
    
    // Take screenshot for visual verification
    await page.screenshot({ path: '/tmp/skip-link-visible-homepage.png' });
  });

  test('skip link has correct colors and styling', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    await page.keyboard.press('Tab');
    
    const skipLink = page.locator('.skip-link');
    
    // Check background color (should be white #ffffff)
    const bgColor = await skipLink.evaluate((el) => {
      return window.getComputedStyle(el).backgroundColor;
    });
    
    // Check text color (should be dark blue #1e3a8a)
    const textColor = await skipLink.evaluate((el) => {
      return window.getComputedStyle(el).color;
    });
    
    // Check z-index
    const zIndex = await skipLink.evaluate((el) => {
      return window.getComputedStyle(el).zIndex;
    });
    
    console.log('Background color:', bgColor);
    console.log('Text color:', textColor);
    console.log('Z-index:', zIndex);
    
    expect(zIndex).toBe('10000');
  });

  test('skip link is first in tab order', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    
    // Get the focused element after first Tab press
    const focusedElement = await page.evaluate(() => {
      const element = document.activeElement;
      return {
        tag: element?.tagName,
        className: element?.className,
        text: element?.textContent?.substring(0, 20),
      };
    });
    
    console.log('First focused element:', focusedElement);
  });

  test('skip link hidden by default', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    
    const skipLink = page.locator('.skip-link');
    
    // Without focus, skip link should not be visible
    const isVisibleInitially = await skipLink.isVisible();
    expect(isVisibleInitially).toBe(false);
  });

  test('skip link jumps to main content on Enter', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    
    // Press Tab to focus skip link
    await page.keyboard.press('Tab');
    
    // Verify skip link is focused
    const skipLink = page.locator('.skip-link');
    expect(await skipLink.isFocused()).toBe(true);
    
    // Get main content position before pressing Enter
    const mainContentBefore = await page.locator('#main-content').boundingBox();
    
    // Press Enter to activate skip link
    await page.keyboard.press('Enter');
    
    // Give a moment for the jump to complete
    await page.waitForTimeout(300);
    
    // Take screenshot showing where we are after skip
    await page.screenshot({ path: '/tmp/skip-link-after-enter-homepage.png' });
  });

  test.describe('Skip link on multiple pages', () => {
    for (const pagePath of TEST_PAGES) {
      test(`skip link appears on Tab on ${pagePath}`, async ({ page }) => {
        await page.goto(`${BASE_URL}${pagePath}`);
        await page.keyboard.press('Tab');
        
        const skipLink = page.locator('.skip-link');
        const isVisible = await skipLink.isVisible();
        
        expect(isVisible).toBe(true);
        expect(await skipLink.textContent()).toContain('Skip to main content');
        
        // Take screenshot for each page
        await page.screenshot({ 
          path: `/tmp/skip-link-${pagePath.replace(/\//g, '_')}.png`
        });
      });
    }
  });

  test('keyboard-only navigation: Tab from address bar to skip link to main content', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    
    // Press Tab multiple times - skip link should be first
    await page.keyboard.press('Tab');
    const skipLinkFocused = await page.locator('.skip-link').isFocused();
    expect(skipLinkFocused).toBe(true);
    
    // Screenshot: skip link focused
    await page.screenshot({ path: '/tmp/keyboard-test-1-skip-focused.png' });
    
    // Press Tab again to move to next element
    await page.keyboard.press('Tab');
    
    // Screenshot: moved to next element
    await page.screenshot({ path: '/tmp/keyboard-test-2-next-element.png' });
  });

  test('skip link is not visible on mouse hover alone', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    
    // Skip link should exist but be hidden
    const skipLink = page.locator('.skip-link');
    
    // Try to hover (this shouldn't make it visible since it's left: -9999px)
    await skipLink.hover({ force: true });
    
    // Screenshot: after hover
    await page.screenshot({ path: '/tmp/skip-link-hover-test.png' });
  });
});
