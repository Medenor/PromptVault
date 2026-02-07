import { chromium } from 'playwright';
import * as dotenv from 'dotenv';

dotenv.config();

const baseURL = process.env.PLAYWRIGHT_TEST_BASE_URL || 'http://localhost:8003';
const adminUser = 'test_admin_ui@example.com';
const adminPass = 'TestAdmin@Pass123456';

async function verifyTables() {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Navigate to login
    await page.goto(`${baseURL}/auth/login`, { waitUntil: 'networkidle' });
    
    // Login
    await page.fill('input[name="email"]', adminUser);
    await page.fill('input[name="password"]', adminPass);
    await page.click('button[type="submit"]');
    await page.waitForLoadState('networkidle');
    
    // Navigate to admin users
    await page.goto(`${baseURL}/admin/users`, { waitUntil: 'networkidle' });
    
    console.log('\n=== USERS TABLE VERIFICATION ===');
    
    // Check for aria-label
    const usersTable = await page.locator('table').first();
    const usersAriaLabel = await usersTable.getAttribute('aria-label');
    console.log('Users table aria-label:', usersAriaLabel);
    
    // Check for caption
    const usersCaption = await page.locator('table caption');
    const usersCaptionCount = await usersCaption.count();
    const usersCaptionText = usersCaptionCount > 0 ? await usersCaption.textContent() : 'NOT FOUND';
    console.log('Users table caption:', usersCaptionText);
    console.log('Users table caption element count:', usersCaptionCount);
    
    // Check headers
    const usersHeaders = await page.locator('table thead th');
    const usersHeaderCount = await usersHeaders.count();
    console.log('Users table header count:', usersHeaderCount);
    
    // Get header texts and scope attributes
    const usersHeaderData = await usersHeaders.evaluateAll((elements) => {
      return elements.map((el) => ({
        text: el.textContent?.trim(),
        scope: el.getAttribute('scope')
      }));
    });
    console.log('Users table headers:');
    usersHeaderData.forEach((h, i) => {
      console.log(`  ${i + 1}. "${h.text}" - scope="${h.scope}"`);
    });
    
    const allUsersHaveScope = usersHeaderData.every(h => h.scope === 'col');
    console.log('All users headers have scope="col":', allUsersHaveScope);
    
    // Navigate to sessions
    await page.goto(`${baseURL}/admin/sessions`, { waitUntil: 'networkidle' });
    
    console.log('\n=== SESSIONS TABLE VERIFICATION ===');
    
    // Check for aria-label
    const sessionsTable = await page.locator('table').first();
    const sessionsAriaLabel = await sessionsTable.getAttribute('aria-label');
    console.log('Sessions table aria-label:', sessionsAriaLabel);
    
    // Check for caption
    const sessionsCaption = await page.locator('table caption');
    const sessionsCaptionCount = await sessionsCaption.count();
    const sessionsCaptionText = sessionsCaptionCount > 0 ? await sessionsCaption.textContent() : 'NOT FOUND';
    console.log('Sessions table caption:', sessionsCaptionText);
    console.log('Sessions table caption element count:', sessionsCaptionCount);
    
    // Check headers
    const sessionsHeaders = await page.locator('table thead th');
    const sessionsHeaderCount = await sessionsHeaders.count();
    console.log('Sessions table header count:', sessionsHeaderCount);
    
    // Get header texts and scope attributes
    const sessionsHeaderData = await sessionsHeaders.evaluateAll((elements) => {
      return elements.map((el) => ({
        text: el.textContent?.trim(),
        scope: el.getAttribute('scope')
      }));
    });
    console.log('Sessions table headers:');
    sessionsHeaderData.forEach((h, i) => {
      console.log(`  ${i + 1}. "${h.text}" - scope="${h.scope}"`);
    });
    
    const allSessionsHaveScope = sessionsHeaderData.every(h => h.scope === 'col');
    console.log('All sessions headers have scope="col":', allSessionsHaveScope);
    
    console.log('\n=== SUMMARY ===');
    console.log('Users table aria-label present:', !!usersAriaLabel);
    console.log('Users table caption present:', usersCaptionCount > 0);
    console.log('Users table headers scope correct:', allUsersHaveScope);
    console.log('Sessions table aria-label present:', !!sessionsAriaLabel);
    console.log('Sessions table caption present:', sessionsCaptionCount > 0);
    console.log('Sessions table headers scope correct:', allSessionsHaveScope);
    
    const allPassed = (
      !!usersAriaLabel &&
      usersCaptionCount > 0 &&
      allUsersHaveScope &&
      !!sessionsAriaLabel &&
      sessionsCaptionCount > 0 &&
      allSessionsHaveScope
    );
    
    console.log('\nALL TESTS PASSED:', allPassed ? 'YES' : 'NO');
    
    if (!allPassed) {
      process.exit(1);
    }
  } finally {
    await browser.close();
  }
}

verifyTables().catch(err => {
  console.error('Error:', err);
  process.exit(1);
});
