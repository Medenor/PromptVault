// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

import { expect, test } from '@playwright/test';
import { AxeBuilder } from '@axe-core/playwright';
import type { AxeResults, Result } from 'axe-core';
import { existsSync, mkdirSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { isAbsolute, join, resolve } from 'node:path';

const BASE_URL = process.env.ACCESSIBILITY_BASE_URL ?? 'http://127.0.0.1:8003';
const AXE_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'];

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
      '/auth/forgot-password',
      '/auth/reset-password?token=test',
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
  : mkdtempSync(join(tmpdir(), 'promptvault-acc-'));

if (USING_EXTERNAL_STATE_DIR) {
  mkdirSync(STATE_DIR, { recursive: true });
}

const USER_STATE_PATH = join(STATE_DIR, 'user-state.json');
const ADMIN_STATE_PATH = join(STATE_DIR, 'admin-state.json');

// Login retries may wait for server-side rate-limit windows.
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

      // Add a small cushion so we don't retry right at the edge of the window.
      await page.waitForTimeout(backoffSeconds * 1000 + 1250);
      currentAttempt += 1;
      continue;
    }

    if (!loginResponse.ok()) {
      const extra =
        loginResponse.status() === 429
          ? ` (rate limited; try reusing ACCESSIBILITY_AUTH_STATE_DIR or using a single admin account for both user/admin scans)`
          : '';
      throw new Error(
        `Login failed for "${username}": received status ${loginResponse.status()} from /api/auth/login.${extra}`
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
      // Reuse state to avoid hammering rate-limited login endpoints across runs.
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
      // Reuse state to avoid hammering rate-limited login endpoints across runs.
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

for (const route of ROUTES) {
  test(`ACC-AXE: ${route} has no critical/serious accessibility violations`, async ({ browser }) => {
    const accessLevel = getRouteAccessLevel(route);
    const hasReusableUserState = USING_EXTERNAL_STATE_DIR && existsSync(USER_STATE_PATH);
    const hasReusableAdminState = USING_EXTERNAL_STATE_DIR && existsSync(ADMIN_STATE_PATH);

    test.skip(
      accessLevel === 'user' &&
        !hasReusableUserState &&
        (!ACCESSIBILITY_USER_USERNAME || !ACCESSIBILITY_USER_PASSWORD),
      `Skipping ${route}: set ACCESSIBILITY_USER_USERNAME and ACCESSIBILITY_USER_PASSWORD (or provide ACCESSIBILITY_AUTH_STATE_DIR with an existing user-state.json) to scan protected user pages.`
    );
    test.skip(
      accessLevel === 'admin' &&
        !hasReusableAdminState &&
        !hasReusableUserState &&
        (!ACCESSIBILITY_ADMIN_USERNAME || !ACCESSIBILITY_ADMIN_PASSWORD),
      `Skipping ${route}: set ACCESSIBILITY_ADMIN_USERNAME and ACCESSIBILITY_ADMIN_PASSWORD (or provide ACCESSIBILITY_AUTH_STATE_DIR with an existing admin-state.json) to scan protected admin pages.`
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
      const expectedPathname = new URL(route, BASE_URL).pathname;
      const response = await page.goto(targetUrl, { waitUntil: 'networkidle' });
      const contentType = response?.headers()['content-type'] ?? '';
      const status = response?.status() ?? 0;

      if (!contentType.includes('text/html') || status >= 400) {
        if (accessLevel === 'public') {
          test.skip(
            true,
            `Skipping ${route}: expected HTML page, received status ${status} with content-type "${contentType}".`
          );
        }
        throw new Error(
          `Expected HTML protected page for ${route}, received status ${status} and content-type "${contentType}". Check credentials/session state.`
        );
      }

      if (accessLevel !== 'public') {
        // Catch silent redirects to /auth/login (or other pages) so protected routes actually get scanned.
        const normalizePath = (pathname: string) =>
          pathname !== '/' && pathname.endsWith('/') ? pathname.slice(0, -1) : pathname;
        const finalPath = normalizePath(new URL(page.url()).pathname);
        const expectedPath = normalizePath(expectedPathname);
        if (finalPath !== expectedPath) {
          throw new Error(
            `Expected to scan protected route ${expectedPath}, but ended up at ${finalPath}. Check credentials/session state.`
          );
        }
      }

      const scan: AxeResults = await new AxeBuilder({ page }).withTags(AXE_TAGS).analyze();
      const blockingViolations = scan.violations.filter(
        (violation: Result) => violation.impact === 'critical' || violation.impact === 'serious'
      );

      const violationSummary = blockingViolations
        .map((violation: Result) => {
          const targets = violation.nodes
            .flatMap((node: Result['nodes'][number]) => node.target)
            .map((target) => String(target))
            .join(', ');
          return `${violation.id}: ${violation.help} [${targets}]`;
        })
        .join('\n');

      expect(
        blockingViolations,
        violationSummary || 'No critical/serious accessibility violations found.'
      ).toEqual([]);
    } finally {
      await context.close();
    }
  });
}
