// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

import { expect, test } from '@playwright/test';
import { authenticatedAdminTest, authenticatedUserTest } from './fixtures/auth.js';

const baseURL = process.env.ACCESSIBILITY_BASE_URL;

if (!baseURL) {
  throw new Error('ACCESSIBILITY_BASE_URL must be set for accessibility focus tests.');
}

const PUBLIC_ROUTES = ['/', '/auth/login', '/auth/register'];
const USER_ROUTES = [
  '/auth/profile',
  '/import-export',
  '/backup-management',
  '/manage-categories',
  '/manage-tags',
];
const ADMIN_ROUTES = ['/admin/users', '/admin/sessions'];

async function assertVisibleFocusIndicator(page) {
  const focusState = await page.evaluate(() => {
    const active = document.activeElement;
    if (!active || active.tagName === 'BODY' || active.tagName === 'HTML') {
      return {
        hasActiveElement: false,
        hasVisibleFocus: false,
        outlineWidth: '0px',
      };
    }

    const styles = window.getComputedStyle(active);
    const outlineWidth = parseInt(styles.outlineWidth || '0', 10);
    const hasOutline = styles.outlineStyle !== 'none' && outlineWidth > 0;
    const hasBoxShadow = styles.boxShadow !== 'none';

    return {
      hasActiveElement: true,
      hasVisibleFocus: active.matches(':focus-visible') || hasOutline || hasBoxShadow,
      outlineWidth: styles.outlineWidth,
      tagName: active.tagName,
      id: active.id,
    };
  });

  expect(focusState.hasActiveElement).toBe(true);
  expect(focusState.hasVisibleFocus).toBe(true);
}

async function runFocusSmoke(page, route) {
  await page.goto(`${baseURL}${route}`, { waitUntil: 'networkidle' });
  await page.keyboard.press('Tab');
  await assertVisibleFocusIndicator(page);
}

test.describe('@smoke-a11y Focus Indicators Public Routes', () => {
  for (const route of PUBLIC_ROUTES) {
    test(`focus indicator is visible on ${route}`, async ({ page }) => {
      await runFocusSmoke(page, route);
    });
  }
});

authenticatedUserTest.describe('@smoke-a11y Focus Indicators User Routes', () => {
  for (const route of USER_ROUTES) {
    authenticatedUserTest(
      `focus indicator is visible on ${route}`,
      async ({ authenticatedPage }) => {
        await runFocusSmoke(authenticatedPage, route);
      }
    );
  }
});

authenticatedAdminTest.describe('@smoke-a11y Focus Indicators Admin Routes', () => {
  for (const route of ADMIN_ROUTES) {
    authenticatedAdminTest(
      `focus indicator is visible on ${route}`,
      async ({ authenticatedPage }) => {
        await runFocusSmoke(authenticatedPage, route);
      }
    );
  }
});
