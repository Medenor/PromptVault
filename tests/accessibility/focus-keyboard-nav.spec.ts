import { test, expect } from '@playwright/test';

test('Focus indicator on skip link and login form - keyboard tab navigation', async ({ page }) => {
  await page.goto('http://127.0.0.1:8003/auth/login', { waitUntil: 'networkidle' });
  
  // Press Tab to focus skip link
  await page.keyboard.press('Tab');
  await page.waitForTimeout(300);
  
  await page.screenshot({ path: '/tmp/focus-skip-link.png' });
  
  // Get skip link focus info
  let focusedElement = await page.evaluate(() => {
    const active = document.activeElement as HTMLElement;
    if (!active) return null;
    const styles = window.getComputedStyle(active);
    return {
      tagName: active.tagName,
      id: active.id,
      classList: Array.from(active.classList).join(' '),
      outline: styles.outline,
      outlineWidth: styles.outlineWidth,
      outlineColor: styles.outlineColor,
      outlineStyle: styles.outlineStyle,
      outlineOffset: styles.outlineOffset,
    };
  });
  
  console.log('Skip link element:', focusedElement);
  expect(focusedElement?.outlineStyle).toBe('solid');
  expect(focusedElement?.outlineWidth).toBe('3px');
  expect(focusedElement?.outlineOffset).toBe('2px');
  
  // Tab multiple times to reach form inputs
  for (let i = 0; i < 3; i++) {
    await page.keyboard.press('Tab');
    await page.waitForTimeout(200);
  }
  
  // Should be at username input
  const usernameInput = await page.evaluate(() => {
    const active = document.activeElement as HTMLElement;
    if (!active) return null;
    const styles = window.getComputedStyle(active);
    return {
      tagName: active.tagName,
      id: active.id,
      outline: styles.outline,
      outlineWidth: styles.outlineWidth,
      outlineColor: styles.outlineColor,
      outlineStyle: styles.outlineStyle,
      outlineOffset: styles.outlineOffset,
    };
  });
  
  await page.screenshot({ path: '/tmp/focus-username-input.png' });
  
  console.log('Username input element:', usernameInput);
  expect(usernameInput?.outlineStyle).toBe('solid');
  expect(usernameInput?.outlineWidth).toBe('3px');
  expect(usernameInput?.outlineOffset).toBe('2px');
  
  // Tab to password input
  await page.keyboard.press('Tab');
  await page.waitForTimeout(300);
  
  const passwordInput = await page.evaluate(() => {
    const active = document.activeElement as HTMLElement;
    if (!active) return null;
    const styles = window.getComputedStyle(active);
    return {
      tagName: active.tagName,
      id: active.id,
      outline: styles.outline,
      outlineWidth: styles.outlineWidth,
      outlineColor: styles.outlineColor,
      outlineStyle: styles.outlineStyle,
      outlineOffset: styles.outlineOffset,
    };
  });
  
  await page.screenshot({ path: '/tmp/focus-password-input.png' });
  
  console.log('Password input element:', passwordInput);
  expect(passwordInput?.outlineStyle).toBe('solid');
  expect(passwordInput?.outlineWidth).toBe('3px');
  expect(passwordInput?.outlineOffset).toBe('2px');
  
  // Tab to remember me checkbox
  await page.keyboard.press('Tab');
  await page.waitForTimeout(300);
  
  const rememberCheckbox = await page.evaluate(() => {
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
  
  await page.screenshot({ path: '/tmp/focus-checkbox.png' });
  
  console.log('Checkbox element:', rememberCheckbox);
  expect(rememberCheckbox?.outlineStyle).toBe('solid');
  expect(rememberCheckbox?.outlineWidth).toBe('3px');
  expect(rememberCheckbox?.outlineOffset).toBe('2px');
  
  // Tab to submit button
  await page.keyboard.press('Tab');
  await page.waitForTimeout(300);
  
  const submitButton = await page.evaluate(() => {
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
  
  await page.screenshot({ path: '/tmp/focus-submit-button.png' });
  
  console.log('Submit button element:', submitButton);
  expect(submitButton?.outlineStyle).toBe('solid');
  expect(submitButton?.outlineWidth).toBe('3px');
  expect(submitButton?.outlineOffset).toBe('2px');
});

test('Focus indicator colors are correct blue (#4A90E2)', async ({ page }) => {
  await page.goto('http://127.0.0.1:8003/auth/login', { waitUntil: 'networkidle' });
  
  // Tab to skip link
  await page.keyboard.press('Tab');
  await page.waitForTimeout(300);
  
  const outlineColor = await page.evaluate(() => {
    const active = document.activeElement as HTMLElement;
    if (!active) return null;
    const styles = window.getComputedStyle(active);
    return styles.outlineColor;
  });
  
  console.log('Outline color:', outlineColor);
  // Should be rgb(74, 144, 226) which is #4A90E2
  expect(outlineColor).toBe('rgb(74, 144, 226)');
});
