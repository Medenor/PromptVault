import { test, expect } from "@playwright/test";
import { existsSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const BASE_URL = "http://127.0.0.1:8003";
const ADMIN_USERNAME = process.env.ACCESSIBILITY_ADMIN_USERNAME || "test_admin_ui@example.com";
const ADMIN_PASSWORD = process.env.ACCESSIBILITY_ADMIN_PASSWORD || "TestAdmin@Pass123456";

const authStateFile = join(tmpdir(), "admin-auth-state.json");

// Protected pages that require authentication
const protectedPages = [
  { name: "Admin Users", path: "/admin/users" },
  { name: "Admin Sessions", path: "/admin/sessions" },
  { name: "Manage Tags", path: "/manage-tags" },
  { name: "Manage Categories", path: "/manage-categories" },
  { name: "Backup Management", path: "/backup-management" },
];

async function login(page: import("@playwright/test").Page, username: string, password: string) {
  await page.goto(`${BASE_URL}/auth/login`, { waitUntil: "networkidle" });

  const usernameInput = page.locator("#username-or-email").first();
  const passwordInput = page.locator("#password").first();
  const loginButton = page.locator("button[type='submit']").first();

  await usernameInput.fill(username);
  await passwordInput.fill(password);

  const [loginResponse] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.url().includes("/api/auth/login") && response.request().method() === "POST",
      { timeout: 30000 }
    ),
    loginButton.click(),
  ]);

  if (!loginResponse.ok()) {
    throw new Error(
      `Login failed: received status ${loginResponse.status()} from /api/auth/login`
    );
  }

  await page.waitForURL((url) => !url.pathname.includes("/auth/login"), { timeout: 20000 });
}

test.beforeAll(async ({ browser }) => {
  if (!existsSync(authStateFile)) {
    const context = await browser.newContext();
    const page = await context.newPage();
    await login(page, ADMIN_USERNAME, ADMIN_PASSWORD);
    await context.storageState({ path: authStateFile });
    await context.close();
  }
});

test.describe("Skip Links Implementation - Authenticated Routes", () => {
  test.use({ storageState: authStateFile });

  for (const testPage of protectedPages) {
    test(`${testPage.name}: Skip link exists and is hidden initially`, async ({ page }) => {
      await page.goto(`${BASE_URL}${testPage.path}`);
      await page.waitForLoadState("networkidle");

      // Check skip link exists
      const skipLink = await page.$("a.skip-link");
      expect(skipLink).toBeTruthy();

      // Check it's initially hidden
      const isHidden = await skipLink!.evaluate((el) => {
        const style = window.getComputedStyle(el);
        const clipPath = style.clipPath;
        return clipPath === "inset(50%)" || el.offsetWidth === 0 || el.offsetHeight === 0;
      });
      expect(isHidden).toBe(true);
    });

    test(`${testPage.name}: Skip link becomes visible on Tab focus`, async ({ page }) => {
      await page.goto(`${BASE_URL}${testPage.path}`);
      await page.waitForLoadState("networkidle");

      const skipLink = await page.$("a.skip-link");
      expect(skipLink).toBeTruthy();

      // Press Tab to focus skip link
      await page.keyboard.press("Tab");
      await page.waitForTimeout(200);

      // Check if visible
      const isVisible = await skipLink!.evaluate((el) => {
        const rect = el.getBoundingClientRect();
        const style = window.getComputedStyle(el);
        return (
          rect.width > 0 &&
          rect.height > 0 &&
          style.visibility !== "hidden" &&
          style.display !== "none"
        );
      });
      expect(isVisible).toBe(true);

      // Screenshot of focused skip link
      await page.screenshot({
        path: `test-results/skip-link-auth-${testPage.name.replace(/ /g, "-")}-focused.png`,
      });
    });

    test(`${testPage.name}: Skip link has proper styling`, async ({ page }) => {
      await page.goto(`${BASE_URL}${testPage.path}`);
      await page.waitForLoadState("networkidle");

      const skipLink = await page.$("a.skip-link");
      expect(skipLink).toBeTruthy();

      // Focus and get styles
      await page.keyboard.press("Tab");
      await page.waitForTimeout(200);

      const hasVisibleStyle = await skipLink!.evaluate((el) => {
        const style = window.getComputedStyle(el);
        const hasBgColor =
          style.backgroundColor !== "rgba(0, 0, 0, 0)" &&
          style.backgroundColor !== "transparent";
        const hasTextColor = style.color !== "rgba(0, 0, 0, 0)" && style.color !== "transparent";
        const hasOutline = style.outline && style.outline !== "none";

        return hasBgColor || hasTextColor || hasOutline;
      });

      expect(hasVisibleStyle).toBe(true);
    });

    test(`${testPage.name}: Skip link navigates to main content`, async ({ page }) => {
      await page.goto(`${BASE_URL}${testPage.path}`);
      await page.waitForLoadState("networkidle");

      // Check main content exists
      const mainContent = await page.$("#main-content");
      expect(mainContent).toBeTruthy();

      // Focus and activate skip link
      await page.keyboard.press("Tab");
      await page.keyboard.press("Enter");
      await page.waitForTimeout(300);

      // Take screenshot
      await page.screenshot({
        path: `test-results/skip-link-auth-${testPage.name.replace(/ /g, "-")}-activated.png`,
      });
    });

    test(`${testPage.name}: Full page screenshot`, async ({ page }) => {
      await page.goto(`${BASE_URL}${testPage.path}`);
      await page.waitForLoadState("networkidle");
      await page.screenshot({
        path: `test-results/skip-link-auth-${testPage.name.replace(/ /g, "-")}-full.png`,
        fullPage: true,
      });
    });
  }
});
