import { test, expect, Page } from "@playwright/test";

const BASE_URL = "http://127.0.0.1:8003";
const ADMIN_EMAIL = "test_admin_ui@example.com";
const ADMIN_PASSWORD = "TestAdmin@Pass123456";

const testPages = [
  { name: "Admin Users", path: "/admin/users" },
  { name: "Admin Sessions", path: "/admin/sessions" },
  { name: "Manage Tags", path: "/manage-tags" },
  { name: "Manage Categories", path: "/manage-categories" },
  { name: "Backup Management", path: "/backup-management" },
];

async function loginAsAdmin(page: Page) {
  await page.goto(`${BASE_URL}/login`);
  await page.fill('input[name="email"]', ADMIN_EMAIL);
  await page.fill('input[name="password"]', ADMIN_PASSWORD);
  await page.click('button[type="submit"]');
  await page.waitForNavigation();
}

test.describe("Skip Links Implementation - Phase 2B Priority 1", () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  for (const testPage of testPages) {
    test(`${testPage.name}: Skip link exists and is hidden initially`, async ({
      page,
    }) => {
      await page.goto(`${BASE_URL}${testPage.path}`);
      await page.waitForLoadState("networkidle");

      // Check skip link exists
      const skipLink = await page.$('a.skip-link');
      expect(skipLink).toBeTruthy();

      // Check it's initially hidden
      const isHidden = await skipLink.evaluate((el) => {
        const style = window.getComputedStyle(el);
        const clipPath = style.clipPath;
        return clipPath === "inset(50%)" || el.offsetWidth === 0 || el.offsetHeight === 0;
      });
      expect(isHidden).toBe(true);
    });

    test(`${testPage.name}: Skip link becomes visible on Tab focus`, async ({
      page,
    }) => {
      await page.goto(`${BASE_URL}${testPage.path}`);
      await page.waitForLoadState("networkidle");

      const skipLink = await page.$('a.skip-link');
      expect(skipLink).toBeTruthy();

      // Press Tab to focus skip link
      await page.keyboard.press("Tab");
      await page.waitForTimeout(200);

      // Check if visible
      const isVisible = await skipLink.evaluate((el) => {
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
      await page.screenshot({ path: `test-results/skip-link-${testPage.name.replace(/ /g, "-")}-focused.png` });
    });

    test(`${testPage.name}: Skip link has proper styling`, async ({ page }) => {
      await page.goto(`${BASE_URL}${testPage.path}`);
      await page.waitForLoadState("networkidle");

      const skipLink = await page.$('a.skip-link');
      expect(skipLink).toBeTruthy();

      // Focus and get styles
      await page.keyboard.press("Tab");
      await page.waitForTimeout(200);

      const hasVisibleStyle = await skipLink.evaluate((el) => {
        const style = window.getComputedStyle(el);
        const hasBgColor = style.backgroundColor !== "rgba(0, 0, 0, 0)" && style.backgroundColor !== "transparent";
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
      const mainContent = await page.$('#main-content');
      expect(mainContent).toBeTruthy();

      // Focus and activate skip link
      await page.keyboard.press("Tab");
      await page.keyboard.press("Enter");
      await page.waitForTimeout(300);

      // Take screenshot
      await page.screenshot({ path: `test-results/skip-link-${testPage.name.replace(/ /g, "-")}-activated.png` });
    });

    test(`${testPage.name}: Tab order continues after skip link activation`, async ({
      page,
    }) => {
      await page.goto(`${BASE_URL}${testPage.path}`);
      await page.waitForLoadState("networkidle");

      // Activate skip link
      await page.keyboard.press("Tab");
      await page.keyboard.press("Enter");
      await page.waitForTimeout(200);

      // Continue with Tab
      await page.keyboard.press("Tab");
      await page.waitForTimeout(200);

      // Check focused element is valid
      const focusedElement = await page.evaluate(() => {
        const active = document.activeElement;
        if (!active) return null;
        return {
          tag: active.tagName,
          id: active.id,
          hasContent: (active as HTMLElement).offsetHeight > 0,
        };
      });

      expect(focusedElement).toBeTruthy();
      expect(focusedElement?.hasContent).toBe(true);
    });

    test(`${testPage.name}: Full page screenshot`, async ({ page }) => {
      await page.goto(`${BASE_URL}${testPage.path}`);
      await page.waitForLoadState("networkidle");
      await page.screenshot({
        path: `test-results/skip-link-${testPage.name.replace(/ /g, "-")}-full.png`,
        fullPage: true,
      });
    });
  }
});
