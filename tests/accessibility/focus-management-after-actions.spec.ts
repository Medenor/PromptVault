import { test, expect, Page } from '@playwright/test';

const BASE_URL = 'http://127.0.0.1:8003';
const TEST_USER_EMAIL = 'test_user_ui@example.com';
const TEST_USER_PASSWORD = 'TestUser@Pass123456';
const TEST_ADMIN_EMAIL = 'test_admin_ui@example.com';
const TEST_ADMIN_PASSWORD = 'TestAdmin@Pass123456';

async function loginAsUser(page: Page) {
  // Navigate to home
  await page.goto(BASE_URL);
  await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

  // Find username/email input - try multiple selectors
  const emailInput = page.locator('input').filter({
    has: page.locator('text=/username|email/i')
  }).first();

  // Try getting the input by position or attribute
  const allInputs = page.locator('input');
  const inputCount = await allInputs.count();
  
  if (inputCount >= 2) {
    // First input is usually username/email, second is password
    const usernameInput = allInputs.nth(0);
    const passwordInput = allInputs.nth(1);
    
    await usernameInput.fill(TEST_USER_EMAIL, { timeout: 10000 });
    await page.waitForTimeout(300);
    
    await passwordInput.fill(TEST_USER_PASSWORD, { timeout: 10000 });
    await page.waitForTimeout(300);
    
    // Find and click login button
    const loginButton = page.locator('button').filter({hasText: /login/i}).first();
    await loginButton.click();
    
    // Wait for navigation
    await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {});
    await page.waitForTimeout(1000);
  }
}

async function loginAsAdmin(page: Page) {
  // Navigate to home
  await page.goto(BASE_URL);
  await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

  // Find and fill inputs
  const allInputs = page.locator('input');
  const inputCount = await allInputs.count();
  
  if (inputCount >= 2) {
    const usernameInput = allInputs.nth(0);
    const passwordInput = allInputs.nth(1);
    
    await usernameInput.fill(TEST_ADMIN_EMAIL, { timeout: 10000 });
    await page.waitForTimeout(300);
    
    await passwordInput.fill(TEST_ADMIN_PASSWORD, { timeout: 10000 });
    await page.waitForTimeout(300);
    
    // Click login button
    const loginButton = page.locator('button').filter({hasText: /login/i}).first();
    await loginButton.click();
    
    // Wait for navigation
    await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {});
    await page.waitForTimeout(1000);
  }
}

test.describe('Focus Management After Actions', () => {
  test('Modal Focus: Version History - Focus moves into modal and returns on close', async ({ page }) => {
    // Login as test user
    await loginAsUser(page);
    
    // Navigate to home to ensure we're on dashboard
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    
    // Find and click a button that opens a modal (e.g., history, diff, etc.)
    const modalTriggers = page.locator('button').filter({hasText: /history|version|diff|view|show/i});
    const triggerCount = await modalTriggers.count();
    
    if (triggerCount > 0) {
      const firstTrigger = modalTriggers.first();
      
      // Click to open modal
      await firstTrigger.click();
      await page.waitForTimeout(800);
      
      // Check if modal is open
      const modal = page.locator('[role="dialog"], .modal, [aria-modal="true"]').first();
      const isVisible = await modal.isVisible({ timeout: 3000 }).catch(() => false);
      
      if (isVisible) {
        // Verify focus is inside modal
        const focusInModal = await page.evaluate(() => {
          const activeEl = document.activeElement;
          const modal = document.querySelector('[role="dialog"], .modal, [aria-modal="true"]');
          return modal ? modal.contains(activeEl) : false;
        });
        
        expect(focusInModal).toBeTruthy();
        
        // Close modal with Escape
        await page.keyboard.press('Escape');
        await page.waitForTimeout(500);
        
        // Verify modal closed
        const isStillVisible = await modal.isVisible({ timeout: 2000 }).catch(() => false);
        expect(isStillVisible).toBeFalsy();
        
        // Verify focus returned to a button
        const focusAfterClose = await page.evaluate(() => {
          const activeEl = document.activeElement;
          return activeEl?.tagName === 'BUTTON' || activeEl?.tagName === 'A';
        });
        
        expect(focusAfterClose).toBeTruthy();
      }
    }
  });

  test('Delete Action: Categories - Focus management after delete', async ({ page }) => {
    // Login as test user
    await loginAsUser(page);
    
    // Navigate to categories
    await page.goto(`${BASE_URL}/categories`);
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    
    // Find a delete button
    const deleteButtons = page.locator('button').filter({hasText: /delete|remove/i});
    const deleteCount = await deleteButtons.count();
    
    if (deleteCount > 0) {
      const firstDelete = deleteButtons.first();
      const beforeElement = await page.evaluate(() => document.activeElement?.tagName);
      
      await firstDelete.click();
      await page.waitForTimeout(500);
      
      // Check if confirmation modal opened
      const confirmModal = page.locator('[role="dialog"]').first();
      const isConfirmVisible = await confirmModal.isVisible({ timeout: 2000 }).catch(() => false);
      
      if (isConfirmVisible) {
        // Verify focus moved to modal
        const focusInConfirm = await page.evaluate(() => {
          const activeEl = document.activeElement;
          const modal = document.querySelector('[role="dialog"]');
          return modal ? modal.contains(activeEl) : false;
        });
        
        expect(focusInConfirm).toBeTruthy();
        
        // Click confirm button
        const confirmButton = page.locator('[role="dialog"] button').filter({hasText: /confirm|delete|yes|ok/i}).first();
        await confirmButton.click();
        await page.waitForTimeout(1000);
        
        // Verify focus is on a valid element (not body)
        const focusAfterDelete = await page.evaluate(() => {
          const activeEl = document.activeElement;
          return activeEl?.tagName !== 'BODY' && activeEl?.tagName !== 'HTML';
        });
        
        expect(focusAfterDelete).toBeTruthy();
      }
    }
  });

  test('Delete Action: Tags - Focus management after delete', async ({ page }) => {
    // Login as test user  
    await loginAsUser(page);
    
    // Navigate to tags
    await page.goto(`${BASE_URL}/tags`);
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    
    // Find a delete button
    const deleteButtons = page.locator('button').filter({hasText: /delete|remove/i});
    const deleteCount = await deleteButtons.count();
    
    if (deleteCount > 0) {
      const firstDelete = deleteButtons.first();
      await firstDelete.click();
      await page.waitForTimeout(500);
      
      // Check confirmation modal
      const confirmModal = page.locator('[role="dialog"]').first();
      const isConfirmVisible = await confirmModal.isVisible({ timeout: 2000 }).catch(() => false);
      
      if (isConfirmVisible) {
        const confirmButton = page.locator('[role="dialog"] button').filter({hasText: /confirm|delete|yes|ok/i}).first();
        await confirmButton.click();
        await page.waitForTimeout(1000);
        
        // Focus should be on a valid element
        const focusValid = await page.evaluate(() => {
          const activeEl = document.activeElement;
          return activeEl?.tagName !== 'BODY';
        });
        
        expect(focusValid).toBeTruthy();
      }
    }
  });

  test('Admin Modal: Delete user - Focus in modal and return on close', async ({ page }) => {
    // Login as admin
    await loginAsAdmin(page);
    
    // Navigate to admin users
    await page.goto(`${BASE_URL}/admin/users`);
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    
    // Find delete button
    const deleteButtons = page.locator('button').filter({hasText: /delete/i});
    const deleteCount = await deleteButtons.count();
    
    if (deleteCount > 0) {
      const firstDelete = deleteButtons.first();
      await firstDelete.click();
      await page.waitForTimeout(500);
      
      // Check modal
      const modal = page.locator('[role="dialog"]').first();
      const isVisible = await modal.isVisible({ timeout: 2000 }).catch(() => false);
      
      if (isVisible) {
        // Focus should be in modal
        const focusInModal = await page.evaluate(() => {
          const activeEl = document.activeElement;
          const modal = document.querySelector('[role="dialog"]');
          return modal ? modal.contains(activeEl) : false;
        });
        
        expect(focusInModal).toBeTruthy();
        
        // Close with Escape
        await page.keyboard.press('Escape');
        await page.waitForTimeout(500);
        
        // Focus should return
        const focusReturned = await page.evaluate(() => {
          const activeEl = document.activeElement;
          return activeEl?.tagName === 'BUTTON' || activeEl?.tagName === 'A';
        });
        
        expect(focusReturned).toBeTruthy();
      }
    }
  });

  test('Admin Sessions: Revoke - Focus management', async ({ page }) => {
    // Login as admin
    await loginAsAdmin(page);
    
    // Navigate to sessions
    await page.goto(`${BASE_URL}/admin/sessions`);
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    
    // Find revoke button
    const revokeButtons = page.locator('button').filter({hasText: /revoke|terminate|end/i});
    const revokeCount = await revokeButtons.count();
    
    if (revokeCount > 0) {
      const firstRevoke = revokeButtons.first();
      await firstRevoke.click();
      await page.waitForTimeout(500);
      
      // Focus should be managed
      const focusValid = await page.evaluate(() => {
        const activeEl = document.activeElement;
        return activeEl?.tagName !== 'BODY' && activeEl?.tagName !== 'HTML';
      });
      
      expect(focusValid).toBeTruthy();
    }
  });
});
