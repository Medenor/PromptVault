// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

// @ts-nocheck

/**
 * Diagnostic test to log actual contrast ratios being computed
 * Used to debug why authentication color contrast tests keep failing
 *
 * This test captures:
 * - Input element: foreground color, background color, computed contrast ratio
 * - Button element: foreground color, background color, computed contrast ratio
 * - Link element: foreground color, background color, computed contrast ratio
 */

import { test, expect } from '@playwright/test';
import {
  testTextContrast,
  testUIContrast,
  parseColor,
  calculateContrastRatio,
  calculateRelativeLuminance,
} from '../utils/contrast.js';
import { getBaseURL } from '../fixtures/auth.js';

const baseURL = getBaseURL();

test.skip('Contrast Ratio Diagnostics', () => {
  test('log contrast ratios for login page elements', async ({ page }) => {
    await page.goto(`${baseURL}/auth/login`, { waitUntil: 'networkidle' });

    console.log('\n========================================');
    console.log('CONTRAST RATIO DIAGNOSTICS - LOGIN PAGE');
    console.log('========================================\n');

    // Test Input Elements
    console.log('INPUT ELEMENTS:');
    console.log('----------------------------------------');
    const inputs = await page.locator('input').all();
    for (let i = 0; i < inputs.length; i++) {
      const input = inputs[i];
      const selector = await input.getAttribute('id') || `input[${i}]`;
      const type = await input.getAttribute('type') || 'text';

      console.log(`\n  Input ${i + 1} (${type}): #${selector}`);

      const result = await testTextContrast(page, input, 'AA');

      console.log(`    Computed color (foreground): ${result.foreground}`);
      console.log(`    Computed background: ${result.background}`);
      console.log(`    Contrast ratio: ${result.ratio}:1`);
      console.log(`    Required: ${result.required}:1`);
      console.log(`    Status: ${result.passes ? 'PASS' : 'FAIL'}`);

      if (result.violation) {
        console.log(`    Violation: ${result.violation}`);
      }

      // Parse and show luminance values for debugging
      try {
        const foreRGB = parseColor(result.foreground);
        const bgRGB = parseColor(result.background);
        const foreLum = calculateRelativeLuminance(foreRGB);
        const bgLum = calculateRelativeLuminance(bgRGB);

        console.log(`    Foreground RGB: rgb(${foreRGB.r}, ${foreRGB.g}, ${foreRGB.b})`);
        console.log(`    Background RGB: rgb(${bgRGB.r}, ${bgRGB.g}, ${bgRGB.b})`);
        console.log(`    Foreground luminance: ${foreLum.toFixed(4)}`);
        console.log(`    Background luminance: ${bgLum.toFixed(4)}`);
      } catch (e) {
        console.log(`    Error parsing colors: ${e.message}`);
      }
    }

    // Test Button Elements
    console.log('\n\nBUTTON ELEMENTS:');
    console.log('----------------------------------------');
    const buttons = await page.locator('button').all();
    for (let i = 0; i < buttons.length; i++) {
      const button = buttons[i];
      const text = await button.textContent();

      console.log(`\n  Button ${i + 1}: "${text?.trim().substring(0, 30)}"`);

      // Test as text contrast (button text)
      const textResult = await testTextContrast(page, button, 'AA');
      console.log(`    Text Contrast:`);
      console.log(`      Computed color (foreground): ${textResult.foreground}`);
      console.log(`      Computed background: ${textResult.background}`);
      console.log(`      Contrast ratio: ${textResult.ratio}:1`);
      console.log(`      Required: ${textResult.required}:1`);
      console.log(`      Status: ${textResult.passes ? 'PASS' : 'FAIL'}`);

      // Test as UI contrast (button border/outline)
      const uiResult = await testUIContrast(page, button, 'AA');
      console.log(`    UI Contrast:`);
      console.log(`      Computed color (foreground): ${uiResult.foreground}`);
      console.log(`      Computed background: ${uiResult.background}`);
      console.log(`      Contrast ratio: ${uiResult.ratio}:1`);
      console.log(`      Required: ${uiResult.required}:1`);
      console.log(`      Status: ${uiResult.passes ? 'PASS' : 'FAIL'}`);

      if (textResult.violation) {
        console.log(`    Text Violation: ${textResult.violation}`);
      }
      if (uiResult.violation) {
        console.log(`    UI Violation: ${uiResult.violation}`);
      }

      // Parse and show luminance values
      try {
        const foreRGB = parseColor(textResult.foreground);
        const bgRGB = parseColor(textResult.background);
        const foreLum = calculateRelativeLuminance(foreRGB);
        const bgLum = calculateRelativeLuminance(bgRGB);

        console.log(`    Foreground RGB: rgb(${foreRGB.r}, ${foreRGB.g}, ${foreRGB.b})`);
        console.log(`    Background RGB: rgb(${bgRGB.r}, ${bgRGB.g}, ${bgRGB.b})`);
        console.log(`    Foreground luminance: ${foreLum.toFixed(4)}`);
        console.log(`    Background luminance: ${bgLum.toFixed(4)}`);
      } catch (e) {
        console.log(`    Error parsing colors: ${e.message}`);
      }
    }

    // Test Link Elements
    console.log('\n\nLINK ELEMENTS:');
    console.log('----------------------------------------');
    const links = await page.locator('a').all();
    for (let i = 0; i < links.length; i++) {
      const link = links[i];
      const text = await link.textContent();

      if (!text?.trim().length) {
        console.log(`\n  Link ${i + 1}: (empty, skipped)`);
        continue;
      }

      console.log(`\n  Link ${i + 1}: "${text?.trim().substring(0, 30)}"`);

      const result = await testTextContrast(page, link, 'AA');

      console.log(`    Computed color (foreground): ${result.foreground}`);
      console.log(`    Computed background: ${result.background}`);
      console.log(`    Contrast ratio: ${result.ratio}:1`);
      console.log(`    Required: ${result.required}:1`);
      console.log(`    Status: ${result.passes ? 'PASS' : 'FAIL'}`);

      if (result.violation) {
        console.log(`    Violation: ${result.violation}`);
      }

      // Parse and show luminance values
      try {
        const foreRGB = parseColor(result.foreground);
        const bgRGB = parseColor(result.background);
        const foreLum = calculateRelativeLuminance(foreRGB);
        const bgLum = calculateRelativeLuminance(bgRGB);

        console.log(`    Foreground RGB: rgb(${foreRGB.r}, ${foreRGB.g}, ${foreRGB.b})`);
        console.log(`    Background RGB: rgb(${bgRGB.r}, ${bgRGB.g}, ${bgRGB.b})`);
        console.log(`    Foreground luminance: ${foreLum.toFixed(4)}`);
        console.log(`    Background luminance: ${bgLum.toFixed(4)}`);
      } catch (e) {
        console.log(`    Error parsing colors: ${e.message}`);
      }
    }

    console.log('\n========================================');
    console.log('END DIAGNOSTICS');
    console.log('========================================\n');

    // This test never fails - it's purely diagnostic
    expect(true).toBe(true);
  });

  test('detailed color inspection for specific elements', async ({ page }) => {
    await page.goto(`${baseURL}/auth/login`, { waitUntil: 'networkidle' });

    console.log('\n========================================');
    console.log('DETAILED ELEMENT INSPECTION');
    console.log('========================================\n');

    // Get the page's computed styles for all elements
    const details = await page.evaluate(() => {
      const info: any[] = [];

      // Check input elements
      document.querySelectorAll('input').forEach((el, idx) => {
        const style = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();

        info.push({
          type: 'input',
          index: idx,
          id: el.id,
          name: el.getAttribute('name'),
          inputType: el.type,
          color: style.color,
          backgroundColor: style.backgroundColor,
          borderColor: style.borderColor,
          outline: style.outline,
          fontSize: style.fontSize,
          fontWeight: style.fontWeight,
          visible: rect.width > 0 && rect.height > 0,
          width: rect.width,
          height: rect.height,
        });
      });

      // Check button elements
      document.querySelectorAll('button').forEach((el, idx) => {
        const style = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();

        info.push({
          type: 'button',
          index: idx,
          text: el.textContent?.substring(0, 30),
          color: style.color,
          backgroundColor: style.backgroundColor,
          borderColor: style.borderColor,
          outline: style.outline,
          fontSize: style.fontSize,
          fontWeight: style.fontWeight,
          visible: rect.width > 0 && rect.height > 0,
          width: rect.width,
          height: rect.height,
        });
      });

      // Check link elements
      document.querySelectorAll('a').forEach((el, idx) => {
        const style = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        const text = el.textContent?.trim();

        if (text && text.length > 0) {
          info.push({
            type: 'link',
            index: idx,
            text: text.substring(0, 30),
            color: style.color,
            backgroundColor: style.backgroundColor,
            textDecoration: style.textDecoration,
            fontSize: style.fontSize,
            fontWeight: style.fontWeight,
            visible: rect.width > 0 && rect.height > 0,
            width: rect.width,
            height: rect.height,
          });
        }
      });

      return info;
    });

    console.log('Computed Styles:');
    console.log(JSON.stringify(details, null, 2));

    console.log('\n========================================');
    console.log('END DETAILED INSPECTION');
    console.log('========================================\n');

    expect(true).toBe(true);
  });

  test('register page contrast diagnostics', async ({ page }) => {
    await page.goto(`${baseURL}/auth/register`, { waitUntil: 'networkidle' });

    console.log('\n========================================');
    console.log('CONTRAST RATIO DIAGNOSTICS - REGISTER PAGE');
    console.log('========================================\n');

    // Test all inputs
    console.log('INPUT ELEMENTS:');
    console.log('----------------------------------------');
    const inputs = await page.locator('input').all();
    for (let i = 0; i < inputs.length; i++) {
      const input = inputs[i];
      const type = await input.getAttribute('type') || 'text';
      const result = await testTextContrast(page, input, 'AA');

      console.log(`\n  Input ${i + 1} (${type}):`);
      console.log(`    Foreground: ${result.foreground}`);
      console.log(`    Background: ${result.background}`);
      console.log(`    Ratio: ${result.ratio}:1 (required: ${result.required}:1) - ${result.passes ? 'PASS' : 'FAIL'}`);
    }

    // Test all buttons
    console.log('\n\nBUTTON ELEMENTS:');
    console.log('----------------------------------------');
    const buttons = await page.locator('button').all();
    for (let i = 0; i < buttons.length; i++) {
      const button = buttons[i];
      const text = await button.textContent();
      const result = await testTextContrast(page, button, 'AA');

      console.log(`\n  Button ${i + 1}: "${text?.trim().substring(0, 30)}"`);
      console.log(`    Foreground: ${result.foreground}`);
      console.log(`    Background: ${result.background}`);
      console.log(`    Ratio: ${result.ratio}:1 (required: ${result.required}:1) - ${result.passes ? 'PASS' : 'FAIL'}`);
    }

    console.log('\n========================================');
    console.log('END DIAGNOSTICS');
    console.log('========================================\n');

    expect(true).toBe(true);
  });
});
