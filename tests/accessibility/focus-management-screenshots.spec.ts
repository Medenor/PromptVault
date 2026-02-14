import { test } from '@playwright/test';

const BASE_URL = 'http://127.0.0.1:8003';
const TEST_USER_EMAIL = 'test_user_ui@example.com';
const TEST_USER_PASSWORD = 'TestUser@Pass123456';
const TEST_ADMIN_EMAIL = 'test_admin_ui@example.com';
const TEST_ADMIN_PASSWORD = 'TestAdmin@Pass123456';

test.describe('Focus Management - Visual Screenshots', () => {
  test('Capture 1: Login form with credentials', async ({ page }) => {
    // Navigate to login page
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    
    // Fill login form
    const allInputs = page.locator('input');
    const usernameInput = allInputs.nth(0);
    const passwordInput = allInputs.nth(1);
    
    await usernameInput.fill(TEST_USER_EMAIL);
    await page.waitForTimeout(300);
    
    await passwordInput.fill(TEST_USER_PASSWORD);
    await page.waitForTimeout(300);
    
    // Screenshot of filled login form
    await page.screenshot({ path: 'test-results/01-login-form-filled.png', fullPage: true });
    console.log('Captured: Login form with credentials filled');
  });

  test('Capture 2: Dashboard and modal trigger buttons', async ({ page }) => {
    // Login
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    
    const allInputs = page.locator('input');
    const usernameInput = allInputs.nth(0);
    const passwordInput = allInputs.nth(1);
    
    await usernameInput.fill(TEST_USER_EMAIL);
    await passwordInput.fill(TEST_USER_PASSWORD);
    
    const loginButton = page.locator('button').filter({hasText: /login/i}).first();
    await loginButton.click();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    
    // Find modal trigger
    const modalTriggers = page.locator('button').filter({hasText: /history|version|diff/i});
    const triggerCount = await modalTriggers.count();
    
    if (triggerCount > 0) {
      const firstTrigger = modalTriggers.first();
      const triggerText = await firstTrigger.textContent();
      
      // Focus on the trigger button
      await firstTrigger.focus();
      await page.waitForTimeout(200);
      
      // Screenshot showing focus on trigger button
      await page.screenshot({ path: 'test-results/02-dashboard-focus-on-button.png', fullPage: true });
      console.log(`Captured: Dashboard with focus on "${triggerText?.trim()}" button`);
    }
  });

  test('Capture 3: Modal open with focus inside', async ({ page }) => {
    // Login and navigate
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    
    const allInputs = page.locator('input');
    await allInputs.nth(0).fill(TEST_USER_EMAIL);
    await allInputs.nth(1).fill(TEST_USER_PASSWORD);
    
    const loginButton = page.locator('button').filter({hasText: /login/i}).first();
    await loginButton.click();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    
    // Open modal
    const modalTriggers = page.locator('button').filter({hasText: /history|version|diff/i});
    const triggerCount = await modalTriggers.count();
    
    if (triggerCount > 0) {
      const firstTrigger = modalTriggers.first();
      await firstTrigger.click();
      await page.waitForTimeout(800);
      
      // Screenshot showing modal open with focus inside
      await page.screenshot({ path: 'test-results/03-modal-open-focus-inside.png', fullPage: true });
      console.log('Captured: Modal open with focus managed inside');
    }
  });

  test('Capture 4: Categories page with delete button focus', async ({ page }) => {
    // Login as user
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    
    const allInputs = page.locator('input');
    await allInputs.nth(0).fill(TEST_USER_EMAIL);
    await allInputs.nth(1).fill(TEST_USER_PASSWORD);
    
    const loginButton = page.locator('button').filter({hasText: /login/i}).first();
    await loginButton.click();
    await page.waitForLoadState('networkidle');
    
    // Navigate to categories
    await page.goto(`${BASE_URL}/categories`);
    await page.waitForLoadState('networkidle');
    
    // Focus on delete button
    const deleteButtons = page.locator('button').filter({hasText: /delete|remove/i});
    const deleteCount = await deleteButtons.count();
    
    if (deleteCount > 0) {
      const firstDelete = deleteButtons.first();
      await firstDelete.focus();
      await page.waitForTimeout(200);
      
      // Screenshot showing focus on delete button
      await page.screenshot({ path: 'test-results/04-categories-delete-button-focus.png', fullPage: true });
      console.log('Captured: Categories page with delete button in focus');
    }
  });

  test('Capture 5: Delete confirmation modal', async ({ page }) => {
    // Login as user
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    
    const allInputs = page.locator('input');
    await allInputs.nth(0).fill(TEST_USER_EMAIL);
    await allInputs.nth(1).fill(TEST_USER_PASSWORD);
    
    const loginButton = page.locator('button').filter({hasText: /login/i}).first();
    await loginButton.click();
    await page.waitForLoadState('networkidle');
    
    // Navigate to categories
    await page.goto(`${BASE_URL}/categories`);
    await page.waitForLoadState('networkidle');
    
    // Click delete button
    const deleteButtons = page.locator('button').filter({hasText: /delete|remove/i});
    const deleteCount = await deleteButtons.count();
    
    if (deleteCount > 0) {
      const firstDelete = deleteButtons.first();
      await firstDelete.click();
      await page.waitForTimeout(500);
      
      // Screenshot showing delete confirmation modal
      await page.screenshot({ path: 'test-results/05-delete-confirmation-modal.png', fullPage: true });
      console.log('Captured: Delete confirmation modal with focus management');
    }
  });

  test('Capture 6: Admin Users page with delete modals', async ({ page }) => {
    // Login as admin
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    
    const allInputs = page.locator('input');
    await allInputs.nth(0).fill(TEST_ADMIN_EMAIL);
    await allInputs.nth(1).fill(TEST_ADMIN_PASSWORD);
    
    const loginButton = page.locator('button').filter({hasText: /login/i}).first();
    await loginButton.click();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    
    // Navigate to admin users
    await page.goto(`${BASE_URL}/admin/users`);
    await page.waitForLoadState('networkidle');
    
    // Screenshot of admin users page
    await page.screenshot({ path: 'test-results/06-admin-users-page.png', fullPage: true });
    console.log('Captured: Admin users page');
  });

  test('Capture 7: Admin Sessions page with revoke buttons', async ({ page }) => {
    // Login as admin
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    
    const allInputs = page.locator('input');
    await allInputs.nth(0).fill(TEST_ADMIN_EMAIL);
    await allInputs.nth(1).fill(TEST_ADMIN_PASSWORD);
    
    const loginButton = page.locator('button').filter({hasText: /login/i}).first();
    await loginButton.click();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    
    // Navigate to admin sessions
    await page.goto(`${BASE_URL}/admin/sessions`);
    await page.waitForLoadState('networkidle');
    
    // Screenshot of admin sessions page
    await page.screenshot({ path: 'test-results/07-admin-sessions-page.png', fullPage: true });
    console.log('Captured: Admin sessions page with revoke buttons');
  });
});
