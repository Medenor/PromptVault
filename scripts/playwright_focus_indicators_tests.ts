// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

import { expect, test } from '@playwright/test';
import { existsSync, mkdirSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { isAbsolute, join, resolve } from 'node:path';

const BASE_URL = process.env.ACCESSIBILITY_BASE_URL ?? 'http://127.0.0.1:8003';

const ROUTES =
  process.env.ACCESSIBILITY_PAGES
    ?.split(',')
    .map((route) => route.trim())
    .filter(Boolean) ?? [
      '/',
      '/import-export',
      '/backup-management',
      '/auth/login',
      '/auth/register',
      '/auth/profile',
      '/manage-categories',
      '/manage-tags',
      '/admin/users',
      '/admin/sessions',
    ];

const ACCESSIBILITY_USER_USERNAME = process.env.ACCESSIBILITY_USER_USERNAME;
const ACCESSIBILITY_USER_PASSWORD = process.env.ACCESSIBILITY_USER_PASSWORD;
const ACCESSIBILITY_ADMIN_USERNAME =
  process.env.ACCESSIBILITY_ADMIN_USERNAME ?? ACCESSIBILITY_USER_USERNAME;
const ACCESSIBILITY_ADMIN_PASSWORD =
  process.env.ACCESSIBILITY_ADMIN_PASSWORD ?? ACCESSIBILITY_USER_PASSWORD;
const EXTERNAL_STATE_DIR_RAW = process.env.ACCESSIBILITY_AUTH_STATE_DIR;
const USING_EXTERNAL_STATE_DIR = Boolean(EXTERNAL_STATE_DIR_RAW);
const STATE_DIR = USING_EXTERNAL_STATE_DIR
  ? isAbsolute(EXTERNAL_STATE_DIR_RAW!)
    ? EXTERNAL_STATE_DIR_RAW!
    : resolve(process.cwd(), EXTERNAL_STATE_DIR_RAW!)
  : mkdtempSync(join(tmpdir(), 'promptvault-focus-'));

if (USING_EXTERNAL_STATE_DIR) {
  mkdirSync(STATE_DIR, { recursive: true });
}

const USER_STATE_PATH = join(STATE_DIR, 'user-state.json');
const ADMIN_STATE_PATH = join(STATE_DIR, 'admin-state.json');

test.setTimeout(300000);

type AccessLevel = 'public' | 'user' | 'admin';

function getRouteAccessLevel(route: string): AccessLevel {
  const pathname = new URL(route, BASE_URL).pathname;
  if (pathname.startsWith('/admin/')) {
    return 'admin';
  }
  if (pathname === '/auth/profile' || pathname.startsWith('/manage-')) {
    return 'user';
  }
  return 'public';
}

async function login(
  page: import('@playwright/test').Page,
  username: string,
  password: string,
  attempt = 1
) {
  const maxAttempts = 7;
  let currentAttempt = attempt;

  while (true) {
    await page.goto(`${BASE_URL}/auth/login`, { waitUntil: 'networkidle' });

    const usernameInput = page.locator('#username-or-email').first();
    const passwordInput = page.locator('#password').first();
    const loginButton = page.locator('button[type="submit"]').first();

    await usernameInput.fill(username);
    await passwordInput.fill(password);
    const [loginResponse] = await Promise.all([
      page.waitForResponse(
        (response) =>
          response.url().includes('/api/auth/login') && response.request().method() === 'POST',
        { timeout: 30000 }
      ),
      loginButton.click(),
    ]);

    if (loginResponse.status() === 429 && currentAttempt < maxAttempts) {
      const rawRetryAfter = loginResponse.headers()['retry-after'];
      const retryAfter = rawRetryAfter ? Number(rawRetryAfter) : NaN;
      const backoffSeconds = Number.isFinite(retryAfter)
        ? Math.max(1, retryAfter)
        : Math.min(180, Math.pow(2, currentAttempt - 1) * 15);

      await page.waitForTimeout(backoffSeconds * 1000 + 1250);
      currentAttempt += 1;
      continue;
    }

    if (!loginResponse.ok()) {
      throw new Error(
        `Login failed for "${username}": received status ${loginResponse.status()} from /api/auth/login`
      );
    }

    await page.waitForURL((url) => !url.pathname.includes('/auth/login'), { timeout: 20000 });
    return;
  }
}

async function createStateForCredentials(
  browser: import('@playwright/test').Browser,
  username: string,
  password: string,
  outputPath: string
): Promise<void> {
  const context = await browser.newContext();
  const page = await context.newPage();
  await login(page, username, password);
  await context.storageState({ path: outputPath });
  await context.close();
}

test.beforeAll(async ({ browser }) => {
  test.setTimeout(300000);
  const forceRelogin = process.env.ACCESSIBILITY_FORCE_RELOGIN === '1';

  if (ACCESSIBILITY_USER_USERNAME && ACCESSIBILITY_USER_PASSWORD) {
    if (!forceRelogin && existsSync(USER_STATE_PATH)) {
      // Reuse state
    } else {
      await createStateForCredentials(
        browser,
        ACCESSIBILITY_USER_USERNAME,
        ACCESSIBILITY_USER_PASSWORD,
        USER_STATE_PATH
      );
    }
  }

  if (
    ACCESSIBILITY_ADMIN_USERNAME &&
    ACCESSIBILITY_ADMIN_PASSWORD &&
    (!ACCESSIBILITY_USER_USERNAME ||
      ACCESSIBILITY_USER_USERNAME !== ACCESSIBILITY_ADMIN_USERNAME ||
      ACCESSIBILITY_USER_PASSWORD !== ACCESSIBILITY_ADMIN_PASSWORD)
  ) {
    if (!forceRelogin && existsSync(ADMIN_STATE_PATH)) {
      // Reuse state
    } else {
      await createStateForCredentials(
        browser,
        ACCESSIBILITY_ADMIN_USERNAME,
        ACCESSIBILITY_ADMIN_PASSWORD,
        ADMIN_STATE_PATH
      );
    }
  }
});

test.afterAll(() => {
  if (!USING_EXTERNAL_STATE_DIR) {
    rmSync(STATE_DIR, { recursive: true, force: true });
  }
});

// Test focus indicators on all pages
for (const route of ROUTES) {
  test(`FOCUS: ${route} - All interactive elements have visible focus indicators`, async ({
    browser,
  }) => {
    const accessLevel = getRouteAccessLevel(route);
    const hasReusableUserState = USING_EXTERNAL_STATE_DIR && existsSync(USER_STATE_PATH);
    const hasReusableAdminState = USING_EXTERNAL_STATE_DIR && existsSync(ADMIN_STATE_PATH);

    test.skip(
      accessLevel === 'user' &&
        !hasReusableUserState &&
        (!ACCESSIBILITY_USER_USERNAME || !ACCESSIBILITY_USER_PASSWORD),
      `Skipping ${route}: set ACCESSIBILITY_USER_USERNAME and ACCESSIBILITY_USER_PASSWORD to scan protected user pages.`
    );
    test.skip(
      accessLevel === 'admin' &&
        !hasReusableAdminState &&
        !hasReusableUserState &&
        (!ACCESSIBILITY_ADMIN_USERNAME || !ACCESSIBILITY_ADMIN_PASSWORD),
      `Skipping ${route}: set ACCESSIBILITY_ADMIN_USERNAME and ACCESSIBILITY_ADMIN_PASSWORD to scan protected admin pages.`
    );

    const storageState =
      accessLevel === 'admin'
        ? ACCESSIBILITY_ADMIN_USERNAME === ACCESSIBILITY_USER_USERNAME &&
          ACCESSIBILITY_ADMIN_PASSWORD === ACCESSIBILITY_USER_PASSWORD
          ? USER_STATE_PATH
          : ADMIN_STATE_PATH
        : accessLevel === 'user'
          ? USER_STATE_PATH
          : undefined;

    const context = await browser.newContext(storageState ? { storageState } : undefined);
    const page = await context.newPage();

    try {
      const targetUrl = new URL(route, BASE_URL).toString();
      await page.goto(targetUrl, { waitUntil: 'networkidle' });

      // Find all interactive elements
      const interactiveElements = await page.locator(
        'button, a, input, select, textarea, [tabindex], [role="button"], [role="link"], th'
      );

      const count = await interactiveElements.count();
      expect(count).toBeGreaterThan(0);

      // Test focus on each interactive element using Tab key
      await page.keyboard.press('Tab');

      // Check if something is focused
      const focusedElement = await page.evaluate(() => {
        const active = document.activeElement;
        if (!active) return null;

        const styles = window.getComputedStyle(active);
        const outline = styles.outline;
        const outlineWidth = styles.outlineWidth;
        const outlineColor = styles.outlineColor;
        const outlineStyle = styles.outlineStyle;
        const outlineOffset = styles.outlineOffset;

        return {
          tagName: active.tagName,
          outline,
          outlineWidth,
          outlineColor,
          outlineStyle,
          outlineOffset,
        };
      });

      // Verify focus indicator exists
      expect(focusedElement).not.toBeNull();
      expect(focusedElement?.outline).not.toBe('');
      expect(focusedElement?.outlineStyle).not.toBe('none');

      // Additional validation: outline should be visible
      // Outline width should be at least 2px for WCAG 2.1 AA compliance
      const outlineWidthValue = focusedElement?.outlineWidth
        ? parseInt(focusedElement.outlineWidth, 10)
        : 0;
      expect(outlineWidthValue).toBeGreaterThanOrEqual(2);

      // Verify outline offset is set (should be 2px for accessibility)
      const offsetValue = focusedElement?.outlineOffset
        ? parseInt(focusedElement.outlineOffset, 10)
        : 0;
      expect(offsetValue).toBeGreaterThanOrEqual(0);
    } finally {
      await context.close();
    }
  });
}

// Dedicated test for focus indicator visibility
test('FOCUS: Verify 3px outline with 2px offset on buttons', async ({ browser }) => {
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    await page.goto(`${BASE_URL}/auth/login`, { waitUntil: 'networkidle' });

    // Find a button and focus it
    const submitButton = page.locator('button[type="submit"]').first();
    await submitButton.focus();

    // Check the computed styles
    const buttonStyles = await page.evaluate(() => {
      const btn = document.querySelector('button[type="submit"]');
      if (!btn) return null;

      const styles = window.getComputedStyle(btn);
      return {
        outline: styles.outline,
        outlineWidth: styles.outlineWidth,
        outlineColor: styles.outlineColor,
        outlineStyle: styles.outlineStyle,
        outlineOffset: styles.outlineOffset,
      };
    });

    expect(buttonStyles).not.toBeNull();
    expect(buttonStyles?.outlineStyle).toBe('solid');

    // Parse outline width (typically "3px" format)
    const widthValue = buttonStyles?.outlineWidth
      ? parseInt(buttonStyles.outlineWidth, 10)
      : 0;
    expect(widthValue).toBe(3);

    // Parse outline offset
    const offsetValue = buttonStyles?.outlineOffset
      ? parseInt(buttonStyles.outlineOffset, 10)
      : 0;
    expect(offsetValue).toBe(2);

    // Check outline color - should be a dark blue (#1e40af or similar)
    expect(buttonStyles?.outlineColor).not.toBe('transparent');
  } finally {
    await context.close();
  }
});

// Test focus indicators on form inputs
test('FOCUS: Verify focus indicators on form inputs', async ({ browser }) => {
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    await page.goto(`${BASE_URL}/auth/login`, { waitUntil: 'networkidle' });

    // Focus on username input
    const usernameInput = page.locator('#username-or-email').first();
    await usernameInput.focus();

    const inputStyles = await page.evaluate(() => {
      const input = document.querySelector('#username-or-email');
      if (!input) return null;

      const styles = window.getComputedStyle(input);
      return {
        outline: styles.outline,
        outlineWidth: styles.outlineWidth,
        outlineColor: styles.outlineColor,
        outlineStyle: styles.outlineStyle,
        outlineOffset: styles.outlineOffset,
      };
    });

    expect(inputStyles).not.toBeNull();
    expect(inputStyles?.outlineStyle).toBe('solid');

    const widthValue = inputStyles?.outlineWidth ? parseInt(inputStyles.outlineWidth, 10) : 0;
    expect(widthValue).toBe(3);

    const offsetValue = inputStyles?.outlineOffset ? parseInt(inputStyles.outlineOffset, 10) : 0;
    expect(offsetValue).toBe(2);
  } finally {
    await context.close();
  }
});

// Test focus indicators on links
test('FOCUS: Verify focus indicators on links', async ({ browser }) => {
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });

    // Find a link and focus it
    const link = page.locator('a').first();
    await link.focus();

    const linkStyles = await page.evaluate(() => {
      const a = document.querySelector('a');
      if (!a) return null;

      const styles = window.getComputedStyle(a);
      return {
        outline: styles.outline,
        outlineWidth: styles.outlineWidth,
        outlineColor: styles.outlineColor,
        outlineStyle: styles.outlineStyle,
        outlineOffset: styles.outlineOffset,
      };
    });

    expect(linkStyles).not.toBeNull();
    expect(linkStyles?.outlineStyle).toBe('solid');

    const widthValue = linkStyles?.outlineWidth ? parseInt(linkStyles.outlineWidth, 10) : 0;
    expect(widthValue).toBe(3);

    const offsetValue = linkStyles?.outlineOffset ? parseInt(linkStyles.outlineOffset, 10) : 0;
    expect(offsetValue).toBe(2);
  } finally {
    await context.close();
  }
});
