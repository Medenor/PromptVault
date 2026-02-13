import { test, expect } from '@playwright/test';

test('Visual focus indicator test on login page - Tab navigation', async ({ page }) => {
  await page.goto('http://127.0.0.1:8003/auth/login', { waitUntil: 'networkidle' });
  
  // Press Tab to focus first element
  await page.keyboard.press('Tab');
  await page.waitForTimeout(300);
  
  // Take screenshot
  await page.screenshot({ path: '/tmp/focus-first-element.png' });
  
  // Get focused element info
  let focusedElement = await page.evaluate(() => {
    const active = document.activeElement as HTMLElement;
    if (!active) return null;
    const styles = window.getComputedStyle(active);
    return {
      tagName: active.tagName,
      outline: styles.outline,
      outlineWidth: styles.outlineWidth,
      outlineColor: styles.outlineColor,
      outlineStyle: styles.outlineStyle,
      outlineOffset: styles.outlineOffset,
    };
  });
  
  console.log('First focused element:', focusedElement);
  expect(focusedElement?.outlineStyle).toBe('solid');
  
  // Tab to next element
  await page.keyboard.press('Tab');
  await page.waitForTimeout(300);
  await page.screenshot({ path: '/tmp/focus-second-element.png' });
  
  focusedElement = await page.evaluate(() => {
    const active = document.activeElement as HTMLElement;
    if (!active) return null;
    const styles = window.getComputedStyle(active);
    return {
      tagName: active.tagName,
      outline: styles.outline,
      outlineWidth: styles.outlineWidth,
      outlineColor: styles.outlineColor,
      outlineStyle: styles.outlineStyle,
      outlineOffset: styles.outlineOffset,
    };
  });
  
  console.log('Second focused element:', focusedElement);
  expect(focusedElement?.outlineStyle).toBe('solid');
  
  // Tab to third element
  await page.keyboard.press('Tab');
  await page.waitForTimeout(300);
  await page.screenshot({ path: '/tmp/focus-third-element.png' });
  
  focusedElement = await page.evaluate(() => {
    const active = document.activeElement as HTMLElement;
    if (!active) return null;
    const styles = window.getComputedStyle(active);
    return {
      tagName: active.tagName,
      outline: styles.outline,
      outlineWidth: styles.outlineWidth,
      outlineColor: styles.outlineColor,
      outlineStyle: styles.outlineStyle,
      outlineOffset: styles.outlineOffset,
    };
  });
  
  console.log('Third focused element:', focusedElement);
  expect(focusedElement?.outlineStyle).toBe('solid');
});

test('Visual focus on home page links', async ({ page }) => {
  await page.goto('http://127.0.0.1:8003/', { waitUntil: 'networkidle' });
  
  // Press Tab to focus first element
  await page.keyboard.press('Tab');
  await page.waitForTimeout(300);
  
  await page.screenshot({ path: '/tmp/focus-home-first.png' });
  
  const focusedElement = await page.evaluate(() => {
    const active = document.activeElement as HTMLElement;
    if (!active) return null;
    const styles = window.getComputedStyle(active);
    return {
      tagName: active.tagName,
      outline: styles.outline,
      outlineWidth: styles.outlineWidth,
      outlineColor: styles.outlineColor,
      outlineStyle: styles.outlineStyle,
      outlineOffset: styles.outlineOffset,
    };
  });
  
  console.log('Home page focused element:', focusedElement);
  expect(focusedElement?.outlineStyle).toBe('solid');
});
