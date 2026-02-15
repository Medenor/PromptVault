import { test } from '@playwright/test';

test.describe('Table Structure Diagnostic', () => {
  test('Inspect Categories Table Structure', async ({ page }) => {
    await page.goto('http://127.0.0.1:8003/manage-categories');
    await page.waitForLoadState('networkidle');
    
    console.log('\n========== CATEGORIES TABLE INSPECTION ==========');
    
    // Get the full table HTML
    const tableHtml = await page.locator('table').first().evaluate(el => el.outerHTML);
    console.log('Table HTML (first 500 chars):', tableHtml.substring(0, 500));
    
    // Check what selectors exist
    const tables = await page.locator('table').count();
    console.log(`Total <table> elements: ${tables}`);
    
    const theads = await page.locator('thead').count();
    console.log(`Total <thead> elements: ${theads}`);
    
    const tbodies = await page.locator('tbody').count();
    console.log(`Total <tbody> elements: ${tbodies}`);
    
    const divTables = await page.locator('[role="table"]').count();
    console.log(`Total [role="table"] divs: ${divTables}`);
    
    const divRows = await page.locator('[role="row"]').count();
    console.log(`Total [role="row"] divs: ${divRows}`);
    
    // Try to find headers by class
    const headersByClass = await page.locator('.table-header, [class*="header"], th').count();
    console.log(`Headers found: ${headersByClass}`);
    
    // Get all text content from first row
    const firstRow = await page.locator('table tr').first().textContent();
    console.log(`First row content: ${firstRow?.substring(0, 100)}`);
    
    // Check if it's a div-based table
    const divTableContainer = await page.locator('div[role="table"]').first();
    if (await divTableContainer.count() > 0) {
      console.log('Found div-based table structure');
      const divHeaderCells = await divTableContainer.locator('div[role="columnheader"]').count();
      console.log(`Div-based header cells: ${divHeaderCells}`);
    }
    
    // Screenshot for visual inspection
    await page.screenshot({ path: '/tmp/categories-table-structure.png', fullPage: true });
    console.log('Screenshot saved to /tmp/categories-table-structure.png');
  });

  test('Inspect Tags Table Structure', async ({ page }) => {
    await page.goto('http://127.0.0.1:8003/manage-tags');
    await page.waitForLoadState('networkidle');
    
    console.log('\n========== TAGS TABLE INSPECTION ==========');
    
    // Get the full table HTML
    const tableHtml = await page.locator('table').first().evaluate(el => el.outerHTML);
    console.log('Table HTML (first 500 chars):', tableHtml.substring(0, 500));
    
    const tables = await page.locator('table').count();
    console.log(`Total <table> elements: ${tables}`);
    
    const theads = await page.locator('thead').count();
    console.log(`Total <thead> elements: ${theads}`);
    
    const tbodies = await page.locator('tbody').count();
    console.log(`Total <tbody> elements: ${tbodies}`);
    
    const divTables = await page.locator('[role="table"]').count();
    console.log(`Total [role="table"] divs: ${divTables}`);
    
    const divRows = await page.locator('[role="row"]').count();
    console.log(`Total [role="row"] divs: ${divRows}`);
    
    // Screenshot for visual inspection
    await page.screenshot({ path: '/tmp/tags-table-structure.png', fullPage: true });
    console.log('Screenshot saved to /tmp/tags-table-structure.png');
  });
});
