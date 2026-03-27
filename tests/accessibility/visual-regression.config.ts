// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

/**
 * Visual regression testing configuration for accessibility
 * Used for comparing focus indicators, contrast, and visual states
 */

import * as path from 'path';

/**
 * Visual regression test configuration
 */
export interface VisualRegressionConfig {
  // Directory to store baseline images
  baselineDir: string;

  // Directory to store actual comparison images
  actualDir: string;

  // Directory to store diff images
  diffDir: string;

  // Threshold for pixel differences (0-1, 0 = exact match)
  pixelThreshold: number;

  // Threshold for percentage of different pixels
  percentThreshold: number;

  // Whether to automatically update baselines
  updateBaselines: boolean;

  // Image format for comparisons
  imageFormat: 'png' | 'jpg';

  // Regions to ignore in visual comparisons
  ignoreRegions?: Array<{
    name: string;
    selector: string;
  }>;

  // Browsers to compare
  browsers: string[];

  // Device types to test
  devices: string[];
}

/**
 * Default configuration
 */
export const defaultConfig: VisualRegressionConfig = {
  baselineDir: path.join(__dirname, '__baseline__'),
  actualDir: path.join(__dirname, '__actual__'),
  diffDir: path.join(__dirname, '__diff__'),
  pixelThreshold: 0.2, // Allow 0.2% pixel difference
  percentThreshold: 0.5, // Allow 0.5% of pixels to differ
  updateBaselines: process.env.UPDATE_BASELINES === 'true',
  imageFormat: 'png',
  ignoreRegions: [
    {
      name: 'timestamp',
      selector: '[data-testid="timestamp"]',
    },
    {
      name: 'dynamic-content',
      selector: '[data-testid="dynamic"]',
    },
  ],
  browsers: ['chromium', 'firefox', 'webkit'],
  devices: ['desktop', 'tablet', 'mobile'],
};

/**
 * Visual states to test
 */
export const visualStates = {
  normal: {
    name: 'Normal',
    prepare: async (page: any) => {
      // Default state, no action needed
    },
  },
  hover: {
    name: 'Hover',
    prepare: async (page: any, selector: string) => {
      await page.locator(selector).hover();
    },
  },
  focus: {
    name: 'Focus',
    prepare: async (page: any, selector: string) => {
      await page.locator(selector).focus();
    },
  },
  active: {
    name: 'Active',
    prepare: async (page: any, selector: string) => {
      // Simulate active state
      await page.evaluate((sel: string) => {
        const el = document.querySelector(sel);
        if (el) el.classList.add('active');
      }, selector);
    },
  },
  disabled: {
    name: 'Disabled',
    prepare: async (page: any, selector: string) => {
      await page.evaluate((sel: string) => {
        const el = document.querySelector(sel) as HTMLElement;
        if (el) {
          el.setAttribute('disabled', 'disabled');
          el.setAttribute('aria-disabled', 'true');
        }
      }, selector);
    },
  },
};

/**
 * Get baseline path for element
 */
export function getBaselinePath(
  config: VisualRegressionConfig,
  page: string,
  element: string,
  state: string,
  browser: string
): string {
  return path.join(
    config.baselineDir,
    `${page}-${element}-${state}-${browser}.${config.imageFormat}`
  );
}

/**
 * Get actual image path
 */
export function getActualPath(
  config: VisualRegressionConfig,
  page: string,
  element: string,
  state: string,
  browser: string
): string {
  return path.join(
    config.actualDir,
    `${page}-${element}-${state}-${browser}.${config.imageFormat}`
  );
}

/**
 * Get diff image path
 */
export function getDiffPath(
  config: VisualRegressionConfig,
  page: string,
  element: string,
  state: string,
  browser: string
): string {
  return path.join(
    config.diffDir,
    `${page}-${element}-${state}-${browser}-diff.${config.imageFormat}`
  );
}

/**
 * Common visual regression checks
 */
export const visualChecks = {
  /**
   * Check focus indicator visibility
   */
  focusIndicator: {
    name: 'Focus Indicator Visibility',
    selector: '*:focus',
    states: ['normal', 'focus'],
    requirement:
      'WCAG 2.4.7 - Focus indicator must be visible on all interactive elements',
  },

  /**
   * Check color contrast
   */
  contrast: {
    name: 'Color Contrast',
    selector: 'body',
    states: ['normal'],
    requirement: 'WCAG 1.4.3 - Text must have sufficient contrast ratio',
  },

  /**
   * Check button states
   */
  buttonStates: {
    name: 'Button States',
    selector: 'button',
    states: ['normal', 'hover', 'focus', 'active'],
    requirement: 'Buttons must be visually distinct in different states',
  },

  /**
   * Check form field visual feedback
   */
  formFeedback: {
    name: 'Form Field Feedback',
    selector: 'input, textarea, select',
    states: ['normal', 'focus'],
    requirement: 'Form fields must provide clear visual feedback',
  },

  /**
   * Check disabled state visibility
   */
  disabledState: {
    name: 'Disabled State',
    selector: '[disabled], [aria-disabled="true"]',
    states: ['disabled', 'normal'],
    requirement: 'Disabled elements must be visually distinguishable',
  },

  /**
   * Check modal/dialog visibility
   */
  modalDialog: {
    name: 'Modal Dialog',
    selector: '[role="dialog"]',
    states: ['normal'],
    requirement: 'Modal dialogs must be clearly visible and distinct from background',
  },

  /**
   * Check navigation highlight
   */
  navigationHighlight: {
    name: 'Navigation Highlight',
    selector: 'nav a',
    states: ['normal', 'hover', 'focus'],
    requirement: 'Navigation items must be clearly identifiable and interactive',
  },
};

/**
 * Browser-specific visual considerations
 */
export const browserConsiderations = {
  chromium: {
    name: 'Chromium (Chrome)',
    focusStyle: 'outline',
    contrastCheck: true,
  },
  firefox: {
    name: 'Firefox',
    focusStyle: 'outline',
    contrastCheck: true,
  },
  webkit: {
    name: 'WebKit (Safari)',
    focusStyle: '-webkit-focus-ring-color',
    contrastCheck: true,
  },
};

/**
 * Device-specific visual considerations
 */
export const deviceConsiderations = {
  desktop: {
    name: 'Desktop',
    width: 1280,
    height: 1024,
    focusIndication: 'keyboard-only',
  },
  tablet: {
    name: 'Tablet',
    width: 768,
    height: 1024,
    focusIndication: 'touch-aware',
  },
  mobile: {
    name: 'Mobile',
    width: 375,
    height: 812,
    focusIndication: 'touch-aware',
  },
};

/**
 * Example usage in tests
 */
export const exampleTestUsage = `
import { Page, expect } from '@playwright/test';
import { defaultConfig, getBaselinePath, getActualPath, getDiffPath } from './visual-regression.config';

test('button focus indicator is visible', async ({ page, browserName }) => {
  await page.goto('/');

  // Take screenshot of button in focus state
  const button = page.locator('button').first();
  await button.focus();

  const path = getActualPath(defaultConfig, 'main', 'button', 'focus', browserName);
  await page.locator('button').first().screenshot({ path });

  // Compare with baseline
  const baselinePath = getBaselinePath(defaultConfig, 'main', 'button', 'focus', browserName);
  expect.soft(path).toMatchSnapshot(baselinePath);
});
`;

/**
 * Update baselines command
 */
export const updateCheckCommand = `
# Update baseline images after intentional visual changes
UPDATE_BASELINES=true npm run test:ui:accessibility

# Or specific test
UPDATE_BASELINES=true npx playwright test main-page.spec.ts
`;

/**
 * Export all config
 */
export default defaultConfig;
