import { test } from '@playwright/test';
import { authenticatedAdminTest } from './fixtures/auth.js';

test.describe('Table ARIA Attributes - Visual Verification (Authenticated)', () => {
  
  authenticatedAdminTest('Verify Admin Users Table with Authentication', async ({ authenticatedPage: page }) => {
    await page.goto('http://127.0.0.1:8003/admin/users');
    await page.waitForLoadState('networkidle');
    
    console.log('\n========== ADMIN USERS TABLE - AUTHENTICATED VIEW ==========');
    
    // Take full page screenshot
    await page.screenshot({ path: '/tmp/admin-users-table-authenticated.png', fullPage: true });
    console.log('Screenshot saved: /tmp/admin-users-table-authenticated.png');
    
    // Verify table exists on page
    const tableElements = await page.locator('table').count();
    console.log(`Tables found on page: ${tableElements}`);
    
    // Get table HTML structure info
    const tableInfo = await page.evaluate(() => {
      const table = document.querySelector('table');
      if (!table) return null;
      
      return {
        hasCaption: !!table.querySelector('caption'),
        captionText: table.querySelector('caption')?.textContent?.substring(0, 100) || null,
        headerCount: table.querySelectorAll('thead th').length,
        headers: Array.from(table.querySelectorAll('thead th')).map(th => ({
          text: th.textContent?.trim().substring(0, 30),
          scope: th.getAttribute('scope'),
          ariaLabel: th.getAttribute('aria-label')
        })),
        bodyRowCount: table.querySelectorAll('tbody tr').length,
        tableAriaLabel: table.getAttribute('aria-label')
      };
    });
    
    if (tableInfo) {
      console.log('\nTable Structure:');
      console.log(`- Has Caption: ${tableInfo.hasCaption ? 'YES' : 'NO'}`);
      if (tableInfo.captionText) {
        console.log(`- Caption: "${tableInfo.captionText}..."`);
      }
      console.log(`- Table ARIA Label: "${tableInfo.tableAriaLabel}"`);
      console.log(`- Header Count: ${tableInfo.headerCount}`);
      console.log('\nTable Headers:');
      tableInfo.headers.forEach((header, idx) => {
        console.log(`  ${idx + 1}. "${header.text}"`);
        console.log(`     scope="${header.scope}" ${header.scope === 'col' ? '✓' : '✗'}`);
        if (header.ariaLabel) {
          console.log(`     aria-label="${header.ariaLabel}"`);
        }
      });
      console.log(`\n- Body Rows: ${tableInfo.bodyRowCount}`);
    }
    
    console.log('\n✓ Admin Users Table Verification Complete');
  });

  authenticatedAdminTest('Verify Admin Sessions Table with Authentication', async ({ authenticatedPage: page }) => {
    await page.goto('http://127.0.0.1:8003/admin/sessions');
    await page.waitForLoadState('networkidle');
    
    console.log('\n========== ADMIN SESSIONS TABLE - AUTHENTICATED VIEW ==========');
    
    // Take full page screenshot
    await page.screenshot({ path: '/tmp/admin-sessions-table-authenticated.png', fullPage: true });
    console.log('Screenshot saved: /tmp/admin-sessions-table-authenticated.png');
    
    // Verify table structure
    const tableInfo = await page.evaluate(() => {
      const table = document.querySelector('table');
      if (!table) return null;
      
      return {
        hasCaption: !!table.querySelector('caption'),
        captionText: table.querySelector('caption')?.textContent?.substring(0, 100) || null,
        headerCount: table.querySelectorAll('thead th').length,
        headers: Array.from(table.querySelectorAll('thead th')).map(th => ({
          text: th.textContent?.trim().substring(0, 30),
          scope: th.getAttribute('scope'),
          ariaLabel: th.getAttribute('aria-label')
        })),
        bodyRowCount: table.querySelectorAll('tbody tr').length,
        tableAriaLabel: table.getAttribute('aria-label')
      };
    });
    
    if (tableInfo) {
      console.log('\nTable Structure:');
      console.log(`- Has Caption: ${tableInfo.hasCaption ? 'YES' : 'NO'}`);
      if (tableInfo.captionText) {
        console.log(`- Caption: "${tableInfo.captionText}..."`);
      }
      console.log(`- Table ARIA Label: "${tableInfo.tableAriaLabel}"`);
      console.log(`- Header Count: ${tableInfo.headerCount}`);
      console.log('\nTable Headers:');
      tableInfo.headers.forEach((header, idx) => {
        console.log(`  ${idx + 1}. "${header.text}"`);
        console.log(`     scope="${header.scope}" ${header.scope === 'col' ? '✓' : '✗'}`);
        if (header.ariaLabel) {
          console.log(`     aria-label="${header.ariaLabel}"`);
        }
      });
      console.log(`\n- Body Rows: ${tableInfo.bodyRowCount}`);
    }
    
    console.log('\n✓ Admin Sessions Table Verification Complete');
  });
});
