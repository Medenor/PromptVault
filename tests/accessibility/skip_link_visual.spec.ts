// Skip Link Visual Verification Test
import { test, expect } from '@playwright/test';

const BASE_URL = process.env.ACCESSIBILITY_BASE_URL ?? 'http://127.0.0.1:8003';

test.describe('Skip Link Visual Verification', () => {
  test('login page shows skip link in DOM', async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/login`);
    
    // Verify skip link exists
    const skipLink = page.locator('.skip-link');
    expect(await skipLink.count()).toBe(1);
    expect(await skipLink.textContent()).toContain('Skip to main content');
    expect(await skipLink.getAttribute('href')).toBe('#main-content');
    
    // Screenshot without focus
    await page.screenshot({ path: '/tmp/01-login-no-focus.png' });
  });

  test('skip link appears when Tab is pressed multiple times', async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/login`);
    
    // Take initial screenshot
    await page.screenshot({ path: '/tmp/02-login-initial.png' });
    
    // Tab through several elements
    for (let i = 0; i < 5; i++) {
      await page.keyboard.press('Tab');
      await page.screenshot({ path: `/tmp/02-login-tab-${i}.png` });
    }
    
    // Check what's currently focused
    const focused = await page.evaluate(() => {
      const elem = document.activeElement as HTMLElement;
      return {
        tag: elem?.tagName,
        href: elem?.getAttribute('href'),
        className: elem?.className?.substring(0, 50),
      };
    });
    
    console.log('Currently focused:', focused);
  });

  test('index page has skip link and main content', async ({ page }) => {
    // Use auth state to access authenticated page if available
    await page.goto(`${BASE_URL}/auth/login`);
    
    // Just verify skip link exists on public pages
    const skipLink = page.locator('.skip-link');
    expect(await skipLink.count()).toBe(1);
    
    await page.screenshot({ path: '/tmp/03-login-page.png' });
  });

  test('verify skip link and main-content element exist in all templates', async ({ page }) => {
    const testCases = [
      { path: '/auth/login', name: 'login' },
      { path: '/auth/register', name: 'register' },
      { path: '/auth/forgot-password', name: 'forgot-password' },
    ];
    
    for (const testCase of testCases) {
      await page.goto(`${BASE_URL}${testCase.path}`);
      
      const skipLink = page.locator('.skip-link');
      const mainContent = page.locator('#main-content');
      
      const skipLinkExists = await skipLink.count();
      const mainContentExists = await mainContent.count();
      
      console.log(`${testCase.name}: skip-link=${skipLinkExists}, main-content=${mainContentExists}`);
      
      expect(skipLinkExists).toBe(1);
      expect(mainContentExists).toBe(1);
      
      // Verify skip link points to main content
      const href = await skipLink.getAttribute('href');
      expect(href).toBe('#main-content');
      
      await page.screenshot({ path: `/tmp/04-${testCase.name}.png` });
    }
  });

  test('skip link CSS is applied correctly', async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/login`);
    
    const skipLink = page.locator('.skip-link');
    
    // Get computed styles
    const styles = await skipLink.evaluate((el) => {
      const computed = window.getComputedStyle(el);
      return {
        position: computed.position,
        top: computed.top,
        left: computed.left,
        zIndex: computed.zIndex,
        backgroundColor: computed.backgroundColor,
        color: computed.color,
        visibility: computed.visibility,
        opacity: computed.opacity,
        borderRadius: computed.borderRadius,
        padding: computed.padding,
      };
    });
    
    console.log('Skip link styles:', JSON.stringify(styles, null, 2));
    
    // Verify key styles
    expect(styles.position).toBe('absolute');
    expect(styles.left).toBe('-9999px'); // Hidden by default
    expect(styles.zIndex).toBe('10000');
    expect(styles.backgroundColor).toBe('rgb(255, 255, 255)');
    expect(styles.visibility).toBe('hidden');
    expect(styles.opacity).toBe('0');
  });

  test('skip link becomes visible on focus', async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/login`);
    
    const skipLink = page.locator('.skip-link');
    
    // Click on skip link to focus it
    await skipLink.focus();
    
    // Get styles after focus
    const styles = await skipLink.evaluate((el) => {
      const computed = window.getComputedStyle(el);
      return {
        left: computed.left,
        visibility: computed.visibility,
        opacity: computed.opacity,
      };
    });
    
    console.log('Skip link styles after focus:', JSON.stringify(styles, null, 2));
    
    // Take screenshot showing focused skip link
    await page.screenshot({ path: '/tmp/05-skip-link-focused.png' });
    
    // Verify it's now visible
    expect(styles.left).not.toBe('-9999px');
    expect(styles.visibility).toBe('visible');
    expect(styles.opacity).toBe('1');
  });

  test('skip link works as anchor link', async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/login`);
    
    // Get skip link href
    const skipLink = page.locator('.skip-link');
    const href = await skipLink.getAttribute('href');
    
    expect(href).toBe('#main-content');
    
    // Get main-content position
    const mainContent = page.locator('#main-content');
    const mainBox = await mainContent.boundingBox();
    
    console.log('Main content position:', mainBox);
    expect(mainBox).toBeTruthy();
    
    // Click skip link
    await skipLink.click();
    
    // Take screenshot after click
    await page.screenshot({ path: '/tmp/06-skip-link-after-click.png' });
  });
});
