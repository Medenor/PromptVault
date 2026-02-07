// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

/**
 * Color contrast calculation utilities for WCAG 2.1 accessibility testing
 * Implements relative luminance and contrast ratio calculations per WCAG 2.1 guidelines
 */

/**
 * Parse CSS color string to RGB values
 * Supports: rgb(), rgba(), hex, named colors, hsl()
 *
 * @param {string} color - CSS color string (e.g., 'rgb(255, 0, 0)', '#FF0000', 'red')
 * @returns {{r: number, g: number, b: number}} RGB values (0-255)
 * @throws {Error} If color format is not recognized
 */
export function parseColor(color) {
  const trimmed = color.trim().toLowerCase();

  // Handle rgb() and rgba()
  const rgbMatch = trimmed.match(/rgba?\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/);
  if (rgbMatch) {
    return {
      r: parseInt(rgbMatch[1], 10),
      g: parseInt(rgbMatch[2], 10),
      b: parseInt(rgbMatch[3], 10),
    };
  }

  // Handle hex colors
  if (trimmed.startsWith('#')) {
    const hex = trimmed.slice(1);
    if (hex.length === 3) {
      return {
        r: parseInt(hex[0] + hex[0], 16),
        g: parseInt(hex[1] + hex[1], 16),
        b: parseInt(hex[2] + hex[2], 16),
      };
    }
    if (hex.length === 6) {
      return {
        r: parseInt(hex.slice(0, 2), 16),
        g: parseInt(hex.slice(2, 4), 16),
        b: parseInt(hex.slice(4, 6), 16),
      };
    }
  }

  // Handle named colors (basic set)
  const namedColors = {
    black: { r: 0, g: 0, b: 0 },
    white: { r: 255, g: 255, b: 255 },
    red: { r: 255, g: 0, b: 0 },
    green: { r: 0, g: 128, b: 0 },
    blue: { r: 0, g: 0, b: 255 },
    gray: { r: 128, g: 128, b: 128 },
    grey: { r: 128, g: 128, b: 128 },
  };

  if (namedColors[trimmed]) {
    return namedColors[trimmed];
  }

  throw new Error(`Unsupported color format: ${color}`);
}

/**
 * Calculate relative luminance of an RGB color per WCAG 2.1 specification
 * https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
 *
 * @param {{r: number, g: number, b: number}} rgb - RGB values (0-255)
 * @returns {number} Relative luminance (0-1)
 */
export function calculateRelativeLuminance(rgb) {
  // Convert to 0-1 range
  const r = rgb.r / 255;
  const g = rgb.g / 255;
  const b = rgb.b / 255;

  // Apply linearization formula per WCAG 2.1
  const rsRGB = r <= 0.03928 ? r / 12.92 : Math.pow((r + 0.055) / 1.055, 2.4);
  const gsRGB = g <= 0.03928 ? g / 12.92 : Math.pow((g + 0.055) / 1.055, 2.4);
  const bsRGB = b <= 0.03928 ? b / 12.92 : Math.pow((b + 0.055) / 1.055, 2.4);

  return 0.2126 * rsRGB + 0.7152 * gsRGB + 0.0722 * bsRGB;
}

/**
 * Calculate contrast ratio between two colors per WCAG 2.1
 * https://www.w3.org/TR/WCAG21/#dfn-contrast-ratio
 *
 * @param {{r: number, g: number, b: number}} color1 - First RGB color
 * @param {{r: number, g: number, b: number}} color2 - Second RGB color
 * @returns {number} Contrast ratio (typically 1-21)
 */
export function calculateContrastRatio(color1, color2) {
  const lum1 = calculateRelativeLuminance(color1);
  const lum2 = calculateRelativeLuminance(color2);

  const lighter = Math.max(lum1, lum2);
  const darker = Math.min(lum1, lum2);

  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * Validate contrast ratio meets WCAG 2.1 standards
 *
 * @param {number} ratio - Contrast ratio to validate
 * @param {'AA' | 'AAA'} level - Conformance level (AA or AAA)
 * @param {'text' | 'ui'} type - Type of element (text or UI component)
 * @returns {boolean} True if ratio meets standard
 */
export function isContrastCompliant(ratio, level = 'AA', type = 'text') {
  const standards = {
    AA: { text: 4.5, ui: 3 },
    AAA: { text: 7, ui: 4.5 },
  };

  const required = standards[level]?.[type] ?? 0;
  return ratio >= required;
}

/**
 * Get computed text and background colors from an element using Playwright page context
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {import('@playwright/test').Locator} element - Element locator
 * @returns {Promise<{foreground: string, background: string}>} Computed colors
 */
export async function getElementColors(page, element) {
  return await element.evaluate((el) => {
    const style = window.getComputedStyle(el);
    return {
      foreground: style.color,
      background: style.backgroundColor,
    };
  });
}

/**
 * Get background color, accounting for inheritance from parent elements
 * Walks up the DOM tree until a non-transparent color is found
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {import('@playwright/test').Locator} element - Element locator
 * @returns {Promise<string>} Computed background color
 */
export async function getEffectiveBackgroundColor(page, element) {
  return await element.evaluate((el) => {
    let current = el;
    while (current) {
      const style = window.getComputedStyle(current);
      const bgColor = style.backgroundColor;

      // Check if color is not transparent
      if (bgColor && bgColor !== 'rgba(0, 0, 0, 0)' && bgColor !== 'transparent') {
        return bgColor;
      }

      current = current.parentElement;
    }
    // Default to white if we reach document root
    return 'rgb(255, 255, 255)';
  });
}

/**
 * Test contrast ratio of text element against its background
 * Returns detailed results for analysis
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {import('@playwright/test').Locator} element - Text element to test
 * @param {'AA' | 'AAA'} wcagLevel - WCAG conformance level
 * @returns {Promise<{
 *   ratio: number,
 *   passes: boolean,
 *   foreground: string,
 *   background: string,
 *   required: number,
 *   violation: string | null
 * }>} Contrast test results
 */
export async function testTextContrast(page, element, wcagLevel = 'AA') {
  const colors = await getElementColors(page, element);
  const background = await getEffectiveBackgroundColor(page, element);

  try {
    const foreRGB = parseColor(colors.foreground);
    const bgRGB = parseColor(background);

    const ratio = calculateContrastRatio(foreRGB, bgRGB);
    const passes = isContrastCompliant(ratio, wcagLevel, 'text');
    const required = wcagLevel === 'AAA' ? 7 : 4.5;

    return {
      ratio: Math.round(ratio * 100) / 100,
      passes,
      foreground: colors.foreground,
      background,
      required,
      violation: passes ? null : `Contrast ratio ${ratio.toFixed(2)}:1 below required ${required}:1 for WCAG ${wcagLevel}`,
    };
  } catch (error) {
    return {
      ratio: 0,
      passes: false,
      foreground: colors.foreground,
      background,
      required: wcagLevel === 'AAA' ? 7 : 4.5,
      violation: `Failed to analyze contrast: ${error.message}`,
    };
  }
}

/**
 * Test contrast ratio of UI component (button, link, etc.)
 * Returns detailed results for analysis
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {import('@playwright/test').Locator} element - UI component to test
 * @param {'AA' | 'AAA'} wcagLevel - WCAG conformance level
 * @returns {Promise<{
 *   ratio: number,
 *   passes: boolean,
 *   foreground: string,
 *   background: string,
 *   required: number,
 *   violation: string | null
 * }>} Contrast test results
 */
export async function testUIContrast(page, element, wcagLevel = 'AA') {
  const colors = await getElementColors(page, element);
  const background = await getEffectiveBackgroundColor(page, element);

  try {
    const foreRGB = parseColor(colors.foreground);
    const bgRGB = parseColor(background);

    const ratio = calculateContrastRatio(foreRGB, bgRGB);
    const passes = isContrastCompliant(ratio, wcagLevel, 'ui');
    const required = wcagLevel === 'AAA' ? 4.5 : 3;

    return {
      ratio: Math.round(ratio * 100) / 100,
      passes,
      foreground: colors.foreground,
      background,
      required,
      violation: passes ? null : `Contrast ratio ${ratio.toFixed(2)}:1 below required ${required}:1 for WCAG ${wcagLevel} UI`,
    };
  } catch (error) {
    return {
      ratio: 0,
      passes: false,
      foreground: colors.foreground,
      background,
      required: wcagLevel === 'AAA' ? 4.5 : 3,
      violation: `Failed to analyze UI contrast: ${error.message}`,
    };
  }
}

/**
 * Batch test contrast for multiple elements
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} selector - CSS selector for elements to test
 * @param {'AA' | 'AAA'} wcagLevel - WCAG conformance level
 * @param {'text' | 'ui'} type - Type of element
 * @returns {Promise<Array>} Array of test results
 */
export async function testContrastBatch(page, selector, wcagLevel = 'AA', type = 'text') {
  const elements = await page.locator(selector).all();
  const results = [];

  for (const element of elements) {
    const testFn = type === 'ui' ? testUIContrast : testTextContrast;
    const result = await testFn(page, element, wcagLevel);
    results.push({
      ...result,
      selector,
    });
  }

  return results;
}
