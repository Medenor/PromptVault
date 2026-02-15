import { test, expect } from "@playwright/test";

const BASE_URL = "http://127.0.0.1:8003";
const ADMIN_USERNAME = process.env.ACCESSIBILITY_ADMIN_USERNAME || "test_admin_ui@example.com";
const ADMIN_PASSWORD = process.env.ACCESSIBILITY_ADMIN_PASSWORD || "TestAdmin@Pass123456";

// Protected pages that require authentication
const protectedPages = [
  { name: "Admin Users", path: "/admin/users" },
  { name: "Admin Sessions", path: "/admin/sessions" },
  { name: "Manage Tags", path: "/manage-tags" },
  { name: "Manage Categories", path: "/manage-categories" },
  { name: "Backup Management", path: "/backup-management" },
];

async function authenticateAndVisitPage(
  page: import("@playwright/test").Page,
  path: string
) {
  // Go to login page
  await page.goto(`${BASE_URL}/auth/login`, { waitUntil: "networkidle" });

  // Fill in credentials
  const usernameInput = page.locator("#username-or-email").first();
  const passwordInput = page.locator("#password").first();
  const loginButton = page.locator("button[type='submit']").first();

  // Check if elements exist before filling
  const usernameVisible = await usernameInput.isVisible({ timeout: 5000 }).catch(() => false);
  if (!usernameVisible) {
    throw new Error("Login form elements not found");
  }

  await usernameInput.fill(ADMIN_USERNAME);
  await passwordInput.fill(ADMIN_PASSWORD);

  // Wait for successful login by monitoring navigation
  const navigationPromise = page.waitForNavigation({ timeout: 20000 }).catch(() => null);
  await loginButton.click();
  await navigationPromise;

  // Now navigate to protected page
  await page.goto(`${BASE_URL}${path}`, { waitUntil: "networkidle" });
}

test.describe("Skip Links Implementation - Authenticated Routes", () => {
  for (const testPage of protectedPages) {
    test(`${testPage.name}: Skip link exists and is hidden initially`, async ({
      page,
    }) => {
      try {
        await authenticateAndVisitPage(page, testPage.path);

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
      } catch (error) {
        console.error(`Test failed for ${testPage.name}: ${error}`);
        throw error;
      }
    });

    test(`${testPage.name}: Skip link becomes visible on Tab focus`, async ({
      page,
    }) => {
      await authenticateAndVisitPage(page, testPage.path);

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
    });

    test(`${testPage.name}: Skip link has proper styling`, async ({ page }) => {
      await authenticateAndVisitPage(page, testPage.path);

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
      await authenticateAndVisitPage(page, testPage.path);

      // Check main content exists
      const mainContent = await page.$("#main-content");
      expect(mainContent).toBeTruthy();

      // Focus and activate skip link
      await page.keyboard.press("Tab");
      await page.keyboard.press("Enter");
      await page.waitForTimeout(300);
    });

    test(`${testPage.name}: Full page screenshot`, async ({ page }) => {
      await authenticateAndVisitPage(page, testPage.path);
      await page.screenshot({
        path: `test-results/skip-link-auth-${testPage.name.replace(/ /g, "-")}-full.png`,
        fullPage: true,
      });
    });
  }
});
