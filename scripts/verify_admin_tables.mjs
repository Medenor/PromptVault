/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/. */

import { chromium } from 'playwright';
import * as dotenv from 'dotenv';

dotenv.config();

const baseURL = process.env.PLAYWRIGHT_TEST_BASE_URL || 'http://localhost:8003';

async function verifyTables() {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Navigate to admin users directly - should redirect to login if not authenticated
    console.log('Navigating to admin users page...');
    const response = await page.goto(`${baseURL}/admin/users`, { waitUntil: 'domcontentloaded' });
    console.log('Response status:', response?.status());
    console.log('Current URL:', page.url());
    
    // Check if we got redirected to login
    if (page.url().includes('/auth/login')) {
      console.log('Redirected to login page');
      
      const emailInput = page.locator('input[type="email"], input[name="email"]');
      const passwordInput = page.locator('input[type="password"], input[name="password"]');
      
      const emailExists = await emailInput.count() > 0;
      const passwordExists = await passwordInput.count() > 0;
      
      console.log('Email input exists:', emailExists);
      console.log('Password input exists:', passwordExists);
      
      if (emailExists && passwordExists) {
        await emailInput.fill('test_admin_ui@example.com');
        await passwordInput.fill('TestAdmin@Pass123456');
        
        // Click submit
        const submitBtn = page.locator('button[type="submit"]');
        const submitExists = await submitBtn.count() > 0;
        console.log('Submit button exists:', submitExists);
        
        if (submitExists) {
          await submitBtn.click();
          await page.waitForLoadState('networkidle');
          console.log('After login URL:', page.url());
          
          // Navigate to admin users
          await page.goto(`${baseURL}/admin/users`, { waitUntil: 'networkidle' });
        }
      }
    }
    
    console.log('\nFinal URL:', page.url());
    
    // Check table structure
    const table = await page.locator('table').first();
    const tableCount = await table.count();
    console.log('Table count:', tableCount);
    
    if (tableCount > 0) {
      const caption = await table.locator('caption').first();
      const captionText = await caption.textContent().catch(() => 'NOT FOUND');
      const ariaLabel = await table.getAttribute('aria-label');
      
      console.log('\nTable aria-label:', ariaLabel);
      console.log('Table caption:', captionText);
      
      const headers = await page.locator('table thead th');
      const headerCount = await headers.count();
      console.log('Header count:', headerCount);
      
      const headerInfo = await headers.evaluateAll((els) => {
        return els.map(el => ({
          text: el.textContent?.trim(),
          scope: el.getAttribute('scope')
        }));
      });
      
      console.log('\nHeaders:');
      headerInfo.forEach((h, i) => {
        console.log(`  ${i + 1}. "${h.text}" (scope="${h.scope}")`);
      });
    }
    
  } catch (err) {
    console.error('Error:', err.message);
  } finally {
    await browser.close();
  }
}

verifyTables();
