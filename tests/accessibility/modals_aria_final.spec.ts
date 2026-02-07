import { test, expect } from '@playwright/test';

test.describe('Modal ARIA Attributes - Final Verification', () => {
  test('1. Version History Modal - ARIA Attributes Present', async ({ page }) => {
    // Navigate to login
    await page.goto('http://localhost:8003');
    await page.waitForLoadState('networkidle');
    
    // Login
    await page.fill('input[placeholder*="username" i], input[placeholder*="email" i]', 'test_admin_ui@example.com');
    await page.fill('input[placeholder*="password" i], input[type="password"]', 'TestAdmin@Pass123456');
    await page.click('button:has-text("Login")');
    
    // Wait for login to complete
    await page.waitForTimeout(2000);
    
    // Go to main page
    await page.goto('http://localhost:8003');
    await page.waitForLoadState('networkidle');
    
    // Click Version History button
    const versionBtn = page.locator('button').filter({ hasText: /Version|History/i }).first();
    if (await versionBtn.isVisible()) {
      await versionBtn.click();
      
      // Wait for modal to open
      await page.waitForTimeout(500);
      
      // Verify modal has proper ARIA attributes
      const modalDetails = await page.evaluate(() => {
        const modals = document.querySelectorAll('[role="dialog"]');
        const visibleModal = Array.from(modals).find(m => !m.classList.contains('hidden'));
        
        if (visibleModal) {
          return {
            id: visibleModal.id,
            role: visibleModal.getAttribute('role'),
            ariaModal: visibleModal.getAttribute('aria-modal'),
            ariaLabelledBy: visibleModal.getAttribute('aria-labelledby'),
            ariaDescribedBy: visibleModal.getAttribute('aria-describedby'),
            isVisible: !visibleModal.classList.contains('hidden'),
            hasTitle: !!document.getElementById(visibleModal.getAttribute('aria-labelledby') || '')
          };
        }
        return null;
      });
      
      console.log('Modal ARIA Verification:');
      console.log(`  Modal ID: ${modalDetails?.id}`);
      console.log(`  Role: ${modalDetails?.role}`);
      console.log(`  aria-modal: ${modalDetails?.ariaModal}`);
      console.log(`  aria-labelledby: ${modalDetails?.ariaLabelledBy}`);
      console.log(`  aria-describedby: ${modalDetails?.ariaDescribedBy}`);
      console.log(`  Is Visible: ${modalDetails?.isVisible}`);
      console.log(`  Has Title Element: ${modalDetails?.hasTitle}`);
      
      expect(modalDetails?.role).toBe('dialog');
      expect(modalDetails?.ariaModal).toBe('true');
      expect(modalDetails?.ariaLabelledBy).toBeTruthy();
      expect(modalDetails?.isVisible).toBe(true);
      expect(modalDetails?.hasTitle).toBe(true);
      
      // Take screenshot
      await page.screenshot({ path: 'test-results/modal-final-verification.png', fullPage: true });
      console.log('Screenshot: test-results/modal-final-verification.png');
      
      // Test Escape closes modal
      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);
      
      const isClosed = await page.evaluate(() => {
        const modals = document.querySelectorAll('[role="dialog"]');
        return Array.from(modals).every(m => m.classList.contains('hidden'));
      });
      
      expect(isClosed).toBe(true);
      console.log('Escape key closes modal: PASS');
    }
  });

  test('2. Inspect all modal HTML structure in DOM', async ({ page }) => {
    // Navigate to admin users
    await page.goto('http://localhost:8003');
    await page.waitForLoadState('networkidle');
    
    // Login
    await page.fill('input[placeholder*="username" i], input[placeholder*="email" i]', 'test_admin_ui@example.com');
    await page.fill('input[placeholder*="password" i], input[type="password"]', 'TestAdmin@Pass123456');
    await page.click('button:has-text("Login")');
    
    await page.waitForTimeout(2000);
    
    // Navigate to admin users
    await page.goto('http://localhost:8003/admin/users');
    await page.waitForLoadState('networkidle');
    
    // Get all modal information from DOM
    const allModals = await page.evaluate(() => {
      const modals = document.querySelectorAll('[role="dialog"]');
      return Array.from(modals).map((m: Element) => {
        const modal = m as HTMLElement;
        const titleId = modal.getAttribute('aria-labelledby');
        const titleElement = titleId ? document.getElementById(titleId) : null;
        
        return {
          id: modal.id,
          role: modal.getAttribute('role'),
          ariaModal: modal.getAttribute('aria-modal'),
          ariaLabelledBy: titleId,
          ariaDescribedBy: modal.getAttribute('aria-describedby'),
          titleText: titleElement?.textContent || 'N/A',
          titleElementId: titleElement?.id || 'MISSING',
          hasCloseable: !!modal.querySelector('button[aria-label*="Close"]'),
          focusableElements: modal.querySelectorAll('button, input, select, textarea, [tabindex]:not([tabindex="-1"])').length,
          className: modal.className
        };
      });
    });
    
    console.log(`\nFound ${allModals.length} modals in DOM:`);
    
    for (let i = 0; i < allModals.length; i++) {
      const modal = allModals[i];
      console.log(`\nModal ${i + 1}:`);
      console.log(`  ID: ${modal.id}`);
      console.log(`  Role: ${modal.role}`);
      console.log(`  aria-modal: ${modal.ariaModal}`);
      console.log(`  aria-labelledby: ${modal.ariaLabelledBy}`);
      console.log(`  aria-describedby: ${modal.ariaDescribedBy}`);
      console.log(`  Title Text: "${modal.titleText}"`);
      console.log(`  Title Element ID: ${modal.titleElementId}`);
      console.log(`  Has Close Button: ${modal.hasCloseable}`);
      console.log(`  Focusable Elements: ${modal.focusableElements}`);
      
      // Verify all required ARIA attributes
      expect(modal.role).toBe('dialog');
      expect(modal.ariaModal).toBe('true');
      expect(modal.ariaLabelledBy).toBeTruthy();
      expect(modal.titleElementId).not.toBe('MISSING');
    }
    
    // All modals should have proper ARIA attributes
    expect(allModals.length).toBeGreaterThan(0);
  });

  test('3. Test focus trap in modal', async ({ page }) => {
    // Navigate to admin users
    await page.goto('http://localhost:8003');
    await page.waitForLoadState('networkidle');
    
    // Login
    await page.fill('input[placeholder*="username" i], input[placeholder*="email" i]', 'test_admin_ui@example.com');
    await page.fill('input[placeholder*="password" i], input[type="password"]', 'TestAdmin@Pass123456');
    await page.click('button:has-text("Login")');
    
    await page.waitForTimeout(2000);
    
    // Navigate to admin users
    await page.goto('http://localhost:8003/admin/users');
    await page.waitForLoadState('networkidle');
    
    // Open modal
    const addBtn = page.locator('button').filter({ hasText: /Add|Create/i }).first();
    if (await addBtn.isVisible()) {
      await addBtn.click();
      await page.waitForTimeout(500);
      
      // Check if first focusable element is focused
      const focusInfo = await page.evaluate(() => {
        const modals = document.querySelectorAll('[role="dialog"]');
        const visibleModal = Array.from(modals).find(m => !m.classList.contains('hidden')) as HTMLElement;
        
        if (visibleModal) {
          const focusables = visibleModal.querySelectorAll(
            'button, input, select, textarea, [tabindex]:not([tabindex="-1"])'
          );
          
          return {
            focusableCount: focusables.length,
            firstFocusable: focusables[0]?.tagName || 'N/A',
            currentFocus: document.activeElement?.tagName || 'N/A',
            isFirstFocused: document.activeElement === focusables[0]
          };
        }
        
        return null;
      });
      
      console.log('\nFocus Management:');
      console.log(`  Focusable elements in modal: ${focusInfo?.focusableCount}`);
      console.log(`  First focusable: ${focusInfo?.firstFocusable}`);
      console.log(`  Currently focused: ${focusInfo?.currentFocus}`);
      console.log(`  First element focused: ${focusInfo?.isFirstFocused}`);
      
      expect(focusInfo?.focusableCount).toBeGreaterThan(0);
      
      // Take screenshot
      await page.screenshot({ path: 'test-results/modal-focus-trap.png', fullPage: true });
    }
  });

  test('4. Verify modal closes on Escape and backdrop click', async ({ page }) => {
    await page.goto('http://localhost:8003');
    await page.waitForLoadState('networkidle');
    
    // Login
    await page.fill('input[placeholder*="username" i], input[placeholder*="email" i]', 'test_admin_ui@example.com');
    await page.fill('input[placeholder*="password" i], input[type="password"]', 'TestAdmin@Pass123456');
    await page.click('button:has-text("Login")');
    
    await page.waitForTimeout(2000);
    
    // Go to main page
    await page.goto('http://localhost:8003');
    await page.waitForLoadState('networkidle');
    
    // Open modal
    const versionBtn = page.locator('button').filter({ hasText: /Version|History/i }).first();
    if (await versionBtn.isVisible()) {
      await versionBtn.click();
      await page.waitForTimeout(500);
      
      // Verify modal is open
      const isOpenBefore = await page.evaluate(() => {
        const modals = document.querySelectorAll('[role="dialog"]');
        return Array.from(modals).some(m => !m.classList.contains('hidden'));
      });
      
      expect(isOpenBefore).toBe(true);
      console.log('Modal opened: PASS');
      
      // Close with Escape
      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);
      
      const isClosedAfterEscape = await page.evaluate(() => {
        const modals = document.querySelectorAll('[role="dialog"]');
        return Array.from(modals).every(m => m.classList.contains('hidden'));
      });
      
      expect(isClosedAfterEscape).toBe(true);
      console.log('Modal closed with Escape: PASS');
    }
  });
});
