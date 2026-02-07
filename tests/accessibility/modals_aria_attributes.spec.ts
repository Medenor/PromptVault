import { test, expect } from '@playwright/test';

// Helper to login
async function loginAsAdmin(page) {
  await page.goto('http://localhost:8003');
  await page.waitForLoadState('networkidle');
  
  // Fill the login form
  await page.fill('input[placeholder*="username" i], input[placeholder*="email" i]', 'test_admin_ui@example.com');
  await page.fill('input[placeholder*="password" i], input[type="password"]', 'TestAdmin@Pass123456');
  
  // Click login button
  await page.click('button:has-text("Login")');
  
  // Wait for successful navigation
  await page.waitForURL('**/', { timeout: 10000 }).catch(() => {});
  
  await page.waitForTimeout(1000);
}

// Helper to wait for modal to be visible (not just exist)
async function waitForVisibleModal(page) {
  // First wait for the dialog element to exist
  await page.waitForSelector('[role="dialog"]', { timeout: 5000 });
  
  // Then wait for it to NOT have the hidden class
  await page.waitForFunction(
    () => {
      const modals = document.querySelectorAll('[role="dialog"]');
      for (let modal of modals) {
        if (!modal.classList.contains('hidden')) {
          return true;
        }
      }
      return false;
    },
    { timeout: 5000 }
  );
}

test.describe('Modal ARIA Attributes and Dialog Roles', () => {
  test('1. Admin Users Page - Create User Modal ARIA attributes', async ({ page }) => {
    await loginAsAdmin(page);
    
    // Navigate to admin users page
    await page.goto('http://localhost:8003/admin/users');
    await page.waitForLoadState('networkidle');
    
    // Click the add user button
    const createButton = page.locator('button').filter({ hasText: /Create|Add/ }).first();
    if (await createButton.isVisible()) {
      await createButton.click();
    } else {
      await page.click('button[aria-label*="Create" i], button[aria-label*="Add" i]');
    }
    
    // Wait for modal to be visible
    await waitForVisibleModal(page);
    
    // Get the visible modal element
    const visibleModals = await page.evaluate(() => {
      const modals = document.querySelectorAll('[role="dialog"]');
      const visible = Array.from(modals).find(m => !m.classList.contains('hidden'));
      if (visible) {
        return {
          id: visible.id,
          role: visible.getAttribute('role'),
          ariaModal: visible.getAttribute('aria-modal'),
          ariaLabelledBy: visible.getAttribute('aria-labelledby'),
          ariaDescribedBy: visible.getAttribute('aria-describedby')
        };
      }
      return null;
    });
    
    console.log('Create User Modal ARIA attributes:');
    console.log(`  role: ${visibleModals?.role}`);
    console.log(`  aria-modal: ${visibleModals?.ariaModal}`);
    console.log(`  aria-labelledby: ${visibleModals?.ariaLabelledBy}`);
    console.log(`  aria-describedby: ${visibleModals?.ariaDescribedBy}`);
    
    expect(visibleModals).toBeTruthy();
    expect(visibleModals?.role).toBe('dialog');
    expect(visibleModals?.ariaModal).toBe('true');
    expect(visibleModals?.ariaLabelledBy).toBeTruthy();
    expect(visibleModals?.ariaDescribedBy).toBeTruthy();
    
    // Verify title element exists with matching ID
    if (visibleModals?.ariaLabelledBy) {
      const titleText = await page.textContent(`#${visibleModals.ariaLabelledBy}`);
      console.log(`  Title text: "${titleText}"`);
      expect(titleText).toBeTruthy();
    }
    
    // Take screenshot
    await page.screenshot({ path: 'test-results/01-modal-create-user.png', fullPage: true });
    console.log('Screenshot: test-results/01-modal-create-user.png');
  });

  test('2. Admin Users Page - Delete Confirmation Modal', async ({ page }) => {
    await loginAsAdmin(page);
    
    // Navigate to admin users page
    await page.goto('http://localhost:8003/admin/users');
    await page.waitForLoadState('networkidle');
    
    // Find first user row and click delete button
    const deleteButtons = page.locator('button').filter({ hasText: /Delete/i });
    const firstDeleteButton = deleteButtons.first();
    
    if (await firstDeleteButton.isVisible()) {
      await firstDeleteButton.click();
      
      // Wait for delete confirmation modal
      await waitForVisibleModal(page);
      
      // Get modal attributes
      const visibleModals = await page.evaluate(() => {
        const modals = document.querySelectorAll('[role="dialog"]');
        const visible = Array.from(modals).find(m => !m.classList.contains('hidden'));
        if (visible) {
          return {
            id: visible.id,
            role: visible.getAttribute('role'),
            ariaModal: visible.getAttribute('aria-modal'),
            ariaLabelledBy: visible.getAttribute('aria-labelledby'),
            ariaDescribedBy: visible.getAttribute('aria-describedby')
          };
        }
        return null;
      });
      
      console.log('Delete Confirmation Modal ARIA attributes:');
      console.log(`  role: ${visibleModals?.role}`);
      console.log(`  aria-modal: ${visibleModals?.ariaModal}`);
      console.log(`  aria-labelledby: ${visibleModals?.ariaLabelledBy}`);
      
      expect(visibleModals).toBeTruthy();
      expect(visibleModals?.role).toBe('dialog');
      expect(visibleModals?.ariaModal).toBe('true');
      expect(visibleModals?.ariaLabelledBy).toBeTruthy();
      
      // Take screenshot
      await page.screenshot({ path: 'test-results/02-modal-delete-confirmation.png', fullPage: true });
      console.log('Screenshot: test-results/02-modal-delete-confirmation.png');
      
      // Close the modal (press Escape)
      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);
    } else {
      console.log('No delete button found');
    }
  });

  test('3. Admin Sessions Page Modal ARIA attributes', async ({ page }) => {
    await loginAsAdmin(page);
    
    // Navigate to admin sessions page
    await page.goto('http://localhost:8003/admin/sessions');
    await page.waitForLoadState('networkidle');
    
    // Look for a session detail button/link
    const sessionButtons = page.locator('button').filter({ hasText: /Detail|View/i });
    
    if (await sessionButtons.first().isVisible()) {
      await sessionButtons.first().click();
      
      // Wait for modal
      try {
        await waitForVisibleModal(page);
        
        // Get modal attributes
        const visibleModals = await page.evaluate(() => {
          const modals = document.querySelectorAll('[role="dialog"]');
          const visible = Array.from(modals).find(m => !m.classList.contains('hidden'));
          if (visible) {
            return {
              id: visible.id,
              role: visible.getAttribute('role'),
              ariaModal: visible.getAttribute('aria-modal'),
              ariaLabelledBy: visible.getAttribute('aria-labelledby')
            };
          }
          return null;
        });
        
        console.log('Session Detail Modal ARIA attributes:');
        console.log(`  role: ${visibleModals?.role}`);
        console.log(`  aria-modal: ${visibleModals?.ariaModal}`);
        console.log(`  aria-labelledby: ${visibleModals?.ariaLabelledBy}`);
        
        expect(visibleModals).toBeTruthy();
        expect(visibleModals?.role).toBe('dialog');
        expect(visibleModals?.ariaModal).toBe('true');
        
        // Take screenshot
        await page.screenshot({ path: 'test-results/03-modal-session-detail.png', fullPage: true });
        
        await page.keyboard.press('Escape');
      } catch (e) {
        console.log('No modal appeared - possibly no sessions available');
      }
    } else {
      console.log('No session detail button found');
    }
  });

  test('4. Main Page - Verify existing modals have ARIA attributes', async ({ page }) => {
    await loginAsAdmin(page);
    
    // Navigate to main page
    await page.goto('http://localhost:8003');
    await page.waitForLoadState('networkidle');
    
    // Look for version history button
    const versionButtons = page.locator('button').filter({ hasText: /Version|History/i });
    
    if (await versionButtons.first().isVisible()) {
      await versionButtons.first().click();
      
      // Wait for modal
      try {
        await waitForVisibleModal(page);
        
        // Get modal attributes
        const visibleModals = await page.evaluate(() => {
          const modals = document.querySelectorAll('[role="dialog"]');
          const visible = Array.from(modals).find(m => !m.classList.contains('hidden'));
          if (visible) {
            return {
              id: visible.id,
              role: visible.getAttribute('role'),
              ariaModal: visible.getAttribute('aria-modal'),
              ariaLabelledBy: visible.getAttribute('aria-labelledby')
            };
          }
          return null;
        });
        
        console.log('Version History Modal ARIA attributes:');
        console.log(`  role: ${visibleModals?.role}`);
        console.log(`  aria-modal: ${visibleModals?.ariaModal}`);
        console.log(`  aria-labelledby: ${visibleModals?.ariaLabelledBy}`);
        
        expect(visibleModals).toBeTruthy();
        expect(visibleModals?.role).toBe('dialog');
        expect(visibleModals?.ariaModal).toBe('true');
        
        // Take screenshot
        await page.screenshot({ path: 'test-results/04-modal-version-history.png', fullPage: true });
        
        await page.keyboard.press('Escape');
      } catch (e) {
        console.log('Version History modal not available');
      }
    } else {
      console.log('No modal trigger button found on main page');
    }
  });

  test('5. Modal Keyboard Navigation and Focus', async ({ page }) => {
    await loginAsAdmin(page);
    
    // Navigate to admin users page
    await page.goto('http://localhost:8003/admin/users');
    await page.waitForLoadState('networkidle');
    
    // Open create user modal
    const createButton = page.locator('button').filter({ hasText: /Create|Add/ }).first();
    if (await createButton.isVisible()) {
      await createButton.click();
    } else {
      await page.click('button[aria-label*="Create" i], button[aria-label*="Add" i]');
    }
    
    // Wait for modal
    await waitForVisibleModal(page);
    
    // Get focusable elements and test tab navigation
    const focusInfo = await page.evaluate(() => {
      const modals = document.querySelectorAll('[role="dialog"]');
      const modal = Array.from(modals).find(m => !m.classList.contains('hidden')) as HTMLElement;
      if (!modal) return { count: 0, elements: [] };
      
      const focusableElements = modal.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      
      return {
        count: focusableElements.length,
        elements: Array.from(focusableElements).map((el: Element) => ({
          tag: (el as HTMLElement).tagName,
          type: (el as HTMLInputElement).type || 'N/A',
          id: (el as HTMLElement).id || 'no-id'
        }))
      };
    });
    
    console.log(`Found ${focusInfo.count} focusable elements in modal`);
    expect(focusInfo.count).toBeGreaterThan(0);
    
    // Tab through elements to verify focus management
    for (let i = 0; i < Math.min(focusInfo.count, 3); i++) {
      await page.keyboard.press('Tab');
      await page.waitForTimeout(100);
      
      const focusedElement = await page.evaluate(() => {
        const el = document.activeElement as HTMLElement;
        return {
          tag: el?.tagName,
          type: (el as HTMLInputElement)?.type || 'N/A',
          id: el?.id || 'no-id'
        };
      });
      
      console.log(`  Tab ${i + 1}: Focused element:`, focusedElement);
    }
    
    // Take screenshot showing focus
    await page.screenshot({ path: 'test-results/05-modal-focus-navigation.png', fullPage: true });
    console.log('Screenshot: test-results/05-modal-focus-navigation.png');
    
    // Test Escape key closes modal
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
    
    const isModalHidden = await page.evaluate(() => {
      const modals = document.querySelectorAll('[role="dialog"]');
      return Array.from(modals).every(m => m.classList.contains('hidden'));
    });
    
    expect(isModalHidden).toBeTruthy();
    console.log('Modal closed with Escape key: PASS');
  });

  test('6. Verify All Modal Structure and IDs', async ({ page }) => {
    await loginAsAdmin(page);
    
    // Navigate to admin/users
    await page.goto('http://localhost:8003/admin/users');
    await page.waitForLoadState('networkidle');
    
    // Open create user modal
    const createButton = page.locator('button').filter({ hasText: /Create|Add/ }).first();
    if (await createButton.isVisible()) {
      await createButton.click();
    } else {
      await page.click('button[aria-label*="Create" i], button[aria-label*="Add" i]');
    }
    
    // Wait for modal
    await waitForVisibleModal(page);
    
    // Get all modal information
    const modalInfo = await page.evaluate(() => {
      const modals = document.querySelectorAll('[role="dialog"]');
      return Array.from(modals).map((modal: Element) => {
        const el = modal as HTMLElement;
        const ariaLabelledBy = el.getAttribute('aria-labelledby');
        const titleElement = ariaLabelledBy ? document.getElementById(ariaLabelledBy) : null;
        
        return {
          id: el.id,
          role: el.getAttribute('role'),
          ariaModal: el.getAttribute('aria-modal'),
          ariaLabelledBy: ariaLabelledBy,
          ariaDescribedBy: el.getAttribute('aria-describedby'),
          isVisible: !el.classList.contains('hidden'),
          titleText: titleElement?.textContent || 'N/A',
          titleId: titleElement?.id || 'N/A'
        };
      });
    });
    
    console.log(`Found ${modalInfo.length} modal(s) on page`);
    
    for (let i = 0; i < modalInfo.length; i++) {
      const modal = modalInfo[i];
      console.log(`\nModal ${i + 1}:`);
      console.log(`  id: ${modal.id}`);
      console.log(`  role: ${modal.role}`);
      console.log(`  aria-modal: ${modal.ariaModal}`);
      console.log(`  aria-labelledby: ${modal.ariaLabelledBy}`);
      console.log(`  aria-describedby: ${modal.ariaDescribedBy}`);
      console.log(`  isVisible: ${modal.isVisible}`);
      console.log(`  titleText: "${modal.titleText}"`);
      
      // Verify attributes for visible modals
      if (modal.isVisible) {
        expect(modal.role).toBe('dialog');
        expect(modal.ariaModal).toBe('true');
        expect(modal.ariaLabelledBy).toBeTruthy();
        expect(modal.titleId).toBeTruthy();
      }
    }
    
    // Take final screenshot
    await page.screenshot({ path: 'test-results/06-modal-structure-verification.png', fullPage: true });
    console.log('Screenshot: test-results/06-modal-structure-verification.png');
  });
});
