import { chromium } from 'playwright';
import * as fs from 'fs';
import * as path from 'path';

const BASE_URL = 'http://localhost:8003';
const SCREENSHOTS_DIR = './focus-management-screenshots';

// Create screenshots directory
if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

let browser;
let context;
let page;
let testResults = [];

async function logTest(name, passed, details = '') {
  const result = { name, passed, details, timestamp: new Date().toISOString() };
  testResults.push(result);
  console.log(`${passed ? 'PASS' : 'FAIL'}: ${name} ${details ? '- ' + details : ''}`);
}

async function setup() {
  browser = await chromium.launch({ headless: true });
  context = await browser.newContext({
    viewport: { width: 1280, height: 720 }
  });
  page = await context.newPage();
  
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      console.error('PAGE ERROR:', msg.text());
    }
  });
}

async function teardown() {
  if (page) await page.close();
  if (context) await context.close();
  if (browser) await browser.close();
}

async function takeScreenshot(name) {
  const filename = `${SCREENSHOTS_DIR}/${name.replace(/\s+/g, '_').toLowerCase()}.png`;
  await page.screenshot({ path: filename, fullPage: true });
  return filename;
}

async function getFocusedElement() {
  return await page.evaluate(() => {
    const focused = document.activeElement;
    if (!focused) return null;
    return {
      tagName: focused.tagName,
      id: focused.id,
      className: focused.className,
      ariaLabel: focused.getAttribute('aria-label'),
      textContent: focused.textContent?.substring(0, 50)
    };
  });
}

async function test1_ModalOpensAndFocusMoves() {
  console.log('\n=== Test 1: Modal Opens and Focus Moves ===');
  
  try {
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    
    const deleteButtons = await page.$$('.delete-btn');
    if (deleteButtons.length === 0) {
      await logTest('Test 1: Modal Opens', false, 'No delete buttons found');
      return;
    }
    
    const firstDeleteButton = deleteButtons[0];
    const initialFocus = await getFocusedElement();
    console.log('Initial focus:', initialFocus);
    
    await firstDeleteButton.click();
    await page.waitForTimeout(500);
    
    const focusAfterModal = await getFocusedElement();
    console.log('Focus after modal opens:', focusAfterModal);
    
    await takeScreenshot('test1_modal_opened_focus_moved');
    
    const focusMoved = focusAfterModal && focusAfterModal.textContent !== initialFocus?.textContent;
    await logTest('Test 1: Modal Opens and Focus Moves', focusMoved, `Focus moved from ${initialFocus?.tagName} to ${focusAfterModal?.tagName}`);
    
  } catch (error) {
    await logTest('Test 1: Modal Opens', false, error.message);
  }
}

async function test2_ModalCloseButtonRestoresFocus() {
  console.log('\n=== Test 2: Modal Close Button Restores Focus ===');
  
  try {
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    
    const deleteButtons = await page.$$('.delete-btn');
    if (deleteButtons.length === 0) {
      await logTest('Test 2: Modal Close Restores Focus', false, 'No delete buttons found');
      return;
    }
    
    const firstDeleteButton = deleteButtons[0];
    
    await firstDeleteButton.click();
    await page.waitForTimeout(500);
    
    const focusInModal = await getFocusedElement();
    console.log('Focus in modal:', focusInModal);
    
    const closeButton = await page.$('button:has-text("Cancel")');
    if (closeButton) {
      await closeButton.click();
    }
    
    await page.waitForTimeout(500);
    
    const focusAfterClose = await getFocusedElement();
    console.log('Focus after modal closes:', focusAfterClose);
    
    await takeScreenshot('test2_modal_closed_focus_restored');
    
    const focusRestored = focusAfterClose && focusAfterClose.textContent?.includes('Delete');
    await logTest('Test 2: Modal Close Restores Focus', focusRestored, `Focus after close: ${focusAfterClose?.textContent || focusAfterClose?.ariaLabel}`);
    
  } catch (error) {
    await logTest('Test 2: Modal Close Restores Focus', false, error.message);
  }
}

async function test3_EscapeKeyClosesFocusRestored() {
  console.log('\n=== Test 3: Escape Key Closes Modal and Restores Focus ===');
  
  try {
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    
    const historyButtons = await page.$$('.history-btn');
    if (historyButtons.length === 0) {
      await logTest('Test 3: Escape Restores Focus', false, 'No history buttons found');
      return;
    }
    
    const firstHistoryButton = historyButtons[0];
    
    await firstHistoryButton.click();
    await page.waitForTimeout(500);
    
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
    
    const focusAfterEscape = await getFocusedElement();
    console.log('Focus after Escape:', focusAfterEscape);
    
    await takeScreenshot('test3_escape_closes_restores_focus');
    
    const focusRestored = focusAfterEscape && focusAfterEscape.textContent?.includes('History');
    await logTest('Test 3: Escape Restores Focus', focusRestored, `Focus after Escape: ${focusAfterEscape?.textContent || focusAfterEscape?.ariaLabel}`);
    
  } catch (error) {
    await logTest('Test 3: Escape Restores Focus', false, error.message);
  }
}

async function test4_FocusIndicatorVisible() {
  console.log('\n=== Test 4: Focus Indicators Are Visible ===');
  
  try {
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    
    await page.keyboard.press('Tab');
    await page.waitForTimeout(300);
    
    const focusedElement = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el) return null;
      const style = window.getComputedStyle(el);
      return {
        hasOutline: style.outlineWidth !== '0px' && style.outlineWidth !== 'none',
        outlineWidth: style.outlineWidth,
        outlineColor: style.outlineColor,
        hasRing: el.className?.includes('ring') || el.className?.includes('focus'),
        className: el.className,
        id: el.id
      };
    });
    
    console.log('Focused element style:', focusedElement);
    
    await takeScreenshot('test4_focus_indicator_visible');
    
    const hasVisibleFocus = focusedElement && (focusedElement.hasOutline || focusedElement.hasRing);
    await logTest('Test 4: Focus Indicator Visible', hasVisibleFocus, `Outline: ${focusedElement?.outlineWidth}, Ring class: ${focusedElement?.hasRing}`);
    
  } catch (error) {
    await logTest('Test 4: Focus Indicator Visible', false, error.message);
  }
}

async function test5_KeyboardNavigationFocus() {
  console.log('\n=== Test 5: Keyboard Navigation with Focus ===');
  
  try {
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    
    await page.keyboard.press('Tab');
    let currentFocus = await getFocusedElement();
    console.log('First tab lands on:', currentFocus);
    
    let focusSequence = [currentFocus];
    
    for (let i = 0; i < 5; i++) {
      await page.keyboard.press('Tab');
      await page.waitForTimeout(200);
      currentFocus = await getFocusedElement();
      focusSequence.push(currentFocus);
      console.log(`Tab ${i + 2}:`, currentFocus?.textContent || currentFocus?.id || currentFocus?.tagName);
    }
    
    await takeScreenshot('test5_keyboard_navigation');
    
    const uniqueFocuses = new Set(focusSequence.map(f => f?.id || f?.textContent));
    const hasProperSequence = focusSequence.length > 0 && uniqueFocuses.size > 1;
    
    await logTest('Test 5: Keyboard Navigation Focus', hasProperSequence, `Focused ${uniqueFocuses.size} unique elements`);
    
  } catch (error) {
    await logTest('Test 5: Keyboard Navigation Focus', false, error.message);
  }
}

async function test6_ManageCategoriesDelete() {
  console.log('\n=== Test 6: Manage Categories Page Focus ===');
  
  try {
    await page.goto(`${BASE_URL}/manage-categories`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    
    await takeScreenshot('test6_manage_categories_page');
    
    const pageTitle = await page.$('h1');
    const titleText = await pageTitle?.textContent();
    const pageLoaded = titleText?.includes('Categories');
    
    await logTest('Test 6: Manage Categories Page Loads', pageLoaded, `Page title: ${titleText}`);
    
  } catch (error) {
    await logTest('Test 6: Manage Categories Page', false, error.message);
  }
}

async function test7_ManageTagsPage() {
  console.log('\n=== Test 7: Manage Tags Page Focus ===');
  
  try {
    await page.goto(`${BASE_URL}/manage-tags`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    
    await takeScreenshot('test7_manage_tags_page');
    
    const pageTitle = await page.$('h1');
    const titleText = await pageTitle?.textContent();
    const pageLoaded = titleText?.includes('Tags');
    
    await logTest('Test 7: Manage Tags Page Loads', pageLoaded, `Page title: ${titleText}`);
    
  } catch (error) {
    await logTest('Test 7: Manage Tags Page', false, error.message);
  }
}

async function runAllTests() {
  console.log('Starting Focus Management Tests...');
  console.log(`Base URL: ${BASE_URL}`);
  console.log(`Screenshots: ${SCREENSHOTS_DIR}`);
  
  await setup();
  
  try {
    await test1_ModalOpensAndFocusMoves();
    await test2_ModalCloseButtonRestoresFocus();
    await test3_EscapeKeyClosesFocusRestored();
    await test4_FocusIndicatorVisible();
    await test5_KeyboardNavigationFocus();
    await test6_ManageCategoriesDelete();
    await test7_ManageTagsPage();
  } finally {
    await teardown();
  }
  
  console.log('\n\n=== TEST SUMMARY ===');
  const passed = testResults.filter(r => r.passed).length;
  const failed = testResults.filter(r => !r.passed).length;
  
  console.log(`Total: ${testResults.length} | Passed: ${passed} | Failed: ${failed}`);
  
  testResults.forEach(result => {
    console.log(`${result.passed ? 'PASS' : 'FAIL'} ${result.name}`);
  });
  
  fs.writeFileSync('focus_test_results.json', JSON.stringify(testResults, null, 2));
  console.log('\nDetailed results saved to focus_test_results.json');
  console.log(`Screenshots saved to ${SCREENSHOTS_DIR}`);
}

runAllTests().catch(err => {
  console.error('Test suite error:', err);
  process.exit(1);
});
