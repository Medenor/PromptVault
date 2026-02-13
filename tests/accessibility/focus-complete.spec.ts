import { test, expect } from '@playwright/test';

test('Complete focus indicator verification - all properties', async ({ page }) => {
  // Test 1: Skip link (accessibility element)
  await page.goto('http://127.0.0.1:8003/auth/login', { waitUntil: 'networkidle' });
  await page.keyboard.press('Tab');
  await page.waitForTimeout(300);
  
  let focusedElement = await page.evaluate(() => {
    const active = document.activeElement as HTMLElement;
    if (!active) return null;
    const styles = window.getComputedStyle(active);
    return {
      element: active.tagName,
      outlineWidth: styles.outlineWidth,
      outlineStyle: styles.outlineStyle,
      outlineColor: styles.outlineColor,
      outlineOffset: styles.outlineOffset,
    };
  });
  
  console.log('Test 1 - Skip Link:', focusedElement);
  expect(focusedElement?.outlineStyle).toBe('solid');
  expect(focusedElement?.outlineWidth).toBe('3px');
  expect(focusedElement?.outlineOffset).toBe('2px');
  expect(focusedElement?.outlineColor).toBe('rgb(74, 144, 226)');
  
  // Test 2: Form input (text input)
  await page.goto('http://127.0.0.1:8003/auth/login', { waitUntil: 'networkidle' });
  await page.locator('#username-or-email').focus();
  await page.keyboard.press('Tab');
  await page.waitForTimeout(300);
  
  focusedElement = await page.evaluate(() => {
    const active = document.activeElement as HTMLElement;
    if (!active) return null;
    const styles = window.getComputedStyle(active);
    return {
      element: active.tagName,
      outlineWidth: styles.outlineWidth,
      outlineStyle: styles.outlineStyle,
      outlineColor: styles.outlineColor,
      outlineOffset: styles.outlineOffset,
    };
  });
  
  console.log('Test 2 - Password Input:', focusedElement);
  expect(focusedElement?.outlineStyle).toBe('solid');
  expect(focusedElement?.outlineWidth).toBe('3px');
  expect(focusedElement?.outlineOffset).toBe('2px');
  
  // Test 3: Checkbox
  await page.keyboard.press('Tab');
  await page.waitForTimeout(300);
  
  focusedElement = await page.evaluate(() => {
    const active = document.activeElement as HTMLElement;
    if (!active) return null;
    const styles = window.getComputedStyle(active);
    return {
      element: active.tagName,
      type: (active as any).type,
      outlineWidth: styles.outlineWidth,
      outlineStyle: styles.outlineStyle,
      outlineColor: styles.outlineColor,
      outlineOffset: styles.outlineOffset,
    };
  });
  
  console.log('Test 3 - Checkbox:', focusedElement);
  expect(focusedElement?.outlineStyle).toBe('solid');
  expect(focusedElement?.outlineWidth).toBe('3px');
  
  // Test 4: Links
  await page.goto('http://127.0.0.1:8003/', { waitUntil: 'networkidle' });
  await page.keyboard.press('Tab');
  await page.waitForTimeout(300);
  
  focusedElement = await page.evaluate(() => {
    const active = document.activeElement as HTMLElement;
    if (!active) return null;
    const styles = window.getComputedStyle(active);
    return {
      element: active.tagName,
      outlineWidth: styles.outlineWidth,
      outlineStyle: styles.outlineStyle,
      outlineColor: styles.outlineColor,
      outlineOffset: styles.outlineOffset,
    };
  });
  
  console.log('Test 4 - Link:', focusedElement);
  expect(focusedElement?.outlineStyle).toBe('solid');
  expect(focusedElement?.outlineWidth).toBe('3px');
  
  console.log('All focus indicator tests passed!');
  console.log('Focus outline properties verified:');
  console.log('- Width: 3px');
  console.log('- Style: solid');
  console.log('- Color: rgb(74, 144, 226) (#4A90E2)');
  console.log('- Offset: 2px');
});
