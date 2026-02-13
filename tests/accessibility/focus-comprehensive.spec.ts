import { test, expect } from '@playwright/test';

test('Focus indicators on home page with multiple elements', async ({ page }) => {
  await page.goto('http://127.0.0.1:8003/', { waitUntil: 'networkidle' });
  
  // Tab to first interactive element
  await page.keyboard.press('Tab');
  await page.waitForTimeout(300);
  
  const firstElement = await page.evaluate(() => {
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
  
  await page.screenshot({ path: '/tmp/home-focus-1.png' });
  console.log('First element:', firstElement);
  expect(firstElement?.outlineStyle).toBe('solid');
  expect(firstElement?.outlineWidth).toBe('3px');
  expect(firstElement?.outlineOffset).toBe('2px');
  expect(firstElement?.outlineColor).toBe('rgb(74, 144, 226)');
  
  // Tab to second element
  await page.keyboard.press('Tab');
  await page.waitForTimeout(300);
  
  await page.screenshot({ path: '/tmp/home-focus-2.png' });
  
  const secondElement = await page.evaluate(() => {
    const active = document.activeElement as HTMLElement;
    if (!active) return null;
    const styles = window.getComputedStyle(active);
    return {
      tagName: active.tagName,
      outline: styles.outline,
      outlineWidth: styles.outlineWidth,
      outlineStyle: styles.outlineStyle,
    };
  });
  
  console.log('Second element:', secondElement);
  expect(secondElement?.outlineStyle).toBe('solid');
  expect(secondElement?.outlineWidth).toBe('3px');
  
  // Tab to third element
  await page.keyboard.press('Tab');
  await page.waitForTimeout(300);
  
  await page.screenshot({ path: '/tmp/home-focus-3.png' });
  
  const thirdElement = await page.evaluate(() => {
    const active = document.activeElement as HTMLElement;
    if (!active) return null;
    const styles = window.getComputedStyle(active);
    return {
      tagName: active.tagName,
      outline: styles.outline,
      outlineWidth: styles.outlineWidth,
      outlineStyle: styles.outlineStyle,
    };
  });
  
  console.log('Third element:', thirdElement);
  expect(thirdElement?.outlineStyle).toBe('solid');
  expect(thirdElement?.outlineWidth).toBe('3px');
});

test('Focus indicator outline properties are correct', async ({ page }) => {
  await page.goto('http://127.0.0.1:8003/auth/login', { waitUntil: 'networkidle' });
  
  // Tab to skip link
  await page.keyboard.press('Tab');
  await page.waitForTimeout(300);
  
  const focusedElement = await page.evaluate(() => {
    const active = document.activeElement as HTMLElement;
    if (!active) return null;
    const styles = window.getComputedStyle(active);
    
    // Parse the outline value
    const outline = styles.outline;
    const outlineWidth = styles.outlineWidth;
    const outlineStyle = styles.outlineStyle;
    const outlineColor = styles.outlineColor;
    const outlineOffset = styles.outlineOffset;
    
    return {
      outline,
      outlineWidth,
      outlineStyle,
      outlineColor,
      outlineOffset,
    };
  });
  
  console.log('Focus outline properties:', focusedElement);
  
  // Verify all properties
  expect(focusedElement?.outlineWidth).toBe('3px');
  expect(focusedElement?.outlineStyle).toBe('solid');
  expect(focusedElement?.outlineColor).toBe('rgb(74, 144, 226)');
  expect(focusedElement?.outlineOffset).toBe('2px');
  
  // Full outline shorthand should include all properties
  expect(focusedElement?.outline).toContain('3px');
  expect(focusedElement?.outline).toContain('solid');
});
