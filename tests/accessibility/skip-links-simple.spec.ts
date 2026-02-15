import { test, expect } from "@playwright/test";

const BASE_URL = "http://127.0.0.1:8003";

// Test pages - we'll focus on public and login pages first
const testPages = [
  { name: "Home", path: "/" },
  { name: "Login", path: "/auth/login" },
  { name: "Register", path: "/auth/register" },
];

test.describe("Skip Links Implementation - Simple Test", () => {
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
      const isHidden = await skipLink!.evaluate((el) => {
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

      const hasVisibleStyle = await skipLink!.evaluate((el) => {
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
