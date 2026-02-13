import { test, expect } from '@playwright/test';

test('Focus indicator outline - verified on multiple pages', async ({ page }) => {
  // Test on login page
  await page.goto('http://127.0.0.1:8003/auth/login', { waitUntil: 'networkidle' });
  await page.keyboard.press('Tab');
  
  const focusedElement1 = await page.evaluate(() => {
    const active = document.activeElement as HTMLElement;
    const styles = window.getComputedStyle(active);
    return {
      outline: styles.outline,
      outlineWidth: styles.outlineWidth,
      outlineStyle: styles.outlineStyle,
      outlineColor: styles.outlineColor,
      outlineOffset: styles.outlineOffset,
    };
  });
  
  console.log('Login page focused element:', focusedElement1);
  expect(focusedElement1.outline).toContain('3px');
  expect(focusedElement1.outline).toContain('solid');
  expect(focusedElement1.outlineColor).toBe('rgb(74, 144, 226)');
  expect(focusedElement1.outlineOffset).toBe('2px');
  
  // Test on home page
  await page.goto('http://127.0.0.1:8003/', { waitUntil: 'networkidle' });
  await page.keyboard.press('Tab');
  
  const focusedElement2 = await page.evaluate(() => {
    const active = document.activeElement as HTMLElement;
    const styles = window.getComputedStyle(active);
    return {
      outline: styles.outline,
      outlineWidth: styles.outlineWidth,
      outlineStyle: styles.outlineStyle,
      outlineColor: styles.outlineColor,
      outlineOffset: styles.outlineOffset,
    };
  });
  
  console.log('Home page focused element:', focusedElement2);
  expect(focusedElement2.outline).toContain('3px');
  expect(focusedElement2.outline).toContain('solid');
  expect(focusedElement2.outlineColor).toBe('rgb(74, 144, 226)');
  expect(focusedElement2.outlineOffset).toBe('2px');
  
  // Test on register page
  await page.goto('http://127.0.0.1:8003/auth/register', { waitUntil: 'networkidle' });
  await page.keyboard.press('Tab');
  
  const focusedElement3 = await page.evaluate(() => {
    const active = document.activeElement as HTMLElement;
    const styles = window.getComputedStyle(active);
    return {
      outline: styles.outline,
      outlineWidth: styles.outlineWidth,
      outlineStyle: styles.outlineStyle,
      outlineColor: styles.outlineColor,
      outlineOffset: styles.outlineOffset,
    };
  });
  
  console.log('Register page focused element:', focusedElement3);
  expect(focusedElement3.outline).toContain('3px');
  expect(focusedElement3.outline).toContain('solid');
  expect(focusedElement3.outlineColor).toBe('rgb(74, 144, 226)');
  expect(focusedElement3.outlineOffset).toBe('2px');
});
