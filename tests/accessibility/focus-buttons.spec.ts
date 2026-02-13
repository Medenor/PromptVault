import { test, expect } from '@playwright/test';

test('Focus indicators on login page - buttons', async ({ page }) => {
  await page.goto('http://127.0.0.1:8003/auth/login', { waitUntil: 'networkidle' });
  
  // Tab through form to reach the submit button
  for (let i = 0; i < 6; i++) {
    await page.keyboard.press('Tab');
    await page.waitForTimeout(200);
  }
  
  // Should be at submit button
  const submitButtonElement = await page.evaluate(() => {
    const active = document.activeElement as HTMLElement;
    if (!active) return null;
    const styles = window.getComputedStyle(active);
    return {
      tagName: active.tagName,
      type: (active as any).type,
      outline: styles.outline,
      outlineWidth: styles.outlineWidth,
      outlineColor: styles.outlineColor,
      outlineStyle: styles.outlineStyle,
      outlineOffset: styles.outlineOffset,
    };
  });
  
  console.log('Submit button:', submitButtonElement);
  
  await page.screenshot({ path: '/tmp/focus-submit-button-final.png' });
  
  expect(submitButtonElement?.outlineStyle).toBe('solid');
  expect(submitButtonElement?.outlineWidth).toBe('3px');
  expect(submitButtonElement?.outlineOffset).toBe('2px');
  expect(submitButtonElement?.outlineColor).toBe('rgb(74, 144, 226)');
});
