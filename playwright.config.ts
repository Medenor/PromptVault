// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

import { defineConfig, devices } from '@playwright/test';
import dotenv from 'dotenv';

/**
 * Read environment variables from file.
 * https://github.com/motdotla/dotenv
 */
dotenv.config();

/**
 * Playwright configuration for PromptVault accessibility and UI tests
 * See https://playwright.dev/docs/test-configuration.
 *
 * Supports both automated accessibility testing (axe-core + custom utilities)
 * and manual UI/authentication testing.
 */
export default defineConfig({
  testDir: './tests',
  testMatch: '**/*.spec.ts',

  /* Run tests in files in parallel */
  fullyParallel: true,

  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,

  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,

  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : undefined,

  /* Reporter to use */
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
    ['list'],
  ],

  /* Shared settings for all the projects below */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: process.env.ACCESSIBILITY_BASE_URL ?? 'http://127.0.0.1:8003',

    /* Collect trace when retrying the failed test. */
    trace: 'on-first-retry',

    /* Screenshot on failure */
    screenshot: 'only-on-failure',

    /* Video on failure */
    video: 'retain-on-failure',

    /* Headless mode for debugging - set HEADED=1 to run in headed mode */
    headless: !process.env.HEADED,
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      testDir: './tests/accessibility',
      use: { ...devices['Desktop Chrome'] },
    },

    /* Functional smoke tests (Phase 0c characterization safety net) */
    {
      name: 'smoke',
      testDir: './tests/smoke',
      use: { ...devices['Desktop Chrome'] },
    },

    {
      name: 'firefox',
      testDir: './tests/accessibility',
      use: { ...devices['Desktop Firefox'] },
    },

    {
      name: 'webkit',
      testDir: './tests/accessibility',
      use: { ...devices['Desktop Safari'] },
    },

    /* Test against mobile viewports */
    {
      name: 'Mobile Chrome',
      testDir: './tests/accessibility',
      use: { ...devices['Pixel 5'] },
    },

    {
      name: 'Mobile Safari',
      testDir: './tests/accessibility',
      use: { ...devices['iPhone 12'] },
    },

    /* Mobile-responsive UI feature (004-mobile-responsive-ui) E2E suites */
    {
      name: 'mobile',
      testDir: './tests/e2e',
      use: { ...devices['iPhone 14'] },
    },

    {
      name: 'iPhone 14',
      testDir: './tests/e2e',
      use: { ...devices['iPhone 14'] },
    },

    {
      name: 'Pixel 7',
      testDir: './tests/e2e',
      use: { ...devices['Pixel 7'] },
    },
  ],

  /* Run your local dev server before starting the tests */
  ...(process.env.ACCESSIBILITY_EXTERNAL_SERVER
    ? {}
    : {
        webServer: {
          command: 'UVICORN_RELOAD=false python3 run_web.py',
          url: process.env.ACCESSIBILITY_BASE_URL ?? 'http://127.0.0.1:8003',
          reuseExistingServer: !process.env.CI,
          timeout: 120 * 1000,
        },
      }),

  /* Global timeout - 60s for accessibility tests that may need extra time */
  timeout: 60 * 1000,

  /* Global test timeout */
  expect: {
    /**
     * Maximum time expect() should spend
     */
    timeout: 5000,
  },
});
