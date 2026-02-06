// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

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
const STATE_DIR = mkdtempSync(join(tmpdir(), 'promptvault-acc-'));
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

  if (loginResponse.status() === 429 && attempt < 4) {
    const retryAfter = Number(loginResponse.headers()['retry-after'] ?? '60');
    await page.waitForTimeout((Number.isFinite(retryAfter) ? retryAfter : 60) * 1000 + 1500);
    await login(page, username, password, attempt + 1);
    return;
  }

  await page.waitForURL((url) => !url.pathname.includes('/auth/login'), { timeout: 20000 });
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

  if (ACCESSIBILITY_USER_USERNAME && ACCESSIBILITY_USER_PASSWORD) {
    await createStateForCredentials(
      browser,
      ACCESSIBILITY_USER_USERNAME,
      ACCESSIBILITY_USER_PASSWORD,
      USER_STATE_PATH
    );
  }

  if (
    ACCESSIBILITY_ADMIN_USERNAME &&
    ACCESSIBILITY_ADMIN_PASSWORD &&
    (!ACCESSIBILITY_USER_USERNAME ||
      ACCESSIBILITY_USER_USERNAME !== ACCESSIBILITY_ADMIN_USERNAME ||
      ACCESSIBILITY_USER_PASSWORD !== ACCESSIBILITY_ADMIN_PASSWORD)
  ) {
    await createStateForCredentials(
      browser,
      ACCESSIBILITY_ADMIN_USERNAME,
      ACCESSIBILITY_ADMIN_PASSWORD,
      ADMIN_STATE_PATH
    );
  }
});

test.afterAll(() => {
  rmSync(STATE_DIR, { recursive: true, force: true });
});

for (const route of ROUTES) {
  test(`ACC-AXE: ${route} has no critical/serious accessibility violations`, async ({ browser }) => {
    const accessLevel = getRouteAccessLevel(route);
    test.skip(
      accessLevel === 'user' && (!ACCESSIBILITY_USER_USERNAME || !ACCESSIBILITY_USER_PASSWORD),
      `Skipping ${route}: set ACCESSIBILITY_USER_USERNAME and ACCESSIBILITY_USER_PASSWORD to scan protected user pages.`
    );
    test.skip(
      accessLevel === 'admin' && (!ACCESSIBILITY_ADMIN_USERNAME || !ACCESSIBILITY_ADMIN_PASSWORD),
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

      const scan = await new AxeBuilder({ page }).withTags(AXE_TAGS).analyze();
      const blockingViolations = scan.violations.filter(
        (violation) => violation.impact === 'critical' || violation.impact === 'serious'
      );

      const violationSummary = blockingViolations
        .map((violation) => {
          const targets = violation.nodes
            .flatMap((node) => node.target)
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
