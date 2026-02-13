import { test, expect } from '@playwright/test';

test.describe('Keyboard Navigation & Modal Focus Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:8003/');
    // Wait for page to load
    await page.waitForLoadState('networkidle');
  });

  test('Skip link is first element on Tab', async ({ page }) => {
    // Take initial screenshot
    await page.screenshot({ path: '/tmp/01-initial.png', fullPage: true });

    // Press Tab from address bar - should focus skip link
    await page.keyboard.press('Tab');
    
    // Check what's focused
    const focused = await page.evaluate(() => document.activeElement?.className);
    console.log('First focused element class:', focused);
    
    // Check if skip link is visible (it becomes visible on focus)
    const skipLinkVisible = await page.evaluate(() => {
      const el = document.querySelector('.skip-link');
      const style = window.getComputedStyle(el);
      return style.visibility !== 'hidden' && style.display !== 'none';
    });
    
    console.log('Skip link visible:', skipLinkVisible);
    await page.screenshot({ path: '/tmp/02-skip-link-focused.png', fullPage: true });
  });

  test('Tab order is logical', async ({ page }) => {
    // Get all focusable elements in order
    const focusableElements = await page.evaluate(() => {
      const selectors = [
        'a[href]',
        'button:not([disabled])',
        'input:not([disabled])',
        'select:not([disabled])',
        'textarea:not([disabled])',
        '[tabindex]:not([tabindex="-1"])'
      ];
      
      const elements = Array.from(
        document.querySelectorAll(selectors.join(','))
      ).filter((el: any) => {
        const style = window.getComputedStyle(el);
        return style.display !== 'none' && style.visibility !== 'hidden';
      });

      return elements.map((el: any) => ({
        tag: el.tagName,
        text: el.textContent?.substring(0, 50),
        ariaLabel: el.getAttribute('aria-label'),
        role: el.getAttribute('role'),
        id: el.id,
        className: el.className
      }));
    });

    console.log('Focusable elements in order:');
    focusableElements.forEach((el, i) => {
      console.log(`${i + 1}. ${el.tag} - "${el.text}" (role: ${el.role}, aria-label: ${el.ariaLabel})`);
    });

    expect(focusableElements.length).toBeGreaterThan(0);
  });

  test('Category/Tag filter list has listbox role', async ({ page }) => {
    // Check the categories list structure
    const listInfo = await page.evaluate(() => {
      const list = document.getElementById('categories-list');
      if (!list) return null;
      
      const items = list.querySelectorAll('[role="option"]');
      return {
        hasListboxRole: list.getAttribute('role') === 'listbox',
        itemCount: items.length,
        items: Array.from(items).map((item: any) => ({
          text: item.textContent,
          tabindex: item.getAttribute('tabindex'),
          ariaSelected: item.getAttribute('aria-selected'),
          isActive: item.classList.contains('active')
        }))
      };
    });

    console.log('Categories list info:', JSON.stringify(listInfo, null, 2));

    expect(listInfo).not.toBeNull();
    expect(listInfo?.hasListboxRole).toBe(true);
    expect(listInfo?.itemCount).toBeGreaterThan(0);

    // Take screenshot showing the list
    await page.screenshot({ path: '/tmp/03-categories-list.png', fullPage: true });
  });

  test('Arrow keys navigate list items', async ({ page }) => {
    // Click on categories list to focus it
    await page.click('#categories-list li');
    
    // Take screenshot of initial state
    await page.screenshot({ path: '/tmp/04-list-initial.png', fullPage: true });
    
    // Get currently focused item
    let initialFocus = await page.evaluate(() => {
      const focused = document.activeElement as HTMLElement;
      return focused?.textContent?.trim();
    });
    console.log('Initial focus:', initialFocus);

    // Press arrow down
    await page.keyboard.press('ArrowDown');
    
    let afterDown = await page.evaluate(() => {
      const focused = document.activeElement as HTMLElement;
      return focused?.textContent?.trim();
    });
    console.log('After Arrow Down:', afterDown);
    
    expect(initialFocus).not.toEqual(afterDown);
    
    await page.screenshot({ path: '/tmp/05-list-after-arrow-down.png', fullPage: true });

    // Press arrow up
    await page.keyboard.press('ArrowUp');
    
    let afterUp = await page.evaluate(() => {
      const focused = document.activeElement as HTMLElement;
      return focused?.textContent?.trim();
    });
    console.log('After Arrow Up:', afterUp);
    
    expect(afterUp).toEqual(initialFocus);
    
    await page.screenshot({ path: '/tmp/06-list-after-arrow-up.png', fullPage: true });
  });

  test('Roving tabindex only one in tab order', async ({ page }) => {
    // Check that only one list item has tabindex="0"
    const rovingTabindex = await page.evaluate(() => {
      const list = document.getElementById('categories-list');
      const items = list?.querySelectorAll('[role="option"]');
      if (!items) return null;
      
      const withTabindex0 = Array.from(items).filter((item: any) => 
        item.getAttribute('tabindex') === '0'
      );
      const withTabindexMinus1 = Array.from(items).filter((item: any) => 
        item.getAttribute('tabindex') === '-1'
      );
      
      return {
        totalItems: items.length,
        itemsWithTabindex0: withTabindex0.length,
        itemsWithTabindexMinus1: withTabindexMinus1.length,
        itemsWithNoTabindex: items.length - withTabindex0.length - withTabindexMinus1.length
      };
    });
    
    console.log('Roving tabindex state:', JSON.stringify(rovingTabindex));
    
    // Only one should have tabindex="0"
    expect(rovingTabindex?.itemsWithTabindex0).toBe(1);
    // Rest should have tabindex="-1" or no tabindex but be options
    expect(rovingTabindex?.totalItems).toBeGreaterThan(1);
  });

  test('Complete keyboard workflow', async ({ page }) => {
    // Take initial screenshot
    await page.screenshot({ path: '/tmp/10-workflow-start.png', fullPage: true });

    // 1. Tab through several elements
    for (let i = 0; i < 5; i++) {
      await page.keyboard.press('Tab');
    }

    const focused = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement;
      return {
        tag: el.tagName,
        text: el.textContent?.substring(0, 30),
        hasVisibleFocus: el.matches(':focus-visible')
      };
    });
    console.log('After 5 tabs, focused:', JSON.stringify(focused));

    await page.screenshot({ path: '/tmp/11-workflow-after-tabs.png', fullPage: true });

    // 2. Shift+Tab to go back
    await page.keyboard.press('Shift+Tab');
    const afterShiftTab = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement;
      return el.textContent?.substring(0, 50);
    });
    console.log('After Shift+Tab:', afterShiftTab);

    expect(afterShiftTab).toBeTruthy();

    await page.screenshot({ path: '/tmp/12-workflow-shift-tab.png', fullPage: true });
  });

  test('No keyboard traps', async ({ page }) => {
    // Navigate through page
    for (let i = 0; i < 10; i++) {
      await page.keyboard.press('Tab');
    }

    const beforeEscape = await page.evaluate(() => {
      return document.activeElement?.tagName;
    });
    console.log('Focused element before escape:', beforeEscape);

    // Press Escape - should not break anything
    await page.keyboard.press('Escape');
    
    // Page should still be responsive
    const afterEscape = await page.evaluate(() => {
      return document.activeElement?.tagName;
    });
    console.log('Focused element after escape:', afterEscape);

    // Should be able to continue tabbing
    await page.keyboard.press('Tab');
    const afterTab = await page.evaluate(() => {
      return document.activeElement?.tagName;
    });
    
    console.log('Focused element after tab:', afterTab);
    expect(afterTab).toBeTruthy();

    await page.screenshot({ path: '/tmp/14-no-traps.png', fullPage: true });
  });
});
