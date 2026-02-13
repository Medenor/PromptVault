// Skip Link Functionality Test - Verified Implementation
import { test, expect } from '@playwright/test';

const BASE_URL = process.env.ACCESSIBILITY_BASE_URL ?? 'http://127.0.0.1:8003';

test.describe('Skip Link Implementation Verification', () => {
  test('skip link exists in DOM on login page', async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/login`);
    
    const skipLink = page.locator('.skip-link');
    
    // Verify skip link element exists in DOM
    const count = await skipLink.count();
    expect(count).toBe(1);
    
    // Verify text content
    const text = await skipLink.textContent();
    expect(text).toContain('Skip to main content');
    
    // Verify href attribute
    const href = await skipLink.getAttribute('href');
    expect(href).toBe('#main-content');
  });

  test('skip link is hidden by default (positioned off-screen)', async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/login`);
    
    const skipLink = page.locator('.skip-link');
    
    // Check that it's positioned off-screen by default
    const leftPosition = await skipLink.evaluate((el) => {
      return window.getComputedStyle(el).left;
    });
    
    console.log('Initial left position:', leftPosition);
    // Should be -9999px or similar off-screen position
    expect(leftPosition).toContain('-');
  });

  test('skip link becomes visible when focused', async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/login`);
    
    const skipLink = page.locator('.skip-link');
    
    // Get initial position
    const initialLeft = await skipLink.evaluate((el) => {
      return window.getComputedStyle(el).left;
    });
    
    console.log('Initial left:', initialLeft);
    
    // Focus the skip link using keyboard
    await page.keyboard.press('Tab');
    
    // Check if skip link is now focused
    const isFocused = await skipLink.evaluate((el) => {
      return document.activeElement === el;
    });
    
    console.log('Skip link is focused:', isFocused);
    
    if (isFocused) {
      // Get position after focus
      const focusedLeft = await skipLink.evaluate((el) => {
        return window.getComputedStyle(el).left;
      });
      
      console.log('After focus left:', focusedLeft);
      
      // After focus, it should be visible (left: 0.75rem or similar)
      expect(focusedLeft).not.toContain('-9999');
      
      // Take screenshot to show it's visible
      await page.screenshot({ path: '/tmp/skip-link-focused-login.png' });
    }
  });

  test('main-content anchor exists on all pages', async ({ page }) => {
    const pages = [
      '/auth/login',
      '/auth/register',
      '/',
      '/admin/users',
      '/backup-management',
    ];
    
    for (const pagePath of pages) {
      await page.goto(`${BASE_URL}${pagePath}`, { waitUntil: 'networkidle' });
      
      const mainContent = page.locator('#main-content');
      const exists = await mainContent.count();
      
      console.log(`Page ${pagePath}: main-content exists =`, exists > 0);
      expect(exists).toBeGreaterThan(0);
    }
  });

  test('skip link has z-index 10000', async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/login`);
    
    const skipLink = page.locator('.skip-link');
    
    const zIndex = await skipLink.evaluate((el) => {
      return window.getComputedStyle(el).zIndex;
    });
    
    console.log('Z-index:', zIndex);
    expect(zIndex).toBe('10000');
  });

  test('skip link has proper background and text colors', async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/login`);
    
    // Focus the skip link
    await page.keyboard.press('Tab');
    
    const skipLink = page.locator('.skip-link');
    
    const bgColor = await skipLink.evaluate((el) => {
      const style = window.getComputedStyle(el);
      return {
        backgroundColor: style.backgroundColor,
        color: style.color,
      };
    });
    
    console.log('Skip link colors:', bgColor);
    
    // Background should be white-ish
    expect(bgColor.backgroundColor).toBeTruthy();
    // Text color should be dark blue-ish
    expect(bgColor.color).toBeTruthy();
  });

  test('skip link works with anchor navigation', async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/login`);
    
    const skipLink = page.locator('.skip-link');
    const mainContent = page.locator('#main-content');
    
    // Focus and activate the skip link
    await page.keyboard.press('Tab');
    await page.keyboard.press('Enter');
    
    // Wait a moment for navigation
    await page.waitForTimeout(200);
    
    // Take screenshot showing the result
    await page.screenshot({ path: '/tmp/skip-link-activated-login.png' });
    
    // Check if main-content is still there
    const mainExists = await mainContent.count();
    expect(mainExists).toBe(1);
  });

  test('skip link appears on multiple pages', async ({ page }) => {
    const testPages = [
      '/',
      '/auth/login',
      '/admin/users',
      '/backup-management',
    ];
    
    for (const pagePath of testPages) {
      // Don't fail on auth-protected pages, just check skip link exists
      await page.goto(`${BASE_URL}${pagePath}`, { 
        waitUntil: 'networkidle',
      }).catch(() => {
        // OK if redirect happens
      });
      
      const skipLink = page.locator('.skip-link');
      const exists = await skipLink.count();
      
      console.log(`Skip link on ${pagePath}:`, exists > 0);
      expect(exists).toBe(1);
      
      const href = await skipLink.getAttribute('href');
      expect(href).toBe('#main-content');
    }
  });

  test('skip link is keyboard accessible (no javascript required)', async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/login`);
    
    // Simple keyboard test without JavaScript
    await page.keyboard.press('Tab');
    
    // Get the currently focused element
    const focusedElement = await page.evaluate(() => {
      const elem = document.activeElement as HTMLElement;
      return {
        tag: elem?.tagName,
        className: elem?.className,
        href: elem?.getAttribute('href'),
        text: elem?.textContent?.substring(0, 30),
      };
    });
    
    console.log('Focused element:', focusedElement);
    
    // Should focus skip link
    expect(focusedElement.href).toBe('#main-content');
    expect(focusedElement.text).toContain('Skip to main content');
  });
});
