import { test, expect } from "@playwright/test";

const BASE_URL = "http://127.0.0.1:8003";
const ADMIN_EMAIL = "test_admin_ui@example.com";
const ADMIN_PASSWORD = "TestAdmin@Pass123456";

test("Debug: Check if login page loads", async ({ page }) => {
  console.log("Navigating to login page...");
  await page.goto(`${BASE_URL}/login`, { waitUntil: "domcontentloaded" });
  console.log("Login page loaded");
  
  const title = await page.title();
  console.log("Page title:", title);
  
  const pageContent = await page.content();
  const hasForm = pageContent.includes('name="email"');
  console.log("Has email form field:", hasForm);
  
  expect(hasForm).toBe(true);
});

test("Debug: Check if admin users page exists", async ({ page }) => {
  console.log("Navigating to admin/users without login...");
  await page.goto(`${BASE_URL}/admin/users`, { waitUntil: "domcontentloaded" });
  
  const status = page.url();
  console.log("Final URL after navigation:", status);
  
  const pageContent = await page.content();
  console.log("Page content length:", pageContent.length);
  console.log("Page contains 'Not Found':", pageContent.includes("Not Found"));
  console.log("Page contains 'Users':", pageContent.includes("Users"));
});

test("Debug: Try login and then access admin users", async ({ page }) => {
  console.log("Step 1: Navigate to login");
  await page.goto(`${BASE_URL}/login`, { waitUntil: "domcontentloaded" });
  
  console.log("Step 2: Fill email field");
  const emailField = await page.$('input[name="email"]');
  if (!emailField) {
    console.log("ERROR: Email field not found!");
    const html = await page.content();
    console.log("Page HTML length:", html.length);
    console.log("Has form element:", html.includes("<form"));
    return;
  }
  
  await page.fill('input[name="email"]', ADMIN_EMAIL);
  console.log("Step 3: Fill password field");
  await page.fill('input[name="password"]', ADMIN_PASSWORD);
  
  console.log("Step 4: Click submit button");
  const submitButton = await page.$('button[type="submit"]');
  if (!submitButton) {
    console.log("ERROR: Submit button not found!");
    return;
  }
  
  await submitButton.click();
  console.log("Step 5: Wait for navigation");
  await page.waitForNavigation({ waitUntil: "domcontentloaded" }).catch(() => {
    console.log("Navigation promise rejected, continuing anyway");
  });
  
  console.log("Step 6: Current URL after login:", page.url());
  
  console.log("Step 7: Navigate to admin/users");
  await page.goto(`${BASE_URL}/admin/users`, { waitUntil: "domcontentloaded" });
  console.log("Step 8: Final URL:", page.url());
  
  const skipLink = await page.$('a.skip-link');
  console.log("Skip link found:", skipLink !== null);
  
  if (skipLink) {
    const text = await skipLink.textContent();
    console.log("Skip link text:", text);
  }
});
