import { test } from '@playwright/test';

test.skip('Visual verification of landmark rendering', async ({ browser }) => {
  const context = await browser.newContext();
  const page = await context.newPage();
  
  // Set credentials in storage
  const loginUrl = 'http://127.0.0.1:8003/auth/login';
  
  console.log('=== VISUAL LANDMARK CHECK ===');
  console.log('Step 1: Navigating to login page...');
  await page.goto(loginUrl, { waitUntil: 'networkidle' });
  await page.screenshot({ path: '/tmp/01-login-page.png' });
  
  console.log('Step 2: Logging in...');
  await page.fill('input[name="username"]', 'test_admin_ui@example.com');
  await page.fill('input[name="password"]', 'TestAdmin@Pass123456');
  await page.click('button[type="submit"]');
  await page.waitForLoadState('networkidle');
  
  console.log('Step 3: Navigating to admin users...');
  await page.goto('http://127.0.0.1:8003/admin/users', { waitUntil: 'networkidle' });
  await page.screenshot({ path: '/tmp/02-admin-users.png' });
  
  const landmarks = await page.evaluate(() => {
    const landmarks: any = {};
    
    const banner = document.querySelector('[role="banner"], header:not(header *)');
    landmarks.banner = !!banner;
    
    const main = document.querySelector('[role="main"], main');
    landmarks.main = !!main;
    
    const footer = document.querySelector('[role="contentinfo"], footer:not(footer *)');
    landmarks.contentinfo = !!footer;
    
    return landmarks;
  });
  
  console.log('Landmarks check result:', landmarks);
  await context.close();
});
