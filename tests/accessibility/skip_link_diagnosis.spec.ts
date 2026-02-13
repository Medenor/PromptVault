// Skip Link Diagnosis Test
import { test, expect } from '@playwright/test';

const BASE_URL = process.env.ACCESSIBILITY_BASE_URL ?? 'http://127.0.0.1:8003';

test.describe('Skip Link CSS Diagnosis', () => {
  test('Check CSS rules applied to skip-link', async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/login`);
    
    const skipLink = page.locator('.skip-link');
    
    // Get all applied styles
    const allStyles = await skipLink.evaluate((el) => {
      const computed = window.getComputedStyle(el);
      const matches = el.matches(':focus');
      const focusVis = el.matches(':focus-visible');
      
      return {
        classList: el.className,
        isFocused: document.activeElement === el,
        matches_focus: matches,
        matches_focusvisible: focusVis,
        computed: {
          left: computed.left,
          visibility: computed.visibility,
          opacity: computed.opacity,
          position: computed.position,
          zIndex: computed.zIndex,
        },
        // Get inline styles if any
        inlineStyle: el.getAttribute('style'),
        // Get CSS rules that apply to this element
        getRule: (prop) => computed.getPropertyValue(prop),
      };
    });
    
    console.log('Skip link styles:', JSON.stringify(allStyles, null, 2));
    
    // Now focus it
    await skipLink.focus();
    
    await page.waitForTimeout(100);
    
    const afterFocus = await skipLink.evaluate((el) => {
      const computed = window.getComputedStyle(el);
      return {
        isFocused: document.activeElement === el,
        matches_focus: el.matches(':focus'),
        matches_focusvisible: el.matches(':focus-visible'),
        left: computed.left,
        visibility: computed.visibility,
        opacity: computed.opacity,
      };
    });
    
    console.log('After focus:', JSON.stringify(afterFocus, null, 2));
  });

  test('Check if skip-link CSS selectors are working', async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/login`);
    
    // Inject a test to check CSS calculations
    const result = await page.evaluate(() => {
      const link = document.querySelector('.skip-link') as HTMLElement;
      if (!link) return { error: 'Skip link not found' };
      
      // Check initial state
      const initialState = window.getComputedStyle(link);
      
      // Focus the link
      link.focus();
      
      // Check state after focus
      const focusedState = window.getComputedStyle(link);
      
      return {
        before: {
          left: initialState.left,
          visibility: initialState.visibility,
          opacity: initialState.opacity,
          ariaHidden: link.getAttribute('aria-hidden'),
        },
        after: {
          left: focusedState.left,
          visibility: focusedState.visibility,
          opacity: focusedState.opacity,
          ariaHidden: link.getAttribute('aria-hidden'),
        },
        isFocused: document.activeElement === link,
        matchesFocus: link.matches(':focus'),
        matchesFocusVisible: link.matches(':focus-visible'),
      };
    });
    
    console.log('CSS calculation result:', JSON.stringify(result, null, 2));
  });

  test('Check stylesheets for skip-link rules', async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/login`);
    
    const rules = await page.evaluate(() => {
      const skipLinkRules: any[] = [];
      const stylesheets = Array.from(document.styleSheets);
      
      for (const sheet of stylesheets) {
        try {
          const cssRules = Array.from(sheet.cssRules || []);
          for (const rule of cssRules) {
            if (rule instanceof CSSStyleRule) {
              if (rule.selectorText && rule.selectorText.includes('skip')) {
                skipLinkRules.push({
                  selector: rule.selectorText,
                  css: rule.style.cssText,
                });
              }
            }
          }
        } catch (e) {
          // CORS or other error
        }
      }
      
      return skipLinkRules;
    });
    
    console.log('Found CSS rules for skip-link:', JSON.stringify(rules, null, 2));
    expect(rules.length).toBeGreaterThan(0);
  });

  test('Test skip-link with keyboard press Tab', async ({ page }) => {
    await page.goto(`${BASE_URL}/auth/login`);
    
    // Take screenshot before any interaction
    await page.screenshot({ path: '/tmp/diag-01-initial.png' });
    
    // Press Tab to try to focus skip link
    await page.keyboard.press('Tab');
    
    await page.screenshot({ path: '/tmp/diag-02-after-tab.png' });
    
    // Check what's focused
    const focused = await page.evaluate(() => {
      const elem = document.activeElement as HTMLElement;
      return {
        tag: elem?.tagName,
        class: elem?.className?.substring(0, 60),
        id: elem?.id,
      };
    });
    
    console.log('Focused element after Tab:', focused);
  });
});
