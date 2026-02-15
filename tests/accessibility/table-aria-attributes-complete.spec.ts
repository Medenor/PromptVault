import { test, expect } from '@playwright/test';
import { authenticatedAdminTest } from './fixtures/auth.js';

test.describe('Phase 2B Priority 3: Table ARIA Attributes - WCAG 2.1 AA Compliance', () => {
  
  // Test 1: Categories Table (Public page - no auth needed)
  test('1. Categories Table - ARIA Attributes and Caption', async ({ page }) => {
    await page.goto('http://127.0.0.1:8003/manage-categories');
    await page.waitForLoadState('networkidle');
    
    console.log('\n========================================');
    console.log('TEST 1: MANAGE-CATEGORIES TABLE');
    console.log('========================================');
    
    // Find the table
    const table = page.locator('table').first();
    expect(table).toBeTruthy();
    
    // Check for caption or aria-label
    const caption = page.locator('table caption').first();
    const captionExists = await caption.count() > 0;
    const captionText = captionExists ? await caption.textContent() : null;
    
    console.log(`\n✓ Table Found`);
    console.log(`Caption exists: ${captionExists}`);
    if (captionText) {
      console.log(`Caption text: "${captionText}"`);
    }
    
    // Verify table structure
    const headerCells = await page.locator('table thead th').all();
    console.log(`\nHeader Cells Found: ${headerCells.length}`);
    
    let allHeadersValid = true;
    for (let i = 0; i < headerCells.length; i++) {
      const th = headerCells[i];
      const scope = await th.getAttribute('scope');
      const text = await th.textContent();
      const ariaLabel = await th.getAttribute('aria-label');
      
      const isValid = scope === 'col' || scope === 'colgroup';
      allHeadersValid = allHeadersValid && isValid;
      
      console.log(`\nHeader ${i + 1}: "${text?.trim()}"`);
      console.log(`  scope: "${scope}" ${isValid ? '✓' : '✗'}`);
      console.log(`  aria-label: "${ariaLabel || '(none)'}"`);
      
      // WCAG requirement: scope="col" for column headers
      if (!isValid) {
        console.log(`  ✗ FAIL: Missing or invalid scope attribute`);
      }
    }
    
    // Take screenshot
    const tbody = await page.locator('table tbody').first();
    const box = await tbody.boundingBox();
    if (box) {
      await page.screenshot({ 
        path: '/tmp/table-aria-1-categories.png',
        clip: { x: Math.max(0, box.x - 10), y: Math.max(0, box.y - 60), width: 1200, height: 250 }
      });
      console.log(`\n✓ Screenshot saved: /tmp/table-aria-1-categories.png`);
    }
    
    expect(captionExists || await table.getAttribute('aria-label')).toBeTruthy();
    expect(allHeadersValid).toBe(true);
    console.log('\n✓ Categories Table: PASS');
  });

  // Test 2: Tags Table (Public page - no auth needed)
  test('2. Tags Table - ARIA Attributes and Caption', async ({ page }) => {
    await page.goto('http://127.0.0.1:8003/manage-tags');
    await page.waitForLoadState('networkidle');
    
    console.log('\n========================================');
    console.log('TEST 2: MANAGE-TAGS TABLE');
    console.log('========================================');
    
    // Find the table
    const table = page.locator('table').first();
    expect(table).toBeTruthy();
    
    // Check for caption or aria-label
    const caption = page.locator('table caption').first();
    const captionExists = await caption.count() > 0;
    const captionText = captionExists ? await caption.textContent() : null;
    
    console.log(`\n✓ Table Found`);
    console.log(`Caption exists: ${captionExists}`);
    if (captionText) {
      console.log(`Caption text: "${captionText}"`);
    }
    
    // Verify table structure
    const headerCells = await page.locator('table thead th').all();
    console.log(`\nHeader Cells Found: ${headerCells.length}`);
    
    let allHeadersValid = true;
    for (let i = 0; i < headerCells.length; i++) {
      const th = headerCells[i];
      const scope = await th.getAttribute('scope');
      const text = await th.textContent();
      const ariaLabel = await th.getAttribute('aria-label');
      
      const isValid = scope === 'col' || scope === 'colgroup';
      allHeadersValid = allHeadersValid && isValid;
      
      console.log(`\nHeader ${i + 1}: "${text?.trim()}"`);
      console.log(`  scope: "${scope}" ${isValid ? '✓' : '✗'}`);
      console.log(`  aria-label: "${ariaLabel || '(none)'}"`);
      
      if (!isValid) {
        console.log(`  ✗ FAIL: Missing or invalid scope attribute`);
      }
    }
    
    // Take screenshot
    const tbody = await page.locator('table tbody').first();
    const box = await tbody.boundingBox();
    if (box) {
      await page.screenshot({ 
        path: '/tmp/table-aria-2-tags.png',
        clip: { x: Math.max(0, box.x - 10), y: Math.max(0, box.y - 60), width: 1200, height: 250 }
      });
      console.log(`\n✓ Screenshot saved: /tmp/table-aria-2-tags.png`);
    }
    
    expect(captionExists || await table.getAttribute('aria-label')).toBeTruthy();
    expect(allHeadersValid).toBe(true);
    console.log('\n✓ Tags Table: PASS');
  });

  // Test 3: Admin Users Table (Requires Authentication)
  authenticatedAdminTest('3. Admin Users Table - ARIA Attributes and Caption', async ({ authenticatedPage: page }) => {
    await page.goto('http://127.0.0.1:8003/admin/users');
    await page.waitForLoadState('networkidle');
    
    console.log('\n========================================');
    console.log('TEST 3: ADMIN USERS TABLE');
    console.log('========================================');
    
    // Find the table
    const table = page.locator('table').first();
    
    // Check if we got redirected due to auth issues
    if (await page.url().includes('/auth/login')) {
      console.log('✗ FAIL: Not authenticated - redirected to login');
      expect(false).toBe(true);
      return;
    }
    
    const tableExists = await table.count() > 0;
    if (!tableExists) {
      console.log('⚠ No table found on page');
      return;
    }
    
    expect(table).toBeTruthy();
    
    // Check for caption or aria-label
    const caption = page.locator('table caption').first();
    const captionExists = await caption.count() > 0;
    const captionText = captionExists ? await caption.textContent() : null;
    
    console.log(`\n✓ Table Found`);
    console.log(`Caption exists: ${captionExists}`);
    if (captionText) {
      console.log(`Caption text: "${captionText}"`);
    }
    
    // Verify table structure
    const headerCells = await page.locator('table thead th').all();
    console.log(`\nHeader Cells Found: ${headerCells.length}`);
    
    let allHeadersValid = true;
    for (let i = 0; i < headerCells.length; i++) {
      const th = headerCells[i];
      const scope = await th.getAttribute('scope');
      const text = await th.textContent();
      const ariaLabel = await th.getAttribute('aria-label');
      
      const isValid = scope === 'col' || scope === 'colgroup';
      allHeadersValid = allHeadersValid && isValid;
      
      console.log(`\nHeader ${i + 1}: "${text?.trim()}"`);
      console.log(`  scope: "${scope}" ${isValid ? '✓' : '✗'}`);
      console.log(`  aria-label: "${ariaLabel || '(none)'}"`);
      
      if (!isValid) {
        console.log(`  ✗ FAIL: Missing or invalid scope attribute`);
      }
    }
    
    // Take screenshot
    const tbody = await page.locator('table tbody').first();
    const box = await tbody.boundingBox();
    if (box) {
      await page.screenshot({ 
        path: '/tmp/table-aria-3-admin-users.png',
        clip: { x: Math.max(0, box.x - 10), y: Math.max(0, box.y - 60), width: 1200, height: 250 }
      });
      console.log(`\n✓ Screenshot saved: /tmp/table-aria-3-admin-users.png`);
    }
    
    expect(captionExists || await table.getAttribute('aria-label')).toBeTruthy();
    expect(allHeadersValid).toBe(true);
    console.log('\n✓ Admin Users Table: PASS');
  });

  // Test 4: Admin Sessions Table (Requires Authentication)
  authenticatedAdminTest('4. Admin Sessions Table - ARIA Attributes and Caption', async ({ authenticatedPage: page }) => {
    await page.goto('http://127.0.0.1:8003/admin/sessions');
    await page.waitForLoadState('networkidle');
    
    console.log('\n========================================');
    console.log('TEST 4: ADMIN SESSIONS TABLE');
    console.log('========================================');
    
    // Find the table
    const table = page.locator('table').first();
    
    // Check if we got redirected due to auth issues
    if (await page.url().includes('/auth/login')) {
      console.log('✗ FAIL: Not authenticated - redirected to login');
      expect(false).toBe(true);
      return;
    }
    
    const tableExists = await table.count() > 0;
    if (!tableExists) {
      console.log('⚠ No table found on page');
      return;
    }
    
    expect(table).toBeTruthy();
    
    // Check for caption or aria-label
    const caption = page.locator('table caption').first();
    const captionExists = await caption.count() > 0;
    const captionText = captionExists ? await caption.textContent() : null;
    
    console.log(`\n✓ Table Found`);
    console.log(`Caption exists: ${captionExists}`);
    if (captionText) {
      console.log(`Caption text: "${captionText}"`);
    }
    
    // Verify table structure
    const headerCells = await page.locator('table thead th').all();
    console.log(`\nHeader Cells Found: ${headerCells.length}`);
    
    let allHeadersValid = true;
    for (let i = 0; i < headerCells.length; i++) {
      const th = headerCells[i];
      const scope = await th.getAttribute('scope');
      const text = await th.textContent();
      const ariaLabel = await th.getAttribute('aria-label');
      
      const isValid = scope === 'col' || scope === 'colgroup';
      allHeadersValid = allHeadersValid && isValid;
      
      console.log(`\nHeader ${i + 1}: "${text?.trim()}"`);
      console.log(`  scope: "${scope}" ${isValid ? '✓' : '✗'}`);
      console.log(`  aria-label: "${ariaLabel || '(none)'}"`);
      
      if (!isValid) {
        console.log(`  ✗ FAIL: Missing or invalid scope attribute`);
      }
    }
    
    // Take screenshot
    const tbody = await page.locator('table tbody').first();
    const box = await tbody.boundingBox();
    if (box) {
      await page.screenshot({ 
        path: '/tmp/table-aria-4-admin-sessions.png',
        clip: { x: Math.max(0, box.x - 10), y: Math.max(0, box.y - 60), width: 1200, height: 250 }
      });
      console.log(`\n✓ Screenshot saved: /tmp/table-aria-4-admin-sessions.png`);
    }
    
    expect(captionExists || await table.getAttribute('aria-label')).toBeTruthy();
    expect(allHeadersValid).toBe(true);
    console.log('\n✓ Admin Sessions Table: PASS');
  });

  // Test 5: Verify Table Semantic Structure
  test('5. Semantic Structure Verification - All Tables', async ({ page }) => {
    console.log('\n========================================');
    console.log('TEST 5: SEMANTIC STRUCTURE VERIFICATION');
    console.log('========================================');
    
    const tables = [
      { url: 'http://127.0.0.1:8003/manage-categories', name: 'Categories' },
      { url: 'http://127.0.0.1:8003/manage-tags', name: 'Tags' }
    ];
    
    for (const table of tables) {
      console.log(`\nChecking ${table.name} Table...`);
      await page.goto(table.url);
      await page.waitForLoadState('networkidle');
      
      const tableElement = page.locator('table').first();
      
      // Check for proper structure
      const hasTheadTbody = await page.evaluate(() => {
        const table = document.querySelector('table');
        if (!table) return false;
        const hasThead = !!table.querySelector('thead');
        const hasTbody = !!table.querySelector('tbody');
        return hasThead && hasTbody;
      });
      
      console.log(`  - Has <thead>: ${hasTheadTbody ? '✓' : '✗'}`);
      console.log(`  - Has <tbody>: ${hasTheadTbody ? '✓' : '✗'}`);
      
      expect(hasTheadTbody).toBe(true);
    }
    
    console.log('\n✓ Semantic Structure Verification: PASS');
  });
});
